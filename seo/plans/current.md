# SEO plan: November 2026 to April 2027

**Status:** baseline, no-data plan. The new site is not live yet and GA4 and Search Console are not connected, so these goals set up measurement rather than chase numbers. Written 2026-10-22, updated 2026-10-23 for the old site's structure and automatic posting. Next review: **2027-04-01**, run with `/seo-review`.

---

## Where we are

| Area | Today |
|---|---|
| Live site | WordPress site down since Oct 2026 (Yoast SEO plugin fatal error). Being replaced by the new static bilingual site. |
| New site | 103 pages: Spanish at the root on the **same addresses the old WordPress site used** (`/aba/`, `/seguros/`, `/staff/`, `/2022/07/<post>/` …) and English under `/en/`. Old addresses that changed (staff slugs, the empty Training page, the four play-therapy flyers) 301 to their new home. Audit: 0 errors. |
| Staff | The 9 real staff members from the old site, with their photos and bios. |
| Blog | 15 old posts migrated at their original dated URLs (with English versions) and 1 new researched article. New posts are written and published automatically on the 1st and 15th of each month. |
| Analytics | Not installed. GA4 tag is ready and switches on when `ga4_measurement_id` is set. |
| Search Console | Not connected. Use a Domain property (see `seo/GOOGLE-SETUP.md`). |
| Google Business Profile | Exists with 8245 NW 36th St, Ste 7, Doral, FL 33166 and (305) 594-5658. Not audited yet. |

## How the last plan did

There was no previous plan. The next review grades this one.

## What changed outside

To research at the next review: Google core and helpful-content updates affecting health (YMYL) sites, changes to AI Overviews and AI search citations, and which Doral and Miami-Dade practices rank for the target queries. Record sources here.

## Goals for the next 6 months

| # | Goal | Metric | Baseline | Target by 2027-04-01 |
|---|---|---|---|---|
| 1 | Replace the broken site and get it fully indexed | Search Console → Pages → indexed / submitted | 0 | 95%+ of sitemap URLs indexed, both languages |
| 2 | Measure what matters | GA4 key events configured and firing | 0 of 5 | 5 of 5, with a monthly lead count baseline from Dec 2026 |
| 3 | Build topical authority in both languages | New bilingual articles published (automatic, 1st and 15th) | 1 | 12 more by 2027-04-15 |
| 4 | Win Spanish search | Search Console impressions on Spanish (root) pages for Spanish queries | 0 | 30+ Spanish queries with impressions; top 10 for "terapia ABA Doral" and "psicólogo en Doral" |
| 5 | Own the local map pack | Google Business Profile completeness and NAP consistency | not audited | Profile 100% complete; identical name, address and phone on the top 15 directories |

## Content calendar

New posts are written **and published automatically** by the scheduled task on the 1st and 15th of each month (see `claude-agents/skills/auto-post/SKILL.md`). The task takes the first row below that has not been written yet. Rows marked **high risk** are researched and saved as drafts instead, because suicide, self-harm, abuse, eating disorders and medication always need a clinician's sign-off (`/publish-article`). Keywords are hypotheses to check against Search Console data once it exists. Each post supports one service page and links back to it.

| Date | Article id | Spanish keyword (main) | English keyword | Cluster | Supports | Risk |
|---|---|---|---|---|---|---|
| Nov 1, 2026 | `what-is-aba-therapy` | qué es la terapia ABA | what is ABA therapy | autism-aba | aba | standard |
| Nov 15, 2026 | `early-signs-of-autism` | señales tempranas de autismo | early signs of autism in toddlers | autism-aba | aba | standard |
| Dec 1, 2026 | `toddler-tantrums-when-to-worry` | berrinches en niños pequeños | toddler tantrums when to worry | behavior-parenting | parent-workshops | standard |
| Dec 15, 2026 | `co-parenting-holidays` | crianza compartida en las fiestas | co-parenting during the holidays | couples-family | psychotherapy | standard |
| Jan 1, 2027 | `school-refusal` | mi hijo no quiere ir a la escuela | child refuses to go to school | anxiety | psychotherapy | standard |
| Jan 15, 2027 | `adhd-evaluation-what-to-expect` | evaluación de TDAH en niños | ADHD testing for kids | adhd-attention | neurofeedback | standard |
| Feb 1, 2027 | `acculturation-stress-families` | estrés migratorio en familias | immigrant family stress | bicultural-families | psychotherapy | standard |
| Feb 15, 2027 | `teen-depression-signs` | señales de depresión en adolescentes | signs of depression in teenagers | teens | psychotherapy | **high** (draft) |
| Mar 1, 2027 | `play-therapy-for-children` | terapia de juego para niños | play therapy for kids | behavior-parenting | psychotherapy | standard |
| Mar 15, 2027 | `bullying-what-parents-can-do` | qué hacer si mi hijo sufre bullying | what to do if my child is bullied | behavior-parenting | parent-workshops | standard |
| Apr 1, 2027 | `helping-a-child-grieve` | cómo ayudar a un niño en duelo | how to help a child grieve | trauma-grief | psychotherapy | standard |
| Apr 15, 2027 | `test-anxiety-kids` | ansiedad ante los exámenes | test anxiety in kids | anxiety | psychotherapy | standard |

Done: `childhood-anxiety-signs` (published 2026-10-22, *síntomas de ansiedad en niños*). To write one by hand, use `/new-article <topic>` (draft for review) or `/new-article auto <topic>` (publish automatically if it passes the gates).

## Pages to improve

- **Staff pages:** the 9 profiles come from the old site. Ask each person to confirm their bio and current credentials, and add any Florida license numbers they hold. Never label anyone "licensed" unless they are. Real bylines and reviewers are the strongest trust signal for health content.
- **Old posts:** the migrated posts carry the reviewers' notes in each migration report (for example the Cogmed schedule and the COVID post's uncredited source). Have someone at HSCF read them once.
- **Area pages:** add one genuinely local detail per city (schools served, how far it is from the main roads, Spanish-language community resources). Keep them useful, not keyword lists.
- **Homepage:** once GA4 is live, check whether visitors use the finder ("Who are you looking for support for?"). If they do, add the top results to the service pages' internal links.
- **Workshop pages:** after Oct 24, publish a short recap page for *Hablemos sobre Ansiedad* (with permission for any photos), and give future workshops their own Event pages.

## Technical and AI search

1. Deploy the new site with `/deploy` (first time: SSH DELUXE backs up WordPress, moves it aside and installs the 15-minute pull from GitHub). Never delete WordPress.
2. Most old WordPress addresses are unchanged. Add a 301 for any other old URL that Search Console or backlinks still show (`REDIRECTS` in `build/build.py`).
3. Turn on the HTTPS and bare-domain redirect once SSL is confirmed on the server.
4. Submit the sitemap in Search Console and Bing Webmaster Tools.
5. Keep the AI crawler policy (`seo/config.json` → `ai_crawlers`) at "allow" for search and answer engines so ChatGPT, Claude, Perplexity and others can cite the practice. The training-crawler policy is a business decision for the practice owners; it is currently "allow", except Bytespider.
6. Run `/site-audit live` after every deploy.

## Local SEO (tasks for a person)

- **Google Business Profile:**
  - Categories: primary "Psychologist"; secondary "Child psychologist", "Family counselor", "Marriage or relationship counselor", "Mental health service".
  - Add the services, the "Spanish spoken" attribute, office photos, hours and the booking link `https://hscfdoral.com/contacto/`.
  - Post each workshop as an Event.
- **NAP consistency:** use exactly "Healthy Solutions for Children and Families, 8245 NW 36th St, Ste 7, Doral, FL 33166, (305) 594-5658" on:
  - Psychology Today (one profile per clinician)
  - insurance directories
  - Healthgrades
  - Apple Business Connect and Bing Places
  - Yelp
  - the Doral Chamber of Commerce
  - Spanish-language local directories
- **Reviews:** psychologists may not solicit testimonials from current therapy clients (APA Ethics Code 5.05; similar rules apply to LMHC, LCSW and LMFT). Let reviews come naturally, never offer anything for them, and reply without confirming that anyone is a client. The clinical director should approve the review policy.

## Measurement

- **GA4 key events:**
  - `generate_lead` (form)
  - `click_to_call`
  - `click_email`
  - `book_consultation_click`
  - `workshop_rsvp`

  Report them by landing page, by language (Spanish root vs `/en/`) and by channel.
- **AI search referrals:** GA4 sessions from chatgpt.com, perplexity.ai, claude.ai, copilot.microsoft.com and gemini.google.com.
- **Search Console:**
  - clicks and impressions for Spanish (root) vs English (`/en/`) pages
  - local-intent queries (Doral, Miami, Hialeah, "near me", "cerca de mí")
  - striking-distance queries in positions 8 to 20
- **Index coverage:** run `fetch_google_data.py --inspect` at each review.
