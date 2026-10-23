# -*- coding: utf-8 -*-
"""Blog pipeline for hscfdoral.com.

Reads content/articles/<id>/{meta.json,es.md,en.md}, validates them, renders the small markdown dialect
documented in CLAUDE.md, and builds the post pages, the Blog hub, the RSS feeds, and the data used by
sitemap.xml, llms.txt and llms-full.txt. Pure standard library; uses `jsonschema` when installed.

Post kinds (meta.kind):
  article  researched post with numbered sources. review_policy "clinician" (a licensed reviewer signs off)
           or "automatic" (published without individual review after the automatic safety gates pass).
  legacy   a post migrated from the old WordPress blog, kept at its original address.
Every post lives at /<yyyy>/<mm>/<es-slug>/ and /en/<yyyy>/<mm>/<en-slug>/ (date_published).
"""
import html, json, math, os, re, unicodedata
from datetime import date

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ART_DIR = os.path.join(ROOT, "content", "articles")
SCHEMA = os.path.join(ROOT, "schemas", "article.schema.json")
SEO_CONFIG = os.path.join(ROOT, "seo", "config.json")
SITE = os.path.join(ROOT, "site")
STRONG_KINDS = {"peer_reviewed", "systematic_review", "clinical_guideline"}
AUTO_MIN_SOURCES, AUTO_MIN_STRONG = 5, 2

UI = {
    "es": {
        "nav": "Blog", "by": "Por", "published": "Publicado", "updated": "Actualizado", "min_read": "min de lectura", "read_time": "Lectura",
        "author": "Autor", "reviewed_by": "Revisión clínica", "toc": "En este artículo", "sources": "Fuentes", "faq": "Preguntas frecuentes",
        "related": "Cómo podemos ayudarte", "related_reading": "Sigue leyendo", "all": "Ver todo el blog", "read": "Leer artículo",
        "crisis_h": "Si necesitas ayuda ahora mismo", "doi": "DOI", "gallery": "Imágenes",
        "draft": "Vista previa del borrador. Este artículo no es público.",
        "note_clinician": "Este artículo se basa en fuentes revisadas por pares y fue revisado por un profesional clínico. Es información general, no un diagnóstico ni un sustituto de la atención profesional.",
        "note_automatic": "Investigado en fuentes de salud reconocidas y redactado por el equipo editorial de Healthy Solutions con apoyo de herramientas de inteligencia artificial. Es información general: no es un diagnóstico ni sustituye la atención de un profesional.",
        "note_legacy": "Publicado originalmente el {date} en el blog de Healthy Solutions. Es información general y no sustituye la atención profesional.",
        "empty": "Pronto publicaremos nuevos artículos.", "filter_label": "Temas", "no_match": "No hay artículos con ese tema todavía.",
        "months": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
        "feed_title": "Blog de Healthy Solutions for Children and Families",
    },
    "en": {
        "nav": "Blog", "by": "By", "published": "Published", "updated": "Updated", "min_read": "min read", "read_time": "Reading time",
        "author": "Author", "reviewed_by": "Clinical review", "toc": "In this article", "sources": "Sources", "faq": "Frequently asked questions",
        "related": "How we can help", "related_reading": "Keep reading", "all": "See the whole blog", "read": "Read article",
        "crisis_h": "If you need help right now", "doi": "DOI", "gallery": "Images",
        "draft": "Draft preview. This article is not public.",
        "note_clinician": "This article is based on peer-reviewed sources and was reviewed by a clinician. It is general information, not a diagnosis or a substitute for professional care.",
        "note_automatic": "Researched in established health sources and written by the Healthy Solutions editorial team with the help of AI tools. It is general information: not a diagnosis or a substitute for professional care.",
        "note_legacy": "Originally published on {date} on the Healthy Solutions blog. It is general information and not a substitute for professional care.",
        "empty": "New articles are on the way.", "filter_label": "Topics", "no_match": "No articles on that topic yet.",
        "months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
        "feed_title": "Healthy Solutions for Children and Families blog",
    },
}

VALID_PAGES = {"home", "about", "services", "staff", "insurance", "blog", "activities", "news", "events", "gallery", "contact", "areas"}


def fmt_date(iso, lang):
    if not iso: return ""
    y, m, d = iso.split("-")
    months = UI[lang]["months"]
    return f"{months[int(m) - 1]} {int(d)}, {y}" if lang == "en" else f"{int(d)} de {months[int(m) - 1]} de {y}"


def slugify(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


# ------------------------------------------------------------------ loading + validation
def _schema_validate(meta, path, errors):
    try:
        import jsonschema
        Validator = jsonschema.Draft202012Validator   # jsonschema 4.0+
    except (ImportError, AttributeError):
        return False                                  # older or missing jsonschema: use the built-in checks
    schema = json.load(open(SCHEMA, encoding="utf-8"))
    for e in sorted(Validator(schema).iter_errors(meta), key=lambda e: [str(x) for x in e.path]):
        errors.append(f"{path}: {'/'.join(str(x) for x in e.path) or '(root)'}: {e.message}")
    return True


def _basic_validate(meta, path, errors):
    for k in ["id", "status", "topic_cluster", "audience", "services", "condition", "en", "es", "author", "date_modified"]:
        if k not in meta: errors.append(f"{path}: missing '{k}'")
    if meta.get("status") not in ("draft", "in_review", "published", "archived"):
        errors.append(f"{path}: status must be draft, in_review, published or archived")
    if meta.get("kind", "article") not in ("article", "legacy"): errors.append(f"{path}: kind must be article or legacy")
    for lang in ("en", "es"):
        loc = meta.get(lang, {})
        for k in ("slug", "title", "seo_title", "description", "primary_keyword", "summary"):
            if not loc.get(k): errors.append(f"{path}: {lang}.{k} is required")
        if len(loc.get("seo_title", "")) > 62: errors.append(f"{path}: {lang}.seo_title is over 62 characters")
        d = len(loc.get("description", ""))
        if d and not (110 <= d <= 158): errors.append(f"{path}: {lang}.description is {d} characters (110-158)")


def publish_gate(meta):
    """Reasons this post may NOT be live. Empty list = allowed. Used by the build and by the automatic writer."""
    why = []
    kind = meta.get("kind", "article")
    policy = meta.get("review_policy", "clinician" if kind == "article" else "legacy")
    if not meta.get("date_published"): why.append("needs date_published")
    if kind == "legacy":
        if not meta.get("legacy_url"): why.append("legacy posts need legacy_url (their old address)")
        return why
    srcs = meta.get("sources", [])
    if policy == "clinician":
        if not meta.get("medical_reviewer"): why.append("review_policy is clinician, so a medical_reviewer is required")
    elif policy == "automatic":
        if meta.get("risk") == "high": why.append("risk is high: high-risk topics must be reviewed by a clinician (review_policy clinician)")
        if len(srcs) < AUTO_MIN_SOURCES: why.append(f"automatic posts need at least {AUTO_MIN_SOURCES} sources (has {len(srcs)})")
        strong = sum(1 for s in srcs if s.get("kind") in STRONG_KINDS)
        if strong < AUTO_MIN_STRONG: why.append(f"automatic posts need at least {AUTO_MIN_STRONG} peer-reviewed, systematic-review or guideline sources (has {strong})")
        if any(not s.get("verified_on") for s in srcs): why.append("every source needs verified_on (the date it was opened and checked)")
        if meta.get("medical_reviewer"): why.append("automatic posts must not list a medical_reviewer; use review_policy clinician")
    else:
        why.append(f"unknown review_policy '{policy}' for an article")
    return why


def load(service_ids, team_ids, include_drafts=False, strict=True):
    """Return (articles, errors, warnings). Each article dict has meta + bodies."""
    errors, warnings, arts = [], [], []
    clusters = {c["id"] for c in json.load(open(SEO_CONFIG, encoding="utf-8")).get("topic_clusters", [])}
    if not os.path.isdir(ART_DIR):
        return [], [], []
    slugs = {"en": {}, "es": {}}
    for name in sorted(os.listdir(ART_DIR)):
        folder = os.path.join(ART_DIR, name)
        if name.startswith((".", "_")) or not os.path.isdir(folder):
            continue
        rp = f"content/articles/{name}"
        try:
            meta = json.load(open(os.path.join(folder, "meta.json"), encoding="utf-8"))
        except FileNotFoundError:
            errors.append(f"{rp}: meta.json is missing"); continue
        except json.JSONDecodeError as e:
            errors.append(f"{rp}/meta.json: invalid JSON ({e})"); continue
        if not _schema_validate(meta, rp + "/meta.json", errors):
            _basic_validate(meta, rp + "/meta.json", errors)
        if meta.get("id") != name:
            errors.append(f"{rp}: meta.id '{meta.get('id')}' must equal the folder name")
        st = meta.get("status"); kind = meta.get("kind", "article")
        if st == "published":
            for why in publish_gate(meta): errors.append(f"{rp}: cannot be published: {why}")
            if meta.get("date_published", "9999") > date.today().isoformat():
                warnings.append(f"{rp}: date_published is in the future; it is built now with that date")
        if meta.get("topic_cluster") not in clusters:
            errors.append(f"{rp}: topic_cluster '{meta.get('topic_cluster')}' is not in seo/config.json")
        for s in meta.get("services", []):
            if s not in service_ids: errors.append(f"{rp}: unknown service '{s}'")
        rev = meta.get("medical_reviewer") or {}
        if rev.get("team_id") and rev["team_id"] not in team_ids:
            errors.append(f"{rp}: medical_reviewer.team_id '{rev['team_id']}' is not on the staff")
        for im in [meta.get("hero_image")] + list(meta.get("gallery") or []):
            if im and not im["src"].startswith("http") and not os.path.exists(os.path.join(SITE, im["src"].lstrip("/"))):
                errors.append(f"{rp}: image {im['src']} does not exist in site/")
        bodies = {}
        for lang in ("en", "es"):
            try:
                bodies[lang] = open(os.path.join(folder, f"{lang}.md"), encoding="utf-8").read()
            except FileNotFoundError:
                errors.append(f"{rp}: {lang}.md is missing"); bodies[lang] = ""
            sl = meta.get(lang, {}).get("slug")
            if sl:
                if sl in slugs[lang]: errors.append(f"{rp}: {lang} slug '{sl}' is already used by {slugs[lang][sl]}")
                slugs[lang][sl] = name
        src_ids = {s.get("id") for s in meta.get("sources", [])}
        for lang, body in bodies.items():
            cited = set()
            for grp in re.findall(r"\[(\d+(?:\s*,\s*\d+)*)\](?!\()", body):
                cited |= {int(x) for x in re.split(r"\s*,\s*", grp)}
            for c in sorted(cited - src_ids): errors.append(f"{rp}/{lang}.md cites [{c}] but there is no source {c}")
            for u in sorted(src_ids - cited): warnings.append(f"{rp}/{lang}.md never cites source {u}")
            if kind == "article":
                words = word_count(body)
                if words < 600: warnings.append(f"{rp}/{lang}.md has only {words} words (aim for 900-1,600)")
            if re.search(r"^# ", body, re.M): errors.append(f"{rp}/{lang}.md uses '# ' (H1). Start at '## '.")
        visible = st == "published" or (include_drafts and st in ("draft", "in_review"))
        if visible:
            arts.append({"id": name, "meta": meta, "body": bodies})
    known = {a["id"] for a in arts}
    for a in arts:
        for lang in ("en", "es"):
            for kind, ident in re.findall(r"\]\((service|page|article):([a-z0-9-]+)\)", a["body"][lang]):
                if kind == "service" and ident not in service_ids: errors.append(f"content/articles/{a['id']}/{lang}.md links to unknown service '{ident}'")
                if kind == "page" and ident not in VALID_PAGES: errors.append(f"content/articles/{a['id']}/{lang}.md links to unknown page '{ident}'")
                if kind == "article" and ident not in known:
                    (errors if strict else warnings).append(f"content/articles/{a['id']}/{lang}.md links to article '{ident}', which is not published")
    arts.sort(key=lambda a: (a["meta"].get("date_published") or a["meta"]["date_modified"], a["id"]), reverse=True)
    return arts, errors, warnings


# ------------------------------------------------------------------ markdown
def render_markdown(md, resolve_link):
    """## / ### headings, paragraphs, - and 1. lists, > callouts, **bold**, *italic*,
    [text](url | service:id | page:id | article:id), [n] citations. Returns (html, [(id, text)] of ## headings)."""
    headings, out, para, lst, quote = [], [], [], [], []
    lst_type = None
    used_ids = set()

    def inline(t):
        t = html.escape(t, quote=False)
        def link(m):
            text, url = m.group(1), m.group(2)
            href, external = resolve_link(html.unescape(url))
            extra = ' target="_blank" rel="noopener"' if external else ""
            return f'<a href="{html.escape(href, quote=True)}"{extra}>{text}</a>'
        t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, t)
        def cite(m):
            ids = [x.strip() for x in m.group(1).split(",")]
            return '<sup class="cite">' + ", ".join(f'<a href="#ref-{i}" aria-label="Source {i}">{i}</a>' for i in ids) + "</sup>"
        t = re.sub(r"\s?\[(\d+(?:\s*,\s*\d+)*)\](?!\()", cite, t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<em>\1</em>", t)
        return t

    def flush_para():
        if para: out.append("<p>" + inline(" ".join(para)) + "</p>"); para.clear()

    def flush_list():
        nonlocal lst_type
        if lst:
            tag = "ol" if lst_type == "ol" else "ul"
            cls = ' class="house-list"' if tag == "ul" else ' class="num-list"'
            out.append(f"<{tag}{cls}>" + "".join(f"<li>{inline(x)}</li>" for x in lst) + f"</{tag}>")
            lst.clear(); lst_type = None

    def flush_quote():
        if quote: out.append('<aside class="callout"><p>' + inline(" ".join(quote)) + "</p></aside>"); quote.clear()

    def flush_all():
        flush_para(); flush_list(); flush_quote()

    for raw in md.replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        if not line.strip():
            flush_all(); continue
        m = re.match(r"^(#{2,3})\s+(.*)$", line)
        if m:
            flush_all()
            level, text = len(m.group(1)), m.group(2).strip()
            hid = slugify(text) or "section"
            base, n = hid, 2
            while hid in used_ids: hid = f"{base}-{n}"; n += 1
            used_ids.add(hid)
            if level == 2: headings.append((hid, re.sub(r"\s?\[\d+(?:\s*,\s*\d+)*\]", "", text)))
            out.append(f'<h{level} id="{hid}">{inline(text)}</h{level}>')
            continue
        m = re.match(r"^\s*[-*]\s+(.*)$", line)
        n = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
        if m or n:
            flush_para(); flush_quote()
            t = "ul" if m else "ol"
            if lst_type and lst_type != t: flush_list()
            lst_type = t; lst.append((m or n).group(1)); continue
        if line.startswith(">"):
            flush_para(); flush_list(); quote.append(line.lstrip("> ").strip()); continue
        if lst and raw.startswith(("  ", "\t")):
            lst[-1] += " " + line.strip(); continue
        flush_list(); flush_quote(); para.append(line.strip())
    flush_all()
    return "\n".join(out), headings


def plain_text(md):
    t = re.sub(r"\[([^\]]+)\]\((?:service|page|article):[^)]+\)", r"\1", md)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 (\2)", t)
    return t.replace("**", "").strip()


def word_count(md):
    return len(re.findall(r"\w+", plain_text(md)))


# ------------------------------------------------------------------ helpers
def _resolver(b, lang, cur):
    def resolve(url):
        if url.startswith(("http://", "https://", "mailto:", "tel:")):
            return url, url.startswith("http")
        kind, _, ident = url.partition(":")
        if kind == "service": return b.rel(b.path_for("service", lang, ident), cur), False
        if kind == "page": return b.rel(b.path_for(ident, lang), cur), False
        if kind == "article": return b.rel(b.path_for("article", lang, ident), cur), False
        return url, False
    return resolve


def _small(src):
    """The -sm.webp version of a local image if the import made one."""
    if src.startswith("http"): return None
    sm = src.replace(".webp", "-sm.webp")
    return sm if sm != src and os.path.exists(os.path.join(SITE, sm)) else None


def _img(b, cur, im, lang, cls, eager=False, sizes="(max-width: 700px) 92vw, 460px"):
    src = im["src"] if im["src"].startswith("http") else b.rel(im["src"].lstrip("/"), cur)
    sm = _small(im["src"])
    srcset = f' srcset="{b.rel(sm, cur)} 560w, {src} {im["width"]}w" sizes="{sizes}"' if sm and im["width"] > 560 else ""
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    return f'<div class="{cls}"><img src="{src}"{srcset} alt="{html.escape(im["alt_" + lang], quote=True)}" width="{im["width"]}" height="{im["height"]}" {load} decoding="async"></div>'


def _author(m, lang):
    a = m["author"]
    return a["name"]


def cluster_names(lang):
    return {c["id"]: c[lang] for c in json.load(open(SEO_CONFIG, encoding="utf-8")).get("topic_clusters", [])}


def card(b, lang, cur, a):
    U = UI[lang]; m = a["meta"]; L = m[lang]
    mins = max(1, math.ceil(word_count(a["body"][lang]) / 200))
    date_s = fmt_date(m.get("date_published") or m["date_modified"], lang)
    media = _img(b, cur, m["hero_image"], lang, "article-card-img", sizes="(max-width: 700px) 92vw, 380px") if m.get("hero_image") else ""
    return (f'<a class="article-card" href="{b.rel(b.path_for("article", lang, a["id"]), cur)}" data-tags="{m["topic_cluster"]}">{media}'
            f'<div class="article-card-body"><span class="article-card-meta">{date_s} <span aria-hidden="true">·</span> {mins} {U["min_read"]}</span>'
            f'<strong>{html.escape(L["title"])}</strong><span class="article-card-summary">{html.escape(L["summary"])}</span>'
            f'<span class="text-link">{U["read"]}</span></div></a>')


# ------------------------------------------------------------------ page builders
def build_all(b, arts, drafts=False):
    """b = the build module. Writes post pages, the hub and RSS feeds. Returns [(es_path, en_path, lastmod)]."""
    urls = []
    for lang in ("es", "en"):
        build_hub(b, lang, arts)
        build_feed(b, lang, [a for a in arts if a["meta"]["status"] == "published"])
        for a in arts:
            build_article(b, lang, a, arts)
    urls.append((b.path_for("blog", "es"), b.path_for("blog", "en"), max([a["meta"]["date_modified"] for a in arts] or [b.TODAY])))
    for a in arts:
        urls.append((b.path_for("article", "es", a["id"]), b.path_for("article", "en", a["id"]), a["meta"]["date_modified"]))
    return urls


def build_hub(b, lang, arts):
    U = UI[lang]; BU = b.C[lang].UI; H = b.C[lang].BLOG
    cur = b.path_for("blog", lang); alt = b.path_for("blog", b.OTHER[lang])
    items = [(BU["home"], b.path_for("home", lang)), (BU["nav_blog"], cur)]
    names = cluster_names(lang)
    present = [c for c in names if any(a["meta"]["topic_cluster"] == c for a in arts)]
    chips = (f'<div class="filters" data-filters=".article-card" role="group" aria-label="{U["filter_label"]}"><span class="filters-label">{U["filter_label"]}</span>'
             f'<button class="chip" type="button" aria-pressed="true" data-filter="all">{H["filter_all"]}</button>'
             + "".join(f'<button class="chip" type="button" aria-pressed="false" data-filter="{c}">{names[c]}</button>' for c in present) + "</div>") if len(present) > 1 else ""
    grid = (chips + f'<div class="article-grid">{"".join(card(b, lang, cur, a) for a in arts)}</div><p class="team-empty" hidden>{U["no_match"]}</p>') if arts else f'<p class="lead">{U["empty"]}</p>'
    body = b.page_hero(lang, cur, items, H["h1"], H["lead"]) + f"""
<section class="section section--flush-top"><div class="wrap">
  {grid}
</div></section>
{b.cta_band(lang, cur)}
"""
    ld = [b.breadcrumb_ld(items),
          {"@context": "https://schema.org", "@type": "Blog", "name": H["h1"] + " · Healthy Solutions", "url": b.absurl(cur), "inLanguage": lang,
           "publisher": {"@id": b.BASE + "#practice"}, "isPartOf": {"@id": b.BASE + "#website"},
           "blogPost": [{"@type": "BlogPosting", "headline": a["meta"][lang]["title"], "url": b.absurl(b.path_for("article", lang, a["id"])),
                         "datePublished": a["meta"].get("date_published") or a["meta"]["date_modified"]} for a in arts[:30]]}]
    b.write(cur, b.page(lang, cur, "blog", alt, H["title"], H["description"], body, ld))


def build_feed(b, lang, arts):
    U = UI[lang]
    path = ("blog/" if lang == "es" else "en/blog/") + "feed.xml"
    esc = lambda s: html.escape(s, quote=False)
    def rfc(d):
        y, m, dd = map(int, d.split("-"))
        return date(y, m, dd).strftime("%a, %d %b %Y 12:00:00 -0400")
    items = "".join(
        f"<item><title>{esc(a['meta'][lang]['title'])}</title><link>{b.absurl(b.path_for('article', lang, a['id']))}</link>"
        f"<guid isPermaLink=\"true\">{b.absurl(b.path_for('article', lang, a['id']))}</guid><pubDate>{rfc(a['meta']['date_published'])}</pubDate>"
        f"<description>{esc(a['meta'][lang]['summary'])}</description></item>\n" for a in arts[:20])
    xml = (f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>\n'
           f"<title>{esc(U['feed_title'])}</title><link>{b.absurl(b.path_for('blog', lang))}</link><language>{lang}</language>"
           f"<description>{esc(b.C[lang].BLOG['description'])}</description>"
           f'<atom:link href="{b.BASE}{path}" rel="self" type="application/rss+xml"/>\n{items}</channel></rss>\n')
    b.write(path, xml)


def build_article(b, lang, a, arts):
    U = UI[lang]; BU = b.C[lang].UI; m = a["meta"]; L = m[lang]
    other = b.OTHER[lang]
    kind = m.get("kind", "article"); policy = m.get("review_policy", "clinician" if kind == "article" else "legacy")
    cur = b.path_for("article", lang, a["id"]); alt = b.path_for("article", other, a["id"])
    items = [(BU["home"], b.path_for("home", lang)), (BU["nav_blog"], b.path_for("blog", lang)), (L["title"], cur)]
    body_html, heads = render_markdown(a["body"][lang], _resolver(b, lang, cur))
    words = word_count(a["body"][lang]); mins = max(1, math.ceil(words / 200))
    is_live = m["status"] == "published"
    r = m.get("medical_reviewer")
    pub = m.get("date_published") or m["date_modified"]
    meta_row = f"""<dl class="meta-row">
  <div><dt>{U['author']}</dt><dd>{html.escape(_author(m, lang))}</dd></div>
  <div><dt>{U['published']}</dt><dd>{fmt_date(pub, lang)}</dd></div>
  {f'<div><dt>{U["reviewed_by"]}</dt><dd>{html.escape(r["name"])}, {html.escape(r["credentials"])}</dd></div>' if r else ''}
  <div><dt>{U['read_time']}</dt><dd>{mins} {U['min_read']}</dd></div>
</dl>"""
    banner = "" if is_live else f'<div class="draft-banner" role="note">{U["draft"]}</div>'
    hero_media = _img(b, cur, m["hero_image"], lang, "house-img house", eager=True) if m.get("hero_image") else None
    srcs = sorted(m.get("sources") or [], key=lambda s: s["id"])
    toc_items = "".join(f'<li><a href="#{hid}">{html.escape(t)}</a></li>' for hid, t in heads) + (f'<li><a href="#sources">{U["sources"]}</a></li>' if srcs else "")
    show_toc = len(heads) >= 3
    refs = "".join(
        f'<li id="ref-{s["id"]}">{html.escape(s["authors"])} ({s["year"]}). <a href="{html.escape(s["url"], quote=True)}" target="_blank" rel="noopener">{html.escape(s["title"])}</a>. '
        f'<em>{html.escape(s["publisher"])}</em>.' + (f' {U["doi"]}: {html.escape(s["doi"])}.' if s.get("doi") else "") + "</li>" for s in srcs)
    note = U["note_legacy"].format(date=fmt_date(pub, lang)) if kind == "legacy" else (U["note_clinician"] if r else U["note_automatic"])
    gallery = ""
    if m.get("gallery"):
        labels = html.escape(json.dumps({"close": b.C[lang].GALLERY["close"], "prev": b.C[lang].GALLERY["prev"], "next": b.C[lang].GALLERY["next"]}, ensure_ascii=False), quote=True)
        tiles = "".join(f'<li><a class="g-item" href="{b.rel(im["src"], cur)}" aria-label="{b.C[lang].GALLERY["open"]}: {html.escape(im["alt_" + lang], quote=True)}">'
                        f'<img src="{b.rel(_small(im["src"]) or im["src"], cur)}" alt="{html.escape(im["alt_" + lang], quote=True)}" width="{im["width"]}" height="{im["height"]}" loading="lazy" decoding="async"></a></li>'
                        for im in [m["hero_image"]] + m["gallery"])
        gallery = f'<h2 id="imagenes">{U["gallery"]}</h2><ul class="gallery gallery--post" data-gallery data-labels="{labels}">{tiles}</ul>'
    faq = L.get("faq") or []
    faq_html = f'<section class="section"><div class="wrap"><div class="section-head"><h2>{U["faq"]}</h2></div>{b.faq_block(faq)}</div></section>' if faq else ""
    more = [x for x in arts if x["id"] != a["id"] and (x["meta"]["topic_cluster"] == m["topic_cluster"] or set(x["meta"]["services"]) & set(m["services"]))][:3]
    more_html = (f'<section class="section section--tight section--flush-top"><div class="wrap"><div class="section-head"><h2>{U["related_reading"]}</h2></div>'
                 f'<div class="article-grid">{"".join(card(b, lang, cur, x) for x in more)}</div>'
                 f'<p class="mt-l"><a class="text-link" href="{b.rel(b.path_for("blog", lang), cur)}">{U["all"]}</a></p></div></section>') if more else ""
    toc_mobile = f'<details class="toc toc-mobile"><summary class="toc-h">{U["toc"]}</summary><ol>{toc_items}</ol></details>' if show_toc else ""
    toc_aside = f'<nav class="toc" aria-label="{U["toc"]}"><p class="toc-h">{U["toc"]}</p><ol>{toc_items}</ol></nav>' if show_toc else ""
    body = banner + b.page_hero(lang, cur, items, html.escape(L["title"]), html.escape(L["summary"]), hero_media, meta_row) + f"""
<section class="section section--blush"><div class="wrap content-grid">
  <article class="prose article-body" lang="{lang}">
    {toc_mobile}
    {body_html}
    {gallery}
    <aside class="crisis-note article-crisis"><h2>{U['crisis_h']}</h2><p>{BU['crisis']}</p></aside>
    <div class="review-box"><p>{note}</p></div>
    {f'<h2 id="sources">{U["sources"]}</h2><ol class="ref-list">{refs}</ol>' if srcs else ''}
  </article>
  <div class="article-aside">
    {toc_aside}
    {b.aside_card(lang, cur)}
  </div>
</div></section>
{faq_html}
<section class="section section--tight"><div class="wrap">
  <div class="section-head"><h2>{U['related']}</h2></div>
  {b.related_cards(lang, cur, m['services'][:3])}
</div></section>
{more_html}
{b.cta_band(lang, cur)}
"""
    url = b.absurl(cur)
    org = {"@id": b.BASE + "#practice"}
    au = m["author"]
    author = {"@type": "Organization", "@id": b.BASE + "#practice", "name": au["name"]} if au["type"] == "Organization" else \
             {"@type": "Person", "name": au["name"], **({"url": b.absurl(b.path_for("person", lang, au["team_id"]))} if au.get("team_id") else {})}
    image = (m["hero_image"]["src"] if m["hero_image"]["src"].startswith("http") else b.BASE + m["hero_image"]["src"].lstrip("/")) if m.get("hero_image") else b.BASE + "assets/img/og-image.jpg"
    page_node = {"@type": "MedicalWebPage" if kind == "article" else "WebPage", "@id": url + "#webpage", "url": url, "name": L["title"], "description": L["description"],
                 "inLanguage": lang, "isPartOf": {"@id": b.BASE + "#website"}, "mainEntity": {"@id": url + "#article"}, "breadcrumb": {"@id": url + "#breadcrumb"},
                 "about": {"@type": "MedicalCondition" if m["condition"].get("is_medical_condition", True) else "Thing", "name": m["condition"]["name_" + lang],
                           **({"sameAs": m["condition"]["same_as"]} if m["condition"].get("same_as") else {})}}
    if kind == "article":
        page_node["audience"] = {"@type": "PeopleAudience", "audienceType": m["audience"]}
        page_node["lastReviewed"] = r["reviewed_on"] if r else m["date_modified"]
    if r:
        page_node["reviewedBy"] = {"@type": "Person", "name": r["name"], "honorificSuffix": r["credentials"], "worksFor": org,
                                   **({"url": b.absurl(b.path_for("person", lang, r["team_id"]))} if r.get("team_id") else {})}
    art_node = {"@type": "BlogPosting", "@id": url + "#article", "headline": L["title"], "description": L["description"], "inLanguage": lang,
                "mainEntityOfPage": {"@id": url + "#webpage"}, "author": author, "publisher": org, "datePublished": pub, "dateModified": m["date_modified"],
                "wordCount": words, "articleSection": cluster_names(lang).get(m["topic_cluster"], m["topic_cluster"]),
                "keywords": ", ".join([L["primary_keyword"]] + L.get("secondary_keywords", [])), "image": image,
                "translationOfWork" if lang == "en" else "workTranslation": {"@id": b.absurl(alt) + "#article"}}
    if srcs:
        art_node["citation"] = [{"@type": "ScholarlyArticle" if s["kind"] in ("peer_reviewed", "systematic_review") else "CreativeWork",
                                 "name": s["title"], "author": s["authors"], "datePublished": str(s["year"]), "publisher": s["publisher"], "url": s["url"],
                                 **({"sameAs": "https://doi.org/" + s["doi"]} if s.get("doi") else {})} for s in srcs]
    crumbs = b.breadcrumb_ld(items); crumbs["@id"] = url + "#breadcrumb"; crumbs.pop("@context", None)
    ld = [{"@context": "https://schema.org", "@graph": [page_node, art_node, crumbs]}] + ([b.faq_ld(faq)] if faq else [])
    out = b.page(lang, cur, "blog", alt, L["seo_title"], L["description"], body, ld, og_image=image,
                 robots=None if is_live else "noindex, nofollow")
    b.write(cur, out)


def related_for_service(b, lang, cur, arts, service_id):
    """Cards for posts that list this service. Returns '' when none."""
    picks = [a for a in arts if service_id in a["meta"]["services"] and a["meta"]["status"] == "published"][:3]
    if not picks: return ""
    return (f'<section class="section section--tight section--flush-top"><div class="wrap"><div class="section-head"><h2>{UI[lang]["related_reading"]}</h2></div>'
            f'<div class="article-grid">{"".join(card(b, lang, cur, a) for a in picks)}</div></div></section>')
