"""Build the Stage catalog: catalog.json, merchants.csv, products.csv and intentional placeholders.

Run from the repo root:  uv run --with pillow python blender/render/build_catalog.py
Writes into web/public/. Lane E owns this script; real renders later overwrite the placeholder files
under the same names (never rename them).
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PUB = ROOT / "web" / "public"
BASE = os.environ.get("STAGE_BASE", "https://hrishikesh-stage.vercel.app")
ONLY_DATA = "--data-only" in sys.argv
FORCE = "--force" in sys.argv  # overwrite existing images (default: only create missing ones)

M = [
    dict(slug="kaapi-thrift", name="Kaapi Thrift", code="KT", instagram="@kaapi.thrift",
         tagline="Pre-loved shirts, tees and overshirts from Bengaluru", category="Shirts, tees and overshirts",
         brandColor="#4A2C1D", accentColor="#F2E3C6",
         story="Kaapi Thrift began as a weekend rack outside a Malleshwaram filter-coffee counter, sold one DM at a time. "
               "Every shirt is washed, pressed and tagged 1 of 1 before it goes live."),
    dict(slug="stonewash-society", name="Stonewash Society", code="SW", instagram="@stonewash.society",
         tagline="Vintage denim and baggy cargos", category="Denim and trousers",
         brandColor="#2B3A67", accentColor="#9FB4D9",
         story="Stonewash Society hunts vintage denim and baggy cargos across Bengaluru's flea markets and mill-outlet bins. "
               "Each pair is measured, mended where it needs it and shot on a real body."),
    dict(slug="kerbside-kicks", name="Kerbside Kicks", code="KK", instagram="@kerbside.kicks",
         tagline="Pre-loved sneakers and loafers, deep-cleaned", category="Sneakers and loafers",
         brandColor="#1E1E1E", accentColor="#E8FF3A",
         story="Kerbside Kicks rescues sneakers and loafers with plenty of miles left in them. "
               "Every pair is deep-cleaned, deodorised and re-laced before it ships."),
    dict(slug="lids-and-lenses", name="Lids & Lenses", code="LL", instagram="@lidsandlenses",
         tagline="Caps, hats and vintage frames", category="Headwear and eyewear",
         brandColor="#B3261E", accentColor="#FFD9D2",
         story="Lids & Lenses started with a shoebox of vintage frames from a closing optician on Commercial Street. "
               "Today it pairs them with washed caps, beanies and bucket hats, one piece at a time."),
    dict(slug="second-hand", name="Second Hand", code="SH", instagram="@secondhand.watches",
         tagline="Vintage watches and chains", category="Watches and chains",
         brandColor="#1F3D2B", accentColor="#D4AF37",
         story="Second Hand restores vintage watches and chains that have already lived one life. "
               "Each piece is serviced, polished and sold with its story."),
]


def mat(color, pattern="solid", patternColor=None, printText=None, roughness=0.85, metalness=0.0, soleColor=None):
    m = dict(color=color, pattern=pattern, patternColor=patternColor or color, printText=printText,
             roughness=roughness, metalness=metalness)
    if soleColor:
        m["soleColor"] = soleColor
    return m


def metal(color):
    return mat(color, roughness=0.25, metalness=1.0)


# sku, merchant, name, category, mesh, price, size, condition, era, colorName, description, tags, material
P = [
    ("KT-001", "kaapi-thrift", "Crisp White Oxford Shirt", "Shirt", "top_shirt", 899, "M", "9/10", "2010s", "White", "A crisp white Oxford that has survived one boardroom and is ready for your stage.", ["white", "shirt", "oxford", "formal", "smart", "classic", "stage"], mat("#F4F3EE")),
    ("KT-002", "kaapi-thrift", "Black Poplin Shirt", "Shirt", "top_shirt", 799, "M", "9/10", "2010s", "Black", "Inky black poplin that makes every other colour in the room look louder.", ["black", "shirt", "poplin", "all-black", "evening", "smart"], mat("#121212")),
    ("KT-003", "kaapi-thrift", "Ecru Heavyweight Tee", "Tee", "top_tee", 549, "L", "8/10", "2000s", "Ecru", "Heavyweight cotton in a lived-in ecru, softer now than it was in 2004.", ["ecru", "cream", "white", "tee", "heavyweight", "basic", "casual"], mat("#EDE4D3", "melange", "#DCCFB7")),
    ("KT-004", "kaapi-thrift", "Washed Black Boxy Tee", "Tee", "top_oversized", 599, "L", "8/10", "2000s", "Washed Black", "Boxy, faded to the perfect off-black, and impossible to look try-hard in.", ["black", "tee", "boxy", "oversized", "baggy", "streetwear", "all-black"], mat("#1D1D1F", "melange", "#2A2A2E")),
    ("KT-005", "kaapi-thrift", "BLR Graphic Boxy Tee", "Tee", "top_oversized", 699, "XL", "9/10", "2010s", "Off-White", "A boxy off-white tee that says BLR before you have to.", ["white", "tee", "graphic", "print", "bangalore", "bengaluru", "boxy", "oversized"], mat("#EFE8DA", "print", "#1A1A1A", "BLR")),
    ("KT-006", "kaapi-thrift", "Beige Linen Overshirt", "Overshirt", "outer_overshirt", 1299, "L", "9/10", "2010s", "Beige", "Breezy beige linen to throw open over anything, from a tee to a stage shirt.", ["beige", "linen", "overshirt", "layer", "stage", "smart-casual", "summer"], mat("#CDBA9A", "melange", "#BFAA86")),
    ("KT-007", "kaapi-thrift", "Charcoal Thrifted Blazer", "Blazer", "outer_blazer", 1799, "40", "8/10", "1990s", "Charcoal", "A nineties charcoal blazer with shoulders that mean business.", ["charcoal", "grey", "blazer", "formal", "keynote", "smart"], mat("#3A3B3F", roughness=0.75)),
    ("KT-008", "kaapi-thrift", "Madras Check Shirt", "Shirt", "top_shirt", 849, "M", "9/10", "1990s", "Red Madras", "Red-and-navy madras straight out of a nineties Chennai summer.", ["red", "navy", "check", "madras", "shirt", "festive", "bold"], mat("#B22234", "check", "#22306B")),
    ("SW-001", "stonewash-society", "Light-Wash Baggy Jeans", "Jeans", "bottom_wide", 1199, "32", "9/10", "2000s", "Light Wash", "Light-wash, low-slung and properly baggy, the way the 2000s intended.", ["blue", "light-wash", "denim", "jeans", "baggy", "wide-leg", "relaxed", "streetwear"], mat("#9FB7CC", "denim", "#7F98B0")),
    ("SW-002", "stonewash-society", "Raw Indigo Wide-Leg Jeans", "Jeans", "bottom_wide", 1299, "32", "9/10", "2010s", "Raw Indigo", "Deep indigo wide-legs with fades only their last owner earned.", ["blue", "indigo", "denim", "jeans", "wide-leg", "dark"], mat("#253A66", "denim", "#1B2B4D")),
    ("SW-003", "stonewash-society", "Black Baggy Cargos", "Cargos", "bottom_wide", 1099, "32", "8/10", "2000s", "Black", "Six pockets, zero regrets: black cargos cut for maximum swagger.", ["black", "cargos", "baggy", "utility", "all-black", "streetwear"], mat("#151515")),
    ("SW-004", "stonewash-society", "Stone Pleated Trousers", "Trousers", "bottom_wide", 999, "32", "9/10", "1990s", "Stone", "Pleated nineties trousers in stone, drapey enough for a dance floor.", ["beige", "stone", "pleated", "trousers", "wide-leg", "smart", "festive"], mat("#CBBFA8")),
    ("SW-005", "stonewash-society", "Slim Charcoal Trousers", "Trousers", "bottom_slim", 899, "32", "8/10", "2010s", "Charcoal", "Sharp slim charcoal trousers that quietly do all the work.", ["charcoal", "grey", "slim", "trousers", "formal", "smart"], mat("#3B3D42")),
    ("SW-006", "stonewash-society", "Washed Grey Slim Jeans", "Jeans", "bottom_slim", 849, "32", "8/10", "2010s", "Washed Grey", "Slim jeans washed to a soft storm grey.", ["grey", "denim", "jeans", "slim", "casual"], mat("#8A8F98", "denim", "#6F747D")),
    ("KK-001", "kerbside-kicks", "Clean White Court Sneakers", "Sneakers", "shoe_sneaker", 2499, "UK 9", "9/10", "2020s", "White", "Deep-cleaned to near box-fresh white; nobody will ever know.", ["white", "sneakers", "court", "minimal", "classic", "stage"], mat("#F4F4F2", roughness=0.6)),
    ("KK-002", "kerbside-kicks", "Black and Gum Sneakers", "Sneakers", "shoe_sneaker", 2299, "UK 9", "8/10", "2010s", "Black / Gum", "Black uppers on a honey gum sole: the low-key flex.", ["black", "gum", "sneakers", "casual", "streetwear"], mat("#1A1A1A", roughness=0.6, soleColor="#A8743A")),
    ("KK-003", "kerbside-kicks", "Red Retro Runners", "Sneakers", "shoe_sneaker", 2799, "UK 9", "8/10", "1990s", "Red", "Nineties runners in loud red for people who walk into rooms.", ["red", "sneakers", "runners", "retro", "bold", "sporty"], mat("#C8302B", roughness=0.65)),
    ("KK-004", "kerbside-kicks", "Tan Penny Loafers", "Loafers", "shoe_loafer", 1999, "UK 9", "9/10", "2000s", "Tan", "Buttery tan penny loafers, already broken in for you.", ["tan", "brown", "loafers", "smart", "festive", "formal"], mat("#8B5A2B", roughness=0.45)),
    ("KK-005", "kerbside-kicks", "Black Leather Loafers", "Loafers", "shoe_loafer", 2199, "UK 9", "9/10", "2010s", "Black", "Polished black loafers that make any trouser look expensive.", ["black", "loafers", "leather", "formal", "all-black", "evening"], mat("#121212", roughness=0.3)),
    ("LL-001", "lids-and-lenses", "Red Six-Panel Cap", "Cap", "head_cap", 499, "Free", "9/10", "2000s", "Red", "A washed red six-panel that turns any look into a statement.", ["red", "cap", "six-panel", "baseball", "bold", "streetwear"], mat("#C62828")),
    ("LL-002", "lids-and-lenses", "Washed Black Cap", "Cap", "head_cap", 449, "Free", "8/10", "2010s", "Washed Black", "Sun-faded black cap with exactly the right amount of slouch.", ["black", "cap", "baseball", "all-black"], mat("#1F1F1F")),
    ("LL-003", "lids-and-lenses", "Cream Corduroy Cap", "Cap", "head_cap", 549, "Free", "9/10", "1990s", "Cream", "Nineties cream corduroy, soft as a Sunday.", ["cream", "white", "cap", "corduroy", "vintage"], mat("#E9DFC9", "corduroy", "#D9CDB2")),
    ("LL-004", "lids-and-lenses", "Rust Rib Beanie", "Beanie", "head_beanie", 399, "Free", "9/10", "2010s", "Rust", "A rust rib beanie for Bengaluru's three cold days a year.", ["rust", "orange", "beanie", "knit", "winter", "casual"], mat("#A6461F", "melange", "#8E3A18", roughness=0.95)),
    ("LL-005", "lids-and-lenses", "Khaki Bucket Hat", "Bucket hat", "head_bucket", 549, "Free", "8/10", "1990s", "Khaki", "A khaki bucket hat with festival energy and nineties provenance.", ["khaki", "beige", "bucket", "hat", "streetwear", "vintage"], mat("#B8A77A")),
    ("LL-006", "lids-and-lenses", "Thin Gold Hex Frames", "Frames", "eye_round", 799, "One size", "9/10", "2010s", "Gold", "Whisper-thin gold hexagons that make you look like you read the whole spec.", ["gold", "glasses", "frames", "hexagonal", "metal", "optical", "classic"], metal("#C9A55A")),
    ("LL-007", "lids-and-lenses", "Black Square Shades", "Shades", "eye_shades", 699, "One size", "8/10", "1990s", "Black", "Square black shades for spotlights and selective eye contact.", ["black", "sunglasses", "shades", "square", "bold", "all-black"], mat("#0E0E0E", roughness=0.25)),
    ("SH-001", "second-hand", "Gold Digital Watch", "Watch", "watch_digital", 1899, "One size", "9/10", "1990s", "Gold", "A nineties gold digital that tells the time and tells stories.", ["gold", "watch", "digital", "retro", "metal", "festive", "stage"], metal("#D4AF37")),
    ("SH-002", "second-hand", "Steel Field Watch", "Watch", "watch_analog", 2499, "One size", "8/10", "1980s", "Steel", "An eighties steel field watch, serviced and still ticking proudly.", ["silver", "steel", "watch", "analog", "field", "classic"], metal("#B8BCC2")),
    ("SH-003", "second-hand", "Black Digital Sports Watch", "Watch", "watch_digital", 1499, "One size", "8/10", "2000s", "Black", "A tough black digital with a stopwatch for your keynote timer.", ["black", "watch", "digital", "sports", "all-black", "casual"], mat("#151515", roughness=0.5)),
    ("SH-004", "second-hand", "Silver Rope Chain", "Chain", "neck_chain", 599, "20 in", "9/10", "2000s", "Silver", "A twisted silver rope chain that catches every spotlight.", ["silver", "chain", "rope", "metal", "streetwear"], metal("#C0C0C0")),
    ("SH-005", "second-hand", "Gold Curb Chain", "Chain", "neck_chain", 699, "20 in", "9/10", "1990s", "Gold", "A nineties gold curb chain with exactly the right weight.", ["gold", "chain", "curb", "metal", "festive"], metal("#D4AF37")),
]

DEFAULT_LOOK = ["KT-002", "KT-006", "SW-001", "KK-001", "LL-006", "SH-001"]
STAGE_READY = ["KT-001", "KT-006", "SW-001", "KK-001", "LL-001", "LL-006", "SH-001"]


SLOTS = ["top", "outerwear", "bottom", "footwear", "headwear", "eyewear", "watch", "neckwear"]


def build_catalog():
    merchants = []
    for m in M:
        merchants.append({**m, "logo": f"/merchants/{m['slug']}.png", "banner": f"/merchants/{m['slug']}-banner.jpg"})
    mslugs = {m["slug"] for m in M}
    meshes = json.loads((ROOT / "contract" / "meshes.json").read_text())["meshes"]
    products = []
    for sku, merchant, name, category, mesh, price, size, condition, era, colorName, desc, tags, material in P:
        assert merchant in mslugs, sku
        slot = meshes[mesh]["slot"]
        products.append(dict(sku=sku, merchant=merchant, name=name, category=category, slot=slot, mesh=mesh, price=price,
                             size=size, condition=condition, era=era, oneOfOne=True,
                             colorName=colorName, description=desc, tags=tags, material=material,
                             image=f"/products/{sku}.webp"))
    assert len({p["sku"] for p in products}) == len(products)
    return {"version": 2, "name": "SHOP-UNI-FY", "currency": "INR", "demoMode": True,
            "defaultLook": DEFAULT_LOOK, "looks": [{"title": "Stage Ready", "skus": STAGE_READY}],
            "merchants": merchants, "products": products}


def write_data(cat):
    (PUB / "catalog").mkdir(parents=True, exist_ok=True)
    (PUB / "catalog" / "catalog.json").write_text(json.dumps(cat, indent=2, ensure_ascii=False) + "\n")
    byslug = {m["slug"]: m for m in cat["merchants"]}
    counts = {}
    for p in cat["products"]:
        counts[p["merchant"]] = counts.get(p["merchant"], 0) + 1
    with open(PUB / "catalog" / "merchants.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["slug", "name", "code", "instagram", "tagline", "category", "story", "brand_color", "accent_color",
                    "logo_url", "banner_url", "store_url", "merchant_app_url", "piece_count"])
        for m in cat["merchants"]:
            w.writerow([m["slug"], m["name"], m["code"], m["instagram"], m["tagline"], m["category"], m["story"],
                        m["brandColor"], m["accentColor"], BASE + m["logo"], BASE + m["banner"], f"/m/{m['slug']}",
                        f"/m/{m['slug']}/app", counts.get(m["slug"], 0)])
    with open(PUB / "catalog" / "products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sku", "name", "store_slug", "store_name", "category", "slot", "price_inr", "size", "condition", "era",
                    "one_of_one", "color", "description", "tags", "image_url", "try_on_path", "viewer_url"])
        for p in cat["products"]:
            w.writerow([p["sku"], p["name"], p["merchant"], byslug[p["merchant"]]["name"], p["category"], p["slot"],
                        p["price"], p["size"], p["condition"], p["era"], "yes", p["colorName"], p["description"],
                        ";".join(p["tags"]), BASE + p["image"], f"/experience?try={p['sku']}",
                        f"{BASE}/product?sku={p['sku']}&embed=1"])


# ---------- placeholders ----------
# Pure Pillow (no numpy). Real Blender renders (render_products.py) overwrite the product cards under the
# same names; SKUs listed in blender/render/rendered.json are never overwritten by this script, even with --force.
import colorsys
import math

FONT = "/System/Library/Fonts/Avenir Next.ttc"
FONTS = ROOT / "blender" / "render" / "fonts"
TEX = PUB / "textures"
MANIFEST = ROOT / "blender" / "render" / "rendered.json"

# merchant wordmark fonts (Google Fonts, stored in blender/render/fonts) + case/tracking
MFONT = {
    "kaapi-thrift": dict(file="InstrumentSerif-Italic.ttf", case="title", track=0.0),
    "stonewash-society": dict(file="TenorSans.ttf", case="upper", track=0.10, stack=True),
    "kerbside-kicks": dict(file="Anton.ttf", case="upper", track=0.08),
    "lids-and-lenses": dict(file="ArchivoBlack.ttf", case="upper", track=0.03),
    "second-hand": dict(file="SpaceMono-Bold.ttf", case="lower", track=0.0),
}
# wordmark colour override (Kerbside's brand black would vanish on dark pages; a deep lime reads on both)
MARK_OVERRIDE = {"kerbside-kicks": "#9CB800"}
# subtle pattern for each merchant banner
BANNER_TEX = {"kaapi-thrift": "melange", "stonewash-society": "denim", "kerbside-kicks": "corduroy",
              "lids-and-lenses": "corduroy", "second-hand": "stripe"}
SLOT_LABEL = {"top": "TOP", "outerwear": "OUTERWEAR", "bottom": "BOTTOM", "footwear": "FOOTWEAR",
              "headwear": "HEADWEAR", "eyewear": "EYEWEAR", "watch": "WATCH", "neckwear": "NECKWEAR"}


def font(size, bold=True):
    """Body type: Poppins (Google Fonts, has the rupee sign). Falls back to Avenir Next."""
    try:
        return ImageFont.truetype(str(FONTS / ("Poppins-SemiBold.ttf" if bold else "Poppins-Medium.ttf")), size)
    except Exception:
        return ImageFont.truetype(FONT, size, index=(2 if bold else 0))


def gfont(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lum(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = [ch(c) for c in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def lift(rgb, lo=0.17, hi=0.40):
    """Move a colour's lightness until its luminance sits in [lo, hi]: readable on white AND near-black."""
    h, l, s = colorsys.rgb_to_hls(*[c / 255 for c in rgb])
    s = min(1.0, s * 1.12 + 0.02)
    c = rgb
    for _ in range(120):
        c = tuple(int(round(v * 255)) for v in colorsys.hls_to_rgb(h, l, s))
        L = lum(c)
        if L < lo:
            l += 0.01
        elif L > hi:
            l -= 0.01
        else:
            return c
    return c


def text_c(d, xy, s, f, fill):
    bb = d.textbbox((0, 0), s, font=f)
    d.text((xy[0] - (bb[2] - bb[0]) / 2, xy[1] - (bb[3] - bb[1]) / 2 - bb[1]), s, font=f, fill=fill)


def tracked_width(f, s, track_px):
    return sum(f.getlength(c) for c in s) + track_px * (len(s) - 1)


def draw_tracked(d, x, y, s, f, fill, track_px):
    for c in s:
        d.text((x, y), c, font=f, fill=fill)
        x += f.getlength(c) + track_px


def should_write(path: Path) -> bool:
    return FORCE or not path.exists()


def rendered_skus():
    try:
        return set(json.loads(MANIFEST.read_text()))
    except Exception:
        return set()


_tex = {}


def tex(name):
    if name not in _tex:
        _tex[name] = Image.open(TEX / f"{name}.png").convert("L")
    return _tex[name]


def tiled(name, size):
    t, w, h = tex(name), size[0], size[1]
    out = Image.new("L", size)
    for x in range(0, w, t.width):
        for y in range(0, h, t.height):
            out.paste(t, (x, y))
    return out


def rrect_mask(size, radius, scale=3):
    big = Image.new("L", (size[0] * scale, size[1] * scale), 0)
    ImageDraw.Draw(big).rounded_rectangle([0, 0, big.width - 1, big.height - 1], radius=radius * scale, fill=255)
    return big.resize(size, Image.LANCZOS)


def fabric_swatch(material, size=440, radius=44, stitch=True):
    """A fabric swatch rendered from the real pattern masks, with a soft light falloff and a stitched edge."""
    S = (size, size)
    base, pc = hex2rgb(material["color"]), hex2rgb(material["patternColor"])
    pat = material["pattern"]
    rough, metal = material.get("roughness", 0.85), material.get("metalness", 0.0)
    if pat in ("stripe", "check", "denim", "melange", "corduroy"):
        img = Image.composite(Image.new("RGB", S, pc), Image.new("RGB", S, base), tiled(pat, S))
    elif metal >= 0.5:
        img = Image.new("RGB", S, base)
        d = ImageDraw.Draw(img)
        dark, light = mix(base, (0, 0, 0), 0.45), mix(base, (255, 255, 255), 0.55)
        for x in range(size):
            t = x / size
            b = max(0, min(1, 0.25 + 0.75 * (0.5 + 0.5 * math.cos(2 * math.pi * (t * 1.35 + 0.08)))))
            d.line([(x, 0), (x, size)], fill=mix(dark, light, b))
        grain = tiled("corduroy", S).point(lambda v: v // 6)
        img = Image.composite(Image.new("RGB", S, mix(base, (255, 255, 255), 0.18)), img, grain)
    else:
        # solid cloth: whisper of heather so it never reads as a flat fill
        shade = tiled("melange", S)
        img = Image.composite(Image.new("RGB", S, mix(base, (255, 255, 255), 0.05)),
                              Image.new("RGB", S, mix(base, (0, 0, 0), 0.05)), shade)
        if pat == "print" and material.get("printText"):
            slug = "blr" if material["printText"].upper() == "BLR" else "ship-it"
            pr = Image.open(TEX / f"print-{slug}.png").convert("RGBA")
            w = int(size * 0.82)
            pr = pr.resize((w, w // 2), Image.LANCZOS)
            a = pr.split()[3].point(lambda v: int(v * 0.96))
            layer = Image.new("RGB", pr.size, pc)
            img.paste(layer, ((size - w) // 2, size // 2 - w // 4), a)
        elif rough < 0.4:
            # glossy: a soft diagonal sheen
            sheen = Image.new("L", S, 0)
            ImageDraw.Draw(sheen).polygon([(size * 0.1, 0), (size * 0.42, 0), (size * 0.12, size), (-size * 0.2, size)], fill=90)
            sheen = sheen.filter(ImageFilter.GaussianBlur(26))
            img.paste((255, 255, 255), (0, 0), sheen)
    # light falloff from the top-left (radial gradient mask: 0 centre, 255 edge)
    rad = Image.radial_gradient("L").resize((int(size * 1.9), int(size * 1.9)), Image.LANCZOS)
    fall = rad.crop((int(size * 0.20), int(size * 0.14), int(size * 0.20) + size, int(size * 0.14) + size))
    fall = fall.point(lambda v: int(v * 0.62))
    img = Image.composite(Image.new("RGB", S, mix(base, (0, 0, 0), 0.55)), img, fall)
    if stitch:
        d = ImageDraw.Draw(img, "RGBA")
        st = (255, 255, 255, 70) if lum(base) < 0.45 else (0, 0, 0, 55)
        m = 22
        for a in range(m + 14, size - m - 14, 14):
            d.line([(a, m), (a + 7, m)], fill=st, width=2)
            d.line([(a, size - m), (a + 7, size - m)], fill=st, width=2)
            d.line([(m, a), (m, a + 7)], fill=st, width=2)
            d.line([(size - m, a), (size - m, a + 7)], fill=st, width=2)
    out = img.convert("RGBA")
    out.putalpha(rrect_mask(S, radius))
    return out


def merchant_name_text(m):
    cfg = MFONT[m["slug"]]
    s = m["name"]
    return s.upper() if cfg["case"] == "upper" else s.lower() if cfg["case"] == "lower" else s


def product_placeholder(p, m):
    if p["sku"] in rendered_skus():
        return
    path = PUB / "products" / f"{p['sku']}.webp"
    if not should_write(path):
        return
    W, H = 800, 1000
    bg = hex2rgb(m["brandColor"])
    acc = hex2rgb(m["accentColor"])
    fg = (255, 255, 255) if lum(bg) < 0.30 else (20, 20, 20)
    # backdrop: soft vertical gradient + spotlight from above
    top, bot = mix(bg, (255, 255, 255), 0.10), mix(bg, (0, 0, 0), 0.50)
    grad = Image.linear_gradient("L").resize((W, H))
    img = Image.composite(Image.new("RGB", (W, H), bot), Image.new("RGB", (W, H), top), grad)
    rad = Image.radial_gradient("L").resize((W * 2, H * 2), Image.LANCZOS)
    spot = rad.crop((W // 2, H, W // 2 + W, 2 * H)).point(lambda v: max(0, int(255 - v * 1.42))).point(lambda v: int(v * 0.30))
    img.paste((255, 255, 255), (0, 0), spot)
    # swatch with a floor shadow
    size = 450
    sx, sy = (W - size) // 2, 215
    sw = fabric_swatch(p["material"], size)
    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).rounded_rectangle([sx + 8, sy + 36, sx + size - 8, sy + size + 28], radius=50, fill=170)
    shadow = shadow.filter(ImageFilter.GaussianBlur(30))
    img.paste((0, 0, 0), (0, 0), shadow)
    img.paste(sw, (sx, sy), sw)
    d = ImageDraw.Draw(img)
    # merchant mark top-left, slot tag top-right
    mf = gfont(MFONT[m["slug"]]["file"], 40)
    d.text((56, 52), merchant_name_text(m), font=mf, fill=acc)
    tag = SLOT_LABEL[p["slot"]]
    tf = font(20)
    tw = tracked_width(tf, tag, 3)
    d.rounded_rectangle([W - 56 - tw - 36, 56, W - 56, 96], radius=20, outline=fg, width=2)
    draw_tracked(d, W - 56 - tw - 18, 62, tag, tf, fg, 3)
    d.text((56, 108), f"{p['sku']}  ·  1 OF 1  ·  {p['size']}  ·  {p['condition']}  ·  {p['era']}", font=font(22, bold=False), fill=mix(fg, bg, 0.35))
    # copy
    nsz = 48
    while nsz > 30 and d.textlength(p["name"], font=font(nsz)) > 660:
        nsz -= 2
    text_c(d, (W / 2, 748), p["name"], font(nsz), fg)
    pat = p["material"]["pattern"]
    sub = p["colorName"] if pat in ("solid", "print") else f"{p['colorName']}  ·  {pat}"
    text_c(d, (W / 2, 808), sub, font(28, bold=False), mix(fg, bg, 0.25))
    d.line([(W / 2 - 36, 862), (W / 2 + 36, 862)], fill=acc, width=3)
    text_c(d, (W / 2, 920), f"₹{p['price']:,}", font(46), acc)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "WEBP", quality=88)


def mark_color(m):
    base = hex2rgb(MARK_OVERRIDE.get(m["slug"], m["brandColor"]))
    return lift(base)


INK, BONE, RED = (11, 11, 18), (243, 238, 230), (255, 61, 46)


def text_bbox(f, s, track_px):
    """Pixel bbox of tracked text drawn at (0, 0)."""
    w = int(tracked_width(f, s, track_px)) + 8
    asc, desc = f.getmetrics()
    tmp = Image.new("L", (w + 40, asc + desc + 40), 0)
    draw_tracked(ImageDraw.Draw(tmp), 20, 20, s, f, 255, track_px)
    bb = tmp.getbbox()
    return (bb[0] - 20, bb[1] - 20, bb[2] - 20, bb[3] - 20)


def merchant_wordmark(m, path):
    """A bone woven-label wordmark: reads on white, on ink and on the merchant's own brand colour."""
    S = 2  # supersample
    cfg = MFONT[m["slug"]]
    s = merchant_name_text(m)
    size = 150 * S
    f = gfont(cfg["file"], size)
    track = cfg["track"] * size
    lines = s.split(" ", 1) if (cfg.get("stack") and " " in s) else [s]
    bbs = [text_bbox(f, ln, track) for ln in lines]
    lh = max(b[3] - b[1] for b in bbs)
    gap_l = int(lh * 0.42)
    tw = max(b[2] - b[0] for b in bbs)
    th = lh * len(lines) + gap_l * (len(lines) - 1)
    padx, pady = 78 * S, 52 * S
    w, h = tw + 2 * padx, th + 2 * pady
    brand = hex2rgb(m["brandColor"])
    lab = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lab)
    rad = 30 * S
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=rad, fill=BONE + (255,))
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=rad, outline=brand + (110,), width=3 * S)
    # stitched border
    inset = 15 * S
    sd = ImageDraw.Draw(lab, "RGBA")
    dash, gap = 12 * S, 9 * S
    x = inset + rad
    while x < w - inset - rad:
        sd.line([(x, inset), (min(x + dash, w - inset - rad), inset)], fill=brand + (95,), width=2 * S)
        sd.line([(x, h - inset), (min(x + dash, w - inset - rad), h - inset)], fill=brand + (95,), width=2 * S)
        x += dash + gap
    y = inset + rad
    while y < h - inset - rad:
        sd.line([(inset, y), (inset, min(y + dash, h - inset - rad))], fill=brand + (95,), width=2 * S)
        sd.line([(w - inset, y), (w - inset, min(y + dash, h - inset - rad))], fill=brand + (95,), width=2 * S)
        y += dash + gap
    ty = pady
    for ln, bb in zip(lines, bbs):
        lw = bb[2] - bb[0]
        draw_tracked(ImageDraw.Draw(lab), (w - lw) // 2 - bb[0], ty - bb[1] + (lh - (bb[3] - bb[1])) // 2, ln, f, brand + (255,), track)
        ty += lh + gap_l
    lab = lab.resize((w // S, h // S), Image.LANCZOS)
    pad = 6
    out = Image.new("RGBA", (lab.width + 2 * pad, lab.height + 2 * pad), (0, 0, 0, 0))
    out.paste(lab, (pad, pad), lab)
    out.save(path)


def wrap_text(d, s, f, max_w, max_lines=2):
    words, lines, cur = s.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=f) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    lines.append(cur)
    return lines[:max_lines]


def thrift_tag(p, m, S=2):
    """A hanging price tag for one piece: swatch, name, size and condition, price, 1 OF 1 stamp.
    Returns (RGBA image at 1x, hole centre in image coords)."""
    W, H = 250, 372
    t = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(t)
    brand = hex2rgb(m["brandColor"])
    ch = 46 * S
    poly = [(ch, 0), (W * S - ch, 0), (W * S, ch), (W * S, H * S), (0, H * S), (0, ch)]
    d.polygon(poly, fill=BONE + (255,))
    # round off by redrawing outline softly
    d.line(poly + [poly[0]], fill=brand + (70,), width=2 * S, joint="curve")
    hole = (W // 2 * S, 44 * S)
    r = 12 * S
    d.ellipse([hole[0] - r - 5 * S, hole[1] - r - 5 * S, hole[0] + r + 5 * S, hole[1] + r + 5 * S], fill=(222, 214, 200, 255))
    d.ellipse([hole[0] - r, hole[1] - r, hole[0] + r, hole[1] + r], fill=(0, 0, 0, 0))
    # swatch
    sw = fabric_swatch(p["material"], 220 * S, radius=110 * S, stitch=False).resize((112 * S, 112 * S), Image.LANCZOS)
    ring = Image.new("RGBA", (120 * S, 120 * S), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse([0, 0, 120 * S - 1, 120 * S - 1], fill=brand + (255,))
    t.paste(ring, ((W - 120) // 2 * S, 92 * S), ring)
    t.paste(sw, ((W - 112) // 2 * S, 96 * S), sw)
    d = ImageDraw.Draw(t)
    # name (Instrument Serif italic, up to 2 lines, centred)
    nf = gfont("InstrumentSerif-Italic.ttf", 33 * S)
    lines = wrap_text(d, p["name"], nf, (W - 40) * S)
    y = 224 * S
    for ln in lines:
        d.text((W * S / 2 - d.textlength(ln, font=nf) / 2, y), ln, font=nf, fill=INK + (255,))
        y += 34 * S
    # meta
    mf = gfont("SpaceMono-Bold.ttf", 16 * S)
    sz = str(p.get("size", "-")).upper()
    meta = f"{'SIZE ' + sz if len(sz) <= 4 else sz}  ·  {p.get('condition', '')}"
    d.text((W * S / 2 - d.textlength(meta, font=mf) / 2, 300 * S), meta, font=mf, fill=brand + (255,))
    d.line([(24 * S, 330 * S), ((W - 24) * S, 330 * S)], fill=brand + (60,), width=2 * S)
    # price + stamp
    pf = font(26 * S)
    d.text((24 * S, 338 * S), f"₹{p['price']:,}", font=pf, fill=INK + (255,))
    sf = gfont("SpaceMono-Bold.ttf", 14 * S)
    stamp = "1 OF 1"
    sw_, sh_ = d.textlength(stamp, font=sf) + 18 * S, 26 * S
    sx, sy = (W - 24) * S - sw_, 342 * S
    d.rounded_rectangle([sx, sy, sx + sw_, sy + sh_], radius=5 * S, outline=RED + (255,), width=2 * S)
    d.text((sx + 9 * S, sy + 4 * S), stamp, font=sf, fill=RED + (255,))
    t = t.resize((W, H), Image.LANCZOS)
    return t, (hole[0] / S, hole[1] / S)


def merchant_banner(m, products, path):
    W, H = 1600, 600
    bg = hex2rgb(m["brandColor"])
    acc = hex2rgb(m["accentColor"])
    fg = BONE
    # base: lighter brand tone on the left, deep on the right
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((W, H))
    img = Image.composite(Image.new("RGB", (W, H), mix(bg, INK, 0.62)), Image.new("RGB", (W, H), mix(bg, (255, 255, 255), 0.06)), grad)
    # fabric texture, very quiet
    t = tiled(BANNER_TEX[m["slug"]], (W, H))
    img = Image.blend(img, Image.composite(Image.new("RGB", (W, H), mix(bg, (255, 255, 255), 0.30)), img, t), 0.18)
    # spotlight on the tag cluster
    rad = Image.radial_gradient("L").resize((1300, 1000), Image.LANCZOS).point(lambda v: max(0, int(255 - v * 1.42))).point(lambda v: int(v * 0.30))
    img.paste((255, 255, 255), (650, -250), rad)
    # left column: handle, name, tagline, count
    d = ImageDraw.Draw(img)
    hf = gfont("SpaceMono-Bold.ttf", 26)
    handle = m.get("instagram", "")
    hw = d.textlength(handle, font=hf)
    d.rounded_rectangle([100, 96, 100 + hw + 36, 96 + 46], radius=23, outline=acc, width=2)
    d.text((118, 105), handle, font=hf, fill=acc)
    cfg = MFONT[m["slug"]]
    name = merchant_name_text(m)
    size = 168
    while size > 50:
        f = gfont(cfg["file"], size)
        if tracked_width(f, name, cfg["track"] * size) <= 720:
            break
        size -= 4
    bb = text_bbox(f, name, cfg["track"] * size)
    ny = 178
    draw_tracked(d, 100 - bb[0], ny - bb[1], name, f, fg, cfg["track"] * size)
    ybar = ny + (bb[3] - bb[1]) + 34
    d.rounded_rectangle([100, ybar, 100 + 90, ybar + 6], radius=3, fill=acc)
    tf = font(31, bold=False)
    ty = ybar + 30
    for ln in wrap_text(d, m["tagline"], tf, 690, 2):
        d.text((100, ty), ln, font=tf, fill=mix(fg, bg, 0.1))
        ty += 44
    n = len(products)
    cf = gfont("SpaceMono-Bold.ttf", 22)
    d.text((100, 520), f"{n} PIECES  ·  EVERY ONE 1 OF 1", font=cf, fill=acc)
    # hanging tags: first, middle, last piece
    picks = [products[0], products[len(products) // 2], products[-1]] if n >= 3 else list(products)
    seen, uniq = set(), []
    for p in picks:
        if p["sku"] not in seen:
            seen.add(p["sku"])
            uniq.append(p)
    cx0, step = (985, 240) if len(uniq) == 3 else (1100, 280)
    angles = [6, -4, 6]
    drops = [30, -6, 52]
    sh_layer = Image.new("L", (W, H), 0)
    placed = []
    for i, p in enumerate(uniq):
        tag, hole = thrift_tag(p, m)
        TS = 0.82
        tag = tag.resize((int(tag.width * TS), int(tag.height * TS)), Image.LANCZOS)
        hole = (hole[0] * TS, hole[1] * TS)
        ang = angles[i % 3]
        rt = tag.rotate(ang, resample=Image.BICUBIC, expand=True)
        # rotate hole point about the tag centre
        cxm, cym = tag.width / 2, tag.height / 2
        a = math.radians(-ang)
        hx, hy = hole[0] - cxm, hole[1] - cym
        rx = hx * math.cos(a) - hy * math.sin(a) + rt.width / 2
        ry = hx * math.sin(a) + hy * math.cos(a) + rt.height / 2
        hole_target = (cx0 + i * step, 120 + drops[i % 3] + 30)
        pos = (int(hole_target[0] - rx), int(hole_target[1] - ry))
        placed.append((rt, pos, hole_target))
        alpha = rt.split()[3]
        sh_layer.paste(alpha.point(lambda v: int(v * 0.55)), (pos[0] + 10, pos[1] + 18), alpha)
    sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(14))
    img.paste((0, 0, 0), (0, 0), sh_layer)
    d = ImageDraw.Draw(img)
    for rt, pos, ht in placed:
        # string from the top edge to the hole, with a slight sag
        sx = ht[0] + (ht[0] - 1200) * 0.04
        d.line([(sx, -10), (ht[0], ht[1])], fill=(226, 218, 204), width=3)
        d.line([(sx + 2, -10), (ht[0] + 2, ht[1])], fill=(150, 142, 128), width=1)
    for rt, pos, ht in placed:
        img.paste(rt, pos, rt)
    img.save(path, "JPEG", quality=90)


def merchant_assets(m, products):
    logo = PUB / "merchants" / f"{m['slug']}.png"
    logo.parent.mkdir(parents=True, exist_ok=True)
    if should_write(logo):
        merchant_wordmark(m, logo)
    banner = PUB / "merchants" / f"{m['slug']}-banner.jpg"
    if should_write(banner):
        merchant_banner(m, products, banner)


def brand_logo(path):
    """SHOP-UNI-FY wordmark in Anton: bone letters, signal-red hyphens, transparent."""
    f = gfont("Anton.ttf", 200)
    s, track = "SHOP-UNI-FY", 200 * 0.02
    bone, red = (243, 238, 230, 255), (255, 61, 46, 255)
    w = int(tracked_width(f, s, track)) + 120
    asc, desc = f.getmetrics()
    img = Image.new("RGBA", (w, asc + desc + 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 60
    for ch in s:
        d.text((x, 40), ch, font=f, fill=red if ch == "-" else bone)
        x += d.textlength(ch, font=f) + track
    bb = img.getbbox()
    img = img.crop((bb[0] - 24, bb[1] - 24, bb[2] + 24, bb[3] + 24))
    img.save(path)


def brand_assets():
    b = PUB / "brand"
    b.mkdir(parents=True, exist_ok=True)
    if should_write(b / "logo.png"):
        brand_logo(b / "logo.png")
    # hero.jpg (Lane C) and persona.png (Lane A) belong to other lanes: placeholders only if missing, never forced.
    ink, gold, plum = (14, 14, 20), (242, 193, 78), (91, 52, 140)
    if not (b / "hero.jpg").exists():
        W, H = 1920, 1080
        img = Image.new("RGB", (W, H), ink)
        d = ImageDraw.Draw(img)
        for y in range(H):
            d.line([(0, y), (W, y)], fill=mix(plum, ink, min(1, y / (H * 0.8))))
        d.text((120, 120), "HRISHIKESH", font=font(96), fill=(255, 255, 255))
        d.text((124, 240), "On stage at Bluehost, Bangalore", font=font(44, bold=False), fill=gold)
        img.save(b / "hero.jpg", "JPEG", quality=88)
    if not (b / "persona.png").exists():
        W, H = 1200, 1500
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([450, 180, 750, 480], fill=(150, 110, 85, 255))
        d.rounded_rectangle([340, 520, 860, 1100], radius=120, fill=(58, 59, 63, 255))
        d.rounded_rectangle([370, 1080, 830, 1500], radius=60, fill=(58, 58, 62, 255))
        img.save(b / "persona.png")


def main():
    cat = build_catalog()
    write_data(cat)
    if not ONLY_DATA:
        byslug = {m["slug"]: m for m in cat["merchants"]}
        bymerchant = {}
        for p in cat["products"]:
            bymerchant.setdefault(p["merchant"], []).append(p)
            product_placeholder(p, byslug[p["merchant"]])
        for m in cat["merchants"]:
            merchant_assets(m, bymerchant[m["slug"]])
        brand_assets()
        for m in cat["merchants"]:
            mc = mark_color(m)
            print(f"  {m['slug']}: wordmark contrast {contrast(mc, (255, 255, 255)):.1f} on white, {contrast(mc, (14, 14, 20)):.1f} on dark")
    print(f"catalog: {len(cat['merchants'])} merchants, {len(cat['products'])} products -> {PUB}")


if __name__ == "__main__":
    main()
