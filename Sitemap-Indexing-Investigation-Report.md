# Deep Technical Investigation: Repeated Search Console Sitemap-Fetch Failures & Indexing-Quota Exhaustion on Two Cloudflare Pages Websites

**Investigation date:** 15 November 2026 (live checks run 16:07–16:09 UTC / 22:07–22:09 +06)
**Investigator:** Muse (read-only investigation; no website, DNS, Cloudflare, sitemap or Search Console setting was modified; no indexing request was submitted; no quota was consumed)
**Sites investigated:**
- Site 1 — SafeCareer Guide: `https://safecareer-guide.pages.dev/`
- Site 2 — Trend Finds: `https://trend-finds.pages.dev/` (canonical) and test host `https://trend-finds.web.app/` (Firebase Hosting)
- Future site concerned: Insight Football (planned Cloudflare-based deployment, free hosting if feasible)

---

## 0. Executive summary — headline conclusions

**The two sites do NOT have the same problem, even though the Search Console symptom looks identical.** That is the single most important finding.

| # | Conclusion | Status |
|---|-----------|--------|
| 1 | **SafeCareer Guide's sitemap is technically clean by every check I could run.** Valid XML, 11/11 listed URLs return HTTP 200, robots.txt allows everything, Googlebot user-agent gets 200. There is no file, header, redirect or robots.txt defect to fix on this site. | **Confirmed** (live checks, §2) |
| 2 | **Trend Finds' sitemap has real defects.** 66 of its 86 listed URLs are `.html` URLs that 308-redirect to extensionless URLs, while the pages' own canonical tags point at the `.html` form — a direct contradiction. Google's own guidance says to replace redirect URLs in sitemaps with the final URLs. | **Confirmed** (live checks, §3) |
| 3 | **The Firebase (web.app) sitemap is invalid for its property.** All 86 URLs in it point to `trend-finds.pages.dev`, not `trend-finds.web.app`. Google's rule: sitemap URLs must be on the same host as the sitemap file. The Firebase deploy is also missing its post pages (they 404). The Firebase "control experiment" is therefore confounded — it proves nothing about Cloudflare. | **Confirmed** (live checks, §3) |
| 4 | **Both Pages sites return soft 404s** — nonexistent paths return HTTP 200 with the homepage HTML. A real SEO defect, but it is **not** the cause of the sitemap-fetch failures (the submitted `/sitemap.xml` itself is a real file returning 200). | **Confirmed** (live checks, §2–3) |
| 5 | **Sitemap-fetch failure and indexing-quota exhaustion are two independent mechanisms.** One is Googlebot's automated sitemap retrieval; the other is a rate limit on the manual "Request indexing" button. Neither causes the other. | **Confirmed** (Google docs, §5) |
| 6 | **The most likely explanation for SafeCareer Guide is Google-side: low crawl demand for a brand-new, zero-authority site** (Google's own listed reason, and John Mueller's stated explanation for exactly this symptom on valid sitemaps). | **Suspected, not proven** (§6) |
| 7 | **A Cloudflare edge contribution cannot be confirmed or ruled out from outside.** Plausible mechanisms exist (Browser Integrity Check / Error 1010 and Bot Fight Mode on Cloudflare's shared `pages.dev` zone, which the user cannot see or control), and other `pages.dev` sites reported the identical symptom in Oct–Nov 2026 — but no failed Google request was ever captured for these two sites, and Googlebot demonstrably *can* crawl both sites (SCG homepage indexed; Firebase homepage crawled). | **Suspected, unproven** (§6) |
| 8 | **"Cloudflare Pages is the cause" is NOT established.** The Firebase host failed too, but its sitemap was invalid anyway, so that comparison is void. | **Confirmed** (reasoning, §6) |
| 9 | **The indexing quota is per-property (per site), not per Google account.** The ~10–12 manual requests/day figure is community-observed, **not** published by Google. Google's only documented quota is the URL Inspection *API* (2,000/day/property) — a different mechanism from the UI button. | **Supported by evidence; UI-button figure undocumented** (§5) |
| 10 | **There is an unresolved quota anomaly.** If no requests had truly been made for several days, the daily quota should have been fresh — yet retries were blocked on 11 Nov (SCG) and again on 15 Nov 15:40/15:46 (Trend Finds). Either requests were made earlier those days, or the effective limit behaves differently for new properties. This needs a controlled test, not more guessing. | **Unresolved** (§5) |
| 11 | **The user's statement "no indexing requests for several days" conflicts with our records**, which show indexing retries attempted today, 15 Nov, at 15:40 and 15:46 (and blocked). Both versions cannot be true as stated. | **Discrepancy — see §5.4** |

**Bottom line for Insight Football:** do not copy the Trend Finds sitemap-generation pattern (listing redirecting URLs), do not submit a cross-host sitemap, do not use soft-404 SPA fallback, and do not hammer "Request indexing". The SCG case shows that even a technically perfect sitemap on a brand-new `pages.dev` site can sit unread for days — so the pre-launch plan (§9) is built around *proving* fetchability and crawl demand before launch, and a custom domain is the one structural change that removes the `pages.dev` unknowns entirely.

---

## 1. Scope, method, and what I could and could not access

### 1.1 What I did (all read-only)

- Live HTTP diagnostics with `curl` from this machine (15 Nov 2026, ~16:07 UTC) on all three hosts: status codes, redirect chains, response headers, `Content-Type`, cache headers, Cloudflare headers; `robots.txt` on each host; Googlebot user-agent fetches of sitemaps and content pages; soft-404 probes; full XML parsing and validation of all three sitemap files (well-formedness, URL counts, hosts, schemes, `lastmod`); status checks of **all 11** SCG sitemap URLs and a random sample of 10 Trend Finds sitemap URLs.
- Read Google's official documentation (Search Central sitemap guide; Search Console Sitemaps report help) and Cloudflare's official Bot Fight Mode documentation, plus dated community reports from the Cloudflare Community forum and Google Search Central Community (Oct–Nov 2026) describing the identical symptom on other `pages.dev` sites.
- Re-checked the background facts supplied in the brief against live evidence, and marked each as confirmed / corrected / unverified.

### 1.2 What I could NOT access (and therefore could not verify)

- **Google Search Console internals** for any property: the Sitemaps report details page (exact error text per sitemap), Crawl Stats, Manual Actions report, Security Issues, URL Inspection live-test results, and the history/count of "Request indexing" clicks. Everything about *what Google actually saw* comes from the user's reports, not from direct inspection.
- **Cloudflare dashboard / account settings** for either Pages project: Bot Fight Mode state, AI Crawl Control settings, WAF rules, Security Events log. Note also that `*.pages.dev` is Cloudflare's own zone — the user has no access to its security settings in any case.
- **The projects' source / build configuration**: the Trend Finds `_redirects` file or Pages settings that produce the `.html` → extensionless 308; the Firebase `firebase.json` / deploy config that explains why post pages 404 on `web.app`; the exact sitemap-generation code for either site.
- **Which Search Console property each sitemap was submitted under** (URL-prefix vs domain property, and whether the submitted sitemap URL was the final URL or a redirecting one).
- **The Firebase support case 10439100** (filed 15 Nov; reply expected within 2 business days — not yet received).

Section 10 lists exactly what is needed from the user to close these gaps.

### 1.3 How this report separates certainty

- **Confirmed** — verified by a live check in this investigation, or stated in official Google/Cloudflare documentation.
- **Supported by evidence** — consistent with live checks and documentation, but with a stated gap.
- **Suspected** — plausible, fits the evidence, but not proven.
- **Unverified / unresolved** — cannot be established from available data; a specific test is given.

---

## 2. Findings — Site 1: SafeCareer Guide (`safecareer-guide.pages.dev`)

### 2.1 Live results (15 Nov 2026, 16:07 UTC)

| Check | Result |
|---|---|
| `GET /sitemap.xml` | **HTTP 200**, 1,898 bytes, no redirect |
| `Content-Type` | `application/xml` |
| `Cache-Control` | `public, max-age=0, must-revalidate` |
| `Server` / edge | `cloudflare`, `CF-RAY: a5af81cf1f0d51fa-DEN` |
| XML well-formed | Yes; root `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">` |
| URLs in sitemap | **11**; all `https://safecareer-guide.pages.dev/…`; **0** non-HTTPS; **0** off-host |
| `lastmod` | Present on 11/11; all `2026-11-11` |
| Sitemap URLs returning 200 | **11/11** (homepage + 10 guide pages, each checked individually; no redirects) |
| `robots.txt` | `User-agent: *` / `Allow: /` / `Sitemap: https://safecareer-guide.pages.dev/sitemap.xml` |
| Googlebot-UA fetch of `/sitemap.xml` | HTTP 200, 1,898 bytes |
| Googlebot-UA fetch of a content page | HTTP 200, 230,859 bytes |
| Homepage | HTTP 200; `<link rel="canonical" href="https://safecareer-guide.pages.dev/">`; `<meta name="robots" content="index, follow, max-image-preview:large">` — no `noindex` |
| `https://safecareer-guide.vercel.app/` | HTTP 308 → `https://safecareer-guide.pages.dev/` (matches the brief) |
| `https://safecareerguide.pages.dev/` (no hyphen, as written in the user's message) | **Does not resolve** (curl exit, HTTP 000). The real host is `safecareer-guide.pages.dev`. If this spelling was ever submitted anywhere, it would fail — worth checking, but it is not the cause of the `pages.dev` property's errors. |
| Nonexistent path (`/this-page-does-not-exist-xyz`) | **HTTP 200, `text/html`** — soft 404 (see §2.3) |
| `/sitemap_index.xml`, `/sitemap-index.xml`, `/sitemap.txt` | All return HTTP 200 with the **homepage HTML** (`text/html`) — consequences of the soft-404 behaviour, not real files |

### 2.2 What this rules out

For SafeCareer Guide, the following candidate causes are **ruled out by live evidence**: sitemap file missing or 404; wrong `Content-Type`; malformed XML; wrong namespace; off-host or non-HTTPS URLs in the sitemap; missing `lastmod`; sitemap URLs that redirect or 404; `robots.txt` blocking Googlebot or the sitemap; a `noindex` or wrong canonical on the homepage; Googlebot user-agent being served an error. **There is nothing wrong with this sitemap that a file-level fix could address.**

### 2.3 The one real defect on this site: soft 404s

Any unknown path returns HTTP 200 with the homepage HTML instead of a 404. This is the classic symptom of an SPA-fallback configuration (e.g. a `/* /index.html 200` redirect rule) on Cloudflare Pages. It does **not** explain the sitemap-fetch failure — `/sitemap.xml` is a real file served correctly — but it is a genuine SEO defect: Googlebot cannot distinguish real pages from missing ones, crawl budget is wasted on nonexistent URLs, and it can contribute to "Crawled — currently not indexed" outcomes. Fix: return a real 404 for unknown paths (see §8, P1).

### 2.4 History (from records, not re-verifiable by me)

- Homepage indexed 2026-11-09 21:54 +06; guide pages not indexed.
- Search Console repeatedly showed "Sitemap could not be fetched".
- Indexing requests hit "Quota Exceeded" 9–10 Nov; a retry on 11 Nov also failed.
- Known unrelated false alarm on this site: Blogger mobile-UA `?m=1` 302 — **not** conflated with the sitemap issue here.

### 2.5 Interpretation

Googlebot **can** crawl this site — the homepage was indexed, and Googlebot-UA fetches succeed from here. What has not happened is Google's automated sitemap reader processing the sitemap. That pattern (site crawlable, sitemap unread) matches Google's own "low crawl demand" explanation and John Mueller's account (see §4.2), not a file or server defect. The Cloudflare-edge hypothesis (§6.2) remains possible but unproven for this site.

---

## 3. Findings — Site 2: Trend Finds

### 3.1 Trend Finds on Cloudflare Pages (`trend-finds.pages.dev`)

| Check | Result |
|---|---|
| `GET /sitemap.xml` | **HTTP 200**, 10,820 bytes, no redirect |
| `Content-Type` | `application/xml` |
| XML well-formed | Yes; correct `http://www.sitemaps.org/schemas/sitemap/0.9` namespace |
| URLs in sitemap | **86**; all `https://trend-finds.pages.dev/…`; all HTTPS; all with `lastmod` (2026-10-08 → 2026-11-14) |
| **URLs ending in `.html`** | **66 of 86** |
| **`.html` URLs' live status** | **HTTP 308 Permanent Redirect** → the same path without `.html` (verified on multiple URLs; 8 of 10 randomly sampled sitemap URLs returned 308) |
| Clean (non-`.html`) URLs | Return HTTP 200 directly (e.g. `/categories/beauty/`, `/contact/`) |
| **Canonical tag on a post page** | `<link rel="canonical" href="https://trend-finds.pages.dev/2026/11/smart-permanent-outdoor-lights-christmas-review.html">` — i.e. the canonical points at the `.html` URL **that the server redirects away from** |
| `robots.txt` | `User-agent: *` / `Allow: /` / `Sitemap: https://trend-finds.pages.dev/sitemap.xml` |
| Googlebot-UA fetch of `/sitemap.xml` | HTTP 200, 10,820 bytes |
| Nonexistent path | **HTTP 200, `text/html`** (homepage HTML) — soft 404, same as SCG |
| `/sitemap_index.xml`, `/sitemap.txt` | HTTP 200 with homepage HTML (`text/html`) — not real files |

**Defect 1 (confirmed): the sitemap lists redirecting URLs.** Google's Sitemaps report help states, under "URLs not followed": *"The URL contains too many redirects for Google web crawlers to follow. We suggest that you replace any redirect URLs in your sitemaps with the URLs that should actually be crawled."* A single 308 is not "too many redirects", so this alone may not produce a "Couldn't fetch" status — but listing 66 non-canonical URLs is a real sitemap-quality defect, and it means the sitemap is not doing its job of handing Google the canonical URLs. The sitemap must list the final extensionless URLs.

**Defect 2 (confirmed): canonical/redirect contradiction.** The server says the canonical form is the extensionless URL (308 from `.html`), while the page's own canonical tag says the `.html` URL is canonical. Google has to resolve the contradiction itself, and the sitemap agrees with the losing side (the canonical tag). One form must be chosen and the server redirect, the canonical tag and the sitemap must all agree. Which form is "correct" is a free choice — but they must agree. (The mechanism producing the 308 — a `_redirects` rule, a Pages setting, or the generator — is not visible to me; see §10.)

**Defect 3 (confirmed): soft 404s**, as on SCG (§2.3).

### 3.2 Trend Finds on Firebase Hosting (`trend-finds.web.app`) — the "control" host

| Check | Result |
|---|---|
| `GET /sitemap.xml` | **HTTP 200**, 10,820 bytes — byte-identical size to the Pages sitemap |
| `Content-Type` | `application/xml; charset=utf-8` |
| XML well-formed | Yes |
| URLs in sitemap | **86 — but ALL of them are `https://trend-finds.pages.dev/…`**; **0** are `trend-finds.web.app` URLs |
| `robots.txt` | `User-agent: *` / `Allow: /` / `Sitemap: https://trend-finds.web.app/sitemap.xml` |
| Homepage `/` | HTTP 200 |
| Post page, `.html` form | **HTTP 404** |
| Post page, extensionless form | **HTTP 404** |
| Nonexistent path | HTTP 404 (correct behaviour, unlike Pages) |

**Defect 4 (confirmed): cross-host sitemap.** Google's Sitemaps report help, under "URL not allowed / Different domain": *"Check that the URLs all begin with the same domain as your sitemap location."* A sitemap hosted at `trend-finds.web.app` listing only `trend-finds.pages.dev` URLs is invalid for the `web.app` property. (Cross-submission of one sitemap for multiple sites is possible, but only with verified ownership of all sites and submission done in the specific way Google documents — a `web.app` robots.txt pointing at a `web.app` sitemap whose contents are `pages.dev` URLs does not satisfy it.) The Firebase sitemap must be generated with `web.app` URLs — or, better, no sitemap should be submitted for a test host at all.

**Defect 5 (confirmed): the Firebase deploy is missing its post pages.** Only the homepage returns 200; the post URLs 404 in both forms. The Firebase deploy is therefore **not a faithful copy of the site** and cannot serve as a control host for the sitemap-fetch question.

**Consequence for the "Firebase also failed, so Cloudflare is not the cause" argument:** that argument is void. The Firebase host failed with an *invalid* sitemap (wrong-host URLs) pointing at *missing* pages. It tells us nothing about whether Cloudflare Pages is or is not involved in the Pages failures. The comparison is confounded, and any conclusion drawn from it must be withdrawn.

### 3.3 History (from records, not re-verifiable by me)

- Sitemap "Couldn't fetch" on **both** hosts, even though the sitemap file returned HTTP 200 when fetched directly.
- Firebase sitemap was initially only 1 URL (homepage), then redeployed as a full 86-URL sitemap and verified live.
- Search Console property verified; Firebase homepage was crawled by Google 14 Nov 22:25 ("Crawled — currently not indexed").
- Indexing retries on 15 Nov 15:40 and 15:46 were blocked by quota on both homepages.
- Firebase support case 10439100 filed 15 Nov re the sitemap "Couldn't fetch" on `web.app`; reply expected within 2 business days (not yet received).

---

## 4. Side-by-side comparison

| Dimension | SafeCareer Guide | Trend Finds — Pages | Trend Finds — Firebase |
|---|---|---|---|
| Host | `safecareer-guide.pages.dev` (Cloudflare Pages) | `trend-finds.pages.dev` (Cloudflare Pages) | `trend-finds.web.app` (Firebase Hosting) |
| Sitemap `GET /sitemap.xml` | 200, `application/xml`, 1,898 B | 200, `application/xml`, 10,820 B | 200, `application/xml; charset=utf-8`, 10,820 B |
| XML valid | Yes | Yes | Yes |
| URLs in sitemap | 11 | 86 | 86 — **all `pages.dev`, 0 `web.app`** |
| Sitemap URLs live status | 11/11 return 200, no redirects | 66/86 return **308** (`.html` → extensionless); 20 return 200 | Post URLs **404** (both forms) |
| Canonical agreement | Canonical = served URL | **Canonical (`.html`) contradicts server redirect (extensionless)** | n/a (pages missing) |
| `robots.txt` | Allow all; correct `Sitemap:` line | Allow all; correct `Sitemap:` line | Allow all; `Sitemap:` line names `web.app` file |
| Googlebot-UA sitemap fetch | 200 | 200 | 200 |
| Soft 404s | Yes (unknown path → 200 + homepage) | Yes | No (correct 404) |
| Search Console sitemap status | "Could not be fetched" | "Couldn't fetch" | "Couldn't fetch" |
| Googlebot crawling the site? | Yes — homepage indexed 9 Nov | Presumably (not separately evidenced) | Yes — homepage crawled 14 Nov 22:25 |
| Pages indexed | Homepage only | 0 of 66 posts known indexed (per records) | 0 |
| Real sitemap defects found | **None** | Redirecting URLs; canonical contradiction; soft 404s | Cross-host URLs; missing pages |
| Quota events | Exceeded 9–10 Nov; retry 11 Nov failed | Blocked 15 Nov 15:40 & 15:46 | Blocked 15 Nov (same attempts) |

**Reading the table:** the *symptom* is identical in all three columns, but the *causes* are not. SCG has no sitemap defect at all; Trend Finds/Pages has sitemap-content defects; Trend Finds/Firebase has a wrong-host sitemap and missing pages. A single explanation ("Cloudflare Pages is broken") cannot cover all three — and the Firebase column, which was supposed to be the control, is invalid as a control.

---

## 5. Search Console behaviour: sitemap fetch, and the indexing quota

### 5.1 What "Couldn't fetch" means (Google's own documentation)

Google's Sitemaps report help lists **five** possible reasons for a "Couldn't fetch" status:

1. The sitemap is blocked by `robots.txt`.
2. The site has an unresolved manual action (Google does not read sitemaps while one is open).
3. The submitted sitemap URL is wrong / returns 404.
4. Some other general error (e.g. server unavailability).
5. **There is low crawl demand for the sitemap.** Google's wording: *"The higher the quality of the site's content, the higher the crawl demand."*

Google also states, in its sitemap guide: *"submitting a sitemap is merely a hint: it doesn't guarantee that Google will download the sitemap or use the sitemap for crawling URLs on the site."* After a failed fetch, Google retries for a few days and then stops until the sitemap is resubmitted.

On 1 October 2026, in episode 114 of Google's own *Search Off the Record* podcast ("Do sitemaps still matter?"), John Mueller addressed exactly this symptom — a valid sitemap showing "Couldn't fetch" — and gave **two** reasons: **host load** ("we don't have any time to crawl this sitemap file because we're too busy with other things") and **low crawl demand** ("we don't actually have any need to crawl a lot from this website"). A Google Search Central Community reply on the same question puts it more bluntly: the label is misleading — in many cases **no fetch has actually failed; Google simply hasn't looked at the sitemap yet**, and because Google never guarantees it will read every sitemap, an unprocessed sitemap "doesn't mean anything is broken. In fact, it may never be processed."

**Applied to these sites:** reasons 1–3 are ruled out by live checks for SCG and for the Trend Finds/Pages sitemap file (robots allows, URLs exist, file returns 200). Reason 4 (general/server error) cannot be ruled out for Google's fetcher specifically, because my curl is not Google's fetcher (see §6.2). Reason 5 (low crawl demand) fits both sites: both are brand-new, have no backlinks or authority, and were submitted within days of launch. **Manual-action status could not be checked** — it needs Search Console access (see §10).

### 5.2 The indexing quota — what is documented vs what is observed

There are **two different quotas** and they are routinely confused. They must not be:

| Mechanism | Limit | Documented by Google? | Applies to |
|---|---|---|---|
| **"Request indexing" button** (URL Inspection tool in the Search Console UI) | **~10–12 manual requests per property per day**, then "Quota exceeded" until the next day | **No — not published by Google.** Community-observed consensus across many independent reports (2026). Google has never published a number for the button. | One URL per click, per verified property |
| **URL Inspection API** (`urlInspection.index:inspect`) | **2,000 queries/day per property, 600/minute**; returns HTTP 429 when spent; resets on Google's daily clock | **Yes** — Google's published Search Console API limits | Programmatic inspection only; **it cannot submit a URL for indexing** (there is no API equivalent of the button) |

Related facts: the Indexing API (a separate product, restricted to `JobPosting`/`BroadcastEvent` pages) allows 200 notifications/day per project — irrelevant here. Submitting a sitemap has no quota. Resubmitting a sitemap does not consume indexing quota.

**Scope — per-site, not per-account:** the brief's record that quota behaviour was "per-SITE, not per-account" is **supported**: Google's API quota documentation attaches the inspection quota to the *property*, and every independent report of the UI button describes the limit as per-property. A quota exhausted on SafeCareer Guide does not affect Trend Finds, and vice versa. (For the UI button specifically, per-property scope is community-observed rather than officially documented — mark it "supported, not officially documented".)

**Reset:** daily. Google does not document the exact hour for the UI button; for its API quotas the reset is on Google's daily clock (midnight Pacific Time). After several days with **zero** requests, the quota should be fully available again — a fresh day should allow ~10 requests.

### 5.3 Are the sitemap failure and the quota exhaustion related?

**No — they are independent mechanisms.** The sitemap status comes from Googlebot's automated, scheduled retrieval of a file. The quota is a rate limit on a human clicking a button to put one URL in a priority crawl queue. One does not cause the other: failed indexing requests do not make sitemap fetches fail, and a failed sitemap fetch does not consume or reduce indexing quota. They co-occurred here because both are downstream of the same underlying condition — a brand-new site with no crawl demand — and because the natural human response to "Google hasn't indexed my pages" is to hammer "Request indexing", which burns the small daily allowance within minutes and then *looks* like a second, separate failure. The two symptoms share a root condition; they do not cause each other.

### 5.4 The discrepancy: "no requests for several days" vs today's blocked retries

The user states no indexing requests have been submitted for several days. Our records show indexing retries were attempted **today, 15 Nov, at 15:40 and 15:46** and were blocked by quota on both Trend Finds homepages. Both statements cannot be true as written. The possibilities:

- (a) The user's "several days" refers to the period *before* today, and today's retries were the first requests in days. If so, the blocks are **anomalous**: a fresh daily quota should have allowed them, and the anomaly itself needs investigation (see the controlled test in §8, P0).
- (b) Requests were in fact made earlier today (or yesterday) and exhausted the quota before 15:40, but were not recorded. Then the blocks are ordinary and expected.
- (c) The effective limit for a very new / low-trust property is lower than the usual ~10, or the "quota exceeded" message is appearing for a different throttling reason. Unverified.

I cannot distinguish (a), (b) and (c) from outside Search Console. **The 11 Nov SCG retry shows the same anomaly**: quota exceeded on 9–10 Nov, then a retry on 11 Nov failed as well — if that was the first request of 11 Nov, it should have succeeded under a daily reset. Either more requests were made that day than recorded, or the reset/limit does not behave as the simple daily model suggests. Do not assume the simple model; test it (§8).

---

## 6. Root causes — confirmed, suspected, unverified

### 6.1 CONFIRMED root causes (verified by live checks in this investigation)

1. **Trend Finds sitemap lists 66 redirecting URLs** (`.html` → extensionless, HTTP 308), contradicting the pages' canonical tags. Real site-generation defect; fix by listing final URLs and making canonical/redirect/sitemap agree (§8, P0).
2. **Trend Finds Firebase sitemap is cross-host** (86 `pages.dev` URLs in a `web.app` sitemap) — invalid for the `web.app` property under Google's same-host rule (§3.2).
3. **Trend Finds Firebase deploy is missing its post pages** (404 in both URL forms) — the test host is not a faithful copy (§3.2).
4. **Soft 404s on both Cloudflare Pages sites** — unknown paths return HTTP 200 with homepage HTML (§2.3, §3.1).
5. **Sitemap-fetch failure and quota exhaustion are independent mechanisms** (§5.3).
6. **The manual "Request indexing" limit (~10–12/day/property) is undocumented by Google**; the only documented quota is the URL Inspection API's 2,000/day/property, which does not submit URLs for indexing (§5.2).
7. **SafeCareer Guide's sitemap has no file-level defect** — every check I could run passes (§2.2).

### 6.2 SUSPECTED causes (plausible, fit the evidence, not proven)

1. **Low crawl demand (Google-side) — the leading explanation for SafeCareer Guide.** Fits all the evidence: brand-new site, no backlinks, no authority; homepage indexed (Googlebot can crawl) but the sitemap never read; Google's own documentation lists it as a reason, and Mueller named it as one of the two reasons for exactly this symptom on valid sitemaps. It also explains why the identical symptom appeared on two unrelated sites: they share newness and zero demand, not a host defect. *Cannot be proven from outside* — crawl-demand is Google's internal judgement — but it is the only explanation that requires no additional failed mechanism.
2. **Cloudflare edge interference on the shared `pages.dev` zone (host load / challenge).** Plausible mechanisms, all documented:
   - **Browser Integrity Check / Error 1010** on `pages.dev`: community reports (Oct 2026) describe Google fetches failing on `pages.dev` while live inspection succeeds, with 1010 responses to some automated clients and no trace in zone Security Events or Worker logs. Users cannot control security settings on the shared `pages.dev` domain.
   - **Bot Fight Mode (free plan):** Cloudflare's own docs say it "cannot be customized, adjusted, or reconfigured via WAF custom rules" and "You cannot bypass or skip Bot Fight Mode using WAF custom rules or Page Rules", and that it may challenge API/app traffic. Verified bots are *meant* to be exempt, but multiple site owners report Googlebot being challenged. On `pages.dev` the zone is Cloudflare's, so the user cannot inspect or toggle it.
   - **"Block AI training crawlers" managed rule:** multiple Nov 2026 community reports with Security Events evidence show verified Googlebot blocked with HTTP 403 by this rule, because Googlebot is a *mixed-use* crawler (search + AI training) — setting Training to **Block** blocks Googlebot entirely; the correct setting is **Disallow**. This is confirmed for custom domains; **whether it can even apply to a `pages.dev` project is unverified** (it is a zone-level setting).
   - **Host load** (Mueller's other reason): Google's crawler having no capacity for the file at fetch time.
   *Why only "suspected":* no failed Google request was ever captured for these sites (no Ray ID, no Security Events entry, no 403 in Search Console's details). Googlebot demonstrably reaches both sites. An intermittent challenge that hits the automated sitemap fetcher but not the live inspection tool or normal crawling is possible, but it is an inference, not an observation.
3. **The quota anomaly has a mundane cause** (unrecorded requests earlier the same day) — suspected over a platform bug, because the alternative requires Google's documented daily reset to be wrong.

### 6.3 UNVERIFIED / unresolved possibilities (cannot be established from available data)

- An open **manual action** on either property (needs Search Console → Security & Manual Actions).
- The sitemap having been submitted under the **wrong property or with a redirecting URL** (needs the Sitemaps report's submitted-URL list).
- **Bot Fight Mode / AI Crawl Control actually enabled** on these projects (needs Cloudflare dashboard; for `pages.dev`, not user-controllable in any case).
- The **exact error text** on each sitemap's details page in Search Console (could be "General HTTP error", a specific code, or nothing — the distinction matters).
- Whether Google's sitemap report is simply **stale/lagging** (the report can lag days behind reality; resubmission + waiting is the only test).
- Whether the **Firebase support case 10439100** reply identifies a cause (pending).
- The mechanism producing Trend Finds' `.html` → extensionless 308 (needs the repo / `_redirects` / Pages settings).

### 6.4 Answering the comparison questions directly

1. **Why did two different Pages sites show nearly identical problems?** Because the two *visible* symptoms (sitemap unread; quota exhausted) have a common upstream condition, not a common host defect: both sites were brand-new, with no backlinks, no authority and therefore near-zero crawl demand, and both were submitted to Search Console and then chased with repeated "Request indexing" clicks. The identical symptom is what new sites on any host look like when Google deprioritises them. The underlying defects, where they exist, are different per site (§4).
2. **Is there a common architectural or configuration mistake?** Yes, two: **(a)** both Pages sites use soft-404 SPA fallback (unknown paths return 200), and **(b)** both were managed by hammering "Request indexing" instead of letting discovery work. Trend Finds adds its own sitemap-generation mistakes. None of these is specific to Cloudflare Pages as a host.
3. **Is Cloudflare Pages itself a likely cause, or the site generation / Search Console configuration?** On the evidence, **site generation and Search Console-side demand are the demonstrated problems; Cloudflare Pages is at most a possible contributor, not the likely cause.** The strongest evidence against a Pages-specific cause: the same failure occurred on Firebase — but that comparison is confounded (§3.2), so it neither convicts nor acquits Cloudflare. The honest position: Pages is not exonerated, but there is no positive evidence against it for these two sites, while there *is* positive evidence of site-side defects (Trend Finds) and of Google-side deprioritisation (both sites).
4. **What tests establish the actual root cause?** §7 gives the exact test sequence, in order.

---

---

## 7. Exact steps to reproduce and diagnose (in order — do not skip ahead)

Each step has a pass/fail criterion. Stop at the first failure and fix it before continuing; later steps are meaningless if an earlier one fails.

**Step 1 — Prove the sitemap file is fetchable (5 minutes, no quota used).**
```bash
curl -sI https://<host>/sitemap.xml
curl -s https://<host>/sitemap.xml | head -c 400
```
Pass: HTTP 200, `Content-Type: application/xml`, body starts with `<?xml` / `<urlset`. (Both sites pass today.)

**Step 2 — Prove the sitemap is valid and its URLs are real.**
```bash
curl -s https://<host>/sitemap.xml -o /tmp/s.xml
python3 -c "import xml.etree.ElementTree as ET; t=ET.parse('/tmp/s.xml'); print(len(t.getroot().findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url')))"
```
Then check every listed URL's status (a loop over the `<loc>` values; expect 200 with no redirect for each). Pass: XML parses; every URL is same-host, HTTPS, and returns 200 directly. (SCG passes. Trend Finds fails: 66/86 return 308.)

**Step 3 — Prove robots.txt allows Googlebot and the sitemap.**
```bash
curl -s https://<host>/robots.txt
```
Pass: no `Disallow` matching `/sitemap.xml` or the listed paths; a `Sitemap:` line naming the exact sitemap URL. (Both sites pass.)

**Step 4 — Prove Googlebot's user-agent is not treated differently.**
```bash
curl -s -o /dev/null -w "%{http_code}\n" -A "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)" https://<host>/sitemap.xml
```
Pass: 200 with the same byte size as a normal fetch. (Both sites pass — but note this only proves the *user-agent string* is not blocked; a challenge based on IP/reverse-DNS or behaviour cannot be tested this way.)

**Step 5 — Run Google's own live test (uses no indexing quota).**
In Search Console → URL Inspection → enter the exact sitemap URL (`https://<host>/sitemap.xml`) → "Test live URL". Pass: "Page fetch: Successful". If this succeeds while the Sitemaps report still says "Couldn't fetch", the file is provably fetchable and the report status is a Google-side scheduling/demand matter (or stale) — do not change the file; wait and resubmit once.

**Step 6 — Read the exact error on the sitemap's details page.**
Search Console → Sitemaps → click the sitemap row. Record verbatim: status, "last read" date, discovered-URL count, and the exact error string (e.g. "General HTTP error: 403" vs "Sitemap could not be read" with no code). A specific HTTP code points at the edge (Cloudflare); no code at all points at demand/scheduling. Screenshot it — this is the single most informative artefact, and I do not have it.

**Step 7 — Check Manual Actions and Security Issues.**
Search Console → Security & Manual Actions → Manual actions; and → Security issues. Pass: "No issues detected" on both. An open manual action explains an unread sitemap by itself (Google's documented reason #2).

**Step 8 — Check Crawl Stats.**
Search Console → Settings → Crawl stats. Look at: total crawl requests over the last 90 days, response breakdown (especially 403/5xx), and whether Googlebot is crawling at all. If crawl volume is near zero while the site is fetchable, that is low demand, not a block. If there is a spike of 403s, that is the edge blocking Googlebot — note the dates and match them against any Cloudflare setting change.

**Step 9 — The controlled quota test (the only way to resolve §5.4).**
Make **zero** "Request indexing" clicks and **zero** URL inspections for 48 hours. Then, on a fresh day, click "Request indexing" for exactly **one** URL (the homepage) and record the exact time, the exact message, and a screenshot. Outcomes: (a) it is accepted → the quota resets normally and the earlier blocks were caused by same-day requests; (b) it still says "Quota exceeded" with zero prior requests that day → the daily-count model is wrong for this property and the exact message/screenshot must be escalated (Google support / Search Central Community). Do not click a second URL that day either way.

**Step 10 — Check the Cloudflare side (only meaningful on a custom domain).**
For `pages.dev` there is nothing to check — the zone is Cloudflare's. If/when a custom domain is used: Cloudflare dashboard → Security → Events, filter user-agent `Googlebot` on `/sitemap.xml`, look for Block/Challenge actions and the rule name (Bot Fight Mode, "Block AI training crawlers", WAF custom rule, rate limit). If a rule is blocking verified Googlebot: set AI Crawl Control to Search = Allow, Training = **Disallow** (not Block), and turn Bot Fight Mode **off** (free plan has no exceptions for it).

**Step 11 — Verify the submitted sitemap URL is the final URL.**
In the Sitemaps report, confirm the submitted URL is exactly `https://<host>/sitemap.xml` (HTTPS, final host, no redirect). Google does not follow redirects for submitted sitemap URLs. If a different spelling was submitted (e.g. the no-hyphen `safecareerguide.pages.dev`, or the `vercel.app` host), remove it and submit the correct one.

---

## 8. Recommended fixes (priority order)

### P0 — Do first (Trend Finds; blocks everything else)

1. **Fix the Trend Finds sitemap to list final URLs.** Regenerate it with the extensionless URLs (the ones the server actually serves with 200), and make the canonical tag, the server redirect and the sitemap all agree on one URL form. Do not list a URL that 308s. (Fixes confirmed defects 1–2, §3.1.)
2. **Fix or drop the Firebase sitemap.** Either generate a `web.app` sitemap containing only `web.app` URLs and deploy the missing post pages to Firebase — or, preferably, **stop submitting any sitemap for the test host** and remove the `web.app` property's sitemap submission. A test deploy should not be presented to Google as a second site. (Fixes confirmed defects 4–5, §3.2.)
3. **Stop clicking "Request indexing" as a routine.** Budget: at most 1–2 clicks/day, homepage and one key page only, only after a real change. Every other URL is discovered via the sitemap and internal links. This alone ends the quota-exhaustion symptom.
4. **Run the controlled quota test (§7, Step 9)** before assuming anything else about the quota.

### P1 — Do next (both sites)

5. **Remove the soft-404 SPA fallback.** Unknown paths must return a real HTTP 404, not the homepage with 200. On Cloudflare Pages this means removing the `/* /index.html 200` style rule (or the SPA fallback setting) and serving a proper 404 page. Verify with: `curl -s -o /dev/null -w "%{http_code}\n" https://<host>/this-page-does-not-exist-xyz` → must be 404.
6. **Resubmit each sitemap exactly once** after fixes 1–2 and 5, then **wait at least 7 days without touching it**. Google retries failed fetches for a few days, then stops until resubmission; repeated resubmission does not speed anything up and the report can lag days behind reality.
7. **Run Google's live URL Inspection test on each `/sitemap.xml`** (§7, Step 5) and record the result. If it says "Page fetch: Successful", the file is proven fetchable — stop changing the file.
8. **Check Manual Actions and Crawl Stats** (§7, Steps 7–8) and record the results; an open manual action or a 403 spike changes the diagnosis completely.

### P2 — Structural (prevents recurrence)

9. **Get a custom domain for each production site** (this is also required for AdSense, which will not approve `pages.dev`). A Cloudflare-proxied custom domain gives you control of the security settings that `pages.dev` does not: Bot Fight Mode can be turned off, and AI Crawl Control can be set to Search = Allow / Training = **Disallow** (never Block) / Agents = Block. Do not use a custom domain until those three settings are verified.
10. **Build crawl demand — the actual long-term fix for "low crawl demand".** A sitemap is a hint, not a discovery mechanism. What earns crawling is: real backlinks (even a few, from relevant pages), internal linking, regular new content, and time. There is no configuration substitute for this.
11. **Keep one canonical host per site.** Do not submit sitemaps for staging/test hosts (`web.app`, `vercel.app`, preview deploys). Add `X-Robots-Tag: noindex` (or basic-auth) to every non-production deploy so Google never treats a test host as a second site.

### Explicitly do NOT do

- Do not keep resubmitting the sitemap daily — it does not help and muddies the "last read" evidence.
- Do not submit indexing requests for every post — the quota is ~10/day and the posts will be discovered anyway.
- Do not enable Bot Fight Mode or set AI Training to **Block** on any domain you control.
- Do not "fix" the sitemap by changing its format (RSS/Atom/text) — the XML file is valid; the problem is not the format.
- Do not move hosts to "fix" the sitemap — the Firebase experiment already showed the same status on a different host, and its sitemap was invalid for independent reasons.

---

## 9. Pre-launch testing procedure for Insight Football

Run every gate **before** submitting anything to Search Console. A gate that fails stops the launch sequence.

**Gate 0 — Hosting decision.** Decide the production host before building: a custom domain on Cloudflare Pages (preferred — also required for AdSense later) or `pages.dev` for initial testing only, with the understanding that `pages.dev` gives you no control over edge security settings and no AdSense. Never launch production on two hosts at once.

**Gate 1 — Sitemap generation rules (build-time, automated).**
- Sitemap lists **only** URLs that return HTTP 200 directly (no redirects) on the production host.
- Every listed URL is same-host, HTTPS, absolute, and matches the page's canonical tag exactly.
- Sitemap is regenerated on every deploy; stale URLs are never listed.
- One sitemap per host; test/preview deploys get **no** sitemap submission and an `X-Robots-Tag: noindex`.

**Gate 2 — Pre-submit live checks (run the commands, record the output).**
```bash
curl -sI https://<insight-football-host>/sitemap.xml        # expect 200, application/xml
curl -s https://<insight-football-host>/robots.txt          # expect Allow: / and correct Sitemap: line
curl -s -o /dev/null -w "%{http_code}\n" -A "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)" https://<insight-football-host>/sitemap.xml  # expect 200
curl -s -o /dev/null -w "%{http_code}\n" https://<insight-football-host>/this-page-does-not-exist-xyz  # expect 404, NOT 200
```
Then validate the XML and check **every** listed URL returns 200 with no redirect (the §7 Step 2 loop). Any failure stops the launch.

**Gate 3 — Cloudflare settings (custom domain only).**
Verify in the dashboard before launch: Bot Fight Mode **off**; AI Crawl Control Search = **Allow**, Training = **Disallow** (never Block), Agents = Block; no WAF custom rule or rate-limit rule matching Googlebot; no IP Access rule covering Google's ranges. Screenshot the settings page.

**Gate 4 — Search Console setup.**
Create **one** URL-prefix property for the exact production host (`https://<host>/`). Submit the sitemap **once**. Run the live URL Inspection test on the sitemap URL and record "Page fetch: Successful". Do **not** click "Request indexing" for any URL on launch day.

**Gate 5 — Wait, then verify (days 1–7).**
- Day 1: confirm the Sitemaps report shows the submission (status may still be pending — that is normal).
- Day 3: check "last read" and discovered-URL count. If "Couldn't fetch" appears, first run §7 Steps 5–8 (live test, exact error text, manual actions, crawl stats) before changing anything.
- Day 7: homepage should be crawled; if the sitemap is still unread but the live test passes and there is no manual action, the cause is low demand — the remedy is §8 item 10 (links, content, time), not more resubmissions.
- **Quota discipline from day 1:** maximum 2 "Request indexing" clicks per day, only for genuinely new/changed key pages, and only after the sitemap has been submitted. Keep a written log (date, time, URL, result) so the quota state is never a matter of memory again.

**Gate 6 — Monitoring cadence.**
Weekly for the first month: Sitemaps report (status, last read, discovered URLs), Crawl Stats (volume, 403/5xx), Indexing report (indexed vs excluded with reasons). Any new "Couldn't fetch" triggers §7 from Step 5, not a rebuild.

---

## 10. What I still need from the user

These items would close the remaining gaps. Nothing here requires changing a site — screenshots and read-only information only:

1. **Screenshots** (Search Console, each property): the Sitemaps report details page for each submitted sitemap (status, last-read date, discovered URLs, exact error text); Security & Manual Actions → Manual actions; Settings → Crawl stats (last 90 days, response breakdown).
2. **URL Inspection live-test result** for each `https://<host>/sitemap.xml` (screenshot of "Page fetch" line).
3. **The exact "Quota exceeded" message** with date/time and a screenshot, from the next occurrence — and a written log of every "Request indexing" click from now on (date, time, URL, result).
4. **Which property each sitemap was submitted under** (exact property string), and whether any sitemap was ever submitted under a different host spelling (`safecareerguide.pages.dev`, `vercel.app`).
5. **Trend Finds redirect source**: the `_redirects` file / Pages redirect settings / generator config that produces the `.html` → extensionless 308, and the canonical-tag logic.
6. **Firebase deploy config** (`firebase.json`, deploy log) explaining why post pages 404 on `web.app`.
7. **The Firebase support case 10439100 reply** when it arrives.
8. **Whether any Cloudflare security setting was ever changed** for these projects (Bot Fight Mode, AI crawler settings, WAF rules) — and, for the custom-domain question, whether a custom domain is planned for either site.

---

## 11. Sources

**Google (official documentation):**
- Build and Submit a Sitemap — https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap — "submitting a sitemap is merely a hint: it doesn't guarantee that Google will download the sitemap or use the sitemap for crawling URLs on the site"; sitemap size limits (50 MB / 50,000 URLs); cross-submission rules.
- Sitemaps report — Search Console Help — https://support.google.com/webmasters/answer/7451001 — fetch/processing error reference, including "URLs not followed" (replace redirect URLs in sitemaps), "URL not allowed / Different domain", "Sitemap contains urls which are blocked by robots.txt".
- Search Console API limits (URL Inspection API: 2,000 queries/day/property, 600/minute) — cited via Google's published limits; see also https://indexing.io/google-search-console-api and https://infinacode.com/blog/url-inspection-api-limits for the per-property scope.
- Google *Search Off the Record*, episode 114, "Do sitemaps still matter?", 1 October 2026 — John Mueller on "Couldn't fetch" for valid sitemaps: host load and low crawl demand. Discussed at https://stillindexed.com/blog/sitemap-couldnt-fetch.

**Cloudflare (official documentation):**
- Bot Fight Mode — https://developers.cloudflare.com/bots/get-started/bot-fight-mode/ — free plan; "Cannot be customized, adjusted, or reconfigured via WAF custom rules"; "You cannot bypass or skip Bot Fight Mode using WAF custom rules or Page Rules."
- Security features interoperability — https://developers.cloudflare.com/waf/feature-interoperability/ — Bot Fight Mode cannot be skipped; Super Bot Fight Mode (Pro+) supports Skip rules and verified-bot allowlisting.

**Community reports (Oct–Nov 2026) — same symptom on other `pages.dev` sites:**
- "Pages sitemap: Google live test succeeds, but Sitemaps report cannot fetch" (`toudouche.pages.dev`) — http://community.cloudflare.com/t/pages-sitemap-google-live-test-succeeds-but-sitemaps-report-cannot-fetch/976048 — live inspection succeeds, report cannot fetch, zero discovered URLs; Error 1010 / Browser Integrity Check on `pages.dev` discussed as a possible (unconfirmed) explanation; "No security settings were disabled. No 1010 response to the real Google fetcher has been observed."
- "Google sitemap fetch fails on pages.dev, but live inspection succeeds" (`todaycommunity.pages.dev`) — http://community.cloudflare.com/t/google-sitemap-fetch-fails-on-pages-dev-but-live-inspection-succeeds/973905 — "Users cannot control the security settings on the shared `pages.dev` domain. The only solution is to use a custom Cloudflare-proxied domain." (Community claim, not confirmed.)
- "Search Engine Bots 403 cannot access sitemap or pages on site" — http://community.cloudflare.com/t/search-engine-bots-403-cannot-access-sitemap-or-pages-on-site/975680 — Training = Block blocking Googlebot/Bingbot; fix is Training = Disallow.
- "Googlebot blocked by Cloudflare AI crawler managed rule despite Search set to Allow" — http://community.cloudflare.com/t/googlebot-blocked-by-cloudflare-ai-crawler-managed-rule-despite-search-set-to-allow/977583 — Security Events evidence: Googlebot (AS15169) blocked on `/sitemap.xml` by "Block AI training crawlers", HTTP 403.
- "Sitemaps issue — Two new Cloudflare-hosted websites show 'Couldn't fetch' for valid sitemaps" — https://support.google.com/webmasters/thread/473074988/sitemaps-issue?hl=en — community reply: "Couldn't fetch" often means Google simply hasn't looked at the sitemap yet; misleading label.
- Bot Fight Mode challenging Googlebot on the free plan (no exceptions) — https://www.timway.com/en/geo-bot-fight-mode.html and https://www.smashingapps.com/does-cloudflare-hurt-seo/ and https://www.siteauditlint.com/blog/cloudflare-search-engine-crawling-issues.
- AI Crawl Control defaults and the Training = Block trap (Sep–Oct 2026) — https://www.clicktrackmarketing.com/blog/cloudflare-ai-crawler-settings and https://evolveamz.com/cloudflare-block-scrapers-allow-ai-crawlers/.

**On the "Request indexing" quota (~10–12/day/property, undocumented by Google):**
- https://www.indexbolt.com/blog/request-indexing-google-search-console — "roughly 10–12 manual requests per property per day; past them, Search Console reports the quota as exceeded until the next day."
- https://foxbusinessmarket.com/2026/11/09/how-to-use-google-search-console-url-inspection-tool/ — "Google limits how many manual requests you can make per day per property, roughly ten."

---

## Appendix A — Exact commands used and their outputs (15 Nov 2026, ~16:07–16:09 UTC)

**A1. Sitemap headers + robots.txt (all three hosts)** — `curl -sI https://<host>/sitemap.xml` and `curl -s https://<host>/robots.txt`:
- `safecareer-guide.pages.dev/sitemap.xml` → HTTP 200, `Content-Type: application/xml`, `Cache-Control: public, max-age=0, must-revalidate`, `Server: cloudflare`, 1,898 bytes. robots.txt: `User-agent: *` / `Allow: /` / `Sitemap: https://safecareer-guide.pages.dev/sitemap.xml`.
- `trend-finds.pages.dev/sitemap.xml` → HTTP 200, `Content-Type: application/xml`, 10,820 bytes. robots.txt identical in form, naming the `pages.dev` sitemap.
- `trend-finds.web.app/sitemap.xml` → HTTP 200, `Content-Type: application/xml; charset=utf-8`, `Cache-Control: max-age=3600`, 10,820 bytes. robots.txt names `https://trend-finds.web.app/sitemap.xml`.

**A2. XML validation (Python `xml.etree`)** — SCG: 11 URLs, all host `safecareer-guide.pages.dev`, all HTTPS, 11/11 with `lastmod` (2026-11-11). Trend Finds (both hosts, identical file): 86 URLs, all host `trend-finds.pages.dev`, all HTTPS, 86/86 with `lastmod` (2026-10-08 → 2026-11-14). Web.app sitemap: 86/86 URLs off-host (all `pages.dev`).

**A3. Googlebot user-agent** — `curl -A "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"`: 200 on all three sitemaps (1,898 / 10,820 / 10,820 bytes) and 200 on an SCG content page.

**A4. Sitemap URL status checks** — SCG: 11/11 URLs → 200. Trend Finds sample of 10: 8 × 308 (all `.html` posts) + 2 × 200 (category/contact pages). Overall: 66/86 sitemap URLs end in `.html` and 308 to extensionless paths; 20/86 are clean. Web.app: post URLs → 404 in both forms; homepage → 200.

**A5. Soft-404 probes** — `curl -s -o /dev/null -w "%{http_code}" https://<host>/this-page-does-not-exist-xyz`: SCG → 200 (`text/html`, homepage); Trend Finds Pages → 200 (`text/html`, homepage); web.app → 404. `/sitemap_index.xml` and `/sitemap.txt` on both Pages hosts → 200 with homepage HTML (`text/html`).

**A6. Redirect/alias checks** — `safecareer-guide.vercel.app/` → HTTP 308 → `https://safecareer-guide.pages.dev/`. `safecareerguide.pages.dev/` (no hyphen) → does not resolve (HTTP 000). Trend Finds `.html` URL without follow: HTTP 308, `Location: /2026/11/…` (extensionless). Canonical on a Trend Finds post: `<link rel="canonical" href="https://trend-finds.pages.dev/2026/11/smart-permanent-outdoor-lights-christmas-review.html">`. Canonical on SCG homepage: self-referencing, with `<meta name="robots" content="index, follow, max-image-preview:large">`.

---

*End of report. No website, DNS, Cloudflare setting, sitemap file or Search Console setting was modified during this investigation. No indexing request was submitted and no quota was consumed.*
