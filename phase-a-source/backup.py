"""Safe backup script for Insight Football (Phase A, IF-MASTER-2026).

Usage (run from the backend/ directory):
    python3 backup.py
    python3 backup.py --db database.db

What it does:
  - Copies database.db to backend/backups/database-<UTC timestamp>.db
  - Appends the copy's SHA-256, timestamp and size to
    backend/backups/manifest-sha256.txt
  - Never overwrites an existing backup: if a file with the same
    timestamp name already exists, a -2, -3, ... suffix is added.
  - Prints the backup path and SHA-256 so it can be recorded.

It never modifies database.db, never deletes anything, and contains
no passwords or secrets. Keep the backups/ folder with the project;
it is the rollback point for every migration (see
BACKUP_AND_ROLLBACK.md). The 8 original database_before_*.db
snapshots shipped in the project are preserved untouched.
"""

import argparse
import hashlib
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
BACKUPS_DIR = BACKEND_DIR / "backups"


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Back up database.db safely.")
    parser.add_argument("--db", default="database.db",
                        help="Database file (default: database.db in backend/)")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.is_absolute():
        db_path = (Path.cwd() / db_path).resolve()
    if not db_path.exists():
        print(f"ERROR: database file not found: {db_path}", file=sys.stderr)
        return 1

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUPS_DIR / f"database-{stamp}.db"
    counter = 1
    while backup_path.exists():
        counter += 1
        backup_path = BACKUPS_DIR / f"database-{stamp}-{counter}.db"

    shutil.copy2(db_path, backup_path)
    digest = sha256_of(backup_path)
    manifest = BACKUPS_DIR / "manifest-sha256.txt"
    with open(manifest, "a", encoding="utf-8") as f:
        f.write(f"{digest}  {backup_path.name}  {stamp} UTC  {backup_path.stat().st_size} bytes\n")

    print(f"Backup created: {backup_path}")
    print(f"Backup SHA-256: {digest}")
    print(f"Manifest updated: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
