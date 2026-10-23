#!/usr/bin/env python3
"""
Technical SEO and crawlability audit for hscfdoral.com.

    python3 build/audit.py                 # audit the built site/ folder (run before every deploy)
    python3 build/audit.py --live          # audit the live site over HTTPS (run after deploy)
    python3 build/audit.py --json out.json # also write machine-readable results

Checks: broken internal links, missing pages in sitemap.xml, titles and descriptions (length,
duplicates), canonical + hreflang pairs, JSON-LD that does not parse, missing alt text, robots.txt
and ai.txt sanity, llms.txt links, noindex or draft banners on live pages, and page weight.
Exit code 1 when there are errors, so it can gate a deploy.
"""
import argparse, html, json, os, re, sys, urllib.parse, urllib.request
from html.parser import HTMLParser

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE = os.path.join(ROOT, "site")
BASE = "https://hscfdoral.com/"


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""; self._in_title = False; self.meta = {}; self.links = []; self.canonical = None
        self.hreflang = {}; self.ld = []; self._in_ld = False; self._ld = ""; self.imgs = []; self.h1 = 0; self.lang = None; self.text = ""
        self.ids = set()

    def handle_starttag(self, tag, a):
        a = dict(a)
        if "id" in a: self.ids.add(a["id"])
        if tag == "html": self.lang = a.get("lang")
        elif tag == "title": self._in_title = True
        elif tag == "meta" and a.get("name"): self.meta[a["name"].lower()] = a.get("content", "")
        elif tag == "link" and a.get("rel") == "canonical": self.canonical = a.get("href")
        elif tag == "link" and a.get("rel") == "alternate" and a.get("hreflang"): self.hreflang[a["hreflang"]] = a.get("href")
        elif tag == "a" and a.get("href"): self.links.append(a["href"])
        elif tag == "img": self.imgs.append(a)
        elif tag == "script" and a.get("type") == "application/ld+json": self._in_ld = True; self._ld = ""
        elif tag == "h1": self.h1 += 1
        if tag in ("img", "script", "link", "source", "video") and (a.get("src") or (tag == "link" and a.get("rel") in ("stylesheet", "icon", "preload", "manifest", "apple-touch-icon"))):
            self.links.append(a.get("src") or a.get("href"))

    def handle_endtag(self, tag):
        if tag == "title": self._in_title = False
        if tag == "script" and self._in_ld:
            self._in_ld = False; self.ld.append(self._ld)

    def handle_data(self, d):
        if self._in_title: self.title += d
        if self._in_ld: self._ld += d
        else: self.text += d


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "HSCF-audit/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace"), dict(r.headers)


def load_local():
    pages = {}
    for d, _, fs in os.walk(SITE):
        if "/assets" in d.replace(SITE, ""): continue
        for f in fs:
            if f.endswith(".html") and not f.startswith("._"):  # skip macOS AppleDouble files on external drives
                rel = os.path.relpath(os.path.join(d, f), SITE).replace(os.sep, "/")
                pages[rel] = open(os.path.join(d, f), encoding="utf-8").read()
    files = {n: open(os.path.join(SITE, n), encoding="utf-8").read() for n in ("robots.txt", "sitemap.xml", "llms.txt", "ai.txt") if os.path.exists(os.path.join(SITE, n))}
    return pages, files


def load_live(base):
    _, files_sm, _ = fetch(base + "sitemap.xml")
    urls = re.findall(r"<loc>([^<]+)</loc>", files_sm)
    pages = {}
    for u in urls + [base + "404.html"]:
        rel = u.replace(base, "") or "index.html"
        if rel.endswith("/"): rel += "index.html"
        try:
            status, body, _ = fetch(u); pages[rel] = body
        except Exception as e:
            pages[rel] = None; print(f"  could not fetch {u}: {e}")
    files = {"sitemap.xml": files_sm}
    for n in ("robots.txt", "llms.txt", "ai.txt"):
        try: files[n] = fetch(base + n)[1]
        except Exception: files[n] = None
    return pages, files


def resolve(href, page_rel):
    href = href.split("#")[0].split("?")[0]
    if not href or href.startswith(("http:", "https:", "mailto:", "tel:", "data:", "javascript:")): return None
    if href.startswith("/"): p = href.lstrip("/")
    else: p = os.path.normpath(os.path.join(os.path.dirname(page_rel), href)).replace(os.sep, "/")
    if p in (".", ""): return "index.html"
    if href.endswith("/"): p = p.rstrip("/") + "/index.html"
    return urllib.parse.unquote(p)


def audit(pages, files, live=False):
    E, W = [], []
    parsed = {}
    for rel, body in pages.items():
        if body is None: E.append(f"{rel}: page did not load"); continue
        pg = Page(); pg.feed(body); parsed[rel] = pg
    titles, descs = {}, {}
    sitemap_urls = set(re.findall(r"<loc>([^<]+)</loc>", files.get("sitemap.xml") or ""))
    for rel, pg in parsed.items():
        is404 = rel == "404.html"
        robots = pg.meta.get("robots", "")
        if not pg.title.strip(): E.append(f"{rel}: missing <title>")
        elif len(pg.title) > 65: W.append(f"{rel}: title is {len(pg.title)} characters (aim for 60 or fewer)")
        d = pg.meta.get("description", "")
        if not d: E.append(f"{rel}: missing meta description")
        elif not (70 <= len(d) <= 165): W.append(f"{rel}: description is {len(d)} characters (110-160 is best)")
        titles.setdefault(pg.title, []).append(rel); descs.setdefault(d, []).append(rel)
        if pg.h1 != 1: (W if is404 else E).append(f"{rel}: has {pg.h1} <h1> elements (needs exactly 1)")
        if not pg.lang: E.append(f"{rel}: <html> has no lang attribute")
        if not is404:
            if "noindex" in robots: E.append(f"{rel}: is marked noindex on the live site")
            if "draft-banner" in pages[rel]: E.append(f"{rel}: shows a draft banner")
            exp = BASE + ("" if rel == "index.html" else rel[:-len("index.html")] if rel.endswith("/index.html") else rel)
            if pg.canonical != exp: E.append(f"{rel}: canonical is {pg.canonical}, expected {exp}")
            if exp not in sitemap_urls: E.append(f"{rel}: not listed in sitemap.xml")
            if not {"en", "es", "x-default"} <= set(pg.hreflang): E.append(f"{rel}: missing hreflang en/es/x-default")
            else:
                twin = pg.hreflang["es" if (pg.lang or "en").startswith("en") else "en"]
                twin_rel = twin.replace(BASE, "") or "index.html"
                if twin_rel.endswith("/"): twin_rel += "index.html"
                tp = parsed.get(twin_rel)
                if not tp: E.append(f"{rel}: hreflang twin {twin_rel} does not exist")
                elif tp.hreflang.get((pg.lang or "en")[:2]) != pg.canonical: E.append(f"{rel}: hreflang is not reciprocal with {twin_rel}")
        for i, block in enumerate(pg.ld):
            try:
                data = json.loads(block)
                for node in (data.get("@graph", [data]) if isinstance(data, dict) else data):
                    if "@type" not in node: E.append(f"{rel}: JSON-LD block {i + 1} has a node without @type")
            except json.JSONDecodeError as e:
                E.append(f"{rel}: JSON-LD block {i + 1} does not parse ({e})")
        if not pg.ld and not is404: W.append(f"{rel}: no structured data")
        for im in pg.imgs:
            if "alt" not in im: E.append(f"{rel}: image without alt attribute ({(im.get('src') or '')[:60]})")
        if not live:
            for href in pg.links:
                if not href: continue
                target = resolve(href, rel)
                if target and not os.path.exists(os.path.join(SITE, target)):
                    if is404 and href.startswith("/"): continue
                    E.append(f"{rel}: broken link → {href}")
                frag = href.split("#")[1] if "#" in href and href.split("#")[0] in ("",) else None
                if frag and frag not in pg.ids and frag != "main": W.append(f"{rel}: in-page link #{frag} has no target")
            kb = len(pages[rel].encode()) / 1024
            if kb > 250: W.append(f"{rel}: HTML is {kb:.0f} KB")
    for t, rels in titles.items():
        if len(rels) > 1 and t: E.append(f"duplicate title on {', '.join(rels)}")
    for d, rels in descs.items():
        if len(rels) > 1 and d: W.append(f"duplicate description on {', '.join(rels)}")
    # crawler files
    rb = files.get("robots.txt") or ""
    if not rb: E.append("robots.txt is missing")
    else:
        groups = re.split(r"\n\s*\n", rb)
        for g in groups:
            if re.search(r"User-agent:\s*\*", g) and re.search(r"^Disallow:\s*/\s*$", g, re.M): E.append("robots.txt blocks every crawler (User-agent: * / Disallow: /)")
        if "Sitemap:" not in rb: W.append("robots.txt does not point to the sitemap")
    if not files.get("ai.txt"): W.append("ai.txt is missing")
    llms = files.get("llms.txt") or ""
    if not llms: E.append("llms.txt is missing")
    else:
        if not llms.startswith("# "): E.append("llms.txt must start with an H1 (# Site name)")
        for u in re.findall(r"\]\((https://hscfdoral\.com/[^)]*)\)", llms):
            rel = u.replace(BASE, "") or "index.html"
            if rel.endswith("/"): rel += "index.html"
            if rel.endswith(".html") and rel not in pages: E.append(f"llms.txt links to a page that does not exist: {u}")
    return E, W


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true", help="audit https://hscfdoral.com instead of site/")
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--json", help="write results to this file")
    a = ap.parse_args()
    pages, files = load_live(a.base) if a.live else load_local()
    E, W = audit(pages, files, live=a.live)
    print(f"Audited {len(pages)} pages ({'live' if a.live else 'site/'})")
    for w in W: print("warning:", w)
    for e in E: print("ERROR:", e)
    print(f"{len(E)} error(s), {len(W)} warning(s)")
    if a.json: json.dump({"errors": E, "warnings": W, "pages": len(pages)}, open(a.json, "w"), indent=1)
    sys.exit(1 if E else 0)


if __name__ == "__main__":
    main()
