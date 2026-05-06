"""FastAPI backend — serves weapon builds to the React frontend."""

import os
import threading
from fastapi import FastAPI, Query, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from database import init_db, get_builds, get_stats  # noqa: E402

app = FastAPI(title="Warzone Meta API")
JERUSALEM = ZoneInfo("Asia/Jerusalem")
scheduler = BackgroundScheduler(timezone=JERUSALEM)

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
WEAPON_DOMINANCIES = ["Long Range", "Close Range", "Sniper", "Support",
                      "Hip Fire", "Aggressive", "Lowest Recoil"]


def _run_weekly():
    from pipeline import run_weekly
    run_weekly()


def _run_daily():
    from pipeline import run_daily
    run_daily()


@app.on_event("startup")
def startup():
    init_db()
    # Weekly: every Thursday at 21:00 Jerusalem time, 7-day lookback
    scheduler.add_job(
        _run_weekly,
        CronTrigger(day_of_week="thu", hour=21, minute=0, timezone=JERUSALEM),
        id="weekly_pipeline",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    # Daily: every day at 21:00 Jerusalem time, current-day videos
    scheduler.add_job(
        _run_daily,
        CronTrigger(hour=21, minute=0, timezone=JERUSALEM),
        id="daily_pipeline",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    print("[scheduler] weekly (Thu 21:00) + daily (21:00) jobs registered — Asia/Jerusalem")


@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown(wait=False)


@app.get("/api/builds")
def list_builds(
    tier: str | None = Query(None),
    weapon_class: str | None = Query(None, alias="class"),
    game: str | None = Query(None),
    play_style: str | None = Query(None, alias="playStyle"),
    weapon_dominancy: str | None = Query(None, alias="weaponDominancy"),
):
    if tier and tier not in TIERS:
        raise HTTPException(400, f"tier must be one of: {TIERS}")
    if weapon_class and weapon_class not in CLASSES:
        raise HTTPException(400, f"class must be one of: {CLASSES}")

    dominancies = None
    if weapon_dominancy:
        dominancies = [d.strip() for d in weapon_dominancy.split(",") if d.strip()]
        for d in dominancies:
            if d not in WEAPON_DOMINANCIES:
                raise HTTPException(400, f"weaponDominancy must be one of: {WEAPON_DOMINANCIES}")

    builds = get_builds(
        tier=tier,
        weapon_class=weapon_class,
        game=game,
        play_style=play_style,
        weapon_dominancy=dominancies,
    )
    return {"builds": builds}


@app.get("/api/stats")
def stats():
    s = get_stats()
    weekly = scheduler.get_job("weekly_pipeline")
    daily = scheduler.get_job("daily_pipeline")
    s["next_weekly"] = str(weekly.next_run_time) if weekly else None
    s["next_daily"] = str(daily.next_run_time) if daily else None
    # Backward compat: surface the soonest run as "next_scrape"
    candidates = [j.next_run_time for j in (weekly, daily) if j and j.next_run_time]
    s["next_scrape"] = str(min(candidates)) if candidates else None
    return s


def _check_secret(provided: str | None):
    secret = os.environ.get("PIPELINE_SECRET")
    if secret and provided != secret:
        raise HTTPException(401, "Invalid secret")


@app.post("/api/pipeline/run-weekly")
def trigger_weekly(x_pipeline_secret: str | None = Header(None)):
    _check_secret(x_pipeline_secret)
    threading.Thread(target=_run_weekly, daemon=True).start()
    return {"message": "Weekly pipeline started (7-day lookback)"}


@app.post("/api/pipeline/run-daily")
def trigger_daily(x_pipeline_secret: str | None = Header(None)):
    _check_secret(x_pipeline_secret)
    threading.Thread(target=_run_daily, daemon=True).start()
    return {"message": "Daily pipeline started (today only)"}


# Backward compat for any old client still hitting /api/pipeline/run
@app.post("/api/pipeline/run")
def trigger_legacy(x_pipeline_secret: str | None = Header(None)):
    _check_secret(x_pipeline_secret)
    threading.Thread(target=_run_weekly, daemon=True).start()
    return {"message": "Pipeline started (weekly mode)"}
