"""Mocked Live Football API tests for Insight Football (IF-MASTER-2026).

Run from the backend/ directory:
    python3 -m unittest discover -s tests -v

Covers the ChatGPT review finding on the Live Football API:
the existing /api/live and /api/match/<id> routes are preserved
exactly as written (no route was replaced or redesigned); these
tests only mock requests.get so the routes can be exercised
without a real API-Football key or network access.

Covered: successful /api/live (including its league filter and
the Bangladesh team exception), successful /api/match/<id>,
empty results, API error responses, connection timeouts, invalid
JSON, and the in-memory cache (a second identical match request
does not call the API again).

No real API key is used anywhere: the tests set
API_FOOTBALL_KEY to the literal fake value "test-api-key-fake"
in the environment of the temporary test copy only.
"""

import importlib
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import requests

BACKEND_DIR = Path(__file__).resolve().parent.parent


def load_app():
    if "app" in sys.modules:
        return importlib.reload(sys.modules["app"])
    return importlib.import_module("app")


def mock_response(payload, status_code=200):
    resp = mock.Mock()
    resp.status_code = status_code
    resp.raise_for_status.return_value = None
    resp.json.return_value = payload
    return resp


def fixture_item(fixture_id=123, league_id=39, league_name="Premier League",
                 home_id=42, home_name="Arsenal",
                 away_id=49, away_name="Chelsea",
                 home_goals=2, away_goals=1, elapsed=67, status="2H"):
    """One match dict, as it appears inside an API "response" list."""
    return {
        "fixture": {"id": fixture_id,
                    "status": {"elapsed": elapsed, "short": status}},
        "league": {"id": league_id, "name": league_name,
                   "country": "England"},
        "teams": {"home": {"id": home_id, "name": home_name,
                           "logo": "https://example.invalid/home.png"},
                  "away": {"id": away_id, "name": away_name,
                           "logo": "https://example.invalid/away.png"}},
        "goals": {"home": home_goals, "away": away_goals},
    }


def fixture_payload(*items):
    """Full API envelope ({"errors": [], "response": [...]}).

    Called with no arguments it returns one default fixture, so
    test_match_success can keep calling fixture_payload() as before.
    """
    if not items:
        items = (fixture_item(),)
    return {"errors": [], "response": list(items)}


class LiveApiTestCase(unittest.TestCase):
    def setUp(self):
        self._old_cwd = Path.cwd()
        self._old_env = dict(os.environ)
        self.tmp = Path(tempfile.mkdtemp(prefix="insight-live-api-test-"))
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
        # Fake key only: makes the routes reach the mocked requests.get.
        os.environ["API_FOOTBALL_KEY"] = "test-api-key-fake"
        sys.path.insert(0, str(self.workdir))
        self.app_module = load_app()
        self.app_module.api_cache.clear()
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

    def get(self, url):
        return self.client.get(url)

    # /api/live

    def test_live_success_filters_leagues(self):
        payload = {
            "errors": [],
            "response": [
                fixture_item(fixture_id=1, league_id=39),   # allowed
                fixture_item(fixture_id=2, league_id=999,
                             league_name="Obscure League",
                             home_name="Team A", away_name="Team B"),
                fixture_item(fixture_id=3, league_id=999,
                             league_name="Obscure League",
                             home_id=1560, home_name="Bangladesh",
                             away_name="Team C"),  # Bangladesh exception
                fixture_item(fixture_id=4, league_id=140,
                             league_name="La Liga",
                             home_name="Real Madrid",
                             away_name="Valencia"),
            ],
        }
        with mock.patch.object(
                self.app_module.requests, "get",
                return_value=mock_response(payload)) as mock_get:
            resp = self.get("/api/live")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total"], 3)
        ids = [m["id"] for m in data["matches"]]
        self.assertEqual(ids, [1, 3, 4])
        self.assertEqual(data["matches"][0]["home"], "Arsenal")
        self.assertEqual(data["matches"][0]["home_score"], 2)
        mock_get.assert_called_once()

    def test_live_empty_results(self):
        with mock.patch.object(
                self.app_module.requests, "get",
                return_value=mock_response({"errors": [], "response": []})):
            resp = self.get("/api/live")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["matches"], [])

    def test_live_api_error_response(self):
        payload = {"errors": {"token": "Invalid API key"},
                   "response": []}
        with mock.patch.object(
                self.app_module.requests, "get",
                return_value=mock_response(payload)):
            resp = self.get("/api/live")
        self.assertEqual(resp.status_code, 502)
        self.assertFalse(resp.get_json()["success"])

    def test_live_connection_timeout(self):
        with mock.patch.object(
                self.app_module.requests, "get",
                side_effect=requests.exceptions.ConnectTimeout("timed out")):
            resp = self.get("/api/live")
        self.assertEqual(resp.status_code, 502)
        self.assertIn("connection failed", resp.get_data(as_text=True))

    def test_live_invalid_json(self):
        bad = mock.Mock()
        bad.raise_for_status.return_value = None
        bad.json.side_effect = ValueError("not JSON")
        with mock.patch.object(
                self.app_module.requests, "get", return_value=bad):
            resp = self.get("/api/live")
        self.assertEqual(resp.status_code, 502)
        self.assertIn("Invalid API response", resp.get_data(as_text=True))

    # /api/match/<id>

    def test_match_success(self):
        events = mock_response({
            "errors": [],
            "response": [{"time": {"elapsed": 23}, "team": {"name": "Arsenal"},
                          "player": {"name": "Saka"}, "type": "Goal"}],
        })
        with mock.patch.object(
                self.app_module.requests, "get",
                side_effect=[mock_response(fixture_payload()),
                             events]) as mock_get:
            resp = self.get("/api/match/123")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["match"]["home"], "Arsenal")
        self.assertEqual(data["match"]["away"], "Chelsea")
        self.assertEqual(data["match"]["league"], "Premier League")
        self.assertEqual(data["match"]["home_score"], 2)
        self.assertEqual(data["match"]["elapsed"], 67)
        self.assertEqual(len(data["events"]), 1)
        self.assertEqual(data["events"][0]["type"], "Goal")
        self.assertIsInstance(data["related_news"], list)
        self.assertEqual(mock_get.call_count, 2)

    def test_match_success_uses_cache(self):
        events = mock_response({"errors": [], "response": []})
        with mock.patch.object(
                self.app_module.requests, "get",
                side_effect=[mock_response(fixture_payload()), events]) \
                as mock_get:
            first = self.get("/api/match/123")
            second = self.get("/api/match/123")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.get_json(), second.get_json())
        # Fixtures + events called once; the second request was cached.
        self.assertEqual(mock_get.call_count, 2)

    def test_match_not_found(self):
        with mock.patch.object(
                self.app_module.requests, "get",
                return_value=mock_response({"errors": [], "response": []})):
            resp = self.get("/api/match/999999")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("Match not found", resp.get_data(as_text=True))

    def test_match_api_error_response(self):
        payload = {"errors": {"requests": "rate limit"}, "response": []}
        with mock.patch.object(
                self.app_module.requests, "get",
                return_value=mock_response(payload)):
            resp = self.get("/api/match/123")
        self.assertEqual(resp.status_code, 502)
        self.assertIn("Football API error", resp.get_data(as_text=True))

    def test_match_events_api_error(self):
        events_error = mock_response(
            {"errors": {"events": "failed"}, "response": []})
        with mock.patch.object(
                self.app_module.requests, "get",
                side_effect=[mock_response(fixture_payload()),
                             events_error]):
            resp = self.get("/api/match/123")
        self.assertEqual(resp.status_code, 502)
        self.assertIn("Events API error", resp.get_data(as_text=True))

    def test_match_connection_timeout(self):
        with mock.patch.object(
                self.app_module.requests, "get",
                side_effect=requests.exceptions.ConnectTimeout("timed out")):
            resp = self.get("/api/match/123")
        self.assertEqual(resp.status_code, 502)
        self.assertIn("connection failed", resp.get_data(as_text=True))

    def test_match_invalid_json(self):
        bad = mock.Mock()
        bad.raise_for_status.return_value = None
        bad.json.side_effect = ValueError("not JSON")
        with mock.patch.object(
                self.app_module.requests, "get", return_value=bad):
            resp = self.get("/api/match/123")
        self.assertEqual(resp.status_code, 502)
        self.assertIn("Invalid API response", resp.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
