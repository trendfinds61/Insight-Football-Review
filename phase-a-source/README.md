# Insight Football — Automated Football News Platform

Master Key: IF-MASTER-2026. Phase A complete (2026-11-15).

An English football news platform for international readers
(USA, UK, Canada, Europe), with Bangladesh Football as a separate,
dedicated category. It collects football news from trusted RSS
sources and shows it on the homepage. Verification, article writing,
SEO checks and publishing gates are NOT part of Phase A — they are
later phases and are not built yet.

## What Phase A changed

1. **Homepage now shows RSS news.** `home()` in `app.py` reads
   `rss_items` where `relevance_status='relevant'` and
   `status='recent'`, mapped to the four categories, in addition to
   the `news` table. RSS items are displayed read-only — nothing is
   copied into `news`, so no duplicate articles are created. Each
   RSS item appears in exactly one category:
   - Bangladesh: `region='bangladesh'`
   - Transfers: any other region, title contains "transfer"
   - International: `region='international'`, title has no "transfer"
   - World: `region='review'`, title has no "transfer", **and the
     link is in a football section (`link LIKE '%/football/%'`)**.
     Phase A fix (ChatGPT review): region `review` also holds
     non-football stories, so a review item is shown as World
     Football only when its link proves it is football news. The
     Senora business story (link `.../business/423945/...`) is
     therefore shown in no football category, while its database
     row is preserved untouched in region `review`. The same
     football-link rule applies to Transfers.
   At most 20 RSS items per category are shown. The "Latest" section
   still shows only `news` items, so RSS items are not shown twice.
2. **Category sections now render.** `templates/index.html` renders
   the `world_news`, `transfer_news`, `international_news` and
   `bangladesh_news` variables (previously headings only, no loops),
   plus the matching RSS lists. A World Football section was added.
3. **Transfer category fixed.** Migration `002` changed the one
   existing transfer row (news id 2) from `TRANSFER NEWS` to
   `TRANSFERS`, matching the admin form and the homepage query.
4. **Senora classification fixed.** The hardcoded special case in
   `rss_collector.py` that forced the Dhaka Tribune business story
   "Senora to run 14 pad dispensers" (link `.../business/423945/...`)
   into region `bangladesh` was removed. Migration `002` corrects
   only that row (rss_items id 1173) to region `review`. No other
   row was changed.
5. **Bangladesh-feed URL filter tightened.** `rss_collector.py` now
   enforces exactly what `SOURCE_AUDIT.md` claims: Dhaka Tribune
   only accepts links under `/sport/football/`, Daily Star only
   under `/sports/football/`. Other links from those mixed feeds are
   skipped. Existing rows are preserved — only future collection
   is affected. Note: only 17 of the 84 existing Bangladesh-feed
   rows match the strict paths, so future intake from those two
   feeds will be much smaller; that is the audited filter working
   as documented.
6. **Admin login added.** `/admin` now requires login at `/login`
   (logout at `/logout`). The password comes only from the
   `ADMIN_PASSWORD` environment variable. There is no default
   password: without `ADMIN_PASSWORD`, login always fails with a
   clear message. Admin POSTs also carry a per-session CSRF token.
7. **Debug off, localhost only.** The app now runs on
   `127.0.0.1:5000` with `debug=False`.
8. **Fresh setup fixed.** `database.py` now creates `rss_items`
   (exact live schema) and the `image_url` column on `news`, so a
   new database matches the live one. Previously a fresh database
   had no `rss_items` table and the collector failed.
9. **Docs and backup.** Added `requirements.txt`, this README,
   `backup.py`, `BACKUP_AND_ROLLBACK.md`, and
   `migrations/` (see below).

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Python 3.12 was used for Phase A testing. Flask 3.1.0,
requests 2.32.3, feedparser 6.0.11, beautifulsoup4 4.12.3,
python-dotenv 1.0.1.

## Run locally

```bash
cd backend
python3 app.py
# open http://127.0.0.1:5000/
```

Always run from the `backend/` directory: the app opens
`database.db` by relative path.

## Environment variables

Create a `.env` file in `backend/` (never commit or share it), e.g.:

```
ADMIN_PASSWORD=choose-a-strong-password-here
FLASK_SECRET_KEY=a-long-random-secret-here
API_FOOTBALL_KEY=your-key-here-if-you-have-one
```

- `ADMIN_PASSWORD` — required for admin login. No default exists.
  Without it, `/login` shows "Admin login is not configured" and
  nobody can log in. Change it by editing `.env` and restarting.
- `FLASK_SECRET_KEY` — signs the login session. Without it, a
  random key is generated at each start and admin sessions do not
  survive a restart (a warning is printed at startup).
- `API_FOOTBALL_KEY` — needed only for `/api/live` and
  `/api/match/<id>`. Without it those endpoints return HTTP 500
  `{"success": false, "error": "API key not configured"}`. This is
  the original behaviour, kept unchanged. No key was supplied with
  Phase A, and none is stored in this project.

Never put passwords or keys in code, in a ZIP, in logs, or in
screenshots.

## Migrations

```bash
cd backend
python3 migrations/run_migrations.py          # apply pending migrations
python3 migrations/run_migrations.py --dry-run  # list pending only
```

The runner first reads the existing migration records (without
writing anything) and works out which migrations are pending.
Only if migrations are pending does it back up `database.db`
(see below) — and the backup is verified before anything is
written: its SHA-256 must match the pre-run database byte for
byte, so the backup is an exact pre-run snapshot. Only then is
the `schema_migrations` table created (if missing), and the
pending `migrations/*.sql` are applied in order, each atomically.
A second run is a safe no-op, and a run with nothing pending
writes nothing at all (no backup, no table creation).

`--dry-run` is genuinely read-only: the database is opened with
SQLite URI `mode=ro`, so no table is created, no backup is made
and nothing is written. It only lists pending migrations.

Each migration is applied atomically: all of its statements plus
its `schema_migrations` record run inside one transaction, so a
failure rolls that migration back in full and the runner stops.
Migrations applied before the failure stay applied; later ones
are not attempted. There is no whole-run rollback — restore the
pre-run backup if the resulting state is unwanted. See
`BACKUP_AND_ROLLBACK.md` and `tests/test_migrations.py`.

- `001_create_rss_items_table.sql` — creates `rss_items` if missing.
  No-op on the live database (the table already exists).
- `002_fix_category_and_senora.sql` — news id 2 category
  `TRANSFER NEWS` -> `TRANSFERS`; rss_items id 1173 region
  `bangladesh` -> `review`. Two UPDATEs only, no DELETEs.

Rollback steps for each migration are in
`BACKUP_AND_ROLLBACK.md`.

## Backup

```bash
cd backend
python3 backup.py
```

Creates `backend/backups/database-<UTC timestamp>.db` and appends
its SHA-256 to `backend/backups/manifest-sha256.txt`. Backups are
never overwritten. The 8 original `database_before_*.db` snapshots
are preserved untouched.

## Collect RSS news

```bash
cd backend
python3 rss_collector.py
```

Fetches the 5 configured feeds (BBC Sport, Sky Sports, The
Guardian, Dhaka Tribune Football, The Daily Star Football) and
inserts new items into `rss_items` (`INSERT OR IGNORE` on the
unique link, so re-running it creates no duplicates). It needs
internet access. It does not publish anything by itself.

## Known issues (Phase A, not fixed — out of approved scope)

- `/api/live` and `/api/match/<id>` need an API-Football key; none
  was supplied, so they return HTTP 500 without one (original
  behaviour, unchanged).
- The RSS relevance check is a simple keyword count (>= 2 football
  keywords = relevant); it does not verify facts. No verification,
  article-writing, SEO, or publishing-gate code exists yet — those
  are later phases.
- `published_at` in `rss_items` is stored as the raw feed string,
  not normalised to one date format.
- RSS fetching has no retry/backoff if a feed is temporarily down.
- The in-memory API cache is lost on restart.
- Phase B (V9 identity database) is BLOCKED until Errata Part 1 is
  obtained. No V9 SQL or triggers were invented in Phase A.

## Project structure

```
backend/
  app.py                  Flask app (routes, admin login, RSS display)
  database.py             creates news + rss_items tables
  database.db             live database (news 2 rows, rss_items 254 rows)
  rss_collector.py        RSS collection + classification
  backup.py               safe database backup
  BACKUP_AND_ROLLBACK.md  backup + rollback instructions
  README.md               this file
  requirements.txt        pinned dependencies
  migrations/             001, 002 + run_migrations.py
  templates/              index.html, admin.html, login.html, match.html
  static/css/style.css
  database_before_*.db    8 original snapshots (preserved)
```
