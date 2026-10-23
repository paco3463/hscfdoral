---
name: auto-post
description: The fully automatic twice-monthly blog post for hscfdoral.com. Picks the next topic from the SEO plan, researches and writes it in Spanish and English, publishes it when every safety gate passes (otherwise saves a draft), rebuilds, audits, and pushes to GitHub, which sends it to WordPress. Used by the scheduled task on the 1st and 15th; can also be run by hand with "/auto-post".
---

# /auto-post

Notes (may be empty): $ARGUMENTS

Nobody is watching this run. Do not ask questions; decide, and write down what you decided in the commit message and in `deploy/log.md`.

## 0. Settings and safety

- Read `seo/config.json` → `auto_blog`. If `enabled` is false, stop and report "automatic posting is turned off".
- The repository is `auto_blog.repo` (branch `auto_blog.branch`). Work in a clone of it. Never store tokens, passwords or server details in the project.
- Only ever add or change files under `content/articles/<new-id>/`, `site/` (generated), `seo/plans/current.md` (to mark the row done) and `deploy/log.md`. Never edit staff, services, prices, insurance or other pages.

## 1. Pick the topic

1. Open `seo/plans/current.md` → "Content calendar". Take the first row whose `Article id` has no folder in `content/articles/`. Use its keywords, cluster, service and risk.
2. If every row is done, choose a topic yourself: read `seo/data/LATEST` (if it exists) for Spanish queries in positions 8–20 or rising queries; otherwise pick a common parent question that fits one of HSCF's services and isn't covered yet. Prefer Spanish-language search demand.
3. If a post with the same primary keyword already exists, skip to the next row.

## 2. Write it

Delegate to the `psych-research-writer` agent in **automatic** mode with the topic, id, cluster, services, keywords, audience and the calendar's risk. Tell it to follow its whole protocol, including opening every source.

## 3. Gate

1. `python3 build/build.py --check` → 0 errors.
2. Check `meta.json`: if `risk` is `high`, or the publish gate failed, the post must have `"status": "draft"` and `"review_policy": "clinician"`. A draft is never built into the live site.
3. `python3 build/build.py`, `python3 build/audit.py` → 0 errors, and `python3 build/build.py --wp` → no error. If the audit fails because of the new post, set it to draft, rebuild and audit again. If the audit fails for another reason, do not push anything; report the errors.

## 4. Publish

1. In `seo/plans/current.md`, add "(published YYYY-MM-DD)" or "(draft, needs review)" after the row's id.
2. Append one line to `deploy/log.md`: date, post id, status, number of sources, audit result.
3. Commit everything with a message like `Blog: <es title> (<status>)` and push to the default branch. Before pushing, `git fetch` and rebase if needed. The GitHub Action **WordPress sync** then builds the WordPress manifest and sends it to https://hscfdoral.com within a few minutes. You don't need to contact the server.
4. If the push is refused (for example, GitHub access was removed), say so plainly in the final report; the post stays in the commit and is pushed next time.

## 5. Report

Reply with: the title in both languages, the status, the live addresses (`https://hscfdoral.com/<yyyy>/<mm>/<es-slug>/` and `/en/...`), the sources, and any notes for a person to check. If the post is a draft, say it needs `/publish-article <id>` after a clinician reviews it.
