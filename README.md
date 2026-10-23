# hscfdoral.com

Bilingual website and automatic blog for **Healthy Solutions for Children and Families**, Doral, FL. Spanish at the root on the old site's addresses, English under `/en/`.

- **See it locally:** `cd site && python3 -m http.server 8000`, then visit http://localhost:8000
- **Rebuild after a change:** `python3 build/build.py && python3 build/audit.py`
- **Full build guide** for people and for Claude: [CLAUDE.md](CLAUDE.md)

## How it stays up to date

- On the **1st and 15th** of every month a scheduled Claude task researches and writes a new post in Spanish and English, publishes it when every safety check passes (risky topics wait as drafts for a clinician), and pushes it here.
- The site runs on **WordPress** with a custom theme. After every push, a GitHub Action builds the pages (`python3 build/build.py --wp`) and sends them to WordPress. One-time setup: [wordpress/INSTALL.md](wordpress/INSTALL.md).

## Working with Claude

Open Claude Code **in this folder** (first time: `bash claude-agents/install.sh`); the agents and commands only show up there. To reach the site from any folder, run `bash claude-agents/install-global.sh` once: it adds an `hscf-doral` agent next to SSH DELUXE.

| Command | Use it to |
|---|---|
| `/auto-post` | write and publish the next post now |
| `/new-article <topic>` | write a post for review (`/new-article auto <topic>` to publish it automatically) |
| `/publish-article <id>` | publish a post that was held for review |
| `/seo-review` | the 6-month SEO review (next: April 1, 2027) |
| `/site-audit live` | check schema, crawlability and mobile layout |
| `/deploy` | first-time WordPress setup through SSH DELUXE, then build + push |

## First-time setup

1. WordPress: give `wordpress/INSTALL.md` and the files from `python3 build/build.py --wp` to SSH DELUXE (backs up the database, installs the theme, imports every page).
2. Google: [seo/GOOGLE-SETUP.md](seo/GOOGLE-SETUP.md).
3. Contact form: set up WP Mail SMTP (INSTALL.md step 7) so the form's emails reach info@hscfdoral.com.
4. Ask each staff member to confirm their bio.
