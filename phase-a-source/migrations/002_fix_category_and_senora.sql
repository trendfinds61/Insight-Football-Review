-- Phase A migration 002: fix transfer category + Senora classification.
-- Date: 2026-11-15. Author: Phase A (IF-MASTER-2026).
--
-- Change 1 -- transfer category normalisation.
-- The admin form offers category 'TRANSFERS' and home() queries
-- category = 'TRANSFERS', but the one existing transfer row
-- (news id 2, "Manchester City Transfer Update") was stored as
-- 'TRANSFER NEWS', so the transfer query returned 0 rows.
-- Before: news id 2 category = 'TRANSFER NEWS'
-- After:  news id 2 category = 'TRANSFERS'
-- Idempotent: a second run updates 0 rows.
--
-- Change 2 -- Senora classification correction.
-- rss_collector.py contained a hardcoded special case that forced any
-- Dhaka Tribune item containing "senora to run 14 pad dispensers" or
-- link "423945" into region='bangladesh'. The affected row is a
-- business story, not football news:
--   rss_items id 1173, "Senora to run 14 pad dispensers at federations,
--   women's football academies", link
--   https://www.dhakatribune.com/business/423945/...
-- Only this one row is corrected. No other row is touched.
-- Before: rss_items id 1173 region = 'bangladesh'
-- After:  rss_items id 1173 region = 'review'
-- Idempotent: a second run updates 0 rows.
--
-- Safety: two UPDATEs, no DELETEs, no other rows changed.
-- Expected counts after this migration (verified by test run):
--   news total = 2 (unchanged), rss_items total = 254 (unchanged)
--   rss_items region='review' = 136 (was 135; +1 is id 1173 only)
--   rss_items region='bangladesh' = 2 (was 3; -1 is id 1173 only)
--   rss_items region='international' = 116 (unchanged)
-- The 135 rows that were already region='review' are preserved
-- untouched; none is deleted or altered.
--
-- Rollback (see BACKUP_AND_ROLLBACK.md):
--   UPDATE news SET category = 'TRANSFER NEWS' WHERE id = 2;
--   UPDATE rss_items SET region = 'bangladesh' WHERE id = 1173;

UPDATE news SET category = 'TRANSFERS'
WHERE id = 2 AND category = 'TRANSFER NEWS';

UPDATE rss_items SET region = 'review'
WHERE id = 1173 AND region = 'bangladesh';
