"""
Site scrapers using Gemini's GOOGLE-SEARCH grounding tool.

The earlier url_context approach failed for codmunity.gg / wzstats.gg
because both are JS-rendered — Gemini fetched the HTML but couldn't
parse the live tier list. The Google Search grounding tool sidesteps
that: Gemini queries Google, finds the indexed content, and synthesises
a structured answer. Verified manually in Google AI Studio.

Codmunity output is also persisted to a JSON cache file so the YouTube
extractor can use it as the canonical weapon whitelist.
"""

import json
import os
import re

GEMINI_MODEL = "gemini-2.5-flash"


# ──────────────────────────────────────────────────────────────────────────
# Whitelist cache (codmunity weapons → JSON file for youtube_gemini)
# ──────────────────────────────────────────────────────────────────────────

def _whitelist_path() -> str:
    data_dir = os.environ.get("DB_DIR")
    if not data_dir:
        data_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(data_dir, "codmunity_whitelist.json")


def _save_codmunity_whitelist(builds: list[dict]) -> None:
    weapons: dict[str, str] = {}
    for b in builds:
        name = (b.get("weapon_name") or "").strip()
        cls = (b.get("weapon_class") or "").strip()
        if name:
            weapons[name] = cls or "AR"
    if not weapons:
        return
    path = _whitelist_path()
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"weapons": weapons}, f, indent=2)
        print(f"[gem-site] saved codmunity whitelist: {len(weapons)} weapons → {path}")
    except Exception as e:
        print(f"[gem-site] failed to save whitelist: {e}")


# ──────────────────────────────────────────────────────────────────────────
# JSON extraction
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


def _build_search_prompt(site_label: str, site_domain: str) -> str:
    return f"""You are extracting the TOP of the current Call of Duty: Warzone meta tier list from {site_label} ({site_domain}).

Today is May 2026 — Warzone is in the BO7 (Black Ops 7) era, Season 3.

Use Google Search to look up {site_label}'s Warzone tier list. Search terms like "{site_domain} Warzone meta tier list", "{site_domain} best ARs", "{site_domain} best SMGs", "{site_domain} sniper tier list" — issue MULTIPLE search queries if needed to cover every weapon class.

**ONLY extract weapons in the top THREE tiers — "Absolute Meta", "Meta", and "A". OMIT everything the site rates lower (B, C, D, F, "not recommended", etc.) entirely. We only want the genuinely competitive picks.**

For each qualifying weapon, return strict JSON: {{"builds": [...]}} with these fields:
- weapon_name (string, exact in-game name, e.g. "MK.78", "Voyak KT-3", "VST", "Strider 300", "Razor 9mm", "Dravec 45")
- weapon_class (AR, SMG, LMG, Sniper, Shotgun, Marksman, Pistol)
- tier — map the site's label, but ONLY these three:
    S / Tier 1 / Meta / Top → "Absolute Meta"
    A / Tier 2 / Strong → "Meta"
    B / Tier 3 / Solid → "A"
    (anything the site rates C / D / F / lower → DO NOT INCLUDE the weapon at all)
- weapon_dominancy (Long Range, Close Range, Sniper, Support, Hip Fire, Aggressive, Lowest Recoil)
- attachments — array of "<Slot>: <Name>" pairs using EXACT in-game names with brand prefixes (e.g. "Greaves Bellum Barrel", "Bowen Bighorn Drum", "Monolithic Suppressor"). DO NOT use generic terms like "18-inch barrel", "45 round mag", "FMJ ammunition" — those are placeholders and will be dropped. If you don't know the exact in-game name for a slot, OMIT that slot.
    Valid slots: Optic, Muzzle, Barrel, Underbarrel, Magazine, Stock, Rear Grip, Laser, Fire Mods, Conversion Kit, Bolt, Comb, Stock Pad, Ammunition, Trigger Action.
- confidence (0.5–0.95)
- reasoning (one short sentence — why the site recommends this build)

Target every weapon the site puts in its top three tiers, across every weapon class — typically 15–25 weapons.

Return ONLY: {{"builds": [...]}}. No prose."""


# ──────────────────────────────────────────────────────────────────────────
# Generic scraper
# ──────────────────────────────────────────────────────────────────────────

def _scrape_via_search(site_label: str, site_domain: str, play_style: str,
                       source_title: str, source_url: str) -> list[dict]:
    gem_key = os.environ.get("GEMINI_API_KEY")
    if not gem_key:
        print(f"[gem-site] GEMINI_API_KEY not set, skipping {site_label}")
        return []

    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        print(f"[gem-site] google-genai package missing ({e}), skipping {site_label}")
        return []

    try:
        client = genai.Client(
            api_key=gem_key,
            http_options=types.HttpOptions(timeout=90_000),
        )
    except Exception as e:
        print(f"[gem-site] failed to construct client for {site_label}: {e}")
        return []

    prompt = _build_search_prompt(site_label, site_domain)
    print(f"[gem-site] searching {site_label} via Google grounding …")

    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        text = (resp.text or "").strip()
        if not text:
            print(f"[gem-site] empty response for {site_label}")
            return []
    except Exception as e:
        print(f"[gem-site] gemini call failed for {site_label}: {type(e).__name__}: {str(e)[:200]}")
        return []

    parsed = _extract_json(text)
    raw_builds = parsed.get("builds", [])
    if not isinstance(raw_builds, list):
        return []

    # Website sources only carry the top three tiers — drop anything else
    # that slips through despite the prompt.
    ALLOWED_TIERS = ("Absolute Meta", "Meta", "A")

    out = []
    dropped_low_tier = 0
    for b in raw_builds:
        wname = (b.get("weapon_name") or "").strip()
        if not wname:
            continue
        wclass = (b.get("weapon_class") or "AR").strip()
        tier = b.get("tier") or "A"
        if tier not in ALLOWED_TIERS:
            dropped_low_tier += 1
            continue  # B / F / unknown — omit for website sources

        out.append({
            "weapon_name": wname,
            "weapon_class": wclass,
            "game": "Warzone",
            "play_style": play_style,
            "weapon_dominancy": b.get("weapon_dominancy"),
            "tier": tier,
            "attachments": b.get("attachments") or [],
            "confidence": float(b.get("confidence") or 0.7),
            "reasoning": b.get("reasoning") or "",
            "source_type": "website",
            "source_url": source_url,
            "source_title": source_title,
            "published_at": None,
            "title": f"{wname} — {source_title}",
            "text": "",
            "upvotes": 0,
        })

    names = ", ".join(b["weapon_name"] for b in out[:5])
    suffix = f" (dropped {dropped_low_tier} below-A-tier)" if dropped_low_tier else ""
    print(f"[gem-site] {site_label}: {len(out)} builds extracted{suffix} [{names}{'...' if len(out) > 5 else ''}]")
    return out


# ──────────────────────────────────────────────────────────────────────────
# Site-specific entry points
# ──────────────────────────────────────────────────────────────────────────

def scrape_codmunity() -> list[dict]:
    builds = _scrape_via_search(
        site_label="CODMunity",
        site_domain="codmunity.gg",
        play_style="Codmunity",
        source_title="codmunity.gg",
        source_url="https://codmunity.gg/",
    )
    if builds:
        _save_codmunity_whitelist(builds)
    return builds


def scrape_wzstats() -> list[dict]:
    return _scrape_via_search(
        site_label="WZStats",
        site_domain="wzstats.gg",
        play_style="WZ Meta",
        source_title="wzstats.gg",
        source_url="https://wzstats.gg/",
    )
