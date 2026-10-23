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

The new host is the GoDaddy cPanel shared plan at `72.167.102.145` (see `deploy/deploy.json`); the old WordPress site is on a different host and is backed up, not moved.

1. Step 0: make sure the old WordPress site has been backed up (files over SFTP + database). Show the user what was saved.
2. Find the web root on the shared plan; save the path to `deploy/deploy.json` → `remote_path`.
3. Create the read-only deploy key and ask the user to add it on GitHub (Settings → Deploy keys, write access off).
4. Clone outside the web root, create the approved marker, run the pull once, add the cPanel cron job.
5. Check the new host with the `curl --resolve` lines in step 5 of the guide **before** the domain moves.
6. Tell the user exactly which DNS record to change (only the `@` A record → `72.167.102.145`; never MX or TXT) and **wait for them to do it**. Then help with SSL (step 7) and set `first_deploy_done` to `true`.

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
