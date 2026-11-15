import functools
import hmac
import os
import secrets
import sqlite3
import time

import requests
from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Secret key for Flask sessions (admin login + CSRF token).
# Phase A rule: never hardcode a secret. Use FLASK_SECRET_KEY when set.
# Without it, a random key is generated at each start, so admin sessions
# do not survive a restart. That is intentional fail-closed behaviour;
# set FLASK_SECRET_KEY for a stable production login (see README.md).
SECRET_KEY_FROM_ENV = bool(os.getenv("FLASK_SECRET_KEY"))
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(32)

API_KEY = os.getenv("API_FOOTBALL_KEY")
API_URL = "https://v3.football.api-sports.io"

# API response cache
api_cache = {}

def get_cached_data(key, ttl=30):
    now = time.time()
    cached = api_cache.get(key)

    if cached and now - cached["time"] < ttl:
        return cached["data"]

    return None

def save_cached_data(key, data):
    api_cache[key] = {
        "time": time.time(),
        "data": data
    }


def get_admin_password():
    """Admin password comes only from the ADMIN_PASSWORD env var.

    Returns None when it is not set. There is no default password:
    without ADMIN_PASSWORD, /admin login always fails closed.
    """
    return os.getenv("ADMIN_PASSWORD")


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# RSS items shown on the homepage. Phase A rule: read-only display, never
# copied into the `news` table, so no duplicate articles are created.
# Partition is disjoint by design, so each RSS item appears at most once:
#   bangladesh     -> region = 'bangladesh'
#   transfers      -> any other region, title contains 'transfer'
#   international  -> region = 'international', title has no 'transfer'
#   world          -> region = 'review', title has no 'transfer'
# (region='review' + a 'transfer' title goes to Transfers, not World.)
#
# Phase A fix (ChatGPT review): region='review' means "not classified
# as a football region", and it contains non-football stories (e.g.
# rss_items id 1173, the Senora business story, whose link is in a
# /business/ section). A review item is therefore shown as World
# Football ONLY when its link is in a football section
# (link LIKE '%/football/%'). The same football-link rule applies to
# Transfers, which also draws from the review pool. Non-football
# review rows stay in the database untouched -- they are excluded
# from display, never deleted -- and can be reclassified later.
# World after this fix shows 2 items (Messi Golden Boot, Real Madrid
# tribute); Senora appears in no football category.
RSS_BASE = "relevance_status = 'relevant' AND status = 'recent'"
RSS_FOOTBALL_LINK = "link LIKE '%/football/%'"
RSS_LIMIT = 20


@app.route("/")
def home():
    conn = get_db_connection()

    news = conn.execute(
        "SELECT * FROM news ORDER BY id DESC"
    ).fetchall()

    world_news = conn.execute(
        "SELECT * FROM news WHERE category = 'WORLD FOOTBALL' ORDER BY id DESC"
    ).fetchall()

    transfer_news = conn.execute(
        "SELECT * FROM news WHERE category = 'TRANSFERS' ORDER BY id DESC"
    ).fetchall()

    international_news = conn.execute(
        "SELECT * FROM news WHERE category = 'INTERNATIONAL FOOTBALL' ORDER BY id DESC"
    ).fetchall()

    bangladesh_news = conn.execute(
        "SELECT * FROM news WHERE category = 'BANGLADESH FOOTBALL' ORDER BY id DESC"
    ).fetchall()

    rss_world = conn.execute(
        "SELECT * FROM rss_items WHERE " + RSS_BASE +
        " AND region = 'review' AND lower(title) NOT LIKE '%transfer%'"
        " AND " + RSS_FOOTBALL_LINK +
        " ORDER BY id DESC LIMIT ?",
        (RSS_LIMIT,),
    ).fetchall()

    rss_transfers = conn.execute(
        "SELECT * FROM rss_items WHERE " + RSS_BASE +
        " AND region != 'bangladesh' AND lower(title) LIKE '%transfer%'"
        " AND " + RSS_FOOTBALL_LINK +
        " ORDER BY id DESC LIMIT ?",
        (RSS_LIMIT,),
    ).fetchall()

    rss_international = conn.execute(
        "SELECT * FROM rss_items WHERE " + RSS_BASE +
        " AND region = 'international' AND lower(title) NOT LIKE '%transfer%'"
        " ORDER BY id DESC LIMIT ?",
        (RSS_LIMIT,),
    ).fetchall()

    rss_bangladesh = conn.execute(
        "SELECT * FROM rss_items WHERE " + RSS_BASE +
        " AND region = 'bangladesh'"
        " ORDER BY id DESC LIMIT ?",
        (RSS_LIMIT,),
    ).fetchall()

    conn.close()

    return render_template(
        "index.html",
        news=news,
        world_news=world_news,
        transfer_news=transfer_news,
        international_news=international_news,
        bangladesh_news=bangladesh_news,
        rss_world=rss_world,
        rss_transfers=rss_transfers,
        rss_international=rss_international,
        rss_bangladesh=rss_bangladesh,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        configured_password = get_admin_password()
        if configured_password is None:
            # Fail closed: no ADMIN_PASSWORD configured, nobody can log in.
            error = "Admin login is not configured. Set the ADMIN_PASSWORD environment variable."
            return render_template("login.html", error=error), 503
        password = request.form.get("password", "")
        if hmac.compare_digest(password, configured_password):
            session.clear()
            session["admin_logged_in"] = True
            session["csrf_token"] = secrets.token_hex(16)
            next_page = request.args.get("next") or request.form.get("next") or url_for("admin")
            # Only allow a local redirect target, never an external URL.
            if not next_page.startswith("/") or next_page.startswith("//"):
                next_page = url_for("admin")
            return redirect(next_page)
        error = "Incorrect password."
    else:
        if get_admin_password() is None:
            error = "Admin login is not configured. Set the ADMIN_PASSWORD environment variable."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    if request.method == "POST":
        # Simple session CSRF check (Phase A, no extra dependency):
        # the form must carry the token issued at login.
        form_token = request.form.get("csrf_token", "")
        session_token = session.get("csrf_token", "")
        if not session_token or not hmac.compare_digest(form_token, session_token):
            abort(403)

        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        content = request.form.get("content", "").strip()
        source = request.form.get("source", "").strip()
        image_url = request.form.get("image_url", "").strip()

        if title and content:
            conn = get_db_connection()

            conn.execute(
                "INSERT INTO news (title, category, content, source, image_url) VALUES (?, ?, ?, ?, ?)",
                (title, category, content, source, image_url)
            )

            conn.commit()
            conn.close()

        return redirect(url_for("home"))

    return render_template("admin.html", csrf_token=session.get("csrf_token", ""))



@app.route("/match/<int:fixture_id>")
def match_page(fixture_id):
    return render_template("match.html", fixture_id=fixture_id)


@app.route("/api/match/<int:fixture_id>")
def match_details(fixture_id):
    if not API_KEY:
        return jsonify({"success": False, "error": "API key not configured"}), 500

    cache_key = f"match:{fixture_id}"
    cached_result = get_cached_data(cache_key, ttl=60)

    if cached_result is not None:
        return jsonify(cached_result)

    headers = {"x-apisports-key": API_KEY}

    try:
        fixture_response = requests.get(
            f"{API_URL}/fixtures",
            headers=headers,
            params={"id": fixture_id},
            timeout=20
        )
        fixture_response.raise_for_status()
        fixture_data = fixture_response.json()

        if fixture_data.get("errors"):
            return jsonify({"success": False, "error": "Football API error"}), 502

        fixtures = fixture_data.get("response", [])

        if not fixtures:
            return jsonify({"success": False, "error": "Match not found"}), 404

        item = fixtures[0]
        league = item.get("league", {})
        teams = item.get("teams", {})
        home = teams.get("home", {})
        away = teams.get("away", {})
        fixture = item.get("fixture", {})
        status = fixture.get("status", {})
        goals = item.get("goals", {})

        match = {
            "league": league.get("name", "Unknown"),
            "country": league.get("country") or "International",
            "home": home.get("name", "Unknown"),
            "away": away.get("name", "Unknown"),
            "home_logo": home.get("logo"),
            "away_logo": away.get("logo"),
            "home_score": goals.get("home"),
            "away_score": goals.get("away"),
            "elapsed": status.get("elapsed"),
            "status": status.get("short", "Unknown")
        }

        events_response = requests.get(
            f"{API_URL}/fixtures/events",
            headers=headers,
            params={"fixture": fixture_id},
            timeout=20
        )
        events_response.raise_for_status()
        events_data = events_response.json()

        if events_data.get("errors"):
            return jsonify({"success": False, "error": "Events API error"}), 502

        events = events_data.get("response", [])

        conn = get_db_connection()
        related_news = conn.execute(
            """
            SELECT title, content, source
            FROM news
            WHERE title LIKE ?
               OR content LIKE ?
               OR title LIKE ?
               OR content LIKE ?
            ORDER BY id DESC
            LIMIT 10
            """,
            (
                "%" + match["home"] + "%",
                "%" + match["home"] + "%",
                "%" + match["away"] + "%",
                "%" + match["away"] + "%"
            )
        ).fetchall()
        conn.close()

        result = {
            "success": True,
            "match": match,
            "events": events,
            "related_news": [dict(row) for row in related_news]
        }

        save_cached_data(cache_key, result)
        return jsonify(result)

    except requests.RequestException:
        return jsonify({
            "success": False,
            "error": "Football API connection failed"
        }), 502

    except ValueError:
        return jsonify({
            "success": False,
            "error": "Invalid API response"
        }), 502


@app.route("/api/live")
def live_scores():
    if not API_KEY:
        return jsonify({"success": False, "error": "API key not configured"}), 500

    cache_key = "live_scores"
    cached_result = get_cached_data(cache_key, ttl=60)

    if cached_result is not None:
        return jsonify(cached_result)

    allowed_league_ids = {
        39, 140, 78, 135, 61,
        2, 3, 848, 1, 7, 30, 10
    }
    bangladesh_team_id = 1560

    try:
        response = requests.get(
            f"{API_URL}/fixtures",
            headers={"x-apisports-key": API_KEY},
            params={"live": "all"},
            timeout=20
        )
        response.raise_for_status()
        data = response.json()

        if data.get("errors"):
            return jsonify({"success": False, "error": data.get("errors")}), 502

        matches = []

        for match in data.get("response", []):
            league = match.get("league", {})
            teams = match.get("teams", {})
            home_team = teams.get("home", {})
            away_team = teams.get("away", {})

            league_id = league.get("id")
            home_id = home_team.get("id")
            away_id = away_team.get("id")

            if league_id not in allowed_league_ids and bangladesh_team_id not in (home_id, away_id):
                continue

            fixture = match.get("fixture", {})
            status = fixture.get("status", {})
            goals = match.get("goals", {})

            matches.append({
                "id": fixture.get("id"),
                "league": league.get("name", "Unknown"),
                "country": league.get("country") or "International",
                "home": home_team.get("name", "Unknown"),
                "away": away_team.get("name", "Unknown"),
                "home_logo": home_team.get("logo"),
                "away_logo": away_team.get("logo"),
                "home_score": goals.get("home"),
                "away_score": goals.get("away"),
                "elapsed": status.get("elapsed"),
                "status": status.get("short")
            })

        result = {
            "success": True,
            "total": len(matches),
            "matches": matches
        }

        save_cached_data(cache_key, result)
        return jsonify(result)

    except requests.RequestException:
        return jsonify({"success": False, "error": "Football API connection failed"}), 502
    except ValueError:
        return jsonify({"success": False, "error": "Invalid API response"}), 502
if __name__ == "__main__":
    if not SECRET_KEY_FROM_ENV:
        print("WARNING: FLASK_SECRET_KEY is not set. A random key is used, "
              "so admin sessions will not survive a restart. "
              "Set FLASK_SECRET_KEY for a stable login (see README.md).")
    if get_admin_password() is None:
        print("WARNING: ADMIN_PASSWORD is not set. Admin login is disabled "
              "until it is set. There is no default password.")
    # Phase A: localhost only, debug off. Never use debug=True on a
    # shared or public run.
    app.run(host="127.0.0.1", port=5000, debug=False)
