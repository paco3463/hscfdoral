# One-time server setup (for SSH DELUXE)

This is done once, through the user's **SSH DELUXE** agent, which holds the connection to the hosting server. Afterwards the site updates itself: every push to GitHub (including the automatic blog posts on the 1st and 15th) goes live within 15 minutes.

```
Claude (scheduled) ──push──▶ GitHub: paco3463/hscfdoral (private)
                                   │  read-only deploy key
web server: cron every 15 min ─────┘  git pull  →  copy site/ into the web root
```

Never paste server passwords, hosts or keys into the project or into GitHub.

## 1. Find the web root

Ask the hosting panel or check which folder serves hscfdoral.com (often `~/public_html` or `~/domains/hscfdoral.com/public_html`). Write the path (not the host) into `deploy/deploy.json` → `remote_path`.

## 2. Back up and move WordPress aside (nothing is deleted)

```bash
WEB_ROOT=~/public_html                       # the folder from step 1
STAMP=$(date +%Y%m%d-%H%M)
mkdir -p ~/backups
tar -czf ~/backups/hscfdoral-wordpress-$STAMP.tar.gz -C "$WEB_ROOT" .
command -v wp >/dev/null && wp --path="$WEB_ROOT" db export ~/backups/hscfdoral-db-$STAMP.sql   # or export the database from the hosting panel
ls -la ~/backups                              # confirm both files exist and are not empty
```

After the user confirms, move the WordPress files (`wp-*`, `index.php`, `.htaccess`, `xmlrpc.php`, `license.txt`, `readme.html`) into `~/backups/wordpress-$STAMP/`. Leave `.well-known/`, `cgi-bin/` and any mail or host files in place.

## 3. Read-only deploy key for the private repo

```bash
ssh-keygen -t ed25519 -N "" -C "hscfdoral server (read-only)" -f ~/.ssh/hscfdoral_deploy
cat ~/.ssh/hscfdoral_deploy.pub
cat >> ~/.ssh/config <<'EOF'
Host github-hscf
  HostName github.com
  User git
  IdentityFile ~/.ssh/hscfdoral_deploy
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config
```

The user adds the printed public key on GitHub: **paco3463/hscfdoral → Settings → Deploy keys → Add deploy key**, title "hscfdoral server", **leave "Allow write access" off**.

## 4. Clone outside the web root

```bash
git clone git@github-hscf:paco3463/hscfdoral.git ~/hscfdoral-repo
chmod +x ~/hscfdoral-repo/deploy/server-pull.sh
```

The clone must **not** be inside the web root (the script refuses if it is), so the source files are never public.

## 5. First publish, then turn on the 15-minute pull

```bash
touch ~/hscfdoral-repo/.git/hscf-deploy-approved          # only after step 2's backup is confirmed
HSCF_WEB_ROOT=~/public_html ~/hscfdoral-repo/deploy/server-pull.sh
( crontab -l 2>/dev/null; echo '*/15 * * * * HSCF_WEB_ROOT=$HOME/public_html $HOME/hscfdoral-repo/deploy/server-pull.sh >> $HOME/hscfdoral-pull.log 2>&1' ) | crontab -
crontab -l
```

Use the real web root in both lines. If the server has no cron, the hosting panel's "Cron jobs" page takes the same line.

## 6. Check it

- `https://hscfdoral.com/`, `/en/`, `/aba/`, `/seguros/`, `/2022/07/como-manejar-los-ataques-de-ansiedad/` return 200.
- `https://hscfdoral.com/karina-la-banca/` redirects to `/jorge-garcia/`.
- A made-up address shows the 404 page.
- From the project: `python3 build/audit.py --live` reports 0 errors.
- `tail ~/hscfdoral-pull.log` shows "published …".

If the server is not Apache (LiteSpeed reads `.htaccess` too; nginx does not), apply the 404 page, redirects and caching from `site/.htaccess` in the server config.

## Day to day

- **Publish changes:** commit and push to `main`. Live within 15 minutes.
- **Force a re-copy:** `touch ~/hscfdoral-repo/.git/hscf-force`.
- **Pause publishing:** `rm ~/hscfdoral-repo/.git/hscf-deploy-approved` (the cron stays, but does nothing).
- **Remove deleted pages too:** add `HSCF_DELETE=1` to the cron line once the old WordPress files have been moved out.
- **Turn on HTTPS redirect:** once SSL works, uncomment the 4 lines in `HTACCESS` in `build/build.py`, rebuild, push.
