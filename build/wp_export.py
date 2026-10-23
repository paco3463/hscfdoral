# -*- coding: utf-8 -*-
"""WordPress export for hscfdoral.com.

    python3 build/build.py --wp

Builds every page exactly as the static site does, but instead of writing site/ it produces:

    wordpress/dist/manifest.json   every page and post (head, main content, nav state), the shared header /
                                   footer / popup per language, static files (robots, sitemap, llms, feeds)
                                   and the old-URL redirects. Imported by the theme (WP-CLI or REST).
    wordpress/dist/hscf/           the theme folder: wordpress/theme/ + site/assets/
    wordpress/dist/hscf.zip        the same theme as a zip (Appearance > Themes > Add New > Upload)

The generator stays the single source of truth. WordPress stores and serves the result, and its editor can
change page text; the importer never overwrites a page someone edited in WordPress unless forced.
"""
import hashlib, json, os, re, shutil, zipfile

THEME_NAME = "hscf"
FORMAT = "hscf-wp-1"
POST_RE = re.compile(r"^(en/)?(\d{4})/(\d{2})/([^/]+)/$")


def _strip_index(p):
    return p[: -len("index.html")] if p.endswith("index.html") else p


def _abs_assets(text):
    """Absolute asset URLs (JSON-LD, og:image, llms.txt) point into the theme folder on WordPress."""
    return text.replace("https://hscfdoral.com/assets/", "{{theme}}/assets/")


def _h1(html):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    if not m: return ""
    t = re.sub(r"<span class=\"creds\">.*?</span>", "", m.group(1))
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t)).strip()


def finalize(b):
    E = b.WP_EXPORT
    root = b.ROOT
    by_path = {}
    art_by_path = {}
    for a in b.ARTICLES:
        for lang in b.LANGS:
            art_by_path[b.ARTICLE_PATHS[lang][a["id"]]] = (a, lang)
    items, notfound = [], None
    for rec in E["pages"]:
        path = _strip_index(rec["cur"])
        if rec["cur"] == "404.html":
            notfound = {"head": _abs_assets(rec["head"]), "main": _abs_assets(rec["main"]), "lang": rec["lang"]}
            continue
        alt = _strip_index(rec["alt"])
        it = {"path": path, "lang": rec["lang"], "alt": alt, "active": rec["active"] or "",
              "title": _h1(rec["main"]) or rec["title"], "head": _abs_assets(rec["head"]), "main": _abs_assets(rec["main"]),
              "splash": rec["splash"], "extra": _abs_assets(rec["extra"])}
        m = POST_RE.match(path)
        if m and path in art_by_path:
            a, lang = art_by_path[path]
            meta = a["meta"]
            it.update({"type": "en_post" if m.group(1) else "post", "slug": m.group(4),
                       "date": (meta.get("date_published") or meta["date_modified"]) + " 12:00:00",
                       "modified": meta["date_modified"] + " 12:00:00", "excerpt": meta[lang]["summary"], "article_id": a["id"]})
        else:
            segs = [s for s in path.split("/") if s]
            it.update({"type": "page", "slug": segs[-1] if segs else "inicio",
                       "parent": ("/".join(segs[:-1]) + "/") if len(segs) > 1 else ""})
        it["hash"] = hashlib.md5((it["head"] + it["main"] + it["extra"] + it["splash"] + it["alt"] + it["active"]).encode()).hexdigest()
        items.append(it)
        by_path[path] = it
    # every page parent must exist
    for it in items:
        if it["type"] == "page" and it["parent"] and it["parent"] not in by_path:
            raise SystemExit(f"WordPress export: page /{it['path']} has no parent page /{it['parent']}")
    # shared parts per language; the header depends on which menu item is current
    partials = {"svgdefs": b.SVG_DEFS}
    actives = sorted({it["active"] for it in items} | {""})
    for lang in b.LANGS:
        for act in actives:
            h = b.header(lang, "x/index.html", act, "@@ALT@@/index.html")
            partials[f"header_{lang}_{act}"] = _abs_assets(h.replace("/@@ALT@@/", "@@ALT@@"))
        partials[f"footer_{lang}"] = _abs_assets(b.footer(lang, "x/index.html"))
        partials[f"modal_{lang}"] = _abs_assets(b.event_modal(lang, "x/index.html"))
    static = {p: _abs_assets(c) for p, c in E["static"].items()}
    redirects = [[src, dst] for src, dst in b.REDIRECTS]
    for p in b.C["es"].TEAM:
        redirects += [[old, p["id"] + "/"] for old in p["old"]]
    redirects += [[t["old"], "#testimonios"] for t in b.C["es"].TESTIMONIALS]
    manifest = {"format": FORMAT, "generated": b.TODAY, "site": b.BASE, "theme": THEME_NAME,
                "settings": {"blogname": "Healthy Solutions for Children and Families",
                             "blogdescription": "Centro bilingüe de salud mental en Doral, FL", "timezone_string": "America/New_York",
                             "contact_to": "info@hscfdoral.com", "permalink_structure": "/%year%/%monthnum%/%postname%/"},
                "partials": partials, "static": static, "redirects": redirects, "notfound": notfound, "items": items}
    dist = os.path.join(root, "wordpress", "dist")
    os.makedirs(dist, exist_ok=True)
    with open(os.path.join(dist, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False)
    # theme = PHP templates + the site's assets
    theme_dir = os.path.join(dist, THEME_NAME)
    if os.path.isdir(theme_dir): shutil.rmtree(theme_dir)
    shutil.copytree(os.path.join(root, "wordpress", "theme"), theme_dir)
    shutil.copytree(os.path.join(root, "site", "assets"), os.path.join(theme_dir, "assets"),
                    ignore=shutil.ignore_patterns(".DS_Store", "._*"))
    shutil.copy(os.path.join(root, "site", "assets", "img", "og-image.jpg"), os.path.join(theme_dir, "screenshot.jpg"))
    zpath = os.path.join(dist, THEME_NAME + ".zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for d, _, fs in os.walk(theme_dir):
            for fn in fs:
                full = os.path.join(d, fn)
                z.write(full, os.path.relpath(full, dist))
    n = {t: sum(1 for i in items if i["type"] == t) for t in ("page", "post", "en_post")}
    size = os.path.getsize(os.path.join(dist, "manifest.json")) / 1e6
    print(f"WordPress export: {n['page']} pages, {n['post']} Spanish posts, {n['en_post']} English posts, "
          f"{len(static)} static files, {len(redirects)} redirects -> wordpress/dist/manifest.json ({size:.1f} MB) and {THEME_NAME}.zip")
    return 0
