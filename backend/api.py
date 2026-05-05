"""FastAPI backend — serves weapon builds to the React frontend."""

import os
import threading
from fastapi import FastAPI, Query, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from database import init_db, get_builds, get_stats  # noqa: E402

app = FastAPI(title="Warzone Meta API")
scheduler = BackgroundScheduler()

ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:4173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

TIERS = ["Absolute Meta", "Meta", "A", "B", "F"]
CLASSES = ["AR", "SMG", "LMG", "Sniper", "Shotgun", "Marksman", "Pistol"]
GAMES = ["Warzone", "BO7", "BO6", "MW3", "MW2"]
PLAY_STYLES = ["Long Range", "Close Range", "Sniper", "Support",
               "Hip Fire", "Tac-Stance", "Aggressive", "Lowest Recoil"]


def _run_pipeline():
    from pipeline import run
    run()


@app.on_event("startup")
def startup():
    init_db()
    scheduler.add_job(
        _run_pipeline,
        CronTrigger(hour=6, minute=0),
        id="daily_pipeline",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    print("[scheduler] daily pipeline job registered — fires at 06:00 UTC")


@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown(wait=False)


@app.get("/api/builds")
def list_builds(
    tier: str | None = Query(None),
    weapon_class: str | None = Query(None, alias="class"),
    game: str | None = Query(None),
    play_style: str | None = Query(None, alias="playStyle"),
):
    if tier and tier not in TIERS:
        raise HTTPException(400, f"tier must be one of: {TIERS}")
    if weapon_class and weapon_class not in CLASSES:
        raise HTTPException(400, f"class must be one of: {CLASSES}")
    builds = get_builds(tier=tier, weapon_class=weapon_class, game=game, play_style=play_style)
    return {"builds": builds}


@app.get("/api/stats")
def stats():
    s = get_stats()
    next_run = scheduler.get_job("daily_pipeline")
    s["next_scrape"] = str(next_run.next_run_time) if next_run else None
    return s


@app.post("/api/pipeline/run")
def run_pipeline(x_pipeline_secret: str | None = Header(None)):
    secret = os.environ.get("PIPELINE_SECRET")
    if secret and x_pipeline_secret != secret:
        raise HTTPException(401, "Invalid secret")
    t = threading.Thread(target=_run_pipeline, daemon=True)
    t.start()
    return {"message": "Pipeline started in background"}
