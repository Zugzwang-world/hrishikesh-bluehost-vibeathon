"""Procedural textures for the stage (numpy only). Arrays are float sRGB, shape (H, W, 3), row 0 = top."""
import numpy as np


def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], dtype=np.float32)


def _blend(img, y0, y1, x0, x1, col, a):
    h, w, _ = img.shape
    y0, y1, x0, x1 = max(0, y0), min(h, y1), max(0, x0), min(w, x1)
    if y1 > y0 and x1 > x0:
        img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - a) + col * a


def outlined_square(img, cx, cy, size, col, alpha=0.85, line=3, fill=0.0):
    s = int(size)
    x0, y0 = int(cx - s / 2), int(cy - s / 2)
    if fill > 0:
        _blend(img, y0, y0 + s, x0, x0 + s, col, fill)
    _blend(img, y0, y0 + line, x0, x0 + s, col, alpha)
    _blend(img, y0 + s - line, y0 + s, x0, x0 + s, col, alpha)
    _blend(img, y0, y0 + s, x0, x0 + line, col, alpha)
    _blend(img, y0, y0 + s, x0 + s - line, x0 + s, col, alpha)


def gradient(w, h, c0="#2D4BFF", c1="#7A5CFF", diag=0.25, shade=0.18):
    x = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    t = np.clip((1 - diag) * x + diag * (1 - y), 0, 1)[..., None]
    img = hexrgb(c0) * (1 - t) + hexrgb(c1) * t
    # gentle darkening toward the bottom and a soft central bloom
    img *= (1 - shade * y[..., None] ** 1.5)
    r2 = ((x - 0.5) * 1.6) ** 2 + ((y - 0.42) * 2.2) ** 2
    img += 0.08 * np.exp(-r2 * 3)[..., None]
    return np.clip(img, 0, 1).astype(np.float32)


def square_cluster(img, corner, cell, cols, rows, rng, col="#AFC2FF"):
    """Stair-stepped cluster of outlined squares growing out of a corner ('bl' or 'tr')."""
    h, w, _ = img.shape
    c = hexrgb(col)
    for i in range(cols):
        for j in range(rows):
            d = i / max(cols - 1, 1) + j / max(rows - 1, 1)
            if rng.random() > 1.15 - d * 0.75:
                continue
            if corner == "bl":
                cx = int(cell * (1.2 + i)) + rng.integers(-4, 5)
                cy = h - int(cell * (1.2 + j)) + rng.integers(-4, 5)
            else:
                cx = w - int(cell * (1.2 + i)) + rng.integers(-4, 5)
                cy = int(cell * (1.2 + j)) + rng.integers(-4, 5)
            size = cell * rng.uniform(0.7, 1.35)
            fill = 0.22 if rng.random() < 0.18 else 0.0
            outlined_square(img, cx, cy, size, c, alpha=rng.uniform(0.55, 0.95),
                            line=max(2, int(cell * 0.06)), fill=fill)


def led_wall_tex(w=1536, h=640, seed=11):
    """Main wall: cobalt to violet gradient with outlined-square clusters bottom-left and top-right."""
    rng = np.random.default_rng(seed)
    img = gradient(w, h)
    cell = h / 9.0
    # cells counted from the corner: (i along x, j along y); dense near the corner, thinning out
    for corner in ("bl", "tr"):
        for i in range(6):
            for j in range(5):
                # dense in the corner, thinning out; keeps the centre band clear for the web's text
                lim = 5.2 if corner == "bl" else 3.9    # top-right stays clear of the name band
                if i * 1.25 + j * 1.15 > lim or rng.random() < 0.2:
                    continue
                if corner == "bl":
                    cx, cy = cell * (0.9 + i * 1.05), h - cell * (0.9 + j * 1.05)
                else:
                    cx, cy = w - cell * (0.9 + i * 1.05), cell * (0.9 + j * 1.05)
                size = cell * rng.choice([0.8, 0.95, 1.0, 1.0, 1.25, 1.5])
                fill = 0.25 if rng.random() < 0.15 else 0.0
                outlined_square(img, cx + rng.integers(-3, 4), cy + rng.integers(-3, 4), size,
                                hexrgb("#B4C6FF"), alpha=rng.uniform(0.6, 0.95), line=3, fill=fill)
    return np.clip(img, 0, 1)


def side_panel_tex(w=640, h=880, seed=5):
    rng = np.random.default_rng(seed)
    img = gradient(w, h, "#2B45F5", "#5E55FF", diag=0.6, shade=0.25)
    cell = w / 7.0
    for i in range(5):
        for j in range(3):
            if i + j * 1.6 > 4.5 or rng.random() < 0.2:
                continue
            cx, cy = w - cell * (0.8 + i), cell * (0.8 + j)
            outlined_square(img, cx, cy, cell * rng.choice([0.8, 1.0, 1.2]), hexrgb("#B4C6FF"),
                            alpha=rng.uniform(0.55, 0.9), line=3)
    return np.clip(img, 0, 1)


def gobo_tex(n=1024, shapes=170, seed=21):
    """Tileable blue gobo wash: bent flame / leaf shapes on dark navy."""
    rng = np.random.default_rng(seed)
    acc = np.zeros((n, n), dtype=np.float32)
    win = 150
    yy, xx = np.mgrid[-win:win, -win:win].astype(np.float32)
    for _ in range(shapes):
        cx, cy = rng.integers(0, n, 2)
        ang = rng.uniform(0, np.pi)
        L = rng.uniform(40, 120)            # half length in px
        Wd = L * rng.uniform(0.16, 0.3)     # half width
        bend = rng.uniform(-0.5, 0.5)
        c, s = np.cos(ang), np.sin(ang)
        u = (xx * c + yy * s) / L
        v = (-xx * s + yy * c) / Wd
        v = v - bend * u * u * (L / Wd) * 0.3
        width = np.clip((1 - u), 0, None) ** 0.9 * np.clip((1 + u), 0, None) ** 0.35
        d = np.abs(v) - width
        shape = np.clip(0.5 - d * 1.2, 0, 1) * (np.abs(u) < 1)
        shape *= rng.uniform(0.45, 1.0) * (0.55 + 0.45 * np.clip(1 - u, 0, 1))
        ys = (np.arange(cy - win, cy + win) % n)
        xs = (np.arange(cx - win, cx + win) % n)
        acc[np.ix_(ys, xs)] = np.maximum(acc[np.ix_(ys, xs)], shape)
    # soft pooled intensity so it does not look uniform
    lo = rng.normal(0, 1, (8, 8)).astype(np.float32)
    lo = np.kron(lo, np.ones((n // 8, n // 8), dtype=np.float32))
    k = np.ones(129, dtype=np.float32) / 129
    lo = np.apply_along_axis(lambda r: np.convolve(np.concatenate([r[-64:], r, r[:64]]), k, mode="same")[64:-64], 0, lo)
    lo = np.apply_along_axis(lambda r: np.convolve(np.concatenate([r[-64:], r, r[:64]]), k, mode="same")[64:-64], 1, lo)
    acc *= np.clip(0.75 + 0.35 * lo, 0.35, 1.1)
    bg = hexrgb("#070C2A")
    blue = hexrgb("#2F66FF")
    hi = hexrgb("#7FA6FF")
    a = acc[..., None]
    img = bg * (1 - a) + blue * a
    img = img + (hi - blue) * np.clip(a - 0.75, 0, 1) * 2.0
    return np.clip(img, 0, 1).astype(np.float32)


def qr_tex(n=96, seed=3):
    """QR-like sticker for chair backs: white card, three finder squares, random modules."""
    rng = np.random.default_rng(seed)
    m = 25
    grid = rng.random((m, m)) < 0.45

    def finder(r, c):
        grid[r:r + 7, c:c + 7] = True
        grid[r + 1:r + 6, c + 1:c + 6] = False
        grid[r + 2:r + 5, c + 2:c + 5] = True
    for r, c in ((0, 0), (0, m - 7), (m - 7, 0)):
        finder(r, c)
    cell = (n - 16) // m
    img = np.ones((n, n, 3), dtype=np.float32) * 0.96
    off = (n - cell * m) // 2
    for r in range(m):
        for c in range(m):
            if grid[r, c]:
                img[off + r * cell: off + (r + 1) * cell, off + c * cell: off + (c + 1) * cell] = 0.08
    return img
