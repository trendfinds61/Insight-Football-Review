# Insight Football — Phase A Fixes Report (ChatGPT Review Findings)
Master Key: IF-MASTER-2026. Date: 2026-11-15. Status: fixes complete, awaiting ChatGPT re-review.

## 0. What this is

ChatGPT independently reviewed the actual Phase A source files in
`phase-a-source/` and did NOT approve Phase A yet. It raised 4
findings. This report fixes all 4, in the separate working copy
only. No Phase B, C, D or E work was done. No original file was
modified. After these corrections the work stops again for
ChatGPT's independent review.

## 1. Deliverables

| File | SHA-256 / note |
|---|---|
| `Insight-Football-PhaseA-Fixes.zip` (new ZIP, 60 files, 706,706 bytes) | `16f31a1ecd0b951bc10cc8d37500d9c9aa1b051967a2aba59a08063f3a796ebe` |
| `Insight-Football-PhaseA.zip` (original Phase A ZIP, unchanged) | `4e53c32e7361853b5e04bfc0048bdcc769ff737eb4a87c5f763b108a22968ab7` |
| Original project ZIP (unchanged) | `b757e5e0ba941eeb1469445405b259006c7dbd9a595958e83dd9ca24c43efc28` |
| V9 Final Report PDF (unchanged) | `3ee3eed448ffdc922800ee789a0c90d527a310709faf21285c88a77ad13b6ee1` |
| V9 Errata Part 2 PDF (unchanged) | `2fdd4d1d8aa53b846f8c85ddcd6c18bba7210060c2ac406c7d75d1789c5b6a71` |

Note on the location question ChatGPT raised: the Phase A report
says the ZIP lives in `hidden_files/phase-a/` — that is its path
on the developer's machine. The copy in GitHub sits at the
repository root. It is the same file: same name, same SHA-256
above. The new fixes ZIP is likewise at the repository root as
`Insight-Football-PhaseA-Fixes.zip`, and `phase-a-source/` now
matches the new ZIP's `backend/` contents exactly.

### Changed files vs the Phase A ZIP (6 changed, 2 added, 0 removed)

Changed:
- `backend/app.py` — World/Transfers football-link rule only
  (diff vs Phase A ZIP shows only the RSS queries + comment;
  the `/api/live` and `/api/match/<id>` routes are byte-identical)
- `backend/migrations/run_migrations.py` — rewritten dry-run +
  atomic apply (see §3, §4)
- `backend/tests/test_phase_a.py` — Senora regression test
- `backend/README.md` — World rule, dry-run, atomicity documented
- `backend/BACKUP_AND_ROLLBACK.md` — dry-run + failure behaviour
- `backend/SOURCE_AUDIT.md` — new §8, Phase A fixes

Added:
- `backend/tests/test_migrations.py` — dry-run + failure tests
- `backend/tests/test_live_api.py` — mocked Live API tests

## 2. Finding 1 — Senora / World Football classification: FIXED

Problem: moving the Senora business story (rss_items id 1173) to
region `review` was not enough, because the homepage showed every
relevant/recent review item as World Football — including that
business story.

Fix (`backend/app.py` only): a review item is shown as World
Football only when its link is in a football section
(`link LIKE '%/football/%'`). The same football-link rule now
applies to Transfers, which also draws from the review pool.
Non-football review rows stay in the database untouched — they
are excluded from display, never deleted — and can be
reclassified later.

Evidence (live server run on a temporary copy, port 5000,
`Debug mode: off`, `Running on http://127.0.0.1:5000`):
- Homepage `GET /` → 200, 47,364 bytes.
- RSS cards shown: 25 (was 26) = 20 International + 2 World +
  2 Bangladesh + 1 Transfer.
- World now shows exactly 2 items: "Messi wins second MLS Golden
  Boot" and "Real Madrid and Valencia honour Jesus de Miguel".
- "Senora" occurs 0 times in the homepage HTML (was 1 card).
- Regression test `test_senora_business_story_in_no_football_category`
  passes: the Senora title and its
  `https://www.dhakatribune.com/business/423945/...` link appear
  nowhere on the homepage, while the database row is preserved
  (id 1173, region `review`, counts unchanged: rss_items 254,
  review 136, bangladesh 2).

## 3. Finding 2 — Migration dry-run safety: FIXED

Problem: `run_migrations.py` created the `schema_migrations`
table before checking `--dry-run`, so a dry run wrote to the
database.

Fix (`backend/migrations/run_migrations.py`): in dry-run mode the
database is opened with SQLite URI `mode=ro`, so it cannot be
written even by accident. No `schema_migrations` table is
created, no backup is made, no migration is applied, no file is
created or changed. The runner only reads the pending list and
the before counts.

Evidence:
- Tests `test_dry_run_is_read_only_with_pending_migration` and
  `test_dry_run_does_not_create_schema_migrations_table` pass:
  file SHA-256 and the full schema dump are identical before and
  after a dry run, including on a database with no
  `schema_migrations` table at all, and no `backups/` directory
  is created.
- Dry run on the real working database (not a copy):
  SHA-256 before `267216bfc614f7b6c9327f38c82dbadb1f4af091d5bcca5666e34a791ec1d6ff`,
  after `267216bfc614f7b6c9327f38c82dbadb1f4af091d5bcca5666e34a791ec1d6ff`
  (identical), output `Before: news=2 rss_items=254 rss_review=136
  rss_bangladesh=2` / `No pending migrations. Database is up to date.`,
  no new backup file created.

## 4. Finding 3 — Migration failure safety: FIXED (and the old claim corrected)

Problem: the old runner's docstring said "if any migration fails,
the transaction is rolled back". That was wrong for a failure
inside a multi-statement migration.

Verified by experiment (Python 3.12.3, SQLite 3.45.1, 2026-11-15):
the old runner used `executescript`, which implicitly commits
before running. A test migration `UPDATE t SET v='b'; INSERT INTO
no_such_table ...` failed on the second statement, yet after
`rollback()` the first UPDATE was still applied (`v='b'`
persisted after reopening the database). So a mid-migration
failure left earlier statements applied and the migration
unrecorded.

Fix (`backend/migrations/run_migrations.py`): each migration is
split into individual statements by `split_statements` (splits
on `;` outside strings/comments; verified: 001 → 1 statement,
002 → 2 statements) and applied plus its `schema_migrations`
record inside one explicit `BEGIN ... COMMIT` transaction.
The same experiment with the new code leaves the table
unchanged (`v='a'`).

Accurate behaviour now (documented in the runner docstring,
`README.md` and `BACKUP_AND_ROLLBACK.md`):
- A failed migration rolls back in full: none of its statements
  persist, and it is NOT recorded, so a fixed re-run tries it again.
- The runner STOPS immediately and returns exit code 1; later
  migrations are NOT attempted.
- Migrations applied BEFORE the failure stay applied and recorded.
  There is no whole-run rollback. If that state is unwanted,
  restore the pre-run backup (listed in the failure message).
- The `schema_migrations` table is created and committed before
  the loop, so a failure never leaves the runner unable to record
  what happened.

Evidence — failure-injection tests on temporary databases
(`tests/test_migrations.py`, all pass):
- `test_single_migration_failure_rolls_back_fully`: a two-statement
  migration whose second statement fails leaves no trace (first
  statement's table absent, migration not recorded), counts
  unchanged (news 2, rss_items 254), and a backup was made.
- `test_failure_between_migrations`: good 900_ok applied and
  recorded, bad 901_bad rolled back and not recorded, valid
  902_later never attempted (table absent, not recorded),
  Phase A 001/002 still recorded.
- `test_good_migration_applies_and_second_run_is_noop`: the new
  atomic apply path works end to end and a second run is a no-op.

## 5. Finding 4 — Live Football API: mocked tests added, routes unchanged

The `/api/live` and `/api/match/<id>` routes were NOT replaced or
redesigned. A diff of `app.py` against the Phase A ZIP shows only
the RSS homepage queries and their comment (see §1). All tests
mock `requests.get`; no real API key is used anywhere (the fake
value `test-api-key-fake` exists only in the test process
environment) and no network access is used.

New file `backend/tests/test_live_api.py` — 12 tests, all pass:
- `test_live_success_filters_leagues`: 4 mocked fixtures → total 3
  (league 39 allowed, league 999 excluded, league 999 with
  Bangladesh team 1560 included via the Bangladesh exception,
  league 140 allowed).
- `test_live_empty_results`: empty response → 200, total 0.
- `test_live_api_error_response`: `errors` field → 502.
- `test_live_connection_timeout`: ConnectTimeout → 502
  "Football API connection failed".
- `test_live_invalid_json`: bad JSON → 502 "Invalid API response".
- `test_match_success`: mocked fixtures + events → 200, correct
  match fields, 1 event, `related_news` list.
- `test_match_success_uses_cache`: second identical request
  returns the cached result (API called twice total, not four).
- `test_match_not_found`: empty fixtures → 404 "Match not found".
- `test_match_api_error_response`: fixture `errors` → 502.
- `test_match_events_api_error`: events `errors` → 502.
- `test_match_connection_timeout`: ConnectTimeout → 502.
- `test_match_invalid_json`: bad JSON → 502.

## 6. Final verification

### 6.1 Full test suite — complete actual output

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
test_dry_run_does_not_create_schema_migrations_table (test_migrations.MigrationRunnerTestCase.test_dry_run_does_not_create_schema_migrations_table) ... ok
test_dry_run_is_read_only_with_pending_migration (test_migrations.MigrationRunnerTestCase.test_dry_run_is_read_only_with_pending_migration) ... ok
test_failure_between_migrations (test_migrations.MigrationRunnerTestCase.test_failure_between_migrations) ... ok
test_good_migration_applies_and_second_run_is_noop (test_migrations.MigrationRunnerTestCase.test_good_migration_applies_and_second_run_is_noop) ... ok
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
Ran 28 tests in 0.851s

OK
```

28 tests, 0 failures (was 10 tests in Phase A). All tests run
against temporary copies; the real `database.db` is never opened
by the test suite.

### 6.2 Live server check (temporary copy, port 5000)

- Log: `Debug mode: off`, `Running on http://127.0.0.1:5000`.
- `GET /` → 200 (47,364 bytes); `GET /admin` → 302 to
  `/login?next=/admin`; `GET /login` → 200; `GET /match/123` → 200.
- `GET /api/live` and `GET /api/match/123` → 500
  `{"success": false, "error": "API key not configured"}` — no key
  supplied, original behaviour, unchanged.
- Server stopped afterwards; no server left running.

### 6.3 Database — before/after (working copy, read-only queries)

| Check | Before fixes | After fixes |
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
| Homepage RSS cards | 26 | 25 (Senora card removed) |
| World RSS items | 3 | 2 |
| Senora occurrences on homepage | 1 | 0 |

No migration was run on the working database for these fixes
(none was needed — the fixes are code, not data). The working
database SHA-256 is unchanged by the dry-run check (§3).

### 6.4 Original backup preservation

- All 8 `database_before_*.db` snapshots preserved in the ZIP.
- Pre-migration backup `backend/backups/database-20261115-084946.db`
  + `backups/manifest-sha256.txt` preserved in the ZIP.
- Pristine originals (separate copy) differ from the working copy
  only in the Phase A changed/added files listed in §1; no other
  original file was touched. The original uploaded ZIP and both
  V9 PDFs verify unchanged by SHA-256 (see §1).

### 6.5 ZIP self-check

The new ZIP was extracted fresh and verified: 60 files under
`backend/`, no `__pycache__`, no `.env`, no secrets (only
environment-variable names in code and placeholder examples in
README). SHA-256 as in §1.

## 7. Known issues (unchanged from Phase A)

- `/api/live` and `/api/match` return 500 without an
  API-Football key (none supplied, none stored; original behaviour).
- Only 17 of 84 existing Bangladesh-feed rows match the strict URL
  paths, so future Bangladesh-feed intake will be much smaller.
- RSS relevance is still a simple keyword count; no verification /
  writing / SEO / publishing code exists yet (later phases).
- `published_at` is still a raw feed string; no RSS retry/backoff;
  API cache is in-memory only.

## 8. Questions for ChatGPT (independent re-review)

Please check the updated source in `phase-a-source/` and the new
ZIP `Insight-Football-PhaseA-Fixes.zip` (SHA-256 in §1) and give
one decision: ACCEPT / CONDITIONAL ACCEPT / REJECT for Phase A.
In particular: (1) does the Senora story appear in any football
category now; (2) is `--dry-run` genuinely read-only;
(3) is the migration failure/rollback behaviour correct and
accurately documented; (4) do the mocked Live API tests cover
the routes without changing them. Do not approve Phase B/C/D/E,
do not invent Errata Part 1 / `cie_guard` / missing V9 SQL.
Originals must stay untouched.
