"""
ಊರ್ಮನಿ ಸುದ್ದಿ — the YouTube channel kit, made from the logo.

    python3 scripts/youtube_kit.py                 # every asset, stills + motion -> assets/youtube/
    python3 scripts/youtube_kit.py --still         # stills only
    python3 scripts/youtube_kit.py thumb \\
        --photo frame.jpg --title "ಸೇನೇಶ್ವರ ಗಣಪತಿ ಪ್ರತಿಷ್ಠಾಪನೆ" \\
        --place "ಬೈಂದೂರು" [--tag "ನೇರಪ್ರಸಾರ"] [--focal 0.47 0.30] --out thumb.jpg

The look: deep ink, warm gold light, a metallic gold medallion around the
round logo — the logo's own sunset, lit like a studio. Sizes are YouTube's:
profile 800², banner 2560x1440 (phone-safe 1546x423), watermark 150²,
thumbnail 1280x720 under 2 MB, end screen and live cards 1920x1080.

Rules this file keeps, each one learned the hard way:
  * no decorative lines — no stripes, rules, streaks or underlines; light only
  * no claim the owner has not made — name, tagline, Karavali, Kannada, handle
  * gold is a fill, never type; red only on news elements (place, live)
  * text is centred on the letter BODY, not the full ink — Kannada subscripts
    hang far below the line and would drag a label out of its pill
  * nothing in the thumbnail's bottom-right, where YouTube puts the duration
"""
from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand.tokens import C, Brand                     # noqa: E402
from brand.typo import font                           # noqa: E402
from brand.surface import house_grade, cover          # noqa: E402
from brand.surface import medallion as surface_medallion, MEDALLION_PAD  # noqa: E402

OUT = os.path.join(ROOT, 'assets', 'youtube')
S = 2                                                 # supersample for stills

INK, INK_DEEP, INK_LIFT = C.ink_900, C.ink_950, C.ink_800
TEXT, TEXT_2 = C.paper_50, C.paper_300
GOLD = C.gold_500
RED = C.red_500

# Metallic stops: light catches the top, the body is the logo's sunset gold,
# the lower edge falls into shadow. Angle 90 = top to bottom.
GOLD_METAL = [(0.0, C.gold_300), (0.42, C.gold_400), (0.72, C.gold_500), (1.0, C.gold_600)]
RED_METAL = [(0.0, C.red_400), (1.0, C.red_600)]


# ─────────────────────────────────────────────────────────────────────────────
#  pixels
# ─────────────────────────────────────────────────────────────────────────────

def gradient(w, h, stops, angle=90):
    """An RGB gradient along `angle` degrees through the given colour stops."""
    a = math.radians(angle)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = xx * math.cos(a) + yy * math.sin(a)
    t = (t - t.min()) / max(1e-6, t.max() - t.min())
    pos = np.array([p for p, _ in stops], np.float32)
    out = np.zeros((h, w, 3), np.float32)
    for ch in range(3):
        out[..., ch] = np.interp(t, pos, np.array([c[ch] for _, c in stops], np.float32))
    out += np.random.default_rng(11).uniform(-.7, .7, (h, w))[..., None]   # no banding
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB')


def glow_layer(w, h, cx, cy, rx, ry, color, a, power=2.0):
    """A soft elliptical light — the only 'decoration' this brand allows."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    al = np.clip(1 - d, 0, 1) ** power * a * 255
    lay = np.zeros((h, w, 4), np.float32)
    lay[..., :3] = color
    lay[..., 3] = al
    return Image.fromarray(lay.astype(np.uint8), 'RGBA')


def vignette(img, amount=0.35):
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    v = 1 - np.clip((d - 0.55) / 0.9, 0, 1) ** 1.6 * amount
    a = np.asarray(img).astype(np.float32)
    a[..., :3] *= v[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), img.mode)


def grain(img, sigma=1.8, seed=2026):
    a = np.asarray(img).astype(np.float32)
    n = np.random.default_rng(seed).normal(0, sigma, a.shape[:2])
    lum = a[..., :3].mean(2) / 255
    a[..., :3] += (n * (1.15 - lum * 0.6))[..., None]     # more in the shadows, like film
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), img.mode)


def ink_scene(w, h, light=None, sea=None, warmth=1.0):
    """The stage: ink deepening to near-black, warm gold light from `light`
    (x, y, rx, ry), a cool sea-blue depth from `sea`, film grain, vignette."""
    top = np.array(INK_LIFT, np.float32)
    bot = np.array(INK_DEEP, np.float32)
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    a = top * (1 - t) + bot * t
    a = np.repeat(a, w, 1)
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    if sea:
        sx, sy, srx, sry = sea
        img.alpha_composite(glow_layer(w, h, sx, sy, srx, sry, C.sea_600, 0.55, 1.6))
    if light:
        lx, ly, lrx, lry = light
        # gold, never amber: amber over navy goes brown, and brown reads cheap
        img.alpha_composite(glow_layer(w, h, lx, ly, lrx, lry, C.gold_600, 0.16 * warmth, 1.7))
        img.alpha_composite(glow_layer(w, h, lx, ly, lrx * 0.5, lry * 0.5, GOLD, 0.22 * warmth, 2.0))
    return vignette(img, 0.42)


# ─────────────────────────────────────────────────────────────────────────────
#  canvas
# ─────────────────────────────────────────────────────────────────────────────

class K:
    """A supersampled RGBA canvas; every coordinate is in delivery pixels."""

    def __init__(self, w, h, bg=None, ss=S):
        self.w, self.h, self.ss = w, h, ss
        if isinstance(bg, Image.Image):
            self.img = bg.convert('RGBA').resize((w * ss, h * ss), Image.Resampling.BICUBIC)
        else:
            bg = bg or (0, 0, 0, 0)
            self.img = Image.new('RGBA', (w * ss, h * ss), bg if len(bg) == 4 else (*bg, 255))

    def lay(self):
        return Image.new('RGBA', self.img.size, (0, 0, 0, 0))

    # shapes ------------------------------------------------------------------
    def _mask(self, box, r):
        s = self.ss
        x0, y0, x1, y1 = box
        w, h = int(round((x1 - x0) * s)), int(round((y1 - y0) * s))
        m = Image.new('L', (w, h), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r * s, fill=255)
        return m, (int(round(x0 * s)), int(round(y0 * s)))

    def fill(self, box, r, color=None, stops=None, angle=90, alpha=1.0, sheen=False):
        """A rounded shape filled flat or with a metallic gradient."""
        m, at = self._mask(box, r)
        if stops:
            src = gradient(m.width, m.height, stops, angle).convert('RGBA')
        else:
            src = Image.new('RGBA', m.size, (*color[:3], 255))
        a = color[3] / 255 if color and len(color) == 4 else 1.0
        src.putalpha(m.point(lambda v: int(v * a * alpha)))
        self.img.alpha_composite(src, at)
        if sheen:
            # light on the upper half of a metal surface, soft-edged
            hgt = m.height
            sh = np.zeros((hgt, m.width), np.float32)
            ramp = np.clip(1 - np.linspace(0, 1, hgt) / 0.55, 0, 1) ** 2 * 0.28
            sh[:] = ramp[:, None]
            al = (sh * np.asarray(m, np.float32)).astype(np.uint8)
            lay = Image.new('RGBA', m.size, (255, 255, 255, 0))
            lay.putalpha(Image.fromarray(al, 'L'))
            self.img.alpha_composite(lay, at)

    def shadow(self, box, r, blur=24, alpha=110, dy=12, color=None):
        s = self.ss
        x0, y0, x1, y1 = box
        lay = self.lay()
        ImageDraw.Draw(lay).rounded_rectangle(
            [x0 * s, (y0 + dy) * s, x1 * s, (y1 + dy) * s], r * s,
            fill=(*(color or C.ink_950), alpha))
        self.img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur * s)))

    def light(self, cx, cy, rx, ry, color, a, power=2.0):
        s = self.ss
        self.img.alpha_composite(glow_layer(self.img.width, self.img.height,
                                            cx * s, cy * s, rx * s, ry * s, color, a, power))

    # type --------------------------------------------------------------------
    def text(self, s_, x, base, f, fill, anchor='ls', shadow=None):
        s = self.ss
        fs = font(*f[:1], int(f[1] * s), *f[2:])
        if shadow:
            dx, dy, blur, col = shadow
            lay = self.lay()
            ImageDraw.Draw(lay).text(((x + dx) * s, (base + dy) * s), s_, font=fs,
                                     fill=col, anchor=anchor)
            self.img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur * s)))
        if len(fill) == 4:
            lay = self.lay()
            ImageDraw.Draw(lay).text((x * s, base * s), s_, font=fs, fill=fill, anchor=anchor)
            self.img.alpha_composite(lay)
        else:
            ImageDraw.Draw(self.img).text((x * s, base * s), s_, font=fs, fill=fill,
                                          anchor=anchor)

    @staticmethod
    def width(s_, f):
        fs = font(*f[:1], int(f[1] * S), *f[2:])
        return ImageDraw.Draw(Image.new('L', (8, 8))).textlength(s_, font=fs) / S

    @staticmethod
    def ink(s_, f):
        """(rise above baseline, drop below) of the real ink."""
        fs = font(*f[:1], int(f[1] * S), *f[2:])
        b = ImageDraw.Draw(Image.new('L', (8, 8))).textbbox((0, 0), s_, font=fs, anchor='ls')
        return -b[1] / S, b[3] / S

    @staticmethod
    def centre_base(cy, s_, f):
        """The baseline that centres a line on `cy` by its letter BODY. A
        subscript (್ರೈ ್ದಿ) hangs far below the line; centring on the full ink
        drags the word up out of its pill. The eye centres the body: ಕ or x."""
        ref = 'ಕ' if any('ಀ' <= ch <= '೿' for ch in s_) else 'x'
        r, d = K.ink(ref, f)
        return cy + (r - d) / 2

    def pill(self, x, y, s_, f, h, color, fill=None, stops=None, padx=26, dot=None,
             sheen=False):
        """A label on a rounded fill, centred on its letter body. Returns right edge."""
        w = self.width(s_, f) + padx * 2 + (h * 0.40 if dot else 0)
        self.fill((x, y, x + w, y + h), h / 2, fill, stops, sheen=sheen)
        tx = x + padx
        if dot:
            r = h * 0.12
            self.fill((tx, y + h / 2 - r, tx + 2 * r, y + h / 2 + r), r, dot)
            tx += h * 0.40
        self.text(s_, tx, self.centre_base(y + h / 2, s_, f), f, color)
        return x + w

    # images ------------------------------------------------------------------
    def paste(self, im, x, y, w=None, h=None):
        s = self.ss
        im = im.convert('RGBA')
        if w and not h:
            h = w * im.height / im.width
        if h and not w:
            w = h * im.width / im.height
        im = im.resize((int(round(w * s)), int(round(h * s))), Image.Resampling.LANCZOS)
        self.img.alpha_composite(im, (int(round(x * s)), int(round(y * s))))
        return w, h

    def finish(self, mode='RGB', grain_sigma=0.0):
        out = self.img.resize((self.w, self.h), Image.Resampling.LANCZOS)
        if grain_sigma:
            out = grain(out, grain_sigma)
        return out if mode == 'RGBA' else out.convert('RGB')


# fonts: (family, size[, weight])
KN = lambda s: ('kn', s)                               # noqa: E731
KNV = lambda s, w=600: ('kn_var', s, w)                # noqa: E731
LAT = lambda s, w=600: ('latin', s, w)                 # noqa: E731


def logo(variant='circle'):
    name = {'cutout': 'oormani_suddi_logo_cutout_bg_erased.png',
            'circle': 'logo_clean_circle.png'}[variant]
    im = Image.open(os.path.join(ROOT, 'assets', name)).convert('RGBA')
    return im.crop(im.getbbox())


def medallion(d, glow=True):
    """The house medallion (brand/surface.py, D128) — the same mark the posts
    and reels carry — on ink: a warm halo, an ink bezel. (d * 1.5)² RGBA."""
    return surface_medallion(int(round(d)), halo=0.30 if glow else 0.0, shadow=0.67,
                             bezel=INK_DEEP)


def ring_mask(d):
    """The ring of medallion(d) as an L mask at the same scale and frame — the
    path the light travels in the motion pieces."""
    pad = d * MEDALLION_PAD
    size = int(round(d + 2 * pad))
    c = size / 2
    ring_w = d * 0.045
    m = Image.new('L', (size, size), 0)
    dr = ImageDraw.Draw(m)
    dr.ellipse([c - d / 2, c - d / 2, c + d / 2, c + d / 2], fill=255)
    dr.ellipse([c - d / 2 + ring_w, c - d / 2 + ring_w, c + d / 2 - ring_w, c + d / 2 - ring_w], fill=0)
    return m


def place_medallion(k, cx, cy, d):
    md = medallion(d)
    k.paste(md, cx - md.width / 2, cy - md.height / 2, md.width, md.height)


def play_icon(k, x, cy, h, color):
    s = k.ss
    lay = k.lay()
    ImageDraw.Draw(lay).polygon(
        [(x * s, (cy - h / 2) * s), ((x + h * 0.88) * s, cy * s), (x * s, (cy + h / 2) * s)],
        fill=color)
    k.img.alpha_composite(lay)


def subscribe_button(k, x, cy, h=72, size=36):
    """Metallic gold button, ink play-disc, Kannada call to action. Returns right edge."""
    sub = 'ಸಬ್‌ಸ್ಕ್ರೈಬ್ ಮಾಡಿ'
    f = KN(size)
    disc = h * 0.62
    bw = h / 2 - disc / 2 + disc + 20 + K.width(sub, f) + 34
    y = cy - h / 2
    k.shadow((x, y, x + bw, y + h), h / 2, blur=18, alpha=150, dy=10)
    k.light(x + bw / 2, cy, bw * 0.75, h * 1.6, GOLD, 0.10)
    k.fill((x, y, x + bw, y + h), h / 2, stops=GOLD_METAL, sheen=True)
    dx = x + (h - disc) / 2
    k.fill((dx, cy - disc / 2, dx + disc, cy + disc / 2), disc / 2, INK)
    play_icon(k, dx + disc * 0.38, cy, disc * 0.42, C.gold_400)
    k.text(sub, dx + disc + 20, K.centre_base(cy, sub, f), f, INK)
    return x + bw


def save(img, name, **kw):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    if p.endswith('.jpg'):
        img.save(p, 'JPEG', quality=kw.get('q', 94), subsampling=0, optimize=True)
    else:
        img.save(p, optimize=True)
    print(f'  {os.path.relpath(p, ROOT)}  {img.width}x{img.height}  '
          f'{os.path.getsize(p) // 1024} KB')
    return p


# ─────────────────────────────────────────────────────────────────────────────
#  1 · profile picture  800x800 — the logo itself; YouTube crops a circle
# ─────────────────────────────────────────────────────────────────────────────

def profile():
    k = K(800, 800, C.paper_50)
    k.paste(logo('circle'), 0, 0, 800, 800)
    save(k.finish(), 'profile_800.png')


# ─────────────────────────────────────────────────────────────────────────────
#  2 · banner  2560x1440 · TV sees all, desktop the middle 2560x423, phones
#      only the centre 1546x423 — everything that matters lives there
# ─────────────────────────────────────────────────────────────────────────────

SAFE = (507, 508, 2053, 931)


def banner(guides=False):
    W, H = 2560, 1440
    cy = (SAFE[1] + SAFE[3]) / 2
    d = 392                                           # medallion fits the strip
    mx = SAFE[0] + 40 + d / 2 + 10
    bg = ink_scene(W, H, light=(mx, cy + 40, 1150, 760), sea=(W * 0.92, H * 0.15, 1100, 800))
    k = K(W, H, bg)
    place_medallion(k, mx, cy, d)

    x = mx + d / 2 + 84
    maxw = SAFE[2] - 24 - x
    head = 'ಕರಾವಳಿಯ ಊರಿನ ಸುದ್ದಿ'
    hs = 104
    while K.width(head, KN(hs)) > maxw and hs > 60:
        hs -= 2
    rise, drop = K.ink(head, KN(hs))
    ph, bh, gap = 54, 74, 40
    block = ph + gap + rise + drop + gap + bh
    y = cy - block / 2
    k.pill(x, y, Brand.coverage + '  •  ಕನ್ನಡ', KNV(31, 640), ph, TEXT,
           fill=(255, 255, 255, 26))
    hb = y + ph + gap + rise
    k.text(head, x - 4, hb, KN(hs), TEXT, shadow=(0, 8, 18, (*INK_DEEP, 200)))
    bcy = hb + drop + gap + bh / 2
    right = subscribe_button(k, x, bcy, bh, 36)
    k.text(Brand.handle, right + 32, K.centre_base(bcy, 'x', LAT(36, 560)),
           LAT(36, 560), TEXT_2)
    img = k.finish(grain_sigma=1.6)
    save(img, 'banner_2560x1440.jpg')
    if guides:
        g = img.copy().convert('RGBA')
        dr = ImageDraw.Draw(g)
        dr.rectangle([0, 508, W, 931], outline=(80, 160, 255), width=4)
        dr.rectangle(SAFE, outline=(255, 60, 140), width=5)
        f = font('latin', 34, 700)
        dr.text((20, 466), 'DESKTOP 2560x423', font=f, fill=(80, 160, 255))
        dr.text((SAFE[0] + 10, SAFE[3] + 12), 'PHONE / SAFE 1546x423', font=f, fill=(255, 60, 140))
        dr.text((20, 20), 'TV 2560x1440', font=f, fill=(255, 255, 255))
        save(g.convert('RGB'), '_check_banner_safe_areas.jpg', q=85)


# ─────────────────────────────────────────────────────────────────────────────
#  3 · video watermark  150x150 transparent (Studio > Branding)
# ─────────────────────────────────────────────────────────────────────────────

def watermark():
    k = K(150, 150)
    k.paste(logo('circle'), 0, 0, 150, 150)
    save(k.finish('RGBA'), 'watermark_150.png')


# ─────────────────────────────────────────────────────────────────────────────
#  4 · thumbnail  1280x720
# ─────────────────────────────────────────────────────────────────────────────

def thumbnail(photo, title, place, tag=None, focal=(0.5, 0.35), out=None,
              highlight_last=True):
    W, H = 1280, 720
    px = 455                                           # the photograph starts here
    bg = ink_scene(W, H, light=(170, 380, 620, 520))
    k = K(W, H, bg)
    ph = Image.open(photo).convert('RGB')
    ph = house_grade(cover(ph, (W - px) * S, H * S, focal), strength=0.85)
    ph = vignette(ph.convert('RGBA'), 0.30)
    # dissolve the photograph into the ink — smoothstep, the join cannot be found
    u = np.linspace(0, 1, 320 * S)
    t = u * u * (3 - 2 * u)
    al = np.ones((ph.height, ph.width), np.float32)
    al[:, :320 * S] = t[None, :]
    ph.putalpha(Image.fromarray((al * 255).astype(np.uint8), 'L'))
    k.img.alpha_composite(ph, (px * S, 0))

    x, top = 56, 56
    ph_h = 62
    xe = k.pill(x, top, place, KN(34), ph_h, C.paper_0, stops=RED_METAL, padx=24)
    if tag:
        k.pill(xe + 14, top, tag, KN(34), ph_h, RED, fill=C.paper_0, dot=RED, padx=22)

    # title: 1–3 lines, as large as fits, centred on the real ink between
    # the place pill and the mark, the last line on metallic gold
    words = title.split()
    pad, gap, maxw = 20, 36, 640
    area = (top + ph_h + gap, H - 168 - gap)

    def plan(size):
        f = KN(size)
        lines, cur = [], ''
        for w in words:
            t_ = (cur + ' ' + w).strip()
            if K.width(t_, f) <= maxw or not cur:
                cur = t_
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        lh = size * 1.22
        boxed = highlight_last and len(lines) > 1
        top_ = -K.ink(lines[0], f)[0]
        bot_ = (len(lines) - 1) * lh + K.ink(lines[-1], f)[1] + (pad if boxed else 0)
        return f, lines, lh, boxed, top_, bot_

    for size in range(136, 60, -4):
        f, lines, lh, boxed, top_, bot_ = plan(size)
        if len(lines) <= 3 and max(K.width(l, f) for l in lines) <= maxw + 40 \
                and bot_ - top_ <= area[1] - area[0]:
            break
    y0 = (area[0] + area[1]) / 2 - (top_ + bot_) / 2
    k.light(x + 260, y0 + (top_ + bot_) / 2, 420, 260, GOLD, 0.10)
    for i, line in enumerate(lines):
        rise, drop = K.ink(line, f)
        base = y0 + i * lh
        if boxed and i == len(lines) - 1:
            lw_ = K.width(line, f)
            box = (x, base - rise - pad, x + lw_ + 2 * pad, base + drop + pad)
            k.shadow(box, 14, blur=16, alpha=160, dy=10)
            k.fill(box, 14, stops=GOLD_METAL, sheen=True)
            k.text(line, x + pad, base, f, INK)
        else:
            k.text(line, x, base, f, C.paper_0, shadow=(0, 6, 14, (*INK_DEEP, 230)))

    # the mark, bottom-left — bottom-right is YouTube's duration badge
    d = 116
    place_medallion(k, x + d / 2, H - 56 - d / 2, d)
    k.text(Brand.handle, x + d + 20, K.centre_base(H - 56 - d / 2, 'x', LAT(30, 600)),
           LAT(30, 600), C.paper_100)
    img = k.finish(grain_sigma=1.2)
    out = out or os.path.join(OUT, 'thumbnail.jpg')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    q = 93
    while True:
        img.save(out, 'JPEG', quality=q, subsampling=0, optimize=True)
        if os.path.getsize(out) < 1_900_000 or q < 60:
            break
        q -= 5
    print(f'  {os.path.relpath(out, ROOT)}  {W}x{H}  {os.path.getsize(out) // 1024} KB')
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  5 · end screen  1920x1080 — the last 20 s of every long video
# ─────────────────────────────────────────────────────────────────────────────

# Where to drop the elements in Studio > End screen (delivery pixels).
END_SLOTS = {'video_1': (150, 292, 900, 714), 'video_2': (1020, 292, 1770, 714),
             'subscribe': (960, 880, 112)}
END_HEAD = 'ಮುಂದೆ ಇದನ್ನೂ ನೋಡಿ'


def end_scene():
    W, H = 1920, 1080
    return ink_scene(W, H, light=(W / 2, 940, 1100, 520), sea=(W * 0.05, 0, 900, 700))


def end_layers():
    """The end screen as separate layers, so the still and the motion piece
    are the same picture: (background, heading, [card, card], medallion+labels)."""
    W, H = 1920, 1080
    head = K(W, H)
    head.text(END_HEAD, W / 2, 196, KN(72), TEXT, anchor='ms',
              shadow=(0, 6, 16, (*INK_DEEP, 220)))
    cards = []
    for key in ('video_1', 'video_2'):
        x0, y0, x1, y1 = END_SLOTS[key]
        c = K(W, H)
        c.shadow((x0, y0, x1, y1), 22, blur=30, alpha=190, dy=18)
        # a raised panel, lit from above — no rim, no outline
        c.fill((x0, y0, x1, y1), 22, stops=[(0, C.ink_700), (1, C.ink_850)])
        play_icon(c, (x0 + x1) / 2 - 24, (y0 + y1) / 2, 56, (*C.paper_0, 60))
        cards.append(c)
    cx, cy, r = END_SLOTS['subscribe']
    m = K(W, H)
    place_medallion(m, cx, cy, 2 * r / 0.9)            # the logo disc ≈ the element
    lab = 'ಸಬ್‌ಸ್ಕ್ರೈಬ್ ಮಾಡಿ'
    m.text(lab, cx - r - 58, K.centre_base(cy, lab, KN(44)), KN(44), TEXT, anchor='rs')
    m.text(Brand.handle, cx + r + 58, K.centre_base(cy, 'ಕ', KN(44)), LAT(38, 600), TEXT_2,
           anchor='ls')
    return end_scene(), head, cards, m


def end_screen(guides=False):
    bg, head, cards, m = end_layers()
    k = K(1920, 1080, bg)
    for lay in (head, *cards, m):
        k.img.alpha_composite(lay.img)
    img = k.finish(grain_sigma=1.2)
    save(img, 'endscreen_1920x1080.png')
    if guides:
        g = img.copy()
        d = ImageDraw.Draw(g)
        f = font('latin', 30, 700)
        for key, v in END_SLOTS.items():
            if len(v) == 4:
                d.rectangle(v, outline=(255, 60, 140), width=4)
                d.text((v[0] + 14, v[1] + 10), key.upper() + ' element', font=f, fill=(255, 60, 140))
            else:
                d.ellipse([v[0] - v[2], v[1] - v[2], v[0] + v[2], v[1] + v[2]],
                          outline=(255, 60, 140), width=4)
        save(g, '_check_endscreen_slots.jpg', q=85)


# ─────────────────────────────────────────────────────────────────────────────
#  6 · live-stream cards  1920x1080, and an overlay for the streaming app
# ─────────────────────────────────────────────────────────────────────────────

LIVE = 'ನೇರಪ್ರಸಾರ'
LIVE_CARDS = {
    'live_starting_soon': ('ನೇರಪ್ರಸಾರ ಸ್ವಲ್ಪ ಹೊತ್ತಿನಲ್ಲೇ ಆರಂಭ', Brand.tagline),
    'live_be_right_back': ('ಸ್ವಲ್ಪ ಹೊತ್ತಿನಲ್ಲೇ ಮರಳುತ್ತೇವೆ', Brand.tagline),
    'live_thank_you': ('ವೀಕ್ಷಿಸಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದ', 'ಸಬ್‌ಸ್ಕ್ರೈಬ್ ಮಾಡಿ  •  ' + Brand.handle),
}
CARD_MED = (960, 425, 470)                             # cx, cy, d


def card_scene():
    return ink_scene(1920, 1080, light=(960, 400, 1000, 700), sea=(1920, 1080, 1000, 700))


def card_text_layer(line1, line2, with_pill=True):
    W, H = 1920, 1080
    k = K(W, H)
    k.text(line1, W / 2, 822, KN(80), TEXT, anchor='ms', shadow=(0, 8, 18, (*INK_DEEP, 220)))
    f2 = KNV(40, 560) if any('ಀ' <= ch <= '೿' for ch in line2) else LAT(38, 560)
    k.text(line2, W / 2, 898, f2, TEXT_2, anchor='ms')
    if with_pill:
        w = K.width(LIVE, KN(32)) + 2 * 24 + 60 * 0.40
        k.pill(W - 56 - w, 56, LIVE, KN(32), 60, C.paper_0, stops=RED_METAL, padx=24,
               dot=C.paper_0)
    return k


def live_card(name, line1, line2):
    k = K(1920, 1080, card_scene())
    place_medallion(k, *CARD_MED)
    k.img.alpha_composite(card_text_layer(line1, line2).img)
    save(k.finish(grain_sigma=1.2), name + '_1920x1080.png')


def live_overlay():
    """Transparent 1920x1080: the medallion and the live pill, top-left, clear
    of everything YouTube draws over a stream."""
    k = K(1920, 1080)
    d = 132
    place_medallion(k, 48 + d / 2, 48 + d / 2, d)
    k.pill(48 + d + 18, 48 + d / 2 - 30, LIVE, KN(32), 60, C.paper_0, stops=RED_METAL,
           padx=22, dot=C.paper_0)
    save(k.finish('RGBA'), 'live_overlay_1920x1080.png')


# ─────────────────────────────────────────────────────────────────────────────
#  7 · motion — channel intro, end screen, live loop  (1920x1080, 30 fps)
# ─────────────────────────────────────────────────────────────────────────────

FPS = 30


def ease_out(t, p=4):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** p


def ease_in_out(t):
    t = min(1.0, max(0.0, t))
    return t * t * t * (t * (t * 6 - 15) + 10)            # smootherstep


def span(t, a, b):
    return min(1.0, max(0.0, (t - a) / (b - a)))


def put(frame, layer, cx, cy, scale=1.0, alpha=1.0, dy=0.0):
    """Composite `layer` centred on (cx, cy + dy) at `scale`, sub-pixel exact."""
    if alpha <= 0.002:
        return
    w, h = layer.size
    sw, sh = w * scale, h * scale
    x0, y0 = math.floor(cx - sw / 2), math.floor(cy + dy - sh / 2)
    ow, oh = int(math.ceil(sw)) + 2, int(math.ceil(sh)) + 2
    inv = 1 / scale
    ox = (x0 - (cx - sw / 2)) * inv
    oy = (y0 - (cy + dy - sh / 2)) * inv
    t = layer.transform((ow, oh), Image.Transform.AFFINE, (inv, 0, ox, 0, inv, oy),
                        resample=Image.Resampling.BICUBIC)
    if alpha < 0.998:
        a = t.getchannel('A').point(lambda v: int(v * alpha))
        t.putalpha(a)
    frame.alpha_composite(t, (x0, y0))


def sheen(mask, phase, width=0.16, strength=0.85):
    """A band of light travelling diagonally across `mask` — a glint on metal.
    phase 0..1 carries it from top-left to bottom-right."""
    w, h = mask.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = (xx / w + yy / h) / 2                              # 0 top-left .. 1 bottom-right
    centre = -0.2 + 1.4 * phase
    band = np.exp(-((u - centre) / width) ** 2) * strength
    al = band * np.asarray(mask, np.float32)
    lay = Image.new('RGBA', (w, h), (255, 244, 214, 0))
    lay.putalpha(Image.fromarray(np.clip(al, 0, 255).astype(np.uint8), 'L'))
    return lay


class Encoder:
    def __init__(self, path, w=1920, h=1080, audio=None, dur=None):
        self.path = path
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
               '-s', f'{w}x{h}', '-r', str(FPS), '-i', '-']
        if audio:
            cmd += audio
        cmd += ['-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p',
                '-profile:v', 'high', '-movflags', '+faststart']
        if audio:
            cmd += ['-c:a', 'aac', '-b:a', '192k', '-ar', '48000']
        if dur:
            cmd += ['-t', f'{dur:.3f}']
        cmd += [path]
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def write(self, img):
        # grain that moves, as film does — a fixed pattern reads as a dirty screen
        self.n = getattr(self, 'n', 0) + 1
        self.p.stdin.write(grain(img.convert('RGB'), 1.1, seed=self.n).tobytes())

    def close(self):
        self.p.stdin.close()
        self.p.wait()
        print(f'  {os.path.relpath(self.path, ROOT)}  {os.path.getsize(self.path) // 1024} KB')


def sfx(*cues):
    """ffmpeg audio inputs + mix for (file, start_s, gain_db) cues — the
    house's own sound effects, cleared in assets/LICENCES.json."""
    args, labels = [], []
    for i, (f, at, db) in enumerate(cues):
        args += ['-i', os.path.join(ROOT, 'assets', 'sfx', f)]
        ms = int(at * 1000)
        labels.append(f'[{i + 1}:a]adelay={ms}|{ms},volume={db}dB[a{i}]')
    mix = ';'.join(labels) + ';' + ''.join(f'[a{i}]' for i in range(len(cues))) + \
        f'amix=inputs={len(cues)}:normalize=0,alimiter=limit=0.89[aout]'
    return args + ['-filter_complex', mix, '-map', '0:v', '-map', '[aout]']


def intro():
    """4 s channel intro: light rises, the medallion arrives, a glint runs
    round the ring, the name settles, a breath, out."""
    W, H, dur = 1920, 1080, 4.0
    bg = ink_scene(W, H, light=(W / 2, 470, 1000, 720), sea=(W, H, 1100, 760)).convert('RGBA')
    dark = Image.new('RGBA', (W, H), (*INK_DEEP, 255))
    d = 440
    med = medallion(d)
    mask = ring_mask(d).resize(med.size, Image.Resampling.LANCZOS)
    name = K(W, H)
    name.text(Brand.name, W / 2, 0 + 128, KN(112), TEXT, anchor='ms',
              shadow=(0, 8, 20, (*INK_DEEP, 230)))
    name_l = name.finish('RGBA').crop((0, 0, W, 190))
    tag = K(W, 120)
    tag.text(Brand.tagline, W / 2, 70, KNV(44, 560), TEXT_2, anchor='ms')
    tag_l = tag.finish('RGBA')
    cy_med = 430
    enc = Encoder(os.path.join(OUT, 'motion_intro_1920x1080.mp4'),
                  audio=sfx(('whoosh.wav', 0.15, -6), ('open.wav', 0.85, -4)), dur=dur)
    for i in range(int(dur * FPS)):
        t = i / FPS
        fr = Image.blend(dark, bg, ease_in_out(span(t, 0.0, 0.9)))
        a_m = ease_out(span(t, 0.25, 1.15), 3)
        put(fr, med, W / 2, cy_med, 0.86 + 0.14 * ease_out(span(t, 0.25, 1.45), 4), a_m)
        g = span(t, 1.05, 2.05)
        if 0 < g < 1:
            gl = sheen(mask, ease_in_out(g))
            put(fr, gl, W / 2, cy_med, 1.0, math.sin(math.pi * g))
        put(fr, name_l, W / 2, 790 - 128 + name_l.height / 2,
            1.0, ease_out(span(t, 1.15, 1.95), 3), dy=26 * (1 - ease_out(span(t, 1.15, 2.1), 4)))
        put(fr, tag_l, W / 2, 870, 1.0, ease_out(span(t, 1.5, 2.3), 3),
            dy=18 * (1 - ease_out(span(t, 1.5, 2.45), 4)))
        out = span(t, 3.45, 4.0)
        if out > 0:
            fr = Image.blend(fr, dark, ease_in_out(out))
        enc.write(fr)
    enc.close()


def end_motion():
    """20 s end screen: the same picture as the still, built in over the first
    second, then a slow breathing light so it never looks frozen. Every element
    is in its final place by 1.2 s — YouTube's end-screen boxes sit on top."""
    W, H, dur = 1920, 1080, 20.0
    bg, head, cards, m = end_layers()
    bg = bg.convert('RGBA')
    lit = bg.copy()
    lit.alpha_composite(glow_layer(W, H, W / 2, 940, 900, 420, GOLD, 0.10, 1.8))
    head_l = head.finish('RGBA')
    card_l = [c.finish('RGBA') for c in cards]
    m_l = m.finish('RGBA')
    enc = Encoder(os.path.join(OUT, 'motion_endscreen_1920x1080.mp4'),
                  audio=sfx(('whoosh.wav', 0.0, -12)), dur=dur)
    for i in range(int(dur * FPS)):
        t = i / FPS
        breath = 0.5 - 0.5 * math.cos(2 * math.pi * t / 8.0)
        fr = Image.blend(bg, lit, breath)
        put(fr, head_l, W / 2, H / 2, 1.0, ease_out(span(t, 0.0, 0.6), 3),
            dy=-14 * (1 - ease_out(span(t, 0.0, 0.7), 4)))
        for j, cl in enumerate(card_l):
            a0 = 0.12 + j * 0.12
            put(fr, cl, W / 2, H / 2, 1.0, ease_out(span(t, a0, a0 + 0.6), 3),
                dy=30 * (1 - ease_out(span(t, a0, a0 + 0.8), 4)))
        put(fr, m_l, W / 2, H / 2, 1.0, ease_out(span(t, 0.4, 1.0), 3),
            dy=22 * (1 - ease_out(span(t, 0.4, 1.2), 4)))
        enc.write(fr)
    enc.close()


def live_loop():
    """10 s seamless loop for before a stream: the light breathes, a glint
    runs round the ring once, the live dot pulses. Frame 0 = frame 300."""
    W, H, dur = 1920, 1080, 10.0
    line1, line2 = LIVE_CARDS['live_starting_soon']
    bg = card_scene().convert('RGBA')
    lit = bg.copy()
    lit.alpha_composite(glow_layer(W, H, 960, 400, 760, 560, GOLD, 0.12, 1.8))
    cx, cy, d = CARD_MED
    med = medallion(d)
    mask = ring_mask(d).resize(med.size, Image.Resampling.LANCZOS)
    txt = card_text_layer(line1, line2).finish('RGBA')
    w_p = K.width(LIVE, KN(32)) + 2 * 24 + 60 * 0.40
    dot_x, dot_y, dot_r = W - 56 - w_p + 24 + 60 * 0.12, 56 + 30, 60 * 0.12
    red_dot = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    ImageDraw.Draw(red_dot).ellipse([2, 2, 61, 61], fill=(*C.red_500, 255))
    red_dot = red_dot.resize((int(dot_r * 2 + 3), int(dot_r * 2 + 3)), Image.Resampling.LANCZOS)
    enc = Encoder(os.path.join(OUT, 'motion_live_starting_soon_loop_1920x1080.mp4'), dur=dur)
    for i in range(int(dur * FPS)):
        t = i / FPS
        breath = 0.5 - 0.5 * math.cos(2 * math.pi * t / dur)
        fr = Image.blend(bg, lit, breath)
        put(fr, med, cx, cy, 1.0 + 0.012 * breath)
        g = span(t, 3.0, 4.6)
        if 0 < g < 1:
            put(fr, sheen(mask, ease_in_out(g)), cx, cy, 1.0 + 0.012 * breath,
                math.sin(math.pi * g))
        fr.alpha_composite(txt)
        # the live dot breathes: covered by the pill's red, then uncovered
        pulse = 0.5 - 0.5 * math.cos(2 * math.pi * t / 1.25)
        put(fr, red_dot, dot_x + dot_r, dot_y, 1.0, 0.9 * pulse)
        enc.write(fr)
    enc.close()


# ─────────────────────────────────────────────────────────────────────────────

SAMPLE = os.path.join(ROOT, 'Ganapathi Video', 'output',
                      'Ganapathi_Seneshwara_Photo_Retouched.jpg')


def build_all(still=False):
    print('ಊರ್ಮನಿ ಸುದ್ದಿ YouTube kit ->', os.path.relpath(OUT, ROOT))
    profile()
    banner(guides=True)
    watermark()
    end_screen(guides=True)
    for name, (l1, l2) in LIVE_CARDS.items():
        live_card(name, l1, l2)
    live_overlay()
    if os.path.exists(SAMPLE):
        thumbnail(SAMPLE, 'ಸೇನೇಶ್ವರ ಗಣಪತಿ ಪ್ರತಿಷ್ಠಾಪನೆ', 'ಬೈಂದೂರು', focal=(0.45, 0.30),
                  out=os.path.join(OUT, 'thumbnail_sample_seneshwara.jpg'))
    if not still:
        intro()
        end_motion()
        live_loop()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--still', action='store_true', help='skip the motion pieces')
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
        build_all(a.still)


if __name__ == '__main__':
    main()
