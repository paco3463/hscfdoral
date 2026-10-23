---
name: new-article
description: Research and write a new bilingual blog post for hscfdoral.com (Spanish + English). "/new-article <topic>" saves it for review; "/new-article auto <topic>" publishes it automatically if every safety gate passes. Use when someone asks for a new article, blog post or resource.
---

# /new-article

Request: $ARGUMENTS

If the request starts with `auto`, the mode is **automatic**; otherwise it is **review**.

1. **Check for overlap first.** Read every `content/articles/*/meta.json` (ignore `_template`). If a post already targets the same keyword or question, stop and propose updating it instead. Two pages competing for one query hurt both.
2. **Pick the details:** `id` (lowercase English words with hyphens), `topic_cluster` from `seo/config.json`, the `services` it supports, and one primary keyword per language. If `seo/plans/current.md` lists the topic in the content calendar, use the keywords and risk given there. If something is truly ambiguous and a person is present, ask one short question; otherwise decide.
3. **Delegate the research and writing** to the `psych-research-writer` agent. Pass the topic, id, cluster, services, keywords, audience and **mode**, and tell it to follow its protocol in full.
4. When it returns, run `python3 build/build.py --check`, `python3 build/build.py` and `python3 build/audit.py`. All must report 0 errors.
5. **Reply with:** both titles, the final status, the addresses (`/<yyyy>/<mm>/<es-slug>/` and `/en/<yyyy>/<mm>/<en-slug>/`), word counts, the source list and the agent's notes.
   - Review mode: end with "When it has been reviewed, run `/publish-article <id>`."
   - Automatic mode, published: end with "Commit and push to GitHub to put it online (GitHub then sends it to WordPress within minutes)."
   - Automatic mode, saved as draft: say why (for example, high-risk topic) and that `/publish-article <id>` publishes it after review.

Never fill in `medical_reviewer` here.
