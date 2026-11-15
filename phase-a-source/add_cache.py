from pathlib import Path

path = Path("app.py")
content = path.read_text()

if "import time" in content and "api_cache = {}" in content:
    print("Cache already exists.")
else:
    content = content.replace(
        "import requests",
        "import requests\nimport time",
        1
    )

    marker = 'API_URL = "https://v3.football.api-sports.io"'

    addition = '''

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
'''

    if marker not in content:
        print("ERROR: Insert location not found.")
    else:
        content = content.replace(marker, marker + addition, 1)
        path.write_text(content)
        print("SUCCESS: Cache system added.")
