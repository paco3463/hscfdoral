"""Add the November 2026 photos to build/media.json without re-importing everything.

    python3 build/tools/add_media_2026_11.py ~/Downloads/FOTOS

Uses the same resizing as import_old_media.py (portraits 4:5, photos WebP + small WebP).
New staff headshots, the "Workshops:Classes" photos (gallery + home + the anxiety workshop),
and a branded initials placeholder for anyone whose headshot hasn't arrived yet.
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from import_old_media import ROOT, OUT, portrait, photo, save  # noqa: E402

STAFF = {  # staff id -> (source file in the FOTOS folder, new file base name)
    "alibel-osorio": ("Alibel picture 2.jpg", "alibel-osorio-terapeuta-hipnoterapeuta-hscf-doral"),
    "beatriz-pedreira": ("Beatriz Pedreira picture.png", "beatriz-pedreira-trabajadora-social-rcswi-hscf-doral"),
    "jesica-viegas": ("Jesica Viegas picture.PNG", "jesica-viegas-terapeuta-de-yoga-breathwork-hscf-doral"),
    "iris-aguila": ("Iris Aguila picture.jpg", "iris-aguila-hscf-doral"),
}
PLACEHOLDERS = {  # staff id -> (initials, file base) until a real headshot arrives
    "andrea-echeverria": ("AE", "andrea-echeverria-coach-hipnosis-clinica-hscf-doral"),
}
WORKSHOPS = [  # gallery number, source file, file base (in display order)
    ("t17", "PHOTO-2026-10-27-16-50-49.jpg", "charla-hscf-facilitadoras-con-el-grupo"),
    ("t18", "workshop picture 1.jpg", "taller-ansiedad-florida-blue-hialeah-publico"),
    ("t08", "PHOTO-2026-10-27-14-57-29.jpg", "taller-ansiedad-florida-blue-hialeah-sala"),
    ("t06", "PHOTO-2026-10-27-14-56-30.jpg", "taller-ansiedad-florida-blue-hialeah-escenario"),
    ("t07", "PHOTO-2026-10-27-14-57-29 2.jpg", "taller-ansiedad-florida-blue-hialeah-ponente"),
    ("t16", "PHOTO-2026-10-27-16-50-49 3.jpg", "charla-hscf-grupo-en-la-sala"),
    ("t15", "PHOTO-2026-10-27-16-50-49 2.jpg", "charla-hscf-presentacion"),
    ("t05", "PHOTO-2026-10-27-14-55-11.jpg", "taller-hscf-grupo-pequeno"),
    ("t11", "PHOTO-2026-10-27-15-38-54 4.jpg", "clase-yoga-respiracion-grupo"),
    ("t13", "PHOTO-2026-10-27-15-38-54.jpg", "clase-hscf-facilitadora"),
    ("t10", "PHOTO-2026-10-27-15-38-54 3.jpg", "clase-hscf-facilitadora-y-participante"),
    ("t14", "PHOTO-2026-10-27-15-38-55.jpg", "clase-hscf-participantes"),
    ("t12", "PHOTO-2026-10-27-15-38-54 5.jpg", "clase-yoga-esteras"),
    ("t09", "PHOTO-2026-10-27-15-38-54 2.jpg", "clase-yoga-relajacion"),
    ("t04", "PHOTO-2026-10-27-14-53-57.jpg", "clase-respiracion-consciente"),
    ("t01", "PHOTO-2026-10-27-14-53-57 2.jpg", "clase-yoga-instructora"),
    ("t02", "PHOTO-2026-10-27-14-53-57 3.jpg", "clase-yoga-meditacion"),
    ("t03", "PHOTO-2026-10-27-14-53-57 4.jpg", "sesion-reiki-relajacion"),
]
TALLER_ANSIEDAD = "PHOTO-2026-10-27-14-57-29.jpg"  # the BCBS / Florida Blue workshop in Hialeah


def initials(text, base):
    """A 4:5 portrait card in the brand colors with the person's initials."""
    w, h = 720, 900
    im = Image.new("RGB", (w, h), (253, 201, 166))  # --apricot-soft
    d = ImageDraw.Draw(im)
    for r, c in ((520, (250, 141, 74)), (380, (255, 237, 226))):  # soft rings: --apricot, --blush
        d.ellipse((w / 2 - r / 2, h * .46 - r / 2, w / 2 + r / 2, h * .46 + r / 2), fill=c)
    font = None
    for f in ("/System/Library/Fonts/Supplemental/Georgia Bold.ttf", "/Library/Fonts/Georgia Bold.ttf"):
        if os.path.exists(f): font = ImageFont.truetype(f, 190); break
    font = font or ImageFont.load_default()
    tw = d.textlength(text, font=font)
    d.text(((w - tw) / 2, h * .46 - 120), text, font=font, fill=(58, 34, 25))  # --cocoa
    out = save(im, f"staff/{base}.webp", 82)
    small = save(im.resize((420, 525), Image.LANCZOS), f"staff/{base}-sm.webp", 78)
    out["sm"], out["sm_w"] = small["src"], small["w"]
    out["jpg"] = save(im, f"staff/{base}.jpg", 82)["src"]
    out["placeholder"] = True
    return out


def main(src):
    path = os.path.join(ROOT, "build", "media.json")
    M = json.load(open(path))
    for k, (f, base) in STAFF.items():
        M["staff"][k] = portrait(os.path.join(src, f), f"staff/{base}")
    for k, (txt, base) in PLACEHOLDERS.items():
        if not M["staff"].get(k) or M["staff"][k].get("placeholder"):
            M["staff"][k] = initials(txt, base)
    ws = os.path.join(src, "Workshops:Classes")
    new = [dict(photo(os.path.join(ws, f), f"galeria/{base}", 1400, 520), n=n) for n, f, base in WORKSHOPS]
    keep = [g for g in M["gallery"] if not str(g.get("n", "")).startswith("t")]
    M["gallery"] = new + keep
    M["talleres"]["hablemos-sobre-ansiedad"] = photo(os.path.join(ws, TALLER_ANSIEDAD), "talleres/taller-hablemos-sobre-ansiedad-florida-blue-hialeah", 1200, 560)
    json.dump(M, open(path, "w"), indent=1)
    print(f"staff: {', '.join(list(STAFF) + list(PLACEHOLDERS))}; gallery: {len(new)} new + {len(keep)} earlier")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Downloads/FOTOS"))
