"""
Channel-based scraper using a TEXT-FIRST extraction strategy.

For each video we send Gemini a single text-only prompt containing the
creator's title, full description, and (if available) auto-captions
transcript. Gemini extracts the weapon builds the creator EXPLICITLY
recommends as current-meta. If the text pass returns nothing AND the
title looks like a build/loadout video, we fall back to a clipped
visual analysis (head + tail of the video).

Validation:
- weapon_name must match (case-insensitive, ignoring dashes/spaces) one of
  the canonical weapon names in wzhub.WARZONE_BUILDS. This kills
  hallucinations and weapons from previous-game eras.
- weapon_class is corrected to the canonical class for that weapon.
- attachment SLOT names must be from a fixed list. Attachment NAMES
  themselves are not whitelisted (they vary per build/season).

Per channel dedupe: same canonical weapon → most recent video wins.
"""

import os
import json
import re
import time
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build as ytbuild

# ──────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────

CHANNELS = [
    {"name": "Camy",       "id": "UC6MKLs52vIfPXWyatOQDXmw", "play_style": "Fast Movement"},
    {"name": "Lion",       "id": "UCnsRRitecBw8Vkx3ix1Ualw", "play_style": "Legacy Meta"},
    {"name": "Ryda",       "handle": "Ryda",                  "play_style": "Rank Play"},
    {"name": "eyeqew",     "id": "UCSF0PqIaps7jindnj6ICTfQ", "play_style": "Personal Meta Builds"},
    {"name": "stract",     "id": "UCbTCJUYDKatfSB_EYBnEghg", "play_style": "Casual and Meta"},
    {"name": "Cpreds",     "handle": "cpreds",                "play_style": "Casual"},
    {"name": "Swagg",      "id": "UCW1CGYCjfKhNLGp_Os1g_Mg", "play_style": "Team Play"},
    {"name": "MrMarvelTV", "id": "UCqBaw9Ze5EJ4fJVbaXbhnmw", "play_style": "Meta and Follower Builds"},
]

DEFAULT_LOOKBACK_DAYS = 7
GEMINI_MODEL = "gemini-2.5-flash"

# Pacing — on the paid Gemini tier (~1M tokens/min) text calls barely
# dent the budget, so the inter-call sleep can be short. It's kept
# non-zero only to be a polite API citizen.
SLEEP_BETWEEN_CALLS_S = 2.0
MAX_VIDEOS_PER_CHANNEL = 12

# On the paid Gemini tier (Tier 1+) the per-minute budget is ~1M tokens,
# so visual is now affordable. Both default ON:
#   ENABLE_VISUAL_FALLBACK — text returned nothing → visual head+tail
#                            clips to find which weapons appear.
#   ENABLE_VISUAL_ENRICH   — text returned weapons but with empty
#                            attachments → scan the FULL video to read
#                            the gunsmith screen wherever it appears.
ENABLE_VISUAL_ENRICH = os.environ.get("ENABLE_VISUAL_ENRICH", "1") == "1"
ENABLE_VISUAL_FALLBACK = os.environ.get("ENABLE_VISUAL_FALLBACK", "1") == "1"

# Visual fallback clip lengths (only used when ENABLE_VISUAL_FALLBACK=1)
HEAD_S = 90
TAIL_S = 90
MIN_GAP_S = 30
# Min seconds between two visual calls. On paid tier we can afford a much
# shorter cooldown than the free-tier 60s.
VISUAL_COOLDOWN_S = 10.0
_last_visual_at = 0.0

VALID_SLOTS = {
    "Optic", "Muzzle", "Barrel", "Underbarrel", "Magazine", "Stock",
    "Rear Grip", "Laser", "Fire Mods", "Conversion Kit", "Bolt",
    "Comb", "Stock Pad", "Ammunition", "Trigger Action", "Arms", "Cable",
}
VALID_CLASSES = {"AR", "SMG", "LMG", "Sniper", "Shotgun", "Marksman", "Pistol"}
VALID_TIERS = {"Absolute Meta", "Meta", "A", "B", "F"}
VALID_DOMINANCIES = {"Long Range", "Close Range", "Sniper", "Support",
                     "Hip Fire", "Aggressive", "Lowest Recoil"}

# Title keywords that suggest the video is build/loadout content. Used to
# gate the visual fallback (no point analysing a tournament gameplay clip).
BUILD_TITLE_KEYWORDS = [
    "loadout", "meta", "build", "best ", "tier ", "broken", " op ",
    "class setup", "gun setup", "guide", "season", "s tier", "broken af",
]


# ──────────────────────────────────────────────────────────────────────────
# Whitelist (built lazily from wzhub.WARZONE_BUILDS)
# ──────────────────────────────────────────────────────────────────────────

_VALID_WEAPONS_CACHE: dict[str, str] | None = None
_WEAPON_TO_CLASS_CACHE: dict[str, str] | None = None

# Fail-fast on persistent quota exhaustion. When `_quota_dead` flips True
# every subsequent Gemini call short-circuits to [] without spending API
# budget. Reset at the start of each scrape() invocation.
_quota_dead = False
_consecutive_429 = 0
ABORT_429_THRESHOLD = 3


class QuotaExhausted(Exception):
    pass


def _normalize_for_match(s: str) -> str:
    return re.sub(r"[\s\-_.]+", "", s.lower())


def _whitelist_path() -> str:
    data_dir = os.environ.get("DB_DIR")
    if not data_dir:
        data_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(data_dir, "codmunity_whitelist.json")


def _load_codmunity_whitelist() -> tuple[dict[str, str], dict[str, str]] | None:
    """Returns (valid, classes) if codmunity cache is available, else None."""
    path = _whitelist_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[yt-gem] codmunity whitelist load failed: {e}")
        return None
    cm_weapons = data.get("weapons", {})
    if not cm_weapons:
        return None
    valid: dict[str, str] = {}
    classes: dict[str, str] = {}
    for name, cls in cm_weapons.items():
        valid[name.lower()] = name
        valid[_normalize_for_match(name)] = name
        classes[name] = cls or "AR"
    return valid, classes


def _ensure_weapon_cache() -> None:
    global _VALID_WEAPONS_CACHE, _WEAPON_TO_CLASS_CACHE
    if _VALID_WEAPONS_CACHE is not None:
        return

    # 1. Primary: codmunity whitelist (written by gemini_site.scrape_codmunity)
    cm = _load_codmunity_whitelist()
    if cm is not None:
        _VALID_WEAPONS_CACHE, _WEAPON_TO_CLASS_CACHE = cm
        n = len(_WEAPON_TO_CLASS_CACHE)
        print(f"[yt-gem] using codmunity whitelist ({n} weapons)")
        return

    # 2. Fallback: wzhub canonical list (only used until codmunity cache exists)
    print("[yt-gem] codmunity whitelist unavailable, falling back to wzhub")
    valid: dict[str, str] = {}
    classes: dict[str, str] = {}
    try:
        from scrapers.wzhub import WARZONE_BUILDS
    except ImportError:
        try:
            from .wzhub import WARZONE_BUILDS  # type: ignore
        except Exception:
            print("[yt-gem] wzhub unavailable too — whitelist empty!")
            _VALID_WEAPONS_CACHE = valid
            _WEAPON_TO_CLASS_CACHE = classes
            return
    for b in WARZONE_BUILDS:
        canonical = b["weapon_name"]
        wclass = b["weapon_class"]
        valid[canonical.lower()] = canonical
        valid[_normalize_for_match(canonical)] = canonical
        classes[canonical] = wclass
    _VALID_WEAPONS_CACHE = valid
    _WEAPON_TO_CLASS_CACHE = classes


def _normalize_weapon_name(name: str) -> str | None:
    """Return canonical name from wzhub list, or None if not whitelisted."""
    if not name:
        return None
    _ensure_weapon_cache()
    n = name.strip().lower()
    if n in _VALID_WEAPONS_CACHE:  # type: ignore[operator]
        return _VALID_WEAPONS_CACHE[n]  # type: ignore[index]
    return _VALID_WEAPONS_CACHE.get(_normalize_for_match(n))  # type: ignore[union-attr]


def _canonical_class_for(weapon: str) -> str | None:
    _ensure_weapon_cache()
    return _WEAPON_TO_CLASS_CACHE.get(weapon)  # type: ignore[union-attr]


def _valid_weapons_for_prompt() -> str:
    _ensure_weapon_cache()
    seen: set[str] = set()
    out: list[str] = []
    for v in _VALID_WEAPONS_CACHE.values():  # type: ignore[union-attr]
        if v not in seen:
            seen.add(v)
            out.append(v)
    out.sort()
    return ", ".join(out)


# Generic / hallucinated attachment-name patterns. If a Gemini-returned name
# matches any of these (case-insensitive), we drop the attachment because it's
# almost certainly not a real in-game name.
_GENERIC_ATT_PATTERNS = [
    # Bare measurements: "18-inch barrel", "16 inch barrel", "22\" barrel"
    re.compile(r"^\d{1,3}[\-\s\"']?(inch|in|\")?\s*(barrel|long\s*barrel|short\s*barrel)$", re.I),
    # Bare round counts: "45 round mag", "60-round drum", "100 round belt"
    re.compile(r"^\d{1,3}[\-\s]?round\s*(mag|magazine|drum|belt)$", re.I),
    # Pure generic mag names with no brand prefix
    re.compile(r"^(extended|standard|tactical|fast)\s*mag(azine)?\s*(i{1,3}|ii)?$", re.I),
    # Bare "FMJ" / "API" / "Tracer" / "Hollow Point" / "AP" with no calibre
    re.compile(r"^(fmj|api|tracer|hollow\s*point|ap|incendiary)(\s*ammunition|\s*rounds)?$", re.I),
    # Generic optic descriptions
    re.compile(r"^(red\s*dot|iron\s*sights?|holographic|2x|3x|4x|6x)(\s*sight|\s*optic)?$", re.I),
    # Pure generic grip / stock / suppressor / brake names
    re.compile(r"^(vertical|ranger|commando|quickdraw|ergonomic|infiltrator)\s*(foregrip|grip|stock|pad)$", re.I),
    re.compile(r"^(suppressor|silencer|muzzle\s*brake|compensator|flash\s*hider)$", re.I),
    re.compile(r"^(short|long|reinforced|gain[-\s]?twist|heavy)\s*barrel$", re.I),
    # "Light Stock", "Heavy Stock", "Balanced Stock" without brand
    re.compile(r"^(light|heavy|balanced|no)\s*stock(\s*mod)?$", re.I),
]


def _looks_generic(name: str) -> bool:
    n = name.strip()
    if not n:
        return True
    return any(p.match(n) for p in _GENERIC_ATT_PATTERNS)


def _validate_build(b: dict) -> dict | None:
    """Sanitize a raw Gemini build dict; return None to drop."""
    canonical = _normalize_weapon_name(b.get("weapon_name", ""))
    if not canonical:
        return None  # not on whitelist → drop

    wclass_input = (b.get("weapon_class") or "").strip()
    canonical_class = _canonical_class_for(canonical)
    wclass = canonical_class or (wclass_input if wclass_input in VALID_CLASSES else "AR")

    tier = b.get("tier") or "A"
    if tier not in VALID_TIERS:
        tier = "A"

    dominancy = b.get("weapon_dominancy")
    if dominancy not in VALID_DOMINANCIES:
        dominancy = None

    raw_atts = b.get("attachments") or []
    clean_atts: list[str] = []
    dropped_generic = 0
    for att in raw_atts:
        if not isinstance(att, str) or ":" not in att:
            continue
        slot, name = att.split(":", 1)
        slot = slot.strip()
        name = name.strip()
        if slot not in VALID_SLOTS or not name:
            continue
        if _looks_generic(name):
            dropped_generic += 1
            continue
        clean_atts.append(f"{slot}: {name}")

    if dropped_generic:
        print(f"[yt-gem]     {canonical}: dropped {dropped_generic} generic-looking attachment(s)")

    return {
        "weapon_name": canonical,
        "weapon_class": wclass,
        "tier": tier,
        "weapon_dominancy": dominancy,
        "attachments": clean_atts,
        "confidence": float(b.get("confidence") or 0.7),
        "reasoning": (b.get("reasoning") or "")[:300],
    }


# ──────────────────────────────────────────────────────────────────────────
# YouTube API helpers
# ──────────────────────────────────────────────────────────────────────────

def _published_after(lookback_days: int) -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    return cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_channel_id(youtube, channel: dict) -> str | None:
    if "id" in channel:
        return channel["id"]
    try:
        resp = youtube.channels().list(part="id", forHandle=channel["handle"]).execute()
        items = resp.get("items", [])
        if items:
            return items[0]["id"]
    except Exception as e:
        print(f"[yt-gem] handle resolution failed for @{channel['handle']}: {e}")
    return None


def _list_recent_videos(youtube, channel_id: str, after: str) -> list[dict]:
    out: list[dict] = []
    page_token = None
    while True:
        try:
            kwargs = dict(
                channelId=channel_id, part="snippet", type="video",
                order="date", publishedAfter=after, maxResults=50,
            )
            if page_token:
                kwargs["pageToken"] = page_token
            resp = youtube.search().list(**kwargs).execute()
        except Exception as e:
            print(f"[yt-gem] search failed: {e}")
            break

        for item in resp.get("items", []):
            out.append({
                "videoId": item["id"]["videoId"],
                "title": item["snippet"].get("title", ""),
                "publishedAt": item["snippet"].get("publishedAt", ""),
            })
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return out


_DURATION_RE = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def _parse_iso_duration(s: str) -> int:
    if not s:
        return 0
    m = _DURATION_RE.match(s)
    if not m:
        return 0
    h, mi, sec = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + sec


def _fetch_metadata(youtube, video_ids: list[str]) -> dict[str, dict]:
    """Returns {video_id: {description, duration_s}} via videos.list."""
    out: dict[str, dict] = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        try:
            resp = youtube.videos().list(
                part="snippet,contentDetails", id=",".join(batch)
            ).execute()
            for item in resp.get("items", []):
                vid = item["id"]
                desc = item.get("snippet", {}).get("description", "")
                dur = _parse_iso_duration(
                    item.get("contentDetails", {}).get("duration", "")
                )
                out[vid] = {"description": desc, "duration_s": dur}
        except Exception as e:
            print(f"[yt-gem] videos.list failed: {e}")
    return out


def _fetch_transcript(video_id: str) -> str | None:
    """Try to fetch English captions (often blocked from cloud IPs)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        chunks = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["en", "en-US", "en-GB"]
        )
        return " ".join(c["text"] for c in chunks)
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────
# Gemini extraction
# ──────────────────────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*", "", (text or "").strip())
    text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {"builds": []}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"builds": []}


def _today_label() -> str:
    return datetime.now().strftime("%B %Y")


def _build_text_prompt(title: str, description: str, transcript: str | None) -> str:
    return f"""You are analysing a Call of Duty: Warzone meta-build YouTube video.

Today is {_today_label()} — Warzone is currently in the BO7 (Black Ops 7) era.

Below is the creator's title, full description, and (if available) auto-captions transcript. **You also have Google Search available** — use it to pull in additional context about this video: third-party recaps, tier-list mentions, comment summaries, the creator's other recent uploads, anything that helps you identify the EXACT weapons + attachments the creator recommends. Don't speculate — only include builds you can verify either from the metadata below or from search results.

Extract every weapon build the creator EXPLICITLY recommends as a CURRENT-meta loadout.

STRICT FILTERING RULES:
- IGNORE weapons the creator describes as old, outdated, or no longer meta.
- IGNORE casual mentions like "I used this last season" or "back when X was meta".
- IGNORE comparison clips that aren't recommendations.
- ONLY include weapons whose name (case-insensitive, ignoring dashes/spaces) matches one from this list:
{_valid_weapons_for_prompt()}

If a weapon is not in this list — even if the creator clearly recommends it — DO NOT include it.

For each qualifying build, return strict JSON with these fields:
- weapon_name: exact match from the list above
- weapon_class: AR, SMG, LMG, Sniper, Shotgun, Marksman, or Pistol
- tier: infer from creator's words —
    * "Absolute Meta" if they say "best", "S-tier", "absolutely broken", "the new king"
    * "Meta" if they say "top pick", "very strong", "great choice"
    * "A" if "solid", "decent", "viable"
    * "B" if "okay" or "outclassed"
    * "F" if "skip", "trash", "don't use"
- weapon_dominancy: Long Range, Close Range, Sniper, Support, Hip Fire, Aggressive, or Lowest Recoil
- attachments: array of "<Slot>: <Name>" — ONLY include attachments where you know the EXACT in-game name as shown in Warzone's gunsmith. Real attachments have proprietary brand-prefixed names — e.g. "Greaves Bellum Barrel", "Bowen Bighorn Drum", "Monolithic Suppressor", "5.56 NATO FMJ", "Hawker Cub-55 Pad", "VAS Drift Lock Foregrip".
    DO NOT use generic descriptive names — these are hallucinations and will be dropped:
      ✗ "18-inch barrel"  → no brand prefix
      ✗ "45 round mag"    → use the in-game mag name like "Rhodes Drum Mag"
      ✗ "FMJ ammunition"  → use the in-game name like "5.56 NATO FMJ"
      ✗ "extended mag"    → use the specific extended mag's brand name
    If you cannot find the exact in-game attachment name in the description, transcript, or search results, OMIT that slot entirely. An empty attachments array is far better than fabricated names.
    Slot must be one of: Optic, Muzzle, Barrel, Underbarrel, Magazine, Stock, Rear Grip, Laser, Fire Mods, Conversion Kit, Bolt, Comb, Stock Pad, Ammunition, Trigger Action.
- confidence: 0.0–1.0 — high if the creator gives a full clear recommendation; low if it's a fleeting mention.
- reasoning: one short sentence (paraphrase the creator's reasoning).

Return ONLY: {{"builds": [...]}}. If nothing qualifies, return {{"builds": []}}.

────── VIDEO METADATA ──────

TITLE: {title}

DESCRIPTION:
{(description or "(none)")[:5000]}

TRANSCRIPT:
{(transcript or "(no transcript available)")[:8000]}
"""


def _build_visual_prompt() -> str:
    return f"""You are analysing a Call of Duty: Warzone meta-build YouTube video. The clips are the BEGINNING and END of the video — where creators usually showcase loadouts.

Today is {_today_label()}. Warzone is in the BO7 era.

ONLY include weapons whose name matches one from this list:
{_valid_weapons_for_prompt()}

For each build return strict JSON:
- weapon_name (from list above)
- weapon_class (AR, SMG, LMG, Sniper, Shotgun, Marksman, or Pistol)
- tier ("Absolute Meta", "Meta", "A", "B", "F")
- weapon_dominancy (Long Range, Close Range, Sniper, Support, Hip Fire, Aggressive, Lowest Recoil)
- attachments: array of "<Slot>: <Name>" you can clearly see on-screen. Slot from: Optic, Muzzle, Barrel, Underbarrel, Magazine, Stock, Rear Grip, Laser, Fire Mods, Conversion Kit, Bolt, Comb, Stock Pad, Ammunition, Trigger Action.
- confidence (0.0–1.0)
- reasoning (one short sentence)

Return ONLY: {{"builds": [...]}}. Drop weapons not in the list.
"""


def _gemini_call_with_retry(make_request_fn, label: str, max_retries: int = 2) -> list[dict]:
    """Generic retry wrapper for Gemini calls. make_request_fn() returns the response.
    Tracks consecutive 429s in a module-level counter; once we hit
    ABORT_429_THRESHOLD in a row, raise QuotaExhausted so the caller can
    bail out of the whole channel sweep instead of grinding for 30 minutes."""
    global _consecutive_429, _quota_dead

    if _quota_dead:
        return []  # short-circuit — quota already declared dead this run

    for attempt in range(max_retries + 1):
        try:
            resp = make_request_fn()
            text = (resp.text or "").strip()
            if not text:
                _consecutive_429 = 0
                return []
            parsed = _extract_json(text)
            builds = parsed.get("builds", [])
            _consecutive_429 = 0
            return builds if isinstance(builds, list) else []
        except Exception as e:
            err = str(e)
            permission = "403" in err or "PERMISSION_DENIED" in err
            if permission:
                print(f"[yt-gem] {label}: 403 (skipping)")
                _consecutive_429 = 0
                return []

            is_429 = "429" in err or "RESOURCE_EXHAUSTED" in err
            is_503 = "503" in err or "UNAVAILABLE" in err
            transient = is_429 or is_503

            if is_429:
                _consecutive_429 += 1
                if _consecutive_429 >= ABORT_429_THRESHOLD:
                    _quota_dead = True
                    print(f"[yt-gem] {_consecutive_429} consecutive 429s — declaring quota dead, aborting")
                    raise QuotaExhausted()

            if transient and attempt < max_retries:
                m = re.search(r"retry in ([\d.]+)s", err)
                wait = float(m.group(1)) if m else 30 * (attempt + 1)
                wait += 5
                print(f"[yt-gem] {label}: transient err, sleep {wait:.1f}s")
                time.sleep(wait)
                continue
            print(f"[yt-gem] {label} failed: {type(e).__name__}: {err[:200]}")
            return []
    return []


def _gemini_text_call(prompt: str, client) -> list[dict]:
    """Text call WITH Google Search grounding so Gemini can supplement
    the title/description/transcript we provide with anything Google has
    indexed about the video (third-party recaps, comment summaries,
    creator's other content, tier-list mentions, etc.)."""
    from google.genai import types
    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
    )
    return _gemini_call_with_retry(
        lambda: client.models.generate_content(
            model=GEMINI_MODEL, contents=prompt, config=config
        ),
        label="text",
    )


def _build_visual_content(video_url: str, duration_s: int, full: bool = False):
    """Build a Gemini Content for visual analysis.
    - full=False → head + tail clips only (cheap, used for the fallback
      path where we just need to know which weapons appear).
    - full=True  → the ENTIRE video, no clipping. Used when we already
      know the weapons but couldn't get their attachments — the gunsmith
      screen can appear anywhere in the video, so we must scan all of it."""
    from google.genai import types
    parts = []
    if full:
        # Whole video, no clipping.
        parts.append(types.Part(file_data=types.FileData(file_uri=video_url)))
    elif not duration_s or duration_s <= HEAD_S + MIN_GAP_S:
        parts.append(types.Part(file_data=types.FileData(file_uri=video_url)))
    else:
        head_end = min(HEAD_S, duration_s)
        parts.append(types.Part(
            file_data=types.FileData(file_uri=video_url),
            video_metadata=types.VideoMetadata(start_offset="0s", end_offset=f"{head_end}s"),
        ))
        tail_start = max(head_end + MIN_GAP_S, duration_s - TAIL_S)
        if tail_start < duration_s:
            parts.append(types.Part(
                file_data=types.FileData(file_uri=video_url),
                video_metadata=types.VideoMetadata(start_offset=f"{tail_start}s", end_offset=f"{duration_s}s"),
            ))
    parts.append(types.Part(text=_build_visual_prompt()))
    return types.Content(parts=parts)


def _gemini_visual_call(video_url: str, duration_s: int, client,
                        full: bool = False) -> list[dict]:
    """Visual call respects a global cooldown so we don't blow the quota.
    `full=True` sends the whole video instead of head+tail clips."""
    global _last_visual_at
    elapsed = time.time() - _last_visual_at
    if elapsed < VISUAL_COOLDOWN_S:
        wait = VISUAL_COOLDOWN_S - elapsed
        print(f"[yt-gem] visual cooldown — waiting {wait:.1f}s")
        time.sleep(wait)
    _last_visual_at = time.time()

    contents = _build_visual_content(video_url, duration_s, full=full)
    return _gemini_call_with_retry(
        lambda: client.models.generate_content(model=GEMINI_MODEL, contents=contents),
        label=f"visual{'-full' if full else ''}({video_url})",
    )


def _looks_like_build_video(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in BUILD_TITLE_KEYWORDS)


def _enrich_attachments(text_builds: list[dict], video_url: str,
                        duration_s: int, client) -> list[dict]:
    """If text-extracted builds have empty attachments, scan the FULL video
    to find them. The gunsmith / loadout screen can appear anywhere in the
    video — not just the intro or outro — so we can't rely on head+tail
    clips here. We send the entire video and merge whatever attachments
    Gemini reads off-screen back onto the matching weapons."""
    needs = [b for b in text_builds if not (b.get("attachments") or [])]
    if not needs:
        return text_builds

    missing_names = ", ".join(b.get("weapon_name", "?") for b in needs[:6])
    print(f"[yt-gem]   {len(needs)} build(s) missing attachments [{missing_names}] — scanning FULL video")
    time.sleep(1)
    visual_raw = _gemini_visual_call(video_url, duration_s, client, full=True)
    if not visual_raw:
        print(f"[yt-gem]   full-video scan returned nothing")
        return text_builds

    # Map normalized weapon name → attachments seen in the full-video scan
    by_weapon: dict[str, list[str]] = {}
    for vb in visual_raw:
        name = _normalize_weapon_name(vb.get("weapon_name", ""))
        atts = vb.get("attachments") or []
        if name and atts:
            by_weapon[name] = atts

    filled = 0
    for b in text_builds:
        if b.get("attachments"):
            continue
        canonical = _normalize_weapon_name(b.get("weapon_name", ""))
        if canonical and canonical in by_weapon:
            b["attachments"] = by_weapon[canonical]
            filled += 1
    print(f"[yt-gem]   full-video scan filled attachments for {filled}/{len(needs)} build(s)")

    return text_builds


def _extract_for_video(video_url: str, video_id: str, title: str,
                       meta: dict, client) -> tuple[list[dict], str]:
    """Text-first; both visual paths gated behind opt-in env flags so the
    free-tier Gemini quota isn't burnt on long videos."""
    description = meta.get("description", "") if meta else ""
    duration_s = meta.get("duration_s", 0) if meta else 0
    transcript = _fetch_transcript(video_id)

    prompt = _build_text_prompt(title, description, transcript)
    raw = _gemini_text_call(prompt, client)
    if raw:
        if ENABLE_VISUAL_ENRICH:
            raw = _enrich_attachments(raw, video_url, duration_s, client)
            label = "text+enrich" if any(b.get("attachments") for b in raw) else "text"
        else:
            label = "text"
        return raw, label

    if ENABLE_VISUAL_FALLBACK and _looks_like_build_video(title):
        time.sleep(2)
        raw = _gemini_visual_call(video_url, duration_s, client)
        if raw:
            return raw, "visual"
        return [], "visual-empty"

    return [], "text-empty"


# ──────────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────────

def scrape(lookback_days: int = DEFAULT_LOOKBACK_DAYS,
           output_list: list[dict] | None = None) -> list[dict]:
    """Channel sweep. If `output_list` is provided, every validated build is
    appended to it as soon as it's extracted — so even if this function gets
    killed by the pipeline's hard-timeout, partial results are preserved
    inside the caller's list."""
    global _quota_dead, _consecutive_429
    _quota_dead = False
    _consecutive_429 = 0

    yt_key = os.environ.get("YOUTUBE_API_KEY")
    gem_key = os.environ.get("GEMINI_API_KEY")
    if not yt_key:
        print("[yt-gem] YOUTUBE_API_KEY not set, skipping")
        return []
    if not gem_key:
        print("[yt-gem] GEMINI_API_KEY not set, skipping")
        return []

    try:
        from google import genai
        from google.genai import types as gtypes
        print("[yt-gem] google-genai package loaded OK")
    except ImportError as e:
        print(f"[yt-gem] google-genai package missing ({e}), skipping")
        return []

    try:
        gemini = genai.Client(
            api_key=gem_key,
            http_options=gtypes.HttpOptions(timeout=120_000),
        )
    except Exception as e:
        print(f"[yt-gem] failed to construct Gemini client: {e}")
        return []

    _ensure_weapon_cache()
    n_unique = len(set(_VALID_WEAPONS_CACHE.values()))  # type: ignore[union-attr]
    print(f"[yt-gem] whitelist: {n_unique} canonical weapons")
    if n_unique == 0:
        print("[yt-gem] empty whitelist — every extraction would be dropped, abort")
        return []

    youtube = ytbuild("youtube", "v3", developerKey=yt_key, cache_discovery=False)
    after = _published_after(lookback_days)

    final: list[dict] = []

    try:
        for channel in CHANNELS:
            if _quota_dead:
                print(f"[yt-gem] skipping {channel['name']} — quota dead")
                continue

            ch_id = _resolve_channel_id(youtube, channel)
            if not ch_id:
                continue

            videos = _list_recent_videos(youtube, ch_id, after)
            videos.sort(key=lambda v: v["publishedAt"], reverse=True)
            videos = videos[:MAX_VIDEOS_PER_CHANNEL]
            print(f"[yt-gem] {channel['name']}: {len(videos)} videos in last {lookback_days}d")

            metas = _fetch_metadata(youtube, [v["videoId"] for v in videos])

            # Per-channel dedupe by canonical weapon name (newest video wins)
            seen: dict[str, dict] = {}

            for v in videos:
                if _quota_dead:
                    break
                url = f"https://youtube.com/watch?v={v['videoId']}"
                meta = metas.get(v["videoId"], {})
                try:
                    raw, method = _extract_for_video(url, v["videoId"], v["title"], meta, gemini)
                except QuotaExhausted:
                    print(f"[yt-gem] {channel['name']}: quota dead mid-video, aborting channel")
                    break
                time.sleep(SLEEP_BETWEEN_CALLS_S)

                valid_builds: list[dict] = []
                for b in raw:
                    vb = _validate_build(b)
                    if vb:
                        valid_builds.append(vb)

                names = ", ".join(b["weapon_name"] for b in valid_builds[:5])
                print(f"[yt-gem]   {url} via {method}: {len(valid_builds)} valid / {len(raw)} raw [{names}]")

                for vb in valid_builds:
                    key = vb["weapon_name"].lower()
                    if key in seen:
                        continue
                    enriched = {
                        **vb,
                        "game": "Warzone",
                        "play_style": channel["play_style"],
                        "source_type": "youtube",
                        "source_url": url,
                        "source_title": f"{channel['name']} — {v['title'][:80]}",
                        "published_at": v["publishedAt"],
                        "title": v["title"],
                        "text": "",
                        "upvotes": 0,
                    }
                    seen[key] = enriched
                    # Incremental write so a later timeout can't lose this build.
                    if output_list is not None:
                        output_list.append(enriched)

            final.extend(seen.values())
            print(f"[yt-gem] {channel['name']}: {len(seen)} unique builds")
    except QuotaExhausted:
        print(f"[yt-gem] outer abort — quota dead, returning {len(final)} partial builds")

    print(f"[yt-gem] total builds across all channels: {len(final)} (output_list={len(output_list) if output_list is not None else '∅'})")
    return final
