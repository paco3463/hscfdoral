# hscfdoral.com

Bilingual website and automatic blog for **Healthy Solutions for Children and Families**, Doral, FL. Spanish at the root on the old site's addresses, English under `/en/`.

- **See it locally:** `cd site && python3 -m http.server 8000`, then visit http://localhost:8000
- **Rebuild after a change:** `python3 build/build.py && python3 build/audit.py`
- **Full build guide** for people and for Claude: [CLAUDE.md](CLAUDE.md)

## How it stays up to date

- On the **1st and 15th** of every month a scheduled Claude task researches and writes a new post in Spanish and English, publishes it when every safety check passes (risky topics wait as drafts for a clinician), and pushes it here.
- The web server pulls this repository every **15 minutes** and copies `site/` to the web root. One-time setup: [deploy/SERVER-SETUP.md](deploy/SERVER-SETUP.md).

## Working with Claude

Open Claude Code in this folder (first time: `bash claude-agents/install.sh`).

| Command | Use it to |
|---|---|
| `/auto-post` | write and publish the next post now |
| `/new-article <topic>` | write a post for review (`/new-article auto <topic>` to publish it automatically) |
| `/publish-article <id>` | publish a post that was held for review |
| `/seo-review` | the 6-month SEO review (next: April 1, 2027) |
| `/site-audit live` | check schema, crawlability and mobile layout |
| `/deploy` | first-time server setup through SSH DELUXE, then build + push |

## First-time setup

1. Server: give `deploy/SERVER-SETUP.md` to SSH DELUXE (backs up WordPress, installs the 15-minute pull).
2. Google: [seo/GOOGLE-SETUP.md](seo/GOOGLE-SETUP.md).
3. Contact form: replace `YOUR_FORM_ID` in `build/build.py` with a Formspree form ID.
4. Ask each staff member to confirm their bio.
