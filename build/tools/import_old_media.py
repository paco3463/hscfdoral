#!/usr/bin/env python3
"""One-time import of the old WordPress media into site/assets/img/.

    python3 build/tools/import_old_media.py /path/to/hscfdoral-media

Resizes, crops and compresses each file, writes WebP (plus a small -sm.webp for cards and
phones, and a JPEG for staff portraits used in structured data), and writes
build/media.json with the final paths and pixel sizes the generator uses.
Re-run it any time the source folder changes; it overwrites its own output only.
"""
import json, os, sys
from PIL import Image, ImageOps

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "site", "assets", "img")

# key -> (source path inside the media folder, output path under assets/img, mode)
# mode: "photo" (max 1600, sm 640), "portrait" (crop 4:5, 900x1125), "logo" (fit 360x160 on white)
STAFF = {
    "jorge-garcia": "2025/05/320x400-1.png", "armando-matiz-reyes": "2020/06/PHOTO-2020-06-07-21-09-39-1.jpg",
    "maria-cecilia-mauricio": "2020/07/yo-1.jpg", "jose-mesa": "2020/10/JOSE-MESA.jpg",
    "juan-felipe-diaz": "2021/04/Juan-Felipe-Diaz-1.jpeg", "paula-callegari": "2025/05/1699537343234.jpg",
    "silvia-lugo": "2022/04/Silvia-1.jpg", "alibel-osorio": "2022/04/20220429_113556.jpg",
    "beatriz-pedreira": "2023/05/Beatriz-Pedreira-1.jpg",
}
GALLERY = [n for n in ("2049 2050 2051 2052 2053 2054 2055 2056 2057 2058 2059 2060 2061 2062 2063 2064 2065 2066 "
                       "2068 2069 2071 2072 2073 2074 2075 2076 2079 2080 2081 2082 2083 2084 2085").split()]
EVENTS = {
    "arte-una-herramienta": "2019/12/arte-una-herramienta_Mesa-de-trabajo-1-1-scaled.jpg", "sindrome-de-asperger": "2019/12/asperger-01-1.jpg",
    "la-vida-sin-limites": "2019/12/degustando1-01-1-scaled.jpg", "la-vida-sin-limites-2": "2019/12/degustando2-01-1.jpg",
    "embellecerte": "2019/12/embellecer2-01-1.jpg", "neurofeedback-en": "2019/12/neurofeedback-02-2-scaled.jpg",
    "neurofeedback-es": "2019/12/neurofeedback-01-2-scaled.jpg", "lo-que-no-mata-fortalece": "2019/12/lo-que-no-mata_Mesa-de-trabajo-1-1.jpg",
    "la-conciencia-los-sentimientos": "2019/12/La-conciencia-los-sentimientos-01-1.jpg", "habia-una-vez-edipo-rey": "2019/12/EXPRESARSE-02-1-scaled.jpg",
    "el-arte-del-reencuentro": "2019/12/family2.jpg",
}
TALLERES = {
    "sos-adolescencia": "2019/12/simon-maage-tXiMrX3Gc-g-unsplash-scaled.jpg", "bailando-con-los-miedos": "2019/12/kiwihug-P_GeWr5wNQc-unsplash-scaled.jpg",
    "bulimia-y-anorexia": "2019/12/anthony-tran-i-ePv9Dxg7U-unsplash-scaled.jpg", "inteligencia-emocional": "2019/12/ben-white-TlBF3ZUVTvE-unsplash-scaled.jpg",
    "por-que-me-enfermo": "2019/12/twinsfisch-GFKPATimbvM-unsplash-scaled.jpg", "cuando-la-adolescencia-toca-la-puerta": "2019/12/cuando-la-adolescenncia.jpeg",
    "el-arte-del-reencuentro": "2019/12/frank-mckenna-cRLEVt6SZxI-unsplash-scaled.jpg", "mi-paz-no-es-negociable": "2019/12/daniel-mingook-kim-H7sHkM9eilw-unsplash-scaled.jpg",
    "mujeres-de-nuestra-edad": "2019/12/artem-beliaikin-j5almO1E8rU-unsplash-scaled.jpg", "amor-y-ego": "2019/12/taylor-smith-C44h1ZmlFF0-unsplash-scaled.jpg",
    "bullying": "2019/12/kat-j-NPmR0RblyhQ-unsplash-scaled.jpg", "promoviendo-relaciones-saludables": "2019/12/everton-vila-AsahNlC0VhQ-unsplash-scaled.jpg",
    "descubriendo-el-oro": "2019/12/svyatoslav-romanov-r38u2Uq1AXk-unsplash-1-scaled.jpg",
}
CURSOS = {
    "sindrome-de-la-cabana": "2020/07/Image-3.jpg", "resistencia-al-mejoramiento": "2020/06/resistencia-al-mejoramiento.jpg",
    "taller-lenguaje": "2020/06/Taller-Lenguaje.jpg", "taller-neuroplasticidad": "2020/06/Taller-Euro.jpg",
}
NEWS = {
    "biodecodificacion-neuroemocional": "2020/08/WhatsApp-Image-2020-07-22-at-9.48.40-PM.jpeg",
    "cuando-la-adolescencia-curso": "2020/08/WhatsApp-Image-2020-07-22-at-9.48.40-PM-1.jpeg",
    "ansiedad-en-tiempos-de-pandemia": "2020/08/WhatsApp-Image-2020-07-22-at-9.48.40-PM-2.jpeg",
}
SERVICES = {  # page photos the old site used
    "psicoterapia": "2019/12/toa-heftiba-_UIVmIBB3JU-unsplash.jpg", "yoga": "2019/12/erik-brolin-ZARfCYDaVg0-unsplash-scaled.jpg",
    "coaching": "2019/12/brujala-scaled.jpg", "hipnoterapia": "2019/12/benoit-beaumatin-xdai21Y9pek-unsplash-scaled.jpg",
    "consulta": "2019/12/tim-gouw-bwki71ap-y8-unsplash.jpg", "talleres": "2019/12/ben-white-TlBF3ZUVTvE-unsplash-scaled.jpg",
    "familia-atardecer": "2019/12/frank-mckenna-cRLEVt6SZxI-unsplash-scaled.jpg", "aprendizaje": "2019/12/john-schnobrich-yFbyvpEGHFQ-unsplash-1-scaled.jpg",
    "equipo-trabajo": "2019/12/helloquence-5fNmWej4tAA-unsplash-scaled.jpg", "aba": "2019/12/artem-beliaikin-j5almO1E8rU-unsplash-scaled.jpg",
}
BLOG = {
    "prioritize-mental-health": ["2023/05/Neutral-Minimalist-New-Website-Launch-Mockup-Instagram-Post.png"],
    "anxiety-attacks": ["2022/07/Logo-con-circulo-dibujado-a-mano.png"],
    "why-see-a-psychologist": ["2022/04/Naranja-Negocios-Servicios-Sitio-Web-2.png"],
    "teen-groups": ["2022/02/WhatsApp-Image-2022-01-22-at-11.14.08-AM-1.jpeg"],
    "staying-healthy": ["2022/01/woman-good-mood-raises-arm-with-muscles-has-strong-body-dressed-gym-outfit-listens-audio-via-modern-headphones-poses-indoor-scaled.jpg"],
    "mind-body-health": ["2021/11/young-woman-doing-padmasana-exercise_1163-5086.jpg"],
    "attention-and-focus": ["2021/10/Wavy_Ppl-03_Single-03-scaled.jpg"],
    "what-is-memory": ["2021/09/memoria-acceso-experiencias-1.jpg"],
    "what-is-cogmed": ["2021/08/3d-medical-figure-with-brain-highlighted.jpg"],
    "helping-children-through-separation": ["2021/07/tadeusz-lakota-wZAQJLjDWNY-unsplash.jpg"],
    "family-wellbeing": ["2021/06/cdc-SAwxJ8PHY3Q-unsplash-1.jpg"],
    "covid-19-emotional-balance": ["2021/04/cdc-5gUNHmQ0xE8-unsplash-1.jpg"],
    "improve-your-mental-health": ["2021/05/mental-health-week-blog-post-tips.jpg"],
    "assertive-communication": ["2021/06/gradikaa-aggi-x31bLGlH6U0-unsplash.jpg"],
    "play-therapy-training-2021": ["2021/06/lisa-saldana.jpeg", "2021/06/play-1.jpeg", "2021/06/play-2.jpeg",
                                   "2021/07/PHOTO-2021-07-12-11-22-20.jpg", "2021/07/PHOTO-2021-07-12-11-22-20-1.jpg", "2021/06/image2.jpeg"],
}
LOGOS = {
    "aetna": "2019/12/Aetna-Logo-1.png", "bcbs": "2019/12/bluecroos-1.png", "cigna": "2019/12/cigna-1.png",
    "unitedhealthcare": "2019/12/unitedhealthcare-1.png", "oscar": "2025/06/oscar-health-logo-1.png", "bind": "2023/04/bind-logo-1.png",
    "optum": "2025/06/optum-vector-logo.png", "avmed": "2025/06/avmed-logo-1.jpg", "lucet": "2025/06/Lucet-Health-logo.webp",
    "umr": "2023/04/Diseno-sin-titulo-43.png", "anthem": "2023/04/Diseno-sin-titulo-46.png",
}


# SEO file names (Spanish, the site's main language): descriptive, lowercase, hyphens, no accents.
# The keys above stay the same (the generator looks photos up by key); only the published file names change.
NAMES = {
    "staff": {
        "jorge-garcia": "jorge-garcia-terapeuta-hscf-doral", "armando-matiz-reyes": "armando-matiz-reyes-hipnosis-clinica-hscf-doral",
        "maria-cecilia-mauricio": "maria-cecilia-mauricio-coach-terapeuta-hscf-doral", "jose-mesa": "jose-mesa-analista-de-conducta-bcaba-hscf-doral",
        "juan-felipe-diaz": "juan-felipe-diaz-consejero-hscf-doral", "paula-callegari": "paula-callegari-terapeuta-trilingue-hscf-doral",
        "silvia-lugo": "silvia-lugo-psicologia-del-deporte-hscf-doral", "alibel-osorio": "alibel-osorio-terapeuta-hscf-doral",
        "beatriz-pedreira": "beatriz-pedreira-trabajadora-social-hscf-doral",
    },
    "services": {
        "aba": "terapia-aba-doral", "psicoterapia": "psicoterapia-individual-familiar-parejas-doral",
        "talleres": "talleres-y-charlas-para-padres-doral", "aprendizaje": "neurofeedback-atencion-concentracion-doral",
        "yoga": "yoga-reflexivo-doral", "coaching": "coaching-personal-doral", "hipnoterapia": "hipnoterapia-relajacion-doral",
        "equipo-trabajo": "cursos-y-talleres-psicologia-doral", "consulta": "servicios-de-salud-mental-doral",
        "familia-atardecer": "terapia-familiar-miami-dade",
    },
    "gallery": {
        "2049": "equipo-hscf-evento-comunitario", "2050": "stand-hscf-feria-comunitaria-doral", "2051": "terapeutas-hscf-evento",
        "2052": "feria-comunitaria-familias-hscf", "2053": "firma-de-libro-evento-hscf", "2054": "equipo-hscf-encuentro",
        "2055": "grupo-de-mujeres-evento-hscf", "2056": "participantes-taller-hscf", "2057": "libro-cuando-la-adolescencia-toca-la-puerta",
        "2058": "terapeutas-hscf-grupo", "2059": "presentacion-libro-adolescencia-hscf", "2060": "sala-de-reuniones-hscf-doral",
        "2061": "encuentro-grupal-hscf", "2062": "taller-de-mujeres-hscf", "2063": "collage-taller-mujeres-de-mi-edad",
        "2064": "taller-presentacion-pizarra-hscf", "2065": "taller-materiales-hscf", "2066": "manualidad-ama-a-tu-familia-hscf",
        "2068": "charla-comunitaria-hscf", "2069": "grupo-taller-mujeres-hscf", "2071": "grupo-participantes-taller-hscf",
        "2072": "dinamica-taller-hscf", "2073": "participantes-charla-hscf", "2074": "facilitadora-taller-hscf",
        "2075": "volante-taller-para-padres-doral", "2076": "volante-como-ser-guias-para-hijos-saludables",
        "2079": "charla-para-padres-hscf", "2080": "charla-con-presentacion-hscf", "2081": "conferencia-psicologia-hscf",
        "2082": "charla-audiencia-hscf", "2083": "taller-dharma-holistic-center-doral", "2084": "charla-comunidad-hscf",
        "2085": "terapeutas-hscf-dharma-holistic-center",
    },
    "events": {
        "arte-una-herramienta": "evento-arte-una-herramienta-hscf", "sindrome-de-asperger": "evento-sindrome-de-asperger-hscf",
        "la-vida-sin-limites": "evento-la-vida-sin-limites-hscf", "la-vida-sin-limites-2": "evento-la-vida-sin-limites-2-hscf",
        "embellecerte": "evento-embellecerte-hscf", "neurofeedback-en": "evento-neurofeedback-ingles-hscf",
        "neurofeedback-es": "evento-neurofeedback-hscf", "lo-que-no-mata-fortalece": "evento-lo-que-no-mata-fortalece-hscf",
        "la-conciencia-los-sentimientos": "evento-la-conciencia-los-sentimientos-hscf", "habia-una-vez-edipo-rey": "evento-habia-una-vez-edipo-rey-hscf",
        "el-arte-del-reencuentro": "evento-el-arte-del-reencuentro-taller-padres-hscf",
    },
    "talleres": {
        "sos-adolescencia": "taller-sos-adolescencia", "bailando-con-los-miedos": "taller-bailando-con-los-miedos",
        "bulimia-y-anorexia": "taller-bulimia-y-anorexia", "inteligencia-emocional": "taller-inteligencia-emocional",
        "por-que-me-enfermo": "taller-por-que-me-enfermo", "cuando-la-adolescencia-toca-la-puerta": "taller-cuando-la-adolescencia-toca-la-puerta",
        "el-arte-del-reencuentro": "taller-el-arte-del-reencuentro", "mi-paz-no-es-negociable": "taller-mi-paz-no-es-negociable",
        "mujeres-de-nuestra-edad": "taller-mujeres-de-nuestra-edad", "amor-y-ego": "taller-amor-y-ego", "bullying": "taller-bullying-acoso-escolar",
        "promoviendo-relaciones-saludables": "taller-promoviendo-relaciones-saludables", "descubriendo-el-oro": "taller-descubriendo-el-oro",
    },
    "cursos": {
        "sindrome-de-la-cabana": "curso-sindrome-de-la-cabana", "resistencia-al-mejoramiento": "curso-resistencia-al-mejoramiento",
        "taller-lenguaje": "curso-lenguaje-de-poder", "taller-neuroplasticidad": "curso-neuroplasticidad",
    },
    "news": {
        "biodecodificacion-neuroemocional": "curso-biodecodificacion-neuroemocional", "cuando-la-adolescencia-curso": "curso-cuando-la-adolescencia-toca-la-puerta",
        "ansiedad-en-tiempos-de-pandemia": "charla-ansiedad-en-tiempos-de-pandemia",
    },
    "blog": {  # the post's Spanish address
        "prioritize-mental-health": "priorizar-la-salud-mental", "anxiety-attacks": "como-manejar-los-ataques-de-ansiedad",
        "why-see-a-psychologist": "la-importancia-del-profesional-en-psicologia", "teen-groups": "grupos-para-adolescentes-hscf",
        "staying-healthy": "estar-sano-depende-de-ti", "mind-body-health": "salud-mente-cuerpo", "attention-and-focus": "la-atencion-y-la-concentracion",
        "what-is-memory": "que-es-la-memoria", "what-is-cogmed": "que-es-cogmed", "helping-children-through-separation": "ayudar-al-nino-con-la-separacion-de-sus-padres",
        "family-wellbeing": "el-bienestar-en-la-familia", "covid-19-emotional-balance": "balance-emocional-despues-del-covid-19",
        "improve-your-mental-health": "como-mejorar-mi-salud-mental", "assertive-communication": "la-comunicacion-asertiva",
        "play-therapy-training-2021": "capacitacion-terapia-de-juego-2021",
    },
    "logos": {k: f"seguro-{k}-aceptado-hscf" for k in ("aetna", "bcbs", "cigna", "unitedhealthcare", "oscar", "bind", "optum", "avmed", "lucet", "umr", "anthem")},
}

def load(src):
    im = Image.open(src)
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255)); bg.paste(im, mask=im.split()[-1]); im = bg
    return im.convert("RGB")


def save(im, rel, quality=80):
    full = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    if rel.endswith(".webp"): im.save(full, "WEBP", quality=quality, method=6)
    else: im.save(full, "JPEG", quality=quality, optimize=True, progressive=True)
    return {"src": "assets/img/" + rel, "w": im.width, "h": im.height}


def fit(im, max_w):
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    return im


def photo(src, base, max_w=1600, sm=640):
    im = load(src)
    out = save(fit(im, max_w), base + ".webp")
    small = save(fit(im, sm), base + "-sm.webp", 76)
    out["sm"], out["sm_w"] = small["src"], small["w"]
    return out


def portrait(src, base):
    im = load(src)
    # crop to 4:5, keeping the top (faces) in frame
    w, h = im.size; target = 4 / 5
    if w / h > target:
        nw = round(h * target); x = (w - nw) // 2; im = im.crop((x, 0, x + nw, h))
    else:
        nh = round(w / target); y = max(0, min(h - nh, round((h - nh) * 0.2))); im = im.crop((0, y, w, y + nh))
    im = im.resize((min(900, im.width), round(min(900, im.width) * 5 / 4)), Image.LANCZOS) if im.width > 900 else im
    out = save(im, base + ".webp", 82)
    small = save(fit(im, 420), base + "-sm.webp", 78)
    out["sm"], out["sm_w"] = small["src"], small["w"]
    out["jpg"] = save(im, base + ".jpg", 82)["src"]
    return out


def logo(src, base):
    im = load(src)
    # trim white borders, then fit on a 360x160 white canvas
    bg = Image.new("RGB", im.size, (255, 255, 255))
    from PIL import ImageChops
    diff = ImageChops.difference(im, bg); box = diff.getbbox()
    if box: im = im.crop(box)
    im.thumbnail((320, 120), Image.LANCZOS)
    canvas = Image.new("RGB", (360, 160), (255, 255, 255))
    canvas.paste(im, ((360 - im.width) // 2, (160 - im.height) // 2))
    return save(canvas, base + ".webp", 88)


def main(media):
    M = {"staff": {}, "gallery": [], "events": {}, "talleres": {}, "cursos": {}, "news": {}, "services": {}, "blog": {}, "logos": {}}
    p = lambda r: os.path.join(media, r)
    N = NAMES
    for k, s in STAFF.items(): M["staff"][k] = portrait(p(s), f"staff/{N['staff'][k]}")
    for n in GALLERY: M["gallery"].append(dict(photo(p(f"2019/12/IMG_{n}.jpg"), f"galeria/{N['gallery'][n]}", 1400, 520), n=n))
    for k, s in EVENTS.items(): M["events"][k] = photo(p(s), f"eventos/{N['events'][k]}", 1200, 520)
    for k, s in TALLERES.items(): M["talleres"][k] = photo(p(s), f"talleres/{N['talleres'][k]}", 1200, 560)
    for k, s in CURSOS.items(): M["cursos"][k] = photo(p(s), f"cursos/{N['cursos'][k]}", 1200, 560)
    for k, s in NEWS.items(): M["news"][k] = photo(p(s), f"novedades/{N['news'][k]}", 1200, 560)
    for k, s in SERVICES.items(): M["services"][k] = photo(p(s), f"servicios/{N['services'][k]}", 1600, 640)
    for k, lst in BLOG.items(): M["blog"][k] = [photo(p(s), f"blog/{N['blog'][k]}" + (f"-{i + 1}" if i else ""), 1200, 560) for i, s in enumerate(lst)]
    for k, s in LOGOS.items(): M["logos"][k] = logo(p(s), f"seguros/{N['logos'][k]}")
    json.dump(M, open(os.path.join(ROOT, "build", "media.json"), "w"), indent=1)
    total = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(OUT) for f in fs)
    print(f"wrote build/media.json; assets/img is now {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Desktop/hscfdoral-media"))
