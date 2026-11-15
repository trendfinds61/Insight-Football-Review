# Insight Football — Phase A Report

Master Key: IF-MASTER-2026. Phase A only. Phase B/C/D/E NOT started.
Date: 2026-11-15. Approved scope: ChatGPT-reviewed Phase 1–2 assessment,
Phase A only, with the 10 mandatory conditions.

## Deliverable

- Updated working project ZIP:
  `hidden_files/phase-a/Insight-Football-PhaseA.zip`
  (58 files, 680K, contains only `backend/` — no venv, no `__pycache__`,
  no `.env`, no secrets)
- SHA-256 of the delivered ZIP:
  `4e53c32e7361853b5e04bfc0048bdcc769ff737eb4a87c5f763b108a22968ab7`
- Working copy: `hidden_files/phase-a/working/backend/`
- Pristine originals (for diffing, never modified):
  `hidden_files/phase-a/original-extract/backend/`
  with per-file SHA-256 list in `hidden_files/phase-a/original-files-sha256.txt`

## Originals untouched — verification

Original ZIP SHA-256 re-checked after all work (identical to before):
`b757e5e0ba941eeb1469445405b259006c7dbd9a595958e83dd9ca24c43efc28`
V9 Final PDF: `3ee3eed448ffdc922800ee789a0c90d527a310709faf21285c88a77ad13b6ee1`
V9 Errata Part 2: `2fdd4d1d8aa53b846f8c85ddcd6c18bba7210060c2ac406c7d75d1789c5b6a71`
Original-extract file SHAs re-checked with `diff` against
`original-files-sha256.txt`: identical, "ORIGINAL-EXTRACT UNCHANGED".
No V9 SQL or triggers were invented. No service was connected.
No paid API was introduced. The original project database was never
modified — all changes were made on the working copy only.

## Changed / added / deleted files

Changed (working copy only):
- `backend/app.py` — homepage now reads `rss_items` (relevant + recent,
  partitioned into the four categories, max 20 per category, read-only,
  nothing copied into `news`); new `/login` + `/logout` routes and
  `login_required` protection for `/admin`; per-session CSRF token on
  admin POST; `SECRET_KEY` from `FLASK_SECRET_KEY` env or a random
  per-start key; `app.run(host="127.0.0.1", port=5000, debug=False)`.
- `backend/database.py` — `create_database()` now also creates
  `rss_items` (exact live schema) and the `image_url` column on `news`.
- `backend/rss_collector.py` — hardcoded Senora special case removed
  from `classify_region()`; Bangladesh-feed filter tightened to the
  per-source paths in `SOURCE_AUDIT.md` (Dhaka Tribune
  `/sport/football/`, Daily Star `/sports/football/`); non-matching
  links from those mixed feeds are now skipped at collection time.
- `backend/templates/index.html` — World Football section added;
  International, Bangladesh and Transfer sections now loop over the
  `world_news` / `transfer_news` / `international_news` /
  `bangladesh_news` variables plus the matching RSS lists; nav gains
  a World link. The "Latest" section still shows only `news`, so RSS
  items are not shown twice.
- `backend/templates/admin.html` — hidden CSRF token field, Log out link.
- `backend/SOURCE_AUDIT.md` — appended §7 (Phase A update, 2026-11-15)
  recording the enforced strict filter and the Senora fix. Existing
  content preserved.

Added (working copy only):
- `backend/templates/login.html` — admin login page (shows a clear
  "not configured" message when `ADMIN_PASSWORD` is unset).
- `backend/migrations/001_create_rss_items_table.sql`
- `backend/migrations/002_fix_category_and_senora.sql`
- `backend/migrations/run_migrations.py` — backs up first, applies
  pending migrations in order, records them in `schema_migrations`,
  prints before/after counts; re-run is a safe no-op.
- `backend/backup.py` — timestamped backup + SHA-256 manifest.
- `backend/BACKUP_AND_ROLLBACK.md` — backup, migration and rollback
  instructions, including the exact rollback SQL for migration 002.
- `backend/requirements.txt` — Flask==3.1.0, requests==2.32.3,
  feedparser==6.0.11, beautifulsoup4==4.12.3, python-dotenv==1.0.1.
- `backend/README.md` — setup, run, env vars, migrations, backup,
  RSS collection, Phase A changes, known issues.
- `backend/tests/test_phase_a.py` — 10 unittest cases (see Tests).
- `backend/backups/database-20261115-084946.db` — pre-migration backup
  made by the migration runner, plus `backups/manifest-sha256.txt`.

Deleted: none. No useful file or backup snapshot was deleted.

## Migrations

- `001_create_rss_items_table.sql` — `CREATE TABLE IF NOT EXISTS
  rss_items (...)` matching the live schema exactly. No-op on the
  live database (table already existed). No rollback needed; do NOT
  drop the table (254 rows).
- `002_fix_category_and_senora.sql` — two UPDATEs only, no DELETEs:
  news id 2 `TRANSFER NEWS` -> `TRANSFERS`; rss_items id 1173
  region `bangladesh` -> `review`. Idempotent (second run updates
  0 rows). Rollback SQL is in `BACKUP_AND_ROLLBACK.md`.

## Before / after database checks (working copy only)

Command: direct SQLite checks before migrations, then
`python3 migrations/run_migrations.py`, then the same checks after.
Actual output (abridged to the count lines):

BEFORE:
```
integrity: ('ok',)
news: (2,) [(1, 'Welcome to Insight Football', 'WORLD FOOTBALL'),
            (2, 'Manchester City Transfer Update', 'TRANSFER NEWS')]
rss_items: (254,)
rss region: [('bangladesh', 3), ('international', 116), ('review', 135)]
rss relevance: [('relevant', 121), ('review', 133)]
rss status: [('old', 39), ('recent', 215)]
senora id1173: [(1173, 'bangladesh')]
dup links: (0,)   dup titles: (0,)
```

Migration runner output (exact):
```
Before: news=2 rss_items=254 rss_review=135 rss_bangladesh=3
Pending migrations: ['001_create_rss_items_table.sql', '002_fix_category_and_senora.sql']
Backup created: .../backend/backups/database-20261115-084946.db
Backup SHA-256: 239b51b1370f3ae500bb605a42747fa7858f88780d646e7cf6bde46a06ea9380
Applied: 001_create_rss_items_table.sql (sha256 2d5ed55540ddedf9...)
Applied: 002_fix_category_and_senora.sql (sha256 29360ef30c765635...)
After: news=2 rss_items=254 rss_review=136 rss_bangladesh=2
Backup kept at: .../backend/backups/database-20261115-084946.db
Migrations applied successfully.
```

AFTER:
```
integrity: ('ok',)
news: [(1, 'Welcome to Insight Football', 'WORLD FOOTBALL'),
       (2, 'Manchester City Transfer Update', 'TRANSFERS')]
rss_items: (254,)
rss region: [('bangladesh', 2), ('international', 116), ('review', 136)]
senora id1173: [(1173, "Senora to run 14 pad dispensers at federations,
  women's football academies", 'review', 'relevant', 'recent')]
dup links: (0,)   dup titles: (0,)
migrations applied: [('001_create_rss_items_table.sql', '2026-11-15T08:49:46.921597+00:00'),
                     ('002_fix_category_and_senora.sql', '2026-11-15T08:49:47.154804+00:00')]
relevant+recent: (97,)
relevant+recent by region: [('bangladesh', 2), ('international', 92), ('review', 3)]
```

Reading the counts: news total 2 (unchanged), rss_items total 254
(unchanged). Region `review` 135 -> 136 and `bangladesh` 3 -> 2 is
exactly the one Senora row (id 1173) moving, as migration 002
requires. The 135 rows that were already `review` are untouched.
All 8 `database_before_*.db` snapshots are present and unchanged
(verified by the original-extract SHA check).

Pre-migration backup verification (exact):
```
BACKUP (pre-migration) check:
 news: [(1, 'WORLD FOOTBALL'), (2, 'TRANSFER NEWS')]
 senora: [(1173, 'bangladesh')]
 rss count: (254,)
 integrity: ('ok',)
 schema_migrations rows: (0,)
backup sha256: 239b51b1370f3ae500bb605a42747fa7858f88780d646e7cf6bde46a06ea9380
```
Note: the backup file also contains an empty `schema_migrations`
table (created by the runner before copying); all data rows in it
are pre-migration values, as shown above.

Rerun of the migration runner (idempotency, exact):
```
Before: news=2 rss_items=254 rss_review=136 rss_bangladesh=2
No pending migrations. Database is up to date.
```

Fresh-setup check (exact): `database.py` run in an empty directory
in /tmp printed `Insight Football Database Created Successfully!`,
created both `news` and `rss_items` tables, and a test
`INSERT INTO rss_items ...` succeeded (rss count 1).

## Tests — commands and actual outputs

Test environment: a private venv (`/tmp/phase-a-venv`, not in the
project) with the pinned requirements installed. Flask 3.1.0,
feedparser 6.0.11, requests 2.32.3. No network was used by the
tests except none at all — the live-score tests only check the
no-API-key path. All tests run against temporary copies of the
backend, never against the working database.db.

### 1. Syntax compile

Command:
```
python -m py_compile app.py database.py rss_collector.py backup.py migrations/run_migrations.py tests/test_phase_a.py
```
Output: `PY_COMPILE OK`

### 2. Unit tests (delivered in backend/tests/test_phase_a.py)

Command (from `backend/`):
```
python -m unittest discover -s tests -v
```
Output (exact, final run after the test fix described below):
```
test_admin_get_unauthenticated_redirects_to_login (test_phase_a.PhaseATestCase.test_admin_get_unauthenticated_redirects_to_login) ... ok
test_admin_post_unauthenticated_redirects_to_login (test_phase_a.PhaseATestCase.test_admin_post_unauthenticated_redirects_to_login) ... ok
test_admin_post_without_csrf_is_rejected (test_phase_a.PhaseATestCase.test_admin_post_without_csrf_is_rejected) ... ok
test_api_endpoints_without_key_return_500 (test_phase_a.PhaseATestCase.test_api_endpoints_without_key_return_500) ... ok
test_database_counts_and_integrity (test_phase_a.PhaseATestCase.test_database_counts_and_integrity) ... ok
test_home_shows_rss_in_categories_no_duplicates (test_phase_a.PhaseATestCase.test_home_shows_rss_in_categories_no_duplicates) ... ok
test_login_fails_closed_without_admin_password (test_phase_a.PhaseATestCase.test_login_fails_closed_without_admin_password) ... ok
test_login_then_admin_post_inserts_news (test_phase_a.PhaseATestCase.test_login_then_admin_post_inserts_news) ... ok
test_logout_locks_admin_again (test_phase_a.PhaseATestCase.test_logout_locks_admin_again) ... ok
test_rss_links_appear_once (test_phase_a.PhaseATestCase.test_rss_links_appear_once) ... ok

----------------------------------------------------------------------
Ran 10 tests in 0.482s

OK
```

One real test failure occurred during development and was fixed,
not hidden: the first run was 9/10, with
`test_rss_links_appear_once` failing because one Guardian link
appeared twice in the raw HTML. Investigation showed the article
itself is displayed once — the second occurrence is inside the
item's own summary text (a Guardian "Continue reading..." anchor
stored in the summary). The test was corrected to count the card
link (`href="..."`) instead of the raw URL string, and then passed.
No application code was changed for this; it was a test-counting
error.

What the 10 tests prove: homepage 200 with RSS items in all four
categories and the Senora item in World; each RSS card link appears
at most once (26 RSS cards shown: 20 International + 3 World +
2 Bangladesh + 1 Transfer, matching the LIMIT 20 partition);
unauthenticated `/admin` GET and POST both redirect to `/login`;
login without `ADMIN_PASSWORD` returns 503 "not configured" and
`/admin` stays locked; login with a test password works, an admin
POST with a valid CSRF token inserts a news row (2 -> 3 on the test
copy only); admin POST without a CSRF token returns 403 and inserts
nothing; logout locks `/admin` again; `/api/live` and
`/api/match/123` return 500 "API key not configured" without a key;
`/match/123` renders 200; DB counts/integrity on the test copy.

### 3. Real running server (temporary copy, port 5001)

The app was started from a temp copy of the backend with
`ADMIN_PASSWORD=live-test-pass`, `FLASK_SECRET_KEY=live-test-secret`
(no API key). Server log (exact):
```
* Serving Flask app 'app'
* Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
* Running on http://127.0.0.1:5001
```
curl results (exact):
```
GET /            -> HTTP 200, 48983 bytes
GET /admin      -> HTTP 302, Location: http://127.0.0.1:5001/login?next=/admin
GET /login      -> HTTP 200
GET /api/live   -> HTTP 500, {"error":"API key not configured","success":false}
GET /api/match/123 -> HTTP 500, {"error":"API key not configured","success":false}
GET /match/123  -> HTTP 200
```
Homepage content checks on the served HTML: "Transfer Centre LIVE!"
2 occurrences (image alt + heading of one card), "Messi wins second
MLS Golden Boot" 2, "Timely lift as SAFF stakes rise" 1,
"BANGLADESH FOOTBALL" 3, "(RSS)" 26, "WORLD FOOTBALL" 6.
Server was stopped afterwards (port 5001 down, verified).

### 4. Collector unit check (no network)

```
Senora region now: review
Senora relevance: review
BD feeds: [('Dhaka Tribune Football', '/sport/football/'), ('The Daily Star Football', '/sports/football/')]
Senora special-case still in file? False
423945 still in file? False
```
(Note: the Senora relevance here is `review` because the unit check
passed an empty summary; the stored row keeps its original
`relevance_status='relevant'` from collection. Only its region was
corrected by migration 002.)

### 5. Delivered ZIP self-check

The delivered ZIP was extracted to a fresh /tmp folder and
re-tested there. Exact output:
```
ZIP PY_COMPILE OK
Before: news=2 rss_items=254 rss_review=136 rss_bangladesh=2
No pending migrations. Database is up to date.
Ran 10 tests in 0.438s
OK
ZIP DB: news (2,) rss (254,) integrity ('ok',)
ZIP DB news2: ('TRANSFERS',) senora: ('review',)
```

## Backup information

- Pre-migration backup: `backend/backups/database-20261115-084946.db`
  (348,160 bytes), SHA-256
  `239b51b1370f3ae500bb605a42747fa7858f88780d646e7cf6bde46a06ea9380`,
  recorded in `backend/backups/manifest-sha256.txt`. Verified:
  pre-migration values (news id 2 `TRANSFER NEWS`, Senora
  `bangladesh`, 254 rows, integrity `ok`).
- Original ZIP (ultimate fallback) SHA-256:
  `b757e5e0ba941eeb1469445405b259006c7dbd9a595958e83dd9ca24c43efc28`
- Rollback steps: `backend/BACKUP_AND_ROLLBACK.md` (migration 002
  rollback SQL + full restore procedure).

## Known issues and remaining tasks

- `/api/live` and `/api/match/<id>` return HTTP 500 without an
  API-Football key. No key was supplied; none is stored. This is
  the original behaviour, unchanged. Blocked on the owner supplying
  a key/tier if live scores are wanted.
- Only 17 of the 84 existing Bangladesh-feed rows match the strict
  URL paths, so future collection from Dhaka Tribune / Daily Star
  will be much smaller. That is the audited filter working as
  documented, but the owner should expect fewer new Bangladesh-feed
  items until the feeds publish under those paths.
- RSS relevance is still a simple keyword count; it does not verify
  facts. No verification, article-writing, SEO, or publishing-gate
  code exists — those are Phases B–E, not started.
- `published_at` in `rss_items` is still the raw feed string, not
  normalised. RSS fetching still has no retry/backoff. The API
  cache is still in-memory only.
- The transfer mapping on the homepage is title-based
  (`lower(title) LIKE '%transfer%'`); an article whose transfer
  news is only in its summary will appear under International/World
  instead of Transfers. Documented in `app.py`.
- Phase B remains BLOCKED until Errata Part 1 is obtained and
  reviewed. No V9 SQL or triggers were invented in Phase A.
- After ChatGPT review and approval, the owner still needs to set
  `ADMIN_PASSWORD` (and `FLASK_SECRET_KEY` for stable sessions) in
  a `.env` file in `backend/` on the phone before using admin login.
