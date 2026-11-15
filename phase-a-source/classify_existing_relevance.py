import sqlite3
from rss_collector import classify_relevance

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("SELECT id, title, summary FROM rss_items")

rows = cursor.fetchall()

counts = {
    "relevant": 0,
    "review": 0
}

for item_id, title, summary in rows:
    result = classify_relevance(title, summary)

    cursor.execute(
        "UPDATE rss_items SET relevance_status = ? WHERE id = ?",
        (result, item_id)
    )

    counts[result] += 1

conn.commit()
conn.close()

print("Classification completed!")
print("Relevant:", counts["relevant"])
print("Review:", counts["review"])
