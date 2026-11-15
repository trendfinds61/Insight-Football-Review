# INSIGHT FOOTBALL
# SOURCE AUDIT & VERIFICATION REGISTER

Last Updated: 2026-11-08
Purpose: Permanent record of RSS source verification.
Rule: Never repeat a completed source check without a documented reason.

## 1. RSS SOURCES

### BBC Sport
URL: https://feeds.bbci.co.uk/sport/football/rss.xml
Type: Football-specific RSS
Status: VERIFIED
Evidence: Football-specific RSS endpoint.
Action: No routine recheck required.

### Sky Sports
URL: https://www.skysports.com/rss/11095
Type: Sports RSS
Status: PREVIOUSLY TESTED
Evidence: Initial sample of 10 RSS entries was football-related.
Action: Keep current configuration. Recheck only if non-football
content enters the database or the feed URL changes.

### The Guardian
URL: https://www.theguardian.com/football/rss
Type: Football-specific RSS
Status: VERIFIED
Evidence: Football-specific RSS endpoint.
Action: No routine recheck required.

### Dhaka Tribune Football
URL: https://www.dhakatribune.com/feed/
Type: Mixed RSS
Status: VERIFIED WITH URL FILTER
Filter:
- Accept /sport/football/
- Reject other URL paths
Code location: rss_collector.py
Action: Do not repeat source audit unless filter fails.

### The Daily Star Football
URL: https://www.thedailystar.net/sports/rss.xml
Type: Mixed sports RSS
Status: VERIFIED WITH URL FILTER
Filter:
- Accept /sports/football/
- Reject other URL paths
Code location: rss_collector.py
Action: Do not repeat source audit unless filter fails.

## 2. COMPLETED WORK

- Strict URL filtering added for Dhaka Tribune.
- Strict URL filtering added for The Daily Star.
- Python syntax compilation successful.
- RSS collector executed successfully.
- New collection reported 1 news item.
- Latest inserted news checked and confirmed as a BBC football URL.
- Legacy review records inspected.
- 65 non-football records identified:
  - 63 general/non-football news
  - 2 cricket news
- Legacy records have NOT been deleted.

## 3. IMPORTANT DATABASE FINDINGS

For Dhaka Tribune Football and The Daily Star Football
where region='review':

- Football URL records: 5
- Non-football URL records: 65

Keep valid football articles even if their relevance_status is review.
Do not mass-delete review records.
Do not run classify_existing_relevance.py blindly.

## 4. RECHECK POLICY

A source marked VERIFIED must not be checked again routinely.

Recheck ONLY when:
1. A non-football article enters the database.
2. RSS URL changes.
3. RSS fetching repeatedly fails.
4. Feed structure changes.
5. A documented production error requires investigation.

Before any recheck:
- Read this register.
- Read previous evidence.
- Identify the exact new failure.
- Check only the affected source.
- Update this file with the new result.

Never restart the entire source audit because of one isolated issue.

## 5. FUTURE SOURCE AUDIT FORMAT

Whenever a new source is added, record:

- Source name
- RSS URL
- Feed type
- Verification date
- Sample articles checked
- Football relevance result
- Required filtering rules
- Final status
- Evidence and notes

A source is not COMPLETE until its verification result
and filtering configuration are recorded here.

## 6. PROJECT RULE

This file is the permanent source-verification record
for Insight Football.

Always consult it before investigating RSS sources.
Do not ask the user to repeat completed checks.
Move forward to the next unfinished project task.

## 7. PHASE A UPDATE — 2026-11-15

- The strict URL filter is now enforced in code, not just claimed:
  `rss_collector.py` accepts only `/sport/football/` links from
  Dhaka Tribune Football and only `/sports/football/` links from
  The Daily Star Football. Other links from those mixed feeds are
  skipped at collection time. Existing database rows were NOT
  deleted or changed by this filter; only future collection is
  affected. (Only 17 of the 84 existing Bangladesh-feed rows match
  the strict paths, so future intake from those feeds will be
  smaller — that is the audited filter working as documented.)
- The hardcoded Senora special case was removed from
  `classify_region()` in `rss_collector.py`. The one affected row
  (rss_items id 1173, "Senora to run 14 pad dispensers ...",
  link `.../business/423945/...`) was corrected by migration
  `002_fix_category_and_senora.sql` from region `bangladesh` to
  region `review`. No other row was changed.
