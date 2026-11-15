"""Phase A migration runner for Insight Football (IF-MASTER-2026).

Usage (run from the backend/ directory):
    python3 migrations/run_migrations.py
    python3 migrations/run_migrations.py --db database.db
    python3 migrations/run_migrations.py --db database.db --dry-run

What it does, in order:
  1. Backs up the database first, using backup.py logic: a timestamped
     copy in backend/backups/ plus a SHA-256 manifest entry. It never
     overwrites an existing backup.
  2. Applies every *.sql file in migrations/ in filename order, but
     only those not already recorded in the schema_migrations table.
  3. Records each applied migration (filename + SHA-256 + time) in
     schema_migrations, so a second run is a safe no-op.
  4. Prints before/after row counts for news and rss_items.

Safety:
  - It only runs the documented Phase A migrations in this folder.
  - It never deletes rows; the migrations themselves contain no DELETE.
  - If any migration fails, the transaction is rolled back and the
    pre-migration backup in backend/backups/ is the restore point.
    See BACKUP_AND_ROLLBACK.md for exact rollback steps.
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


def main():
    parser = argparse.ArgumentParser(description="Apply Phase A migrations.")
    parser.add_argument("--db", default="database.db",
                        help="Database file (default: database.db in backend/)")
    parser.add_argument("--dry-run", action="store_true",
                        help="List pending migrations without applying them.")
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

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " filename TEXT PRIMARY KEY, sha256 TEXT NOT NULL,"
            " applied_at TEXT NOT NULL)"
        )
        applied = {r[0] for r in conn.execute("SELECT filename FROM schema_migrations")}
        before = counts(conn)
        print(f"Before: news={before['news']} rss_items={before['rss_items']} "
              f"rss_review={before['rss_review']} rss_bangladesh={before['rss_bangladesh']}")

        pending = [p for p in sql_files if p.name not in applied]
        if not pending:
            print("No pending migrations. Database is up to date.")
            return 0
        print("Pending migrations:", [p.name for p in pending])
        if args.dry_run:
            print("Dry run: nothing was changed, no backup was made.")
            return 0

        backup_path = make_backup(db_path)

        for sql_file in pending:
            sql = sql_file.read_text(encoding="utf-8")
            digest = sha256_of(sql_file)
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations (filename, sha256, applied_at)"
                " VALUES (?, ?, ?)",
                (sql_file.name, digest,
                 datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            print(f"Applied: {sql_file.name} (sha256 {digest[:16]}...)")

        after = counts(conn)
        print(f"After: news={after['news']} rss_items={after['rss_items']} "
              f"rss_review={after['rss_review']} rss_bangladesh={after['rss_bangladesh']}")
        print(f"Backup kept at: {backup_path}")
        print("Migrations applied successfully.")
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"ERROR: migration failed, rolled back: {exc}", file=sys.stderr)
        print("Restore the backup listed above if needed. "
              "See BACKUP_AND_ROLLBACK.md.", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
