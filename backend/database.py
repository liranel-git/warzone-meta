import sqlite3
import json
import os
from datetime import datetime

_data_dir = os.environ.get("DB_DIR", os.path.dirname(__file__))
DB_PATH = os.path.join(_data_dir, "warzone.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS builds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                weapon_name TEXT NOT NULL,
                weapon_class TEXT NOT NULL,
                game TEXT NOT NULL DEFAULT 'Warzone',
                play_style TEXT,
                tier TEXT NOT NULL,
                attachments TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_url TEXT,
                source_title TEXT,
                confidence REAL DEFAULT 0.8,
                reasoning TEXT,
                upvotes INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        # Migrations for existing databases
        for col, definition in [
            ("game", "TEXT NOT NULL DEFAULT 'Warzone'"),
            ("play_style", "TEXT"),
        ]:
            try:
                conn.execute(f"ALTER TABLE builds ADD COLUMN {col} {definition}")
            except Exception:
                pass  # already exists
        # Replace old unique index (weapon_name, weapon_class) with one that includes game
        conn.execute("DROP INDEX IF EXISTS idx_weapon")
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_weapon_game
            ON builds(weapon_name, weapon_class, game)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scrape_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                items_scraped INTEGER,
                builds_added INTEGER,
                ran_at TEXT DEFAULT (datetime('now'))
            )
        """)


def upsert_build(build: dict):
    game = build.get("game", "Warzone")
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO builds
                (weapon_name, weapon_class, game, play_style, tier, attachments,
                 source_type, source_url, source_title, confidence, reasoning, upvotes, updated_at)
            VALUES
                (:weapon_name, :weapon_class, :game, :play_style, :tier, :attachments,
                 :source_type, :source_url, :source_title, :confidence, :reasoning, :upvotes,
                 datetime('now'))
            ON CONFLICT(weapon_name, weapon_class, game) DO UPDATE SET
                tier        = CASE WHEN excluded.confidence > builds.confidence
                                   THEN excluded.tier        ELSE builds.tier        END,
                attachments = CASE WHEN excluded.confidence > builds.confidence
                                   THEN excluded.attachments ELSE builds.attachments END,
                reasoning   = CASE WHEN excluded.confidence > builds.confidence
                                   THEN excluded.reasoning   ELSE builds.reasoning   END,
                play_style  = COALESCE(excluded.play_style, builds.play_style),
                source_url   = excluded.source_url,
                source_title = excluded.source_title,
                confidence  = MAX(excluded.confidence, builds.confidence),
                upvotes     = MAX(excluded.upvotes, builds.upvotes),
                updated_at  = datetime('now')
        """, {
            **build,
            "game": game,
            "play_style": build.get("play_style"),
            "attachments": json.dumps(build["attachments"]),
        })


def get_builds(tier=None, weapon_class=None, game=None, play_style=None) -> list[dict]:
    sql = "SELECT * FROM builds WHERE 1=1"
    params = []
    if tier:
        sql += " AND tier = ?"
        params.append(tier)
    if weapon_class:
        sql += " AND weapon_class = ?"
        params.append(weapon_class)
    if game:
        sql += " AND game = ?"
        params.append(game)
    if play_style:
        sql += " AND play_style = ?"
        params.append(play_style)

    tier_order = ("CASE tier WHEN 'Absolute Meta' THEN 1 WHEN 'Meta' THEN 2 "
                  "WHEN 'A' THEN 3 WHEN 'B' THEN 4 WHEN 'F' THEN 5 ELSE 6 END")
    sql += f" ORDER BY {tier_order}, confidence DESC"

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        d["attachments"] = json.loads(d["attachments"])
        result.append(d)
    return result


def get_stats() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM builds").fetchone()[0]
        by_tier = {}
        for row in conn.execute("SELECT tier, COUNT(*) as n FROM builds GROUP BY tier"):
            by_tier[row["tier"]] = row["n"]
        last_log = conn.execute(
            "SELECT ran_at FROM scrape_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return {
        "total": total,
        "by_tier": by_tier,
        "last_scraped": last_log["ran_at"] if last_log else None,
    }


def log_scrape(source: str, items_scraped: int, builds_added: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO scrape_log (source, items_scraped, builds_added) VALUES (?, ?, ?)",
            (source, items_scraped, builds_added),
        )
