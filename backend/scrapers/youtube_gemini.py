"""
Channel-based scraper: pulls videos + Shorts from each curated creator,
passes the URL to Gemini for visual extraction of weapon builds, and
groups results by play style (one play style per channel).

Per channel dedupe: if the same weapon shows up in multiple recent
videos/shorts, the most recent build wins.
"""

import os
import json
import re
import time
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build as ytbuild

# Channel → play style mapping. Uses the same channel IDs/handles that the
# legacy youtube.py scraper already validated.
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

EXTRACTION_PROMPT = """You are analysing a Call of Duty: Warzone meta build video. Extract every distinct weapon build that the creator showcases or recommends.

For each build, return strict JSON with these fields:
- weapon_name (string, exact in-game name)
- weapon_class (one of: AR, SMG, LMG, Sniper, Shotgun, Marksman, Pistol)
- tier (one of: "Absolute Meta", "Meta", "A", "B", "F" — infer from creator commentary; "this is the best" / "S-tier" → Absolute Meta; "very good / top pick" → Meta; "solid" → A; "okay / outdated" → B; "skip / bad" → F)
- weapon_dominancy (one of: "Long Range", "Close Range", "Sniper", "Support", "Hip Fire", "Aggressive", "Lowest Recoil")
- attachments (array of strings, format "<Slot>: <Name>" — e.g. "Optic: Slate Reflector")
- confidence (float 0.0-1.0; how clearly the creator presents this build)
- reasoning (one short sentence on why)

Return ONLY a JSON object: {"builds": [...]}.
If no clear builds are shown (e.g. the video is gameplay only, news, or reaction), return {"builds": []}."""


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
    """Returns list of {videoId, title, publishedAt} for videos AND shorts."""
    out = []
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


# ──────────────────────────────────────────────────────────────────────────
# Gemini extraction
# ──────────────────────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of Gemini's response."""
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    # Find first {...} block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {"builds": []}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"builds": []}


def _gemini_extract(video_url: str, client) -> list[dict]:
    """Send a YouTube URL to Gemini and return its parsed builds list."""
    try:
        from google.genai import types
        contents = types.Content(parts=[
            types.Part(file_data=types.FileData(file_uri=video_url)),
            types.Part(text=EXTRACTION_PROMPT),
        ])
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=contents)
        text = (resp.text or "").strip()
        if not text:
            print(f"[yt-gem] empty response for {video_url}")
            return []
    except Exception as e:
        print(f"[yt-gem] gemini call failed for {video_url}: {type(e).__name__}: {e}")
        return []

    parsed = _extract_json(text)
    builds = parsed.get("builds", [])
    if not isinstance(builds, list):
        return []
    print(f"[yt-gem]   {video_url}: {len(builds)} builds")
    return builds


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
        print(f"[yt-gem] google-genai package loaded OK")
    except ImportError as e:
        print(f"[yt-gem] google-genai package missing ({e}), skipping")
        return []

    try:
        from google.genai import types as gtypes
        gemini = genai.Client(
            api_key=gem_key,
            http_options=gtypes.HttpOptions(timeout=120_000),  # 2 min per video
        )
    except Exception as e:
        print(f"[yt-gem] failed to construct Gemini client: {e}")
        return []

    youtube = ytbuild("youtube", "v3", developerKey=yt_key, cache_discovery=False)
    after = _published_after(lookback_days)

    final: list[dict] = []

    for channel in CHANNELS:
        ch_id = _resolve_channel_id(youtube, channel)
        if not ch_id:
            continue

        videos = _list_recent_videos(youtube, ch_id, after)
        # newest first
        videos.sort(key=lambda v: v["publishedAt"], reverse=True)
        print(f"[yt-gem] {channel['name']}: {len(videos)} videos in last {lookback_days}d")

        # Per-channel dedupe: weapon_name → first build seen (newest wins because list is sorted)
        seen: dict[str, dict] = {}

        for v in videos:
            url = f"https://youtube.com/watch?v={v['videoId']}"
            builds = _gemini_extract(url, gemini)
            time.sleep(0.5)  # gentle rate limit

            for b in builds:
                wname = (b.get("weapon_name") or "").strip()
                if not wname:
                    continue
                key = wname.lower()
                if key in seen:
                    continue  # already have a more recent build for this weapon

                wclass = (b.get("weapon_class") or "").strip() or "AR"
                tier = b.get("tier") or "A"
                if tier not in ("Absolute Meta", "Meta", "A", "B", "F"):
                    tier = "A"

                seen[key] = {
                    "weapon_name": wname,
                    "weapon_class": wclass,
                    "game": "Warzone",
                    "play_style": channel["play_style"],
                    "weapon_dominancy": b.get("weapon_dominancy"),
                    "tier": tier,
                    "attachments": b.get("attachments") or [],
                    "confidence": float(b.get("confidence") or 0.7),
                    "reasoning": b.get("reasoning") or "",
                    "source_type": "youtube",
                    "source_url": url,
                    "source_title": f"{channel['name']} — {v['title'][:80]}",
                    "published_at": v["publishedAt"],
                    "title": v["title"],
                    "text": "",
                    "upvotes": 0,
                }

        final.extend(seen.values())
        print(f"[yt-gem] {channel['name']}: {len(seen)} unique builds extracted")

    print(f"[yt-gem] total builds across all channels: {len(final)}")
    return final
