
import os
import sqlite3
import requests

from flask import Flask, render_template, request, redirect, url_for, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("API_FOOTBALL_KEY")
API_URL = "https://v3.football.api-sports.io"


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


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

    conn.close()

    return render_template(
        "index.html",
        news=news,
        world_news=world_news,
        transfer_news=transfer_news,
        international_news=international_news,
        bangladesh_news=bangladesh_news
    )


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
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

    return render_template("admin.html")


@app.route("/api/live")
def live_scores():
    if not API_KEY:
        return jsonify({"success": False, "error": "API key not configured"}), 500

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

        return jsonify({
            "success": True,
            "total": len(matches),
            "matches": matches
        })

    except requests.RequestException:
        return jsonify({"success": False, "error": "Football API connection failed"}), 502
    except ValueError:
        return jsonify({"success": False, "error": "Invalid API response"}), 502
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
