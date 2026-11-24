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
    dict(slug="kaapi-club", name="Kaapi Club", code="KC", tagline="Bengaluru café streetwear",
         category="Tees and shirts", brandColor="#4A2C1D", accentColor="#E9C46A",
         story="Kaapi Club started as a tee drop for the regulars of a Malleshwaram filter-coffee counter. "
               "Every piece is cut for long Bengaluru days that start with decoction and end on a rooftop."),
    dict(slug="rao-and-sons", name="Rao & Sons", code="RS", tagline="Third-generation tailors",
         category="Blazers and overshirts", brandColor="#1F2A44", accentColor="#C9A227",
         story="Three generations of the Rao family have cut cloth on the same Chickpet street since 1962. "
               "Their blazers keep the old-school canvas structure but drop the stiffness for modern stages."),
    dict(slug="indigo-loom", name="Indigo Loom", code="IL", tagline="Denim and trousers, wide-leg to slim",
         category="Denim and trousers", brandColor="#22346B", accentColor="#E8E1D3",
         story="Indigo Loom works with small mills to weave denim and trouser cloth that softens with every wear. "
               "From roomy wide-legs to sharp slims, every pair is hemmed to Indian heights."),
    dict(slug="kerb", name="Kerb", code="KB", tagline="Sneakers and loafers for city miles",
         category="Footwear", brandColor="#111111", accentColor="#E63946",
         story="Kerb makes clean sneakers and soft loafers built to survive Bengaluru pavements. "
               "Cushioned soles, honest leather and nothing you have to break in."),
    dict(slug="cap-theory", name="Cap Theory", code="CT", tagline="Caps, beanies and bucket hats",
         category="Headwear", brandColor="#B3122B", accentColor="#F4EDE4",
         story="Cap Theory believes the right hat finishes a look and starts a conversation. "
               "Small-batch caps, beanies and bucket hats, stitched in Tiruppur."),
    dict(slug="second-hand", name="Second Hand", code="SH", tagline="Watches with a story",
         category="Watches", brandColor="#2F3E36", accentColor="#D9C8A0",
         story="Second Hand designs everyday watches inspired by the dials our grandparents wore. "
               "Analog and retro digital pieces that keep time and good taste."),
    dict(slug="lens-lane", name="Lens Lane", code="LL", tagline="Eyewear and chains",
         category="Eyewear and accessories", brandColor="#4B3F72", accentColor="#F2B880",
         story="Lens Lane designs frames and chains that sit somewhere between studio and street. "
               "Lightweight acetate, honest metal and shapes that suit Indian faces."),
]


def mat(color, pattern="solid", patternColor=None, printText=None, roughness=0.85, metalness=0.0):
    return dict(color=color, pattern=pattern, patternColor=patternColor or color, printText=printText,
                roughness=roughness, metalness=metalness)


# sku, merchant, name, slot, mesh, price, colorName, description, tags, material
P = [
    # Kaapi Club: tees and shirts
    ("KC-001", "kaapi-club", "Everyday Tee", "top", "top_tee", 799, "White", "Heavyweight cotton crew tee with a clean, structured neckline.", ["white", "basic", "classic", "minimal", "stage"], mat("#F4F2EE")),
    ("KC-002", "kaapi-club", "Everyday Tee", "top", "top_tee", 799, "Black", "Heavyweight cotton crew tee in deep black.", ["black", "basic", "all-black", "minimal"], mat("#1B1B1D")),
    ("KC-003", "kaapi-club", "Decoction Oversized Tee", "top", "top_oversized", 1199, "Coffee Brown", "Dropped-shoulder oversized tee in a rich coffee tone.", ["brown", "oversized", "baggy", "streetwear", "casual"], mat("#5B3A29")),
    ("KC-004", "kaapi-club", "Ship It Oversized Tee", "top", "top_oversized", 1299, "Off-White", "Oversized tee with a bold SHIP IT chest print for builders.", ["white", "print", "graphic", "oversized", "tech", "startup"], mat("#EFEAE0", "print", "#C0392B", "SHIP IT")),
    ("KC-005", "kaapi-club", "BLR Graphic Tee", "top", "top_tee", 999, "Black", "Black tee with a golden BLR city print.", ["black", "print", "graphic", "bangalore", "bengaluru", "city"], mat("#161616", "print", "#F2C14E", "BLR")),
    ("KC-006", "kaapi-club", "Oxford Shirt", "top", "top_shirt", 1899, "White", "Crisp white cotton Oxford with a button-down collar.", ["white", "shirt", "formal", "smart", "classic", "stage"], mat("#FAFAF7")),
    ("KC-007", "kaapi-club", "Linen Shirt", "top", "top_shirt", 2199, "Sky Blue", "Breathable linen shirt in a soft sky blue.", ["blue", "shirt", "linen", "summer", "smart-casual"], mat("#A9C7E3")),
    ("KC-008", "kaapi-club", "Breton Stripe Tee", "top", "top_tee", 1099, "Navy Stripe", "Off-white tee with fine navy Breton stripes.", ["stripe", "navy", "white", "casual", "classic"], mat("#F3F1EA", "stripe", "#1F2A44")),
    ("KC-009", "kaapi-club", "Melange Tee", "top", "top_tee", 899, "Grey Melange", "Soft heather-grey everyday tee.", ["grey", "melange", "basic", "casual"], mat("#9A9A9C", "melange", "#C9C9CB")),
    ("KC-010", "kaapi-club", "Festive Mandarin Shirt", "top", "top_shirt", 2499, "Marigold", "Mandarin-collar shirt in a glowing marigold for festive evenings.", ["yellow", "marigold", "festive", "ethnic", "diwali", "celebration", "bangalore"], mat("#D98E04", roughness=0.55)),
    # Rao & Sons: blazers and overshirts
    ("RS-001", "rao-and-sons", "Stage Blazer", "outerwear", "outer_blazer", 6999, "Charcoal", "Soft-structured single-breasted blazer that reads sharp under stage lights.", ["charcoal", "grey", "blazer", "formal", "stage", "keynote", "smart"], mat("#3A3B3F", roughness=0.75)),
    ("RS-002", "rao-and-sons", "Midnight Blazer", "outerwear", "outer_blazer", 7499, "Black", "Black wool-blend blazer with satin-finish buttons.", ["black", "blazer", "all-black", "formal", "evening"], mat("#141416", roughness=0.7)),
    ("RS-003", "rao-and-sons", "Bandhgala-Cut Blazer", "outerwear", "outer_blazer", 8999, "Royal Maroon", "Maroon blazer with a bandhgala-inspired cut for festive nights.", ["maroon", "red", "festive", "ethnic", "wedding", "blazer", "bangalore"], mat("#6E1423", roughness=0.6)),
    ("RS-004", "rao-and-sons", "Check Overshirt", "outerwear", "outer_overshirt", 3499, "Olive Check", "Brushed cotton overshirt in an olive check.", ["olive", "green", "check", "overshirt", "casual", "layer"], mat("#5B6B3A", "check", "#2E3520")),
    ("RS-005", "rao-and-sons", "Corduroy Overshirt", "outerwear", "outer_overshirt", 3999, "Rust", "Mid-wale corduroy overshirt in warm rust.", ["rust", "orange", "brown", "corduroy", "overshirt", "casual"], mat("#A0522D", "corduroy", "#7E3F22")),
    # Indigo Loom: denim and trousers
    ("IL-001", "indigo-loom", "Baggy Wide-Leg Trousers", "bottom", "bottom_wide", 2799, "Stone", "Relaxed, baggy wide-leg trousers in a stone twill.", ["beige", "stone", "baggy", "wide-leg", "relaxed", "streetwear"], mat("#C8BBA3")),
    ("IL-002", "indigo-loom", "Wide-Leg Denim", "bottom", "bottom_wide", 3299, "Mid Indigo", "Wide-leg jeans in a mid-wash indigo denim.", ["blue", "denim", "jeans", "wide-leg", "baggy", "casual"], mat("#2C3E66", "denim", "#4A5F8C")),
    ("IL-003", "indigo-loom", "Slim Selvedge Denim", "bottom", "bottom_slim", 3499, "Raw Indigo", "Slim-fit raw selvedge jeans that fade with you.", ["blue", "denim", "jeans", "slim", "classic"], mat("#1E2A47", "denim", "#33456E")),
    ("IL-004", "indigo-loom", "Slim Chinos", "bottom", "bottom_slim", 2299, "Black", "Slim stretch chinos in jet black.", ["black", "chinos", "slim", "all-black", "smart"], mat("#18181A")),
    ("IL-005", "indigo-loom", "Pleated Wide Trousers", "bottom", "bottom_wide", 3199, "Charcoal", "Single-pleat wide trousers with a sharp drape.", ["charcoal", "grey", "wide-leg", "formal", "stage", "smart"], mat("#3A3A3E", roughness=0.8)),
    ("IL-006", "indigo-loom", "Slim Chinos", "bottom", "bottom_slim", 2199, "Khaki", "Slim stretch chinos in classic khaki.", ["khaki", "beige", "chinos", "slim", "smart-casual"], mat("#B59F78")),
    ("IL-007", "indigo-loom", "Corduroy Wide Trousers", "bottom", "bottom_wide", 2999, "Cream", "Wide corduroy trousers in a festive cream.", ["cream", "white", "corduroy", "wide-leg", "festive"], mat("#E8DCC4", "corduroy", "#CFC1A5")),
    # Kerb: footwear
    ("KB-001", "kerb", "Court Sneaker", "footwear", "shoe_sneaker", 3999, "White", "Clean leather court sneaker in all white.", ["white", "sneakers", "minimal", "classic", "stage"], mat("#F5F5F2", roughness=0.6)),
    ("KB-002", "kerb", "Court Sneaker", "footwear", "shoe_sneaker", 3999, "Black", "Leather court sneaker in tonal black.", ["black", "sneakers", "all-black", "minimal"], mat("#1A1A1A", roughness=0.6)),
    ("KB-003", "kerb", "City Runner", "footwear", "shoe_sneaker", 4499, "Signal Red", "Lightweight runner in a loud signal red.", ["red", "sneakers", "sporty", "bold"], mat("#C62828", roughness=0.65)),
    ("KB-004", "kerb", "Penny Loafer", "footwear", "shoe_loafer", 4999, "Tan", "Soft tan leather penny loafer.", ["tan", "brown", "loafers", "smart", "festive", "formal"], mat("#8B5A2B", roughness=0.45)),
    ("KB-005", "kerb", "Penny Loafer", "footwear", "shoe_loafer", 4999, "Black", "Polished black leather penny loafer.", ["black", "loafers", "formal", "all-black", "evening"], mat("#121212", roughness=0.3)),
    # Cap Theory: headwear
    ("CT-001", "cap-theory", "Six-Panel Cap", "headwear", "head_cap", 899, "Red", "Structured six-panel cap in a bright red twill.", ["red", "cap", "baseball", "bold", "streetwear"], mat("#C8102E")),
    ("CT-002", "cap-theory", "Six-Panel Cap", "headwear", "head_cap", 899, "Black", "Structured six-panel cap in black twill.", ["black", "cap", "baseball", "all-black"], mat("#151515")),
    ("CT-003", "cap-theory", "BLR Logo Cap", "headwear", "head_cap", 999, "Cream", "Cream cap with an embroidered navy BLR.", ["cream", "white", "cap", "print", "bangalore", "bengaluru"], mat("#EDE6D6", "print", "#1F3A5F", "BLR")),
    ("CT-004", "cap-theory", "Rib Beanie", "headwear", "head_beanie", 749, "Charcoal", "Chunky rib-knit beanie in charcoal.", ["charcoal", "grey", "beanie", "winter", "casual"], mat("#3C3C3C", roughness=0.95)),
    ("CT-005", "cap-theory", "Rib Beanie", "headwear", "head_beanie", 749, "Mustard", "Chunky rib-knit beanie in mustard.", ["yellow", "mustard", "beanie", "bold"], mat("#D4A017", roughness=0.95)),
    ("CT-006", "cap-theory", "Bucket Hat", "headwear", "head_bucket", 1099, "Olive", "Washed cotton bucket hat in olive.", ["olive", "green", "bucket", "hat", "streetwear"], mat("#6B7344")),
    # Second Hand: watches
    ("SH-001", "second-hand", "Field Analog", "watch", "watch_analog", 5499, "Steel", "Steel field watch with a matte black dial.", ["silver", "steel", "analog", "classic", "smart"], mat("#C0C0C0", roughness=0.3, metalness=0.9)),
    ("SH-002", "second-hand", "Dress Analog", "watch", "watch_analog", 6999, "Gold", "Slim gold-tone dress watch with a cream dial.", ["gold", "analog", "festive", "formal", "evening"], mat("#C9A227", roughness=0.25, metalness=1.0)),
    ("SH-003", "second-hand", "Retro Digital", "watch", "watch_digital", 2499, "Black", "Retro digital watch in matte black resin.", ["black", "digital", "retro", "all-black", "casual"], mat("#1C1C1C", roughness=0.5)),
    ("SH-004", "second-hand", "Retro Digital", "watch", "watch_digital", 2799, "Silver", "Retro digital watch with a brushed silver case.", ["silver", "digital", "retro", "tech"], mat("#BFC3C7", roughness=0.35, metalness=0.8)),
    # Lens Lane: eyewear and chains
    ("LL-001", "lens-lane", "Round Optical", "eyewear", "eye_round", 2499, "Tortoise", "Round acetate optical frame in warm tortoise.", ["brown", "tortoise", "glasses", "round", "classic"], mat("#6B4423", roughness=0.35)),
    ("LL-002", "lens-lane", "Round Optical", "eyewear", "eye_round", 2499, "Black", "Round acetate optical frame in gloss black.", ["black", "glasses", "round", "all-black", "classic"], mat("#111111", roughness=0.3)),
    ("LL-003", "lens-lane", "Wire Round", "eyewear", "eye_round", 2999, "Gold", "Thin gold wire round frame.", ["gold", "glasses", "round", "metal", "festive"], mat("#C5A35A", roughness=0.25, metalness=0.9)),
    ("LL-004", "lens-lane", "Stage Shades", "eyewear", "eye_shades", 1999, "Black", "Bold black sunglasses for bright lights.", ["black", "sunglasses", "shades", "all-black", "bold"], mat("#0E0E0E", roughness=0.25)),
    ("LL-005", "lens-lane", "Curb Chain", "neckwear", "neck_chain", 1499, "Silver", "Sterling-finish curb chain.", ["silver", "chain", "metal", "streetwear"], mat("#C8C8C8", roughness=0.2, metalness=1.0)),
    ("LL-006", "lens-lane", "Rope Chain", "neckwear", "neck_chain", 1799, "Gold", "Gold-tone rope chain for festive nights.", ["gold", "chain", "metal", "festive", "bangalore"], mat("#D4AF37", roughness=0.2, metalness=1.0)),
]

SLOTS = ["top", "outerwear", "bottom", "footwear", "headwear", "eyewear", "watch", "neckwear"]


def build_catalog():
    merchants = []
    for m in M:
        merchants.append({**m, "logo": f"/merchants/{m['slug']}.png", "banner": f"/merchants/{m['slug']}-banner.jpg"})
    mslugs = {m["slug"] for m in M}
    meshes = json.loads((ROOT / "contract" / "meshes.json").read_text())["meshes"]
    products = []
    for sku, merchant, name, slot, mesh, price, colorName, desc, tags, material in P:
        assert merchant in mslugs, sku
        assert meshes[mesh]["slot"] == slot, sku
        products.append(dict(sku=sku, merchant=merchant, name=name, slot=slot, mesh=mesh, price=price,
                             colorName=colorName, description=desc, tags=tags, material=material,
                             image=f"/products/{sku}.webp"))
    assert len({p["sku"] for p in products}) == len(products)
    return {"version": 1, "currency": "INR", "merchants": merchants, "products": products}


def write_data(cat):
    (PUB / "catalog").mkdir(parents=True, exist_ok=True)
    (PUB / "catalog" / "catalog.json").write_text(json.dumps(cat, indent=2, ensure_ascii=False) + "\n")
    byslug = {m["slug"]: m for m in cat["merchants"]}
    counts = {}
    for p in cat["products"]:
        counts[p["merchant"]] = counts.get(p["merchant"], 0) + 1
    with open(PUB / "catalog" / "merchants.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["slug", "name", "code", "tagline", "category", "story", "brand_color", "accent_color",
                    "logo_url", "banner_url", "product_count"])
        for m in cat["merchants"]:
            w.writerow([m["slug"], m["name"], m["code"], m["tagline"], m["category"], m["story"], m["brandColor"],
                        m["accentColor"], BASE + m["logo"], BASE + m["banner"], counts.get(m["slug"], 0)])
    with open(PUB / "catalog" / "products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sku", "name", "merchant_slug", "merchant_name", "slot", "price_inr", "color", "description",
                    "tags", "image_url", "try_on_path"])
        for p in cat["products"]:
            w.writerow([p["sku"], p["name"], p["merchant"], byslug[p["merchant"]]["name"], p["slot"], p["price"],
                        p["colorName"], p["description"], ";".join(p["tags"]), BASE + p["image"],
                        f"/stage?try={p['sku']}"])


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
    "kaapi-club": dict(file="BowlbyOne.ttf", case="title", track=0.0),
    "rao-and-sons": dict(file="DMSerifDisplay.ttf", case="title", track=0.0),
    "indigo-loom": dict(file="TenorSans.ttf", case="upper", track=0.14),
    "kerb": dict(file="Anton.ttf", case="upper", track=0.10),
    "cap-theory": dict(file="ArchivoBlack.ttf", case="upper", track=0.04),
    "second-hand": dict(file="SpaceMono-Bold.ttf", case="lower", track=0.0),
    "lens-lane": dict(file="Syne.ttf", case="lower", track=0.0),
}
# wordmark colour override (Kerb's brand black would vanish on dark pages; its accent red reads on both)
MARK_OVERRIDE = {"kerb": "#E63946"}
# subtle pattern for each merchant banner
BANNER_TEX = {"kaapi-club": "melange", "rao-and-sons": "check", "indigo-loom": "denim", "kerb": "corduroy",
              "cap-theory": "corduroy", "second-hand": "stripe", "lens-lane": "melange"}
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
    d.text((56, 108), p["sku"], font=font(22, bold=False), fill=mix(fg, bg, 0.35))
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
    """Product wordmark: type only, light text on transparent. Working name STAGE."""
    f = gfont("Syne.ttf", 150)
    s, track = "STAGE", 150 * 0.03
    w = int(tracked_width(f, s, track)) + 80
    asc, desc = f.getmetrics()
    img = Image.new("RGBA", (w, asc + desc + 60), (0, 0, 0, 0))
    draw_tracked(ImageDraw.Draw(img), 40, 30, s, f, (246, 243, 236, 255), track)
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
