# Backup and rollback — Insight Football, Phase A (IF-MASTER-2026)

## Rule

Never work without a backup. Before every migration, a timestamped
copy of `database.db` is made in `backend/backups/` and its SHA-256
is appended to `backend/backups/manifest-sha256.txt`. Backups are
never overwritten. The original uploaded ZIP is the ultimate fallback;
its SHA-256 is `b757e5e0ba941eeb1469445405b259006c7dbd9a595958e83dd9ca24c43efc28`.

The 8 original `database_before_*.db` snapshots are preserved
untouched. Do not delete them.

## How to back up (any time)

Run from the `backend/` directory:

```
python3 backup.py
```

Expected output (paths and hashes will differ):

```
Backup created: .../backend/backups/database-20261115-090000.db
Backup SHA-256: <64 hex characters>
Manifest updated: .../backend/backups/manifest-sha256.txt
```

Verify a backup before relying on it:

```
sha256sum backend/backups/database-<timestamp>.db
# compare with the matching line in backend/backups/manifest-sha256.txt
python3 -c "import sqlite3; c=sqlite3.connect('backend/backups/database-<timestamp>.db'); print(c.execute('PRAGMA integrity_check').fetchone()); print(c.execute('SELECT COUNT(*) FROM rss_items').fetchone())"
# expected: ('ok',) and (254,)
```

## How to migrate (Phase A)

Run from the `backend/` directory:

```
python3 migrations/run_migrations.py
```

The runner first makes a backup (as above), then applies pending
`migrations/*.sql` files in filename order, recording each one in
the `schema_migrations` table. A second run is a safe no-op.

Dry run (lists pending migrations, changes nothing, makes no backup):

```
python3 migrations/run_migrations.py --dry-run
```

Dry run is genuinely read-only: the runner opens the database
with SQLite URI `mode=ro`, so it cannot write even by accident.
No `schema_migrations` table is created, no backup is made, no
migration is applied and no file is created or changed. This was
a ChatGPT review finding — the first Phase A runner created the
`schema_migrations` table before checking `--dry-run`. Verified by
`tests/test_migrations.py`: file SHA-256 and the full schema dump
are identical before and after a dry run, including on a database
that has no `schema_migrations` table at all.

## Migration failure and rollback behaviour (verified)

Each migration is applied atomically: all of its statements plus
its `schema_migrations` record run inside one explicit
BEGIN ... COMMIT transaction (the runner splits the SQL file into
statements instead of using `executescript`, which in Python 3.12
implicitly commits first and is therefore not atomic — verified by
experiment 2026-11-15: a failed `executescript` left its first
UPDATE applied even after `rollback()`).

- If a migration fails, that migration is rolled back in full:
  none of its statements persist, and it is NOT recorded in
  `schema_migrations`, so a fixed re-run will try it again.
- The runner STOPS immediately and returns exit code 1. Later
  migrations are NOT attempted.
- Migrations applied BEFORE the failure stay applied and recorded.
  There is no whole-run rollback. If that state is unwanted,
  restore the pre-run backup (step 3 under "Full restore" below);
  the backup is listed in the failure message.
- The `schema_migrations` table itself is created (if missing) and
  committed before the loop, so a failure never leaves the runner
  unable to record what happened.

Failure-injection tests in `tests/test_migrations.py` prove this
on a temporary database: a two-statement migration whose second
statement fails leaves no trace (first statement rolled back, not
recorded), and a run with a good migration followed by a bad one
applies and records only the good one and never attempts the one
after the bad one.

## Rollback — migration 001 (`001_create_rss_items_table.sql`)

No rollback is needed or provided. The migration only runs
`CREATE TABLE IF NOT EXISTS rss_items`. On the live database the
table already existed, so it changed nothing. Do NOT drop
`rss_items`: it holds 254 collected items.

## Rollback — migration 002 (`002_fix_category_and_senora.sql`)

This migration changed exactly two values. To undo it, first back
up the current database (`python3 backup.py`), then run:

```sql
UPDATE news SET category = 'TRANSFER NEWS' WHERE id = 2;
UPDATE rss_items SET region = 'bangladesh' WHERE id = 1173;
```

Verify afterwards:

```sql
SELECT id, title, category FROM news WHERE id = 2;
-- expected: 2 | Manchester City Transfer Update | TRANSFER NEWS
SELECT id, region FROM rss_items WHERE id = 1173;
-- expected: 1173 | bangladesh
SELECT COUNT(*) FROM news;       -- expected: 2
SELECT COUNT(*) FROM rss_items;  -- expected: 254
```

## Full restore (if a database is damaged)

1. Stop the Flask app.
2. Back up the damaged file first, so nothing is lost:
   `cp database.db database-damaged-<date>.db`
3. Copy the newest good backup over it:
   `cp backend/backups/database-<timestamp>.db database.db`
4. Verify: `PRAGMA integrity_check` must return `ok`, and
   `SELECT COUNT(*) FROM rss_items` must return 254.
5. Re-run migrations if the restored backup predates them:
   `python3 migrations/run_migrations.py`

## Code rollback (app.py / templates / rss_collector.py)

Phase A changed only the working copy. The pristine originals are
kept separately by the developer (original-extract). To undo a code
change, restore that single file from the pristine copy and restart
the app. Do not copy a database file over a code file or vice versa.
