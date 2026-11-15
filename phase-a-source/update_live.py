import re

with open("app.py", "r") as f:
    code = f.read()

new_route = '''@app.route("/api/live")
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


'''

pattern = r'@app\.route\("/api/live"\)\s+def live_scores\(\):.*?(?=\nif __name__ == "__main__":)'
updated, count = re.subn(pattern, lambda m: new_route.rstrip(), code, count=1, flags=re.S)

if count != 1:
    print("ERROR: Live route not found. Original file unchanged.")
else:
    with open("app.py", "w") as f:
        f.write(updated)
    print("SUCCESS: Live score filter updated.")