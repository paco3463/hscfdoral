---
name: seo-review
description: Run the 6-month SEO review for hscfdoral.com. Pulls fresh GA4 and Search Console data, grades the last plan, researches search and AI-search changes, and writes the next 6-month plan. Use every 6 months (see seo/config.json next_review) or when asked how the site is doing in search.
---

# /seo-review

Extra instructions from the user (may be empty): $ARGUMENTS

1. Check the setup:
   - `seo/config.json` → `google.ga4_property_id` is filled in
   - the service account key exists at `google.service_account_key_path`, or `GOOGLE_APPLICATION_CREDENTIALS` is set
   - the Python packages are installed: `pip install -r seo/scripts/requirements.txt`

   If something is missing, walk the user through the matching step in `seo/GOOGLE-SETUP.md` and stop.
2. Delegate the full review to the `seo-strategist` agent, passing along any extra instructions.
3. When it returns, also list the articles whose `next_review_due` has passed. Health articles need a yearly evidence check, so offer to run `psych-research-writer` on them.
4. **Reply with:**
   - the 3 headline numbers
   - what worked
   - the top 5 actions
   - the articles to commission, as ready-to-run `/new-article …` lines
   - whether anything needs `/deploy`

   Finish with the date of the next review.
