import sqlite3

def create_database():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Phase A: the live database.db already has an `image_url` column on
    # `news`, but the original CREATE TABLE did not. Include it so a fresh
    # database matches the live one.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT,
            content TEXT NOT NULL,
            source TEXT,
            published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            image_url TEXT
        )
    """)

    # Phase A: `rss_items` was created by an unrecorded manual step, so a
    # fresh database had no such table and rss_collector.py failed on its
    # first INSERT. This CREATE TABLE matches the live schema exactly
    # (verified against database.db sqlite_master, 2026-11-15).
    # It never deletes or alters existing rows.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rss_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            feed_url TEXT,
            link TEXT NOT NULL UNIQUE,
            summary TEXT,
            published_at TEXT,
            image_url TEXT,
            collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'new',
            relevance_status TEXT DEFAULT 'pending',
            region TEXT DEFAULT 'review'
        )
    """)

    conn.commit()
    conn.close()

    print("Insight Football Database Created Successfully!")

if __name__ == "__main__":
    create_database()
