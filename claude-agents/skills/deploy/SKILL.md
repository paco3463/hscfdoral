---
name: deploy
description: Put hscfdoral.com online. The first time, installs the site into WordPress on the GoDaddy shared plan through the user's SSH DELUXE agent (wordpress/INSTALL.md). After that, builds, audits and pushes to GitHub; a GitHub Action sends the content to WordPress. Use when the user says deploy, publish the site, push live or upload.
---

# /deploy

Notes from the user (may be empty): $ARGUMENTS

The live site is **WordPress** (theme `hscf`) on the GoDaddy cPanel shared plan, addon domain folder `~/public_html/hscfdoral.com`. Its pages and posts come from this project: `python3 build/build.py --wp` builds `wordpress/dist/manifest.json` and the theme `wordpress/dist/hscf.zip`, and the theme's importer loads them. The server connection belongs to the user's **SSH DELUXE** agent. Never put hosts, usernames, passwords, keys or Application Passwords in this project.

## 1. Build and gate

1. `python3 build/build.py`, then `python3 build/audit.py`. **If the audit reports any ERROR, stop** and offer `/site-audit`.
2. `python3 build/build.py --wp`. It must print the page and post counts with no error.
3. Never publish `preview/` (drafts).

## 2. First time only: WordPress setup

Read `deploy/deploy.json`. If `first_deploy_done` is `false`:

1. Copy `wordpress/dist/hscf.zip`, `wordpress/dist/manifest.json` and `wordpress/INSTALL.md` to the user's computer (the Bigger One drive, `CLAUDE FILES /HSCF DORAL/wordpress/dist/`), so SSH DELUXE can upload them.
2. Hand `wordpress/INSTALL.md` to SSH DELUXE (or tell the user to). It backs up the database, installs and activates the theme, runs the import (dry run first), checks the addresses, sets up WP Mail SMTP and, once DNS points to `72.167.102.145`, HTTPS.
3. DNS is the user's job: only the `@` A record → `72.167.102.145`. Never MX, TXT, DKIM CNAMEs or SRV.
4. After HTTPS works, the user creates an Application Password and adds the GitHub secrets `WP_USER` / `WP_APP_PASSWORD` (INSTALL.md step 9). Then set `first_deploy_done` to `true`.

## 3. Every deploy

- **Content** (copy in `build/content_*.py`, posts, SEO settings): commit and push to `main` (`git fetch` and rebase first). The GitHub Action **WordPress sync** sends it within minutes. Check its run: `gh run list --workflow wordpress-sync.yml -L 3`.
- **Design or behaviour** (`site/assets/`, `wordpress/theme/`): also rebuild with `--wp`, put the new `hscf.zip` on the drive, and ask SSH DELUXE for INSTALL.md → "Updating the theme".
- If the Action can't reach WordPress, SSH DELUXE can import by hand: upload `manifest.json` to `~/hscf-import/` and run `wp --path="$HOME/public_html/hscfdoral.com" hscf sync ~/hscf-import/manifest.json`.
- The import keeps pages someone edited in WordPress and lists them. Tell the user which ones, and only use `--force` if they agree.

## 4. Verify

`python3 build/audit.py --live`; `/`, `/en/`, `/robots.txt`, `/sitemap.xml`, `/llms.txt` and one service page return 200; an old address such as `/karina-la-banca/` returns 301; a made-up address returns 404.

After the first deploy, remind the user to submit `https://hscfdoral.com/sitemap.xml` in Search Console and Bing Webmaster Tools. For old URLs that Search Console still reports, add 301s to `REDIRECTS` in `build/build.py` (they reach WordPress with the next sync).

## 5. Log

Append a line to `deploy/log.md`: date, what changed, audit result, commit id, and the sync result (created / updated / kept edits).
