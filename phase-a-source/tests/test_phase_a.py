"""Phase A tests for Insight Football (IF-MASTER-2026).

Run from the backend/ directory:
    python3 -m unittest discover -s tests -v

Safety: every test runs against a TEMPORARY COPY of this backend
directory (created in the system temp area). The real database.db
in this folder is never opened by these tests, and no test inserts
into it. The temporary copy excludes __pycache__, backups/ and the
database_before_*.db snapshots (they are not needed for these tests).

Tests cover Phase A only:
  - homepage shows RSS items in the four categories, each link once
  - category rendering (Transfer row now matches 'TRANSFERS')
  - /admin requires login; unauthenticated GET/POST are redirected
  - login fails closed when ADMIN_PASSWORD is not set
  - login with ADMIN_PASSWORD works, then an admin POST inserts news
  - admin POST without a CSRF token is rejected (403)
  - /api/live and /api/match return the original 500 behaviour
    when no API_FOOTBALL_KEY is set (no key is used in these tests)
  - database counts and integrity on the test copy

No network access is used: the live-score tests only check the
no-API-key path, and no RSS fetch is performed.
"""

import importlib
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def load_app():
    """Import (or reload) the app module from the current directory."""
    if "app" in sys.modules:
        return importlib.reload(sys.modules["app"])
    return importlib.import_module("app")


class PhaseATestCase(unittest.TestCase):
    def setUp(self):
        self._old_cwd = Path.cwd()
        self._old_env = dict(os.environ)
        self.tmp = Path(tempfile.mkdtemp(prefix="insight-phase-a-test-"))
        shutil.copytree(
            BACKEND_DIR,
            self.tmp / "backend",
            ignore=shutil.ignore_patterns(
                "__pycache__", "backups", "database_before_*.db", ".venv",
            ),
        )
        self.workdir = self.tmp / "backend"
        os.chdir(self.workdir)
        os.environ["FLASK_SECRET_KEY"] = "test-secret-key-for-phase-a"
        os.environ["ADMIN_PASSWORD"] = "test-admin-password"
        os.environ.pop("API_FOOTBALL_KEY", None)
        sys.path.insert(0, str(self.workdir))
        self.app_module = load_app()
        self.app_module.app.config["TESTING"] = True
        self.client = self.app_module.app.test_client()

    def tearDown(self):
        if "app" in sys.modules:
            del sys.modules["app"]
        sys.path = [p for p in sys.path if p != str(self.workdir)]
        os.chdir(self._old_cwd)
        os.environ.clear()
        os.environ.update(self._old_env)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def login(self):
        return self.client.post(
            "/login",
            data={"password": "test-admin-password"},
            follow_redirects=True,
        )

    def test_home_shows_rss_in_categories_no_duplicates(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        # News rows (manual admin content) are still shown.
        self.assertIn("Welcome to Insight Football", html)
        self.assertIn("Manchester City Transfer Update", html)
        # RSS items appear in their category sections.
        self.assertIn("Transfer Centre LIVE!", html)  # Transfers (RSS)
        self.assertIn("Messi wins second MLS Golden Boot", html)  # World (RSS)
        self.assertIn("Timely lift as SAFF stakes rise", html)  # Bangladesh (RSS)
        # Senora row is region='review' after migration 002, so it is
        # shown in World, not in Bangladesh.
        self.assertIn("Senora to run 14 pad dispensers", html)
        self.assertIn('(RSS)', html)
        # Category headings are all rendered with content now.
        for heading in ("WORLD FOOTBALL", "TRANSFER CENTRE",
                        "INTERNATIONAL FOOTBALL", "BANGLADESH FOOTBALL"):
            self.assertIn(heading, html)

    def test_rss_links_appear_once(self):
        resp = self.client.get("/")
        html = resp.get_data(as_text=True)
        conn = sqlite3.connect(self.workdir / "database.db")
        rows = conn.execute(
            "SELECT link FROM rss_items "
            "WHERE relevance_status='relevant' AND status='recent'"
        ).fetchall()
        conn.close()
        shown = 0
        for (link,) in rows:
            # Count the card link only (href="..."). The raw URL can also
            # occur inside an item's summary text (e.g. a Guardian
            # "Continue reading..." anchor stored in the summary), which
            # is not a second display of the article.
            count = html.count(f'href="{link}"')
            self.assertIn(count, (0, 1),
                          f"link shown {count} times (expected 0 or 1): {link}")
            if count == 1:
                shown += 1
        # At most 20 per category are shown, so shown <= 80, and at
        # least the 3 Bangladesh + 1 Transfer + 2 World items appear.
        self.assertGreaterEqual(shown, 6)
        self.assertLessEqual(shown, 80)

    def test_admin_get_unauthenticated_redirects_to_login(self):
        resp = self.client.get("/admin")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])

    def test_admin_post_unauthenticated_redirects_to_login(self):
        resp = self.client.post("/admin", data={"title": "x", "content": "y"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])

    def test_login_fails_closed_without_admin_password(self):
        del os.environ["ADMIN_PASSWORD"]
        importlib.reload(self.app_module)
        self.app_module.app.config["TESTING"] = True
        self.client = self.app_module.app.test_client()
        resp = self.client.post("/login", data={"password": "anything"})
        self.assertEqual(resp.status_code, 503)
        self.assertIn("not configured", resp.get_data(as_text=True))
        # Still locked out of /admin afterwards.
        self.assertEqual(self.client.get("/admin").status_code, 302)

    def test_login_then_admin_post_inserts_news(self):
        resp = self.login()
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Admin News Dashboard", resp.get_data(as_text=True))
        conn = sqlite3.connect(self.workdir / "database.db")
        before = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]
        conn.close()
        self.assertEqual(before, 2)
        admin_page = self.client.get("/admin").get_data(as_text=True)
        token = re.search(r'name="csrf_token" value="([^"]+)"', admin_page).group(1)
        post = self.client.post("/admin", data={
            "csrf_token": token,
            "title": "Phase A Test Article",
            "category": "TRANSFERS",
            "content": "Test content written by the Phase A test suite.",
            "source": "Phase A tests",
            "image_url": "",
        }, follow_redirects=False)
        self.assertEqual(post.status_code, 302)
        conn = sqlite3.connect(self.workdir / "database.db")
        after = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]
        row = conn.execute(
            "SELECT title, category FROM news WHERE title='Phase A Test Article'"
        ).fetchone()
        conn.close()
        self.assertEqual(after, 3)
        self.assertEqual(row, ("Phase A Test Article", "TRANSFERS"))

    def test_admin_post_without_csrf_is_rejected(self):
        self.login()
        resp = self.client.post("/admin", data={
            "title": "No token article",
            "category": "TRANSFERS",
            "content": "Should be rejected.",
        })
        self.assertEqual(resp.status_code, 403)
        conn = sqlite3.connect(self.workdir / "database.db")
        count = conn.execute(
            "SELECT COUNT(*) FROM news WHERE title='No token article'"
        ).fetchone()[0]
        conn.close()
        self.assertEqual(count, 0)

    def test_logout_locks_admin_again(self):
        self.login()
        self.assertEqual(self.client.get("/admin").status_code, 200)
        self.client.get("/logout")
        self.assertEqual(self.client.get("/admin").status_code, 302)

    def test_api_endpoints_without_key_return_500(self):
        live = self.client.get("/api/live")
        self.assertEqual(live.status_code, 500)
        self.assertIn("API key not configured", live.get_data(as_text=True))
        match = self.client.get("/api/match/123")
        self.assertEqual(match.status_code, 500)
        self.assertIn("API key not configured", match.get_data(as_text=True))
        # The match page itself renders without a key.
        self.assertEqual(self.client.get("/match/123").status_code, 200)

    def test_database_counts_and_integrity(self):
        conn = sqlite3.connect(self.workdir / "database.db")
        self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone(), ("ok",))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM news").fetchone()[0], 2)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM rss_items").fetchone()[0], 254)
        self.assertEqual(
            conn.execute("SELECT category FROM news WHERE id=2").fetchone()[0],
            "TRANSFERS")
        self.assertEqual(
            conn.execute("SELECT region FROM rss_items WHERE id=1173").fetchone()[0],
            "review")
        conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
