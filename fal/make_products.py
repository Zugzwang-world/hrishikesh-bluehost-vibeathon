"""Editorial product photos (31 pieces) and store banners (5) through fal, matched to the looks on Hrishikesh.

Each product photo is an edit of a crop of that piece as it appears in his look render (so colour and pattern match),
restaged as an editorial still life on the store's brand-colour backdrop. Banners are composed from the store's new
product photos; the store wordmark (clean type, /merchants/SLUG.png) is overlaid, never generated.

Usage: python3 fal/make_products.py products|banners [--workers N] [--only SKU,SKU]
Writes web/public/products/SKU.webp (800 x 1000) and web/public/merchants/SLUG-banner.jpg (1600 x 600).
"""
from __future__ import annotations

import io
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from fal_call import data_uri, download, fal, ledger_total  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
PUB = REPO / "web/public"
CAT = json.loads((PUB / "catalog/catalog.json").read_text())
MER = {m["slug"]: m for m in CAT["merchants"]}
LOOKS = json.loads((PUB / "looks/index.json").read_text())["looks"]
DEFAULT = set(CAT.get("defaultLook") or [])
RAW = Path.home() / "code/hrishikesh-bluehost-vibeathon/out/fal/products"
MODEL, USD = "fal-ai/nano-banana-pro/edit", 0.15

# crop boxes on the normalised 800 x 1400 look canvas (feet at y 1380, 1.75 m = 1300 px)
CROP = {
    "headwear": (230, 30, 570, 300), "eyewear": (270, 110, 530, 290),
    "top": (110, 230, 690, 780), "outerwear": (90, 230, 710, 800), "neckwear": (220, 230, 580, 520),
    "bottom": (170, 590, 630, 1395), "footwear": (210, 1220, 590, 1400), "watch": (430, 600, 720, 900),
}
STAGING = {
    "top": "hung on a slim natural-wood hanger, front view, gently shaped as if just pressed",
    "outerwear": "hung open on a slim natural-wood hanger, front view, showing the collar and front placket",
    "bottom": "neatly folded in a clean editorial flat lay, top-down, waistband and leg shape visible",
    "footwear": "a pair, placed at a three-quarter angle on a low matte plinth",
    "headwear": "resting on a low matte plinth, three-quarter view showing the front",
    "eyewear": "folded, resting on a small matte stone plinth, three-quarter view",
    "watch": "on a small matte stone plinth, dial facing the camera, strap curved naturally",
    "neckwear": "draped in a soft curve on a small matte stone plinth",
}
PATTERN = {
    "denim": "denim with natural fading", "melange": "a soft heathered, slubby texture", "check": "a madras check pattern",
    "corduroy": "fine-wale corduroy", "stripe": "stripes", "solid": "", "print": "",
}


def look_for(p):
    cands = [l for l in LOOKS if p["sku"] in l["skus"]]
    return min(cands, key=lambda l: len(set(l["skus"]) ^ DEFAULT))


def ref_crop(p) -> Path:
    look = look_for(p)
    im = Image.open(PUB / look["src"].lstrip("/")).convert("RGBA").crop(CROP[p["slot"]])
    bg = Image.new("RGBA", im.size, (128, 128, 128, 255))
    bg.alpha_composite(im)
    s = 768 / max(bg.size)
    bg = bg.convert("RGB").resize((round(bg.width * s), round(bg.height * s)), Image.LANCZOS)
    out = RAW / f"{p['sku']}.ref.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    bg.save(out, quality=92)
    return out


def describe(p):
    m = p["material"]
    d = f"the {p['colorName'].lower()} {p['name'].lower()} (exact colour {m['color']})"
    pat = PATTERN.get(m["pattern"], "")
    if pat:
        d += f" in {pat}"
    if m["pattern"] == "print" and m.get("printText"):
        d += f", with the bold '{m['printText']}' graphic on the chest exactly as in the reference"
    if m.get("soleColor"):
        d += ", with a honey gum-rubber sole"
    if m.get("metalness", 0) >= 0.9:
        d += ", polished metal catching a clean highlight"
    return d


def product_prompt(p):
    mer = MER[p["merchant"]]
    return (f"Editorial e-commerce product photograph of exactly the item shown in the reference image: {describe(p)}. "
            f"Match its colour, pattern, texture and details to the reference precisely. Show the item alone, no person, "
            f"no mannequin, {STAGING[p['slot']]}. Seamless paper backdrop in the brand colour {mer['brandColor']} with a "
            f"soft gradient, soft directional studio key light with a gentle rim light so the item separates from the "
            f"backdrop, a soft natural shadow. A small blank kraft-paper thrift tag tied on with twine. Premium Instagram "
            f"thrift-store editorial styling, sharp focus, centred, generous margins. Plain, unbranded design: no brand stripes, swooshes, side logos, wordmarks or recognisable trademark details anywhere. No text, no logos, no watermark.")


def save_product(raw: Path, sku: str):
    im = Image.open(raw).convert("RGB")
    W, H = 800, 1000
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    im.crop((x, y, x + W, y + H)).save(PUB / "products" / f"{sku}.webp", "WEBP", quality=86, method=6)


def do_product(p):
    raw = RAW / f"{p['sku']}.png"
    if not raw.exists():
        ref = ref_crop(p)
        r = fal(MODEL, {"prompt": product_prompt(p), "image_urls": [data_uri(ref)], "num_images": 1,
                        "output_format": "png", "aspect_ratio": "4:5"}, USD, note=f"product {p['sku']}")
        download(r["images"][0]["url"], raw)
    save_product(raw, p["sku"])
    return p["sku"]


def font(name, size):
    return ImageFont.truetype(str(REPO / "blender/render/fonts" / name), size)


def do_banner(slug):
    mer = MER[slug]
    prods = [p for p in CAT["products"] if p["merchant"] == slug][:4]
    raw = RAW / f"banner-{slug}.png"
    if not raw.exists():
        refs = [data_uri(PUB / "products" / f"{p['sku']}.webp") for p in prods]
        names = ", ".join(f"{p['colorName'].lower()} {p['name'].lower()}" for p in prods)
        prompt = (f"Wide editorial fashion banner for {mer['name']}, an Instagram thrift store in Bengaluru "
                  f"({mer['tagline'].lower()}). A styled still life of these exact pieces from the reference images: {names}, "
                  f"arranged artfully on the RIGHT two thirds of the frame, matching their colours and patterns exactly. "
                  f"Seamless backdrop in the brand colour {mer['brandColor']}, soft studio light, gentle shadows, premium "
                  f"magazine styling. Keep the LEFT third calm, darker and empty for a wordmark. No text, no logos, no people.")
        r = fal(MODEL, {"prompt": prompt, "image_urls": refs, "num_images": 1, "output_format": "png",
                        "aspect_ratio": "21:9"}, USD, note=f"banner {slug}")
        download(r["images"][0]["url"], raw)
    im = Image.open(raw).convert("RGB")
    W, H = 1600, 600
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((x, y, x + W, y + H)).convert("RGBA")
    # left-side dark gradient for the wordmark
    g = Image.linear_gradient("L").rotate(90, expand=True).resize((W, H))  # 0 on the left .. 255 on the right
    shade = Image.new("RGBA", (W, H), (8, 8, 14, 0))
    shade.putalpha(g.point(lambda v: int(max(0, 235 - v * 1.5))))
    im.alpha_composite(shade)
    logo = Image.open(PUB / "merchants" / f"{slug}.png").convert("RGBA")
    ls = min(480 / logo.width, 140 / logo.height)
    logo = logo.resize((round(logo.width * ls), round(logo.height * ls)), Image.LANCZOS)
    # the wordmark goes on exactly as designed (clean type); never recoloured or generated
    lx, ly = 96, (H - logo.height) // 2 - 56
    im.alpha_composite(logo, (lx, ly))
    d = ImageDraw.Draw(im)
    f = font("Poppins-Medium.ttf", 28)
    words, lines, cur = mer["tagline"].split(), [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if d.textlength(trial, font=f) > 470 and cur:
            lines.append(cur); cur = w_
        else:
            cur = trial
    lines.append(cur)
    ty = ly + logo.height + 26
    for ln in lines:
        d.text((lx + 4, ty), ln, font=f, fill=(243, 238, 230, 235)); ty += 38
    d.text((lx + 4, ty + 12), f"{mer['instagram']}  ·  1 OF 1 PIECES", font=font("SpaceMono-Bold.ttf", 20),
           fill=(212, 175, 55, 255))
    im.convert("RGB").save(PUB / "merchants" / f"{slug}-banner.jpg", "JPEG", quality=88)
    return slug


def main():
    what = sys.argv[1]
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 8
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    RAW.mkdir(parents=True, exist_ok=True)
    if what == "products":
        jobs = [p for p in CAT["products"] if not only or p["sku"] in only]
        fn = do_product
    else:
        jobs = [m["slug"] for m in CAT["merchants"] if not only or m["slug"] in only]
        fn = do_banner
    print(f"{len(jobs)} {what}, ledger {ledger_total()} USD", flush=True)
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(fn, j): j for j in jobs}
        for f in as_completed(futs):
            try:
                print("ok", f.result(), flush=True)
            except Exception as e:
                print("FAIL", futs[f] if isinstance(futs[f], str) else futs[f]["sku"], str(e)[:200], flush=True)
    print("ledger USD", ledger_total())


if __name__ == "__main__":
    main()
