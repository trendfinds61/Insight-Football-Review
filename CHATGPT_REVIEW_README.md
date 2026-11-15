# Insight Football — ChatGPT Review Pack (Phase A)

Master Key: IF-MASTER-2026

## What to review
Phase A ONLY. Phase B/C/D/E are NOT approved and NOT in this pack as implementation.
Phase B remains BLOCKED until Errata Part 1 is obtained. Do not invent missing V9 SQL or triggers.

## Files in this folder
1. `Insight-Football-PhaseA.zip` — updated working project, 58 files, 680K
   SHA-256: 4e53c32e7361853b5e04bfc0048bdcc769ff737eb4a87c5f763b108a22968ab7
2. `PHASE_A_REPORT.md` — full Phase A report: changed/added files, migrations, before/after DB checks, test commands and actual outputs, known issues
3. `Insight-Football-audit_0_84wz.zip` — ORIGINAL uploaded project, 47 files, 580K (do not modify)
   SHA-256: b757e5e0ba941eeb1469445405b259006c7dbd9a595958e83dd9ca24c43efc28
4. `Insight_Football_V9_Final_Architecture_Report_61_5hn4.pdf` — V9 Final, 28 pages
   SHA-256: 3ee3eed448ffdc922800ee789a0c90d527a310709faf21285c88a77ad13b6ee1
5. `Insight_Football_V9_Errata_Part2_60_6ixq.pdf` — V9 Errata Part 2, 20 pages
   SHA-256: 2fdd4d1d8aa53b846f8c85ddcd6c18bba7210060c2ac406c7d75d1789c5b6a71

## Phase A scope (approved)
- Fix RSS-to-homepage integration without duplicate articles
- Correct category rendering and transfer classification (TRANSFERS)
- Fix Senora classification (rss_items id 1173, bangladesh -> review) without damaging other records
- Admin authentication (password only from ADMIN_PASSWORD env, fail-closed, no default) and Flask debug off, localhost only
- Add requirements.txt, README.md, safe backup procedure
- Database changes only through documented migrations on a working copy
- Preserve all 254 rss_items, 135 review items, and all 8 database backup snapshots

## Database before / after (working copy)
- Before: news 2, rss_items 254, review 135, bangladesh 3, integrity ok
- After: news 2, rss_items 254, review 136, bangladesh 2, integrity ok
- The +1 / -1 is exactly the Senora row id 1173.

## Tests reported
- py_compile: OK
- unittest, 10 tests: OK in 0.482s
- Real server on temp copy, port 5001: Debug mode off, / 200, /admin 302 to login, /login 200, /api/live 500 (no API key), /match/123 200

## Please check
1. Are the Phase A fixes correct and minimal?
2. Is any original data lost or damaged?
3. Is admin auth safe (no hardcoded password)?
4. Are the migrations safe and reversible as documented?
5. Is anything in the ZIP a secret, credential, or paid dependency?
6. What, if anything, must be fixed before Phase A is accepted?

## Do NOT
- Do not approve Phase B/C/D/E from this pack.
- Do not invent Errata Part 1, cie_guard, or missing V9 SQL.
- The original ZIP and original database must stay untouched.
