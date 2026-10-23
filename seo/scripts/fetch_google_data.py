#!/usr/bin/env python3
"""
Pull Google Analytics 4 and Search Console data for hscfdoral.com into seo/data/<date>/.

Used by the /seo-review skill at the start of every 6-month review, and safe to run any time.
Authentication: a Google Cloud service account (see seo/GOOGLE-SETUP.md). The key file stays
OUTSIDE the project; its path comes from GOOGLE_APPLICATION_CREDENTIALS or seo/config.json.

    pip install -r seo/scripts/requirements.txt
    python3 seo/scripts/fetch_google_data.py            # last 180 days + the 180 before, for comparison
    python3 seo/scripts/fetch_google_data.py --days 90  # shorter window
    python3 seo/scripts/fetch_google_data.py --inspect  # also run URL Inspection on every sitemap URL
"""
import argparse, datetime as dt, json, os, re, sys, urllib.request, xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG = os.path.join(ROOT, "seo", "config.json")
SCOPES = ["https://www.googleapis.com/auth/analytics.readonly", "https://www.googleapis.com/auth/webmasters.readonly"]


def fail(msg):
    print(f"\nERROR: {msg}\n", file=sys.stderr)
    sys.exit(1)


def load_config():
    cfg = json.load(open(CONFIG, encoding="utf-8"))
    g = cfg.get("google", {})
    key = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.path.expanduser(g.get("service_account_key_path", ""))
    prop = os.environ.get("GA4_PROPERTY_ID") or str(g.get("ga4_property_id", "")).strip()
    site = os.environ.get("GSC_SITE") or g.get("search_console_site", "")
    return cfg, key, prop, site


def credentials(key_path):
    try:
        from google.oauth2 import service_account
    except ImportError:
        fail("Google libraries are not installed. Run: pip install -r seo/scripts/requirements.txt")
    if not key_path or not os.path.isfile(key_path):
        fail(f"Service account key not found at '{key_path}'. Follow seo/GOOGLE-SETUP.md, step 3.")
    creds = service_account.Credentials.from_service_account_file(key_path, scopes=SCOPES)
    print(f"Using service account {creds.service_account_email}")
    return creds


def ranges(days):
    """Search Console data lags ~3 days, so both windows end 3 days ago."""
    end = dt.date.today() - dt.timedelta(days=3)
    start = end - dt.timedelta(days=days - 1)
    prev_end = start - dt.timedelta(days=1)
    prev_start = prev_end - dt.timedelta(days=days - 1)
    return (start.isoformat(), end.isoformat()), (prev_start.isoformat(), prev_end.isoformat())


# ------------------------------------------------------------------ GA4
GA4_REPORTS = {
    "pages": (["pagePath"], ["screenPageViews", "activeUsers", "engagementRate", "userEngagementDuration", "keyEvents"], 500),
    "landing_pages": (["landingPage"], ["sessions", "engagedSessions", "keyEvents"], 500),
    "channels": (["sessionDefaultChannelGroup"], ["sessions", "activeUsers", "engagedSessions", "keyEvents"], 50),
    "sources": (["sessionSource", "sessionMedium"], ["sessions", "keyEvents"], 100),
    "cities": (["city"], ["activeUsers", "sessions"], 100),
    "languages": (["language"], ["activeUsers"], 50),
    "devices": (["deviceCategory"], ["sessions", "engagementRate"], 10),
    "events": (["eventName"], ["eventCount"], 100),
}


def run_ga4(creds, prop, window, prev_window):
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, OrderBy, RunReportRequest
    from google.api_core import exceptions as gexc
    client = BetaAnalyticsDataClient(credentials=creds)
    out = {}
    for name, (dims, mets, limit) in GA4_REPORTS.items():
        def request(metrics):
            return RunReportRequest(
                property=f"properties/{prop}",
                dimensions=[Dimension(name=d) for d in dims],
                metrics=[Metric(name=m) for m in metrics],
                date_ranges=[DateRange(start_date=window[0], end_date=window[1], name="current"),
                             DateRange(start_date=prev_window[0], end_date=prev_window[1], name="previous")],
                order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name=metrics[0]), desc=True)],
                limit=limit,
            )
        try:
            resp = client.run_report(request(mets))
        except gexc.InvalidArgument:
            # older properties report "conversions" instead of "keyEvents"
            alt = [("conversions" if m == "keyEvents" else m) for m in mets]
            resp = client.run_report(request(alt)); mets = alt
        except gexc.PermissionDenied:
            fail("GA4 refused access. In GA4 → Admin → Property access management, add the service account email as Viewer (seo/GOOGLE-SETUP.md step 4).")
        except gexc.NotFound:
            fail(f"GA4 property '{prop}' was not found. Check ga4_property_id in seo/config.json (numbers only).")
        heads = [h.name for h in resp.dimension_headers]
        rows = []
        for r in resp.rows:
            row = {h: v.value for h, v in zip(heads, r.dimension_values)}
            row.update({m.name: _num(v.value) for m, v in zip(resp.metric_headers, r.metric_values)})
            rows.append(row)
        out[name] = {"dimensions": dims, "metrics": mets, "rows": rows}
        print(f"  GA4 {name}: {len(rows)} rows")
    return out


def _num(v):
    try:
        f = float(v); return int(f) if f.is_integer() else round(f, 4)
    except ValueError:
        return v


# ------------------------------------------------------------------ Search Console
def run_gsc(creds, site, window, prev_window, inspect=False, site_url=""):
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    svc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
    out = {}

    def query(dims, win, limit, extra=None):
        rows, start = [], 0
        while True:
            body = {"startDate": win[0], "endDate": win[1], "dimensions": dims, "rowLimit": min(limit, 25000), "startRow": start, "dataState": "final"}
            if extra: body.update(extra)
            try:
                resp = svc.searchanalytics().query(siteUrl=site, body=body).execute()
            except HttpError as e:
                if e.resp.status == 403:
                    fail(f"Search Console refused access to {site}. Add the service account email as a user on that property (seo/GOOGLE-SETUP.md step 5).")
                raise
            got = resp.get("rows", [])
            for r in got:
                d = dict(zip(dims, r["keys"])); d.update(clicks=r["clicks"], impressions=r["impressions"], ctr=round(r["ctr"], 4), position=round(r["position"], 2))
                rows.append(d)
            if len(got) < body["rowLimit"] or len(rows) >= limit: return rows
            start += len(got)

    for name, dims, limit in (("queries", ["query"], 5000), ("pages", ["page"], 2000), ("query_page", ["query", "page"], 10000),
                              ("countries", ["country"], 50), ("devices", ["device"], 5)):
        out[name] = {"current": query(dims, window, limit), "previous": query(dims, prev_window, limit) if name in ("queries", "pages") else []}
        print(f"  Search Console {name}: {len(out[name]['current'])} rows")
    # Spanish vs English pages
    for lang, pat in (("es_pages", "/es/"),):
        out[lang] = query(["page"], window, 2000, {"dimensionFilterGroups": [{"filters": [{"dimension": "page", "operator": "contains", "expression": pat}]}]})
    try:
        out["sitemaps"] = svc.sitemaps().list(siteUrl=site).execute().get("sitemap", [])
    except HttpError:
        out["sitemaps"] = []
    if inspect and site_url:
        out["inspection"] = inspect_urls(svc, site, site_url)
    return out


def inspect_urls(svc, site, site_url):
    try:
        xml = urllib.request.urlopen(site_url.rstrip("/") + "/sitemap.xml", timeout=30).read()
    except Exception as e:
        print(f"  could not read sitemap for inspection: {e}"); return []
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [loc.text for loc in ET.fromstring(xml).findall("s:url/s:loc", ns)]
    results = []
    for u in urls[:1900]:  # daily quota is 2,000
        try:
            r = svc.urlInspection().index().inspect(body={"inspectionUrl": u, "siteUrl": site}).execute()
            idx = r.get("inspectionResult", {}).get("indexStatusResult", {})
            results.append({"url": u, "verdict": idx.get("verdict"), "coverage": idx.get("coverageState"), "last_crawl": idx.get("lastCrawlTime"),
                            "google_canonical": idx.get("googleCanonical"), "user_canonical": idx.get("userCanonical")})
        except Exception as e:
            results.append({"url": u, "error": str(e)[:200]})
    print(f"  URL inspection: {len(results)} URLs")
    return results


# ------------------------------------------------------------------ summary
def summarize(ga, gsc):
    s = {}
    if gsc:
        cur = gsc["queries"]["current"]; prev = {r["query"]: r for r in gsc["queries"]["previous"]}
        s["search_totals"] = {"clicks": sum(r["clicks"] for r in gsc["pages"]["current"]), "impressions": sum(r["impressions"] for r in gsc["pages"]["current"]),
                              "clicks_previous": sum(r["clicks"] for r in gsc["pages"]["previous"]), "impressions_previous": sum(r["impressions"] for r in gsc["pages"]["previous"])}
        s["top_queries"] = sorted(cur, key=lambda r: -r["clicks"])[:25]
        s["striking_distance"] = sorted([r for r in cur if 8 <= r["position"] <= 20 and r["impressions"] >= 20], key=lambda r: -r["impressions"])[:40]
        s["low_ctr"] = sorted([r for r in cur if r["position"] <= 6 and r["impressions"] >= 50 and r["ctr"] < 0.03], key=lambda r: -r["impressions"])[:25]
        s["rising_queries"] = sorted([dict(r, clicks_previous=prev.get(r["query"], {}).get("clicks", 0)) for r in cur
                                      if r["clicks"] - prev.get(r["query"], {}).get("clicks", 0) >= 3], key=lambda r: -(r["clicks"] - r["clicks_previous"]))[:25]
        spanish = [r for r in cur if re.search(r"[áéíóúñ¿¡]|\b(niños|terapia|psicólogo|psicologo|ansiedad|para|cerca)\b", r["query"], re.I)]
        s["spanish_queries"] = sorted(spanish, key=lambda r: -r["impressions"])[:40]
        pages = {}
        for r in gsc["query_page"]["current"]:
            pages.setdefault(r["query"], set()).add(r["page"])
        s["cannibalization"] = [{"query": q, "pages": sorted(p)} for q, p in pages.items() if len(p) > 1][:40]
    if ga:
        s["channels"] = ga["channels"]["rows"]
        s["top_pages"] = ga["pages"]["rows"][:30]
        s["key_events"] = [r for r in ga["events"]["rows"] if r.get("eventName") not in ("page_view", "session_start", "first_visit", "user_engagement", "scroll")][:20]
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--inspect", action="store_true", help="URL Inspection for every sitemap URL (slow, uses daily quota)")
    ap.add_argument("--skip-ga4", action="store_true"); ap.add_argument("--skip-gsc", action="store_true")
    args = ap.parse_args()
    cfg, key, prop, site = load_config()
    if not args.skip_ga4 and not prop:
        fail("ga4_property_id is empty in seo/config.json. Find it in GA4 → Admin → Property details.")
    creds = credentials(key)
    window, prev = ranges(args.days)
    print(f"Window {window[0]} → {window[1]} (compared with {prev[0]} → {prev[1]})")
    ga = None if args.skip_ga4 else run_ga4(creds, prop, window, prev)
    gsc = None if args.skip_gsc else run_gsc(creds, site, window, prev, args.inspect, cfg.get("site_url", ""))
    folder = os.path.join(ROOT, "seo", "data", dt.date.today().isoformat())
    os.makedirs(folder, exist_ok=True)
    meta = {"fetched_at": dt.datetime.now().isoformat(timespec="seconds"), "window": window, "previous_window": prev, "ga4_property": prop, "search_console_site": site}
    for name, data in (("ga4.json", ga), ("search_console.json", gsc), ("summary.json", summarize(ga, gsc)), ("meta.json", meta)):
        if data is not None:
            json.dump(data, open(os.path.join(folder, name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(ROOT, "seo", "data", "LATEST"), "w").write(os.path.basename(folder) + "\n")
    print(f"\nSaved to seo/data/{os.path.basename(folder)}/  (seo/data/LATEST points to it)")


if __name__ == "__main__":
    main()
