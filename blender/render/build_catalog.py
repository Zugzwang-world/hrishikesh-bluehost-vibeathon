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
FONT = "/System/Library/Fonts/Avenir Next.ttc"


def font(size, bold=True):
    try:
        return ImageFont.truetype(FONT, size, index=(2 if bold else 0))
    except Exception:
        return ImageFont.load_default()


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lum(rgb):
    r, g, b = [c / 255 for c in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def text_c(d, xy, s, f, fill):
    bb = d.textbbox((0, 0), s, font=f)
    d.text((xy[0] - (bb[2] - bb[0]) / 2, xy[1] - (bb[3] - bb[1]) / 2 - bb[1]), s, font=f, fill=fill)


def should_write(path: Path) -> bool:
    return FORCE or not path.exists()


def product_placeholder(p, m):
    path = PUB / "products" / f"{p['sku']}.webp"
    if not should_write(path):
        return
    W, H = 800, 1000
    bg = hex2rgb(m["brandColor"])
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    # soft vertical gradient
    for y in range(H):
        d.line([(0, y), (W, y)], fill=mix(bg, (0, 0, 0), 0.35 * y / H))
    fg = (255, 255, 255) if lum(bg) < 0.55 else (20, 20, 20)
    acc = hex2rgb(m["accentColor"])
    col = hex2rgb(p["material"]["color"])
    # swatch disc with shadow
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).ellipse([230, 300, 570, 640], fill=150)
    sh = sh.filter(ImageFilter.GaussianBlur(24))
    img.paste((0, 0, 0), (0, 14), sh)
    d = ImageDraw.Draw(img)
    d.ellipse([220, 280, 580, 640], fill=col, outline=acc, width=6)
    if p["material"]["pattern"] != "solid":
        pc = hex2rgb(p["material"]["patternColor"])
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).ellipse([226, 286, 574, 634], fill=255)
        layer = Image.new("RGB", (W, H), col)
        ld = ImageDraw.Draw(layer)
        pat = p["material"]["pattern"]
        if pat in ("stripe", "corduroy"):
            step = 28 if pat == "stripe" else 12
            for y in range(280, 640, step):
                ld.rectangle([220, y, 580, y + step // 2 - 2], fill=pc)
        elif pat == "check":
            for x in range(220, 580, 48):
                ld.rectangle([x, 280, x + 18, 640], fill=pc)
            for y in range(280, 640, 48):
                ld.rectangle([220, y, 580, y + 18], fill=pc)
        elif pat in ("denim", "melange"):
            for i in range(-400, 400, 9):
                ld.line([(220 + i, 640), (580 + i, 280)], fill=pc, width=3)
        elif pat == "print" and p["material"]["printText"]:
            text_c(ld, (400, 460), p["material"]["printText"], font(84), pc)
        img.paste(layer, (0, 0), mask)
        d = ImageDraw.Draw(img)
    d.text((56, 52), m["name"].upper(), font=font(30), fill=acc)
    d.text((56, 96), p["sku"], font=font(24, bold=False), fill=fg)
    text_c(d, (400, 720), p["name"], font(48), fg)
    text_c(d, (400, 784), p["colorName"], font(34, bold=False), fg)
    text_c(d, (400, 880), f"₹{p['price']:,}", font(44), acc)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "WEBP", quality=88)


def merchant_assets(m):
    bg = hex2rgb(m["brandColor"])
    acc = hex2rgb(m["accentColor"])
    logo = PUB / "merchants" / f"{m['slug']}.png"
    logo.parent.mkdir(parents=True, exist_ok=True)
    if should_write(logo):
        f = font(120)
        tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        bb = tmp.textbbox((0, 0), m["name"], font=f)
        w, h = bb[2] - bb[0] + 40, bb[3] - bb[1] + 40
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        # wordmark in brand colour unless too dark to read on dark pages; light brands use their colour
        ImageDraw.Draw(img).text((20 - bb[0], 20 - bb[1]), m["name"], font=f, fill=bg + (255,))
        img.save(logo)
    banner = PUB / "merchants" / f"{m['slug']}-banner.jpg"
    if should_write(banner):
        W, H = 1600, 600
        img = Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(img)
        for x in range(W):
            d.line([(x, 0), (x, H)], fill=mix(bg, (0, 0, 0), 0.4 * x / W))
        for i in range(6):
            d.ellipse([1100 + i * 30, -200 + i * 40, 1700 + i * 30, 400 + i * 40], outline=acc, width=2)
        fg = (255, 255, 255) if lum(bg) < 0.55 else (20, 20, 20)
        d.text((100, 190), m["name"], font=font(120), fill=fg)
        d.text((104, 350), m["tagline"], font=font(44, bold=False), fill=acc)
        img.save(banner, "JPEG", quality=88)


def brand_assets():
    b = PUB / "brand"
    b.mkdir(parents=True, exist_ok=True)
    ink, gold, plum = (14, 14, 20), (242, 193, 78), (91, 52, 140)
    if should_write(b / "logo.png"):
        img = Image.new("RGBA", (800, 240), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([20, 40, 180, 200], outline=gold + (255,), width=14)
        d.ellipse([70, 90, 130, 150], fill=gold + (255,))
        d.text((220, 52), "STAGE", font=font(120), fill=(255, 255, 255, 255))
        img.save(b / "logo.png")
    if should_write(b / "hero.jpg"):
        W, H = 1920, 1080
        img = Image.new("RGB", (W, H), ink)
        d = ImageDraw.Draw(img)
        for y in range(H):
            d.line([(0, y), (W, y)], fill=mix(plum, ink, min(1, y / (H * 0.8))))
        cone = Image.new("L", (W, H), 0)
        ImageDraw.Draw(cone).polygon([(900, 0), (1020, 0), (1300, 980), (620, 980)], fill=90)
        cone = cone.filter(ImageFilter.GaussianBlur(40))
        img.paste((255, 240, 210), (0, 0), cone)
        d = ImageDraw.Draw(img)
        d.ellipse([700, 930, 1220, 1010], fill=(60, 50, 90))
        d.ellipse([900, 380, 1020, 500], fill=(150, 110, 85))  # head
        d.rounded_rectangle([860, 510, 1060, 760], radius=40, fill=(58, 59, 63))  # blazer
        d.rectangle([925, 515, 995, 700], fill=(244, 242, 238))  # tee
        d.rounded_rectangle([870, 760, 1050, 940], radius=20, fill=(58, 58, 62))
        d.rounded_rectangle([860, 935, 950, 965], radius=12, fill=(245, 245, 242))
        d.rounded_rectangle([970, 935, 1060, 965], radius=12, fill=(245, 245, 242))
        d.text((120, 120), "HRISHIKESH", font=font(96), fill=(255, 255, 255))
        d.text((124, 240), "On stage at Bluehost, Bangalore", font=font(44, bold=False), fill=gold)
        img.save(b / "hero.jpg", "JPEG", quality=88)
    if should_write(b / "persona.png"):
        W, H = 1200, 1500
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([450, 180, 750, 480], fill=(150, 110, 85, 255))
        d.pieslice([430, 150, 770, 420], 180, 360, fill=(30, 24, 22, 255))
        d.rounded_rectangle([340, 520, 860, 1100], radius=120, fill=(58, 59, 63, 255))
        d.rectangle([540, 530, 660, 1000], fill=(244, 242, 238, 255))
        d.rounded_rectangle([370, 1080, 830, 1500], radius=60, fill=(58, 58, 62, 255))
        img.save(b / "persona.png")


def main():
    cat = build_catalog()
    write_data(cat)
    if not ONLY_DATA:
        byslug = {m["slug"]: m for m in cat["merchants"]}
        for p in cat["products"]:
            product_placeholder(p, byslug[p["merchant"]])
        for m in cat["merchants"]:
            merchant_assets(m)
        brand_assets()
    print(f"catalog: {len(cat['merchants'])} merchants, {len(cat['products'])} products -> {PUB}")


if __name__ == "__main__":
    main()
