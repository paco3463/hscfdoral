# -*- coding: utf-8 -*-
"""Static site generator for hscfdoral.com.

Spanish is the main language and lives at the site root on the same addresses the old WordPress site used
(/about-us/, /aba/, /seguros/, /2022/07/<post>/ ...). English mirrors every page under /en/.
Outputs standalone HTML pages (folder/index.html) into ../site.

    python3 build/build.py            build the live site into site/
    python3 build/build.py --check    validate content and articles only
    python3 build/build.py --drafts   also build draft articles into preview/ (never deploy preview/)
"""
import datetime, html, json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(__file__))
import content_en, content_es
import articles as ART

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "site")
BASE = "https://hscfdoral.com/"
TODAY = datetime.date.today().isoformat()
C = {"en": content_en, "es": content_es}
MEDIA = json.load(open(os.path.join(ROOT, "build", "media.json"), encoding="utf-8"))
ARTICLES = []                       # visible articles for this build (filled in main)
ARTICLE_PATHS = {"en": {}, "es": {}}
ABS_LINKS = False                   # True while building 404.html, so links work from any depth
LANGS = ("es", "en")
OTHER = {"es": "en", "en": "es"}
TEL1, TEL2 = "+13055945658", "+17864239495"


def _smart(v):
    """Typographic apostrophes and quotes in page copy."""
    if isinstance(v, str):
        v = re.sub(r"(?<=[A-Za-zÀ-ÿ])'(?=[A-Za-zÀ-ÿ])", "\u2019", v)
        v = re.sub(r'(^|[\s(])"(?=[^\s>])', "\\1\u201c", v)
        v = re.sub(r'(?<=[.!?,])"', "\u201d", v)
        return v
    if isinstance(v, list): return [_smart(x) for x in v]
    if isinstance(v, dict): return {k: (_smart(x) if k not in ("id", "img", "slug", "services", "staff", "related", "nearby", "tags", "old", "videos", "fig") else x) for k, x in v.items()}
    return v

for _m in C.values():
    for _n in [n for n in dir(_m) if n.isupper() and n not in ("FINDER", "FINDER_TESTING", "COURSES")]:
        setattr(_m, _n, _smart(getattr(_m, _n)))

EXTRA = {
    "es": {"locale": "es_US", "main_nav": "Principal", "crumbs": "Ruta de navegación", "splash_aria": "Entrar al sitio web",
           "portrait_of": "Retrato de", "close": "Cerrar", "who_label": "Elige para quién buscas apoyo", "nf_other": "Go to the English home page",
           "mailto_ok": "Tu aplicación de correo debería abrirse con tu solicitud lista. Solo presiona enviar.",
           "mail_subject": "Solicitud de cita desde hscfdoral.com", "logos_label": "Seguros con los que trabajamos",
           "play": "Reproducir", "in_network_short": "En la red"},
    "en": {"locale": "en_US", "main_nav": "Main", "crumbs": "Breadcrumb", "splash_aria": "Enter the website",
           "portrait_of": "Portrait of", "close": "Close", "who_label": "Choose who you're looking for support for", "nf_other": "Ir a la página de inicio en español",
           "mailto_ok": "Your email app should open with your request filled in. Just press send.",
           "mail_subject": "Appointment request from hscfdoral.com", "logos_label": "Insurance plans we work with",
           "play": "Play", "in_network_short": "In network"},
}

ADDRESS = {"@type": "PostalAddress", "streetAddress": "8245 NW 36th St, Ste 7", "addressLocality": "Doral",
           "addressRegion": "FL", "postalCode": "33166", "addressCountry": "US"}

# ---------------------------------------------------------------- routing
PAGES = {
    "home": ("", "en/"), "about": ("about-us/", "en/about/"), "activities": ("actividades/", "en/activities/"),
    "news": ("novedades/", "en/news/"), "events": ("eventos/", "en/events/"), "gallery": ("galeria/", "en/gallery/"),
    "services": ("servicios/", "en/services/"), "insurance": ("seguros/", "en/insurance/"), "staff": ("staff/", "en/staff/"),
    "blog": ("blog/", "en/blog/"), "contact": ("contacto/", "en/contact/"), "areas": ("areas/", "en/areas/"),
}

def path_for(key, lang, ident=None):
    """Site-relative file path of a page, e.g. 'aba/index.html' or 'en/aba-therapy/index.html'."""
    i = 0 if lang == "es" else 1
    if key in PAGES: p = PAGES[key][i]
    elif key == "service": p = ("" if lang == "es" else "en/") + svc_by_id(lang, ident)["slug"] + "/"
    elif key == "person": p = (ident + "/") if lang == "es" else ("en/staff/" + ident + "/")
    elif key == "area": p = PAGES["areas"][i] + ident + "/"
    elif key == "article": p = ARTICLE_PATHS[lang][ident]
    elif key == "404": return "404.html"
    else: raise KeyError(key)
    return p + "index.html"

def rel(target, current):
    """Link from the current page to target (both site-relative file paths)."""
    if target.endswith("index.html"): target = target[: -len("index.html")]
    if ABS_LINKS: return "/" + target
    r = "../" * current.count("/") + target
    return r or "./"

def absurl(p):
    if p.endswith("index.html"): p = p[: -len("index.html")]
    return BASE + p

def strip(s):
    return html.escape(re.sub(r"<[^>]+>", "", s).replace("&amp;", "&"), quote=True)

def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"

def svc_by_id(lang, sid):
    return next(s for s in C[lang].SERVICES if s["id"] == sid)

def person_by_id(lang, pid):
    return next(p for p in C[lang].TEAM if p["id"] == pid)

# ---------------------------------------------------------------- icons
ARROW = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10h11M11 5l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
PHONE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.6 3.5l2.4-.5 1.6 4-2 1.4a12 12 0 0 0 7 7l1.4-2 4 1.6-.5 2.4a2 2 0 0 1-2 1.6A17 17 0 0 1 5 5.5a2 2 0 0 1 1.6-2z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>'
GLOBE = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M3 12h18M12 3c2.6 2.6 3.8 5.6 3.8 9s-1.2 6.4-3.8 9c-2.6-2.6-3.8-5.6-3.8-9S9.4 5.6 12 3z" fill="none" stroke="currentColor" stroke-width="1.7"/></svg>'
CHEV = '<svg viewBox="0 0 12 8" aria-hidden="true"><path d="M1 1.5l5 5 5-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>'
CLOSE = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'
CAL = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="5" width="17" height="15.5" rx="3" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M3.5 10h17M8 3v4M16 3v4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>'
PIN = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z" fill="none" stroke="currentColor" stroke-width="1.7"/><circle cx="12" cy="9.5" r="2.5" fill="none" stroke="currentColor" stroke-width="1.7"/></svg>'
PAUSE = '<svg class="i-pause" viewBox="0 0 14 14" aria-hidden="true"><rect x="3" y="2" width="3" height="10" rx="1" fill="currentColor"/><rect x="8" y="2" width="3" height="10" rx="1" fill="currentColor"/></svg>'
PLAY = '<svg class="i-play" viewBox="0 0 14 14" aria-hidden="true"><path d="M4 2.2v9.6a.6.6 0 0 0 .9.5l7.4-4.8a.6.6 0 0 0 0-1L4.9 1.7a.6.6 0 0 0-.9.5z" fill="currentColor"/></svg>'
CHECK = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10.5l4 4 8-9" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
EXT = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M8 4H4v12h12v-4M11 3h6v6M17 3l-8 8" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>'

HOUSE_PATH = "M0.44,0.03 Q0.5,-0.015 0.56,0.03 L0.985,0.335 Q1,0.35 1,0.375 L1,0.94 Q1,1 0.94,1 L0.06,1 Q0,1 0,0.94 L0,0.375 Q0,0.35 0.015,0.335 Z"
HOUSE_CHIMNEY = ("M0.44,0.03 Q0.5,-0.015 0.56,0.03 L0.735,0.156 L0.735,0.075 Q0.735,0.055 0.755,0.055 L0.8,0.055 Q0.82,0.055 0.82,0.075 "
                 "L0.82,0.217 L0.985,0.335 Q1,0.35 1,0.375 L1,0.94 Q1,1 0.94,1 L0.06,1 Q0,1 0,0.94 L0,0.375 Q0,0.35 0.015,0.335 Z")
SVG_DEFS = ('<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>'
            '<clipPath id="house" clipPathUnits="objectBoundingBox"><path d="' + HOUSE_PATH + '"/></clipPath>'
            '<clipPath id="house-chimney" clipPathUnits="objectBoundingBox"><path d="' + HOUSE_CHIMNEY + '"/></clipPath>'
            '</defs></svg>')

def house_svg_fill(cls=""):
    d = re.sub(r"(-?\d*\.?\d+),(-?\d*\.?\d+)", lambda m: f"{float(m.group(1))*1000:.0f},{float(m.group(2))*1000:.0f}", HOUSE_CHIMNEY)
    return f'<svg class="{cls}" viewBox="0 0 1000 1000" aria-hidden="true"><path d="{d}" fill="currentColor"/></svg>'

def fig(x, s, ground=86):
    top = ground - 60 * s; hy = top + 7 * s; sy = top + 18 * s; hip = top + 40 * s
    al = f"M{x:.1f},{sy:.1f} Q{x-10*s:.1f},{sy+1*s:.1f} {x-17*s:.1f},{top+3*s:.1f}"
    ar = f"M{x:.1f},{sy:.1f} Q{x+10*s:.1f},{sy+1*s:.1f} {x+17*s:.1f},{top+3*s:.1f}"
    o = f"transform-origin:{x:.1f}px {sy:.1f}px"
    return (f'<g class="fig" style="transform-origin:{x:.1f}px {ground}px">'
            f'<circle cx="{x:.1f}" cy="{hy:.1f}" r="{7*s:.1f}" fill="currentColor"/>'
            f'<path d="M{x:.1f},{sy-1*s:.1f} L{x:.1f},{hip:.1f}" stroke="currentColor" stroke-width="{10*s:.1f}" stroke-linecap="round"/>'
            f'<path d="M{x:.1f},{hip:.1f} L{x-7*s:.1f},{ground-2*s:.1f} M{x:.1f},{hip:.1f} L{x+7*s:.1f},{ground-2*s:.1f}" stroke="currentColor" stroke-width="{6*s:.1f}" stroke-linecap="round" fill="none"/>'
            f'<path class="arm arm-l" style="{o}" d="{al}" stroke="currentColor" stroke-width="{5.5*s:.1f}" stroke-linecap="round" fill="none"/>'
            f'<path class="arm arm-r" style="{o}" d="{ar}" stroke="currentColor" stroke-width="{5.5*s:.1f}" stroke-linecap="round" fill="none"/>'
            '</g>')

FIGS = {
    "child": lambda: fig(56, 1.0) + fig(94, .66), "teen": lambda: fig(54, 1.0) + fig(92, .86), "adult": lambda: fig(70, 1.12),
    "couple": lambda: fig(50, 1.0) + fig(90, 1.0), "family": lambda: fig(70, 1.08) + fig(34, .68) + fig(106, .68),
}

# ---------------------------------------------------------------- images
def pic(m, alt, cur, cls="house-img house", eager=False, sizes="(max-width: 700px) 92vw, 460px", wrap=True):
    """A local image from build/media.json, with a small version for phones and cards."""
    src = rel(m["src"], cur)
    srcset = f' srcset="{rel(m["sm"], cur)} {m["sm_w"]}w, {src} {m["w"]}w" sizes="{sizes}"' if m.get("sm") and m.get("sm_w", 0) < m["w"] else ""
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    tag = f'<img src="{src}"{srcset} alt="{strip(alt)}" width="{m["w"]}" height="{m["h"]}" {load} decoding="async">'
    return f'<div class="{cls}">{tag}</div>' if wrap else tag

def gal(n):
    """Gallery photo by its old file number, e.g. gal("2073") -> (media entry, number)."""
    return next(m for m in MEDIA["gallery"] if m["src"].endswith(f"img-{n}.webp")), n

def gpic(n, lang, cur, cls="house-img house", eager=False, sizes="(max-width: 900px) 92vw, 560px"):
    m, n = gal(n)
    return pic(m, C[lang].GALLERY["alts"][n], cur, cls, eager, sizes)

def staff_pic(pid, lang, cur, cls="house-img house", eager=False, sizes="(max-width: 700px) 60vw, 300px", alt=None):
    p = person_by_id(lang, pid)
    return pic(MEDIA["staff"][pid], EXTRA[lang]["portrait_of"] + " " + p["name"] if alt is None else alt, cur, cls, eager, sizes)

# ---------------------------------------------------------------- shared chunks
def _seo_config():
    return json.load(open(os.path.join(ROOT, "seo", "config.json"), encoding="utf-8"))

def analytics_tag():
    """GA4 tag, only when seo/config.json has a measurement ID. Never sends form contents or health details."""
    mid = _seo_config().get("google", {}).get("ga4_measurement_id", "").strip()
    if not re.fullmatch(r"G-[A-Z0-9]{4,}", mid or ""):
        return ""
    return (f'<script async src="https://www.googletagmanager.com/gtag/js?id={mid}"></script>\n'
            f'<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag("js",new Date());'
            f'gtag("config","{mid}",{{"allow_google_signals":false,"allow_ad_personalization_signals":false}});</script>')

def head(lang, cur, title, desc, alt_path, ld=None, og_image=None, preload_video=False, robots="index, follow, max-image-preview:large"):
    E = EXTRA[lang]
    canon = absurl(cur)
    es_p = cur if lang == "es" else alt_path
    en_p = cur if lang == "en" else alt_path
    og = og_image or (BASE + ("assets/img/og-image-es.jpg" if lang == "es" else "assets/img/og-image.jpg"))
    lds = "".join(jsonld(x) for x in (ld or []))
    pre = f'<link rel="preload" href="{rel("assets/media/hero-poster.webp", cur)}" as="image" type="image/webp">\n' if preload_video else ""
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{strip(title)}</title>
<meta name="description" content="{strip(desc)}">
<link rel="canonical" href="{canon}">
<link rel="alternate" hreflang="es" href="{absurl(es_p)}">
<link rel="alternate" hreflang="en" href="{absurl(en_p)}">
<link rel="alternate" hreflang="x-default" href="{absurl(es_p)}">
<meta name="robots" content="{robots}">
<meta name="theme-color" content="#FE4109">
<meta name="color-scheme" content="light">
<meta name="format-detection" content="telephone=no">
<meta name="geo.region" content="US-FL">
<meta name="geo.placename" content="Doral, Florida">
<meta name="geo.position" content="25.8097;-80.3299">
<meta name="ICBM" content="25.8097, -80.3299">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Healthy Solutions for Children and Families">
<meta property="og:locale" content="{E['locale']}">
<meta property="og:locale:alternate" content="{EXTRA[OTHER[lang]]['locale']}">
<meta property="og:title" content="{strip(title)}">
<meta property="og:description" content="{strip(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{og}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{strip(title)}">
<meta name="twitter:description" content="{strip(desc)}">
<meta name="twitter:image" content="{og}">
<link rel="icon" href="{rel('assets/img/favicon.ico', cur)}" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="{rel('assets/img/favicon-32.png', cur)}">
<link rel="apple-touch-icon" href="{rel('assets/img/apple-touch-icon.png', cur)}">
<link rel="manifest" href="{rel('site.webmanifest', cur)}">
<link rel="alternate" type="application/rss+xml" title="Healthy Solutions — Blog" href="{rel('blog/feed.xml' if lang == 'es' else 'en/blog/feed.xml', cur)}">
<link rel="preload" href="{rel('assets/fonts/fraunces.woff2', cur)}" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{rel('assets/fonts/figtree.woff2', cur)}" as="font" type="font/woff2" crossorigin>
{pre}<link rel="stylesheet" href="{rel('assets/css/styles.css', cur)}">
{analytics_tag()}
{lds}
</head>
"""

def business_ld(lang):
    M = C[lang]
    return {
        "@context": "https://schema.org", "@type": "MedicalClinic", "@id": BASE + "#practice",
        "name": "Healthy Solutions for Children and Families", "alternateName": "HSCF",
        "description": strip(M.HOME["description"]), "url": BASE,
        "logo": BASE + "assets/img/logo.png", "image": BASE + "assets/img/og-image.jpg",
        "telephone": "+1-305-594-5658", "email": "info@hscfdoral.com",
        "contactPoint": [{"@type": "ContactPoint", "telephone": "+1-305-594-5658", "contactType": "customer service", "availableLanguage": ["Spanish", "English"]},
                         {"@type": "ContactPoint", "telephone": "+1-786-423-9495", "contactType": "customer service", "availableLanguage": ["Spanish", "English"]}],
        "availableLanguage": [{"@type": "Language", "name": "Spanish"}, {"@type": "Language", "name": "English"}],
        "address": ADDRESS, "geo": {"@type": "GeoCoordinates", "latitude": 25.8097, "longitude": -80.3299},
        "hasMap": "https://www.google.com/maps?q=8245+NW+36th+St+Ste+7,+Doral,+FL+33166",
        "areaServed": [{"@type": "City", "name": a["city"]} for a in C["en"].AREAS] + [{"@type": "AdministrativeArea", "name": "Miami-Dade County"}],
        "medicalSpecialty": "Psychiatric",
        "knowsAbout": ["Psychotherapy", "Family therapy", "Couples therapy", "Play therapy", "Cognitive behavioral therapy", "Applied Behavior Analysis",
                       "Autism", "Psychological testing", "Neuropsychological testing", "Developmental assessment", "Parenting workshops", "Neurofeedback", "Hypnotherapy", "Coaching"],
        "makesOffer": [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": strip(s["name"]), "url": absurl(path_for("service", lang, s["id"]))}} for s in C[lang].SERVICES],
        "employee": [{"@type": "Person", "name": p["name"], "url": absurl(path_for("person", lang, p["id"]))} for p in C[lang].TEAM],
    }

def breadcrumb_ld(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": strip(n), "item": absurl(p)} for i, (n, p) in enumerate(items)]}

def event_ld(lang):
    ev = C[lang].EVENT
    return {"@context": "https://schema.org", "@type": "Event", "name": "Hablemos sobre Ansiedad",
            "description": strip(ev["summary"]), "startDate": "2026-10-24T15:00:00-04:00", "endDate": "2026-10-24T17:00:00-04:00",
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "eventStatus": "https://schema.org/EventScheduled",
            "inLanguage": "es", "isAccessibleForFree": True, "image": BASE + "assets/img/event-ansiedad-flyer.jpg",
            "location": {"@type": "Place", "name": "Florida Blue Center",
                         "address": {"@type": "PostalAddress", "streetAddress": "1001 W 49th St", "addressLocality": "Hialeah", "addressRegion": "FL", "postalCode": "33012", "addressCountry": "US"}},
            "organizer": {"@type": "Organization", "@id": BASE + "#practice", "name": "Healthy Solutions for Children and Families", "url": BASE},
            "performer": [{"@type": "Person", "name": n} for n, r in ev["leaders"]],
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD", "availability": "https://schema.org/InStock", "url": absurl(path_for("events", lang)), "validFrom": "2026-10-01T00:00:00-04:00"}}

def faq_ld(faq):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": strip(q), "acceptedAnswer": {"@type": "Answer", "text": strip(a)}} for q, a in faq]}

def webpage_ld(kind, lang, cur, name, desc=""):
    return {"@context": "https://schema.org", "@type": kind, "name": strip(name), "url": absurl(cur), "inLanguage": lang,
            **({"description": strip(desc)} if desc else {}), "isPartOf": {"@id": BASE + "#website"}, "about": {"@id": BASE + "#practice"}}

def nav_link(lang, cur, key, label, active, ident=None):
    ac = ' aria-current="page"' if active == key else ""
    return f'<a href="{rel(path_for(key, lang, ident), cur)}"{ac}>{label}</a>'

def header(lang, cur, active, alt_path):
    M = C[lang]; U = M.UI; E = EXTRA[lang]
    L = lambda k, i=None: rel(path_for(k, lang, i), cur)
    act_items = [("news", U["nav_news"], M.ACTIVITIES["cards"][0][2]), ("events", U["nav_events"], M.ACTIVITIES["cards"][1][2]),
                 ("gallery", U["nav_gallery"], M.ACTIVITIES["cards"][2][2])]
    act_menu = "".join(f'<a href="{L(k)}"><strong>{n}</strong><span>{d}</span></a>' for k, n, d in act_items) + \
        f'<a href="{L("service", "courses")}"><strong>{svc_by_id(lang, "courses")["menu"]}</strong><span>{M.ACTIVITIES["cards"][3][2]}</span></a>' + \
        f'<a class="nav-menu-all" href="{L("activities")}">{U["nav_all_activities"]}</a>'
    svc_menu = "".join(f'<a href="{L("service", s["id"])}"><strong>{s["menu"]}</strong><span>{s["short"]}</span></a>' for s in M.SERVICES if s["id"] != "courses") + \
        f'<a href="{L("insurance")}#evaluaciones"><strong>{M.FINDER_TESTING}</strong><span>{M.INSURANCE["testing_p"]}</span></a>' + \
        f'<a class="nav-menu-all" href="{L("services")}">{U["nav_all_services"]}</a>'
    staff_menu = "".join(f'<a class="nav-person" href="{L("person", p["id"])}">{staff_pic(p["id"], lang, cur, "house-img house", sizes="44px", alt="")}<span class="nav-person-text"><strong>{p["name"]}</strong><span>{p["title_role"]}</span></span></a>' for p in M.TEAM) + \
        f'<a class="nav-menu-all" href="{L("staff")}">{U["nav_all_staff"]}</a>'
    def drop(key, label, menu, mid, cls=""):
        cur_cls = " is-current" if active == key else ""
        return (f'<div class="nav-drop{cur_cls}"><button type="button" aria-expanded="false" aria-controls="{mid}">{label} {CHEV}</button>'
                f'<div class="nav-menu{cls}" id="{mid}" role="group" aria-label="{label}">{menu}</div></div>')
    other = OTHER[lang]
    switch = f'<a class="lang-switch" href="{rel(alt_path, cur)}" hreflang="{other}" lang="{other}" aria-label="{U["switch_aria"]}">{GLOBE}<span class="lang-text">{U["switch_label"]}</span><span class="lang-short" aria-hidden="true">{other.upper()}</span></a>'
    mob = lambda k, label: nav_link(lang, cur, k, label, active)
    mob_drop = lambda label, links: f'<details><summary>{label}</summary>{links}</details>'
    return f"""<a class="skip-link" href="#main">{U['skip']}</a>
<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="{L('home')}" aria-label="Healthy Solutions for Children and Families, {U['home']}">
      <img src="{rel('assets/img/logo.png', cur)}" alt="" width="312" height="287">
      <span class="brand-name">Healthy Solutions<small>for Children and Families</small></span>
    </a>
    <nav class="nav" aria-label="{E['main_nav']}">
      {nav_link(lang, cur, 'about', U['nav_about'], active)}
      {drop('activities', U['nav_activities'], act_menu, 'act-menu', ' nav-menu--one')}
      {drop('services', U['nav_services'], svc_menu, 'svc-menu')}
      {nav_link(lang, cur, 'insurance', U['nav_insurance'], active)}
      {drop('staff', U['nav_staff'], staff_menu, 'staff-menu', ' nav-menu--people')}
      {nav_link(lang, cur, 'blog', U['nav_blog'], active)}
    </nav>
    <div class="header-actions">
      {switch}
      <a class="btn btn--small header-cta" href="{L('contact')}">{U['cta_book']}</a>
      <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="mobile-sheet" aria-label="{U['menu_open']}"><span></span></button>
    </div>
  </div>
</header>
<div class="mobile-sheet" id="mobile-sheet" aria-hidden="true" inert>
  <div class="mobile-sheet-top">
    <a class="brand" href="{L('home')}"><img src="{rel('assets/img/logo.png', cur)}" alt="" width="312" height="287"><span class="brand-name">Healthy Solutions<small>for Children and Families</small></span></a>
    <button class="mobile-close" type="button" aria-label="{U['menu_close']}">{CLOSE}</button>
  </div>
  <nav class="mobile-nav" aria-label="{E['main_nav']}">
    {mob('home', U['home'])}
    {mob('about', U['nav_about'])}
    {mob_drop(U['nav_activities'], ''.join(f'<a href="{L(k)}">{n}</a>' for k, n, d in act_items) + f'<a href="{L("service", "courses")}">{svc_by_id(lang, "courses")["menu"]}</a><a href="{L("activities")}">{U["nav_all_activities"]}</a>')}
    {mob_drop(U['nav_services'], ''.join(f'<a href="{L("service", s["id"])}">{s["menu"]}</a>' for s in M.SERVICES if s["id"] != "courses") + f'<a href="{L("insurance")}#evaluaciones">{M.FINDER_TESTING}</a><a href="{L("services")}">{U["nav_all_services"]}</a>')}
    {mob('insurance', U['nav_insurance'])}
    {mob_drop(U['nav_staff'], ''.join(f'<a href="{L("person", p["id"])}">{p["name"]}</a>' for p in M.TEAM) + f'<a href="{L("staff")}">{U["nav_all_staff"]}</a>')}
    {mob('blog', U['nav_blog'])}
    {mob('contact', U['nav_contact'])}
  </nav>
  <a class="btn" href="{L('contact')}">{U['cta_book_long']}</a>
  {switch.replace(' aria-label="' + U['switch_aria'] + '"', '')}
  <p class="mobile-contact"><a href="tel:{TEL1}">{U['phone']}</a> · <a href="tel:{TEL2}">{U['phone2']}</a><br>{U['address_line1']}, {U['address_line2']}<br>{U['languages_note']}</p>
</div>
"""

def footer(lang, cur):
    M = C[lang]; U = M.UI
    L = lambda k, i=None: rel(path_for(k, lang, i), cur)
    explore = [("about", U["nav_about"]), ("activities", U["nav_activities"]), ("services", U["nav_services"]), ("insurance", U["nav_insurance"]),
               ("staff", U["nav_staff"]), ("blog", U["nav_blog"]), ("contact", U["nav_contact"])]
    svcs = "".join(f'<li><a href="{L("service", s["id"])}">{s["menu"]}</a></li>' for s in M.SERVICES)
    areas = " ".join(f'<a href="{L("area", a["id"])}">{a["city"]}</a>' for a in M.AREAS)
    return f"""<footer class="site-footer">
  <div class="wrap">
    <div class="footer-grid">
      <div class="footer-brand">
        <img src="{rel('assets/img/logo.png', cur)}" alt="" width="312" height="287" loading="lazy">
        <p class="footer-name">Healthy Solutions for Children and Families</p>
        <p>{U['footer_tagline']}</p>
      </div>
      <div>
        <h2>{U['footer_explore']}</h2>
        <ul>{''.join(f'<li><a href="{L(k)}">{n}</a></li>' for k, n in explore)}</ul>
      </div>
      <div>
        <h2>{U['footer_services']}</h2>
        <ul>{svcs}</ul>
      </div>
      <div>
        <h2>{U['footer_visit']}</h2>
        <ul>
          <li>{U['address_line1']}<br>{U['address_line2']}</li>
          <li><a href="tel:{TEL1}">{U['phone']}</a></li>
          <li><a href="tel:{TEL2}">{U['phone2']}</a></li>
          <li><a href="mailto:info@hscfdoral.com">{U['email']}</a></li>
          <li>{U['languages_note']}</li>
        </ul>
      </div>
    </div>
    <nav class="footer-areas" aria-label="{U['footer_areas']}"><a class="footer-areas-hub" href="{L('areas')}">{U['footer_areas']}</a> {areas}</nav>
    <div class="footer-crisis"><p>{U['crisis']}</p></div>
    <div class="footer-bottom">
      <p>&copy; <span data-year>2026</span> {U['footer_rights']}</p>
      <p>{U['footer_privacy']}</p>
    </div>
  </div>
</footer>
"""

def event_modal(lang, cur):
    U = C[lang].UI; ev = C[lang].EVENT; E = EXTRA[lang]
    leaders = ", ".join(f"<strong>{n}</strong> ({r})" for n, r in ev["leaders"])
    ics = {"uid": "hablemos-ansiedad-20261024@hscfdoral.com", "start": "20261024T190000Z", "end": "20261024T210000Z",
           "title": "Hablemos sobre Ansiedad (HSCF)", "location": "Florida Blue Center, 1001 W 49th St, Hialeah, FL 33012",
           "description": strip(ev["summary"]).replace("&#x27;", "'")}
    ics_attr = html.escape(json.dumps(ics, ensure_ascii=False), quote=True)
    maps = "https://www.google.com/maps/dir/?api=1&amp;destination=Florida+Blue+Center+1001+W+49th+St+Hialeah+FL+33012"
    mail = f"mailto:info@hscfdoral.com?subject={ev['rsvp_subject'].replace(' ', '%20')}&amp;body={ev['rsvp_body'].replace(' ', '%20')}"
    sub = f'<p class="event-sub">{ev["title"]}</p>' if ev["title"] != ev["title_es"] else ""
    return f"""<dialog class="event-modal" id="event-modal" aria-labelledby="event-title" data-id="ansiedad-2026-10-24" data-end="2026-10-24T17:00:00-04:00">
  <button class="event-close" type="button" data-close aria-label="{U['event_close']}">{CLOSE}</button>
  <div class="event-modal-grid" tabindex="-1" autofocus>
    <div class="event-flyer"><img src="{rel('assets/img/event-ansiedad-flyer.jpg', cur)}" alt="{strip(ev['flyer_alt'])}" width="1350" height="1688" loading="lazy"></div>
    <div class="event-body">
      <span class="badge">{U['event_badge']}</span>
      <h2 id="event-title">{ev['title_es']}</h2>
      {sub}
      <p>{ev['summary']}</p>
      <ul class="event-facts">
        <li>{CAL}<div><strong>{ev['date']}</strong><span>{ev['time']}</span></div></li>
        <li>{PIN}<div><strong>{ev['venue']}</strong><span>{ev['address']}</span></div></li>
      </ul>
      <p class="event-leaders">{U['event_led_by']}: {leaders}</p>
      <div class="btn-row">
        <a class="btn" href="{mail}">{U['event_reserve']}</a>
        <a class="btn btn--ghost" href="tel:{TEL1}">{U['event_call']}</a>
      </div>
      <div class="event-links">
        <button type="button" data-ics="{ics_attr}">{U['event_calendar']}</button>
        <a href="{maps}" target="_blank" rel="noopener">{U['event_directions']}<span class="sr-only"> ({U['external']})</span></a>
      </div>
    </div>
  </div>
</dialog>
<button class="event-pill" type="button" aria-haspopup="dialog"><img src="{rel('assets/img/event-ansiedad-flyer-sm.jpg', cur)}" alt="" width="540" height="675">{U['event_reopen']}</button>
"""

def page(lang, cur, active, alt_path, title, desc, body, ld=None, splash=None, preload_video=False, extra_script="", og_image=None, robots=None):
    kw = {"robots": robots} if robots else {}
    return (head(lang, cur, title, desc, alt_path, ld, og_image=og_image, preload_video=preload_video, **kw) + "<body>\n" + SVG_DEFS + "\n" + (splash or "")
            + header(lang, cur, active, alt_path) + f'<main id="main">\n{body}\n</main>\n' + footer(lang, cur)
            + event_modal(lang, cur) + extra_script + f'<script src="{rel("assets/js/main.js", cur)}" defer></script>\n</body>\n</html>\n')

def crumbs(lang, cur, items):
    lis = [f'<li><span aria-current="page">{n}</span></li>' if i == len(items) - 1 else f'<li><a href="{rel(p, cur)}">{n}</a></li>' for i, (n, p) in enumerate(items)]
    return f'<nav class="crumbs" aria-label="{EXTRA[lang]["crumbs"]}"><ol>{"".join(lis)}</ol></nav>'

def page_hero(lang, cur, crumbs_items, h1, lead, media=None, extra=""):
    grid_cls = "page-hero-grid" + ("" if media else " page-hero-grid--text")
    return f"""<section class="page-hero"><div class="wrap">
  {crumbs(lang, cur, crumbs_items)}
  <div class="{grid_cls}">
    <div><h1>{h1}</h1><p class="lead">{lead}</p>{extra}</div>
    {media or ''}
  </div>
</div></section>"""

def faq_block(faq):
    return '<div class="faq">' + "".join(
        f'<details><summary>{q}<span class="plus" aria-hidden="true"></span></summary><div class="faq-a"><p>{a}</p></div></details>' for q, a in faq) + "</div>"

def cta_band(lang, cur, h=None, p=None):
    U = C[lang].UI; H = C[lang].HOME
    return f"""<section class="section section--tight"><div class="wrap">
  <div class="cta-band">
    <h2>{h or H['cta_h2']}</h2>
    <p>{p or H['cta_p']}</p>
    <div class="btn-row">
      <a class="btn btn--light" href="{rel(path_for('contact', lang), cur)}">{U['cta_book_long']}</a>
      <a class="btn btn--ghost" href="tel:{TEL1}">{PHONE}{U['phone']}</a>
    </div>
    {house_svg_fill('cta-house')}
  </div>
</div></section>"""

def aside_card(lang, cur):
    U = C[lang].UI
    return f"""<aside class="aside-card" aria-labelledby="aside-h">
  <h2 id="aside-h">{U['aside_title']}</h2>
  <p>{U['aside_text']}</p>
  <a class="btn" href="{rel(path_for('contact', lang), cur)}">{U['cta_book_long']}</a>
  <a class="btn btn--ghost" href="tel:{TEL1}">{PHONE}{U['phone']}</a>
  <dl>
    <div><dt>{U['aside_address_label']}</dt><dd>{U['address_line1']}<br>{U['address_line2']}</dd></div>
    <div><dt>{U['aside_phones_label']}</dt><dd><a href="tel:{TEL1}">{U['phone']}</a><br><a href="tel:{TEL2}">{U['phone2']}</a></dd></div>
    <div><dt>{U['languages']}</dt><dd>{U['languages_note']}</dd></div>
  </dl>
</aside>"""

def map_iframe(lang, cls="map-frame"):
    src = f"https://maps.google.com/maps?q=8245%20NW%2036th%20St%20Ste%207%2C%20Doral%2C%20FL%2033166&amp;t=m&amp;z=15&amp;hl={lang}&amp;output=embed"
    return f'<div class="{cls}"><iframe src="{src}" title="{C[lang].UI["map_title"]}" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe></div>'

def svc_list(lang, cur, ids=None):
    items = []
    for s in C[lang].SERVICES:
        if ids and s["id"] not in ids: continue
        items.append(f'<li><a href="{rel(path_for("service", lang, s["id"]), cur)}"><span class="svc-name">{s["name"]}</span>'
                     f'<span class="svc-short">{s["short"]}</span><span class="svc-go" aria-hidden="true">{ARROW}</span></a></li>')
    return '<ul class="svc-list">' + "".join(items) + "</ul>"

def related_cards(lang, cur, ids):
    return '<div class="related">' + "".join(
        f'<a href="{rel(path_for("service", lang, r), cur)}"><strong>{svc_by_id(lang, r)["name"]}</strong><span>{svc_by_id(lang, r)["short"]}</span></a>' for r in ids) + "</div>"

def staff_cards(lang, cur, ids, cls="team-row"):
    U = C[lang].UI
    return f'<div class="{cls}">' + "".join(
        f'<a class="person" href="{rel(path_for("person", lang, pid), cur)}">{staff_pic(pid, lang, cur, sizes="(max-width: 1100px) 220px, 15vw")}'
        f'<div><h3>{person_by_id(lang, pid)["name"]}{(" <span class=\"creds\">" + person_by_id(lang, pid)["creds"] + "</span>") if person_by_id(lang, pid)["creds"] else ""}</h3><p>{person_by_id(lang, pid)["title_role"]}</p></div></a>'
        for pid in ids) + "</div>"

def logo_strip(lang, cur):
    return f'<ul class="logo-strip" aria-label="{EXTRA[lang]["logos_label"]}">' + "".join(
        f'<li><img src="{rel(m["src"], cur)}" alt="{n}" width="{m["w"]}" height="{m["h"]}" loading="lazy" decoding="async"></li>'
        for k, n, m in [(k, LOGO_NAMES[k], MEDIA["logos"][k]) for k in LOGO_ORDER]) + "</ul>"

LOGO_ORDER = ["aetna", "bcbs", "cigna", "unitedhealthcare", "oscar", "bind", "umr", "optum", "anthem", "avmed", "lucet"]
LOGO_NAMES = {"aetna": "Aetna", "bcbs": "Blue Cross Blue Shield", "cigna": "Cigna", "unitedhealthcare": "UnitedHealthcare", "oscar": "Oscar",
              "bind": "Bind", "umr": "UMR", "optum": "Optum", "anthem": "Anthem Blue Cross", "avmed": "AvMed", "lucet": "Lucet"}

def write(path, content):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full) or OUT, exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)

def alt_of(key, lang, ident=None):
    return path_for(key, OTHER[lang], ident)

def home_crumb(lang):
    return (C[lang].UI["home"], path_for("home", lang))

# ================================================================= pages
def build_home(lang):
    M = C[lang]; U = M.UI; H = M.HOME; E = EXTRA[lang]
    cur = path_for("home", lang); alt = alt_of("home", lang)
    L = lambda k, i=None: rel(path_for(k, lang, i), cur)
    splash = f"""<div class="splash" role="dialog" aria-modal="true" aria-label="{E['splash_aria']}">
  <div class="splash-inner">
    <button class="splash-door" type="button" aria-label="{E['splash_aria']}"><img src="{rel('assets/img/logo.png', cur)}" alt="" width="312" height="287"></button>
    <p class="splash-hint">{H['splash_hint']}</p>
    <p class="splash-name">{H['splash_name']}</p>
    <nav class="splash-lang" aria-label="Idioma / Language"><a href="{rel(path_for('home', 'es'), cur)}" hreflang="es" lang="es"{' aria-current="true"' if lang == 'es' else ''}>Español</a><a href="{rel(path_for('home', 'en'), cur)}" hreflang="en" lang="en"{' aria-current="true"' if lang == 'en' else ''}>English</a></nav>
  </div>
</div>
"""
    bars = "".join(f'<button class="scene-bar" type="button" aria-label="{H["scenes"][i]}"><i></i></button>' for i in range(3))
    points = "".join(f"<li>{p}</li>" for p in H["hero_points"])
    who = "".join(
        f'<button class="who" type="button" aria-pressed="false" data-who="{g["id"]}"><svg viewBox="0 0 140 90" aria-hidden="true">{FIGS[g["fig"]]()}</svg><strong>{g["label"]}</strong><span>{g["sub"]}</span></button>'
        for g in M.FINDER)
    fservices = {s["id"]: {"name": s["name"], "url": L("service", s["id"])} for s in M.SERVICES}
    fservices["testing"] = {"name": M.FINDER_TESTING, "url": L("insurance") + "#evaluaciones"}
    fdata = {"groups": [{"id": g["id"], "concerns": g["concerns"]} for g in M.FINDER], "services": fservices,
             "people": {p["id"]: {"name": p["name"], "first": p["first"], "role": p["title_role"], "img": rel(MEDIA["staff"][p["id"]]["sm"], cur), "url": L("person", p["id"])} for p in M.TEAM},
             "labels": {"match": H["finder_match"], "meet": U["view_profile"]}}
    finder_script = "<script>window.HSCF_FINDER=" + json.dumps(fdata, ensure_ascii=False).replace("</", "<\\/") + ";</script>\n"
    news_img = {"psychotherapy": MEDIA["services"]["psicoterapia"], "parent-workshops": MEDIA["talleres"]["promoviendo-relaciones-saludables"], "yoga": MEDIA["services"]["yoga"]}
    news = "".join(f'<a class="news-card" href="{L("service", sid)}">{pic(news_img[sid], "", cur, "news-card-img", sizes="(max-width: 760px) 92vw, 380px")}'
                   f'<div><h3>{t}</h3><p>{d}</p><span class="text-link">{U["learn_more"]}</span></div></a>' for sid, t, d in H["news_cards"])
    testis = "".join(
        f'<figure class="testimonial"><blockquote><p>{t["quote"]}</p></blockquote>'
        f'<details><summary><span class="t-more">{U["read_more"]}</span><span class="t-less">{U["read_less"]}</span></summary>{"".join(f"<p>{x}</p>" for x in t["full"])}</details>'
        f'<figcaption>{t["name"]}</figcaption></figure>' for t in M.TESTIMONIALS)
    breathe_labels = html.escape(json.dumps({k: H["breathe_" + k] for k in ("in", "hold", "out", "ready", "done", "start", "stop")}, ensure_ascii=False), quote=True)
    bh = re.sub(r"(-?\d*\.?\d+),(-?\d*\.?\d+)", lambda m: f"{float(m.group(1))*100:.1f},{float(m.group(2))*100:.1f}", HOUSE_CHIMNEY)
    body = f"""
<section class="hero hero--film">
  <div class="hero-film" aria-hidden="true">
    <video class="hero-video" autoplay muted loop playsinline preload="auto" poster="{rel('assets/media/hero-poster.webp', cur)}" data-segments="0,4.2,7.0,10.4">
      <source src="{rel('assets/media/hero-720.mp4', cur)}" type="video/mp4" media="(max-width: 900px)">
      <source src="{rel('assets/media/hero-1080.mp4', cur)}" type="video/mp4">
    </video>
    <div class="hero-shade"></div>
  </div>
  <div class="wrap hero-inner">
    <div class="hero-copy">
      <h1>{H['hero_h1']}</h1>
      <p class="lead">{H['hero_lead']}</p>
      <div class="btn-row">
        <a class="btn" href="{L('contact')}">{U['cta_book_long']}</a>
        <a class="btn btn--ghost" href="{L('services')}">{U['cta_explore']}</a>
      </div>
      <ul class="hero-points">{points}</ul>
    </div>
  </div>
  <div class="hero-controls-wrap"><div class="wrap">
    <div class="hero-controls">
      <div class="scene-bars">{bars}</div>
      <button class="video-toggle" type="button" aria-pressed="false" aria-label="{H['video_pause']}" data-pause="{H['video_pause']}" data-play="{H['video_play']}">{PAUSE}{PLAY}</button>
    </div>
  </div></div>
  <svg class="hero-roof" viewBox="0 0 1440 90" preserveAspectRatio="none" aria-hidden="true"><path d="M0,90 L0,78 L688,12 Q720,-2 752,12 L1440,78 L1440,90 Z" fill="currentColor"/></svg>
</section>

<section class="section section--tight finder" data-finder aria-labelledby="finder-h">
  <div class="wrap">
    <div class="finder-panel">
      <div class="finder-head"><h2 id="finder-h">{H['finder_h2']}</h2><p>{H['finder_lead']}</p></div>
      <div class="who-grid" role="group" aria-label="{E['who_label']}">{who}</div>
      <div class="finder-step" hidden><h3>{H['finder_step2']}</h3><div class="concern-list" role="group" aria-label="{H['finder_step2']}"></div></div>
      <div class="finder-result" hidden aria-live="polite">
        <div><h3>{H['finder_result_h']}</h3><ul class="rec-list"></ul><p class="finder-note">{H['finder_note']}</p></div>
        <div><div class="match"></div>
          <div class="btn-row mt-s"><a class="btn btn--small" href="{L('contact')}">{U['cta_book_long']}</a><button class="finder-restart" type="button">{H['finder_restart']}</button></div>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="section section--flush-top" aria-labelledby="news-h">
  <div class="wrap">
    <div class="section-head"><h2 id="news-h">{H['news_h2']}</h2></div>
    <div class="news-grid">{news}</div>
  </div>
</section>

<section class="section section--blush" aria-labelledby="what-h">
  <div class="wrap split">
    <div class="intro-media">
      {gpic('2050', lang, cur)}
      <div class="tag"><img src="{rel('assets/img/logo.png', cur)}" alt="" width="312" height="287">{U['languages_note']}</div>
    </div>
    <div>
      <h2 id="what-h">{H['what_h2']}</h2>
      <h3 class="sub-h">{H['what_h3']}</h3><p>{H['what_p']}</p>
      <h3 class="sub-h">{H['how_h3']}</h3><p>{H['how_p']}</p>
      <div class="btn-row mt-m"><a class="btn" href="{L('contact')}">{U['nav_contact']}</a><a class="btn btn--ghost" href="{L('about')}">{U['nav_about']}</a></div>
    </div>
  </div>
</section>

<section class="section" aria-labelledby="labor-h">
  <div class="wrap split">
    <div>
      <h2 id="labor-h">{H['labor_h2']}</h2>
      <div class="mt-s">{''.join(f'<p>{p}</p>' for p in H['labor_p'])}</div>
      <a class="text-link" href="{L('service', 'parent-workshops')}">{H['labor_link']}</a>
    </div>
    {gpic('2073', lang, cur, 'house-img house-c')}
  </div>
</section>

<section class="section section--blush breathe" data-breathe data-labels="{breathe_labels}" aria-labelledby="breathe-h">
  <div class="wrap">
    <div class="section-head"><h2 id="breathe-h">{H['breathe_h2']}</h2><p class="lead">{H['breathe_p']}</p></div>
    <div class="breathe-stage"><svg class="breathe-house" viewBox="-6 -6 112 112" aria-hidden="true"><path class="bh-back" d="{bh}" transform="translate(-4 -4) scale(1.08)"/><path class="bh-front" d="{bh}"/>{fig(50, 1.0, ground=88)}</svg></div>
    <div class="breathe-readout"><span class="breathe-label" aria-live="polite">{H['breathe_ready']}</span><span class="breathe-count" aria-hidden="true"></span></div>
    <button class="btn breathe-btn" type="button" aria-pressed="false">{H['breathe_start']}</button>
  </div>
</section>

<section class="section" aria-labelledby="staff-h">
  <div class="wrap">
    <div class="section-head"><h2 id="staff-h">{H['staff_h2']}</h2><p class="lead">{H['staff_lead']}</p></div>
    {staff_cards(lang, cur, [p['id'] for p in M.TEAM], 'team-row team-row--nine')}
    <p class="mt-l"><a class="text-link" href="{L('staff')}">{H['staff_link']}</a></p>
  </div>
</section>

<section class="section section--blush" id="testimonios" aria-labelledby="testi-h">
  <div class="wrap">
    <div class="section-head"><h2 id="testi-h">{H['testimonials_h2']}</h2><p class="lead">{H['testimonials_lead']}</p></div>
    <div class="testimonial-grid">{testis}</div>
  </div>
</section>

<section class="section section--tight" aria-labelledby="allies-h">
  <div class="wrap">
    <div class="section-head"><h2 id="allies-h">{H['allies_h2']}</h2><p class="lead">{H['allies_p']}</p></div>
    {logo_strip(lang, cur)}
    <p class="mt-m"><a class="text-link" href="{L('insurance')}">{H['allies_link']}</a></p>
  </div>
</section>

<section class="section section--tight section--flush-top" aria-labelledby="event-h">
  <div class="wrap">
    <div class="event-band">
      <img src="{rel('assets/img/event-ansiedad-flyer-sm.jpg', cur)}" alt="{strip(M.EVENT['flyer_alt'])}" width="540" height="675" loading="lazy">
      <div>
        <span class="badge">{U['event_badge']}</span>
        <h2 id="event-h">{H['event_h2']}</h2>
        <p>{H['event_p']}</p>
        <div class="btn-row"><a class="btn btn--light" href="#event-modal" data-open-event>{H['event_cta']}</a><a class="btn btn--ghost" href="{L('events')}">{U['nav_events']}</a></div>
      </div>
    </div>
  </div>
</section>

<section class="section section--blush" aria-labelledby="faq-h">
  <div class="wrap">
    <div class="section-head"><h2 id="faq-h">{U['faq_title']}</h2></div>
    {faq_block(H['faq'])}
  </div>
</section>

<section class="section" aria-labelledby="contact-h">
  <div class="wrap split">
    <div>
      <h2 id="contact-h">{H['contact_h2']}</h2>
      <p class="lead mt-s">{H['contact_p']}</p>
      {contact_list(lang, cur)}
      <div class="btn-row"><a class="btn" href="{L('contact')}">{U['cta_book_long']}</a></div>
    </div>
    {map_iframe(lang)}
  </div>
</section>
"""
    ld = [business_ld(lang), event_ld(lang), faq_ld(H["faq"]),
          {"@context": "https://schema.org", "@type": "WebSite", "@id": BASE + "#website", "url": BASE, "name": "Healthy Solutions for Children and Families",
           "inLanguage": ["es", "en"], "publisher": {"@id": BASE + "#practice"}}]
    write(cur, page(lang, cur, "home", alt, H["title"], H["description"], body, ld, splash=splash, preload_video=True, extra_script=finder_script))

def contact_list(lang, cur):
    U = C[lang].UI; K = C[lang].CONTACT
    return f"""<ul class="contact-list">
  <li><span class="k">{K['call_label']}</span><span class="v"><a href="tel:{TEL1}">{U['phone']}</a><br><a href="tel:{TEL2}">{U['phone2']}</a></span></li>
  <li><span class="k">{K['email_label']}</span><span class="v"><a href="mailto:info@hscfdoral.com">{U['email']}</a></span></li>
  <li><span class="k">{K['address_label']}</span><span class="v">{U['address_line1']}<small>{U['address_line2']}</small></span></li>
</ul>"""

def build_about(lang):
    M = C[lang]; U = M.UI; A = M.ABOUT
    cur = path_for("about", lang); alt = alt_of("about", lang)
    items = [home_crumb(lang), (U["nav_about"], cur)]
    pillars = "".join(f"<li><h3>{a}</h3><p>{b}</p></li>" for a, b in A["pillars"])
    extra = f'<div class="btn-row mt-m"><a class="btn" href="{rel(path_for("contact", lang), cur)}">{U["cta_book_long"]}</a><a class="btn btn--ghost" href="{rel(path_for("staff", lang), cur)}">{U["nav_staff"]}</a></div>'
    body = page_hero(lang, cur, items, A["h1"], A["lead"], gpic("2069", lang, cur, eager=True), extra) + f"""
<section class="section section--blush"><div class="wrap split">
  <div class="prose">{''.join(f'<p>{p}</p>' for p in A['p'])}</div>
  {gpic('2050', lang, cur, 'house-img house-c')}
</div></section>
<section class="section"><div class="wrap">
  <div class="section-head"><h2>{A['pillars_h2']}</h2></div>
  <ul class="values values--three">{pillars}</ul>
</div></section>
<section class="section section--blush"><div class="wrap">
  <div class="section-head"><h2>{A['staff_h2']}</h2><p class="lead">{A['staff_p']}</p></div>
  {staff_cards(lang, cur, [p['id'] for p in M.TEAM], 'team-row team-row--nine')}
</div></section>
{cta_band(lang, cur, A['cta_h2'])}
"""
    ld = [business_ld(lang), breadcrumb_ld(items), webpage_ld("AboutPage", lang, cur, A["title"], A["description"])]
    write(cur, page(lang, cur, "about", alt, A["title"], A["description"], body, ld))

def build_activities(lang):
    M = C[lang]; U = M.UI; A = M.ACTIVITIES
    cur = path_for("activities", lang); alt = alt_of("activities", lang)
    items = [home_crumb(lang), (U["nav_activities"], cur)]
    def href(k): return rel(path_for("service", lang, k.split(":")[1]) if k.startswith("service:") else path_for(k, lang), cur)
    imgs = {"news": MEDIA["news"]["cuando-la-adolescencia-curso"], "events": MEDIA["events"]["el-arte-del-reencuentro"], "gallery": gal("2083")[0],
            "service:courses": MEDIA["cursos"]["taller-neuroplasticidad"], "blog": MEDIA["blog"]["family-wellbeing"][0]}
    cards = "".join(f'<a class="news-card" href="{href(k)}">{pic(imgs[k], "", cur, "news-card-img", sizes="(max-width: 760px) 92vw, 380px")}<div><h2>{t}</h2><p>{d}</p><span class="text-link">{U["learn_more"]}</span></div></a>' for k, t, d in A["cards"])
    body = page_hero(lang, cur, items, A["h1"], A["lead"], gpic("2058", lang, cur, eager=True)) + f"""
<section class="section section--flush-top"><div class="wrap"><div class="news-grid">{cards}</div></div></section>
{cta_band(lang, cur)}
"""
    ld = [breadcrumb_ld(items), webpage_ld("CollectionPage", lang, cur, A["title"], A["description"])]
    write(cur, page(lang, cur, "activities", alt, A["title"], A["description"], body, ld))

def build_news(lang):
    M = C[lang]; U = M.UI; N = M.NEWS; E = EXTRA[lang]
    cur = path_for("news", lang); alt = alt_of("news", lang)
    items = [home_crumb(lang), (U["nav_activities"], path_for("activities", lang)), (U["nav_news"], cur)]
    videos = "".join(
        f'<div class="yt" data-yt="{v}"><a class="yt-link" href="https://www.youtube.com/watch?v={v}" target="_blank" rel="noopener" aria-label="{N["video_label"]} {i + 1} ({U["external"]})">'
        f'<img src="https://i.ytimg.com/vi/{v}/hqdefault.jpg" alt="" width="480" height="360" loading="lazy" decoding="async"><span class="yt-play" aria-hidden="true">{PLAY}</span></a>'
        f'<p class="yt-title">{N["video_title"]} · {i + 1}</p></div>' for i, v in enumerate(N["videos"]))
    posters = "".join(f'<figure class="poster">{pic(MEDIA["news"][k], a, cur, "poster-img", sizes="(max-width: 760px) 92vw, 380px")}<figcaption>{cap}</figcaption></figure>' for k, cap, a in N["posters"])
    body = page_hero(lang, cur, items, N["h1"], N["lead"]) + f"""
<section class="section section--flush-top"><div class="wrap">
  <div class="section-head"><h2>{N['videos_h2']}</h2><p class="lead">{N['videos_p']}</p></div>
  <div class="yt-grid">{videos}</div>
</div></section>
<section class="section section--blush"><div class="wrap">
  <div class="section-head"><h2>{N['posters_h2']}</h2><p class="lead">{N['posters_p']}</p></div>
  <div class="poster-grid">{posters}</div>
</div></section>
{cta_band(lang, cur)}
"""
    ld = [breadcrumb_ld(items), webpage_ld("CollectionPage", lang, cur, N["title"], N["description"])]
    write(cur, page(lang, cur, "activities", alt, N["title"], N["description"], body, ld))

def build_events(lang):
    M = C[lang]; U = M.UI; V = M.EVENTS; ev = M.EVENT
    cur = path_for("events", lang); alt = alt_of("events", lang)
    items = [home_crumb(lang), (U["nav_activities"], path_for("activities", lang)), (U["nav_events"], cur)]
    leaders = ", ".join(f"<strong>{n}</strong> ({r})" for n, r in ev["leaders"])
    past = "".join(f'<figure class="poster">{pic(MEDIA["events"][k], t, cur, "poster-img", sizes="(max-width: 760px) 92vw, 380px")}<figcaption><strong>{t}</strong><span>{s}</span></figcaption></figure>' for k, t, s in V["past"])
    body = page_hero(lang, cur, items, V["h1"], V["lead"]) + f"""
<section class="section section--flush-top" id="proximo"><div class="wrap">
  <div class="section-head"><h2>{V['next_h2']}</h2></div>
  <div class="event-band event-band--page">
    <img src="{rel('assets/img/event-ansiedad-flyer-sm.jpg', cur)}" alt="{strip(ev['flyer_alt'])}" width="540" height="675" loading="lazy">
    <div>
      <span class="badge">{U['event_badge']}</span>
      <h3 class="event-band-h">{ev['title_es']}</h3>
      <p>{ev['summary']}</p>
      <ul class="event-facts event-facts--light">
        <li>{CAL}<div><strong>{ev['date']}</strong><span>{ev['time']}</span></div></li>
        <li>{PIN}<div><strong>{ev['venue']}</strong><span>{ev['address']}</span></div></li>
      </ul>
      <p class="event-leaders">{U['event_led_by']}: {leaders}</p>
      <div class="btn-row"><a class="btn btn--light" href="#event-modal" data-open-event>{U['event_reserve']}</a><a class="btn btn--ghost" href="tel:{TEL1}">{U['event_call']}</a></div>
    </div>
  </div>
</div></section>
<section class="section section--blush"><div class="wrap">
  <div class="section-head"><h2>{V['past_h2']}</h2><p class="lead">{V['past_p']}</p></div>
  <div class="poster-grid">{past}</div>
</div></section>
{cta_band(lang, cur)}
"""
    ld = [breadcrumb_ld(items), event_ld(lang), webpage_ld("CollectionPage", lang, cur, V["title"], V["description"])]
    write(cur, page(lang, cur, "activities", alt, V["title"], V["description"], body, ld))

def build_gallery(lang):
    M = C[lang]; U = M.UI; G = M.GALLERY
    cur = path_for("gallery", lang); alt = alt_of("gallery", lang)
    items = [home_crumb(lang), (U["nav_activities"], path_for("activities", lang)), (U["nav_gallery"], cur)]
    nums = [x["src"].split("img-")[1].split(".")[0] for x in MEDIA["gallery"]]
    tiles = "".join(
        f'<li><a class="g-item" href="{rel(m["src"], cur)}" data-w="{m["w"]}" data-h="{m["h"]}" aria-label="{G["open"]}: {strip(G["alts"][n])}">'
        f'<img src="{rel(m["sm"], cur)}" alt="{strip(G["alts"][n])}" width="{m["sm_w"]}" height="{round(m["h"] * m["sm_w"] / m["w"])}" loading="lazy" decoding="async"></a></li>'
        for n, m in zip(nums, MEDIA["gallery"]))
    labels = html.escape(json.dumps({"close": G["close"], "prev": G["prev"], "next": G["next"]}, ensure_ascii=False), quote=True)
    body = page_hero(lang, cur, items, G["h1"], G["lead"]) + f"""
<section class="section section--flush-top"><div class="wrap">
  <ul class="gallery" data-gallery data-labels="{labels}">{tiles}</ul>
</div></section>
{cta_band(lang, cur)}
"""
    ld = [breadcrumb_ld(items), {**webpage_ld("ImageGallery", lang, cur, G["title"], G["description"]),
          "image": [{"@type": "ImageObject", "contentUrl": BASE + m["src"], "caption": strip(G["alts"][n])} for n, m in zip(nums, MEDIA["gallery"])]}]
    write(cur, page(lang, cur, "activities", alt, G["title"], G["description"], body, ld))

def build_services_hub(lang):
    M = C[lang]; U = M.UI; S = M.SERVICES_HUB
    cur = path_for("services", lang); alt = alt_of("services", lang)
    items = [home_crumb(lang), (U["nav_services"], cur)]
    body = page_hero(lang, cur, items, S["h1"], S["lead"], pic(MEDIA["services"]["consulta"], "", cur, eager=True)) + f"""
<section class="section section--blush section--tight"><div class="wrap">
  <ul class="values values--two">
    <li><h2 class="values-h">{S['what_h2']}</h2><p>{S['what_p']}</p></li>
    <li><h2 class="values-h">{S['how_h2']}</h2><p>{S['how_p']}</p></li>
  </ul>
</div></section>
<section class="section"><div class="wrap svc-layout">
  <div class="section-head"><h2>{S['list_h2']}</h2></div>
  <div>{svc_list(lang, cur)}</div>
</div></section>
<section class="section section--blush" id="evaluaciones"><div class="wrap split">
  <div>
    <h2>{S['testing_h2']}</h2>
    <div class="mt-s">{''.join(f'<p>{p}</p>' for p in S['testing_p'])}</div>
    <a class="text-link" href="{rel(path_for('insurance', lang), cur)}#evaluaciones">{S['testing_link']}</a>
  </div>
  <div>
    <h2>{S['behavior_h2']}</h2>
    <p class="mt-s">{S['behavior_p']}</p>
  </div>
</div></section>
{cta_band(lang, cur)}
"""
    ld = [breadcrumb_ld(items),
          {"@context": "https://schema.org", "@type": "ItemList", "name": strip(S["h1"]), "itemListElement": [
              {"@type": "ListItem", "position": i + 1, "url": absurl(path_for("service", lang, s["id"])), "name": strip(s["name"])} for i, s in enumerate(M.SERVICES)]}]
    write(cur, page(lang, cur, "services", alt, S["title"], S["description"], body, ld))

def render_blocks(lang, cur, blocks):
    M = C[lang]; U = M.UI; out = []
    for b in blocks:
        kind = b[0]
        if kind in ("h2", "h3", "p"): out.append(f"<{kind}>{b[1]}</{kind}>")
        elif kind == "ul": out.append('<ul class="house-list">' + "".join(f"<li>{x}</li>" for x in b[1]) + "</ul>")
        elif kind == "workshops":
            out.append('<div class="card-grid">' + "".join(
                f'<article class="w-card">{pic(MEDIA["talleres"][k], "", cur, "w-card-img", sizes="(max-width: 760px) 92vw, 300px")}<div><h3>{t}</h3><p>{d}</p></div></article>'
                for k, t, d in M.WORKSHOPS) + "</div>")
        elif kind == "courses":
            cards = []
            for k, t, d, im, link in M.COURSES:
                media = pic(MEDIA["cursos"][im], "", cur, "w-card-img w-card-img--wide", sizes="(max-width: 760px) 92vw, 380px") if im else f'<div class="w-card-img w-card-img--wide w-card-blank">{house_svg_fill("w-card-house")}</div>'
                more = f'<a class="text-link" href="{link}" target="_blank" rel="noopener">{U["see_material"]}<span class="sr-only"> ({U["external"]})</span></a>' if link else ""
                cards.append(f'<article class="w-card">{media}<div><h3>{t}</h3><p>{d}</p>{more}</div></article>')
            out.append('<div class="card-grid card-grid--wide">' + "".join(cards) + "</div>")
    return "\n".join(out)

def build_service(lang, s):
    M = C[lang]; U = M.UI
    cur = path_for("service", lang, s["id"]); alt = alt_of("service", lang, s["id"])
    items = [home_crumb(lang), (U["nav_services"], path_for("services", lang)), (s["menu"] if len(s["menu"]) < 30 else s["name"], cur)]
    extra = f'<div class="btn-row mt-m"><a class="btn" href="{rel(path_for("contact", lang), cur)}">{U["cta_book_long"]}</a><a class="btn btn--ghost" href="tel:{TEL1}">{PHONE}{U["phone"]}</a></div>'
    wide = s["id"] in ("parent-workshops", "courses")
    staff = (f'<h2>{U["staff_title"]}</h2><div class="clinician-mini">' + "".join(
        f'<a href="{rel(path_for("person", lang, pid), cur)}">{staff_pic(pid, lang, cur, sizes="64px", alt="")}<div><strong>{person_by_id(lang, pid)["name"]}</strong><span>{person_by_id(lang, pid)["title_role"]}</span></div></a>'
        for pid in s["staff"]) + "</div>") if s["staff"] else f'<h2>{U["staff_title"]}</h2><p>{U["staff_none"]}</p>'
    main_col = f'<div class="prose">{render_blocks(lang, cur, s["body"])}{staff if not wide else ""}</div>'
    if wide:
        content = f'<section class="section section--blush"><div class="wrap">{main_col}<div class="prose mt-l">{staff}</div></div></section>'
    else:
        content = f'<section class="section section--blush"><div class="wrap content-grid">{main_col}{aside_card(lang, cur)}</div></section>'
    faq = f'<section class="section"><div class="wrap"><div class="section-head"><h2>{U["faq_title"]}</h2></div>{faq_block(s["faq"])}</div></section>' if s["faq"] else ""
    body = page_hero(lang, cur, items, s["h1"], s["lead"], pic(MEDIA["services"][s["img"]], "", cur, eager=True), extra) + content + faq + f"""
<section class="section section--tight{' section--flush-top' if faq else ''}"><div class="wrap">
  <div class="section-head"><h2>{U['related_services']}</h2></div>
  {related_cards(lang, cur, s['related'])}
</div></section>
{ART.related_for_service(sys.modules[__name__], lang, cur, ARTICLES, s['id'])}
{cta_band(lang, cur)}
"""
    ld = [breadcrumb_ld(items),
          {"@context": "https://schema.org", "@type": "Service", "name": strip(s["name"]), "serviceType": strip(s["name"]), "description": strip(s["description"]),
           "url": absurl(cur), "provider": {"@id": BASE + "#practice"}, "availableLanguage": ["Spanish", "English"],
           "areaServed": [{"@type": "City", "name": a["city"]} for a in M.AREAS],
           "availableChannel": {"@type": "ServiceChannel", "serviceLocation": {"@type": "Place", "name": "Healthy Solutions for Children and Families", "address": ADDRESS}}}]
    if s["faq"]: ld.append(faq_ld(s["faq"]))
    write(cur, page(lang, cur, "services", alt, s["title"], s["description"], body, ld))

def build_insurance(lang):
    M = C[lang]; U = M.UI; I = M.INSURANCE; E = EXTRA[lang]
    cur = path_for("insurance", lang); alt = alt_of("insurance", lang)
    items = [home_crumb(lang), (U["nav_insurance"], cur)]
    packs = "".join(f'<li class="pack"><strong>{a}</strong><span>{b}</span><span>{c}</span></li>' for a, b, c in I["packages"])
    tests = "".join(f'<li><strong>{a}</strong>{f"<span>{b}</span>" if b else ""}</li>' for a, b in I["testing"])
    plans = "".join(f'<li>{CHECK}<span><strong>{n}</strong>{f" <em class=\"in-net\">{I["in_network"]}</em>" if net else ""}</span></li>' for n, net in I["plans"])
    body = page_hero(lang, cur, items, I["h1"], I["lead"]) + f"""
<section class="section section--flush-top"><div class="wrap">
  <div class="section-head"><h2>{I['packages_h2']}</h2><p class="lead">{I['packages_p']}</p></div>
  <ul class="packs">{packs}</ul>
</div></section>
<section class="section section--blush" id="evaluaciones"><div class="wrap split split--top">
  <div><h2>{I['testing_h2']}</h2><p class="lead mt-s">{I['testing_p']}</p></div>
  <ul class="test-list">{tests}</ul>
</div></section>
<section class="section" id="seguros"><div class="wrap">
  <div class="section-head"><h2>{I['insurance_h2']}</h2></div>
  <div class="split split--top">
    <ul class="plan-list">{plans}</ul>
    <div>
      <p class="tricare">{I['tricare']}</p>
      <p>{I['logos_p']}</p>
    </div>
  </div>
  <div class="mt-l">{logo_strip(lang, cur)}</div>
</div></section>
<section class="section section--blush section--tight"><div class="wrap split">
  <div><h2>{I['contact_h2']}</h2>{contact_list(lang, cur)}</div>
  {map_iframe(lang)}
</div></section>
{cta_band(lang, cur)}
"""
    ld = [breadcrumb_ld(items), webpage_ld("WebPage", lang, cur, I["title"], I["description"]),
          {"@context": "https://schema.org", "@type": "ItemList", "name": strip(I["packages_h2"]),
           "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": f"{a} · {b} · {c}"} for i, (a, b, c) in enumerate(I["packages"])]}]
    write(cur, page(lang, cur, "insurance", alt, I["title"], I["description"], body, ld))

def build_staff_hub(lang):
    M = C[lang]; U = M.UI; T = M.STAFF_HUB
    cur = path_for("staff", lang); alt = alt_of("staff", lang)
    items = [home_crumb(lang), (U["nav_staff"], cur)]
    chips = f'<button class="chip" type="button" aria-pressed="true" data-filter="all">{T["filter_all"]}</button>' + "".join(
        f'<button class="chip" type="button" aria-pressed="false" data-filter="{k}">{v}</button>' for k, v in T["filters"])
    cards = "".join(
        f'<a class="team-card" href="{rel(path_for("person", lang, p["id"]), cur)}" data-tags="{" ".join(p["tags"])}">{staff_pic(p["id"], lang, cur, sizes="(max-width: 520px) 92vw, 300px")}'
        f'<div><h2>{p["name"]}{(" <span class=\"creds\">" + p["creds"] + "</span>") if p["creds"] else ""}</h2><p class="role">{p["title_role"]}</p></div>'
        f'<p class="short">{p["short"]}</p><span class="text-link">{U["view_profile"]} {p["first"]}</span></a>' for p in M.TEAM)
    body = page_hero(lang, cur, items, T["h1"], T["lead"]) + f"""
<section class="section section--flush-top"><div class="wrap">
  <div class="filters" data-filters=".team-card" role="group" aria-label="{T['filter_label']}"><span class="filters-label">{T['filter_label']}</span>{chips}</div>
  <div class="team-grid">{cards}</div>
  <p class="team-empty" hidden>{T['empty']}</p>
</div></section>
{cta_band(lang, cur)}
"""
    ld = [breadcrumb_ld(items),
          {"@context": "https://schema.org", "@type": "ItemList", "name": strip(T["h1"]), "itemListElement": [
              {"@type": "ListItem", "position": i + 1, "url": absurl(path_for("person", lang, p["id"])), "name": p["name"]} for i, p in enumerate(M.TEAM)]}]
    write(cur, page(lang, cur, "staff", alt, T["title"], T["description"], body, ld))

def build_person(lang, p):
    M = C[lang]; U = M.UI; E = EXTRA[lang]
    cur = path_for("person", lang, p["id"]); alt = alt_of("person", lang, p["id"])
    items = [home_crumb(lang), (U["nav_staff"], path_for("staff", lang)), (p["name"], cur)]
    where = "en Doral, FL" if lang == "es" else "in Doral, FL"
    title = f'{p["name"]} | {p["title_role"]} {where} | HSCF'
    if len(title) > 60: title = f'{p["name"]} | {p["title_role"]} | HSCF'
    desc = f'{p["name"]}{", " + p["creds"] if p["creds"] else ""}: {p["short"]} Healthy Solutions, Doral, FL.'
    if len(desc) > 158: desc = f'{p["name"]}: {p["short"]}'
    if len(desc) < 110: desc = desc + (" Atendemos en español e inglés en Doral, FL." if lang == "es" else " Bilingual care in Doral, FL.")
    ul = lambda lst: '<ul class="house-list">' + "".join(f"<li>{x}</li>" for x in lst) + "</ul>"
    details = []
    if p["focus"]: details.append(f'<div><h2>{U["focus"]}</h2>{ul(p["focus"])}</div>')
    if p["approaches"]: details.append(f'<div><h2>{U["approaches"]}</h2>{ul(p["approaches"])}</div>')
    if p["background"]: details.append(f'<div><h2>{U["background"]}</h2>{ul(p["background"])}</div>')
    if p["langs"]: details.append(f'<div><h2>{U["languages"]}</h2>{ul(p["langs"])}</div>')
    meta = f'<dl class="meta-row"><div><dt>{U["services_label"]}</dt><dd>{", ".join(svc_by_id(lang, sid)["name"] for sid in p["services"])}</dd></div>' + \
           (f'<div><dt>{U["languages"]}</dt><dd>{", ".join(p["langs"])}</dd></div>' if p["langs"] else "") + "</dl>"
    others = [x["id"] for x in M.TEAM if x["id"] != p["id"] and set(x["services"]) & set(p["services"])][:4]
    body = f"""<section class="page-hero"><div class="wrap">
  {crumbs(lang, cur, items)}
  <div class="profile-hero">
    {staff_pic(p['id'], lang, cur, 'house-img house', eager=True, sizes='(max-width: 900px) 80vw, 440px')}
    <div>
      <h1>{p['name']}{('<span class="creds">' + p['creds'] + '</span>') if p['creds'] else ''}</h1>
      <p class="role">{p['role']}</p>
      {meta}
      <div class="btn-row"><a class="btn" href="{rel(path_for('contact', lang), cur)}">{U['book_with']} {p['first']}</a><a class="btn btn--ghost" href="tel:{TEL1}">{PHONE}{U['phone']}</a></div>
    </div>
  </div>
</div></section>
<section class="section section--blush"><div class="wrap content-grid">
  <div class="prose">
    {f'<blockquote class="pull-quote"><p>{p["quote"]}</p></blockquote>' if p['quote'] else ''}
    {''.join(f'<p>{x}</p>' for x in p['bio'])}
    <div class="detail-grid">{''.join(details)}</div>
  </div>
  {aside_card(lang, cur)}
</div></section>
<section class="section section--tight"><div class="wrap">
  <div class="section-head"><h2>{U['services_label']}</h2></div>
  {related_cards(lang, cur, p['services'])}
  {('<div class="mt-l">' + staff_cards(lang, cur, others, 'team-row team-row--four') + '</div>') if others else ''}
  <p class="mt-l"><a class="text-link" href="{rel(path_for('staff', lang), cur)}">{U['all_staff']}</a></p>
</div></section>
"""
    person = {"@context": "https://schema.org", "@type": "Person", "name": p["name"], "jobTitle": strip(p["role"]),
              "image": BASE + MEDIA["staff"][p["id"]]["jpg"], "url": absurl(cur), "worksFor": {"@id": BASE + "#practice"},
              "description": strip(p["short"]), "knowsAbout": [strip(x) for x in p["focus"]],
              "workLocation": {"@type": "Place", "address": ADDRESS}}
    if p["creds"]: person["honorificSuffix"] = p["creds"]
    if p["langs"]: person["knowsLanguage"] = p["langs"]
    ld = [breadcrumb_ld(items), person]
    write(cur, page(lang, cur, "staff", alt, title, desc, body, ld, og_image=BASE + MEDIA["staff"][p["id"]]["jpg"]))

def build_contact(lang):
    M = C[lang]; U = M.UI; K = M.CONTACT; E = EXTRA[lang]
    cur = path_for("contact", lang); alt = alt_of("contact", lang)
    items = [home_crumb(lang), (U["nav_contact"], cur)]
    opts = lambda lst: "".join(f'<option value="{strip(o)}">{o}</option>' for o in lst)
    radios = lambda name, lst: "".join(f'<label><input type="radio" name="{name}" value="{strip(o)}"{" checked" if i == 0 else ""}><span>{o}</span></label>' for i, o in enumerate(lst))
    msgs = html.escape(json.dumps({"required": K["f_required"], "success": K["f_success"], "error": K["f_error"], "sending": K["f_sending"], "mailto": E["mailto_ok"], "subject": E["mail_subject"]}, ensure_ascii=False), quote=True)
    body = page_hero(lang, cur, items, K["h1"], K["lead"]) + f"""
<section class="section section--tight section--flush-top" id="book"><div class="wrap contact-grid">
  <div class="form-panel">
    <h2>{K['form_h2']}</h2>
    <p class="form-note">{K['form_note']}</p>
    <form data-contact-form action="https://formspree.io/f/YOUR_FORM_ID" method="POST" data-email="info@hscfdoral.com" data-msgs="{msgs}" novalidate>
      <div class="form-grid">
        <div class="field full"><label for="f-name">{K['f_name']}</label><input id="f-name" name="name" type="text" autocomplete="name" required></div>
        <div class="field"><label for="f-email">{K['f_email']}</label><input id="f-email" name="email" type="email" autocomplete="email" inputmode="email"></div>
        <div class="field"><label for="f-phone">{K['f_phone']}</label><input id="f-phone" name="phone" type="tel" autocomplete="tel" inputmode="tel"></div>
        <div class="field"><label for="f-for">{K['f_for']}</label><select id="f-for" name="for">{opts(K['f_for_opts'])}</select></div>
        <div class="field"><label for="f-service">{K['f_service']}</label><select id="f-service" name="service">{opts(K['f_service_opts'])}</select></div>
        <fieldset class="field"><legend>{K['f_lang']}</legend><div class="radio-row">{radios('language', K['f_lang_opts'])}</div></fieldset>
        <fieldset class="field"><legend>{K['f_contact']}</legend><div class="radio-row">{radios('contact_by', K['f_contact_opts'])}</div></fieldset>
        <div class="field full"><label for="f-msg">{K['f_msg']}</label><textarea id="f-msg" name="message" rows="4"></textarea></div>
        <div class="hp" aria-hidden="true"><label>Leave empty<input type="text" name="_gotcha" tabindex="-1" autocomplete="off"></label></div>
        <input type="hidden" name="page_language" value="{lang}">
        <div class="full"><button class="btn" type="submit">{K['f_submit']}</button></div>
      </div>
      <div class="form-status" role="status" tabindex="-1" hidden></div>
    </form>
  </div>
  <div>
    <h2 class="details-h">{K['details_h2']}</h2>
    {contact_list(lang, cur)}
    <div class="crisis-note"><p>{U['crisis']}</p></div>
  </div>
</div></section>
<section class="section section--tight"><div class="wrap">
  <div class="section-head"><h2>{K['map_h2']}</h2><p class="lead">{K['map_p']}</p>
  <div><a class="text-link" href="https://www.google.com/maps/dir/?api=1&amp;destination=8245+NW+36th+St+Ste+7+Doral+FL+33166" target="_blank" rel="noopener">{U['directions']}<span class="sr-only"> ({U['external']})</span></a></div></div>
  {map_iframe(lang, 'map-frame map-frame--wide')}
</div></section>
"""
    ld = [business_ld(lang), breadcrumb_ld(items), webpage_ld("ContactPage", lang, cur, K["title"], K["description"])]
    write(cur, page(lang, cur, "contact", alt, K["title"], K["description"], body, ld))

def build_areas_hub(lang):
    M = C[lang]; U = M.UI; A = M.AREAS_HUB
    cur = path_for("areas", lang); alt = alt_of("areas", lang)
    items = [home_crumb(lang), (U["nav_areas"], cur)]
    cards = "".join(f'<a class="area-card" href="{rel(path_for("area", lang, a["id"]), cur)}"><strong>{a["city"]}</strong><span>{a["lead"]}</span></a>' for a in M.AREAS)
    also = "".join(f"<li>{c}</li>" for c in A["also"])
    body = page_hero(lang, cur, items, A["h1"], A["lead"], pic(MEDIA["services"]["familia-atardecer"], "", cur, eager=True)) + f"""
<section class="section section--blush"><div class="wrap"><div class="area-grid">{cards}</div></div></section>
<section class="section"><div class="wrap split">
  <div><h2>{A['also_h2']}</h2><ul class="plain-cloud mt-m">{also}</ul></div>
  {map_iframe(lang)}
</div></section>
{cta_band(lang, cur)}
"""
    ld = [business_ld(lang), breadcrumb_ld(items)]
    write(cur, page(lang, cur, "", alt, A["title"], A["description"], body, ld))

def build_area(lang, a):
    M = C[lang]; U = M.UI
    cur = path_for("area", lang, a["id"]); alt = alt_of("area", lang, a["id"])
    items = [home_crumb(lang), (U["nav_areas"], path_for("areas", lang)), (a["city"], cur)]
    near = "".join(f'<li><a href="{rel(path_for("area", lang, n), cur)}">{next(x for x in M.AREAS if x["id"] == n)["city"]}</a></li>' for n in a["nearby"])
    extra = f'<div class="btn-row mt-m"><a class="btn" href="{rel(path_for("contact", lang), cur)}">{U["cta_book_long"]}</a><a class="btn btn--ghost" href="tel:{TEL1}">{PHONE}{U["phone"]}</a></div>'
    img_n = {"doral": "2050", "hialeah": "2052", "miami-lakes": "2069", "coral-gables": "2058", "kendall": "2073", "miami": "2084"}[a["id"]]
    body = page_hero(lang, cur, items, a["h1"], a["lead"], gpic(img_n, lang, cur, eager=True), extra) + f"""
<section class="section section--blush"><div class="wrap content-grid">
  <div class="prose">
    {''.join(f'<p>{x}</p>' for x in a['body'])}
    <h2>{U['drive']}</h2>
    <p>{a['drive']}</p>
    {map_iframe(lang)}
    <h2>{U['areas_nearby']}</h2>
    <ul class="city-cloud">{near}</ul>
  </div>
  {aside_card(lang, cur)}
</div></section>
<section class="section section--tight"><div class="wrap">
  <div class="section-head"><h2>{U['services_here']} {a['city']}</h2></div>
  {related_cards(lang, cur, a['services'])}
</div></section>
{cta_band(lang, cur)}
"""
    ld = [breadcrumb_ld(items),
          {"@context": "https://schema.org", "@type": "WebPage", "name": strip(a["title"]), "url": absurl(cur), "inLanguage": lang,
           "about": {"@id": BASE + "#practice"}, "mentions": {"@type": "City", "name": a["city"], "containedInPlace": {"@type": "State", "name": "Florida"}}}]
    write(cur, page(lang, cur, "", alt, a["title"], a["description"], body, ld))

def build_404():
    global ABS_LINKS
    ABS_LINKS = True
    lang = "es"; N = C["es"].NOT_FOUND; NE = C["en"].NOT_FOUND
    cur = "404.html"
    body = f"""<section class="nf"><div class="wrap">
  <img src="/assets/img/logo.png" alt="" width="312" height="287">
  <h1>{N['h1']}</h1>
  <p class="lead nf-lead">{N['p']}</p>
  <p class="lead nf-lead" lang="en">{NE['p']}</p>
  <div class="btn-row btn-row--center"><a class="btn" href="/">{N['home']}</a><a class="btn btn--ghost" href="/en/" lang="en">{NE['home']}</a></div>
</div></section>"""
    out = page(lang, cur, "", "en/index.html", N["title"], N["description"], body, [], robots="noindex")
    ABS_LINKS = False
    write(cur, out)

# ---------------------------------------------------------------- crawl + AI files
def build_sitemap(extra_urls):
    """extra_urls: (es_path, en_path, lastmod) from the article pipeline."""
    urls = []
    def add(key, ident=None):
        urls.append((path_for(key, "es", ident), path_for(key, "en", ident), TODAY))
    for k in ["home", "about", "activities", "news", "events", "gallery", "services", "insurance", "staff", "contact", "areas"]: add(k)
    for s in C["es"].SERVICES: add("service", s["id"])
    for p in C["es"].TEAM: add("person", p["id"])
    for a in C["es"].AREAS: add("area", a["id"])
    urls += extra_urls
    def pri(p):
        if p in ("index.html", "en/index.html"): return "1.0"
        return "0.9" if p.count("/") <= (2 if p.startswith("en/") else 1) else "0.7"
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for es, en, lastmod in urls:
        for p in (es, en):
            sm.append(f"  <url>\n    <loc>{absurl(p)}</loc>\n    <lastmod>{lastmod}</lastmod>\n    <priority>{pri(p)}</priority>\n"
                      f'    <xhtml:link rel="alternate" hreflang="es" href="{absurl(es)}"/>\n'
                      f'    <xhtml:link rel="alternate" hreflang="en" href="{absurl(en)}"/>\n'
                      f'    <xhtml:link rel="alternate" hreflang="x-default" href="{absurl(es)}"/>\n  </url>')
    sm.append("</urlset>")
    write("sitemap.xml", "\n".join(sm) + "\n")
    return urls

def build_crawler_files(cfg, preview=False):
    """robots.txt, ai.txt and .htaccess. All AI-crawler choices come from seo/config.json."""
    bots = {}
    for group in ("search_and_answer", "training"):
        for name, rule in cfg["ai_crawlers"][group].items():
            bots[name] = (group, rule)
    lines = ["# robots.txt for hscfdoral.com", "# Generated by build/build.py from seo/config.json. Edit that file, not this one.", ""]
    if preview:
        lines += ["User-agent: *", "Disallow: /", ""]
    else:
        lines += ["User-agent: *", "Allow: /", "Disallow: /404.html", ""]
        for group, title in (("search_and_answer", "AI search and answer engines (they can find and cite the site)"), ("training", "AI model training crawlers")):
            for rule in ("allow", "disallow"):
                names = [n for n, (g, r) in bots.items() if g == group and r == rule]
                if not names: continue
                lines.append(f"# {title}: {rule}")
                lines += [f"User-agent: {n}" for n in names]
                lines += ["Allow: /", "Disallow: /404.html"] if rule == "allow" else ["Disallow: /"]
                lines.append("")
    lines.append(f"Sitemap: {BASE}sitemap.xml")
    write("robots.txt", "\n".join(lines) + "\n")
    training = cfg["ai_crawlers"]["training"]
    allow_training = sum(1 for r in training.values() if r == "allow") >= len(training) / 2
    ai = ["# ai.txt for hscfdoral.com (Spawning ai.txt format)", "# Says whether this site's text and media may be used to train AI models.",
          "# Generated from seo/config.json -> ai_crawlers.training. Per-crawler rules live in robots.txt.", "# Contact: info@hscfdoral.com", "", "User-Agent: *"]
    ai += (["Allow: /", "Disallow: /404.html"] if allow_training else ["Disallow: /"])
    write("ai.txt", "\n".join(ai) + "\n")
    write(".htaccess", htaccess())

# Old WordPress addresses that moved. Everything else on the old site keeps its exact address.
REDIRECTS = [
    ("contact-us", "contacto/"), ("trainings", "cursos-y-talleres/"), ("novedades-2", "novedades/"),
    ("mentores", "staff/"), ("annette-dallera", "staff/"), ("sandra-alvarez", "staff/"),
    ("2021/06/play-therapy-training-module-1", "2021/06/lisa-saldana-presents-play-therapy-training/"),
    ("2021/06/play-therapy-training-module-2", "2021/06/lisa-saldana-presents-play-therapy-training/"),
    ("2021/07/play-therapy-training-working-with-familes-with-play-therapy", "2021/06/lisa-saldana-presents-play-therapy-training/"),
    ("2021/06/capacitacion", "2021/06/lisa-saldana-presents-play-therapy-training/"),
    ("category/.*", "blog/"), ("author/.*", "blog/"), ("blog/page/[0-9]+", "blog/"), ("feed", "blog/feed.xml"),
]

def htaccess():
    rules = list(REDIRECTS)
    for p in C["es"].TEAM:
        for old in p["old"]: rules.append((old, p["id"] + "/"))
    for t in C["es"].TESTIMONIALS: rules.append((t["old"], "#testimonios"))
    lines = "\n".join(f"  RewriteRule ^{src}/?$ /{dst} [L,R=301,NE]" for src, dst in rules)
    return HTACCESS.replace("@@REDIRECTS@@", lines)

HTACCESS = r"""# hscfdoral.com — Apache settings for the static site (ignored by non-Apache servers)
# Generated by build/build.py. Edit REDIRECTS in build.py, not this file.

ErrorDocument 404 /404.html
Options -Indexes
DirectoryIndex index.html

# Correct file types
AddType application/manifest+json .webmanifest
AddType font/woff2 .woff2
AddType video/mp4 .mp4
AddType image/webp .webp
AddType application/rss+xml .xml
AddType text/plain .txt
AddDefaultCharset utf-8

<IfModule mod_rewrite.c>
  RewriteEngine On

  # Never serve hidden files (except .well-known)
  RewriteRule "(^|/)\.(?!well-known/)" - [F]

  # Force HTTPS and the bare domain. Turn on only after SSL works on the server,
  # otherwise the site will redirect in a loop. Remove the leading "# " on the 4 lines.
  # RewriteCond %{HTTPS} off [OR]
  # RewriteCond %{HTTP_HOST} ^www\. [NC]
  # RewriteCond %{HTTP_HOST} ^(?:www\.)?(.+)$ [NC]
  # RewriteRule ^ https://%1%{REQUEST_URI} [L,R=301]

  # Old WordPress addresses that moved (most old addresses are unchanged)
@@REDIRECTS@@

  # The old WordPress system is gone
  RewriteRule ^(wp-admin|wp-login\.php|wp-content|wp-includes|wp-json|xmlrpc\.php)(/.*)?$ - [G]
</IfModule>

# Compression
<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE text/html text/css text/plain text/xml application/javascript application/json application/ld+json application/xml application/rss+xml image/svg+xml
</IfModule>

# Caching: pages revalidate, assets cache for a month
<IfModule mod_expires.c>
  ExpiresActive On
  ExpiresDefault "access plus 1 hour"
  ExpiresByType text/html "access plus 0 seconds"
  ExpiresByType application/rss+xml "access plus 1 hour"
  ExpiresByType text/css "access plus 30 days"
  ExpiresByType application/javascript "access plus 30 days"
  ExpiresByType image/png "access plus 30 days"
  ExpiresByType image/jpeg "access plus 30 days"
  ExpiresByType image/webp "access plus 30 days"
  ExpiresByType font/woff2 "access plus 1 year"
  ExpiresByType video/mp4 "access plus 30 days"
</IfModule>

# Security headers
<IfModule mod_headers.c>
  Header always set X-Content-Type-Options "nosniff"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
  Header always set X-Frame-Options "SAMEORIGIN"
  Header always set Permissions-Policy "camera=(), microphone=(), geolocation=()"
</IfModule>
"""

def build_llms(cfg, arts):
    """llms.txt (llmstxt.org format) and llms-full.txt, generated from the same content as the pages."""
    ES, EN = C["es"], C["en"]; U = EN.UI
    sh = lambda t: re.sub(r"<[^>]+>", "", t.replace("<br>", "; ")).replace("&amp;", "&").replace("&nbsp;", " ")
    L = ["# Healthy Solutions for Children and Families (HSCF)", "",
         "> Bilingual (Spanish and English) mental health center in Doral, Florida. Psychotherapy for children, teens, adults, couples and families; ABA therapy; psychological and developmental testing for ages 2 to 21; parent workshops; neurofeedback, reflective yoga, coaching and hypnotherapy. The site's main language is Spanish; English pages are under /en/.", "",
         "Key facts:",
         f"- Address: {U['address_line1']}, {U['address_line2']}",
         f"- Phone: {U['phone']} or {U['phone2']} · Email: {U['email']}",
         "- Languages: Spanish and English (one therapist also works in Portuguese)",
         "- Insurance: in network with Aetna, Blue Cross Blue Shield, Cigna and UnitedHealthcare; also works with Oscar and Bind; does not accept TRICARE",
         "- Private packages: 8, 12 or 16 weekly sessions",
         "- Areas served: " + ", ".join(cfg["markets"]["primary"] + cfg["markets"]["secondary"]),
         "- Not an emergency service. In a crisis, call or text 988 (Suicide & Crisis Lifeline) or call 911.", "",
         "## Services", ""]
    L += [f"- [{s['name']}]({absurl(path_for('service', 'en', s['id']))}): {sh(s['short'])}" for s in EN.SERVICES]
    L += [f"- [Insurance, packages and testing]({absurl(path_for('insurance', 'en'))}): {sh(EN.INSURANCE['description'])}"]
    L += ["", "## Staff", ""]
    L += [f"- [{p['name']}{', ' + p['creds'] if p['creds'] else ''}]({absurl(path_for('person', 'en', p['id']))}): {p['role']}. {sh(p['short'])}" for p in EN.TEAM]
    if arts:
        L += ["", "## Blog", ""]
        L += [f"- [{a['meta']['en']['title']}]({absurl(path_for('article', 'en', a['id']))}): {a['meta']['en']['summary']}" for a in arts[:30]]
    L += ["", "## En español (idioma principal)", ""]
    L += [f"- [Inicio]({absurl(path_for('home', 'es'))}): {sh(ES.HOME['hero_lead'])}"]
    L += [f"- [{s['name']}]({absurl(path_for('service', 'es', s['id']))}): {sh(s['short'])}" for s in ES.SERVICES]
    L += [f"- [Seguros y paquetes]({absurl(path_for('insurance', 'es'))}): {sh(ES.INSURANCE['description'])}"]
    L += [f"- [{a['meta']['es']['title']}]({absurl(path_for('article', 'es', a['id']))}): {a['meta']['es']['summary']}" for a in arts[:30]]
    L += ["", "## Optional", "",
          f"- [About us]({absurl(path_for('about', 'en'))})",
          f"- [Events]({absurl(path_for('events', 'en'))}): the free Hablemos sobre Ansiedad workshop and past events",
          f"- [Contact]({absurl(path_for('contact', 'en'))})",
          f"- [Areas we serve]({absurl(path_for('areas', 'en'))})",
          f"- [Full text for AI assistants]({BASE}llms-full.txt)",
          f"- [Sitemap]({BASE}sitemap.xml)"]
    write("llms.txt", "\n".join(L) + "\n")
    F = ["# Healthy Solutions for Children and Families — full text", "",
         f"Source: {BASE} · Generated {TODAY} from the site's content. Information is general and not a substitute for care.", ""]
    F += ["## About", ""] + [sh(x) for x in EN.ABOUT["p"]] + [""]
    for s in EN.SERVICES:
        F += [f"## {s['name']} ({absurl(path_for('service', 'en', s['id']))})", "", sh(s["lead"]), ""]
        for b in s["body"]:
            if b[0] in ("p", "h2", "h3"): F.append(("### " if b[0] != "p" else "") + sh(b[1]))
            elif b[0] == "ul": F += [f"- {sh(x)}" for x in b[1]]
            elif b[0] == "workshops": F += [f"- {t}: {d}" for k, t, d in EN.WORKSHOPS]
            elif b[0] == "courses": F += [f"- {t}: {d}" for k, t, d, im, ln in EN.COURSES]
        F += [""] + [f"Q: {sh(q)}\nA: {sh(a)}\n" for q, a in s["faq"]]
    I = EN.INSURANCE
    F += ["## Insurance and packages", ""] + [f"- {a}, {b.lower()}, {c.lower()}" for a, b, c in I["packages"]]
    F += ["", I["testing_p"]] + [f"- {a}{' (' + b + ')' if b else ''}" for a, b in I["testing"]]
    F += ["", "Insurance: " + ", ".join(n + (" (in network)" if net else "") for n, net in I["plans"]) + ". " + I["tricare"], ""]
    F += ["## Frequently asked questions", ""] + [f"Q: {sh(q)}\nA: {sh(a)}\n" for q, a in EN.HOME["faq"]]
    for a in arts:
        for lang in ("en", "es"):
            m = a["meta"]; loc = m[lang]
            F += [f"## {loc['title']} ({absurl(path_for('article', lang, a['id']))})", ""]
            if m.get("medical_reviewer"): F.append(f"Clinically reviewed by {m['medical_reviewer']['name']}, {m['medical_reviewer']['credentials']} on {m['medical_reviewer']['reviewed_on']}.")
            F += ["", ART.plain_text(a["body"][lang]), ""]
            if m.get("sources"):
                F += ["Sources:"] + [f"[{x['id']}] {x['authors']} ({x['year']}). {x['title']}. {x['publisher']}. {x['url']}" for x in sorted(m["sources"], key=lambda x: x["id"])]
            F.append("")
    write("llms-full.txt", "\n".join(F) + "\n")

def build_static_misc():
    write("site.webmanifest", json.dumps({
        "name": "Healthy Solutions for Children and Families", "short_name": "HSCF", "start_url": "/", "display": "standalone",
        "background_color": "#FFFBF7", "theme_color": "#FE4109", "lang": "es",
        "icons": [{"src": "/assets/img/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "/assets/img/icon-512.png", "sizes": "512x512", "type": "image/png"}]}, indent=2))

def clean_output():
    """Remove previously generated files so deleted pages and articles do not linger. assets/ is never touched."""
    if not os.path.isdir(OUT): return
    for name in os.listdir(OUT):
        full = os.path.join(OUT, name)
        if name == "assets": continue
        if os.path.isdir(full): shutil.rmtree(full)
        elif name.endswith((".html", ".xml", ".txt", ".webmanifest")) or name in (".htaccess", "CNAME", ".nojekyll"): os.remove(full)

def main(argv=None):
    import argparse
    global OUT, ARTICLES
    ap = argparse.ArgumentParser(description="Build hscfdoral.com (Spanish + English) into site/.")
    ap.add_argument("--check", action="store_true", help="validate content only, write nothing")
    ap.add_argument("--drafts", action="store_true", help="also build draft and in-review articles into preview/ (never deploy preview/)")
    args = ap.parse_args(argv)
    svc_ids = {s["id"] for s in C["es"].SERVICES}; team_ids = {p["id"] for p in C["es"].TEAM}
    arts, errors, warnings = ART.load(svc_ids, team_ids, include_drafts=args.drafts or args.check, strict=not (args.drafts or args.check))
    for w in warnings: print("warning:", w)
    for e in errors: print("ERROR:", e)
    if errors:
        print(f"{len(errors)} error(s). Nothing was built."); return 1
    if args.check:
        print(f"OK: {len(arts)} article(s) checked, {len(warnings)} warning(s)."); return 0
    taken = {PAGES[k][0].strip("/") for k in PAGES} | {s["slug"] for s in C["es"].SERVICES} | team_ids
    for a in arts:
        d = (a["meta"].get("date_published") or a["meta"]["date_modified"])[:7].replace("-", "/")
        for lang in LANGS:
            ARTICLE_PATHS[lang][a["id"]] = ("" if lang == "es" else "en/") + d + "/" + a["meta"][lang]["slug"] + "/"
        legacy = a["meta"].get("legacy_url")
        if legacy and legacy.strip("/") + "/" != ARTICLE_PATHS["es"][a["id"]]:
            print(f"ERROR: content/articles/{a['id']}: legacy_url {legacy} does not match its new address /{ARTICLE_PATHS['es'][a['id']]}"); return 1
    ARTICLES = arts
    if args.drafts:
        OUT = os.path.join(ROOT, "preview")
        if os.path.isdir(OUT): shutil.rmtree(OUT)
        shutil.copytree(os.path.join(ROOT, "site", "assets"), os.path.join(OUT, "assets"))
    else:
        clean_output()
    cfg = _seo_config()
    for lang in LANGS:
        build_home(lang); build_about(lang); build_activities(lang); build_news(lang); build_events(lang); build_gallery(lang)
        build_services_hub(lang); build_insurance(lang); build_staff_hub(lang); build_contact(lang); build_areas_hub(lang)
        for s in C[lang].SERVICES: build_service(lang, s)
        for p in C[lang].TEAM: build_person(lang, p)
        for a in C[lang].AREAS: build_area(lang, a)
    art_urls = ART.build_all(sys.modules[__name__], arts, drafts=args.drafts)
    build_404()
    urls = build_sitemap(art_urls)
    build_crawler_files(cfg, preview=args.drafts)
    build_llms(cfg, arts)
    build_static_misc()
    live = sum(1 for a in arts if a["meta"]["status"] == "published")
    print(f"built {len(urls) * 2 + 1} pages into {os.path.relpath(OUT, ROOT)}/ ({live} published post(s){', drafts included' if args.drafts else ''})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
