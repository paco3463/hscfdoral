---
name: site-audit
description: Technical SEO and crawlability audit of hscfdoral.com (schema/JSON-LD, sitemap, robots.txt, ai.txt, llms.txt, hreflang, links, mobile). Use before or after a deploy, or when Search Console shows indexing problems. Add "live" to audit the public site.
---

# /site-audit

Scope: $ARGUMENTS (empty = the local build; "live" = https://hscfdoral.com)

1. Delegate to the `technical-seo-auditor` agent with the scope.
2. Make sure every fix lands in the generator (`build/`, `seo/config.json`, `site/assets/`), never in generated HTML. Rebuild and re-run `python3 build/audit.py` until it reports 0 errors.
3. Reply with: errors fixed, warnings left with the reason, and anything a human must do.
