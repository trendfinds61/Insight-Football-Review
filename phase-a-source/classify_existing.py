import sqlite3
from rss_collector import classify_date

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("SELECT id, published_at FROM rss_items")
rows = cursor.fetchall()

counts = {"recent": 0, "old": 0, "review": 0}

for item_id, published_at in rows:
    status = classify_date(published_at)
    cursor.execute(
        "UPDATE rss_items SET status = ? WHERE id = ?",
        (status, item_id)
    )
    counts[status] += 1

conn.commit()
conn.close()

print("Classification completed!")
print("Recent:", counts["recent"])
print("Old:", counts["old"])
print("Review:", counts["review"])
