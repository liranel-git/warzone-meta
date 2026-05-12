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
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from database import init_db, upsert_build, log_scrape, delete_builds_by_play_style
from scrapers.wzhub import scrape as scrape_wzhub
from scrapers.youtube_gemini import scrape as scrape_youtube_gemini, CHANNELS as YT_CHANNELS
from scrapers.gemini_site import scrape_codmunity, scrape_wzstats

# Codmunity + WZ Stats now use Gemini's google_search grounding tool
# (verified to return useful data in AI Studio, unlike the old
# url_context approach). Default ON; set ENABLE_GEMINI_SITES=0 to skip.
ENABLE_GEMINI_SITES = os.environ.get("ENABLE_GEMINI_SITES", "1") == "1"

# Bucket groupings — used to scope the per-run wipe.
SITE_PLAY_STYLES: list[str] = ["Codmunity", "WZ Meta"]
WZHUB_PLAY_STYLE: str = "WZ Hub"
YT_PLAY_STYLES: list[str] = [ch["play_style"] for ch in YT_CHANNELS]

# Daily runs refresh ONLY wzhub + YouTube channels. Codmunity / WZ Meta
# are weekly-only (their grounded calls are expensive). So a daily run
# must NOT wipe those buckets, or they go blank between weekly runs.
DAILY_SCOPE: list[str] = [WZHUB_PLAY_STYLE] + YT_PLAY_STYLES
WEEKLY_SCOPE: list[str] = SITE_PLAY_STYLES + [WZHUB_PLAY_STYLE] + YT_PLAY_STYLES


def _run_with_youtube_lookback(lookback_days: int, label: str):
    init_db()

    def run_step(name, fn, hard_timeout_s):
        """Run a scraper with hard timeout. Returns the result list, or [] if
        the scraper timed out / failed. Does NOT mutate the DB — caller
        decides what to upsert."""
        t0 = time.time()
        print(f"[pipeline] >>> starting {name} (hard-timeout {hard_timeout_s}s)", flush=True)
        sys.stdout.flush()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(fn)
            try:
                res = fut.result(timeout=hard_timeout_s)
                elapsed = time.time() - t0
                print(f"[pipeline] <<< {name}: {len(res)} builds ({elapsed:.1f}s)", flush=True)
                return res
            except concurrent.futures.TimeoutError:
                elapsed = time.time() - t0
                print(f"[pipeline] !!! {name} TIMED OUT after {elapsed:.1f}s — moving on", flush=True)
                ex._threads.clear()
                concurrent.futures.thread._threads_queues.clear()
                return []
            except Exception as e:
                elapsed = time.time() - t0
                print(f"[pipeline] !!! {name} FAILED after {elapsed:.1f}s: {type(e).__name__}: {e}", flush=True)
                return []

    upserted = 0

    def upsert_batch(builds: list[dict], source_label: str):
        nonlocal upserted
        if not builds:
            return
        n_ok = 0
        for b in builds:
            try:
                upsert_build(b)
                n_ok += 1
            except Exception as e:
                print(f"[pipeline] upsert failed for {b.get('weapon_name')}: {e}", flush=True)
        upserted += n_ok
        print(f"[pipeline] {source_label}: upserted {n_ok}/{len(builds)}", flush=True)

    # ─── WIPE FIRST so any partial scraper results land in a clean slate.
    # If a scraper crashes / times out mid-run, the rows that DID make it in
    # before the crash are kept — much better than losing everything.
    scope = WEEKLY_SCOPE if label == "weekly" else DAILY_SCOPE
    deleted_total = delete_builds_by_play_style(scope)
    print(f"[pipeline] wiped {deleted_total} rows across {len(scope)} in-scope play_styles ({label})", flush=True)

    # ─── Site scrapers (weekly only, grounded → expensive)
    sites_429ed = 0
    run_sites = ENABLE_GEMINI_SITES and label == "weekly"
    if run_sites:
        cod_builds = run_step("codmunity", scrape_codmunity, hard_timeout_s=120)
        upsert_batch(cod_builds, "Codmunity")
        if not cod_builds:
            sites_429ed += 1
        time.sleep(30)

        wzs_builds = run_step("wzstats", scrape_wzstats, hard_timeout_s=120)
        upsert_batch(wzs_builds, "WZ Meta")
        if not wzs_builds:
            sites_429ed += 1

        # If BOTH site scrapers returned zero, Gemini quota is almost
        # certainly exhausted for the day. Skip YouTube — every call would
        # 429 and grind the pipeline for 30 minutes burning quota.
        if sites_429ed == 2:
            print("[pipeline] codmunity AND wzstats both returned 0 — Gemini quota likely dead. Skipping youtube_gemini.", flush=True)
        else:
            print("[pipeline] cooling down 60s before youtube_gemini …", flush=True)
            time.sleep(60)
    elif ENABLE_GEMINI_SITES:
        print(f"[pipeline] codmunity + wzstats SKIPPED (only run on weekly; this is {label})", flush=True)
    else:
        print("[pipeline] codmunity + wzstats SKIPPED (ENABLE_GEMINI_SITES=0)", flush=True)

    # ─── wzhub — cheap, no API calls
    wz_builds = run_step("wzhub", scrape_wzhub, hard_timeout_s=30)
    upsert_batch(wz_builds, "WZ Hub")

    # ─── youtube_gemini — most expensive, most fragile. Pass output_list so
    # builds extracted before any timeout are preserved.
    if not (run_sites and sites_429ed == 2):
        yt_partial: list[dict] = []
        run_step(
            "youtube_gemini",
            lambda: scrape_youtube_gemini(lookback_days=lookback_days, output_list=yt_partial),
            hard_timeout_s=60 * 30,
        )
        # Upsert whatever made it into the shared list, even on timeout.
        upsert_batch(yt_partial, "YouTube (partial-safe)")

    if upserted == 0:
        print(f"[pipeline] {label}: nothing was upserted")
    log_scrape(label, upserted, upserted)
    print(f"[pipeline] {label}: {upserted} builds upserted total", flush=True)
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
