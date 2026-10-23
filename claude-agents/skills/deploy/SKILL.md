---
name: deploy
description: Put hscfdoral.com online. The first time, sets up the server through the user's SSH DELUXE agent (backs up WordPress, installs the 15-minute pull from GitHub). After that, builds, audits and pushes to GitHub; the server publishes within 15 minutes. Use when the user says deploy, publish the site, push live or upload.
---

# /deploy

Notes from the user (may be empty): $ARGUMENTS

The live site is the `site/` folder of the private GitHub repo `paco3463/hscfdoral`. The web server pulls it every 15 minutes (`deploy/server-pull.sh`). The server connection belongs to the user's **SSH DELUXE** agent (see `/agents`, usually `ssh-deluxe`). Never put hosts, usernames, passwords or keys in this project.

## 1. Build and gate

1. `python3 build/build.py`, then `python3 build/audit.py`. **If the audit reports any ERROR, stop** and offer `/site-audit`.
2. Never publish `preview/` (drafts). `.gitignore` keeps it out of the repo.

## 2. First time only: set up the server

Read `deploy/deploy.json`. If `first_deploy_done` is `false`, follow `deploy/SERVER-SETUP.md` step by step **through SSH DELUXE**:

1. Find the web root; save the path to `deploy/deploy.json` → `remote_path`.
2. Back up WordPress (files + database), show the user the backup files, and **wait for a clear yes** before moving the WordPress files aside. Nothing is deleted.
3. Create the read-only deploy key and ask the user to add it on GitHub (Settings → Deploy keys, write access off).
4. Clone outside the web root, create the approved marker, run the pull once, install the cron line.
5. Check the addresses in section 6 of the setup guide, then set `first_deploy_done` to `true`.

If SSH DELUXE isn't reachable, tell the user, and give them `deploy/SERVER-SETUP.md` to hand to it.

## 3. Every deploy

1. Commit the changes with a short message saying what changed, and push to `main` (`git fetch` and rebase first if needed).
2. Wait about 15 minutes (or ask SSH DELUXE to `touch ~/hscfdoral-repo/.git/hscf-force` and run the pull now).
3. Verify: `python3 build/audit.py --live`; `/`, `/en/`, `/robots.txt`, `/sitemap.xml`, `/llms.txt` and one service page return 200; a made-up address returns 404.

## 4. After the first deploy

- Remind the user to submit `https://hscfdoral.com/sitemap.xml` in Search Console and Bing Webmaster Tools.
- Once SSL is confirmed, turn on the HTTPS/bare-domain redirect in `build/build.py` → `HTACCESS`, rebuild and push.
- For old WordPress URLs that Search Console still reports, add 301s to `REDIRECTS` in `build/build.py`.

## 5. Log

Append a line to `deploy/log.md`: date, what changed, audit result, commit id, and (first time) the backup file names.
