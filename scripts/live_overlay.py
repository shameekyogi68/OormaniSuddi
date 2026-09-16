#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — YouTube Live overlay
===================================
Builds the stream background from the team's format file.

The team's `LIVE BG.png` is a 1920×1080 overlay: fully transparent above, where
the camera and screen show through, and a solid maroon band along the bottom,
reserved for partner and donor logos. There are no partners yet, so the band
markets the channel itself.

THE FORMAT IS READ, NOT RE-TYPED.  The band's height and colour are measured
from the team's file on every run, so if they move the band the overlay
follows. Everything above the band is forced to alpha 0 — exactly the
transparency they sent — so nothing here can ever creep over the picture.

DESIGNED FOR A PHONE.  Most of this stream will be watched on a phone, where
1920px plays about 400px wide and every pixel of type shrinks by almost five.
So the band carries few words, set large: the brand, one call to action, the
handle. Anything smaller would be decoration nobody can read.

"LIVE" IS NOT BAKED IN.  YouTube keeps the recording after the stream ends, and
a "ನೇರ ಪ್ರಸಾರ" painted into the background would still be claiming to be live on
the replay — the same kind of unearned assertion this project refuses for
ಬ್ರೇಕಿಂಗ್. YouTube marks the stream live itself and switches that to a replay
automatically. The badge is still provided, as its own optional layer.

    python3 scripts/live_overlay.py
    python3 scripts/live_overlay.py --partner logos/a.png --partner logos/b.png

Writes to out/live/:
    live_bg.png        the overlay — the top layer in OBS / StreamYard
    live_bug.png       optional corner logo watermark
    live_badge.png     optional "LIVE · ನೇರ ಪ್ರಸಾರ" badge (see above before using)
    live_preview.jpg   all of it over a sample frame, for checking only
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from brand import typo                                           # noqa: E402
from brand import ornament as orn                                # noqa: E402
from brand.surface import (Surface, rule, gilded_vrule, logo,    # noqa: E402
                           cover, house_grade)
from brand.tokens import C, Brand, mix                           # noqa: E402

W, H, SS = 1920, 1080, 2
MARGIN = 72
SHADOW = (0, 2 * SS, 8 * SS, (0, 0, 0, 120))

CTA_TOP = 'ಕ್ಷಣ ಕ್ಷಣದ ಕರಾವಳಿ ಸುದ್ದಿಗಾಗಿ'
CTA_MAIN = 'ಸಬ್‌ಸ್ಕ್ರೈಬ್ ಮಾಡಿ, ಬೆಲ್ ಒತ್ತಿ'
FOLLOW = 'ನಮ್ಮನ್ನು ಫಾಲೋ ಮಾಡಿ'
PLATFORMS = 'YouTube  •  Instagram  •  Facebook'
PARTNERS = 'ಸಹಯೋಗ'

# Promo mode — Citizen news tip line & live event broadcast booking
PROMO_CENTER = 'ನಿಮ್ಮೂರಿನ ಸುದ್ದಿ • ಸಮಸ್ಯೆ • ನೇರ ಪ್ರಸಾರಕ್ಕಾಗಿ'
PROMO_PHONE_KICKER = 'ವಾಟ್ಸಾಪ್ / ಕರೆ ಮಾಡಿ'
PROMO_PHONE = '96117 56514'


# ─────────────────────────────────────────────────────────────────────────────
#  THE TEAM'S FORMAT
# ─────────────────────────────────────────────────────────────────────────────

def read_format(path: str) -> tuple[int, tuple]:
    """(first row of the band, the band's colour), measured from the file."""
    with Image.open(path) as im:
        a = np.asarray(im.convert('RGBA'))
    if a.shape[:2] != (H, W):
        raise SystemExit(f'{path} is {a.shape[1]}×{a.shape[0]}; a YouTube Live '
                         f'overlay must be {W}×{H}.')
    opaque = np.where(a[..., 3].max(axis=1) > 0)[0]
    if not len(opaque):
        raise SystemExit(f'{path} has no band — it is transparent throughout.')
    top = int(opaque.min())
    vals, counts = np.unique(a[top:, :, :3].reshape(-1, 3), axis=0,
                             return_counts=True)
    return top, tuple(int(v) for v in vals[counts.argmax()])


def finish(img: Image.Image, top: int | None = None) -> Image.Image:
    """Downsample with PREMULTIPLIED alpha, then re-empty the picture area.

    A straight Lanczos resize of RGBA drags the black of transparent pixels
    into every soft edge and draws a dark halo round the logo and the type.
    Premultiplying first is what keeps the edges clean on a live picture."""
    a = np.asarray(img).astype(np.float32) / 255.0
    pm = np.concatenate([a[..., :3] * a[..., 3:4], a[..., 3:4]], -1)
    pm_img = Image.fromarray((pm * 255 + 0.5).astype(np.uint8), 'RGBA')
    s = np.asarray(pm_img.resize((W, H), Image.Resampling.LANCZOS)
                   ).astype(np.float32) / 255.0
    al = s[..., 3:4]
    col = np.where(al > 1e-4, s[..., :3] / np.maximum(al, 1e-4), 0.0)
    out = (np.concatenate([np.clip(col, 0, 1), al], -1) * 255 + 0.5
           ).astype(np.uint8)
    if top is not None:
        out[:top] = 0          # the team's transparency, guaranteed
        # …and the team's opacity. Lanczos rings where the band meets the
        # empty picture area and left the band at alpha 241 in places, which
        # would let the camera show faintly through the bottom of the frame.
        out[top:, :, 3] = 255
    out[out[..., 3] == 0] = 0
    return Image.fromarray(out, 'RGBA')


# ─────────────────────────────────────────────────────────────────────────────
#  DRAWING
# ─────────────────────────────────────────────────────────────────────────────

def band_ground(sf: Surface, top: int, colour: tuple):
    """The team's maroon, given depth: lit at the top edge, grounded at the
    foot, with fine grain — flat digital colour is what looks cheap on a TV."""
    bh = H - top
    hi = mix(colour, C.red_600, 0.40)
    lo = mix(colour, C.ink_950, 0.38)
    t = np.linspace(0.0, 1.0, bh * SS, dtype=np.float32)
    t = t * t * (3 - 2 * t)
    rows = np.stack([hi[i] + (lo[i] - hi[i]) * t for i in range(3)], -1)
    arr = np.empty((bh * SS, W * SS, 4), np.float32)
    arr[..., :3] = rows[:, None, :]
    rng = np.random.default_rng(1956)          # Karnataka's year; any seed
    arr[..., :3] += rng.normal(0.0, 2.0, (bh * SS, W * SS, 1)).astype(np.float32)
    arr[..., 3] = 255
    sf.img.alpha_composite(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8),
                                           'RGBA'), (0, top * SS))


def band_glow(sf: Surface, top: int, cx: float, cy: float, rx: float,
              ry: float, color, a: float):
    """A soft light INSIDE the band only. radial_glow would spill upward into
    the picture area, and the picture area must stay empty."""
    bh = H - top
    ys = (np.arange(bh * SS, dtype=np.float32) + 0.5) / SS + top
    xs = (np.arange(W * SS, dtype=np.float32) + 0.5) / SS
    d = np.sqrt(((xs[None, :] - cx) / rx) ** 2 + ((ys[:, None] - cy) / ry) ** 2)
    tt = np.clip(1.0 - d, 0.0, 1.0)
    sf.img.alpha_composite(orn._tint(tt * tt * (3 - 2 * tt) * 255.0, color, a),
                           (0, top * SS))


def top_edge(sf: Surface, top: int):
    """A gold line where the picture ends — the broadcast convention that
    tells the eye the band is furniture, not part of the shot."""
    rule(sf, 0, top, W, (*C.gold_500, 255), 3.0)
    rule(sf, 0, top, W, (*mix(C.gold_300, C.paper_0, 0.3), 170), 1.0)
    rule(sf, 0, top + 3, W, (*C.ink_950, 90), 1.0)


def ringed_logo(sf: Surface, cx: float, cy: float, d: float, a: float = 1.0):
    """The circle logo on a gold ring with a soft contact shadow."""
    ring = 6
    S = int((d + 2 * ring + 24) * SS)
    lay = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    c = S / 2
    r_out = (d / 2 + ring) * SS
    sh = Image.new('L', (S, S), 0)
    ImageDraw.Draw(sh).ellipse([c - r_out, c - r_out + 4 * SS,
                                c + r_out, c + r_out + 4 * SS], fill=150)
    from PIL import ImageFilter
    sh = sh.filter(ImageFilter.GaussianBlur(5 * SS))
    lay.alpha_composite(orn._tint(np.asarray(sh, np.float32), (0, 0, 0), 1.0))
    dr = ImageDraw.Draw(lay)
    dr.ellipse([c - r_out, c - r_out, c + r_out, c + r_out], fill=(*C.gold_500, 255))
    r_in = r_out - 1.5 * SS
    dr.ellipse([c - r_in, c - r_in, c + r_in, c + r_in],
               outline=(*mix(C.gold_300, C.paper_0, 0.35), 200), width=SS)
    lg = logo(int(d * SS))
    lay.alpha_composite(lg, (int(c - d * SS / 2), int(c - d * SS / 2)))
    if a < 1.0:
        lay.putalpha(lay.getchannel('A').point(lambda v: int(v * a)))
    orn._paste(sf, lay, cx * SS - c, cy * SS - c)


def bell(sf: Surface, cx: float, cy: float, h: float, color):
    """A plain notification bell, drawn — never YouTube's own button art."""
    S = int(h * 1.4 * SS)
    lay = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    u = h * SS
    ox, oy = S / 2, S / 2
    pts = [(ox, oy - 0.50 * u)]
    for i in range(21):
        t = i / 20
        pts.append((ox + (0.17 + 0.23 * t ** 1.7) * u, oy + (-0.36 + 0.60 * t) * u))
    pts += [(ox + 0.47 * u, oy + 0.30 * u), (ox - 0.47 * u, oy + 0.30 * u)]
    for i in range(20, -1, -1):
        t = i / 20
        pts.append((ox - (0.17 + 0.23 * t ** 1.7) * u, oy + (-0.36 + 0.60 * t) * u))
    fill = (*color[:3], 255)
    dr.polygon(pts, fill=fill)
    dr.ellipse([ox - 0.19 * u, oy - 0.58 * u, ox + 0.19 * u, oy - 0.26 * u], fill=fill)
    dr.ellipse([ox - 0.05 * u, oy - 0.66 * u, ox + 0.05 * u, oy - 0.56 * u], fill=fill)
    dr.ellipse([ox - 0.10 * u, oy + 0.33 * u, ox + 0.10 * u, oy + 0.52 * u], fill=fill)
    orn._paste(sf, lay, cx * SS - ox, cy * SS - oy)


def mic_icon(sf: Surface, cx: float, cy: float, h: float, color):
    """A broadcast microphone icon in gold."""
    S = int(h * 1.5 * SS)
    lay = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    u = h * SS
    ox, oy = S / 2, S / 2
    col = (*color[:3], 255)
    # capsule
    dr.rounded_rectangle([ox - 0.16 * u, oy - 0.44 * u, ox + 0.16 * u, oy + 0.06 * u],
                         radius=int(0.16 * u), fill=col)
    # cradle
    dr.arc([ox - 0.28 * u, oy - 0.24 * u, ox + 0.28 * u, oy + 0.24 * u],
           start=0, end=180, fill=col, width=max(2, int(2.5 * SS)))
    # stem
    dr.rectangle([ox - 0.04 * u, oy + 0.24 * u, ox + 0.04 * u, oy + 0.42 * u], fill=col)
    # base
    dr.rounded_rectangle([ox - 0.22 * u, oy + 0.40 * u, ox + 0.22 * u, oy + 0.48 * u],
                         radius=int(2 * SS), fill=col)
    orn._paste(sf, lay, cx * SS - ox, cy * SS - oy)


def phone_icon(sf: Surface, cx: float, cy: float, h: float, color):
    """A clean phone handset icon."""
    S = int(h * 1.5 * SS)
    lay = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    u = h * SS
    ox, oy = S / 2, S / 2
    col = (*color[:3], 255)
    dr.rounded_rectangle([ox - 0.28 * u, oy - 0.38 * u, ox - 0.06 * u, oy - 0.14 * u],
                         radius=int(4 * SS), fill=col)
    dr.rounded_rectangle([ox + 0.06 * u, oy + 0.14 * u, ox + 0.28 * u, oy + 0.38 * u],
                         radius=int(4 * SS), fill=col)
    pts = [(ox - 0.22 * u, oy - 0.18 * u), (ox - 0.08 * u, oy - 0.18 * u),
           (ox + 0.18 * u, oy + 0.08 * u), (ox + 0.18 * u, oy + 0.22 * u),
           (ox + 0.08 * u, oy + 0.22 * u), (ox - 0.22 * u, oy - 0.06 * u)]
    dr.polygon(pts, fill=col)
    orn._paste(sf, lay, cx * SS - ox, cy * SS - oy)


def partner_tiles(sf: Surface, x0: float, top: int, paths: list[str]) -> float:
    """White tiles for partner logos, so any logo reads on maroon. Returns the
    right edge. Contained, never cropped — a partner's mark is not ours to cut."""
    th = 100
    tw = int(th * 1.6)
    gap = 18
    y0 = top + 60
    x = x0
    for p in paths:
        tile = Image.new('RGBA', (tw * SS, th * SS), (0, 0, 0, 0))
        ImageDraw.Draw(tile).rounded_rectangle([0, 0, tw * SS - 1, th * SS - 1],
                                               radius=14 * SS, fill=(*C.paper_50, 255))
        with Image.open(p) as src:
            lg = src.convert('RGBA')
        pad = 12 * SS
        sc = min((tw * SS - 2 * pad) / lg.width, (th * SS - 2 * pad) / lg.height)
        lg = lg.resize((max(1, int(lg.width * sc)), max(1, int(lg.height * sc))),
                       Image.Resampling.LANCZOS)
        tile.alpha_composite(lg, ((tw * SS - lg.width) // 2, (th * SS - lg.height) // 2))
        orn._paste(sf, tile, x * SS, y0 * SS)
        x += tw + gap
    return x - gap


def text_w(s: str, f) -> float:
    return typo.text_width(s, f) / SS


# ─────────────────────────────────────────────────────────────────────────────
#  LAYERS
# ─────────────────────────────────────────────────────────────────────────────

def build_bg(top: int, colour: tuple, partners: list[str],
             mode: str = 'subscribe') -> Image.Image:
    sf = Surface(W, H, SS, bg=(0, 0, 0, 0))
    bh = H - top
    band_ground(sf, top, colour)

    # ── left: the channel ────────────────────────────────────────────────
    d = min(150, bh - 36)
    lcx, lcy = MARGIN + d / 2 + 6, top + bh / 2
    band_glow(sf, top, lcx, lcy, 260, bh * 0.9, C.gold_500, 0.10)
    ringed_logo(sf, lcx, lcy, d)

    f_name = typo.font('kn', int(58 * SS))
    f_tag = typo.font('kn_var', int(30 * SS), weight=560)
    f_handle_sm = typo.font('latin', int(30 * SS), weight=700)
    tx = MARGIN + d + 12 + 30
    sub, f_sub = ((Brand.handle, f_handle_sm) if partners
                  else (Brand.tagline, f_tag))
    typo.draw_text(sf.img, Brand.name, tx * SS, (top + 88) * SS, f_name,
                   C.paper_0, shadow=SHADOW)
    typo.draw_text(sf.img, sub, tx * SS, (top + 140) * SS, f_sub,
                   C.gold_300, shadow=SHADOW)
    left_edge = tx + max(text_w(Brand.name, f_name), text_w(sub, f_sub))

    # ── right: partners, or — until there are any — the handle/phone ─────
    right = W - MARGIN
    if partners:
        n = len(partners)
        block_w = n * 160 + (n - 1) * 18
        rx0 = right - block_w
        f_lab = typo.font('kn_var', int(26 * SS), weight=600)
        typo.draw_text(sf.img, PARTNERS, (rx0 + block_w / 2) * SS,
                       (top + 46) * SS, f_lab, C.gold_300, anchor_x='c',
                       shadow=SHADOW)
        partner_tiles(sf, rx0, top, partners)
    elif mode == 'promo':
        f_kicker = typo.font('kn_var', int(28 * SS), weight=580)
        f_phone = typo.font('latin', int(58 * SS), weight=780)
        block_w = max(text_w(PROMO_PHONE_KICKER, f_kicker),
                      text_w(PROMO_PHONE, f_phone))
        rx0 = right - block_w
        mid = (rx0 + block_w / 2) * SS
        typo.draw_text(sf.img, PROMO_PHONE_KICKER, mid, (top + 72) * SS, f_kicker,
                       C.gold_300, anchor_x='c', shadow=SHADOW)
        typo.draw_text(sf.img, PROMO_PHONE, mid, (top + 138) * SS, f_phone,
                       C.paper_0, anchor_x='c', shadow=SHADOW)
    else:
        f_follow = typo.font('kn_var', int(26 * SS), weight=560)
        f_handle = typo.font('latin', int(56 * SS), weight=760)
        f_plat = typo.font('latin', int(24 * SS), weight=520)
        block_w = max(text_w(FOLLOW, f_follow), text_w(Brand.handle, f_handle),
                      text_w(PLATFORMS, f_plat))
        rx0 = right - block_w
        mid = (rx0 + block_w / 2) * SS
        typo.draw_text(sf.img, FOLLOW, mid, (top + 54) * SS, f_follow,
                       C.gold_300, anchor_x='c', shadow=SHADOW)
        typo.draw_text(sf.img, Brand.handle, mid, (top + 118) * SS, f_handle,
                       C.paper_0, anchor_x='c', shadow=SHADOW)
        typo.draw_text(sf.img, PLATFORMS, mid, (top + 158) * SS, f_plat,
                       C.paper_200, anchor_x='c', shadow=SHADOW)

    # ── centre: the one thing to do ──────────────────────────────────────
    div1, div2 = left_edge + 56, rx0 - 56
    for x in (div1, div2):
        gilded_vrule(sf, x, top + 34, H - 34, weight=1.6, a_mid=0.75)
    cx0, cx1 = div1 + 30, div2 - 30
    ccx = (cx0 + cx1) / 2
    f_top = typo.font('kn_var', int(30 * SS), weight=560)

    if mode == 'promo':
        room = cx1 - cx0
        main = typo.fit(PROMO_CENTER, 'kn', int(46 * SS), int(34 * SS), room * SS,
                        80 * SS, 1.1, max_lines=1)
        rise, drop = typo.ink_extents(main.lines[0], main.f)
        cy = (top + bh / 2) * SS
        base = cy + (rise - drop) / 2
        typo.draw_text(sf.img, main.lines[0], ccx * SS, base,
                       main.f, C.paper_0, anchor_x='c', shadow=SHADOW)
        # Subtle gold accent line underneath
        ry = top + bh / 2 + 34
        rule(sf, ccx - 140, ry, ccx + 140, (*C.gold_500, 80), 1.2)
        rule(sf, ccx - 60, ry, ccx + 60, (*C.gold_400, 140), 1.0)
    else:
        typo.draw_text(sf.img, CTA_TOP, ccx * SS, (top + 72) * SS, f_top,
                       C.gold_300, anchor_x='c', shadow=SHADOW)
        bell_h = 40
        room = (cx1 - cx0) - bell_h - 18
        main = typo.fit(CTA_MAIN, 'kn', int(46 * SS), int(32 * SS), room * SS,
                        60 * SS, 1.1, max_lines=1)
        mw = main.width / SS
        gx = ccx - (bell_h + 18 + mw) / 2
        base = top + 136
        bell(sf, gx + bell_h / 2, base - main.first_rise / SS * 0.48, bell_h,
             C.gold_400)
        typo.draw_text(sf.img, main.lines[0], (gx + bell_h + 18) * SS, base * SS,
                       main.f, C.paper_0, shadow=SHADOW)

    top_edge(sf, top)
    return finish(sf.img, top)


def build_bug() -> Image.Image:
    """A corner logo, top right — clear of YouTube's title, which sits top left."""
    sf = Surface(W, H, SS, bg=(0, 0, 0, 0))
    d = 104
    ringed_logo(sf, W - MARGIN - d / 2 - 6, MARGIN + d / 2 - 12, d, a=0.92)
    return finish(sf.img)


def build_badge() -> Image.Image:
    sf = Surface(W, H, SS, bg=(0, 0, 0, 0))
    f_live = typo.font('latin', int(28 * SS), weight=800)
    f_kn = typo.font('kn_var', int(28 * SS), weight=640)
    ph, pad, dot, gap = 54, 24, 14, 14
    w_live, w_kn = text_w('LIVE', f_live), text_w('ನೇರ ಪ್ರಸಾರ', f_kn)
    pw = pad + dot + gap + w_live + 16 + 2 + 16 + w_kn + pad
    x0, y0 = MARGIN, 56
    lay = Image.new('RGBA', (int(pw * SS), int(ph * SS)), (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    dr.rounded_rectangle([0, 0, pw * SS - 1, ph * SS - 1], radius=ph * SS / 2,
                         fill=(*C.red_500, 245),
                         outline=(*C.red_400, 255), width=2 * SS)
    cy = ph * SS / 2
    dx = (pad + dot / 2) * SS
    dr.ellipse([dx - dot * SS / 2, cy - dot * SS / 2, dx + dot * SS / 2,
                cy + dot * SS / 2], fill=(*C.paper_0, 255))
    xl = (pad + dot + gap) * SS
    r_live, _ = typo.ink_extents('LIVE', f_live)
    typo.draw_text(lay, 'LIVE', xl, cy + r_live / 2, f_live, C.paper_0)
    xs = xl + (w_live + 16) * SS
    dr.rectangle([xs, cy - 14 * SS, xs + 2 * SS, cy + 14 * SS],
                 fill=(*C.paper_0, 150))
    r_kn, _ = typo.ink_extents('ನೇರ ಪ್ರಸಾರ', f_kn)
    typo.draw_text(lay, 'ನೇರ ಪ್ರಸಾರ', xs + 18 * SS, cy + r_kn * 0.42, f_kn,
                   C.paper_0)
    orn._paste(sf, lay, x0 * SS, y0 * SS)
    return finish(sf.img)


def preview(layers: list[Image.Image], path: str):
    """The overlay over a stand-in camera frame. For checking only."""
    sample = os.path.join(ROOT, 'assets', 'stock', 'coastal_fishing_harbour_docks.jpg')
    if os.path.exists(sample):
        with Image.open(sample) as src:
            frame = house_grade(cover(src, W, H)).convert('RGBA')
    else:
        frame = Image.new('RGBA', (W, H), (60, 60, 64, 255))
    for lay in layers:
        frame.alpha_composite(lay)
    frame.convert('RGB').save(path, quality=90)


def main() -> int:
    ap = argparse.ArgumentParser(description='Build the YouTube Live overlay '
                                             'from the team\'s format file.')
    ap.add_argument('--base', default='LIVE BG.png',
                    help='the team\'s format file (default: "LIVE BG.png")')
    ap.add_argument('--out', default=os.path.join('out', 'live'))
    ap.add_argument('--partner', action='append', default=[],
                    help='a partner logo; repeat for up to four')
    args = ap.parse_args()

    if len(args.partner) > 4:
        print('✗ the band holds four partner logos at a readable size; '
              f'{len(args.partner)} were given.', file=sys.stderr)
        return 1
    for p in args.partner:
        if not os.path.exists(p):
            print(f'✗ partner logo not found: {p}', file=sys.stderr)
            return 1

    top, colour = read_format(args.base)
    print(f'format: {args.base} — picture 0–{top - 1}, band {top}–{H - 1} '
          f'({H - top}px), #{colour[0]:02X}{colour[1]:02X}{colour[2]:02X}')
    os.makedirs(args.out, exist_ok=True)

    bug = build_bug()
    bug.save(os.path.join(args.out, 'live_bug.png'), optimize=True)
    badge = build_badge()
    badge.save(os.path.join(args.out, 'live_badge.png'), optimize=True)

    # ── 1. Default Subscribe & Social Follow Overlay ─────────────────────
    bg = build_bg(top, colour, args.partner, mode='subscribe')
    empty = np.asarray(bg)[:top, :, 3].max()
    assert empty == 0, 'the picture area is no longer transparent'
    bg.save(os.path.join(args.out, 'live_bg.png'), optimize=True)

    full = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    full.alpha_composite(bg)
    full.alpha_composite(bug)
    full.alpha_composite(badge)
    full.save(os.path.join(args.out, 'live_overlay_full.png'), optimize=True)
    preview([bg, bug, badge], os.path.join(args.out, 'live_preview.jpg'))

    # ── 2. Promotion & News Coverage / Tip Line Overlay ──────────────────
    promo_bg = build_bg(top, colour, args.partner, mode='promo')
    promo_bg.save(os.path.join(args.out, 'live_promo_bg.png'), optimize=True)

    promo_full = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    promo_full.alpha_composite(promo_bg)
    promo_full.alpha_composite(bug)
    promo_full.alpha_composite(badge)
    promo_full.save(os.path.join(args.out, 'live_promo_overlay_full.png'), optimize=True)
    preview([promo_bg, bug, badge], os.path.join(args.out, 'live_promo_preview.jpg'))

    mode = f'{len(args.partner)} partner logo(s)' if args.partner else 'channel branding (no partners yet)'
    print(f'  ✓ live_bg.png                 band: {mode}; picture area verified transparent')
    print('  ✓ live_bug.png                optional corner logo')
    print('  ✓ live_badge.png              optional LIVE badge')
    print('  ✓ live_overlay_full.png       full transparent overlay (Subscribe + Socials)')
    print('  ✓ live_preview.jpg            preview of subscribe overlay')
    print('  ✓ live_promo_bg.png           promo band: news coverage tip line + phone')
    print('  ✓ live_promo_overlay_full.png full transparent overlay (News Tip / Raise Voice + Phone)')
    print('  ✓ live_promo_preview.jpg      preview of promo overlay')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
