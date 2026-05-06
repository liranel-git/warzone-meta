"""
Generic website scraper that uses Gemini's URL-context tool to fetch a
JS-rendered meta page and extract structured weapon builds. Used for
codmunity.gg, wzstats.gg, etc. — sites that don't return useful HTML
via plain HTTP.
"""

import json
import os
import re

GEMINI_MODEL = "gemini-2.5-flash"

PROMPT = """Visit the URL provided and extract every weapon build the page presents as part of the current Warzone meta tier list.

Return strict JSON: {"builds": [...]}. Each build object must have:
- weapon_name (string)
- weapon_class (one of: AR, SMG, LMG, Sniper, Shotgun, Marksman, Pistol)
- tier (one of: "Absolute Meta", "Meta", "A", "B", "F" — match the website's tier label as closely as possible: S/Meta → "Absolute Meta", A → "Meta", B → "A", C/D → "B", F → "F")
- weapon_dominancy (string: Long Range, Close Range, Sniper, Support, Hip Fire, Aggressive, or Lowest Recoil)
- attachments (array of "<Slot>: <Name>" strings — at minimum: Optic / Muzzle / Barrel / Magazine / Stock when shown)
- confidence (float 0.5-0.95 reflecting how clearly the build is presented)
- reasoning (one short sentence)

If the page does not show explicit builds, return {"builds": []}. URL: """


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


def scrape_site(url: str, play_style: str, source_title: str) -> list[dict]:
    gem_key = os.environ.get("GEMINI_API_KEY")
    if not gem_key:
        print(f"[gem-site] GEMINI_API_KEY not set, skipping {url}")
        return []

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("[gem-site] google-genai package missing, skipping")
        return []

    client = genai.Client(api_key=gem_key)

    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=PROMPT + url,
            config=types.GenerateContentConfig(
                tools=[types.Tool(url_context=types.UrlContext())],
            ),
        )
        text = resp.text or ""
    except Exception as e:
        print(f"[gem-site] gemini call failed for {url}: {e}")
        return []

    parsed = _extract_json(text)
    raw_builds = parsed.get("builds", [])
    if not isinstance(raw_builds, list):
        return []

    out = []
    for b in raw_builds:
        wname = (b.get("weapon_name") or "").strip()
        if not wname:
            continue
        wclass = (b.get("weapon_class") or "AR").strip()
        tier = b.get("tier") or "A"
        if tier not in ("Absolute Meta", "Meta", "A", "B", "F"):
            tier = "A"

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
            "source_url": url,
            "source_title": source_title,
            "published_at": None,
            "title": f"{wname} — {source_title}",
            "text": "",
            "upvotes": 0,
        })

    print(f"[gem-site] {source_title}: {len(out)} builds extracted")
    return out


# ──────────────────────────────────────────────────────────────────────────
# Site-specific entry points
# ──────────────────────────────────────────────────────────────────────────

def scrape_codmunity() -> list[dict]:
    return scrape_site(
        "https://codmunity.gg/loadouts",
        play_style="Codmunity",
        source_title="codmunity.gg",
    )


def scrape_wzstats() -> list[dict]:
    return scrape_site(
        "https://wzstats.gg/warzone/meta",
        play_style="WZ Meta",
        source_title="wzstats.gg",
    )
