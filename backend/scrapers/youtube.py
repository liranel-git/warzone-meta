"""
Fetches recent videos from a curated list of trusted WZBO7 content creators.
Uses channel IDs (or resolves handles to IDs) so we only get content from
these specific creators rather than doing keyword searches.
Transcripts are skipped — YouTube blocks bulk transcript requests from home IPs.
Title + description from the Data API is sufficient for Claude to classify builds.
"""

import os
from datetime import datetime, timedelta
from googleapiclient.discovery import build

CHANNELS = [
    {"name": "Camy",       "id": "UC6MKLs52vIfPXWyatOQDXmw"},
    {"name": "Lion",       "id": "UCnsRRitecBw8Vkx3ix1Ualw"},
    {"name": "Ryda",       "handle": "Ryda"},
    {"name": "eyeqew",     "id": "UCSF0PqIaps7jindnj6ICTfQ"},
    {"name": "stract",     "id": "UCbTCJUYDKatfSB_EYBnEghg"},
    {"name": "Cpreds",     "handle": "cpreds"},
    {"name": "Swagg",      "id": "UCW1CGYCjfKhNLGp_Os1g_Pg"},
    {"name": "MrMarvelTV", "id": "UCqBaw9Ze5EJ4fJVbaXbhnmw"},
]

MAX_VIDEOS_PER_CHANNEL = 10


def _published_after() -> str:
    cutoff = datetime.utcnow() - timedelta(days=90)
    return cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_channel_id(youtube, channel: dict) -> str | None:
    if "id" in channel:
        return channel["id"]
    try:
        resp = youtube.channels().list(part="id", forHandle=channel["handle"]).execute()
        items = resp.get("items", [])
        if items:
            return items[0]["id"]
        print(f"[youtube] could not resolve handle @{channel['handle']}")
        return None
    except Exception as e:
        print(f"[youtube] handle resolution failed for @{channel['handle']}: {e}")
        return None


def scrape() -> list[dict]:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("[youtube] YOUTUBE_API_KEY not set, skipping")
        return []

    youtube = build("youtube", "v3", developerKey=api_key, cache_discovery=False)
    items = []
    seen_ids = set()

    for channel in CHANNELS:
        channel_id = _resolve_channel_id(youtube, channel)
        if not channel_id:
            continue

        try:
            response = (
                youtube.search()
                .list(
                    channelId=channel_id,
                    part="snippet",
                    type="video",
                    order="date",
                    publishedAfter=_published_after(),
                    maxResults=MAX_VIDEOS_PER_CHANNEL,
                    relevanceLanguage="en",
                )
                .execute()
            )
        except Exception as e:
            print(f"[youtube] search failed for {channel['name']}: {e}")
            continue

        for result in response.get("items", []):
            video_id = result["id"]["videoId"]
            if video_id in seen_ids:
                continue
            seen_ids.add(video_id)

            snippet = result["snippet"]
            title = snippet.get("title", "")
            description = snippet.get("description", "")[:1500]

            items.append({
                "title": title,
                "text": (
                    f"Creator: {channel['name']}\n"
                    f"Title: {title}\n\n"
                    f"Description:\n{description}"
                ),
                "source_type": "youtube",
                "source_url": f"https://youtube.com/watch?v={video_id}",
                "upvotes": 0,
            })

        print(f"[youtube] {channel['name']}: {len(response.get('items', []))} videos")

    print(f"[youtube] total: {len(items)} videos across {len(CHANNELS)} channels")
    return items
