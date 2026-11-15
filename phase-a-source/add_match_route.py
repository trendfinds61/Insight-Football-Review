file_path = "app.py"

with open(file_path, "r") as file:
    content = file.read()

marker = '@app.route("/api/live")'

if marker not in content:
    print("ERROR: Route location not found.")
    raise SystemExit

if '@app.route("/match/<int:fixture_id>")' in content:
    print("Match routes already exist.")
    raise SystemExit

route_code = '''
@app.route("/match/<int:fixture_id>")
def match_page(fixture_id):
    return render_template("match.html", fixture_id=fixture_id)


@app.route("/api/match/<int:fixture_id>")
def match_details(fixture_id):
    if not API_KEY:
        return jsonify({"success": False, "error": "API key not configured"}), 500

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

        return jsonify({
            "success": True,
            "match": match,
            "events": events,
            "related_news": [dict(row) for row in related_news]
        })

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


'''

content = content.replace(marker, route_code + marker, 1)

with open(file_path, "w") as file:
    file.write(content)

print("SUCCESS: Match routes added.")