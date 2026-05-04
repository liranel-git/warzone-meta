"""
Scrapes r/CODWarzone and r/CODLoadouts for weapon build posts.
Uses Reddit's public JSON API — no auth required.
"""

import requests
import time
import random

HEADERS = {"User-Agent": "WarzoneMetaBot/1.0 (personal project)"}

# Stick to the two most active subs — fewer requests, less rate limiting
SUBREDDITS = ["CODWarzone", "CODLoadouts"]

# Trimmed to 4 queries — each one costs an API call per subreddit
SEARCH_QUERIES = [
    "best loadout BO7",
    "meta weapon Black Ops 7",
    "broken gun WZBO7",
    "overpowered loadout Black Ops 7",
]

BASE_DELAY = 2.0   # seconds between every request
MAX_RETRIES = 3


def _get(url: str) -> dict | None:
    """GET with exponential backoff on 429."""
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 429:
                wait = BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)
                print(f"[reddit] 429 rate limit — waiting {wait:.1f}s before retry {attempt + 1}/{MAX_RETRIES}")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            if attempt == MAX_RETRIES - 1:
                print(f"[reddit] GET failed {url}: {e}")
            continue
        except Exception as e:
            print(f"[reddit] GET failed {url}: {e}")
            return None
    return None


def _sleep():
    """Polite delay between requests with slight jitter."""
    time.sleep(BASE_DELAY + random.uniform(0, 0.5))


def _extract_post(post: dict) -> dict | None:
    data = post.get("data", {})
    title = data.get("title", "")
    text = data.get("selftext", "")
    score = data.get("score", 0)
    url = f"https://reddit.com{data.get('permalink', '')}"
    post_id = data.get("id", "")

    if score < 10:
        return None

    return {
        "title": title,
        "text": (text[:2000] if text else ""),
        "source_type": "reddit",
        "source_url": url,
        "upvotes": score,
        "post_id": post_id,
    }


def _fetch_top_comments(post_id: str, subreddit: str) -> str:
    _sleep()
    url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json?limit=10&depth=1"
    data = _get(url)
    if not data or len(data) < 2:
        return ""
    comments = []
    for child in data[1]["data"]["children"][:10]:
        body = child["data"].get("body", "")
        if body and body != "[deleted]":
            comments.append(body[:500])
    return "\n---\n".join(comments)


def scrape() -> list[dict]:
    items = []
    seen_ids = set()

    for sub in SUBREDDITS:
        # Top posts this week
        _sleep()
        data = _get(f"https://www.reddit.com/r/{sub}/top.json?t=week&limit=25")
        if data:
            for post in data["data"]["children"]:
                item = _extract_post(post)
                if item and item["post_id"] not in seen_ids:
                    seen_ids.add(item["post_id"])
                    comments = _fetch_top_comments(item["post_id"], sub)
                    item["text"] = item["text"] + ("\n\nTop comments:\n" + comments if comments else "")
                    items.append(item)

        # Keyword searches
        for query in SEARCH_QUERIES:
            _sleep()
            url = (
                f"https://www.reddit.com/r/{sub}/search.json"
                f"?q={requests.utils.quote(query)}&sort=top&t=week&limit=10&restrict_sr=1"
            )
            data = _get(url)
            if data:
                for post in data["data"]["children"]:
                    item = _extract_post(post)
                    if item and item["post_id"] not in seen_ids:
                        seen_ids.add(item["post_id"])
                        items.append(item)

    print(f"[reddit] scraped {len(items)} posts")
    return items
