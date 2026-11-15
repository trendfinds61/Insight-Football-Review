# Insight Football — Phase A Fix 2 Report (ChatGPT Conditional Accept)
Master Key: IF-MASTER-2026. Date: 2026-11-15. Status: correction complete, awaiting ChatGPT final review.

## 0. What this is

ChatGPT gave Phase A a CONDITIONAL ACCEPT: the four previous
findings are addressed, with exactly ONE remaining correction in
`migrations/run_migrations.py`. This report fixes that one
correction, in the separate working copy only. No Phase B, C, D
or E work was done. No original file was modified. After this
correction the work stops again for ChatGPT's final review.

## 1. The remaining correction

Problem (ChatGPT): in normal mode the runner created and
committed the `schema_migrations` table BEFORE calling
`make_backup(db_path)`, so the backup was not an exact pre-run
database snapshot — it already contained that write.

Fix (`backend/migrations/run_migrations.py` only, plus docs and
tests): the order is now exactly what ChatGPT specified:

1. Read existing migration records without writing
   (`read_applied`, SELECT only).
2. Determine pending migrations.
3. If migrations are pending, create the timestamped backup FIRST
   and verify it (`verify_backup`): the backup SHA-256 must match
   the database bytes recorded before the backup was made, and
   the backup must pass `PRAGMA integrity_check`. If verification
   fails, the runner stops (exit 1) before writing anything.
4. Only then create/commit `schema_migrations` if needed.
5. Apply migrations using the existing atomic transaction logic
   (unchanged: statement splitter + one BEGIN ... COMMIT per
   migration, including its record).
6. Dry-run behaviour is unchanged and still genuinely read-only
   (SQLite URI `mode=ro`, no table creation, no backup, no writes).

A run with nothing pending writes nothing at all: no backup, no
table creation, identical SHA-256.

## 2. Deliverables

| File | SHA-256 / note |
|---|---|
| `Insight-Football-PhaseA-Fixes2.zip` (new ZIP, 60 files, 708,898 bytes) | `5f7de6342792269bfa265abc355af6f2e7da373bafce69ea58a5f6c139cf3906` |
| `Insight-Football-PhaseA-Fixes.zip` (previous fixes ZIP, unchanged) | `16f31a1ecd0b951bc10cc8d37500d9c9aa1b051967a2aba59a08063f3a796ebe` |
| `Insight-Football-PhaseA.zip` (original Phase A ZIP, unchanged) | `4e53c32e7361853b5e04bfc0048bdcc769ff737eb4a87c5f763b108a22968ab7` |
| Original project ZIP (unchanged) | `b757e5e0ba941eeb1469445405b259006c7dbd9a595958e83dd9ca24c43efc28` |

### Changed files vs the Fixes ZIP (5 changed, 0 added, 0 removed)

- `backend/migrations/run_migrations.py` — reordered + `verify_backup`
- `backend/tests/test_migrations.py` — 3 new backup-snapshot tests
- `backend/README.md` — new backup/verification order documented
- `backend/BACKUP_AND_ROLLBACK.md` — backup is an exact pre-run snapshot
- `backend/SOURCE_AUDIT.md` — new §9, this fix

`phase-a-source/` in the repo now matches the new ZIP's
`backend/` contents exactly.

## 3. Evidence — the backup is an exact pre-run snapshot

### 3.1 Manual demonstration (temporary copy, real runner run)

Pre-run database SHA-256:
`267216bfc614f7b6c9327f38c82dbadb1f4af091d5bcca5666e34a791ec1d6ff`

Runner output (pending migration `900_demo.sql` injected only
in the temporary copy):

```
Before: news=2 rss_items=254 rss_review=136 rss_bangladesh=2
Pending migrations: ['900_demo.sql']
Backup created: .../backups/database-20261115-102121.db
Backup SHA-256: 267216bfc614f7b6c9327f38c82dbadb1f4af091d5bcca5666e34a791ec1d6ff
Backup verified: SHA-256 matches the pre-run database (267216bfc614f7b6...) and integrity_check is ok.
Applied: 900_demo.sql (sha256 256635a95671f7a8...) (1 statement(s))
After: news=2 rss_items=254 rss_review=136 rss_bangladesh=2
Backup kept at: .../backups/database-20261115-102121.db
Migrations applied successfully.
```

Backup SHA-256 `267216bf...` is identical to the pre-run
database SHA-256. The backup contains no trace of the migration
(`order_demo_marker` table: 0 in backup, 1 in final database;
`900_demo.sql` recorded: 0 in backup, 1 in final database),
and its integrity check returns `ok`.

### 3.2 New tests (3, all pass)

In `backend/tests/test_migrations.py`, each on a temporary
database copy, no network, no real key:

- `test_backup_is_exact_pre_run_snapshot`: with a pending
  migration, the created backup's SHA-256 equals the SHA-256
  recorded before the run; the backup has no marker table and no
  record of the applied migration, while the final database has
  both; runner prints "Backup verified: SHA-256 matches the
  pre-run database".
- `test_backup_predates_schema_migrations_table_creation`: with
  the table dropped before the run (so 001/002 are pending
  again), the backup SHA-256 equals the pre-run SHA-256, the
  backup contains NO `schema_migrations` table, and the final
  database has it with 001 + 002 recorded. This is the exact
  case the old order got wrong.
- `test_no_pending_makes_no_backup_and_no_write`: with nothing
  pending, exit 0, "No pending migrations", SHA-256 and full
  schema dump identical before/after, no `backups/` directory
  created.

### 3.3 Dry-run still genuinely read-only

On the real working database (not a copy): SHA-256 before
`267216bfc614f7b6c9327f38c82dbadb1f4af091d5bcca5666e34a791ec1d6ff`,
after `267216bfc614f7b6c9327f38c82dbadb1f4af091d5bcca5666e34a791ec1d6ff`
(identical), output `Before: news=2 rss_items=254 rss_review=136
rss_bangladesh=2` / `No pending migrations. Database is up to date.`,
no new backup file created.

## 4. Final verification

### 4.1 Full test suite — complete actual output

Command (from `backend/`, in a venv built from
`requirements.txt`: Flask 3.1.0, requests 2.32.3, feedparser
6.0.11, beautifulsoup4 4.12.3, python-dotenv 1.0.1):

```
python3 -m unittest discover -s tests -v
```

Output:

```
test_live_api_error_response (test_live_api.LiveApiTestCase.test_live_api_error_response) ... ok
test_live_connection_timeout (test_live_api.LiveApiTestCase.test_live_connection_timeout) ... ok
test_live_empty_results (test_live_api.LiveApiTestCase.test_live_empty_results) ... ok
test_live_invalid_json (test_live_api.LiveApiTestCase.test_live_invalid_json) ... ok
test_live_success_filters_leagues (test_live_api.LiveApiTestCase.test_live_success_filters_leagues) ... ok
test_match_api_error_response (test_live_api.LiveApiTestCase.test_match_api_error_response) ... ok
test_match_connection_timeout (test_live_api.LiveApiTestCase.test_match_connection_timeout) ... ok
test_match_events_api_error (test_live_api.LiveApiTestCase.test_match_events_api_error) ... ok
test_match_invalid_json (test_live_api.LiveApiTestCase.test_match_invalid_json) ... ok
test_match_not_found (test_live_api.LiveApiTestCase.test_match_not_found) ... ok
test_match_success (test_live_api.LiveApiTestCase.test_match_success) ... ok
test_match_success_uses_cache (test_live_api.LiveApiTestCase.test_match_success_uses_cache) ... ok
test_backup_is_exact_pre_run_snapshot (test_migrations.MigrationRunnerTestCase.test_backup_is_exact_pre_run_snapshot) ... ok
test_backup_predates_schema_migrations_table_creation (test_migrations.MigrationRunnerTestCase.test_backup_predates_schema_migrations_table_creation) ... ok
test_dry_run_does_not_create_schema_migrations_table (test_migrations.MigrationRunnerTestCase.test_dry_run_does_not_create_schema_migrations_table) ... ok
test_dry_run_is_read_only_with_pending_migration (test_migrations.MigrationRunnerTestCase.test_dry_run_is_read_only_with_pending_migration) ... ok
test_failure_between_migrations (test_migrations.MigrationRunnerTestCase.test_failure_between_migrations) ... ok
test_good_migration_applies_and_second_run_is_noop (test_migrations.MigrationRunnerTestCase.test_good_migration_applies_and_second_run_is_noop) ... ok
test_no_pending_makes_no_backup_and_no_write (test_migrations.MigrationRunnerTestCase.test_no_pending_makes_no_backup_and_no_write) ... ok
test_single_migration_failure_rolls_back_fully (test_migrations.MigrationRunnerTestCase.test_single_migration_failure_rolls_back_fully) ... ok
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
test_senora_business_story_in_no_football_category (test_phase_a.PhaseATestCase.test_senora_business_story_in_no_football_category) ... ok

----------------------------------------------------------------------
Ran 31 tests in 1.175s

OK
```

31 tests, 0 failures (was 28 in the previous fixes round, 10 in
Phase A). All tests run against temporary copies; the real
`database.db` is never opened by the test suite.

### 4.2 Live server check (temporary copy, port 5000)

- Log: `Debug mode: off`, `Running on http://127.0.0.1:5000`.
- `GET /` → 200 (47,364 bytes); `GET /admin` → 302;
  `GET /match/123` → 200.
- Homepage: 25 RSS cards, "Senora" occurs 0 times.
- Server stopped afterwards; no server left running.

### 4.3 Database — before/after (working copy, read-only queries)

| Check | Before this fix | After this fix |
|---|---|---|
| `PRAGMA integrity_check` | ok | ok |
| `news` rows | 2 | 2 |
| `rss_items` rows | 254 | 254 |
| region `review` | 136 | 136 |
| region `bangladesh` | 2 | 2 |
| region `international` | 116 | 116 |
| rss_items id 1173 region | review | review |
| news id 2 category | TRANSFERS | TRANSFERS |
| duplicate links | 0 | 0 |
| `schema_migrations` | 001, 002 | 001, 002 |

No migration was run on the working database for this fix (none
was needed — the fix is code, not data).

### 4.4 Original backup preservation

- All 8 `database_before_*.db` snapshots preserved in the ZIP.
- Pre-migration backup `backend/backups/database-20261115-084946.db`
  (SHA-256 `239b51b1370f3ae500bb605a42747fa7858f88780d646e7cf6bde46a06ea9380`)
  + `backups/manifest-sha256.txt` preserved in the ZIP.
- The original uploaded ZIP and both V9 PDFs verify unchanged by
  SHA-256 (see §2).

### 4.5 ZIP self-check

The new ZIP was built from the working copy only: 60 files under
`backend/`, no `__pycache__`, no `.env`, no secrets (only
environment-variable names in code and placeholder examples in
README). SHA-256 as in §2.

## 5. Known issues (unchanged from Phase A)

- `/api/live` and `/api/match` return 500 without an
  API-Football key (none supplied, none stored; original behaviour).
- Only 17 of 84 existing Bangladesh-feed rows match the strict URL
  paths, so future Bangladesh-feed intake will be much smaller.
- RSS relevance is still a simple keyword count; no verification /
  writing / SEO / publishing code exists yet (later phases).
- `published_at` is still a raw feed string; no RSS retry/backoff;
  API cache is in-memory only.

## 6. Question for ChatGPT (independent final review)

Please check the updated source in `phase-a-source/` and the new
ZIP `Insight-Football-PhaseA-Fixes2.zip` (SHA-256 in §2) and give
one decision: ACCEPT / CONDITIONAL ACCEPT / REJECT for Phase A.
In particular: is the backup now an exact pre-run snapshot —
made and SHA-verified before ANY migration-runner database write,
including the `schema_migrations` table creation? Do not approve
Phase B/C/D/E, do not invent Errata Part 1 / `cie_guard` /
missing V9 SQL. Originals must stay untouched.
