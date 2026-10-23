---
name: publish-article
description: Publish a blog post on hscfdoral.com that was held for review (for example a high-risk topic the automatic writer saved as a draft). Records the reviewer, sets the dates, rebuilds and audits. Use only after a real person has reviewed the draft, e.g. "/publish-article teen-depression-signs".
---

# /publish-article

Post: $ARGUMENTS

1. Open `content/articles/<id>/meta.json`. The `status` must be `in_review` or `draft`. If the body is unfinished, stop and say what is missing.
2. Show the user the `research_notes` and ask them to confirm each point has been resolved. Apply edits the reviewer requested to `es.md`, `en.md` or `meta.json`. Clinical wording changes come from the reviewer, not from you.
3. **Ask for the reviewer details. Never invent or assume them:** full name, credentials (PsyD, PhD, LMHC, LCSW, LMFT…), optional Florida license number, and their staff id if they have a profile in `build/content_es.py` → `TEAM`.
   - High-risk posts (`"risk": "high"`) need a licensed clinician. If the user has no licensed reviewer, keep the post as a draft.
4. **Update `meta.json`:** `medical_reviewer` (with `reviewed_on` today), `"review_policy": "clinician"`, `"status": "published"`, `date_published` today (this sets the post's `/<yyyy>/<mm>/` address), `date_modified` today, `next_review_due` today + 12 months.
5. Run `python3 build/build.py --check`, `python3 build/build.py` and `python3 build/audit.py`. Fix any errors.
6. Reply with the live addresses in Spanish and English, then: "Commit and push to GitHub to put it online, or run `/deploy`."
