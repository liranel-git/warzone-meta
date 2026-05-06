"""
Orchestrates scraping → database upsert.

Two modes:
  - run_weekly(): 7-day lookback for YouTube, full website refresh
  - run_daily():  1-day lookback for YouTube, full website refresh
"""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from database import init_db, upsert_build, log_scrape
from scrapers.wzhub import scrape as scrape_wzhub
from scrapers.youtube_gemini import scrape as scrape_youtube_gemini
from scrapers.gemini_site import scrape_codmunity, scrape_wzstats


def _run_with_youtube_lookback(lookback_days: int, label: str):
    init_db()

    builds: list[dict] = []

    # 1. wzhub.gg — embedded dataset, always fresh
    try:
        wzhub_builds = scrape_wzhub()
        print(f"[pipeline] wzhub: {len(wzhub_builds)}")
        builds.extend(wzhub_builds)
    except Exception as e:
        print(f"[pipeline] wzhub failed: {e}")

    # 2. codmunity.gg — Gemini URL context
    try:
        cod_builds = scrape_codmunity()
        print(f"[pipeline] codmunity: {len(cod_builds)}")
        builds.extend(cod_builds)
    except Exception as e:
        print(f"[pipeline] codmunity failed: {e}")

    # 3. wzstats.gg — Gemini URL context
    try:
        wzs_builds = scrape_wzstats()
        print(f"[pipeline] wzstats: {len(wzs_builds)}")
        builds.extend(wzs_builds)
    except Exception as e:
        print(f"[pipeline] wzstats failed: {e}")

    # 4. YouTube channels via Gemini visual extraction
    try:
        yt_builds = scrape_youtube_gemini(lookback_days=lookback_days)
        print(f"[pipeline] youtube ({lookback_days}d): {len(yt_builds)}")
        builds.extend(yt_builds)
    except Exception as e:
        print(f"[pipeline] youtube failed: {e}")

    if not builds:
        print(f"[pipeline] {label}: nothing to upsert")
        return 0

    for b in builds:
        try:
            upsert_build(b)
        except Exception as e:
            print(f"[pipeline] upsert failed for {b.get('weapon_name')}: {e}")

    log_scrape(label, len(builds), len(builds))
    print(f"[pipeline] {label}: {len(builds)} builds upserted")
    return len(builds)


def run_weekly():
    """Thursday 21:00 Jerusalem — 7-day lookback (Friday → Thursday)."""
    return _run_with_youtube_lookback(7, "weekly")


def run_daily():
    """Daily 21:00 Jerusalem — only the current day's videos."""
    return _run_with_youtube_lookback(1, "daily")


# Default entry point — defaults to weekly behaviour for backward compat.
def run():
    return run_weekly()


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "weekly"
    if mode == "daily":
        run_daily()
    else:
        run_weekly()
