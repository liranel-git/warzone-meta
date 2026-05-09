import sqlite3
import json
import os

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
                weapon_dominancy TEXT,
                tier TEXT NOT NULL,
                attachments TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_url TEXT,
                source_title TEXT,
                confidence REAL DEFAULT 0.8,
                reasoning TEXT,
                upvotes INTEGER DEFAULT 0,
                published_at TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        # Migrations for existing databases
        for col, definition in [
            ("game", "TEXT NOT NULL DEFAULT 'Warzone'"),
            ("play_style", "TEXT"),
            ("weapon_dominancy", "TEXT"),
            ("published_at", "TEXT"),
        ]:
            try:
                conn.execute(f"ALTER TABLE builds ADD COLUMN {col} {definition}")
            except Exception:
                pass

        # Drop old indexes; new uniqueness is per (weapon, class, game, play_style)
        # so different creators/sources can each have their own build for the same weapon.
        conn.execute("DROP INDEX IF EXISTS idx_weapon")
        conn.execute("DROP INDEX IF EXISTS idx_weapon_game")
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_weapon_source
            ON builds(weapon_name, weapon_class, game, play_style)
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
    play_style = build.get("play_style") or "Unknown"
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO builds
                (weapon_name, weapon_class, game, play_style, weapon_dominancy, tier, attachments,
                 source_type, source_url, source_title, confidence, reasoning, upvotes,
                 published_at, updated_at)
            VALUES
                (:weapon_name, :weapon_class, :game, :play_style, :weapon_dominancy, :tier, :attachments,
                 :source_type, :source_url, :source_title, :confidence, :reasoning, :upvotes,
                 :published_at, datetime('now'))
            ON CONFLICT(weapon_name, weapon_class, game, play_style) DO UPDATE SET
                tier             = CASE WHEN excluded.published_at IS NOT NULL
                                         AND (builds.published_at IS NULL OR excluded.published_at >= builds.published_at)
                                        THEN excluded.tier ELSE builds.tier END,
                attachments      = CASE WHEN excluded.published_at IS NOT NULL
                                         AND (builds.published_at IS NULL OR excluded.published_at >= builds.published_at)
                                        THEN excluded.attachments ELSE builds.attachments END,
                reasoning        = CASE WHEN excluded.published_at IS NOT NULL
                                         AND (builds.published_at IS NULL OR excluded.published_at >= builds.published_at)
                                        THEN excluded.reasoning ELSE builds.reasoning END,
                weapon_dominancy = COALESCE(excluded.weapon_dominancy, builds.weapon_dominancy),
                source_url       = excluded.source_url,
                source_title     = excluded.source_title,
                confidence       = MAX(excluded.confidence, builds.confidence),
                upvotes          = MAX(excluded.upvotes, builds.upvotes),
                published_at     = COALESCE(excluded.published_at, builds.published_at),
                updated_at       = datetime('now')
        """, {
            **build,
            "game": game,
            "play_style": play_style,
            "weapon_dominancy": build.get("weapon_dominancy"),
            "published_at": build.get("published_at"),
            "upvotes": build.get("upvotes", 0),
            "confidence": build.get("confidence", 0.7),
            "reasoning": build.get("reasoning"),
            "source_url": build.get("source_url"),
            "source_title": build.get("source_title"),
            "attachments": json.dumps(build["attachments"]),
        })


def get_builds(tier=None, weapon_class=None, game=None, play_style=None,
               weapon_dominancy=None) -> list[dict]:
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
    if weapon_dominancy:
        if isinstance(weapon_dominancy, str):
            weapon_dominancy = [weapon_dominancy]
        placeholders = ",".join("?" * len(weapon_dominancy))
        sql += f" AND weapon_dominancy IN ({placeholders})"
        params.extend(weapon_dominancy)

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
        by_play_style = {}
        for row in conn.execute("SELECT play_style, COUNT(*) as n FROM builds GROUP BY play_style"):
            by_play_style[row["play_style"] or "Unknown"] = row["n"]
        last_log = conn.execute(
            "SELECT ran_at FROM scrape_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return {
        "total": total,
        "by_tier": by_tier,
        "by_play_style": by_play_style,
        "last_scraped": last_log["ran_at"] if last_log else None,
    }


def delete_builds_by_play_style(play_styles: list[str], game: str = "Warzone") -> int:
    """Wipe rows for the given play_style buckets. Used before re-inserting
    fresh data so stale builds (e.g. from a previous run before the whitelist
    was active) don't linger."""
    if not play_styles:
        return 0
    placeholders = ",".join("?" * len(play_styles))
    with get_conn() as conn:
        cur = conn.execute(
            f"DELETE FROM builds WHERE game = ? AND play_style IN ({placeholders})",
            [game, *play_styles],
        )
        return cur.rowcount or 0


def log_scrape(source: str, items_scraped: int, builds_added: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO scrape_log (source, items_scraped, builds_added) VALUES (?, ?, ?)",
            (source, items_scraped, builds_added),
        )
