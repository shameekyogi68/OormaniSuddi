"""Greeting — a festival wish, designed as a poster rather than a bulletin.

Every other template in this directory is news, and news grammar is built to
be believed: a masthead, a category rail, a left-aligned headline, hairlines.
Set a festival wish in that grammar and it reads as a report ABOUT a festival.
The first Gauri Ganesha poster did exactly that — it looked like a news card
with a beautiful photograph behind it.

A greeting is built to be felt and forwarded, and the design language that does
that in Karnataka is old and specific:

  * SYMMETRY.  Devotional and festive art is centred. The eye enters at the
    salutation, drops through the image, and lands on the festival's name.
  * THE NAME IS THE HERO, in gold. Set in the serif, in a foil that catches
    light — never flat yellow, which is the loudest single mark of a cheap
    poster.
  * THE DEITY IS NEVER COVERED.  A photograph must declare `keep_clear`, the
    band of the image holding the deity or subject. The solver scales and
    shifts the picture so no type ever enters that band; if it cannot, it sets
    the picture inside a temple arch instead; if even that fails, it refuses.
    Words across Ganapati's face are not a layout imperfection on this channel.
  * SIGNED, NOT MASTHEADED.  "ಶುಭ ಕೋರುವವರು" above the brand, the way a wish
    from a family or an institution has always been signed on a festival
    banner. No dateline, no category, no "ವಿಶೇಷ".
  * DISCLOSED.  An AI image carries its label on the poster itself (D49).

See DECISIONS.md D54.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from types import SimpleNamespace

import numpy as np
from PIL import Image, ImageFilter

from brand import typo
from brand import ornament as orn
from brand.content import Photo, ContentError
from brand.copy import CORE_TAGS
from brand.surface import Surface, scrim, vgradient, radial_glow, grain, paste_logo
from brand.tokens import C, Grade, Brand, fmt, mix, rgb


# ─────────────────────────────────────────────────────────────────────────────
#  THEMES
#  Gold is the constant — it is the brand, and it is the colour of every
#  festival here. A theme changes only the GROUND the gold sits on and the
#  colour of the light around the subject.
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Theme:
    key: str
    deep: tuple      # the darkness everything falls into
    mid: tuple       # the lift at the top of the ground
    glow: tuple      # lamp light around the subject and behind the name
    use_for: str


THEMES: dict[str, Theme] = {t.key: t for t in [
    Theme('sacred', rgb('#150405'), rgb('#3B0C0A'), rgb('#FFB547'),
          'Gauri-Ganesha, Navaratri, Dasara, Janmashtami, temple jatre, Shivaratri'),
    Theme('lights', rgb('#05061A'), rgb('#1B1542'), rgb('#FFC34D'),
          'Deepavali, Karthika Deepotsava, Tulasi pooje'),
    Theme('harvest', rgb('#041209'), rgb('#123420'), rgb('#F2C45A'),
          'Ugadi, Makara Sankranti, Bisu (Tulu new year), Nagara Panchami, Kedda'),
    Theme('rajyotsava', rgb('#1A0304'), rgb('#520B0C'), rgb('#FFD22E'),
          'Kannada Rajyotsava — the red and yellow of the Karnataka flag'),
    Theme('national', rgb('#040A17'), rgb('#10213D'), rgb('#FF9A3C'),
          'Independence Day, Republic Day, Gandhi Jayanti'),
    Theme('serene', rgb('#031414'), rgb('#0C302D'), rgb('#EAD9A2'),
          'Eid, Christmas, Buddha Purnima, Mahavir Jayanti, Guru Nanak Jayanti'),
]}


# Per format, in final pixels. A 9:16 wish is a WhatsApp status and a story;
# 4:5 is the feed; 1:1 is the forward. The foot margins keep the signature
# clear of the reply bar a status or story draws over the bottom of the frame.
SCALE = {
    'story':  dict(sal=34, date=24, hero=(112, 72), wish=(76, 54), bless=(31, 26),
                   bless_lines=2, label=21, name=36, handle=22, disc=18, logo=58,
                   top=104, bot=150, pad=80, corner=(36, 132),
                   bokeh=34, twinkles=6),
    'post':   dict(sal=30, date=22, hero=(96, 62), wish=(64, 46), bless=(28, 24),
                   bless_lines=2, label=19, name=32, handle=20, disc=17, logo=50,
                   top=68, bot=62, pad=76, corner=(28, 104),
                   bokeh=26, twinkles=5),
    'square': dict(sal=26, date=20, hero=(78, 54), wish=(52, 40), bless=(24, 21),
                   bless_lines=1, label=17, name=28, handle=18, disc=15, logo=42,
                   top=54, bot=48, pad=72, corner=(24, 90),
                   bokeh=22, twinkles=4),
}

WISH_INK = mix(C.paper_0, C.gold_300, 0.10)

LIMITS = dict(occasion=30, wish=26, salutation=34, blessing=96,
              sign_label=24, date=30)


# ─────────────────────────────────────────────────────────────────────────────
#  CONTENT
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Greeting:
    occasion: str                               # the festival, set in foil: "ಗೌರಿ ಗಣೇಶ ಹಬ್ಬದ"
    wish: str = 'ಹಾರ್ದಿಕ ಶುಭಾಶಯಗಳು'
    salutation: str = 'ನಾಡಿನ ಸಮಸ್ತ ಜನತೆಗೆ'
    blessing: str = ''
    theme: str = 'sacred'
    photo: Photo | None = None
    # The band of the photograph, as fractions of its HEIGHT, that holds the
    # deity or subject. Required with a photo: it is what the layout solver
    # guarantees no type will ever enter.
    keep_clear: tuple[float, float] = (0.0, 0.0)
    sign_label: str = 'ಶುಭ ಕೋರುವವರು'
    date: str = ''
    tags: list[str] = field(default_factory=list)
    slug: str = ''

    def validate(self) -> 'Greeting':
        if not (self.occasion or '').strip():
            raise ContentError('occasion is required — the festival, set as the '
                               'hero line, e.g. "ಗೌರಿ ಗಣೇಶ ಹಬ್ಬದ".')
        for k, n in LIMITS.items():
            v = getattr(self, k) or ''
            if len(v) > n:
                raise ContentError(
                    f'{k} is {len(v)} characters; a greeting sets it at poster '
                    f'size and it must stay within {n}. A wish that needs more '
                    f'words than that is a caption, not a poster.')
        if self.theme not in THEMES:
            raise ContentError(f'unknown theme {self.theme!r}; choose from '
                               f'{sorted(THEMES)}')
        if self.photo is not None:
            self.photo.validate()
            a, b = self.keep_clear
            if not (0.0 <= a < b <= 1.0):
                raise ContentError(
                    'a greeting photograph must declare keep_clear: [top, bottom] '
                    '— the band of the image, as fractions of its height, that '
                    'holds the deity or subject — so the wish is never set across '
                    'it. For a seated pair of idols filling the middle of a '
                    'portrait photo that is typically about [0.3, 0.66].')
        for k in ('occasion', 'wish', 'salutation', 'blessing', 'sign_label', 'date'):
            v = getattr(self, k) or ''
            if not v:
                continue
            fam = 'kn_serif' if k in ('occasion', 'wish') else 'kn_var'
            gone = typo.missing_glyphs(v, typo.font_for(v, fam, 40))
            if gone:
                raise ContentError(f'{k} contains characters no house font can '
                                   f'set: {" ".join(gone)}')
        return self

    @classmethod
    def from_dict(cls, d: dict) -> 'Greeting':
        d = dict(d)
        d.pop('kind', None)
        d.pop('template', None)
        extra = set(d) - set(cls.__dataclass_fields__)
        if extra:
            raise ContentError(f'unknown greeting field(s) {sorted(extra)}')
        if d.get('photo'):
            d['photo'] = Photo.from_dict(d['photo'])
        if 'keep_clear' in d:
            d['keep_clear'] = tuple(d['keep_clear'])
        return cls(**d)

    @classmethod
    def load(cls, path: str) -> 'Greeting':
        with open(path, encoding='utf-8') as f:
            return cls.from_dict(json.load(f))


# ─────────────────────────────────────────────────────────────────────────────
#  LAYOUT
# ─────────────────────────────────────────────────────────────────────────────

def _top_limit(g: Greeting, S: dict) -> float:
    """Where the salutation zone ends and the picture may begin."""
    return S['top'] + S['sal'] * 1.3 + (S['date'] * 1.5 if g.date else 0) + 30


def _blocks(g: Greeting, S: dict, W: int, ss: int, k: float = 1.0):
    """Fit the wish stack at scale `k` and measure it, in final pixels."""
    cw = W - 2 * S['pad']
    hh, hl = S['hero']
    wh, wl = S['wish']
    bh, bl = S['bless']
    occ = typo.fit(g.occasion, 'kn_serif', int(ss * hh * k), int(ss * hl * k),
                   ss * cw, ss * hh * k * 1.3 * 2, 1.14, align='center',
                   max_lines=2)
    wish = (typo.fit(g.wish, 'kn_serif', int(ss * wh * k), int(ss * wl * k),
                     ss * cw, ss * wh * k * 1.7, 1.14, align='center',
                     max_lines=1) if g.wish else None)
    nb = S['bless_lines']
    bless = (typo.fit(g.blessing, 'kn_var', int(ss * bh * k), int(ss * bl * k),
                      ss * (cw - 40), ss * bh * k * 1.5 * nb + 8 * ss, 1.46,
                      weight=470, align='center', max_lines=nb)
             if g.blessing else None)
    b = SimpleNamespace(occ=occ, wish=wish, bless=bless, k=k)
    b.g_occ = 10 * k
    b.g_wish = 30 * k
    b.div = 30
    b.g_div = 22 * k
    b.g_bless = 40 * k
    b.sig = (((S['label'] * 1.35 + 12) if g.sign_label else 0)
             + S['logo'] + 14 + S['handle'] * 1.4)
    b.disc = (14 + S['disc'] * 1.4) if g.photo else 0
    b.total = (occ.height / ss + b.g_occ
               + ((wish.height / ss + b.g_wish) if wish else 18)
               + b.div + b.g_div
               + ((bless.height / ss + b.g_bless) if bless else 16)
               + b.sig + b.disc)
    return b


def _solve_bleed(size, band, W, H, top_limit, bot_limit, zmax=1.16):
    """Zoom and vertical offset that keep the subject band inside
    [top_limit, bot_limit] on a full-bleed crop — or None.

    The smallest feasible zoom wins: every step of zoom is upscaling, and a
    soft photograph is the second loudest mark of a cheap poster. Inside the
    feasible range the band is centred in the space it has."""
    iw, ih = size
    a, b = band
    base = max(W / iw, H / ih)
    for z in np.arange(1.0, zmax + 1e-6, 0.01):
        sc = base * z
        nh = ih * sc
        lo = max(0.0, b * nh - bot_limit)
        hi = min(nh - H, a * nh - top_limit)
        if lo <= hi:
            ideal = (a + b) / 2 * nh - (top_limit + bot_limit) / 2
            cy = min(max(ideal, lo), hi)
            return SimpleNamespace(z=float(z), sc=sc, cy=cy,
                                   top=a * nh - cy, bottom=b * nh - cy)
    return None


def _solve_window(size, band, W, S, top_limit, text_top):
    """An arch window holding the photograph when full bleed cannot keep the
    subject clear of the type — or None when even that cannot."""
    iw, ih = size
    a, b = band
    wy0 = top_limit + 26
    wy1 = text_top - 30
    wh = wy1 - wy0
    if wh < 160:
        return None
    # The subject fills 80% of the window's height and sits low in it, so the
    # crowns have air under the apex. At 90% and centred, Gauri's crown all
    # but touched the arch line.
    sc = wh * 0.80 / ((b - a) * ih)
    if sc < wh / ih:
        sc = wh / ih
    ww = min(W - 2 * S['pad'] - 20, iw * sc, wh * 1.22)
    if ww < 160 or (b - a) * ih * sc > wh:
        return None
    nh, nw = ih * sc, iw * sc
    cy = min(max((a + b) / 2 * nh - wh * 0.58, 0.0), nh - wh)
    wx0 = (W - ww) / 2
    return SimpleNamespace(sc=sc, cy=cy, nw=nw, nh=nh, x=wx0, y=wy0, w=ww, h=wh,
                           rise=ww * 0.30,
                           top=wy0 + max(0.0, a * nh - cy),
                           bottom=wy0 + min(wh, b * nh - cy))


def _sharpen(im: Image.Image, ss: int) -> Image.Image:
    """Recover some edge after the upscale a phone-sized source always needs."""
    return im.filter(ImageFilter.UnsharpMask(radius=1.4 * ss, percent=38,
                                             threshold=2))


def _draw_bleed(sf, g, th, sol, W, H, top, text_top):
    ss = sf.ss
    with Image.open(g.photo.path) as src:
        im = src.convert('RGB')
    sc = sol.sc * ss
    nw, nh = int(round(im.width * sc)), int(round(im.height * sc))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    cx = int((nw - W * ss) * min(max(g.photo.focal[0], 0.0), 1.0))
    cy = min(max(int(round(sol.cy * ss)), 0), nh - H * ss)
    im = im.crop((cx, cy, cx + W * ss, cy + H * ss))
    im = _sharpen(orn.warm_grade(im, th.deep), ss)
    sf.img.alpha_composite(im.convert('RGBA'))

    span = sol.bottom - sol.top
    radial_glow(sf, W * 0.5, sol.top + span * 0.36, W * 0.62, th.glow, 0.08)
    orn.vignette(sf, th.deep, 0.62)
    scrim(sf, 0, top + 110, th.deep, 0.90, 0.0, curve=1.5)
    # The veil must be nearly solid by the time the hero's ink begins: the
    # first cut reached depth 70px too late and the lit ledge of the mantapa
    # showed through the tops of the festival name.
    scrim(sf, sol.bottom - 40, text_top + 26, th.deep, 0.0, 0.90, curve=1.4)
    scrim(sf, text_top + 26, H, th.deep, 0.90, 0.97, curve=1.0)
    return [(0, 0, W, top + 60),
            (0, top, W * 0.15, sol.bottom),
            (W * 0.85, top, W, sol.bottom)]


def _draw_window(sf, g, th, win, W, H, text_top):
    ss = sf.ss
    radial_glow(sf, W * 0.5, win.y + win.h * 0.45, W * 0.74, th.glow, 0.22)
    orn.mandala(sf, W * 0.5, win.y + win.h * 0.50,
                min(W * 0.48, win.h * 0.74), C.gold_400, 0.20)

    with Image.open(g.photo.path) as src:
        im = src.convert('RGB')
    nw, nh = int(round(win.nw * ss)), int(round(win.nh * ss))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    ww, wh = int(round(win.w * ss)), int(round(win.h * ss))
    cx = int((nw - ww) * min(max(g.photo.focal[0], 0.0), 1.0))
    cy = min(max(int(round(win.cy * ss)), 0), nh - wh)
    im = _sharpen(orn.warm_grade(im.crop((cx, cy, cx + ww, cy + wh)), th.deep), ss)

    # The foot of the window DISSOLVES into the ground. It first ended on a
    # straight cut, which is the hard photo seam STANDARDS forbids: a fade of
    # the picture's own alpha has no edge to find.
    rows = np.linspace(0.0, 1.0, wh, dtype=np.float32)
    t = np.clip((rows - 0.80) / 0.20, 0.0, 1.0)
    foot = 1.0 - t * t * (3.0 - 2.0 * t)
    arch = np.asarray(orn.arch_mask(ww, wh, win.rise * ss), np.float32)
    im = im.convert('RGBA')
    im.putalpha(Image.fromarray((arch * foot[:, None]).astype(np.uint8), 'L'))
    orn._paste(sf, im, win.x * ss, win.y * ss)
    orn.arch_frame(sf, win.x, win.y, win.w, win.h, win.rise)
    return [(0, 0, W, win.y - 30),
            (0, win.y, win.x - 24, text_top - 10),
            (win.x + win.w + 24, win.y, W, text_top - 10)]


def _draw_plate(sf, th, W, top, text_top):
    cy = top + (text_top - top) * 0.48
    r = min(W * 0.42, (text_top - top) * 0.46)
    radial_glow(sf, W * 0.5, cy, r * 1.7, th.glow, 0.22)
    orn.mandala(sf, W * 0.5, cy, r, C.gold_400, 0.34)
    radial_glow(sf, W * 0.5, cy, r * 0.45, th.glow, 0.20)
    return [(0, 0, W, text_top - 20)]


def _draw_salutation(sf, g, S, W, th):
    ss = sf.ss
    f = typo.font('kn_var', int(ss * S['sal']), weight=600)
    rise, _ = typo.ink_extents(g.salutation, f)
    base = S['top'] * ss + rise
    tw = typo.text_width(g.salutation, f) / ss
    # Gold type over a bright marigold garland is gold on yellow. A pool of
    # the ground under the line seats it without veiling the whole top.
    orn.pool(sf, W / 2, S['top'] + S['sal'] * 0.45, tw / 2 + 190,
             S['sal'] * 2.2, th.deep, 0.86)
    typo.draw_text(sf.img, g.salutation, W * ss / 2, base, f, C.gold_300,
                   anchor_x='c', shadow=(0, ss * 2, ss * 10, (0, 0, 0, 220)))
    yl = (base - rise * 0.40) / ss
    gap, L = 22, 84
    orn.fade_line(sf, W / 2 - tw / 2 - gap - L, W / 2 - tw / 2 - gap, yl,
                  C.gold_400, 1.2, 0.0, 0.9, 0.9)
    orn.fade_line(sf, W / 2 + tw / 2 + gap, W / 2 + tw / 2 + gap + L, yl,
                  C.gold_400, 1.2, 0.9, 0.0, 1.1)
    orn.diamond(sf, W / 2 - tw / 2 - gap + 2, yl, 3.4, C.gold_400, 0.95)
    orn.diamond(sf, W / 2 + tw / 2 + gap - 2, yl, 3.4, C.gold_400, 0.95)
    if g.date:
        fd = typo.font_for(g.date, 'kn_var', int(ss * S['date']), weight=480)
        rd, _ = typo.ink_extents(g.date, fd)
        typo.draw_text(sf.img, g.date, W * ss / 2,
                       base + S['sal'] * 0.55 * ss + rd + 6 * ss, fd, C.paper_200,
                       anchor_x='c', shadow=(0, ss, ss * 8, (0, 0, 0, 200)))


def _draw_wish(sf, g, S, b, th, W, text_top):
    ss = sf.ss
    cx = W * ss / 2
    y = text_top * ss

    for i, line in enumerate(b.occ.lines):
        orn.foil_text(sf, line, b.occ.f, cx, y + b.occ.first_rise + i * b.occ.lh,
                      glow=th.glow, glow_a=0.30)
    y += b.occ.height + b.g_occ * ss

    if b.wish:
        for i, line in enumerate(b.wish.lines):
            typo.draw_text(sf.img, line, cx,
                           y + b.wish.first_rise + i * b.wish.lh, b.wish.f,
                           WISH_INK, anchor_x='c',
                           shadow=(0, ss * 3, ss * 14, (0, 0, 0, 215)))
        y += b.wish.height + b.g_wish * ss
    else:
        y += 18 * ss

    orn.ornate_divider(sf, W / 2, y / ss + b.div / 2,
                       min(250, (W - 2 * S['pad']) * 0.34))
    y += (b.div + b.g_div) * ss

    if b.bless:
        typo.draw_block(sf.img, b.bless, (S['pad'] + 20) * ss, y, C.paper_100,
                        shadow=(0, ss * 2, ss * 10, (0, 0, 0, 200)),
                        box_w=(W - 2 * S['pad'] - 40) * ss)
        y += b.bless.height + b.g_bless * ss
    else:
        y += 16 * ss

    if g.sign_label:
        fl = typo.font('kn_var', int(ss * S['label']), weight=520)
        rl, _ = typo.ink_extents(g.sign_label, fl)
        typo.draw_text(sf.img, g.sign_label, cx, y + rl, fl,
                       mix(C.gold_300, C.paper_200, 0.35), anchor_x='c',
                       shadow=(0, ss, ss * 8, (0, 0, 0, 200)))
        y += (S['label'] * 1.35 + 12) * ss

    fn = typo.font('kn', int(ss * S['name']))
    nw = typo.text_width(Brand.name, fn) / ss
    L, gp = S['logo'], 14
    gx = W / 2 - (L + gp + nw) / 2
    ly = y / ss
    paste_logo(sf, gx, ly, L)
    rn, dn = typo.ink_extents(Brand.name, fn)
    typo.draw_text(sf.img, Brand.name, (gx + L + gp) * ss,
                   (ly + L / 2) * ss + (rn - dn) / 2, fn, C.paper_0,
                   shadow=(0, ss * 2, ss * 10, (0, 0, 0, 210)))
    y += (L + 14) * ss

    fh = typo.font('latin', int(ss * S['handle']), weight=700)
    ft = typo.font('kn_var', int(ss * S['handle'] * 0.95), weight=480)
    # A gold bead between handle and tagline, not a typed middle dot — at this
    # size "·" was a speck that read as dust on the screen. The tagline is
    # quieter than the handle, so the one thing to act on is the brightest
    # thing on the line.
    rh, _ = typo.ink_extents(Brand.handle, fh)
    rt, _ = typo.ink_extents(Brand.tagline, ft)
    w_h, w_t = typo.text_width(Brand.handle, fh), typo.text_width(Brand.tagline, ft)
    gap = 20 * ss
    base = y + max(rh, rt)
    x = cx - (w_h + 2 * gap + w_t) / 2
    typo.draw_text(sf.img, Brand.handle, x, base, fh, C.gold_400,
                   shadow=(0, ss, ss * 6, (0, 0, 0, 190)))
    orn.diamond(sf, (x + w_h + gap) / ss, (base - rh * 0.42) / ss,
                3.2, C.gold_500, 0.9)
    typo.draw_text(sf.img, Brand.tagline, x + w_h + 2 * gap, base, ft,
                   C.paper_300, shadow=(0, ss, ss * 6, (0, 0, 0, 190)))
    y += S['handle'] * 1.4 * ss

    if g.photo is not None:
        txt = disclosure_label(g.photo)
        fd = typo.font_for(txt, 'kn_var', int(ss * S['disc']), weight=470)
        rd, _ = typo.ink_extents(txt, fd)
        typo.draw_text(sf.img, txt, cx, y + 14 * ss + rd, fd, C.paper_300,
                       anchor_x='c', shadow=(0, ss, ss * 6, (0, 0, 0, 200)))


def disclosure_label(photo: Photo) -> str:
    """The compact on-poster disclosure. The nature label is the legally
    operative part; for an actual photograph, which carries no label, the
    credit stands in so no picture is ever unattributed."""
    return photo.label or f'ಕೃಪೆ: {photo.credit}'


def _plan(g: Greeting, format_key: str = 'story'):
    """Decide where everything goes, without drawing anything.

    Kept apart from _compose so the promise at the centre of this template —
    no type inside the subject band — can be tested on every format in
    milliseconds, instead of only by rendering three posters and looking."""
    g.validate()
    if format_key not in SCALE:
        raise ValueError(f'greeting formats are {sorted(SCALE)}')
    F = fmt(format_key)
    W, H, ss = F.w, F.h, F.ss
    S = SCALE[format_key]
    top = _top_limit(g, S)

    mode, sol = 'plate', None
    if g.photo is not None:
        with Image.open(g.photo.path) as probe:
            size = probe.size
        for k in (1.0, 0.93, 0.86):
            b = _blocks(g, S, W, ss, k)
            text_top = H - S['bot'] - b.total
            sol = _solve_bleed(size, g.keep_clear, W, H, top, text_top - 28)
            if sol is not None:
                mode = 'bleed'
                break
        if sol is None:
            b = _blocks(g, S, W, ss, 1.0)
            text_top = H - S['bot'] - b.total
            sol = _solve_window(size, g.keep_clear, W, S, top, text_top)
            if sol is None:
                raise ContentError(
                    f'{format_key}: this photograph cannot carry the wish without '
                    f'setting type across its subject, even framed in an arch. '
                    f'Shorten the blessing, or use a photograph with more room '
                    f'around the deity.')
            mode = 'window'
    else:
        b = _blocks(g, S, W, ss, 1.0)
        text_top = H - S['bot'] - b.total
    return SimpleNamespace(F=F, S=S, th=THEMES[g.theme], top=top, mode=mode,
                           sol=sol, b=b, text_top=text_top)


def _compose(g: Greeting, format_key: str = 'story'):
    """Build the poster. Returns (surface, layout)."""
    p = _plan(g, format_key)
    W, H, ss = p.F.w, p.F.h, p.F.ss
    S, th, top, sol, b = p.S, p.th, p.top, p.sol, p.b
    text_top, mode = p.text_top, p.mode

    sf = Surface(W, H, ss, bg=th.deep)
    vgradient(sf, 0, H, th.mid, th.deep, 1.0, 1.0)

    if mode == 'bleed':
        regions = _draw_bleed(sf, g, th, sol, W, H, top, text_top)
    elif mode == 'window':
        regions = _draw_window(sf, g, th, sol, W, H, text_top)
    else:
        regions = _draw_plate(sf, th, W, top, text_top)

    # The guard, restated on the result rather than trusted from the solver.
    subject = (sol.top, sol.bottom) if sol is not None else None
    if subject and not (subject[1] <= text_top - 8 and subject[0] >= top - 1):
        raise RuntimeError(f'greeting layout guard: the subject band '
                           f'{subject} overlaps the type ({top:.0f}–'
                           f'{text_top:.0f}). This is a solver bug.')

    orn.bokeh(sf, th.glow, f'{g.slug}|{g.occasion}|{format_key}', regions,
              n=S['bokeh'], twinkles=S['twinkles'])
    orn.corner_filigree(sf, *S['corner'])
    _draw_salutation(sf, g, S, W, th)
    _draw_wish(sf, g, S, b, th, W, text_top)
    grain(sf, Grade.grain * 0.8, Grade.grain_shadow_bias)

    return sf, SimpleNamespace(mode=mode, subject=subject, text_top=text_top,
                               top=top, scale=b.k, W=W, H=H)


def greeting(g: Greeting, path: str, format_key: str = 'story') -> str:
    """Render one greeting poster to `path`."""
    sf, _ = _compose(g, format_key)
    return sf.save(path, quality=96)


# ─────────────────────────────────────────────────────────────────────────────
#  PACKAGE
# ─────────────────────────────────────────────────────────────────────────────

FORMATS_OUT = (('story', 'wish_9x16.jpg'),
               ('post', 'wish_4x5.jpg'),
               ('square', 'wish_1x1.jpg'))


def greeting_copy(g: Greeting) -> dict:
    """Caption and forward text. The AI label travels with the post as well
    as sitting on the picture, because a forward strips the picture's context."""
    head = ' '.join(x for x in (g.salutation, g.occasion, g.wish) if x).strip()
    body = [head if head.endswith(('.', '!')) else head + '.']
    if g.blessing:
        body.append(g.blessing.rstrip('.') + '.')
    body.append(f'— {Brand.name} ಬಳಗ')
    if g.photo is not None and g.photo.label:
        body.append(g.photo.label)
    tags: list[str] = []
    for t in list(g.tags) + CORE_TAGS:
        t = t.lstrip('#').replace(' ', '')
        if t and t not in tags:
            tags.append(t)
    hashtags = ['#' + t for t in tags[:10]]
    alt = f'{g.occasion} {g.wish} — {Brand.name} ಶುಭಾಶಯ ಪೋಸ್ಟರ್'
    if g.photo is not None:
        alt += f'. {disclosure_label(g.photo)}'
        if g.photo.caption:
            alt += f': {g.photo.caption}'
    return {
        'instagram': '\n\n'.join(body) + '\n\n' + ' '.join(hashtags)
                     + f'\n\n{Brand.handle}',
        'whatsapp': '\n\n'.join(body) + f'\n\n{Brand.handle}',
        'hashtags': hashtags,
        'alt_text': alt,
    }


def package(g: Greeting, outdir: str, formats=None) -> list[tuple[str, str]]:
    """Every format plus copy, into `outdir`."""
    g.validate()
    os.makedirs(outdir, exist_ok=True)
    made = []
    for key, name in FORMATS_OUT:
        if formats and key not in formats:
            continue
        p = os.path.join(outdir, name)
        sf, lay = _compose(g, key)
        sf.save(p, quality=96)
        made.append((p, key))
        print(f'  ✓ {name:<15} {key:<7} {lay.mode}'
              + (f'  (type scale {lay.scale:.2f})' if lay.scale < 1 else ''))
    c = greeting_copy(g)
    with open(os.path.join(outdir, 'wish_copy.json'), 'w', encoding='utf-8') as f:
        json.dump(c, f, ensure_ascii=False, indent=2)
        f.write('\n')
    with open(os.path.join(outdir, 'wish_copy.txt'), 'w', encoding='utf-8') as f:
        f.write('═══ INSTAGRAM / FACEBOOK CAPTION ' + '═' * 36 + '\n\n')
        f.write(c['instagram'] + '\n\n')
        f.write('═══ WHATSAPP — STATUS & FORWARD ' + '═' * 37 + '\n\n')
        f.write(c['whatsapp'] + '\n\n')
        f.write('═══ ALT TEXT ' + '═' * 56 + '\n\n' + c['alt_text'] + '\n')
    print('  ✓ wish_copy.txt  ·  wish_copy.json')
    return made
