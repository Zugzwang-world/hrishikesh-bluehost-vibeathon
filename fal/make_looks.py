"""Step 2 of Brief 10: clothes-only edits of the chosen base, background removed, normalised cutouts.

Usage: python3 fal/make_looks.py BASE_PNG [stage|singles|extra|all] [--workers N]
Writes web/public/looks/KEY.webp (KEY = sorted SKUs joined with commas) and web/public/looks/index.json.
Raw renders are cached in out/fal/looks/ so nothing is generated twice.
"""
from __future__ import annotations

import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from fal_call import data_uri, download, fal, ledger_total  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
CAT = json.loads((REPO / "web/public/catalog/catalog.json").read_text())
BY = {p["sku"]: p for p in CAT["products"]}
SLOTS = ["top", "outerwear", "bottom", "footwear", "headwear", "eyewear", "watch", "neckwear"]
OUT = REPO / "web/public/looks"
RAW = Path.home() / "code/hrishikesh-bluehost-vibeathon/out/fal/looks"
EDIT_MODEL, EDIT_USD = "fal-ai/nano-banana-pro/edit", 0.15
BG_MODELS = [("fal-ai/birefnet/v2", 0.01), ("fal-ai/birefnet", 0.01), ("fal-ai/bria/background/remove", 0.02)]
CANVAS_W, CANVAS_H, FIG_H, FEET_Y = 800, 1400, 1300, 1380

DEFAULT = CAT.get("defaultLook") or ["KT-002", "KT-006", "SW-001", "KK-001", "LL-006", "SH-001"]
STAGE_READY = next((l["skus"] for l in CAT.get("looks", []) if l["title"] == "Stage Ready"),
                   ["KT-001", "KT-006", "SW-001", "KK-001", "LL-001", "LL-006", "SH-001"])
ALL_BLACK = ["KT-002", "SW-003", "KK-005", "LL-002", "LL-007", "SH-003"]
FESTIVE = ["KT-008", "SW-004", "KK-004", "LL-006", "SH-001", "SH-005"]
_idx_lock = threading.Lock()


def key(skus):
    return ",".join(sorted(skus))


def by_slot(skus):
    return {BY[s]["slot"]: BY[s] for s in skus}


def piece(p):
    m = p["material"]
    d = f"{p['colorName'].lower()} {p['name'].lower()}"
    if m["pattern"] not in ("solid", "print"):
        d += f" ({m['pattern']} pattern)"
    if m["pattern"] == "print" and m.get("printText"):
        d += f" with a bold '{m['printText']}' print on the chest"
    if m.get("soleColor"):
        d += " with a gum-brown rubber sole"
    return d


def describe(skus):
    s = by_slot(skus)
    parts = []
    parts.append(f"top: {piece(s['top'])}" + (", buttoned" if s["top"]["mesh"] == "top_shirt" else ""))
    parts.append(f"over it: {piece(s['outerwear'])}, worn open" if "outerwear" in s else "no jacket or overshirt")
    parts.append(f"bottoms: {piece(s['bottom'])}")
    parts.append(f"shoes: {piece(s['footwear'])}")
    parts.append(f"on his head: {piece(s['headwear'])}" if "headwear" in s else "no hat, his own curly hair visible")
    if "eyewear" in s and s["eyewear"]["mesh"] == "eye_shades":
        parts.append(f"eyewear: {piece(s['eyewear'])} instead of his glasses")
    else:
        parts.append("his own thin gold hexagonal glasses")
    parts.append(f"on his left wrist: {piece(s['watch'])}" if "watch" in s else "no watch")
    parts.append(f"around his neck: {piece(s['neckwear'])}" if "neckwear" in s else "no necklace")
    return "; ".join(parts)


def edit_prompt(skus):
    return ("Edit this photo of the man. Change ONLY his clothes and accessories so he wears exactly: " + describe(skus) +
            ". Keep his face, curly hair, skin, body, pose, arm position, framing, camera angle, lighting and the plain dark "
            "stage background exactly the same. Full length, feet visible. Photorealistic, the same person.")


def normalise(rgba: Image.Image) -> Image.Image:
    a = rgba.split()[3].point(lambda v: 255 if v > 24 else 0)
    bb = a.getbbox()
    fig = rgba.crop(bb)
    s = FIG_H / fig.height
    fig = fig.resize((max(1, round(fig.width * s)), FIG_H), Image.LANCZOS)
    if fig.width > CANVAS_W:
        fig = fig.resize((CANVAS_W, round(FIG_H * CANVAS_W / fig.width)), Image.LANCZOS)
    c = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    c.paste(fig, ((CANVAS_W - fig.width) // 2, FEET_Y - fig.height), fig)
    return c


def remove_bg(src_png: Path, dest_png: Path) -> Path:
    if dest_png.exists():
        return dest_png
    last = None
    for model, usd in BG_MODELS:
        try:
            r = fal(model, {"image_url": data_uri(src_png)}, usd, note=f"bg {src_png.stem}")
            url = (r.get("image") or {}).get("url") or (r.get("images") or [{}])[0].get("url")
            return download(url, dest_png)
        except RuntimeError as e:
            last = e
            if "budget stop" in str(e):
                raise
    raise RuntimeError(f"bg removal failed: {last}")


def publish(skus, title, cut_png: Path):
    k = key(skus)
    img = normalise(Image.open(cut_png).convert("RGBA"))
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / f"{k}.webp", "WEBP", quality=82, method=6)
    with _idx_lock:
        ip = OUT / "index.json"
        try:
            idx = json.loads(ip.read_text())
        except Exception:
            idx = {"version": 1, "caption": "AI render of Hrishikesh",
                   "canvas": {"w": CANVAS_W, "h": CANVAS_H, "figurePx": FIG_H, "feetY": FEET_Y}, "looks": []}
        idx["looks"] = [l for l in idx["looks"] if l["key"] != k]
        idx["looks"].append({"key": k, "skus": sorted(skus), "title": title, "src": f"/looks/{k}.webp"})
        order = {key(STAGE_READY): 0, key(DEFAULT): 1}
        idx["looks"].sort(key=lambda l: (order.get(l["key"], 2), l["key"]))
        ip.write_text(json.dumps(idx, indent=1) + "\n")
    return k


def render(base: Path, skus, title):
    k = key(skus)
    raw = RAW / f"{k}.png"
    cut = RAW / f"{k}.cut.png"
    if key(skus) == key(DEFAULT):
        src = base  # the base already wears the default look
    else:
        if not raw.exists():
            r = fal(EDIT_MODEL, {"prompt": edit_prompt(skus), "image_urls": [data_uri(base)], "num_images": 1,
                                 "output_format": "png", "aspect_ratio": "9:16"}, EDIT_USD, note=f"look {k}")
            download(r["images"][0]["url"], raw)
        src = raw
    remove_bg(src, cut)
    publish(skus, title, cut)
    return k


def looks_for(which):
    out = []
    if which in ("stage", "all"):
        out += [(STAGE_READY, "Stage Ready"), (DEFAULT, "Hrishikesh today")]
    if which in ("singles", "all"):
        d = by_slot(DEFAULT)
        for p in CAT["products"]:
            if p["sku"] in DEFAULT:
                continue
            look = [x["sku"] for sl, x in d.items() if sl != p["slot"]] + [p["sku"]]
            out.append((look, None))
    if which in ("extra", "all"):
        out += [(ALL_BLACK, "All Black"), (FESTIVE, "Festive Bengaluru")]
    return out


def main():
    global RAW
    base = Path(sys.argv[1])
    RAW = RAW / base.stem
    which = sys.argv[2] if len(sys.argv) > 2 else "stage"
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
    RAW.mkdir(parents=True, exist_ok=True)
    jobs = looks_for(which)
    print(f"{len(jobs)} looks, ledger {ledger_total()} USD", flush=True)
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(render, base, s, t): (s, t) for s, t in jobs}
        for f in as_completed(futs):
            s, t = futs[f]
            try:
                print("ok", f.result(), t or "", flush=True)
            except Exception as e:
                print("FAIL", key(s), str(e)[:200], flush=True)
    print("ledger USD", ledger_total())


if __name__ == "__main__":
    main()
