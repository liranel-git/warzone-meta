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

from database import (
    init_db, upsert_build, log_scrape, delete_builds_by_play_style, purge_low_tier
)
from scrapers.wzhub import scrape as scrape_wzhub
from scrapers.youtube_gemini import scrape as scrape_youtube_gemini, CHANNELS as YT_CHANNELS
from scrapers.gemini_site import scrape_codmunity, scrape_wzstats

# Codmunity + WZ Stats now use Gemini's google_search grounding tool
# (verified to return useful data in AI Studio, unlike the old
# url_context approach). Default ON; set ENABLE_GEMINI_SITES=0 to skip.
ENABLE_GEMINI_SITES = os.environ.get("ENABLE_GEMINI_SITES", "1") == "1"

# NOTE: there is no longer an up-front scope wipe. Each scraper's
# upsert_batch() wipes ONLY the play_style buckets it actually produced
# data for (see upsert_batch below). This means:
#   - A daily run never touches Codmunity / WZ Meta (those scrapers don't
#     run on daily, so no batch carries those play_styles).
#   - A failed/empty scrape leaves its bucket's existing data intact
#     instead of nuking it.


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
        """Wipe-then-insert, but ONLY for the play_style buckets actually
        present in `builds`. A scraper that returned nothing (429, timeout,
        no videos) leaves its existing bucket untouched — a failed scrape
        must never destroy data that's already there."""
        nonlocal upserted
        if not builds:
            print(f"[pipeline] {source_label}: 0 builds — existing data left intact", flush=True)
            return
        styles = sorted({b.get("play_style") for b in builds if b.get("play_style")})
        deleted = delete_builds_by_play_style(styles)
        n_ok = 0
        for b in builds:
            try:
                upsert_build(b)
                n_ok += 1
            except Exception as e:
                print(f"[pipeline] upsert failed for {b.get('weapon_name')}: {e}", flush=True)
        upserted += n_ok
        print(f"[pipeline] {source_label}: wiped {deleted}, upserted {n_ok}/{len(builds)} across {styles}", flush=True)

    # ─── Site scrapers (weekly only, grounded → expensive but fine on
    # the paid tier). Short courtesy sleeps only — no longer free-tier
    # quota survival hacks.
    sites_429ed = 0
    run_sites = ENABLE_GEMINI_SITES and label == "weekly"
    if run_sites:
        cod_builds = run_step("codmunity", scrape_codmunity, hard_timeout_s=120)
        upsert_batch(cod_builds, "Codmunity")
        if not cod_builds:
            sites_429ed += 1
        time.sleep(3)

        wzs_builds = run_step("wzstats", scrape_wzstats, hard_timeout_s=120)
        upsert_batch(wzs_builds, "WZ Meta")
        if not wzs_builds:
            sites_429ed += 1

        # If BOTH site scrapers returned zero something is genuinely
        # wrong (network, key, both URLs dead). Still attempt YouTube —
        # on the paid tier a transient blip on the sites shouldn't gate
        # the whole run.
        if sites_429ed == 2:
            print("[pipeline] codmunity AND wzstats both returned 0 — continuing to youtube_gemini anyway (paid tier).", flush=True)
        else:
            time.sleep(3)
    elif ENABLE_GEMINI_SITES:
        print(f"[pipeline] codmunity + wzstats SKIPPED (only run on weekly; this is {label})", flush=True)
    else:
        print("[pipeline] codmunity + wzstats SKIPPED (ENABLE_GEMINI_SITES=0)", flush=True)

    # ─── wzhub — cheap, no API calls
    wz_builds = run_step("wzhub", scrape_wzhub, hard_timeout_s=30)
    upsert_batch(wz_builds, "WZ Hub")

    # ─── youtube_gemini — most expensive, most fragile. Pass output_list so
    # builds extracted before any timeout are preserved. Always runs now
    # (paid tier — a site-scraper blip no longer gates the YouTube pass).
    yt_partial: list[dict] = []
    run_step(
        "youtube_gemini",
        lambda: scrape_youtube_gemini(lookback_days=lookback_days, output_list=yt_partial),
        hard_timeout_s=60 * 50,  # 50 min — last run timed out at 30 mid-channel
    )
    # Upsert whatever made it into the shared list, even on timeout.
    upsert_batch(yt_partial, "YouTube (partial-safe)")

    # Self-healing sweep: website buckets must only carry Absolute Meta /
    # Meta / A. This purges any below-A rows left over from a pre-tier-filter
    # run, or from a scraper (codmunity) that has since stopped returning
    # data so its bucket never got wiped+rewritten.
    purged = purge_low_tier(["Codmunity", "WZ Meta", "WZ Hub"])
    if purged:
        print(f"[pipeline] purged {purged} below-A-tier rows from website buckets", flush=True)

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
