"""
Fetches recent videos from a curated list of trusted WZBO7 content creators.
Uses channel IDs (or resolves handles to IDs) so we only get content from
these specific creators rather than doing keyword searches.
Transcripts are skipped — YouTube blocks bulk transcript requests from home IPs.
Full video descriptions are fetched via videos.list so Claude gets the complete
build info that creators typically put at the start or end of descriptions.
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
    {"name": "Swagg",      "id": "UCW1CGYCjfKhNLGp_Os1g_Mg"},
    {"name": "MrMarvelTV", "id": "UCqBaw9Ze5EJ4fJVbaXbhnmw"},
]

LOOKBACK_DAYS = 7


def _published_after() -> str:
    cutoff = datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)
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


def _fetch_all_video_ids(youtube, channel_id: str, channel_name: str) -> list[tuple[str, str]]:
    """Return list of (video_id, title) for all videos in the lookback window."""
    results = []
    page_token = None
    published_after = _published_after()

    while True:
        try:
            kwargs = dict(
                channelId=channel_id,
                part="snippet",
                type="video",
                order="date",
                publishedAfter=published_after,
                maxResults=50,
                relevanceLanguage="en",
            )
            if page_token:
                kwargs["pageToken"] = page_token

            response = youtube.search().list(**kwargs).execute()
        except Exception as e:
            print(f"[youtube] search failed for {channel_name}: {e}")
            break

        for item in response.get("items", []):
            video_id = item["id"]["videoId"]
            title = item["snippet"].get("title", "")
            results.append((video_id, title))

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return results


def _fetch_full_descriptions(youtube, video_ids: list[str]) -> dict[str, str]:
    """Batch-fetch full descriptions for up to 50 video IDs at a time."""
    descriptions = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        try:
            resp = youtube.videos().list(
                part="snippet",
                id=",".join(batch),
            ).execute()
            for item in resp.get("items", []):
                vid = item["id"]
                descriptions[vid] = item["snippet"].get("description", "")
        except Exception as e:
            print(f"[youtube] videos.list failed: {e}")
    return descriptions


def scrape() -> list[dict]:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("[youtube] YOUTUBE_API_KEY not set, skipping")
        return []

    youtube = build("youtube", "v3", developerKey=api_key, cache_discovery=False)

    # Step 1: collect all video IDs across channels
    channel_videos: list[tuple[str, str, str]] = []  # (video_id, title, channel_name)
    seen_ids: set[str] = set()

    for channel in CHANNELS:
        channel_id = _resolve_channel_id(youtube, channel)
        if not channel_id:
            continue

        pairs = _fetch_all_video_ids(youtube, channel_id, channel["name"])
        new = [(vid, title, channel["name"]) for vid, title in pairs if vid not in seen_ids]
        for vid, title, _ in new:
            seen_ids.add(vid)
        channel_videos.extend(new)
        print(f"[youtube] {channel['name']}: {len(new)} videos in last {LOOKBACK_DAYS} days")

    if not channel_videos:
        print("[youtube] no videos found")
        return []

    # Step 2: fetch full descriptions in batches
    all_ids = [vid for vid, _, _ in channel_videos]
    descriptions = _fetch_full_descriptions(youtube, all_ids)

    # Step 3: assemble items
    items = []
    for video_id, title, channel_name in channel_videos:
        full_desc = descriptions.get(video_id, "")
        items.append({
            "title": title,
            "text": (
                f"Creator: {channel_name}\n"
                f"Title: {title}\n\n"
                f"Description:\n{full_desc}"
            ),
            "source_type": "youtube",
            "source_url": f"https://youtube.com/watch?v={video_id}",
            "source_title": title,
            "upvotes": 0,
        })

    print(f"[youtube] total: {len(items)} videos across {len(CHANNELS)} channels")
    return items
