"""Orchestrates scraping → database upsert."""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from database import init_db, upsert_build, log_scrape
from scrapers.wzhub import scrape as scrape_wzhub


def run():
    init_db()

    # Primary source: wzhub.gg structured weapon builds
    builds = scrape_wzhub()
    print(f"[pipeline] wzhub builds: {len(builds)}")

    if not builds:
        print("[pipeline] nothing to upsert")
        return

    for build in builds:
        upsert_build(build)

    log_scrape("wzhub.gg", len(builds), len(builds))
    print(f"[pipeline] done — {len(builds)} builds upserted")


if __name__ == "__main__":
    run()
