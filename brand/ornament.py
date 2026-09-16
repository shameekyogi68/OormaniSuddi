"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Ornament
=======================
Drawn decoration, for the greeting genre and nothing else.

The news system forbids ornament — one accent, hairlines not borders, no frame
round the canvas (AGENTS.md rule 3). That rule is right for news: a decorated
news card reads as less credible, not more. A festival wish is the opposite
contract. Its decoration IS its content, and the Gauri Ganesha poster drawn in
news grammar — masthead, eyebrow rail, left-aligned headline — read as a
bulletin about a festival rather than a greeting from one. See DECISIONS D54.

So ornament lives in this module, imported by templates/greeting.py only, and
no news template or golden hash can be moved by anything in it.

Everything here is still the single brand gold, drawn at hairline weights on
the supersampled canvas and dithered like the rest of the system. What makes a
greeting premium is finish and restraint — foil that catches light, a lotus
where a lesser design would put clip-art — not the quantity of decoration.
"""
from __future__ import annotations

import math
import random
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import typo
from .surface import Surface, _dither, _scurve
from .tokens import C, mix


# ─────────────────────────────────────────────────────────────────────────────
#  PLUMBING
# ─────────────────────────────────────────────────────────────────────────────

def _paste(sf: Surface, im: Image.Image, x: float, y: float):
    """alpha_composite at a DEVICE position that may be partly off-canvas.

    PIL refuses a negative destination outright, and a centred glow or a
    mirrored corner tile routinely starts a few pixels outside the frame."""
    x, y = int(round(x)), int(round(y))
    W, H = sf.img.size
    sx, sy = max(0, -x), max(0, -y)
    dx, dy = max(0, x), max(0, y)
    w = min(im.width - sx, W - dx)
    h = min(im.height - sy, H - dy)
    if w <= 0 or h <= 0:
        return
    if (sx, sy, w, h) != (0, 0, im.width, im.height):
        im = im.crop((sx, sy, sx + w, sy + h))
    sf.img.alpha_composite(im, (dx, dy))


def _tint(mask: np.ndarray, color, a: float) -> Image.Image:
    """A flat colour whose alpha is `mask` (0..255) scaled by `a`."""
    h, w = mask.shape
    arr = np.empty((h, w, 4), np.float32)
    arr[..., 0], arr[..., 1], arr[..., 2] = color[0], color[1], color[2]
    arr[..., 3] = mask * a
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')


def fade_line(sf: Surface, x0: float, x1: float, y: float, color,
              weight: float = 1.2, a0: float = 0.0, a1: float = 0.85,
              power: float = 1.0):
    """A horizontal hairline whose alpha runs from `a0` at x0 to `a1` at x1.

    The flourish either side of a centred line of type. It must dissolve at
    its outer end: a rule that stops dead reads as a table border."""
    ss = sf.ss
    X0, X1 = int(round(x0 * ss)), int(round(x1 * ss))
    n = X1 - X0
    if n <= 0:
        return
    t = np.linspace(0.0, 1.0, n, dtype=np.float32) ** power
    a = (a0 + (a1 - a0) * t) * 255.0
    h = max(1, int(round(weight * ss)))
    band = np.empty((h, n, 4), np.float32)
    band[..., 0], band[..., 1], band[..., 2] = color[0], color[1], color[2]
    band[..., 3] = a[None, :]
    _paste(sf, Image.fromarray(band.astype(np.uint8), 'RGBA'),
           X0, y * ss - h / 2)


def diamond(sf: Surface, cx: float, cy: float, r: float, color, a: float = 1.0):
    """A small filled lozenge — the bead that closes a flourish."""
    ss = sf.ss
    R = int(math.ceil(r * ss)) + 2
    lay = Image.new('RGBA', (2 * R, 2 * R), (0, 0, 0, 0))
    rr = r * ss
    ImageDraw.Draw(lay).polygon(
        [(R, R - rr), (R + rr, R), (R, R + rr), (R - rr, R)],
        fill=(*color[:3], int(255 * a)))
    _paste(sf, lay, cx * ss - R, cy * ss - R)


def _petal(bx: float, by: float, length: float, width: float,
           angle_deg: float, steps: int = 16) -> list[tuple[float, float]]:
    """A pointed petal from base (bx, by) toward `angle_deg` (0 = straight up,
    clockwise). Two quadratic curves meeting at the tip: the lotus petal of
    temple carving, not a round clip-art leaf."""
    ang = math.radians(angle_deg)
    ux, uy = math.sin(ang), -math.cos(ang)
    px, py = -uy, ux
    tx, ty = bx + ux * length, by + uy * length
    pts = []
    for side in (1, -1):
        idx = range(steps + 1) if side == 1 else range(steps, -1, -1)
        qx = bx + ux * length * 0.42 + px * width * side
        qy = by + uy * length * 0.42 + py * width * side
        for i in idx:
            t = i / steps
            pts.append(((1 - t) ** 2 * bx + 2 * (1 - t) * t * qx + t * t * tx,
                        (1 - t) ** 2 * by + 2 * (1 - t) * t * qy + t * t * ty))
    return pts


# ─────────────────────────────────────────────────────────────────────────────
#  GOLD FOIL TYPE
# ─────────────────────────────────────────────────────────────────────────────

def _foil_stops():
    """Read top to bottom of a glyph: a pale lit lip, the body, a darker
    equator, a reflected band, and a warm foot. The reversal at the equator is
    what makes gold read as METAL; a two-stop gradient reads as yellow paint,
    and flat yellow is the loudest single mark of a cheap festival poster."""
    return [(0.00, mix(C.gold_300, C.paper_0, 0.62)),
            (0.24, C.gold_300),
            (0.48, C.gold_500),
            (0.58, C.gold_600),
            (0.79, C.gold_400),
            (1.00, C.gold_600)]


def _ramp(t: np.ndarray, stops) -> np.ndarray:
    xs = [s[0] for s in stops]
    return np.stack([np.interp(t, xs, [s[1][i] for s in stops])
                     for i in range(3)], -1).astype(np.float32)


def foil_text(sf: Surface, text: str, f, cx: float, baseline: float, *,
              glow=None, glow_a: float = 0.0, depth: float = 1.0) -> float:
    """Set one line of type in engraved gold foil, centred on DEVICE `cx`,
    sitting on DEVICE `baseline`. Returns the device width.

    Layers, bottom up: a wide warm bloom (optional), a soft cast shadow, a
    tight contact shadow, the foil body, then a lit upper lip and a shaded
    lower lip cut from the glyph's own outline — which is what makes the
    letters look struck into metal rather than printed on it.

    The glyphs are drawn through typo.draw_text, so glyph safety and Kannada
    shaping apply exactly as they do everywhere else."""
    w = typo.text_width(text, f)
    rise, drop = typo.ink_extents(text, f)
    size = f.size
    pad = int(size * 0.7)
    lw, lh = int(w + 2 * pad), int(rise + drop + 2 * pad)
    lay = Image.new('RGBA', (lw, lh), (0, 0, 0, 0))
    typo.draw_text(lay, text, pad, pad + rise, f, (255, 255, 255, 255))
    mimg = lay.getchannel('A')
    m = np.asarray(mimg, np.float32)
    ox, oy = cx - w / 2 - pad, baseline - rise - pad

    def blurred(r):
        return np.asarray(mimg.filter(ImageFilter.GaussianBlur(max(0.5, r))),
                          np.float32)

    if glow is not None and glow_a > 0:
        _paste(sf, _tint(blurred(size * 0.30), glow, glow_a), ox, oy)
    _paste(sf, _tint(blurred(size * 0.12), (8, 3, 2), 0.70 * depth),
           ox, oy + size * 0.06)
    _paste(sf, _tint(blurred(size * 0.02), (10, 4, 2), 0.85 * depth),
           ox, oy + max(2.0, size * 0.025))

    t = np.clip((np.arange(lh, dtype=np.float32) - pad) / max(1.0, rise + drop),
                0.0, 1.0)
    body = np.empty((lh, lw, 4), np.float32)
    body[..., :3] = _ramp(t, _foil_stops())[:, None, :]
    body[..., :3] = _dither(body[..., :3], 0.6)
    body[..., 3] = m
    _paste(sf, Image.fromarray(np.clip(body, 0, 255).astype(np.uint8), 'RGBA'),
           ox, oy)

    k = max(1, int(round(size * 0.022)))
    down = np.pad(m, ((k, 0), (0, 0)))[:lh]
    up = np.pad(m, ((0, k), (0, 0)))[k:]
    _paste(sf, _tint(np.clip(m - down, 0, 255),
                     mix(C.paper_0, C.gold_300, 0.25), 0.55), ox, oy)
    _paste(sf, _tint(np.clip(m - up, 0, 255), C.gold_700, 0.45), ox, oy)
    return w


# ─────────────────────────────────────────────────────────────────────────────
#  FLOURISHES
# ─────────────────────────────────────────────────────────────────────────────

def ornate_divider(sf: Surface, cx: float, y: float, half: float,
                   color=C.gold_400, weight: float = 1.3, a: float = 0.9):
    """A lotus between two tapering gold hairlines.

    The one mark every festival design in this region reaches for, drawn as
    carving rather than as an icon: three pointed petals on a slim seat, and
    a bead either side where the rules begin."""
    gap = 30
    fade_line(sf, cx - half, cx - gap, y, color, weight, 0.0, a * 0.85, 0.9)
    fade_line(sf, cx + gap, cx + half, y, color, weight, a * 0.85, 0.0, 1.1)
    ss = sf.ss
    R = int(28 * ss)
    lay = Image.new('RGBA', (2 * R, 2 * R), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    c = (*color[:3], int(255 * a))
    bx, by = R, R + 4 * ss
    d.polygon(_petal(bx, by, 18 * ss, 6.5 * ss, 0), fill=c)
    d.polygon(_petal(bx - 1.5 * ss, by, 13 * ss, 5 * ss, -58), fill=c)
    d.polygon(_petal(bx + 1.5 * ss, by, 13 * ss, 5 * ss, 58), fill=c)
    d.polygon([(bx - 10 * ss, by + 1 * ss), (bx, by + 5.5 * ss),
               (bx + 10 * ss, by + 1 * ss), (bx, by + 3 * ss)], fill=c)
    for sgn in (-1, 1):
        ex = bx + sgn * (gap - 8) * ss
        rr = 2.3 * ss
        d.ellipse([ex - rr, R - rr, ex + rr, R + rr], fill=c)
    _paste(sf, lay, cx * ss - R, y * ss - R)


def corner_filigree(sf: Surface, inset: float, arm: float, color=C.gold_400,
                    weight: float = 1.3, a: float = 0.8):
    """Four mirrored corner flourishes: a double hairline angle with a nested
    lozenge, fading along each arm.

    Not a frame. A frame is a continuous border and boxes the picture in; four
    corners that dissolve toward each other imply the edge of a card without
    drawing one, which is the difference between a printed invitation and a
    certificate."""
    ss = sf.ss
    pad = 6
    T = int((arm + pad * 2 + 10) * ss)
    m = Image.new('L', (T, T), 0)
    d = ImageDraw.Draw(m)
    o = pad * ss
    w = max(1, round(weight * ss))
    d.line([(o, o), (o + arm * ss, o)], fill=255, width=w)
    d.line([(o, o), (o, o + arm * ss)], fill=255, width=w)
    i = o + 9 * ss
    ia = arm * 0.60 * ss
    wi = max(1, round(weight * 0.8 * ss))
    d.line([(i, i), (o + ia, i)], fill=180, width=wi)
    d.line([(i, i), (i, o + ia)], fill=180, width=wi)
    kx = o + 21 * ss
    r = 4.4 * ss
    d.polygon([(kx, kx - r), (kx + r, kx), (kx, kx + r), (kx - r, kx)], fill=255)

    yy, xx = np.mgrid[0:T, 0:T].astype(np.float32)
    dist = np.maximum(xx - o, yy - o) / (arm * ss * 1.04)
    fall = np.clip(1.0 - dist, 0.0, 1.0) ** 0.6
    mask = np.asarray(m, np.float32) * fall

    beads = Image.new('L', (T, T), 0)
    bd = ImageDraw.Draw(beads)
    for ex, ey in ((o + (arm + 6) * ss, o), (o, o + (arm + 6) * ss)):
        rr = 2.2 * ss
        bd.ellipse([ex - rr, ey - rr, ex + rr, ey + rr], fill=150)
    mask = np.maximum(mask, np.asarray(beads, np.float32))

    tl = _tint(mask, color, a)
    X0 = int((inset - pad) * ss)
    X1 = sf.img.width - X0 - T
    Y1 = sf.img.height - X0 - T
    _paste(sf, tl, X0, X0)
    _paste(sf, tl.transpose(Image.Transpose.FLIP_LEFT_RIGHT), X1, X0)
    _paste(sf, tl.transpose(Image.Transpose.FLIP_TOP_BOTTOM), X0, Y1)
    _paste(sf, tl.transpose(Image.Transpose.ROTATE_180), X1, Y1)


def bokeh(sf: Surface, color, seed: str, regions: list[tuple], n: int = 34,
          r: tuple = (3.0, 15.0), a: tuple = (0.10, 0.42), twinkles: int = 6):
    """Out-of-focus lamp light and a few sparkles, seeded so the same greeting
    renders identically every time.

    Confined to `regions` — never across the deity or the type. Mostly small:
    radii are drawn from a skewed distribution, because a field of equal-sized
    circles is the look of a stock "celebration" background."""
    regions = [b for b in regions if b[2] - b[0] > 4 and b[3] - b[1] > 4]
    if not regions:
        return
    rng = random.Random(zlib.crc32(seed.encode('utf-8')))
    areas = [(b[2] - b[0]) * (b[3] - b[1]) for b in regions]

    def pick():
        x0, y0, x1, y1 = rng.choices(regions, weights=areas)[0]
        return rng.uniform(x0, x1), rng.uniform(y0, y1)

    lay = Image.new('RGBA', (sf.w, sf.h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    core = mix(color, (255, 250, 235), 0.40)
    for _ in range(n):
        x, y = pick()
        rad = r[0] + (r[1] - r[0]) * rng.random() ** 2.4
        al = a[0] + (a[1] - a[0]) * rng.random()
        d.ellipse([x - rad, y - rad, x + rad, y + rad],
                  fill=(*color[:3], int(255 * al * 0.55)))
        cr = rad * 0.45
        d.ellipse([x - cr, y - cr, x + cr, y + cr],
                  fill=(*core[:3], int(255 * al)))
    lay = lay.filter(ImageFilter.GaussianBlur(2.2))

    tw = Image.new('RGBA', (sf.w, sf.h), (0, 0, 0, 0))
    dt = ImageDraw.Draw(tw)
    spark = (255, 244, 212)
    for _ in range(twinkles):
        x, y = pick()
        L = rng.uniform(8, 16)
        dt.polygon([(x - L, y), (x, y - 0.9), (x + L, y), (x, y + 0.9)],
                   fill=(*spark, 170))
        dt.polygon([(x, y - L * 1.3), (x + 0.9, y), (x, y + L * 1.3),
                    (x - 0.9, y)], fill=(*spark, 190))
        dt.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(*spark, 240))
    lay.alpha_composite(tw.filter(ImageFilter.GaussianBlur(0.6)))
    sf.img.alpha_composite(lay.resize(sf.img.size, Image.Resampling.BICUBIC))


def vignette(sf: Surface, color, strength: float = 0.6, cx: float = 0.5,
             cy: float = 0.46, rx: float = 0.78, ry: float = 0.66,
             power: float = 2.0):
    """An elliptical fall-off into the theme's ground, so the eye is held on
    the subject and the edges read as candle-lit rather than cropped."""
    w, h = sf.w, sf.h
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dd = np.sqrt(((xx / w - cx) / rx) ** 2 + ((yy / h - cy) / ry) ** 2)
    al = np.clip((dd - 0.55) / 0.75, 0.0, 1.0) ** power * strength
    lay = np.empty((h, w, 4), np.uint8)
    lay[..., 0], lay[..., 1], lay[..., 2] = color[0], color[1], color[2]
    lay[..., 3] = (al * 255).astype(np.uint8)
    sf.img.alpha_composite(Image.fromarray(lay, 'RGBA').resize(
        sf.img.size, Image.Resampling.BILINEAR))


def pool(sf: Surface, cx: float, cy: float, rx: float, ry: float, color,
         a: float = 0.7):
    """A soft elliptical darkening under a line of type.

    A full-width scrim that is dark enough to seat small gold type over a
    bright garland also flattens the top of the photograph. A pool shaped to
    the line darkens only what the type needs, so the flowers either side stay
    lit and the words still read."""
    ss = sf.ss
    X0, X1 = int((cx - rx) * ss), int((cx + rx) * ss)
    Y0, Y1 = int((cy - ry) * ss), int((cy + ry) * ss)
    w, h = X1 - X0, Y1 - Y0
    if w <= 0 or h <= 0:
        return
    xx = (np.arange(w, dtype=np.float32) + 0.5) / w * 2 - 1
    yy = (np.arange(h, dtype=np.float32) + 0.5) / h * 2 - 1
    d = np.sqrt(xx[None, :] ** 2 + yy[:, None] ** 2)
    t = np.clip(1.0 - d, 0.0, 1.0)
    mask = (t * t * (3 - 2 * t)) * 255.0
    _paste(sf, _tint(mask, color, a), X0, Y0)


def mandala(sf: Surface, cx: float, cy: float, r: float, color=C.gold_400,
            a: float = 0.3):
    """A hairline rosette for a greeting with no photograph.

    Geometric rather than iconographic, so the same plate serves Deepavali,
    Eid and Christmas alike — a coastal channel greets all of its readers."""
    ss = sf.ss
    R = int(r * ss)
    S = 2 * R + 8
    m = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(m)
    c0 = S / 2
    w = max(1, round(1.1 * ss))

    def ring(rr, v=255, width=w):
        d.ellipse([c0 - rr, c0 - rr, c0 + rr, c0 + rr], outline=v, width=width)

    def outline(pts, v=255):
        d.line(pts + [pts[0]], fill=v, width=w, joint='curve')

    def petals(count, base, length, width, v=255, offset=0.0):
        for k in range(count):
            ang = offset + k * 360.0 / count
            rad = math.radians(ang)
            outline(_petal(c0 + math.sin(rad) * base, c0 - math.cos(rad) * base,
                           length, width, ang), v)

    def dots(count, rr, dot, v=255, offset=0.0):
        for k in range(count):
            rad = math.radians(offset + k * 360.0 / count)
            x, y = c0 + math.sin(rad) * rr, c0 - math.cos(rad) * rr
            d.ellipse([x - dot, y - dot, x + dot, y + dot], fill=v)

    ring(R * 0.10)
    petals(8, R * 0.10, R * 0.20, R * 0.06)
    ring(R * 0.33)
    petals(16, R * 0.33, R * 0.22, R * 0.035, v=220, offset=11.25)
    ring(R * 0.57, v=200)
    dots(32, R * 0.64, 1.7 * ss, v=210)
    petals(24, R * 0.70, R * 0.22, R * 0.055, v=180)
    ring(R * 0.95, v=150)
    dots(96, R * 0.99, 1.1 * ss, v=150)

    mask = np.asarray(m.filter(ImageFilter.GaussianBlur(0.5 * ss)), np.float32)
    _paste(sf, _tint(mask, color, a), cx * ss - c0, cy * ss - c0)


# ─────────────────────────────────────────────────────────────────────────────
#  PHOTOGRAPH TREATMENT
# ─────────────────────────────────────────────────────────────────────────────

def warm_grade(im: Image.Image, deep, contrast: float = 0.12,
               saturation: float = 1.06, shadow_amt: float = 0.20) -> Image.Image:
    """The festive counterpart of house_grade.

    house_grade cools shadows toward brand ink navy, which is right for news
    and deadening on a lamp-lit altar. This keeps the warmth, lifts colour a
    touch, and lets the shadows fall into the THEME's ground instead, so the
    picture and the page it sits on are one continuous darkness."""
    arr = np.asarray(im.convert('RGB')).astype(np.float32) / 255.0
    arr = _scurve(arr, contrast)
    lum = (arr[..., 0] * 0.2126 + arr[..., 1] * 0.7152
           + arr[..., 2] * 0.0722)[..., None]
    arr = lum + (arr - lum) * saturation
    wgt = ((1.0 - lum) ** 2.2) * shadow_amt
    dv = np.array(deep[:3], np.float32) / 255.0
    arr = arr * (1.0 - wgt) + dv * wgt
    return Image.fromarray((np.clip(arr, 0.0, 1.0) * 255.0 + 0.5)
                           .astype(np.uint8), 'RGB')


def arch_points(w: float, h: float, rise: float,
                steps: int = 44) -> list[tuple[float, float]]:
    """Outline of a temple arch window, origin top-left: vertical sides, then
    two circular arcs springing at `rise` below the apex and meeting in a
    point. Returned open at the bottom — (0, h) … (w, h) — so it serves both
    as a fill polygon and as a frame polyline with no line across the foot.

    A drop-pointed arch rather than a round one: the round arch reads as a
    Western picture frame, the pointed one as a mantapa or gopura doorway."""
    cx0 = w * 0.75
    yc = (cx0 ** 2 - (w / 2 - cx0) ** 2 - rise ** 2) / (2 * rise)
    ccx, ccy = cx0, rise + yc
    rad = math.hypot(cx0, yc)
    a0 = math.atan2(rise - ccy, 0 - ccx)
    a1 = math.atan2(0 - ccy, w / 2 - ccx)
    left = [(ccx + rad * math.cos(a0 + (a1 - a0) * i / steps),
             ccy + rad * math.sin(a0 + (a1 - a0) * i / steps))
            for i in range(steps + 1)]
    right = [(w - x, y) for x, y in reversed(left)]
    return [(0.0, h)] + left + right[1:] + [(w, h)]


def arch_mask(w: int, h: int, rise: float) -> Image.Image:
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).polygon(arch_points(w, h, rise), fill=255)
    return m


def arch_frame(sf: Surface, x: float, y: float, w: float, h: float,
               rise: float, gap: float = 9.0, color=C.gold_400,
               inner=C.gold_600):
    """A double gold line round an arch window, open at the foot and fading
    toward it, with a lotus finial at the apex."""
    ss = sf.ss
    mx, my = 30, 58
    LW, LH = int((w + 2 * mx) * ss), int((h + my + 8) * ss)
    ox, oy = mx * ss, my * ss

    def shifted(pts, dx, dy):
        return [(ox + (px + dx) * ss, oy + (py + dy) * ss) for px, py in pts]

    outer = Image.new('L', (LW, LH), 0)
    do = ImageDraw.Draw(outer)
    do.line(shifted(arch_points(w + 2 * gap, h + gap, rise + gap * 0.9),
                    -gap, -gap), fill=255, width=max(1, round(1.6 * ss)),
            joint='curve')
    apx, apy = ox + w / 2 * ss, oy - (gap + 5) * ss
    do.polygon(_petal(apx, apy, 20 * ss, 7 * ss, 0), fill=255)
    do.polygon(_petal(apx - 1.5 * ss, apy, 14 * ss, 5 * ss, -58), fill=255)
    do.polygon(_petal(apx + 1.5 * ss, apy, 14 * ss, 5 * ss, 58), fill=255)

    inn = Image.new('L', (LW, LH), 0)
    ImageDraw.Draw(inn).line(shifted(arch_points(w, h, rise), 0, 0), fill=255,
                             width=max(1, round(1.0 * ss)), joint='curve')

    rows = np.arange(LH, dtype=np.float32)
    fade = np.clip(1.0 - np.clip((rows - oy) / max(1.0, h * ss), 0, 1) * 0.82,
                   0.18, 1.0)[:, None]
    _paste(sf, _tint(np.asarray(outer, np.float32) * fade, color, 0.9),
           x * ss - ox, y * ss - oy)
    _paste(sf, _tint(np.asarray(inn, np.float32) * fade, inner, 0.8),
           x * ss - ox, y * ss - oy)
