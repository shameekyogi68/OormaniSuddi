"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Paper & Red, the news look (D92).
=================================================
The drawing kit shared by ಸುದ್ದಿ ಸಾರ, ಮುಖ್ಯ ಸುದ್ದಿ and ಸ್ಪೀಡ್ ನ್ಯೂಸ್. Everything
takes a `Surface` and delivery-pixel coordinates, like the rest of the engine.

Colour by role, from the logo and nowhere else (tokens.C):
  RED   the news — the kicker, ಬ್ರೇಕಿಂಗ್, the half of a headline after its colon
  GOLD  the brand — the line under a photograph, the stroke under the red bug,
        numeral chips, accent rules. A FILL on paper, never small type: the
        sunset gold on paper is 1.7:1. Gold words use gold_800.
  INK / PAPER  everything else.

A crime or death headline is set in ink only. Red on a person's name reads
as a verdict whatever the words say.
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageEnhance

from . import typo
from .content import Story
from .surface import Surface, cover, house_grade, logo
from .tokens import C, Brand, Paper as P, category

PAPER = C.paper_50
INK = C.ink_950
BODY = C.ink_800
GREY = C.ink_500
RULE = C.paper_200
RED = C.red_500
GOLD = C.gold_500
GOLD_MARK = C.gold_600       # small gold marks, where the sunset gold vanishes
GOLD_TYPE = C.gold_800       # gold words on paper
WHITE = C.paper_0

# Categories whose headline never carries red. D92 point 5.
INK_ONLY = ('crime', 'obituary')

# Headlines are Noto Sans Kannada at ExtraBold: the approved Paper & Red look.
HEAD_WEIGHT = 800
HEAD_FLOOR = 40      # px; below this a headline is a caption

COLONS = (':', '：')


def page(W: int, H: int) -> Surface:
    return Surface(W, H, 2, bg=(*PAPER, 255))


def _rect(sf: Surface, box, fill):
    sf.draw.rectangle([sf.s(box[0]), sf.s(box[1]), sf.s(box[2]) - 1,
                       sf.s(box[3]) - 1], fill=fill)


# ─────────────────────────────────────────────────────────────────────────────
#  PHOTOGRAPH
# ─────────────────────────────────────────────────────────────────────────────

def photo(sf: Surface, ph, box) -> bool:
    """Place a story's photograph in `box`, credited inside its own corner.

    A real photograph gets the house grade and nothing else. A generated one
    also loses some colour and contrast — the glossy, over-saturated look is
    the first thing that marks a picture as AI, and the disclosure already
    says it is. Returns False when there is no picture to place.
    """
    if not ph or not ph.path or not os.path.exists(ph.path):
        return False
    W = int((box[2] - box[0]) * sf.ss)
    H = int((box[3] - box[1]) * sf.ss)
    im = cover(Image.open(ph.path).convert('RGB'), W, H, ph.focal)
    im = house_grade(im, strength=0.6)
    if ph.is_synthetic:
        im = ImageEnhance.Color(im).enhance(P.ai_saturation)
        im = ImageEnhance.Contrast(im).enhance(P.ai_contrast)
    sf.img.alpha_composite(im.convert('RGBA'),
                           (int(box[0] * sf.ss), int(box[1] * sf.ss)))
    credit(sf, ph.disclosure, box)
    return True


def credit(sf: Surface, text: str, box):
    """The disclosure, bottom-right INSIDE the picture it describes, on a soft
    scrim — the label has to travel with the image (IT Rules, D57)."""
    if not text:
        return
    x0, y0, x1, y1 = box
    h = 110
    ramp = Image.linear_gradient('L').resize((int((x1 - x0) * sf.ss),
                                              int(h * sf.ss)))
    ramp = ramp.point(lambda v: int(v * 0.62))
    shade = Image.new('RGBA', ramp.size, (0, 0, 0, 255))
    shade.putalpha(ramp)
    sf.img.alpha_composite(shade, (int(x0 * sf.ss), int((y1 - h) * sf.ss)))
    f = typo.font_for(text, 'kn_var', sf.s(P.credit), weight=560)
    text = typo.ellipsize(text, f, sf.s(x1 - x0 - 2 * P.margin), sep='  •  ')
    typo.draw_text(sf.img, text, sf.s(x1 - P.margin), sf.s(y1 - 22),
                   f, (*WHITE, 238), anchor_x='r')


def sunline(sf: Surface, y: float, x0: float = 0, x1: float | None = None,
            h: float = P.sunline):
    """The gold horizon under every photograph."""
    _rect(sf, (x0, y, sf.w if x1 is None else x1, y + h), GOLD)


# ─────────────────────────────────────────────────────────────────────────────
#  BRAND
# ─────────────────────────────────────────────────────────────────────────────

def bug(sf: Surface, x: float, y: float, size: int = P.bug) -> float:
    """The house mark: ಊರ್ಮನಿ ಸುದ್ದಿ in white on a flat red block, with the
    logo's gold stroke beneath it — its red ಸುದ್ದಿ band over the gold tagline.
    Returns the right edge."""
    f = typo.font('kn', sf.s(size), weight=HEAD_WEIGHT)
    w = typo.text_width(Brand.name, f) / sf.ss
    pad, h = size * 0.55, size * 1.72
    _rect(sf, (x, y, x + w + 2 * pad, y + h), RED)
    _rect(sf, (x, y + h, x + w + 2 * pad, y + h + max(5, size // 6)), GOLD)
    typo.draw_text(sf.img, Brand.name, sf.s(x + pad),
                   sf.s(y + h * 0.5 + size * 0.36), f, WHITE)
    return x + w + 2 * pad


def roundlogo(sf: Surface, x: float, y: float, size: float):
    sf.img.alpha_composite(logo(int(sf.s(size))), (int(sf.s(x)), int(sf.s(y))))


def chip(sf: Surface, x: float, y: float, n: int, size: int = 34,
         of: int | None = None) -> float:
    """A numeral on a gold chip — the logo's sun, as a counter. Returns the
    right edge of what was drawn."""
    t = f'{n:02d}'
    f = typo.font('kn_var', sf.s(size), weight=800)
    w = typo.text_width(t, f) / sf.ss
    p = size * 0.34
    _rect(sf, (x, y, x + w + 2 * p, y + size * 1.36), GOLD)
    typo.draw_text(sf.img, t, sf.s(x + p), sf.s(y + size * 1.02), f, INK)
    x2 = x + w + 2 * p
    if of:
        g = typo.font('kn_var', sf.s(int(size * 0.8)), weight=600)
        typo.draw_text(sf.img, f'/ {of:02d}', sf.s(x2 + 12),
                       sf.s(y + size * 1.02), g, GREY)
        x2 += 12 + typo.text_width(f'/ {of:02d}', g) / sf.ss
    return x2


def accent(sf: Surface, x: float, y: float, w: float = 96, h: float = 8):
    _rect(sf, (x, y, x + w, y + h), GOLD)


def footer(sf: Surface, page_label: str = ''):
    """Hairline, a gold mark, the handle; the page number on the right."""
    W, H, m = sf.w, sf.h, P.margin
    y = H - P.footer_h
    _rect(sf, (m, y, W - m, y + 2), RULE)
    _rect(sf, (m, y + 32, m + 24, y + 56), GOLD)
    f = typo.font('kn_var', sf.s(P.meta), weight=620)
    typo.draw_text(sf.img, Brand.handle, sf.s(m + 40), sf.s(y + 54), f, INK)
    if page_label:
        typo.draw_text(sf.img, page_label, sf.s(W - m), sf.s(y + 54), f, GREY,
                       anchor_x='r')


# ─────────────────────────────────────────────────────────────────────────────
#  TYPE
# ─────────────────────────────────────────────────────────────────────────────

def kicker(sf: Surface, x: float, y: float, story: Story,
           breaking: bool = False, size: int = P.kicker) -> float:
    """CATEGORY / place — or ಬ್ರೇಕಿಂಗ್ / place. `y` is the top; returns the
    bottom."""
    f = typo.font('kn_var', sf.s(size), weight=720)
    base = y + size * 0.92
    if breaking:
        t = 'ಬ್ರೇಕಿಂಗ್'
        w = typo.text_width(t, f) / sf.ss
        _rect(sf, (x, y - 6, x + w + 28, y + size + 14), RED)
        typo.draw_text(sf.img, t, sf.s(x + 14), sf.s(base), f, WHITE)
        x += w + 28 + 18
    else:
        t = category(story.category)['kn']
        typo.draw_text(sf.img, t, sf.s(x), sf.s(base), f, RED)
        x += typo.text_width(t, f) / sf.ss + 16
    place = (story.location or '').strip() or Brand.coverage
    typo.draw_text(sf.img, '/', sf.s(x), sf.s(base), f, RULE)
    x += typo.text_width('/', f) / sf.ss + 16
    typo.draw_text(sf.img, place, sf.s(x), sf.s(base),
                   typo.font_for(place, 'kn_var', sf.s(size), weight=620), GREY)
    return y + size * 1.3


def split_headline(text: str) -> tuple[str, str]:
    """(before the colon, after it). The colon stays with the first half."""
    for c in COLONS:
        if c in text:
            a, b = text.split(c, 1)
            if a.strip() and b.strip():
                return a.strip() + c, b.strip()
    return text.strip(), ''


def headline(sf: Surface, x: float, y: float, w: float, text: str,
             max_h: float, hi: int = P.head_hi, lo: int = P.head_lo,
             ink_only: bool = False, align: str = 'left') -> float:
    """The headline, largest size that fits `w` x `max_h`.

    A colon ends a line: the first half in ink, the second in red — the
    reference post's grammar, and the news half is the red one. With no colon
    the whole line is ink. Returns the bottom edge.
    """
    a, b = split_headline(text)
    lead = P.head_lead

    def set_at(size):
        f = typo.font('kn', sf.s(size), weight=HEAD_WEIGHT)
        ba = typo.layout(a, f, sf.s(w), lead, align=align)
        bb = typo.layout(b, f, sf.s(w), lead, align=align) if b else None
        gap = ba.lh - ba.first_rise - ba.last_drop if bb else 0
        return ba, bb, gap, (ba.height + gap + (bb.height if bb else 0)) / sf.ss

    fits = [s_ for s_ in range(hi, lo - 1, -2) if set_at(s_)[3] <= max_h]
    if not fits:
        # Copy longer than the room: shrink rather than spill into the footer
        # or under the Reels caption — down to a floor that still reads on a
        # phone. Past that the copy is too long, and preflight says so.
        fits = [s_ for s_ in range(lo - 2, HEAD_FLOOR - 1, -2)
                if set_at(s_)[3] <= max_h][:1] or [HEAD_FLOOR]
    # The ink half reads best as one line — the reference post's shape — so
    # give up a little size for it, but never below four-fifths of the
    # largest size that fits.
    size = fits[0] if fits else lo
    if b and fits:
        one = [s_ for s_ in fits if set_at(s_)[0].n == 1 and s_ >= fits[0] * 0.8]
        if one:
            size = one[0]
    ba, bb, gap, _h = set_at(size)
    col_b = INK if ink_only else RED
    bottom = typo.draw_block(sf.img, ba, sf.s(x), sf.s(y), INK,
                             box_w=sf.s(w))
    if bb:
        bottom = typo.draw_block(sf.img, bb, sf.s(x), bottom + gap, col_b,
                                 box_w=sf.s(w))
    return bottom / sf.ss


def body(sf: Surface, x: float, y: float, w: float, text: str,
         size: int = P.body, weight: int = 560, fill=INK,
         max_h: float | None = None, lo: int = 34) -> float:
    """A paragraph in the body face; shrinks toward `lo` to fit `max_h`."""
    if max_h:
        b = typo.fit(text, 'kn_var', sf.s(size), sf.s(lo), sf.s(w),
                     sf.s(max_h), P.body_lead, weight=weight)
    else:
        b = typo.layout(text, typo.font('kn_var', sf.s(size), weight=weight),
                        sf.s(w), P.body_lead)
    return typo.draw_block(sf.img, b, sf.s(x), sf.s(y), fill,
                           box_w=sf.s(w)) / sf.ss


def meta(sf: Surface, x: float, y: float, text: str, fill=GREY,
         size: int = P.meta, weight: int = 520, anchor: str = 'l',
         max_w: float | None = None):
    """One line of small print; `y` is the baseline."""
    f = typo.font_for(text, 'kn_var', sf.s(size), weight=weight)
    if max_w:
        text = typo.ellipsize(text, f, sf.s(max_w))
    typo.draw_text(sf.img, text, sf.s(x), sf.s(y), f, fill, anchor_x=anchor)


def grievance(sf: Surface, y: float):
    """IT Rules 2021 Part III: the Grievance Officer, on every closing slide.
    Wrapped, never cut — a contact with half an email address is no contact.
    `y` is the baseline of the LAST line."""
    g = Brand.grievance_line()
    if not g:
        return
    f = typo.font_for(g, 'kn_var', sf.s(22), weight=520)
    b = typo.layout(g, f, sf.s(sf.w - 2 * P.margin), 1.4, align='center')
    top = sf.s(y) - b.height + b.last_drop
    typo.draw_block(sf.img, b, sf.s(P.margin), top, GREY,
                    box_w=sf.s(sf.w - 2 * P.margin))


def ink_only(story: Story) -> bool:
    return story.category in INK_ONLY


def disclosure_line(story: Story) -> str:
    return story.photo.disclosure if story.photo else ''
