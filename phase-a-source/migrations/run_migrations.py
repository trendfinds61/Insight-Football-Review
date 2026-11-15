"""Phase A migration runner for Insight Football (IF-MASTER-2026).

Usage (run from the backend/ directory):
    python3 migrations/run_migrations.py
    python3 migrations/run_migrations.py --db database.db
    python3 migrations/run_migrations.py --db database.db --dry-run

What it does, in order:
  1. Backs up the database first, using backup.py logic: a timestamped
     copy in backend/backups/ plus a SHA-256 manifest entry. It never
     overwrites an existing backup. No backup is made when there is
     nothing pending, or in dry-run mode.
  2. Applies every *.sql file in migrations/ in filename order, but
     only those not already recorded in the schema_migrations table.
  3. Records each applied migration (filename + SHA-256 + time) in
     schema_migrations, so a second run is a safe no-op.
  4. Prints before/after row counts for news and rss_items.

Dry run (--dry-run) is genuinely read-only:
  - The database is opened with SQLite URI mode=ro, so the file
    cannot be written even by accident.
  - No schema_migrations table is created, no backup is made, no
    migration is applied, no file is created or changed.
  - It only reads: the pending-migration list and the before counts.
  - Verified by tests/test_migrations.py: file SHA-256 and the full
    schema dump are identical before and after a dry run, including
    on a database that has no schema_migrations table at all.

Failure and rollback behaviour (verified, see tests/test_migrations.py):
  - Each migration is applied ATOMICALLY: all of its statements plus
    its schema_migrations record are executed inside one explicit
    BEGIN ... COMMIT transaction, using a statement splitter
    (split_statements) instead of executescript. The old runner used
    executescript, which in Python 3.12 implicitly commits before
    running, so a failure in the middle of a multi-statement
    migration left the earlier statements applied -- the old
    docstring claim "the transaction is rolled back" was wrong for
    that case, and this runner fixes it.
  - If a migration fails, that migration is rolled back in full
    (none of its statements persist), it is NOT recorded in
    schema_migrations, the runner STOPS immediately and returns 1,
    and later migrations are NOT attempted.
  - Migrations applied BEFORE the failure stay applied and recorded.
    There is no whole-run rollback: a failure does not undo earlier
    migrations. If the resulting state is unwanted, restore the
    pre-run backup in backend/backups/ (see BACKUP_AND_ROLLBACK.md).
  - The schema_migrations bookkeeping table itself is created (if
    missing) and committed before the loop, so a failure never
    leaves the runner unable to record what happened.

Safety:
  - It only runs the documented Phase A migrations in this folder.
  - It never deletes rows; the migrations themselves contain no DELETE.
  - Run it only against a working copy, never against the original
    uploaded database. The original ZIP is the ultimate fallback.
"""

import argparse
import hashlib
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = Path(__file__).resolve().parent
BACKUPS_DIR = BACKEND_DIR / "backups"


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def split_statements(text):
    """Split SQL text into individual statements.

    Splits on ';' outside single-quoted strings and -- / /* */
    comments. Comment-only / empty chunks are dropped; a trailing
    chunk with real SQL but no ';' raises ValueError instead of
    being silently ignored. Leading comments stay attached to the
    statement that follows them, so they are harmless to execute.
    """
    stmts = []
    buf = []
    i = 0
    n = len(text)
    in_sq = in_lc = in_bc = False
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if in_lc:
            buf.append(ch)
            if ch == "\n":
                in_lc = False
            i += 1
            continue
        if in_bc:
            buf.append(ch)
            if ch == "*" and nxt == "/":
                buf.append(nxt)
                i += 2
                in_bc = False
                continue
            i += 1
            continue
        if in_sq:
            buf.append(ch)
            if ch == "'":
                if nxt == "'":
                    buf.append(nxt)
                    i += 2
                    continue
                in_sq = False
            i += 1
            continue
        if ch == "-" and nxt == "-":
            in_lc = True
            buf.append(ch)
            buf.append(nxt)
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_bc = True
            buf.append(ch)
            buf.append(nxt)
            i += 2
            continue
        if ch == "'":
            in_sq = True
            buf.append(ch)
            i += 1
            continue
        if ch == ";":
            buf.append(ch)
            stmt = "".join(buf).strip()
            buf = []
            body = [ln for ln in stmt.splitlines()
                    if ln.strip() and not ln.strip().startswith("--")]
            if body:
                stmts.append(stmt)
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        body = [ln for ln in tail.splitlines()
                if ln.strip() and not ln.strip().startswith("--")]
        if body:
            raise ValueError(f"unterminated statement (missing ';'): {tail!r}")
    return stmts


def make_backup(db_path):
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUPS_DIR / f"database-{stamp}.db"
    counter = 1
    while backup_path.exists():
        counter += 1
        backup_path = BACKUPS_DIR / f"database-{stamp}-{counter}.db"
    import shutil
    shutil.copy2(db_path, backup_path)
    digest = sha256_of(backup_path)
    manifest = BACKUPS_DIR / "manifest-sha256.txt"
    with open(manifest, "a", encoding="utf-8") as f:
        f.write(f"{digest}  {backup_path.name}  {stamp} UTC  {backup_path.stat().st_size} bytes\n")
    print(f"Backup created: {backup_path}")
    print(f"Backup SHA-256: {digest}")
    return backup_path


def counts(conn):
    out = {}
    for table in ("news", "rss_items"):
        out[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    out["rss_review"] = conn.execute(
        "SELECT COUNT(*) FROM rss_items WHERE region = 'review'"
    ).fetchone()[0]
    out["rss_bangladesh"] = conn.execute(
        "SELECT COUNT(*) FROM rss_items WHERE region = 'bangladesh'"
    ).fetchone()[0]
    return out


def read_applied(conn):
    """Filenames already recorded, without writing anything.

    Returns an empty set when the schema_migrations table does not
    exist yet (fresh database / dry run), instead of creating it.
    """
    row = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master "
        "WHERE type='table' AND name='schema_migrations'"
    ).fetchone()[0]
    if not row:
        return set()
    return {r[0] for r in conn.execute("SELECT filename FROM schema_migrations")}


def apply_migration(conn, sql_file):
    """Apply one migration atomically, including its record.

    All statements of the file plus the INSERT into
    schema_migrations run inside a single BEGIN ... COMMIT. On any
    error the whole migration is rolled back and the error is
    re-raised; the caller stops the run.
    """
    sql = sql_file.read_text(encoding="utf-8")
    digest = sha256_of(sql_file)
    statements = split_statements(sql)
    conn.execute("BEGIN")
    try:
        for stmt in statements:
            conn.execute(stmt)
        conn.execute(
            "INSERT INTO schema_migrations (filename, sha256, applied_at)"
            " VALUES (?, ?, ?)",
            (sql_file.name, digest,
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    print(f"Applied: {sql_file.name} (sha256 {digest[:16]}...) "
          f"({len(statements)} statement(s))")


def main():
    parser = argparse.ArgumentParser(description="Apply Phase A migrations.")
    parser.add_argument("--db", default="database.db",
                        help="Database file (default: database.db in backend/)")
    parser.add_argument("--dry-run", action="store_true",
                        help="List pending migrations without applying them. "
                             "Read-only: makes no backup and changes nothing.")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.is_absolute():
        db_path = (Path.cwd() / db_path).resolve()
    if not db_path.exists():
        print(f"ERROR: database file not found: {db_path}", file=sys.stderr)
        return 1

    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not sql_files:
        print("No migration files found.")
        return 0

    if args.dry_run:
        # Genuinely read-only: mode=ro opens the file without any
        # write capability. Nothing below this point writes: no
        # schema_migrations creation, no backup, no migration.
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            applied = read_applied(conn)
            before = counts(conn)
            print(f"Before: news={before['news']} rss_items={before['rss_items']} "
                  f"rss_review={before['rss_review']} rss_bangladesh={before['rss_bangladesh']}")
            pending = [p for p in sql_files if p.name not in applied]
            if not pending:
                print("No pending migrations. Database is up to date.")
                return 0
            print("Pending migrations:", [p.name for p in pending])
            print("Dry run: nothing was changed, no backup was made.")
            return 0
        finally:
            conn.close()

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " filename TEXT PRIMARY KEY, sha256 TEXT NOT NULL,"
            " applied_at TEXT NOT NULL)"
        )
        conn.commit()
        applied = {r[0] for r in conn.execute("SELECT filename FROM schema_migrations")}
        before = counts(conn)
        print(f"Before: news={before['news']} rss_items={before['rss_items']} "
              f"rss_review={before['rss_review']} rss_bangladesh={before['rss_bangladesh']}")

        pending = [p for p in sql_files if p.name not in applied]
        if not pending:
            print("No pending migrations. Database is up to date.")
            return 0
        print("Pending migrations:", [p.name for p in pending])

        backup_path = make_backup(db_path)

        for sql_file in pending:
            try:
                apply_migration(conn, sql_file)
            except Exception as exc:
                print(f"ERROR: migration {sql_file.name} failed, "
                      f"rolled back in full: {exc}", file=sys.stderr)
                print("Migrations applied before this failure stay applied. "
                      "Later migrations were NOT attempted. "
                      f"Restore the backup {backup_path} if needed. "
                      "See BACKUP_AND_ROLLBACK.md.", file=sys.stderr)
                return 1

        after = counts(conn)
        print(f"After: news={after['news']} rss_items={after['rss_items']} "
              f"rss_review={after['rss_review']} rss_bangladesh={after['rss_bangladesh']}")
        print(f"Backup kept at: {backup_path}")
        print("Migrations applied successfully.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
