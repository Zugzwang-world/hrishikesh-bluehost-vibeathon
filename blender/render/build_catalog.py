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
    "kaapi-thrift": dict(file="BowlbyOne.ttf", case="title", track=0.0),
    "stonewash-society": dict(file="TenorSans.ttf", case="upper", track=0.12),
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


def merchant_wordmark(m, path):
    cfg = MFONT[m["slug"]]
    s = merchant_name_text(m)
    size = 150
    f = gfont(cfg["file"], size)
    track = cfg["track"] * size
    w = int(tracked_width(f, s, track)) + 60
    asc, desc = f.getmetrics()
    h = asc + desc + 50
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    draw_tracked(d, 30, 25, s, f, mark_color(m) + (255,), track)
    bb = img.getbbox()
    img = img.crop((max(0, bb[0] - 20), max(0, bb[1] - 20), min(w, bb[2] + 20), min(h, bb[3] + 20)))
    img.save(path)


def merchant_banner(m, products, path):
    W, H = 1600, 600
    bg = hex2rgb(m["brandColor"])
    acc = hex2rgb(m["accentColor"])
    fg = (255, 255, 255) if lum(bg) < 0.30 else (20, 20, 20)
    # base: horizontal gradient from a lighter brand tone (left) to a deep one (right)
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((W, H))  # black on the left -> white on the right
    img = Image.composite(Image.new("RGB", (W, H), mix(bg, (0, 0, 0), 0.55)), Image.new("RGB", (W, H), mix(bg, (255, 255, 255), 0.08)), grad)
    # fabric texture, very quiet
    t = tiled(BANNER_TEX[m["slug"]], (W, H))
    img = Image.blend(img, Image.composite(Image.new("RGB", (W, H), mix(bg, (255, 255, 255), 0.28)), img, t), 0.20)
    # soft spotlight behind the swatches
    rad = Image.radial_gradient("L").resize((1200, 900), Image.LANCZOS).point(lambda v: max(0, int(255 - v * 1.42))).point(lambda v: int(v * 0.26))
    img.paste((255, 255, 255), (700, -150), rad)
    d = ImageDraw.Draw(img)
    # name, shrunk to fit
    cfg = MFONT[m["slug"]]
    name = merchant_name_text(m)
    size = 150
    while size > 50:
        f = gfont(cfg["file"], size)
        if tracked_width(f, name, cfg["track"] * size) <= 720:
            break
        size -= 4
    asc, desc = f.getmetrics()
    draw_tracked(d, 100, 150, name, f, fg, cfg["track"] * size)
    d.line([(104, 150 + asc + desc + 34), (184, 150 + asc + desc + 34)], fill=acc, width=5)
    d.text((100, 150 + asc + desc + 58), m["tagline"], font=font(36, bold=False), fill=mix(fg, bg, 0.12))
    n = len(products)
    d.text((100, 535), f"{n} PIECES  ·  TRY THEM ON THE STAGE", font=font(22), fill=acc)
    # row of overlapping product swatches (real colours and patterns)
    dia = 150 if n <= 6 else 130
    x0, x1 = 880, 1500
    step = min(dia * 0.78, (x1 - x0 - dia) / max(1, n - 1))
    cy = 300
    shadow = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shadow)
    items = []
    for i, p in enumerate(products):
        cx = x0 + dia / 2 + i * step
        items.append((cx, p))
        sd.ellipse([cx - dia / 2 + 4, cy - dia / 2 + 14, cx + dia / 2 - 4, cy + dia / 2 + 14], fill=150)
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    img.paste((0, 0, 0), (0, 0), shadow)
    for cx, p in items:
        sw = fabric_swatch(p["material"], 300, radius=150, stitch=False).resize((dia, dia), Image.LANCZOS)
        ring = Image.new("RGBA", (dia + 8, dia + 8), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([0, 0, dia + 7, dia + 7], fill=(255, 255, 255, 235))
        img.paste(ring, (int(cx - dia / 2 - 4), int(cy - dia / 2 - 4)), ring)
        img.paste(sw, (int(cx - dia / 2), int(cy - dia / 2)), sw)
    img.save(path, "JPEG", quality=88)


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
