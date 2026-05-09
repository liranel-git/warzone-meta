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

# Pacing — text calls cost ~5–15K tokens each (vs 50–150K for video),
# so we can do significantly more per minute.
SLEEP_BETWEEN_CALLS_S = 4.0
MAX_VIDEOS_PER_CHANNEL = 10

# Visual fallback clip lengths (only used when text returned nothing)
HEAD_S = 90
TAIL_S = 90
MIN_GAP_S = 30

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
    for att in raw_atts:
        if not isinstance(att, str) or ":" not in att:
            continue
        slot, name = att.split(":", 1)
        slot = slot.strip()
        name = name.strip()
        if slot in VALID_SLOTS and name:
            clean_atts.append(f"{slot}: {name}")

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

Below is the creator's title, full description, and (if available) auto-captions transcript. Extract every weapon build the creator EXPLICITLY recommends as a CURRENT-meta loadout.

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
- attachments: array of "<Slot>: <Name>" — ONLY for attachments the creator EXPLICITLY mentions by name. Skip slots they don't specify.
    Slot must be one of: Optic, Muzzle, Barrel, Underbarrel, Magazine, Stock, Rear Grip, Laser, Fire Mods, Conversion Kit, Bolt, Comb, Stock Pad, Ammunition, Trigger Action.
    DO NOT GUESS attachments. If the creator doesn't say it, leave it out.
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
    """Generic retry wrapper for Gemini calls. make_request_fn() returns the response."""
    for attempt in range(max_retries + 1):
        try:
            resp = make_request_fn()
            text = (resp.text or "").strip()
            if not text:
                return []
            parsed = _extract_json(text)
            builds = parsed.get("builds", [])
            return builds if isinstance(builds, list) else []
        except Exception as e:
            err = str(e)
            permission = "403" in err or "PERMISSION_DENIED" in err
            if permission:
                print(f"[yt-gem] {label}: 403 (skipping)")
                return []
            transient = ("429" in err or "RESOURCE_EXHAUSTED" in err
                         or "503" in err or "UNAVAILABLE" in err)
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
    return _gemini_call_with_retry(
        lambda: client.models.generate_content(model=GEMINI_MODEL, contents=prompt),
        label="text",
    )


def _build_visual_content(video_url: str, duration_s: int):
    from google.genai import types
    parts = []
    if not duration_s or duration_s <= HEAD_S + MIN_GAP_S:
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


def _gemini_visual_call(video_url: str, duration_s: int, client) -> list[dict]:
    contents = _build_visual_content(video_url, duration_s)
    return _gemini_call_with_retry(
        lambda: client.models.generate_content(model=GEMINI_MODEL, contents=contents),
        label=f"visual({video_url})",
    )


def _looks_like_build_video(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in BUILD_TITLE_KEYWORDS)


def _enrich_attachments(text_builds: list[dict], video_url: str,
                        duration_s: int, client) -> list[dict]:
    """If text-extracted builds have empty attachments, run a visual call to
    fill them in. Visual extraction can read attachment slot/name pairs off
    the loadout screen even when the creator doesn't say them verbally."""
    needs = [b for b in text_builds if not (b.get("attachments") or [])]
    if not needs or duration_s <= 0:
        return text_builds

    print(f"[yt-gem]   enriching {len(needs)} build(s) with empty attachments via visual")
    time.sleep(2)
    visual_raw = _gemini_visual_call(video_url, duration_s, client)
    if not visual_raw:
        return text_builds

    # Map normalized weapon name → attachments seen in visual
    by_weapon: dict[str, list[str]] = {}
    for vb in visual_raw:
        name = _normalize_weapon_name(vb.get("weapon_name", ""))
        atts = vb.get("attachments") or []
        if name and atts:
            by_weapon[name] = atts

    for b in text_builds:
        if b.get("attachments"):
            continue
        canonical = _normalize_weapon_name(b.get("weapon_name", ""))
        if canonical and canonical in by_weapon:
            b["attachments"] = by_weapon[canonical]

    return text_builds


def _extract_for_video(video_url: str, video_id: str, title: str,
                       meta: dict, client) -> tuple[list[dict], str]:
    """Try text first. Enrich missing attachments visually. Fall back to
    visual-only when text returned nothing AND title suggests builds."""
    description = meta.get("description", "") if meta else ""
    duration_s = meta.get("duration_s", 0) if meta else 0
    transcript = _fetch_transcript(video_id)

    prompt = _build_text_prompt(title, description, transcript)
    raw = _gemini_text_call(prompt, client)
    if raw:
        raw = _enrich_attachments(raw, video_url, duration_s, client)
        return raw, "text+enrich" if any(b.get("attachments") for b in raw) else "text"

    if _looks_like_build_video(title):
        time.sleep(2)
        raw = _gemini_visual_call(video_url, duration_s, client)
        if raw:
            return raw, "visual"
        return [], "visual-empty"

    return [], "text-empty"


# ──────────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────────

def scrape(lookback_days: int = DEFAULT_LOOKBACK_DAYS) -> list[dict]:
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

    for channel in CHANNELS:
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
            url = f"https://youtube.com/watch?v={v['videoId']}"
            meta = metas.get(v["videoId"], {})
            raw, method = _extract_for_video(url, v["videoId"], v["title"], meta, gemini)
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
                seen[key] = {
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

        final.extend(seen.values())
        print(f"[yt-gem] {channel['name']}: {len(seen)} unique builds")

    print(f"[yt-gem] total builds across all channels: {len(final)}")
    return final
