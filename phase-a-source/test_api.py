import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")
API_URL = "https://v3.football.api-sports.io"

response = requests.get(
    f"{API_URL}/fixtures",
    headers={"x-apisports-key": API_KEY},
    params={"live": "all"},
    timeout=20
)

data = response.json()
matches = data.get("response", [])

if matches:
    fixture_id = matches[0]["fixture"]["id"]

    print("Testing Fixture ID:", fixture_id)

    result = requests.get(
        f"{API_URL}/fixtures/events",
        headers={"x-apisports-key": API_KEY},
        params={"fixture": fixture_id},
        timeout=20
    )

    print("HTTP Status:", result.status_code)
    print("Events:", result.json())
else:
    print("No live matches available.")