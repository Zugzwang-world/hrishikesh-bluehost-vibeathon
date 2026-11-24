"""Generate the Stage pattern textures (original, made in code, tileable).

Run from the repo root:  uv run --with pillow --with numpy python blender/render/build_textures.py

Writes into web/public/textures/:
  stripe.png check.png denim.png melange.png corduroy.png   512 x 512 grayscale masks
      (white = patternColor, black = base colour). One tile = 0.25 m on the garment.
  print-blr.png print-ship-it.png                             1024 x 512 RGBA, white type on transparent.
Both the web (three.js) and Blender (render_products.py) read these exact files.
Lane E owns this script. Never rename the outputs.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "web" / "public" / "textures"
FONTS = Path(__file__).resolve().parent / "fonts"
N = 512
rng = np.random.default_rng(24112026)


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def periodic_noise(size=N, cutoff=None, power=0.0, aniso=(1.0, 1.0)):
    """Tileable noise: random spectrum -> inverse FFT is periodic by construction. Returns ~[0, 1]."""
    fy = np.fft.fftfreq(size)[:, None] * size
    fx = np.fft.fftfreq(size)[None, :] * size
    f = np.sqrt((fx / aniso[0]) ** 2 + (fy / aniso[1]) ** 2) + 1e-6
    spec = (rng.normal(size=(size, size)) + 1j * rng.normal(size=(size, size)))
    amp = 1.0 / f ** power
    if cutoff:
        amp = amp * np.exp(-((f / cutoff) ** 2))
    amp[0, 0] = 0
    n = np.fft.ifft2(spec * amp).real
    n = (n - n.mean()) / (n.std() + 1e-9)
    return n  # zero mean, unit std


def to01(n, k=0.25):
    return np.clip(0.5 + n * k, 0, 1)


def save_mask(name, m):
    m = np.clip(m, 0, 1)
    Image.fromarray((m * 255 + 0.5).astype(np.uint8), "L").save(OUT / name)


yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)


def stripe():
    # Breton: 8 bands across the tile (period 64 px = 3.1 cm), pattern band 38% of the period.
    period = N / 8
    ph = (yy % period) / period
    edge = 1.5 / period
    band = smooth((ph - 0.0) / edge) * (1 - smooth((ph - 0.38) / edge))
    # knit texture: fine horizontal courses + wale ticks, gentle slub
    knit = 0.045 * np.sin(2 * np.pi * yy / 4) + 0.04 * np.sin(2 * np.pi * xx / 4 + 1.3)
    slub = 0.05 * periodic_noise(cutoff=70, power=0.6, aniso=(1, 3))
    m = band * (0.93 + knit + slub) + (1 - band) * (0.05 + 0.5 * (knit + slub) * 0.4)
    save_mask("stripe.png", m)


def check():
    # Two-way check: 4 repeats per tile (6.25 cm). Bands of 0.5 alpha in both directions
    # overlap to full, so crossings read darkest, like a woven shirting check.
    period = N / 4
    def band(coord):
        ph = (coord % period) / period
        e = 2.0 / period
        return smooth(ph / e) * (1 - smooth((ph - 0.5) / e))
    h = band(yy)
    v = band(xx)
    m = 0.5 * h + 0.5 * v
    # woven threads: fine warp/weft, plus slight hand
    weave = 0.05 * np.sin(2 * np.pi * xx / 4) * np.sin(2 * np.pi * yy / 4)
    thread = 0.03 * np.sin(2 * np.pi * xx / 2) + 0.03 * np.sin(2 * np.pi * yy / 2)
    slub = 0.05 * periodic_noise(cutoff=90, power=0.5)
    m = m + (weave + thread + slub) * (0.5 + 0.5 * m)
    save_mask("check.png", m)


def denim():
    # Right-hand twill: diagonal 8 px pitch (4 mm) with a 3-over-1 float, white weft pick showing
    # on the surface, plus horizontal slub streaks and fine mottling.
    pitch = 8
    d = ((xx + yy) % pitch) / pitch
    twill = smooth((d - 0.0) / 0.2) * (1 - smooth((d - 0.5) / 0.25))
    warp = 0.5 + 0.5 * np.sin(2 * np.pi * xx / 4)  # vertical warp yarns
    slub = periodic_noise(cutoff=60, power=0.3, aniso=(0.12, 1.0))  # long along x: weft slubs
    mott = periodic_noise(cutoff=40, power=0.9)
    m = 0.24 + 0.34 * twill + 0.10 * warp + 0.09 * slub + 0.04 * mott
    save_mask("denim.png", m)


def melange():
    # Heather: two scales of tileable noise + fine fibre speckle.
    n1 = periodic_noise(cutoff=55, power=0.2)
    n2 = periodic_noise(cutoff=160, power=0.0)
    fibre = periodic_noise(cutoff=256, power=0.0, aniso=(1.0, 1.0))
    m = 0.5 + 0.13 * n1 + 0.09 * n2 + 0.07 * fibre
    # sparse bright neps
    neps = (periodic_noise(cutoff=256, power=0.0) > 2.1).astype(float) * 0.35
    save_mask("melange.png", m + neps)


def corduroy():
    # 64 wales across the tile (8 px each). Ridge = base (black), groove between ridges = patternColor (white).
    period = N / 64
    ph = (xx % period) / period
    groove = 0.5 + 0.5 * np.cos(2 * np.pi * (ph - 0.5))  # 1 at the groove centre (ph=0.0/1.0), 0 on the ridge crown
    groove = groove ** 1.8
    fibre = periodic_noise(cutoff=256, power=0.0, aniso=(0.3, 1.0))
    slub = periodic_noise(cutoff=60, power=0.5, aniso=(0.4, 1.0))
    m = 0.08 + 0.80 * groove + 0.05 * fibre + 0.05 * slub
    save_mask("corduroy.png", m)


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def print_texture(slug, text, fontfile, tracking=0, fill_w=0.86, fill_h=0.7):
    W, H = 1024, 512
    # size the type to fit
    size = 400
    while size > 20:
        f = font(fontfile, size)
        glyphs = [f.getbbox(c) for c in text]
        adv = [f.getlength(c) for c in text]
        total = sum(adv) + tracking * size / 100 * (len(text) - 1)
        asc, desc = f.getmetrics()
        bb = f.getbbox(text)
        th = bb[3] - bb[1]
        if total <= W * fill_w and th <= H * fill_h:
            break
        size -= 4
    img = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    bb = f.getbbox(text)
    th = bb[3] - bb[1]
    x = (W - total) / 2
    y = (H - th) / 2 - bb[1]
    for c, a in zip(text, adv):
        d.text((x, y), c, font=f, fill=(255, 255, 255, 255))
        x += a + tracking * size / 100
    img.save(OUT / f"print-{slug}.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    stripe()
    check()
    denim()
    melange()
    corduroy()
    print_texture("blr", "BLR", "ArchivoBlack.ttf", tracking=4, fill_w=0.80, fill_h=0.62)
    print_texture("ship-it", "SHIP IT", "ArchivoBlack.ttf", tracking=3, fill_w=0.88, fill_h=0.5)
    print(f"textures -> {OUT}")


if __name__ == "__main__":
    main()
