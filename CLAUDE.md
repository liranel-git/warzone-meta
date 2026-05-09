# Warzone Meta — Project Context

## What this project does
A Call of Duty: Warzone weapon-build tracker. Aggregates current-meta loadouts from multiple sources (curated YouTube creators, codmunity.gg, wzstats.gg, wzhub.gg), categorises them by tier (Absolute Meta / Meta / A / B / F), and surfaces them in a React UI with per-source ("play style") filters and multi-select weapon-dominancy tags (Long Range, Close Range, Sniper, etc.).

## Stack
- **Backend**: FastAPI + SQLite + APScheduler. Deployed on **Railway**. Persistent volume mounted at `/app/data` (`DB_DIR` env var).
- **Frontend**: React + Vite, deployed on **Vercel**.
- **AI**: Gemini 2.5 Flash via `google-genai` SDK — used for both video understanding (`FileData(file_uri=...)`) and Google Search grounding (`Tool(google_search=GoogleSearch())`). Anthropic / Claude was removed from the pipeline during the restructure.
- **Routing**: BrowserRouter with two routes — `/` (main) and `/admin`. Older `/meta-hub`, `/maps-hub`, `/camo-hub` routes were removed.

## Architecture

### Database
SQLite, single `builds` table with unique index on `(weapon_name, weapon_class, game, play_style)`. Two key fields:
- `play_style` — identifies the **source/channel** (e.g. "Fast Movement", "Codmunity", "WZ Hub"). NOT the weapon style.
- `weapon_dominancy` — identifies the **weapon style** (Long Range, Close Range, etc.).

`scrape_log` table tracks pipeline runs.

### Scrapers (`backend/scrapers/`)
- **`wzhub.py`** — embedded ~108-weapon dataset hand-derived from wzhub.gg. No API calls. Always populates `play_style="WZ Hub"`. Source-of-truth fallback when codmunity scrape fails.
- **`gemini_site.py`** — generic Gemini-grounded scraper. Used for `codmunity.gg` and `wzstats.gg`. Uses `Tool(google_search=GoogleSearch())` (NOT `url_context` — that doesn't work on JS-rendered sites). After every successful Codmunity scrape, the weapon list is persisted to `$DB_DIR/codmunity_whitelist.json` for the YouTube extractor to consume.
- **`youtube_gemini.py`** — for the 8 curated channels. Per channel:
  1. List up-to-`MAX_VIDEOS_PER_CHANNEL` (10) most-recent videos within the lookback window.
  2. Batch-fetch description + ISO duration via `videos.list(part=snippet,contentDetails)`.
  3. Best-effort transcript via `youtube-transcript-api` (often blocked from cloud IPs — that's fine, we fall back to title+description).
  4. Send title + description + transcript as a TEXT prompt to Gemini, **with `Tool(google_search=GoogleSearch())` enabled** so Gemini can supplement with third-party recaps.
  5. Validation: weapon_name must match a canonical name in the whitelist (codmunity if cached, wzhub fallback). Wrong class → corrected to canonical class. Slot must be in a fixed list. Hallucinated weapons are dropped.
  6. Optional visual fallback (env-gated `ENABLE_VISUAL_FALLBACK=1`) for text-empty + build-keyword titles. Has a 60s global cooldown.
  7. Per-channel dedupe by canonical weapon name — most recent video wins.

### Channels → Play Styles
Defined in `youtube_gemini.py` `CHANNELS`:
| Channel | Play Style |
|---|---|
| Camy | Fast Movement |
| Lion | Legacy Meta |
| Ryda | Rank Play |
| eyeqew | Personal Meta Builds |
| stract | Casual and Meta |
| Cpreds | Casual |
| Swagg | Team Play |
| MrMarvelTV | Meta and Follower Builds |

Plus three site-derived styles: `Codmunity`, `WZ Meta`, `WZ Hub`.

### Pipeline (`backend/pipeline.py`)
Two entry points: `run_weekly()` (7-day YouTube lookback, runs site scrapers) and `run_daily()` (1-day lookback, **skips site scrapers** — uses cached codmunity whitelist).

Each scraper runs inside `concurrent.futures.ThreadPoolExecutor` with a hard timeout. Codmunity / WZStats grounded calls are heavy (~50–100K input tokens each), so we sleep 30s between them and 60s after wzstats before YouTube starts, to let the per-minute Gemini quota refresh.

After all scrapers finish, the pipeline:
1. Wipes ALL known play_style buckets (`KNOWN_PLAY_STYLES`) regardless of whether each got fresh data — kills stale rows from older runs.
2. Upserts whatever was scraped.
3. Logs the run via `log_scrape()` so `last_scraped` timestamp updates.

### Scheduler
APScheduler with `Asia/Jerusalem` timezone. Two cron jobs:
- **Weekly**: every Thursday 21:00 → `run_weekly()`
- **Daily**: every day 21:00 → `run_daily()`

### API endpoints
- `GET /api/builds?game=Warzone&playStyle=...&weaponDominancy=A,B` — list filtered builds. `weaponDominancy` is comma-separated for multi-select.
- `GET /api/stats` — total + by-tier + last_scraped + next_weekly + next_daily.
- `POST /api/pipeline/run-weekly` — manual trigger (header `x-pipeline-secret`).
- `POST /api/pipeline/run-daily` — manual trigger.
- Legacy `POST /api/pipeline/run` exists for backward compat.

### Frontend layout (`/`)
1. `Header` — title + last_scraped (formatted in Asia/Jerusalem) + next_scrape + Admin button.
2. `NavBar` — single "META BUILDS" tab.
3. **Play-style chip row** — All + 11 chips (8 channels + Codmunity + WZ Meta + WZ Hub).
4. **Weapon-dominancy multi-select tag row** — All + 7 tags (Long Range, Close Range, Sniper, Support, Hip Fire, Aggressive, Lowest Recoil). "All" is exclusive; clicking a specific tag deselects All. Switching play style auto-resets dominancy to "All".
5. `SearchBar` — substring match on weapon_name within current filters.
6. Tier-grouped results, or flat list when searching.
7. After search results, if filtering by a specific play style would yield more matches across all play styles, show a "**Search across all play styles →**" link that flips play_style to All but keeps dominancy + query.

`/admin` has two buttons:
- **Weekly Refresh (7 days)** — full pipeline incl. site scrapers
- **Daily Refresh (today)** — YouTube + wzhub only

## Environment variables (Railway)
- `ANTHROPIC_API_KEY` — left in env but unused (Claude was removed)
- `GEMINI_API_KEY` — required for both site scrapers and YouTube text/visual extraction
- `YOUTUBE_API_KEY` — required for YouTube Data API (search, videos.list)
- `PIPELINE_SECRET` — frontend admin password; sent as `x-pipeline-secret` header
- `DB_DIR=/app/data` — points at the persistent Railway volume
- `DISABLE_REDDIT=1` — legacy, no longer relevant
- Optional toggles:
  - `ENABLE_GEMINI_SITES=1` (default 1) — runs codmunity + wzstats on weekly. Set to 0 to skip.
  - `ENABLE_VISUAL_ENRICH=0` (default 0) — fills empty attachments by visual fallback. Costs 50–100K tokens per call; only enable on a paid Gemini tier.
  - `ENABLE_VISUAL_FALLBACK=0` (default 0) — runs visual when text returns 0 builds AND title looks build-y. Same cost concern.

## Known quirks / gotchas

### Why Gemini's url_context tool doesn't work for codmunity / wzstats
Both sites are JavaScript-rendered. `Tool(url_context=UrlContext())` fetches the raw HTML, which is mostly empty shells. Switched to `Tool(google_search=GoogleSearch())` — Gemini queries Google's index instead of fetching directly. Verified working for both sites.

### Why we can't combine `FileData` + `google_search` in one Gemini call
SDK forbids it. So:
- Text path (no FileData) — has google_search ✓
- Visual path (FileData) — has no grounding tool ✗

### Free-tier Gemini 250K-input-tokens-per-minute cap
Hard ceiling. Heavy grounded calls (codmunity + wzstats) easily blow it if back-to-back. Mitigations:
- Site scrapers only run on weekly, with 30s sleep between them and 60s cooldown before YouTube
- YouTube text calls sleep 6s between them
- Visual calls have a global 60s cooldown when enabled
- 429s auto-retry with backoff parsed from Gemini's error

### Why MetaHub / MapsHub / CamoHub were removed
The play-style filter rework made them redundant — the user wanted a single "Meta Builds" view with all the filtering inline. Map information now appears as a "Best Maps" toggle inside each WeaponCard, computed from the weapon's `weapon_dominancy`.

### YouTube transcript API on Railway
Returns `None` most of the time because YouTube blocks bulk transcript requests from cloud-provider IPs. Pipeline handles this gracefully and falls back to title + description.

### Per-source dedup vs cross-source
Within one play_style we keep only ONE row per `(weapon_name, weapon_class, game, play_style)`. Across play_styles, the same weapon CAN appear multiple times (e.g. Voyak KT-3 from Camy AND from Lion are kept separate, since they may have different attachments).

## Running locally

### Backend
```
cd backend
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```
Set `YOUTUBE_API_KEY`, `GEMINI_API_KEY`, optionally `PIPELINE_SECRET` in a `.env` at repo root.

### Frontend
```
cd frontend
npm install
npm run dev
```
Set `VITE_API_URL=http://localhost:8000` for local backend.

### Manual pipeline run
```
cd backend
python pipeline.py weekly   # or daily
```

## Conventions
- Python: 3.10+ syntax (`str | None`, `list[dict]`).
- Imports: stdlib → third-party → local. Lazy imports inside functions for circular-import-prone modules (e.g. `from scrapers.wzhub import WARZONE_BUILDS` is lazy in `youtube_gemini`).
- All long-running operations use `flush=True` on `print` so Railway log tail is real-time.
- All filters/queries are SQL-parameterised; never f-string SQL.
- Inline styles in React (no CSS-in-JS lib) — kept simple.
- Commit messages follow imperative present tense, with a short summary line + body explaining the *why*.
