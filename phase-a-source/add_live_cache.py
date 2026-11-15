from pathlib import Path

path = Path("app.py")
code = path.read_text()

old_start = '''    allowed_league_ids = {
        39, 140, 78, 135, 61,
        2, 3, 848, 1, 7, 30, 10
    }'''

new_start = '''    cache_key = "live_scores"
    cached_result = get_cached_data(cache_key, ttl=60)

    if cached_result is not None:
        return jsonify(cached_result)

    allowed_league_ids = {
        39, 140, 78, 135, 61,
        2, 3, 848, 1, 7, 30, 10
    }'''

old_return = '''        return jsonify({
            "success": True,
            "total": len(matches),
            "matches": matches
        })'''

new_return = '''        result = {
            "success": True,
            "total": len(matches),
            "matches": matches
        }

        save_cached_data(cache_key, result)
        return jsonify(result)'''

if code.count(old_start) != 1:
    print("ERROR: Live scores location not found.")
elif code.count(old_return) != 1:
    print("ERROR: Live scores return block not found.")
else:
    code = code.replace(old_start, new_start, 1)
    code = code.replace(old_return, new_return, 1)
    path.write_text(code)
    print("SUCCESS: Live Scores cache added!")