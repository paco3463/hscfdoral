# One-time server setup (for SSH DELUXE)

The new site goes on the **GoDaddy cPanel shared hosting plan at `72.167.102.145`**. This is done once, through the user's **SSH DELUXE** agent. Afterwards the site updates itself: every push to GitHub (including the automatic blog posts on the 1st and 15th) goes live within 15 minutes.

```
Claude (scheduled) ──push──▶ GitHub: paco3463/hscfdoral (private)
                                   │  read-only deploy key
shared hosting: cron every 15 min ─┘  git pull  →  copy site/ into the web root
```

Never paste passwords or private keys into the project or into GitHub.

## Where things are today (checked 2026-10-23)

| | Now | After the move |
|---|---|---|
| DNS | GoDaddy (`ns03/ns04.domaincontrol.com`) | unchanged |
| `hscfdoral.com` A record | `160.153.0.192` (old WordPress host) | **`72.167.102.145`** |
| `www` | CNAME → `hscfdoral.com` | unchanged (follows the A record) |
| Email (MX) | `smtp.secureserver.net`, `mailstore1.secureserver.net` (GoDaddy email) | **unchanged — do not touch** |

Only the one A record changes. Leave the nameservers, MX, TXT (SPF/DKIM) and CNAME records alone, or info@hscfdoral.com email stops working.

## 0. Back up the old WordPress site first

The old site still runs on the old host (`160.153.0.192`). Before the domain moves, download a copy of it over SFTP (all files in its web root) and export its database (WP-CLI `wp db export`, or phpMyAdmin / the hosting panel). Keep both in `~/backups/` or on the Bigger One drive. Nothing on the old host needs to be deleted.

## 1. Prepare the shared hosting account

1. `hscfdoral.com` is an **addon domain** on the account (cPanel → Domains, "Share document root" off). Its web root is **`~/public_html/hscfdoral.com`** (recorded in `deploy/deploy.json` → `remote_path`). The account's primary domain is a different site: never touch anything else in `public_html`.
2. Turn on **SSH access** (GoDaddy: My Products → Web Hosting → Manage → Settings → SSH Access → On). SSH DELUXE connects with the cPanel username.
3. If the web root already has a placeholder `index.html` or `default.html` from GoDaddy, move it into `~/backups/`.

## 2. Read-only deploy key for the private repo

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
ssh-keygen -t ed25519 -N "" -C "hscfdoral server (read-only)" -f ~/.ssh/hscfdoral_deploy
cat ~/.ssh/hscfdoral_deploy.pub
cat >> ~/.ssh/config <<'EOF'
Host github-hscf
  HostName ssh.github.com
  Port 443
  User git
  IdentityFile ~/.ssh/hscfdoral_deploy
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config
ssh -o StrictHostKeyChecking=accept-new -T github-hscf    # after the key is added below; "successfully authenticated" is the good answer
```

The user adds the printed public key on GitHub: **paco3463/hscfdoral → Settings → Deploy keys → Add deploy key**, title "hscfdoral server", **"Allow write access" off**.

## 3. Clone outside the web root

```bash
git clone git@github-hscf:paco3463/hscfdoral.git ~/hscfdoral-repo
chmod +x ~/hscfdoral-repo/deploy/server-pull.sh
```

GitHub is reached over port 443 (`ssh.github.com`), which shared hosts rarely block. The clone lives in the home folder, **not** inside `public_html` (the script refuses if it is), so the source files are never public.

## 4. First publish, then turn on the 15-minute pull


```bash
touch ~/hscfdoral-repo/.git/hscf-deploy-approved
HSCF_WEB_ROOT=$HOME/public_html/hscfdoral.com ~/hscfdoral-repo/deploy/server-pull.sh
ls ~/public_html/hscfdoral.com     # index.html, aba/, seguros/, en/, assets/ …
```

Then add the cron job in **cPanel → Cron Jobs** (common setting "Once per fifteen minutes"), command:

```
HSCF_WEB_ROOT=$HOME/public_html/hscfdoral.com $HOME/hscfdoral-repo/deploy/server-pull.sh >> $HOME/hscfdoral-pull.log 2>&1
```

## 5. Check the new host before moving the domain

From any computer, ask the new server for the site directly, without DNS:

```bash
curl -sI --resolve hscfdoral.com:80:72.167.102.145 http://hscfdoral.com/            # 200
curl -sI --resolve hscfdoral.com:80:72.167.102.145 http://hscfdoral.com/aba/        # 200
curl -sI --resolve hscfdoral.com:80:72.167.102.145 http://hscfdoral.com/karina-la-banca/   # 301 → /jorge-garcia/
curl -sI --resolve hscfdoral.com:80:72.167.102.145 http://hscfdoral.com/no-existe/   # 404
```

## 6. Move the domain

GoDaddy → Domains → hscfdoral.com → **DNS** → edit the **A** record with name **@**: value `72.167.102.145`, TTL 600 (or 1/2 hour). Save. Change nothing else. Most visitors see the new site within an hour.

## 7. HTTPS

1. Once DNS points to the new host, issue the SSL certificate: cPanel → **SSL/TLS Status** → Run AutoSSL (or GoDaddy's SSL page if the plan uses a GoDaddy certificate). Include `hscfdoral.com` and `www.hscfdoral.com`.
2. When `https://hscfdoral.com/` loads with a padlock, turn on the redirect: in `build/build.py` → `HTACCESS`, remove the `# ` in front of the four `RewriteCond`/`RewriteRule` lines under "Force HTTPS", and change `http://hscfdoral.com/$1` to `https://hscfdoral.com/$1` in the host-name rule just below it. Rebuild, audit and push. It goes live on the next pull.
3. From the project: `python3 build/audit.py --live` → 0 errors. Submit `https://hscfdoral.com/sitemap.xml` in Search Console and Bing.

## Day to day

- **Publish changes:** commit and push to `main`. Live within 15 minutes. `tail ~/hscfdoral-pull.log` shows each publish.
- **Force a re-copy now:** `touch ~/hscfdoral-repo/.git/hscf-force` and run the script once.
- **Pause publishing:** `rm ~/hscfdoral-repo/.git/hscf-deploy-approved` (the cron stays, but does nothing).
- **Also remove pages deleted from the site:** add `HSCF_DELETE=1` at the start of the cron command.
- The host is Apache/LiteSpeed (cPanel), so `site/.htaccess` handles the 404 page, redirects, caching and compression.
