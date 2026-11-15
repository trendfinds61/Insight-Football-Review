from pathlib import Path
import re

path = Path("app.py")
code = path.read_text()

old_header = '    headers = {"x-apisports-key": API_KEY}'

new_header = '''    cache_key = f"match:{fixture_id}"
    cached_result = get_cached_data(cache_key, ttl=60)

    if cached_result is not None:
        return jsonify(cached_result)

    headers = {"x-apisports-key": API_KEY}'''

old_return = '''        return jsonify({
            "success": True,
            "match": match,
            "events": events,
            "related_news": [dict(row) for row in related_news]
        })'''

new_return = '''        result = {
            "success": True,
            "match": match,
            "events": events,
            "related_news": [dict(row) for row in related_news]
        }

        save_cached_data(cache_key, result)
        return jsonify(result)'''

if code.count(old_header) != 1:
    print("ERROR: Header location not found exactly once.")
elif code.count(old_return) != 1:
    print("ERROR: Return block not found exactly once.")
else:
    code = code.replace(old_header, new_header, 1)
    code = code.replace(old_return, new_return, 1)
    path.write_text(code)
    print("SUCCESS: Match Centre cache added!")