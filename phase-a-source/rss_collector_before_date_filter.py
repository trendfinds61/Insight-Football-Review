import feedparser
import sqlite3

DB_NAME = "database.db"

FEEDS = [
    {
        "name": "BBC Sport",
        "url": "https://feeds.bbci.co.uk/sport/football/rss.xml"
    },
    {
        "name": "Sky Sports",
        "url": "https://www.skysports.com/rss/11095"
    },
    {
        "name": "The Guardian",
        "url": "https://www.theguardian.com/football/rss"
    }
]


def collect_news():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    total_added = 0
    total_images = 0

    for feed in FEEDS:
        print(f"\nChecking {feed['name']}...")

        parsed = feedparser.parse(feed["url"])

        print(f"News found: {len(parsed.entries)}")

        for item in parsed.entries:
            title = item.get("title", "").strip()
            link = item.get("link", "").strip()
            summary = item.get("summary", "")
            published = item.get("published", "")

            thumbnails = item.get("media_thumbnail", [])
            image_url = thumbnails[0].get("url", "") if thumbnails else ""

            if not image_url:
                media = item.get("media_content", [])
                if media:
                    image_url = media[0].get("url", "")
            if not image_url:
                for media_link in item.get("links", []):
                    if media_link.get("rel") == "enclosure" and media_link.get("type", "").startswith("image/"):
                        image_url = media_link.get("href", "")
                        break

            if not title or not link:
                continue

            cursor.execute(
                """
                INSERT OR IGNORE INTO rss_items
                (title, source, feed_url, link, summary, published_at, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    feed["name"],
                    feed["url"],
                    link,
                    summary,
                    published,
                    image_url
                )
            )

            if cursor.rowcount > 0:
                total_added += 1

            if image_url:
                cursor.execute(
                    """
                    UPDATE rss_items
                    SET image_url = ?
                    WHERE link = ?
                    AND (image_url IS NULL OR image_url = '')
                    """,
                    (image_url, link)
                )

                if cursor.rowcount > 0:
                    total_images += 1

    conn.commit()
    conn.close()

    print(f"\nNew news collected: {total_added}")
    print(f"Images saved or updated: {total_images}")


if __name__ == "__main__":
    collect_news()
