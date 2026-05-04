"""Orchestrates scraping → classification → database upsert."""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from database import init_db, upsert_build, log_scrape
from scrapers.reddit import scrape as scrape_reddit
from scrapers.youtube import scrape as scrape_youtube
from classifier.claude_classifier import classify_in_batches


def run():
    init_db()

    # 1. Scrape
    # Reddit blocks cloud provider IPs (AWS/Railway) with 403 — only run locally
    if os.environ.get("DISABLE_REDDIT") != "1":
        reddit_items = scrape_reddit()
    else:
        print("[pipeline] Reddit disabled (cloud environment)")
        reddit_items = []
    youtube_items = scrape_youtube()
    all_items = reddit_items + youtube_items
    print(f"[pipeline] total items: {len(all_items)}")

    if not all_items:
        print("[pipeline] nothing to classify")
        return

    # 2. Classify
    builds = classify_in_batches(all_items, batch_size=8)
    print(f"[pipeline] extracted {len(builds)} builds")

    # 3. Persist
    for build in builds:
        upsert_build(build)

    log_scrape("reddit+youtube", len(all_items), len(builds))
    print(f"[pipeline] done — {len(builds)} builds upserted")


if __name__ == "__main__":
    run()
