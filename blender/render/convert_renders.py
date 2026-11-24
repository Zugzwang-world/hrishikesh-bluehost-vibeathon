"""Convert Blender product renders to web/public/products/SKU.webp and record them in rendered.json.

  uv run --with pillow python blender/render/convert_renders.py [SKU ...]

Reads blender/render/out/SKU.png (written by render_products.py), saves 800 x 1000 WebP under the stable
name /products/SKU.webp and adds the SKU to blender/render/rendered.json so build_catalog.py never overwrites it.
Lane E owns this script.
"""
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "blender" / "render" / "out"
PROD = ROOT / "web" / "public" / "products"
MANIFEST = ROOT / "blender" / "render" / "rendered.json"


def main():
    only = set(sys.argv[1:])
    try:
        done = set(json.loads(MANIFEST.read_text()))
    except Exception:
        done = set()
    n = 0
    for png in sorted(OUT.glob("*.png")):
        sku = png.stem
        if only and sku not in only:
            continue
        im = Image.open(png).convert("RGB")
        if im.size != (800, 1000):
            im = im.resize((800, 1000), Image.LANCZOS)
        im.save(PROD / f"{sku}.webp", "WEBP", quality=88, method=4)
        done.add(sku)
        n += 1
    MANIFEST.write_text(json.dumps(sorted(done), indent=2) + "\n")
    print(f"converted {n} renders; rendered.json now lists {len(done)} SKUs")


if __name__ == "__main__":
    main()
