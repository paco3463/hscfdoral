# Connect Google Analytics 4 and Search Console

Do this once. Afterwards, `/seo-review` pulls fresh numbers on its own every 6 months, using a read-only **service account**: a robot Google account that can read reports and nothing else. Allow about 30 minutes.

You need: the Google account that owns (or will own) the HSCF analytics, and access to the hscfdoral.com DNS settings at GoDaddy.

---

## 1. Google Analytics 4: property and tag

1. Go to https://analytics.google.com → **Admin** → **Create** → **Property**. Name it `HSCF – hscfdoral.com`, set the time zone to Eastern and the currency to USD.
2. Add a **Web** data stream for `https://hscfdoral.com`.
3. Copy two values into `seo/config.json` → `google`:
   - **Measurement ID** (looks like `G-AB12CD34EF`) → `ga4_measurement_id`. This switches on the tag in every page at the next build.
   - **Property ID** (numbers only, under Admin → Property details) → `ga4_property_id`.
4. Rebuild and deploy: `python3 build/build.py`, then `/deploy`.
5. Once the site has had a few visits, go to **Admin → Events** and mark these as **key events**:
   - `generate_lead`: the consultation form was sent
   - `click_to_call`: someone tapped the phone number
   - `click_email`: someone tapped the email address
   - `book_consultation_click`: a "Book a consultation" button was clicked
   - `workshop_rsvp`: someone RSVP'd to a workshop by email

> Privacy: the site sends only the *type* of action, never names, emails, phone numbers, messages or health details. Ad personalization and Google signals are switched off in the tag. Don't add tracking to anything a client would log into.

## 2. Search Console: domain property

1. Go to https://search.google.com/search-console → **Add property** → **Domain** → `hscfdoral.com`.
2. Google shows a `TXT` record. In GoDaddy → **DNS** for hscfdoral.com, add a TXT record with host `@` and that value. Then click **Verify**. It can take up to an hour.
3. After the new site is live, open **Sitemaps** and submit `https://hscfdoral.com/sitemap.xml`.
4. Optional but recommended: also add the site to **Bing Webmaster Tools** (https://www.bing.com/webmasters). You can import it from Search Console in one click. Several AI search tools draw partly on Bing's index.

## 3. Google Cloud: the read-only service account

1. Go to https://console.cloud.google.com and create a project called `hscf-seo`.
2. Under **APIs & Services → Library**, enable both:
   - **Google Analytics Data API**
   - **Google Search Console API**
3. Under **IAM & Admin → Service accounts → Create service account**:
   - Name: `hscf-seo-reader`
   - Skip the optional role steps. It doesn't need Cloud permissions.
4. Open the new account → **Keys** → **Add key** → **JSON**. A file downloads.
5. Move the file to the path in `seo/config.json` → `service_account_key_path` (default `~/.config/hscf/ga-service-account.json`):

   ```
   mkdir -p ~/.config/hscf
   mv ~/Downloads/hscf-seo-*.json ~/.config/hscf/ga-service-account.json
   chmod 600 ~/.config/hscf/ga-service-account.json
   ```

   **Never put this file inside the project folder, email it, or paste its contents anywhere.**
6. Copy the service account's email address. It looks like `hscf-seo-reader@hscf-seo.iam.gserviceaccount.com`.

## 4. Give the service account read access to GA4

GA4 → **Admin** → **Property access management** → **+** → **Add users** → paste the service account email → role **Viewer** → **Add**.

## 5. Give the service account access to Search Console

Search Console → **Settings** → **Users and permissions** → **Add user** → paste the service account email → permission **Full**. Full is needed for URL Inspection; search data works with Restricted.

## 6. Test it

```
pip install -r seo/scripts/requirements.txt
python3 seo/scripts/fetch_google_data.py
```

You should see row counts for each report, ending with `Saved to seo/data/<today>/`. If it stops with an error, the message names the step above to recheck. A brand-new property shows zero rows until Google has collected data; Search Console takes a few days.

## Optional: pull data monthly on your Mac

The 6-month review fetches fresh data itself. If you'd also like a monthly snapshot, add this to `crontab -e`. The Bigger One drive must be connected at the time.

```
0 9 1 * * cd "/Volumes/BIGGER ONE/CLAUDE FILES /HSCF DORAL" && /usr/bin/env python3 seo/scripts/fetch_google_data.py >> seo/data/fetch.log 2>&1
```
