"""Migration runner tests for Insight Football (IF-MASTER-2026).

Run from the backend/ directory:
    python3 -m unittest discover -s tests -v

Covers the ChatGPT review findings on migrations/run_migrations.py:
  - --dry-run is genuinely read-only: file SHA-256 and the full
    schema dump are identical before and after, no backup is made,
    and no schema_migrations table is created on a database that
    has none.
  - a migration that fails mid-way is rolled back in full: none of
    its statements persist and it is not recorded.
  - a failure between migrations: earlier migrations stay applied
    and recorded, the failed one is not recorded, later ones are
    never attempted, and the runner exits non-zero.
  - a good migration applies, is recorded, and a second run is a
    no-op (validates the new atomic apply path end to end).

Safety: every test runs the runner as a subprocess against a
TEMPORARY COPY of this backend directory (created in the system
temp area). The real database.db in this folder is never touched.
Injected migration files exist only in the temporary copy. No
network access is used. No real API key is used anywhere.
"""

import hashlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def schema_dump(db_path):
    """Full schema + counts, for before/after comparison."""
    conn = sqlite3.connect(db_path)
    try:
        schema = conn.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "ORDER BY type, name, tbl_name"
        ).fetchall()
        counts = {
            "news": conn.execute("SELECT COUNT(*) FROM news").fetchone()[0],
            "rss_items": conn.execute(
                "SELECT COUNT(*) FROM rss_items").fetchone()[0],
        }
        migrations = []
        has_table = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type='table' AND name='schema_migrations'"
        ).fetchone()[0]
        if has_table:
            migrations = conn.execute(
                "SELECT filename FROM schema_migrations ORDER BY filename"
            ).fetchall()
        return {"schema": schema, "counts": counts, "migrations": migrations}
    finally:
        conn.close()


class MigrationRunnerTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="insight-migration-test-"))
        shutil.copytree(
            BACKEND_DIR,
            self.tmp / "backend",
            ignore=shutil.ignore_patterns(
                "__pycache__", "backups", "database_before_*.db", ".venv",
            ),
        )
        self.workdir = self.tmp / "backend"
        self.db_path = self.workdir / "database.db"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_runner(self, *args):
        return subprocess.run(
            [sys.executable, "migrations/run_migrations.py", *args],
            cwd=self.workdir,
            capture_output=True, text=True, timeout=60,
        )

    def inject_migration(self, filename, sql):
        path = self.workdir / "migrations" / filename
        path.write_text(sql, encoding="utf-8")
        return path

    def has_table(self, name):
        conn = sqlite3.connect(self.db_path)
        try:
            return bool(conn.execute(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE type='table' AND name=?", (name,)).fetchone()[0])
        finally:
            conn.close()

    def recorded(self, filename):
        conn = sqlite3.connect(self.db_path)
        try:
            return bool(conn.execute(
                "SELECT COUNT(*) FROM schema_migrations WHERE filename=?",
                (filename,)).fetchone()[0])
        finally:
            conn.close()

    def test_dry_run_is_read_only_with_pending_migration(self):
        self.inject_migration(
            "900_probe.sql",
            "CREATE TABLE IF NOT EXISTS dry_run_probe (id INTEGER);\n")
        before_sha = sha256_of(self.db_path)
        before = schema_dump(self.db_path)
        result = self.run_runner("--db", "database.db", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("900_probe.sql", result.stdout)
        self.assertIn("Dry run", result.stdout)
        # Nothing changed: same bytes, same schema, same counts.
        self.assertEqual(sha256_of(self.db_path), before_sha)
        self.assertEqual(schema_dump(self.db_path), before)
        # No backup was made.
        self.assertFalse((self.workdir / "backups").exists())
        # The probe table was not created.
        self.assertFalse(self.has_table("dry_run_probe"))

    def test_dry_run_does_not_create_schema_migrations_table(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DROP TABLE schema_migrations")
        conn.commit()
        conn.close()
        self.inject_migration(
            "900_probe.sql",
            "CREATE TABLE IF NOT EXISTS dry_run_probe (id INTEGER);\n")
        before_sha = sha256_of(self.db_path)
        before = schema_dump(self.db_path)
        result = self.run_runner("--db", "database.db", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("900_probe.sql", result.stdout)
        self.assertEqual(sha256_of(self.db_path), before_sha)
        self.assertEqual(schema_dump(self.db_path), before)
        # The old runner created this table before checking --dry-run.
        self.assertFalse(self.has_table("schema_migrations"))
        self.assertFalse((self.workdir / "backups").exists())

    def test_single_migration_failure_rolls_back_fully(self):
        self.inject_migration(
            "900_bad.sql",
            "CREATE TABLE failure_marker (id INTEGER);\n"
            "INSERT INTO no_such_table VALUES (1);\n")
        result = self.run_runner("--db", "database.db")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("900_bad.sql", result.stderr)
        # First statement rolled back: no trace of the migration.
        self.assertFalse(self.has_table("failure_marker"))
        self.assertFalse(self.recorded("900_bad.sql"))
        # Counts unchanged; a backup was still made as restore point.
        dump = schema_dump(self.db_path)
        self.assertEqual(dump["counts"], {"news": 2, "rss_items": 254})
        self.assertTrue((self.workdir / "backups").exists())
        self.assertTrue(list((self.workdir / "backups").glob("database-*.db")))

    def test_failure_between_migrations(self):
        self.inject_migration(
            "900_ok.sql",
            "CREATE TABLE ok_marker (id INTEGER);\n")
        self.inject_migration(
            "901_bad.sql",
            "CREATE TABLE bad_marker (id INTEGER);\n"
            "INSERT INTO no_such_table VALUES (1);\n")
        self.inject_migration(
            "902_later.sql",
            "CREATE TABLE later_marker (id INTEGER);\n")
        result = self.run_runner("--db", "database.db")
        self.assertNotEqual(result.returncode, 0)
        # Good migration applied and recorded.
        self.assertTrue(self.has_table("ok_marker"))
        self.assertTrue(self.recorded("900_ok.sql"))
        # Failed migration rolled back in full, not recorded.
        self.assertFalse(self.has_table("bad_marker"))
        self.assertFalse(self.recorded("901_bad.sql"))
        # Runner stopped: the migration after the failure was never
        # attempted, even though it is valid.
        self.assertFalse(self.has_table("later_marker"))
        self.assertFalse(self.recorded("902_later.sql"))
        # Earlier Phase A migrations are still recorded.
        self.assertTrue(self.recorded("001_create_rss_items_table.sql"))
        self.assertTrue(self.recorded("002_fix_category_and_senora.sql"))
        dump = schema_dump(self.db_path)
        self.assertEqual(dump["counts"], {"news": 2, "rss_items": 254})

    def test_good_migration_applies_and_second_run_is_noop(self):
        self.inject_migration(
            "900_ok.sql",
            "CREATE TABLE ok_marker (id INTEGER);\n")
        first = self.run_runner("--db", "database.db")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("Applied: 900_ok.sql", first.stdout)
        self.assertTrue(self.has_table("ok_marker"))
        self.assertTrue(self.recorded("900_ok.sql"))
        second = self.run_runner("--db", "database.db")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("No pending migrations", second.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
