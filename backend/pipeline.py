"""
Orchestrates scraping → database upsert.

Two modes:
  - run_weekly(): 7-day lookback for YouTube, full website refresh
  - run_daily():  1-day lookback for YouTube, full website refresh

Per-play-style wipe before upsert: when a scraper returns fresh data for
a play_style bucket, we DELETE the bucket first so stale rows from older
runs don't linger. Buckets that didn't get fresh data this run are left
untouched.
"""

import os
import sys
import time
import concurrent.futures
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from database import init_db, upsert_build, log_scrape, delete_builds_by_play_style
from scrapers.wzhub import scrape as scrape_wzhub
from scrapers.youtube_gemini import scrape as scrape_youtube_gemini, CHANNELS as YT_CHANNELS
from scrapers.gemini_site import scrape_codmunity, scrape_wzstats

# Codmunity + WZ Stats URL-context calls were eating tokens (their homepage
# HTML counts as input tokens via the url_context tool) without returning
# data. Gated off by default; flip ENABLE_GEMINI_SITES=1 once we find URLs
# Gemini can actually parse.
ENABLE_GEMINI_SITES = os.environ.get("ENABLE_GEMINI_SITES", "0") == "1"

# All play-style buckets we manage. Wiped before every run so stale rows
# (hallucinated weapons from pre-whitelist runs, channels that went silent,
# etc.) don't linger in the UI.
KNOWN_PLAY_STYLES: list[str] = ["WZ Hub", "Codmunity", "WZ Meta"] + [
    ch["play_style"] for ch in YT_CHANNELS
]


def _run_with_youtube_lookback(lookback_days: int, label: str):
    init_db()

    builds: list[dict] = []

    def step(name, fn, hard_timeout_s):
        t0 = time.time()
        print(f"[pipeline] >>> starting {name} (hard-timeout {hard_timeout_s}s)", flush=True)
        sys.stdout.flush()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(fn)
            try:
                res = fut.result(timeout=hard_timeout_s)
            except concurrent.futures.TimeoutError:
                elapsed = time.time() - t0
                print(f"[pipeline] !!! {name} TIMED OUT after {elapsed:.1f}s — moving on", flush=True)
                ex._threads.clear()
                concurrent.futures.thread._threads_queues.clear()
                return
            except Exception as e:
                elapsed = time.time() - t0
                print(f"[pipeline] !!! {name} FAILED after {elapsed:.1f}s: {type(e).__name__}: {e}", flush=True)
                return
        elapsed = time.time() - t0
        print(f"[pipeline] <<< {name}: {len(res)} builds ({elapsed:.1f}s)", flush=True)
        builds.extend(res)

    if ENABLE_GEMINI_SITES:
        # Codmunity runs FIRST so its weapon list is cached before
        # youtube_gemini loads its whitelist.
        step("codmunity", scrape_codmunity, hard_timeout_s=120)
        step("wzstats", scrape_wzstats, hard_timeout_s=120)
    else:
        print("[pipeline] codmunity + wzstats SKIPPED (ENABLE_GEMINI_SITES=0)", flush=True)

    step("wzhub", scrape_wzhub, hard_timeout_s=30)
    step(
        "youtube_gemini",
        lambda: scrape_youtube_gemini(lookback_days=lookback_days),
        hard_timeout_s=60 * 30,
    )

    # ALWAYS wipe every known play-style bucket — even ones where we
    # didn't extract anything this run. Otherwise stale rows from older
    # runs (hallucinated weapons before the whitelist, channels that went
    # silent for a few days) hang around in the UI forever.
    deleted_total = delete_builds_by_play_style(KNOWN_PLAY_STYLES)
    print(f"[pipeline] wiped {deleted_total} rows across {len(KNOWN_PLAY_STYLES)} known play_styles", flush=True)

    if not builds:
        print(f"[pipeline] {label}: nothing to upsert (all buckets now empty)")
        log_scrape(label, 0, 0)
        return 0

    by_style: dict[str, list[dict]] = defaultdict(list)
    for b in builds:
        by_style[b.get("play_style") or "Unknown"].append(b)

    upserted = 0
    for play_style, style_builds in by_style.items():
        print(f"[pipeline] {play_style}: upserting {len(style_builds)}", flush=True)
        for b in style_builds:
            try:
                upsert_build(b)
                upserted += 1
            except Exception as e:
                print(f"[pipeline] upsert failed for {b.get('weapon_name')}: {e}", flush=True)

    log_scrape(label, len(builds), upserted)
    print(f"[pipeline] {label}: {upserted} builds upserted across {len(by_style)} play_styles", flush=True)
    return upserted


def run_weekly():
    """Thursday 21:00 Jerusalem — 7-day lookback (Friday → Thursday)."""
    return _run_with_youtube_lookback(7, "weekly")


def run_daily():
    """Daily 21:00 Jerusalem — only the current day's videos."""
    return _run_with_youtube_lookback(1, "daily")


def run():
    return run_weekly()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "weekly"
    if mode == "daily":
        run_daily()
    else:
        run_weekly()
