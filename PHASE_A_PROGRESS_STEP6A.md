# Insight Football — Phase A Progress Report: Step 6a Complete (Step 6b Next)

**Document:** IF-MASTER-2026 — Phase A progress record
**Date:** 15 November 2026, 23:25 +06
**Compiled by:** Muse, from Muse-verified data and phone-side results reported via ChatGPT
**Status:** Candidate validation in progress — Step 6a PASSED. No Production Switch authorized. No Phase B/C/D/E work authorized.

## 1. What this document is

A progress record for the Phase A candidate deployment on the phone (proot Ubuntu), Steps 0–6a. It changes no code and runs no implementation work.

Every item is labeled by source:

- **Muse-verified** — checked by Muse against the approved ZIP, its contents, or test runs on Muse's own machine.
- **Reported (phone-side)** — results from the user's Ubuntu session, relayed via ChatGPT. Not independently verified by Muse.

## 2. Approved ZIP (Muse-verified)

- File: `Insight-Football-PhaseA-Fixes2.zip`
- SHA-256: `5f7de6342792269bfa265abc355af6f2e7da373bafce69ea58a5f6c139cf3906`
- 60 files under `backend/`; 708,898 bytes.
- ChatGPT review: ACCEPTED (15 Nov 2026).
- Phone-side SHA check: matches the approved hash (reported). ZIP path on the phone (Ubuntu): `/mnt/shared/Download/Insight-Football-PhaseA-Fixes2.zip`.

## 3. Steps 0–5 — completion and verification evidence

| Step | What was done | Result |
|---|---|---|
| Step 0 | Original server stopped; starting state confirmed | Reported: done |
| Step 1 | Final pre-install backup created | Reported: done. Backup path: `/root/Insight-Football-backup-20261115-before-install` (exact folder name still to confirm — an earlier message also wrote `...-before-PhaseA-install`) |
| Step 2 | Candidate copy created | Reported: done. Candidate: `/root/Insight-Football-candidate` |
| Step 3 | ZIP extracted to temp dir; collision check; overlay excluding `database.db` and `.env` | Reported: passed. Candidate database SHA still equals the original after overlay |
| Step 4 | Candidate venv created; `pip install -r requirements.txt` | Reported: done. **Deviation:** the venv is inside the candidate backend (`backend/venv/`), not at `/root/Insight-Football-venv` as the approved plan specified — see §7.1 |
| Step 5 | Migration test on a working copy, then on the candidate database | Reported: passed. Runner output `Backup verified`. After: `news=2 rss_items=254 rss_review=136 rss_bangladesh=2` — matches Muse's verified expectation exactly |

**Data-safety comparison (reported; every figure matches Muse's verified expectation exactly):**

| Check | Original / Candidate | Result |
|---|---|---|
| RSS items | 254 / 254 | 0 missing, 0 new, 1 changed |
| RSS changed record | id 1173: `bangladesh` → `review` | Intended change only |
| News items | 2 / 2 | 0 missing, 0 new, 1 changed |
| News changed record | id 2: `TRANSFER NEWS` → `TRANSFERS` | Intended change only |
| Candidate RSS region counts | Bangladesh 2, International 116, Review 136 | Matches Muse's verified counts |

No RSS item lost, no new duplicate created, no other row changed.

**Backup manifest verification: PENDING.** The user still has to run the manifest check (`cat backups/manifest-sha256.txt` + `sha256sum backups/*.db`) and send the output. Known facts (Muse-verified from the ZIP): the manifest has exactly one entry — `database-20261115-084946.db`, SHA `239b51b1370f3ae500bb605a42747fa7858f88780d646e7cf6bde46a06ea9380`, 348160 bytes. The two runner-created backups are not in the manifest (expected — the manifest predates them), and those two must have identical SHAs to each other (both are pre-migration snapshots of the same database bytes).

## 4. Step 6a — test suite

- **31/31 tests passed** (reported, phone-side) in 285.45s.
- Muse cross-check (Muse-verified): the same 31 tests pass on Muse's machine — pytest `31 passed` in 1.52s; `unittest discover` `Ran 31 tests, OK` in 1.11s. The 285.45s duration is the phone's time, recorded as reported; it is much slower than Muse's machine but it is a pass, not a failure.
- **The `.env` test-isolation fix:** `tests/test_phase_a.py` was modified in the candidate — it is the ONLY file differing from the approved ZIP (see §5). Purpose (reported): isolate the tests from the real `.env`. The exact change was not independently verified by Muse.

## 5. Approved ZIP vs Candidate comparison (phone-side output, 15 Nov 2026 ~23:25 +06)

- ZIP files compared: **57** (60 files in the ZIP minus `database.db` and the 2 `backups/` files, which were excluded from the comparison together with `.env`).
- Candidate files counted: **1002** (57 ZIP files + 945 added; database, `.env` and `backups/` excluded from the count on both sides).
- **Missing from candidate: NONE** — all 57 ZIP files are present.
- **Changed files: `tests/test_phase_a.py` only** (the `.env` test-isolation fix, §4).
- **Added to candidate: 945 files** — `.pytest_cache/` (6 files) + `venv/` (~939 files, Python 3.12 site-packages).
- Excluded from the comparison: database yes, `.env` yes, backup directory yes.

`.pytest_cache/` files (in full): `.pytest_cache/.gitignore`, `.pytest_cache/CACHEDIR.TAG`, `.pytest_cache/README.md`, `.pytest_cache/v/cache/lastfailed`, `.pytest_cache/v/cache/nodeids`, `.pytest_cache/v/cache/stepwise`.

`venv/` packages installed (summarized by package from the file listing): Flask 3.1.3, beautifulsoup4 4.15.0, feedparser 6.0.14, requests 2.34.2, python-dotenv 1.2.4, blinker 1.9.0, click 8.5.1, Jinja2 3.1.6, MarkupSafe 3.0.4, Werkzeug 3.1.9, itsdangerous 2.2.0, idna 3.20, certifi 2026.10.23, charset-normalizer 3.5.2, soupsieve 4.0.1, urllib3 2.8.0, typing-extensions 4.16.0, pip 24.0.

**Deviation (see §7.2):** these are NEWER than the pinned versions in `requirements.txt` (Flask==3.1.0, requests==2.32.3, feedparser==6.0.11, beautifulsoup4==4.12.3, python-dotenv==1.0.1). Tests pass with the newer versions.

Note: the raw comparison output listed every `venv/` site-packages file individually (~939 lines). It is summarized here by package; the substance (which packages, which versions, counts) is preserved in full above.

## 6. Original project — untouched (reported)

- `/root/Insight-Football` was not modified by any step; the original database is unchanged (reported). The row-by-row comparison in §3 supports this: only the two intended changes exist in the candidate, and no step wrote to the original.

## 7. Deviations and open items (flags — not failures, but must be decided before any Production Switch)

1. **venv location.** The venv is inside the candidate backend (`/root/Insight-Football-candidate/backend/venv/`), but the approved plan specified `/root/Insight-Football-venv` (outside the project). A venv inside the project folder can break when the folder is renamed during the Production Switch (activate scripts and console-script shebangs contain absolute paths). Decision needed: move the venv outside the project before the switch, or recreate it after the switch.
2. **venv package versions are newer than the `requirements.txt` pins** (Flask 3.1.3 vs 3.1.0; requests 2.34.2 vs 2.32.3; feedparser 6.0.14 vs 6.0.11; beautifulsoup4 4.15.0 vs 4.12.3; python-dotenv 1.2.4 vs 1.0.1). Tests pass with these versions. Decision needed: accept the newer versions and record them, or reinstall exactly the pinned versions and re-run the 31 tests.
3. **Backup manifest verification is pending** (see §3). The user still has to run the check and send the output.
4. **Test duration 285.45s on the phone** vs ~1.5s on Muse's machine — recorded as reported; slow but passing. No action unless it indicates an environment problem.
5. **Backup folder exact name to confirm** (earlier messages used both `...-before-PhaseA` and `...-before-PhaseA-install`).

## 8. Exact next action — Step 6b: Candidate server smoke test

Precondition: the original server is stopped; no process on port 5000.

```bash
cd /root/Insight-Football-candidate/backend
/root/Insight-Football-candidate/backend/venv/bin/python app.py
```

(Note: the plan specified `/root/Insight-Football-venv/bin/python`, but the actual venv is inside the candidate backend — use the path above.)

Expected log: `Debug mode: off`, `Running on http://127.0.0.1:5000`.

Checks: `GET /` → 200, 25 RSS cards, "Senora" 0 times; `GET /admin` → 302 to `/login`; wrong-password login → error, no entry; correct-password login (from `.env`) → admin page 200; `GET /match/123` → 200; `/api/live` and `/api/match/123` → 200 if an API key is set, or 500 `API key not configured` if no key is set (expected, not a failure). No admin POST on the live candidate server, so no test row is inserted into the candidate database. Stop the server afterwards.

One step at a time; send each output for review before the next step.

## 9. Remaining Go/No-Go checks (before any Production Switch)

1. Backup manifest verification passes (§3, §7.3).
2. Step 6b smoke test passes (all checks in §8).
3. Deviations §7.1 and §7.2 are decided and resolved.
4. `.env` SHA identical (original vs candidate); all 8 `database_before_*.db` SHAs identical.
5. No file beyond the approved set plus `venv/` and `.pytest_cache/` exists in the candidate.
6. Explicit owner approval for the Production Switch (separate message).

## 10. SHA-256 values and paths (reference)

- Approved ZIP: `5f7de6342792269bfa265abc355af6f2e7da373bafce69ea58a5f6c139cf3906`
- Shipped pre-migration backup (`backups/database-20261115-084946.db`): `239b51b1370f3ae500bb605a42747fa7858f88780d646e7cf6bde46a06ea9380`
- Original uploaded `database.db` (Muse-verified): `dc4d9b589ecf6ec1724169296cdee924f61baa9da938663d7fbbf361f1804771`
- Migrated working `database.db` on Muse's machine: `267216bfc614f7b6c9327f38c82dbadb1f4af091d5bcca5666e34a791ec1d6ff`
- Original project: `/root/Insight-Football`
- Candidate: `/root/Insight-Football-candidate`
- Pre-install backup: `/root/Insight-Football-backup-20261115-before-install` (exact name to confirm, §7.5)
- ZIP on the phone: `/mnt/shared/Download/Insight-Football-PhaseA-Fixes2.zip`
- Candidate venv (actual): `/root/Insight-Football-candidate/backend/venv`

## 11. Scope — explicit

- **NO Production Switch is authorized by this document.**
- **NO Phase B, C, D, or E work is included or authorized.**
- Phase B remains BLOCKED pending Errata Part 1.
- This document is a progress record only; it changes no code and runs no implementation work.
