# Put the new site into WordPress (for SSH DELUXE)

This puts the new hscfdoral.com into the WordPress that is already installed for the addon domain **hscfdoral.com** on the GoDaddy cPanel shared plan. It is done once, by the user's **SSH DELUXE** agent, with WP-CLI. Afterwards, new blog posts arrive by themselves (see "Automatic blog posts" at the end).

## Rules for this job

- Work **only** inside `~/public_html/hscfdoral.com` (the addon domain's folder) and `~/hscf-import` (a new folder outside the web root). The account's primary domain and every other site in `public_html` must not be touched: don't run commands from `public_html` itself, and always pass `--path` to `wp`.
- Never put passwords, keys or Application Passwords in files, chat or the project. The user types them into WordPress or GitHub themselves.
- Don't change any DNS record except the `@` A record (that one is the user's job, at GoDaddy). MX, TXT (SPF, DMARC), DKIM CNAMEs and SRV records keep email working.
- Stop and ask the user before deleting anything that isn't listed below.

## What you need

From the user's Mac, in `/Volumes/BIGGER ONE/CLAUDE FILES /HSCF DORAL/wordpress/dist/` (note the space after `CLAUDE FILES`):

| File | What it is |
|---|---|
| `hscf.zip` | the theme: templates + the site's CSS, JavaScript, fonts, photos and video (about 15 MB) |
| `manifest.json` | every page and post in Spanish and English, the SEO files (robots.txt, sitemap.xml, llms.txt, feeds) and the old-address redirects (about 2 MB) |

They're built from the project with `python3 build/build.py --wp`. If they're missing, ask the user to run that in the project folder (or ask Claude).

## 1. Check the WordPress install and make a backup

```bash
WPROOT="$HOME/public_html/hscfdoral.com"
ls "$WPROOT/wp-config.php"                       # must exist: WordPress is installed in this folder
wp --info | head -3                              # WP-CLI is installed on GoDaddy cPanel; if not: see "No WP-CLI" below
wp --path="$WPROOT" core version                 # 6.0 or newer
wp --path="$WPROOT" option get home              # http://hscfdoral.com or https://hscfdoral.com
php -v | head -1                                 # PHP 7.4 or newer (8.1+ is best)
mkdir -p ~/backups ~/hscf-import
wp --path="$WPROOT" db export ~/backups/hscfdoral-wp-before-import-$(date +%F).sql
```

**No WP-CLI?** `mkdir -p ~/bin && curl -sSo ~/bin/wp https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar && chmod +x ~/bin/wp`, then use `~/bin/wp`.

## 2. Upload the two files

From the Mac (adjust the SSH host alias to the one SSH DELUXE uses):

```bash
scp "/Volumes/BIGGER ONE/CLAUDE FILES /HSCF DORAL/wordpress/dist/hscf.zip" \
    "/Volumes/BIGGER ONE/CLAUDE FILES /HSCF DORAL/wordpress/dist/manifest.json" <ssh-host>:hscf-import/
```

## 3. Check the plugins

```bash
wp --path="$WPROOT" plugin list
wp --path="$WPROOT" post list --post_type=page,post --post_status=any --fields=ID,post_type,post_name,post_title
```

- **Deactivate SEO plugins** if any are active (Yoast SEO, Rank Math, All in One SEO, SEOPress, The SEO Framework). The site brings its own titles, descriptions, canonical links, hreflang, schema, robots.txt and sitemap; a second set would conflict. `wp --path="$WPROOT" plugin deactivate <name>`
- Deactivate "coming soon" or maintenance-mode plugins.
- Security, backup and caching plugins (LiteSpeed Cache, Wordfence…) can stay. The import clears LiteSpeed, WP Super Cache and W3 Total Cache by itself.
- A brand-new install has a "Hello world!" post and a "Sample Page". Delete only those two, by the IDs shown: `wp --path="$WPROOT" post delete <id> <id> --force`. Ask the user before deleting any other page.

## 4. Install the theme

```bash
cd ~/hscf-import && unzip -oq hscf.zip -d "$WPROOT/wp-content/themes/"
ls "$WPROOT/wp-content/themes/hscf/style.css"
wp --path="$WPROOT" theme activate hscf
```

(Or: WordPress admin → Appearance → Themes → Add New → Upload Theme → `hscf.zip` → Activate.)

## 5. Import the pages and posts

```bash
wp --path="$WPROOT" hscf sync ~/hscf-import/manifest.json --dry-run     # expect: "would be 102 created"
wp --path="$WPROOT" hscf sync ~/hscf-import/manifest.json               # "102 created … Import finished."
wp --path="$WPROOT" hscf sync ~/hscf-import/manifest.json               # run again: "102 unchanged"
```

The import creates 70 pages, 16 Spanish posts and 16 English posts. It sets the home page, the permalinks (`/%year%/%monthnum%/%postname%/`), the site title and time zone, turns comments off, and stores robots.txt, sitemap.xml, ai.txt, llms.txt, llms-full.txt, the RSS feeds and the old-address redirects. It only ever changes pages it created itself.

If it reports **"WordPress saved the address as … instead of …"**, a page left over from the install is using that address: show the user the page (`wp post list --name=<slug> --post_type=any`), delete it with their OK, and run the import again.

Make sure pretty addresses work. `.htaccess` in `$WPROOT` must contain the standard WordPress block:

```bash
grep -c "BEGIN WordPress" "$WPROOT/.htaccess"    # 1 is good. 0 or "No such file": add the block below
```

```apache
# BEGIN WordPress
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]
RewriteBase /
RewriteRule ^index\.php$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /index.php [L]
</IfModule>
# END WordPress
```

## 6. Check it

If the domain already points to this server, use the address directly. If not yet, add `--resolve hscfdoral.com:80:72.167.102.145` to each `curl`.

```bash
for u in / /en/ /aba/ /en/aba-therapy/ /seguros/ /jose-mesa/ /en/staff/jose-mesa/ /blog/ \
         /2026/10/sintomas-de-ansiedad-en-ninos/ /en/2026/10/signs-of-anxiety-in-children/ \
         /robots.txt /sitemap.xml /llms.txt /blog/feed.xml /karina-la-banca/ /no-existe/; do
  printf "%-50s " "$u"; curl -s -o /dev/null -w "%{http_code} %{redirect_url}\n" "http://hscfdoral.com$u"
done
```

Expected: 200 for the pages and files, **301 → /jorge-garcia/** for `/karina-la-banca/` (an old address), **404** for `/no-existe/`. Then ask the user to open the home page on their phone and computer.

## 7. Email from the contact form

The form on `/contacto/` and `/en/contact/` emails **info@hscfdoral.com** through WordPress. The domain's DMARC policy is `p=reject`, so mail must go out through GoDaddy's mail server, not the web server (never add the web server's IP to SPF).

1. `wp --path="$WPROOT" plugin install wp-mail-smtp --activate`
2. The user finishes it in WordPress admin → WP Mail SMTP → Settings (they type the mailbox password there, not in chat):
   - From Email `info@hscfdoral.com`, tick "Force From Email"; From Name `Healthy Solutions`.
   - Mailer: **Other SMTP**. Host `smtpout.secureserver.net`, Encryption **SSL**, Port **465**, Authentication on, Username `info@hscfdoral.com`, Password: the mailbox password.
3. WP Mail SMTP → Tools → Email Test → send to info@hscfdoral.com. Then send a test from the site's contact form.
4. If the test can't connect (some shared plans block outside mail ports), tell the user. The options are GoDaddy's hosting relay or a sending service (Brevo, SendGrid, Postmark), which needs its own DNS records; the user decides. Until then the form shows its error message and visitors can still call or email.

The form stores nothing in WordPress; each message is only emailed.

## 8. HTTPS (after the domain points here)

1. cPanel → **SSL/TLS Status** → Run AutoSSL for `hscfdoral.com` and `www.hscfdoral.com`. Wait for the padlock on `https://hscfdoral.com/`.
2. Switch WordPress to https:
   ```bash
   wp --path="$WPROOT" option update home https://hscfdoral.com
   wp --path="$WPROOT" option update siteurl https://hscfdoral.com
   ```
3. Add these lines at the **top** of `$WPROOT/.htaccess`, above `# BEGIN WordPress` (they only affect this domain's folder):
   ```apache
   # BEGIN HSCF https
   <IfModule mod_rewrite.c>
   RewriteEngine On
   RewriteCond %{HTTPS} off [OR]
   RewriteCond %{HTTP_HOST} ^www\. [NC]
   RewriteRule ^(.*)$ https://hscfdoral.com/$1 [L,R=301]
   </IfModule>
   # END HSCF https
   ```
4. Check: `curl -sI http://www.hscfdoral.com/aba/` → `301` to `https://hscfdoral.com/aba/`; `curl -sI https://hscfdoral.com/` → `200`.
5. In WordPress → Settings → Reading, make sure "Discourage search engines" is **off**.

## 9. Automatic blog posts

Twice a month a scheduled Claude task writes a post and pushes it to the private GitHub repo `paco3463/hscfdoral`. A GitHub Action (`.github/workflows/wordpress-sync.yml`) then sends it here over HTTPS (`POST /wp-json/hscf/v1/sync`). Nothing on the server pulls from GitHub, and GitHub holds no server login: only a WordPress Application Password that can be revoked any time.

The user sets it up once, **after step 8** (WordPress only allows Application Passwords over HTTPS):

1. WordPress admin → Users → Profile (an administrator) → **Application Passwords** → name `GitHub auto-post` → Add. Copy the password it shows once.
2. GitHub → `paco3463/hscfdoral` → Settings → Secrets and variables → Actions → **New repository secret**: `WP_USER` = the WordPress username, `WP_APP_PASSWORD` = that password.
3. GitHub → Actions → **WordPress sync** → Run workflow, with "Only show what would change" ticked. The log should say `102 unchanged`. Run it once more without the tick.

Check from here at any time: `wp --path="$WPROOT" hscf status`.

## Day to day

| Task | Command (on the server) |
|---|---|
| Import a new manifest by hand | `wp --path="$WPROOT" hscf sync ~/hscf-import/manifest.json` |
| See what would change | add `--dry-run` |
| Overwrite pages someone edited in WordPress | add `--force` (otherwise the edit is kept and reported) |
| Move pages that were removed from the project to the trash | add `--prune` |
| Last import and its result | `wp --path="$WPROOT" hscf status` |

**Editing in WordPress.** Page text can be edited in WordPress (Pages, Posts, Posts (English)). The next import keeps that edit and lists it as "Edited in WordPress", instead of overwriting it. For lasting changes, change the project (`build/content_es.py` and `build/content_en.py`) so both languages stay in step.

**Updating the theme.** The import sends pages and posts, not the theme. After a change to the design, scripts or photos (`site/assets/`, `wordpress/theme/`), rebuild (`python3 build/build.py --wp`), upload the new `hscf.zip` to `~/hscf-import/`, and repeat step 4's `unzip` line. No re-activation is needed. Then run step 5 once.

**Undo.** `wp --path="$WPROOT" theme activate twentytwentyfive` brings back a default theme immediately. The database backup from step 1 restores everything with `wp --path="$WPROOT" db import ~/backups/<file>.sql`.
