"""
Orchestrates scraping → database upsert.

Two modes:
  - run_weekly(): 7-day lookback for YouTube, full website refresh
  - run_daily():  1-day lookback for YouTube, full website refresh
"""

import os
import concurrent.futures
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from database import init_db, upsert_build, log_scrape
from scrapers.wzhub import scrape as scrape_wzhub
from scrapers.youtube_gemini import scrape as scrape_youtube_gemini
from scrapers.gemini_site import scrape_codmunity, scrape_wzstats

# Codmunity + WZ Meta site scraping via Gemini URL-context is currently
# unreliable (calls hang past their nominal timeout). Disable for now —
# the data still flows from wzhub.gg + the eight YouTube channels.
ENABLE_GEMINI_SITES = os.environ.get("ENABLE_GEMINI_SITES", "0") == "1"


def _run_with_youtube_lookback(lookback_days: int, label: str):
    import sys
    import time
    init_db()

    builds: list[dict] = []

    def step(name, fn, hard_timeout_s):
        """Run a scraper with a HARD timeout. If it doesn't finish in time,
        we abandon the future and continue — the daemon thread will be
        cleaned up when the worker exits."""
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
                # don't wait for the abandoned thread on shutdown
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

    step("wzhub", scrape_wzhub, hard_timeout_s=30)

    if ENABLE_GEMINI_SITES:
        step("codmunity", scrape_codmunity, hard_timeout_s=90)
        step("wzstats", scrape_wzstats, hard_timeout_s=90)
    else:
        print("[pipeline] codmunity + wzstats SKIPPED (set ENABLE_GEMINI_SITES=1 to enable)", flush=True)

    step(
        "youtube_gemini",
        lambda: scrape_youtube_gemini(lookback_days=lookback_days),
        hard_timeout_s=60 * 30,  # 30 min cap for the entire YouTube pass
    )

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
