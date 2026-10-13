"""
ಊರ್ಮನಿ ಸುದ್ದಿ — the YouTube channel kit, made from the logo.

    python3 scripts/youtube_kit.py                 # every channel asset -> assets/youtube/
    python3 scripts/youtube_kit.py thumb \\
        --photo frame.jpg --title "ಸೇನೇಶ್ವರ ಗಣಪತಿ ಪ್ರತಿಷ್ಠಾಪನೆ" \\
        --place "ಬೈಂದೂರು" [--tag "ನೇರಪ್ರಸಾರ"] [--focal 0.47 0.30] --out thumb.jpg

Everything is drawn from assets/logo_* and the house palette in brand/tokens.py,
so the channel and the posts are one brand. Sizes are YouTube's own:
profile 800², banner 2560x1440 (safe 1546x423), watermark 150², thumbnail
1280x720 under 2 MB, end screen and live cards 1920x1080.

House rules kept: gold only as a fill, never as type; red only on news
elements (the place and the live pill) and the logo's own speed strokes;
nothing in the thumbnail's bottom-right, where YouTube puts the duration.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand.tokens import C, Brand                     # noqa: E402
from brand.typo import font                           # noqa: E402
from brand.surface import house_grade, cover          # noqa: E402

OUT = os.path.join(ROOT, 'assets', 'youtube')
S = 2                                                 # supersample

INK, INK2, INK3 = C.ink_900, C.ink_600, C.ink_400
PAPER, PAPER2 = C.paper_50, C.paper_100
GOLD, GOLD_HI, GOLD_LO = C.gold_500, C.gold_400, C.gold_600
RED, SEA = C.red_500, C.sea_500


# ─────────────────────────────────────────────────────────────────────────────
#  canvas
# ─────────────────────────────────────────────────────────────────────────────

class K:
    """A supersampled RGBA canvas; every coordinate is in delivery pixels."""

    def __init__(self, w, h, bg=PAPER):
        self.w, self.h = w, h
        self.img = Image.new('RGBA', (w * S, h * S), (*bg, 255) if len(bg) == 3 else bg)

    def d(self):
        return ImageDraw.Draw(self.img)

    def lay(self):
        return Image.new('RGBA', self.img.size, (0, 0, 0, 0))

    # shapes ------------------------------------------------------------------
    def rrect(self, box, r, fill, outline=None, width=0):
        x0, y0, x1, y1 = box
        lay = self.lay()
        ImageDraw.Draw(lay).rounded_rectangle(
            [x0 * S, y0 * S, x1 * S, y1 * S], r * S, fill=fill,
            outline=outline, width=int(width * S))
        self.img.alpha_composite(lay)

    def shadow(self, box, r, blur=24, alpha=60, dy=10):
        x0, y0, x1, y1 = box
        lay = self.lay()
        ImageDraw.Draw(lay).rounded_rectangle(
            [x0 * S, (y0 + dy) * S, x1 * S, (y1 + dy) * S], r * S,
            fill=(*C.ink_950, alpha))
        self.img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur * S)))

    def circle(self, cx, cy, r, fill, outline=None, width=0):
        self.rrect((cx - r, cy - r, cx + r, cy + r), r, fill, outline, width)

    def glow(self, cx, cy, radius, color, a=0.5, power=2.2):
        W, H = self.img.size
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        dd = np.sqrt((xx - cx * S) ** 2 + (yy - cy * S) ** 2) / (radius * S)
        al = np.clip(1 - dd, 0, 1) ** power * a * 255
        lay = np.zeros((H, W, 4), np.float32)
        lay[..., :3] = color
        lay[..., 3] = al
        self.img.alpha_composite(Image.fromarray(lay.astype(np.uint8), 'RGBA'))

    def vgrad(self, y0, y1, c0, c1, a0=1.0, a1=1.0):
        Y0, Y1 = int(y0 * S), int(y1 * S)
        t = np.linspace(0, 1, max(1, Y1 - Y0))[:, None]
        rgb = np.array(c0)[None] * (1 - t) + np.array(c1)[None] * t
        al = (a0 + (a1 - a0) * t) * 255
        band = np.concatenate([rgb, al], 1)[:, None, :].repeat(self.img.width, 1)
        band[..., :3] += np.random.default_rng(7).uniform(-.6, .6, band.shape[:2])[..., None]
        self.img.alpha_composite(
            Image.fromarray(np.clip(band, 0, 255).astype(np.uint8), 'RGBA'), (0, Y0))

    def hscrim(self, x0, x1, color, a0, a1, y0=0, y1=None):
        """A horizontal veil — smoothstep, so the join cannot be found."""
        y1 = self.h if y1 is None else y1
        X0, X1 = int(x0 * S), int(x1 * S)
        u = np.linspace(0, 1, max(1, X1 - X0))
        t = u * u * (3 - 2 * u)
        al = (a0 + (a1 - a0) * t) * 255
        band = np.zeros((1, X1 - X0, 4), np.float32)
        band[..., :3] = color
        band[..., 3] = al
        band = band.repeat(int((y1 - y0) * S), 0)
        self.img.alpha_composite(Image.fromarray(band.astype(np.uint8), 'RGBA'),
                                 (X0, int(y0 * S)))

    def sea(self, y0, y1, x0=0, x1=None, color=SEA, a=0.35, n=14):
        """The logo's horizon reduced to geometry: ruled water, lines closing
        up toward the horizon the way perspective does."""
        x1 = self.w if x1 is None else x1
        lay = self.lay()
        dr = ImageDraw.Draw(lay)
        for i in range(n):
            t = (i / (n - 1)) ** 1.8
            y = y0 + (y1 - y0) * t
            w = 1.2 + 2.6 * t
            al = int(255 * a * (0.35 + 0.65 * t))
            dr.rectangle([x0 * S, y * S, x1 * S, (y + w) * S], fill=(*color, al))
        self.img.alpha_composite(lay)

    def reflection(self, cx, y0, y1, color=GOLD, a=0.8, n=10, w0=260):
        """The sun's path on the water — short gold dashes that narrow away."""
        lay = self.lay()
        dr = ImageDraw.Draw(lay)
        for i in range(n):
            t = i / (n - 1)
            y = y0 + (y1 - y0) * (t ** 1.6)
            half = w0 * (1 - 0.75 * t) / 2
            dr.rounded_rectangle([(cx - half) * S, y * S, (cx + half) * S, (y + 5 + 4 * t) * S],
                                 4 * S, fill=(*color, int(255 * a * (1 - 0.6 * t))))
        self.img.alpha_composite(lay)

    def speed(self, x0, x1, y, n=6, gap=22, color=RED):
        """The ಸುದ್ದಿ speed strokes from the logo — tapered, staggered."""
        lay = self.lay()
        dr = ImageDraw.Draw(lay)
        for i in range(n):
            yy = y + i * gap
            sx = x0 + (i % 3) * 70 + (i * 37) % 90
            th = 9 if i % 2 == 0 else 6
            pts = [(sx * S, (yy + th / 2) * S), (x1 * S, yy * S),
                   (x1 * S, (yy + th) * S)]
            dr.polygon(pts, fill=(*color, 235))
        self.img.alpha_composite(lay)

    # type --------------------------------------------------------------------
    def text(self, s, x, base, f, fill, anchor='ls', stroke=0, stroke_fill=None,
             shadow=None):
        """Baseline-anchored type. `f` is a delivery-size font; drawn at S."""
        fs = font(*f[:1], int(f[1] * S), *f[2:]) if isinstance(f, tuple) else f
        if shadow:
            dx, dy, blur, col = shadow
            lay = self.lay()
            ImageDraw.Draw(lay).text(((x + dx) * S, (base + dy) * S), s, font=fs,
                                     fill=col, anchor=anchor,
                                     stroke_width=int(stroke * S), stroke_fill=col)
            self.img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur * S)))
        self.d().text((x * S, base * S), s, font=fs, fill=fill, anchor=anchor,
                      stroke_width=int(stroke * S), stroke_fill=stroke_fill)

    @staticmethod
    def width(s, f):
        fs = font(*f[:1], int(f[1] * S), *f[2:])
        return ImageDraw.Draw(Image.new('L', (8, 8))).textlength(s, font=fs) / S

    @staticmethod
    def ink(s, f):
        """(rise above baseline, drop below) of the real ink."""
        fs = font(*f[:1], int(f[1] * S), *f[2:])
        b = ImageDraw.Draw(Image.new('L', (8, 8))).textbbox((0, 0), s, font=fs, anchor='ls')
        return -b[1] / S, b[3] / S

    def pill(self, x, y, s, f, fill, color, h=None, padx=22, dot=None):
        """A label on a rounded fill, text optically centred on its ink."""
        rise, drop = self.ink(s, f)
        h = h or (rise + drop) + 30
        w = self.width(s, f) + padx * 2 + (h * 0.42 if dot else 0)
        self.rrect((x, y, x + w, y + h), h / 2, fill)
        tx = x + padx
        if dot:
            r = h * 0.13
            self.circle(tx + r, y + h / 2, r, dot)
            tx += h * 0.42
        self.text(s, tx, y + h / 2 + (rise - drop) / 2, f, color)
        return x + w

    # images ------------------------------------------------------------------
    def paste(self, im, x, y, w=None, h=None):
        im = im.convert('RGBA')
        if w and not h:
            h = w * im.height / im.width
        if h and not w:
            w = h * im.width / im.height
        im = im.resize((int(w * S), int(h * S)), Image.Resampling.LANCZOS)
        self.img.alpha_composite(im, (int(x * S), int(y * S)))
        return w, h

    def grain(self, sigma=2.4):
        a = np.asarray(self.img).astype(np.float32)
        n = np.random.default_rng(2026).normal(0, sigma, a.shape[:2])
        a[..., :3] += n[..., None]
        self.img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')

    def finish(self, mode='RGB'):
        out = self.img.resize((self.w, self.h), Image.Resampling.LANCZOS)
        return out if mode == 'RGBA' else out.convert('RGB')


def logo(variant='cutout'):
    name = {'cutout': 'oormani_suddi_logo_cutout_bg_erased.png',
            'circle': 'logo_clean_circle.png',
            'card': 'logo_clean_card.png'}[variant]
    im = Image.open(os.path.join(ROOT, 'assets', name)).convert('RGBA')
    return im.crop(im.getbbox())


def save(img, name, **kw):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    if p.endswith('.jpg'):
        img.save(p, 'JPEG', quality=kw.get('q', 93), subsampling=0, optimize=True)
    else:
        img.save(p, optimize=True)
    print(f'  {os.path.relpath(p, ROOT)}  {img.width}x{img.height}  '
          f'{os.path.getsize(p) // 1024} KB')
    return p


# fonts: (family, size[, weight])
KN = lambda s: ('kn', s)                               # noqa: E731
KNV = lambda s, w=600: ('kn_var', s, w)                # noqa: E731
LAT = lambda s, w=600: ('latin', s, w)                 # noqa: E731


def play_icon(k, x, cy, h, color):
    lay = k.lay()
    ImageDraw.Draw(lay).polygon(
        [(x * S, (cy - h / 2) * S), ((x + h * 0.88) * S, cy * S), (x * S, (cy + h / 2) * S)],
        fill=color)
    k.img.alpha_composite(lay)


# ─────────────────────────────────────────────────────────────────────────────
#  1 · profile picture  800x800 (shown as a circle, as small as 24px)
# ─────────────────────────────────────────────────────────────────────────────

def profile():
    k = K(800, 800, PAPER)
    k.paste(logo('circle'), 0, 0, 800, 800)
    save(k.finish(), 'profile_800.png')


# ─────────────────────────────────────────────────────────────────────────────
#  2 · banner  2560x1440 · TV sees all, desktop the middle 2560x423,
#      phones only the centre 1546x423 — everything that matters lives there
# ─────────────────────────────────────────────────────────────────────────────

SAFE = (507, 508, 2053, 931)


def banner(guides=False):
    W, H = 2560, 1440
    k = K(W, H, PAPER)
    hz = 905                                            # horizon
    # sky: warm paper deepening toward the sunset at the horizon
    k.vgrad(0, hz, PAPER, (252, 232, 190), 1, 1)
    k.glow(2290, hz - 40, 1250, GOLD_HI, 0.55)
    k.glow(2290, hz - 40, 520, GOLD, 0.55)
    # the sun, set on the right — seen by desktop and TV, never under the copy
    sun = Image.new('RGBA', (560 * S, 560 * S), (0, 0, 0, 0))
    yy, xx = np.mgrid[0:560 * S, 0:560 * S]
    t = (yy / (560 * S))[..., None]
    col = np.array(C.gold_300) * (1 - t) + np.array(C.amber_500) * t
    m = ((xx - 280 * S) ** 2 + (yy - 280 * S) ** 2) <= (275 * S) ** 2
    arr = np.zeros((560 * S, 560 * S, 4), np.float32)
    arr[..., :3] = col
    arr[..., 3] = m * 255
    sun = Image.fromarray(arr.astype(np.uint8), 'RGBA').filter(ImageFilter.GaussianBlur(1.2))
    sun = sun.crop((0, 0, 560 * S, int((hz - (hz - 330)) * S)))   # sunk below the sea
    k.img.alpha_composite(sun, (int((2290 - 280) * S), int((hz - 330) * S)))
    # sea
    k.vgrad(hz, H, (232, 238, 238), (214, 226, 230))
    k.sea(hz + 4, H, color=SEA, a=0.30, n=18)
    k.reflection(2290, hz + 14, hz + 260, GOLD, 0.85, 11, 520)
    # horizon hairline
    k.rrect((0, hz - 1.5, W, hz + 1.5), 0, (*INK, 90))

    # the logo's red speed strokes run in from the left edge toward the mark
    k.speed(150, 520, 660, n=6, gap=30)

    # the mark — on paper the cutout is native: its black type needs the light
    lg = logo('cutout')
    lh = 405
    lw, _ = k.paste(lg, 540, SAFE[1] + 10, h=lh)

    # copy block, inside the phone-safe area
    x = 540 + lw + 64
    maxw = SAFE[2] - 20 - x
    y = 538
    k.pill(x, y, Brand.coverage + '  •  ಕನ್ನಡ', KNV(32, 650), INK, C.paper_0, h=52)
    head = 'ಕರಾವಳಿಯ ಊರಿನ ಸುದ್ದಿ'
    hs = 100
    while K.width(head, KN(hs)) > maxw and hs > 60:
        hs -= 2
    rise, drop = K.ink(head, KN(hs))
    k.text(head, x - 4, y + 52 + 28 + rise, KN(hs), INK)
    base2 = y + 52 + 28 + rise + drop + 58
    topics = 'ಹಬ್ಬ  •  ಜಾತ್ರೆ  •  ಕಂಬಳ  •  ಯಕ್ಷಗಾನ  •  ಊರಿನ ಆಗುಹೋಗು'
    ts = 42
    while K.width(topics, KNV(ts, 560)) > maxw and ts > 28:
        ts -= 1
    k.text(topics, x, base2, KNV(ts, 560), INK2)
    # subscribe: gold is the brand's fill, so the call to action wears it
    by = base2 + 30
    bh = 68
    sub = 'ಸಬ್‌ಸ್ಕ್ರೈಬ್ ಮಾಡಿ'
    bw = K.width(sub, KN(36)) + 116
    k.shadow((x, by, x + bw, by + bh), bh / 2, blur=14, alpha=55, dy=6)
    k.rrect((x, by, x + bw, by + bh), bh / 2, GOLD)
    k.circle(x + 40, by + bh / 2, 22, INK)
    play_icon(k, x + 33, by + bh / 2, 20, GOLD)
    r, dp = K.ink(sub, KN(36))
    k.text(sub, x + 78, by + bh / 2 + (r - dp) / 2, KN(36), INK)
    k.text(Brand.handle, x + bw + 28, by + bh / 2 + 13, LAT(36, 600), INK2)
    k.grain(1.6)
    img = k.finish()
    save(img, 'banner_2560x1440.jpg', q=94)
    if guides:
        g = img.copy().convert('RGBA')
        lay = Image.new('RGBA', g.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(lay)
        dr.rectangle([0, 508, W, 931], outline=(30, 120, 255, 255), width=4)
        dr.rectangle(SAFE, outline=(255, 30, 120, 255), width=5)
        dr.rectangle([0, 0, W - 1, H - 1], outline=(0, 0, 0, 255), width=4)
        g.alpha_composite(lay)
        f = font('latin', 34, 700)
        d = ImageDraw.Draw(g)
        d.text((20, 470), 'DESKTOP 2560x423', font=f, fill=(30, 120, 255))
        d.text((SAFE[0] + 10, SAFE[3] + 12), 'PHONE / SAFE 1546x423', font=f, fill=(255, 30, 120))
        d.text((20, 20), 'TV 2560x1440', font=f, fill=(0, 0, 0))
        save(g.convert('RGB'), '_check_banner_safe_areas.jpg', q=85)


# ─────────────────────────────────────────────────────────────────────────────
#  3 · video watermark  150x150 transparent (Studio > Branding)
# ─────────────────────────────────────────────────────────────────────────────

def watermark():
    k = K(150, 150, (0, 0, 0, 0))
    k.paste(logo('circle'), 0, 0, 150, 150)
    save(k.finish('RGBA'), 'watermark_150.png')


# ─────────────────────────────────────────────────────────────────────────────
#  4 · thumbnail  1280x720
# ─────────────────────────────────────────────────────────────────────────────

def thumbnail(photo, title, place, tag=None, focal=(0.5, 0.35), out=None,
              highlight_last=True):
    W, H = 1280, 720
    k = K(W, H, INK)
    px = 455                                            # photo starts here
    ph = Image.open(photo).convert('RGB')
    ph = house_grade(cover(ph, (W - px) * S, H * S, focal), strength=0.8)
    k.img.alpha_composite(ph.convert('RGBA'), (px * S, 0))
    # dissolve the picture into the ink panel, and settle the floor
    k.hscrim(px, px + 300, INK, 1.0, 0.0)
    lay = K(W, H, (0, 0, 0, 0))
    lay.vgrad(H - 200, H, INK, INK, 0.0, 0.55)
    k.img.alpha_composite(lay.img)
    k.glow(140, 330, 520, GOLD, 0.10)

    x, top = 52, 52
    xe = k.pill(x, top, place, KN(34), RED, C.paper_0, h=60)
    if tag:
        k.pill(xe + 14, top, tag, KN(34), C.paper_0, RED, h=60, dot=RED)

    # title: 2–3 lines, as large as fits; the last line on a gold fill
    words = title.split()
    maxw, area = 640, (top + 60 + 40, H - 190)
    best = None
    for size in range(132, 70, -4):
        f = KN(size)
        lines, cur = [], ''
        for w in words:
            t = (cur + ' ' + w).strip()
            if K.width(t, f) <= maxw or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        lh = size * 1.30
        if len(lines) <= 3 and max(K.width(l, f) for l in lines) <= maxw + 40 \
                and lh * len(lines) <= area[1] - area[0]:
            best = (size, lines, lh)
            break
    size, lines, lh = best or (72, [title], 94)
    f = KN(size)
    block = lh * len(lines)
    y = area[0] + (area[1] - area[0] - block) / 2
    for i, line in enumerate(lines):
        rise, drop = K.ink(line, f)
        base = y + i * lh + size * 0.98
        if highlight_last and i == len(lines) - 1 and len(lines) > 1:
            lw_ = K.width(line, f)
            k.rrect((x - 14, base - size * 0.86, x + lw_ + 18, base + size * 0.30), 10, GOLD)
            k.text(line, x, base, f, INK)
        else:
            k.text(line, x, base, f, C.paper_0, stroke=3, stroke_fill=INK,
                   shadow=(0, 6, 10, (*C.ink_950, 200)))

    # the mark, bottom-left — bottom-right is YouTube's duration badge
    k.paste(logo('circle'), x - 6, H - 160, 128, 128)
    k.text(Brand.handle, x + 136, H - 82, LAT(30, 650), C.paper_100)
    img = k.finish()
    out = out or os.path.join(OUT, 'thumbnail.jpg')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    q = 92
    while True:
        img.save(out, 'JPEG', quality=q, subsampling=0, optimize=True)
        if os.path.getsize(out) < 1_900_000 or q < 60:
            break
        q -= 5
    print(f'  {os.path.relpath(out, ROOT)}  {W}x{H}  {os.path.getsize(out) // 1024} KB')
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  5 · end screen  1920x1080 — the last 5–20 s of every long video
# ─────────────────────────────────────────────────────────────────────────────

# Where to drop the elements in Studio > End screen (delivery pixels).
END_SLOTS = {'video_1': (150, 300, 900, 722), 'video_2': (1020, 300, 1770, 722),
             'subscribe': (960, 880, 118)}


def _paper_scene(k, hz):
    W, H = k.w, k.h
    k.vgrad(0, hz, PAPER, (250, 236, 204))
    k.glow(W / 2, hz, W * 0.62, GOLD_HI, 0.45)
    k.vgrad(hz, H, (232, 238, 238), (214, 226, 230))
    k.sea(hz + 3, H, a=0.28, n=12)
    k.rrect((0, hz - 1, W, hz + 1), 0, (*INK, 80))


def end_screen(guides=False):
    W, H = 1920, 1080
    k = K(W, H, PAPER)
    _paper_scene(k, 760)
    k.reflection(W / 2, 772, 1040, GOLD, 0.6, 9, 640)
    head = 'ಮುಂದೆ ಇದನ್ನೂ ನೋಡಿ'
    k.text(head, W / 2, 200, KN(76), INK, anchor='ms')
    k.rrect((W / 2 - 60, 228, W / 2 + 60, 236), 4, GOLD)
    for key in ('video_1', 'video_2'):
        x0, y0, x1, y1 = END_SLOTS[key]
        k.shadow((x0, y0, x1, y1), 18, blur=22, alpha=70, dy=12)
        k.rrect((x0 - 8, y0 - 8, x1 + 8, y1 + 8), 24, C.paper_0)
        k.rrect((x0, y0, x1, y1), 16, C.ink_800)
        play_icon(k, (x0 + x1) / 2 - 26, (y0 + y1) / 2, 60, (*C.paper_0, 90))
    cx, cy, r = END_SLOTS['subscribe']
    k.circle(cx, cy, r + 12, GOLD)
    k.circle(cx, cy, r + 4, C.paper_0)
    k.paste(logo('circle'), cx - r, cy - r, 2 * r, 2 * r)
    k.text('ಸಬ್‌ಸ್ಕ್ರೈಬ್ ಮಾಡಿ', cx - r - 40, cy + 16, KN(46), INK, anchor='rs')
    k.text(Brand.handle, cx + r + 40, cy + 14, LAT(40, 650), INK2, anchor='ls')
    img = k.finish()
    save(img, 'endscreen_1920x1080.png')
    if guides:
        g = img.copy()
        d = ImageDraw.Draw(g)
        f = font('latin', 30, 700)
        for key, v in END_SLOTS.items():
            if len(v) == 4:
                d.rectangle(v, outline=(255, 30, 120), width=4)
                d.text((v[0] + 14, v[1] + 10), key.upper() + ' element', font=f, fill=(255, 30, 120))
            else:
                d.ellipse([v[0] - v[2], v[1] - v[2], v[0] + v[2], v[1] + v[2]],
                          outline=(255, 30, 120), width=4)
        save(g, '_check_endscreen_slots.jpg', q=85)


# ─────────────────────────────────────────────────────────────────────────────
#  6 · live-stream cards  1920x1080 and an overlay for OBS / Streamyard
# ─────────────────────────────────────────────────────────────────────────────

def live_card(name, line1, line2):
    W, H = 1920, 1080
    k = K(W, H, PAPER)
    _paper_scene(k, 820)
    k.reflection(W / 2, 832, 1060, GOLD, 0.7, 8, 560)
    k.glow(W / 2, 400, 420, GOLD_HI, 0.35)
    k.paste(logo('cutout'), W / 2 - 245, 110, h=450)
    k.text(line1, W / 2, 692, KN(82), INK, anchor='ms')
    w = K.width(line2, KNV(42, 560))
    k.text(line2, W / 2, 776, KNV(42, 560), INK2, anchor='ms')
    k.rrect((W / 2 - w / 2, 802, W / 2 + w / 2, 806), 2, (*GOLD, 255))
    k.pill(W - 52 - K.width('ನೇರಪ್ರಸಾರ', KN(34)) - 44 - 25, 52, 'ನೇರಪ್ರಸಾರ',
           KN(34), RED, C.paper_0, h=60, dot=C.paper_0)
    save(k.finish(), name)


def live_overlay():
    """Transparent 1920x1080 for the streaming app: the mark and the live pill,
    top-left, clear of everything YouTube draws over a stream."""
    W, H = 1920, 1080
    k = K(W, H, (0, 0, 0, 0))
    k.shadow((44, 44, 44 + 132, 44 + 132), 66, blur=10, alpha=90, dy=4)
    k.paste(logo('circle'), 44, 44, 132, 132)
    k.pill(196, 80, 'ನೇರಪ್ರಸಾರ', KN(32), RED, C.paper_0, h=58, dot=C.paper_0)
    save(k.finish('RGBA'), 'live_overlay_1920x1080.png')


# ─────────────────────────────────────────────────────────────────────────────

SAMPLE = os.path.join(ROOT, 'Ganapathi Video', 'output',
                      'Ganapathi_Seneshwara_Photo_Retouched.jpg')


def build_all():
    print('ಊರ್ಮನಿ ಸುದ್ದಿ YouTube kit ->', os.path.relpath(OUT, ROOT))
    profile()
    banner(guides=True)
    watermark()
    end_screen(guides=True)
    live_card('live_starting_soon_1920x1080.png',
              'ನೇರಪ್ರಸಾರ ಸ್ವಲ್ಪ ಹೊತ್ತಿನಲ್ಲೇ ಆರಂಭ', Brand.tagline)
    live_card('live_be_right_back_1920x1080.png',
              'ಸ್ವಲ್ಪ ಹೊತ್ತಿನಲ್ಲೇ ಮರಳುತ್ತೇವೆ', Brand.tagline)
    live_card('live_thank_you_1920x1080.png',
              'ವೀಕ್ಷಿಸಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದ', 'ಸಬ್‌ಸ್ಕ್ರೈಬ್ ಮಾಡಿ  •  ' + Brand.handle)
    live_overlay()
    if os.path.exists(SAMPLE):
        thumbnail(SAMPLE, 'ಸೇನೇಶ್ವರ ಗಣಪತಿ ಪ್ರತಿಷ್ಠಾಪನೆ', 'ಬೈಂದೂರು',
                  focal=(0.45, 0.30),
                  out=os.path.join(OUT, 'thumbnail_sample_seneshwara.jpg'))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd')
    t = sub.add_parser('thumb', help='one video thumbnail from a real frame')
    t.add_argument('--photo', required=True)
    t.add_argument('--title', required=True, help='Kannada, 2–4 words is best')
    t.add_argument('--place', required=True)
    t.add_argument('--tag', help='optional second pill, e.g. ನೇರಪ್ರಸಾರ')
    t.add_argument('--focal', nargs=2, type=float, default=(0.5, 0.35),
                   help='x y of the subject in the photo, 0–1')
    t.add_argument('--no-highlight', action='store_true')
    t.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    if a.cmd == 'thumb':
        thumbnail(a.photo, a.title, a.place, a.tag, tuple(a.focal), a.out,
                  highlight_last=not a.no_highlight)
    else:
        build_all()


if __name__ == '__main__':
    main()
