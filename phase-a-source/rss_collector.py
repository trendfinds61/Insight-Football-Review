import feedparser
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

DB_NAME = "database.db"


def classify_date(published):
    try:
        if not published:
            return "review"

        published_date = parsedate_to_datetime(published)

        if published_date.tzinfo is None:
            published_date = published_date.replace(
                tzinfo=timezone.utc
            )

        age = (
            datetime.now(timezone.utc) - published_date
        ).total_seconds()

        if age < 0:
            return "review"

        return "recent" if age <= 7 * 86400 else "old"

    except (TypeError, ValueError, OverflowError):
        return "review"


FOOTBALL_KEYWORDS = [
    "football", "soccer", "premier league", "champions league",
    "europa league", "la liga", "serie a", "bundesliga", "ligue 1",
    "fifa", "uefa", "world cup", "transfer", "striker", "goalkeeper",
    "manager", "coach", "match", "fixture", "goal", "penalty",
    "arsenal", "chelsea", "liverpool", "manchester united",
    "manchester city", "real madrid", "barcelona", "bayern munich",
    "psg", "ronaldo", "messi", "mbappe", "haaland", "neymar",
    "bangladesh football", "bangladesh national team",
    "bangladesh premier league", "bangladesh football league",
    "bangladesh women's football", "bangladesh women",
    "bangladesh u17", "bangladesh u-17",
    "bangladesh u20", "bangladesh u-20",
    "bangladesh u23", "bangladesh u-23",
    "bangladesh football federation", "bff",
    "bashundhara kings", "abahani", "abahani",
    "mohammedan sporting club", "mohammedan",
    "fortis fc", "rahmatganj", "brothers union",
    "saff", "saff", "saff championship",
    "hamza choudhury", "jamal bhuyan",
    "sheikh russel kc", "women's football bangladesh"
]


def classify_relevance(title, summary):
    text = (title or "") + " " + (summary or "")
    text = text.lower()

    matches = sum(
        1 for keyword in FOOTBALL_KEYWORDS
        if keyword in text
    )

    if matches >= 2:
        return "relevant"

    return "review"


def classify_region(title, summary, source, link):
    text = ((title or "") + " " + (summary or "")).lower()

    bangladesh_keywords = [
        "bangladesh football", "bangladesh national team",
        "bangladesh football federation", "bangladesh premier league",
        "bashundhara kings", "jamal bhuyan", "hamza choudhury",
        "abahani", "mohammedan sporting club", "fortis fc",
        "rahmatganj", "brothers union", "sheikh russel kc",
        "morsalin", "bangladesh vs bhutan",
        "bangladesh beat bhutan", "bangladesh defeat bhutan",
        "bangladesh national football team",
        "bangladesh women's national team"
    ]

    if any(keyword in text for keyword in bangladesh_keywords):
        return "bangladesh"

    if "saff championship" in text and "bangladesh" in text:
        return "bangladesh"

    # Phase A: the hardcoded Senora special case was removed. It forced a
    # Dhaka Tribune business story ("Senora to run 14 pad dispensers")
    # into region='bangladesh' even though it is not football news.
    # See migration 002, which corrects the one affected row
    # (rss_items id 1173) back to region='review'.
    if classify_relevance(title, summary) == "relevant":
        return "international"

    return "review"


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
    },
    {
        "name": "Dhaka Tribune Football",
        "url": "https://www.dhakatribune.com/feed/",
        "football_only": True,
        # Phase A: strict URL filter, exactly as SOURCE_AUDIT.md claims.
        # Only links under /sport/football/ are accepted from this feed.
        "football_url_path": "/sport/football/"
    },
    {
        "name": "The Daily Star Football",
        "url": "https://www.thedailystar.net/sports/rss.xml",
        "football_only": True,
        # Phase A: strict URL filter, exactly as SOURCE_AUDIT.md claims.
        # Only links under /sports/football/ are accepted from this feed.
        "football_url_path": "/sports/football/"
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
            title = BeautifulSoup(item.get("title", ""), "html.parser").get_text(" ", strip=True)
            link = item.get("link", "").strip()

            summary = item.get("summary", "")

            is_bangladesh_feed = feed.get("football_only", False)
            # Phase A: strict per-source URL filter (SOURCE_AUDIT.md).
            # Dhaka Tribune: only /sport/football/ ; Daily Star: only
            # /sports/football/ . Any other link from these mixed feeds is
            # skipped entirely. Existing rows in the database are NOT
            # deleted or changed by this; only future collection is affected.
            football_url_path = feed.get("football_url_path")
            if football_url_path:
                is_direct_football_url = football_url_path in link.lower()
            else:
                is_direct_football_url = "/football/" in link.lower()

            if is_bangladesh_feed and not is_direct_football_url:
                continue

            published = item.get("published", "")

            if not title or not link:
                continue

            thumbnails = item.get("media_thumbnail", [])
            image_url = (
                thumbnails[0].get("url", "")
                if thumbnails else ""
            )

            if not image_url:
                media = item.get("media_content", [])
                if media:
                    image_url = media[0].get("url", "")

            if not image_url:
                for media_link in item.get("links", []):
                    if (
                        media_link.get("rel") == "enclosure"
                        and media_link.get("type", "").startswith("image/")
                    ):
                        image_url = media_link.get("href", "")
                        break

            date_status = classify_date(published)
            if is_bangladesh_feed:
                if is_direct_football_url:
                    relevance_status = "relevant"
                    region = classify_region(title, summary, feed["name"], link)
                    if region == "review":
                        region = "international"
                else:
                    relevance_status = "review"
                    region = "review"
            else:
                relevance_status = classify_relevance(title, summary)
                region = classify_region(title, summary, feed["name"], link)

            cursor.execute(
                """
                INSERT OR IGNORE INTO rss_items
                (
                    title, source, feed_url, link, summary,
                    published_at, image_url, status, relevance_status, region
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    feed["name"],
                    feed["url"],
                    link,
                    summary,
                    published,
                    image_url,
                    date_status,
                    relevance_status,
                    region
                )
            )

            if cursor.rowcount > 0:
                total_added += 1

                if image_url:
                    total_images += 1

            elif image_url:
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
