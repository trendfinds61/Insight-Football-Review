-- Phase A migration 001: create the rss_items table if it is missing.
-- Date: 2026-11-15. Author: Phase A (IF-MASTER-2026).
--
-- Background: the live database.db already contains rss_items, but no
-- file in the project created it -- database.py only created `news`.
-- A fresh database therefore had no rss_items table and
-- rss_collector.py failed on its first INSERT. This statement matches
-- the live schema exactly (verified against database.db sqlite_master).
--
-- Safety: CREATE TABLE IF NOT EXISTS only. It never deletes, alters,
-- or copies any row. Running it twice is a no-op (idempotent).
-- Rollback: none needed and none provided. Do NOT drop rss_items:
-- it holds 254 collected items. If this migration must be "undone",
-- simply leave the table in place; it is the correct schema.

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
);
