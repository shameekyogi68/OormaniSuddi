"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Components
==========================
The vocabulary every layout is built from. Each function draws at a given
top edge and returns the bottom edge, so layouts compose by flowing.

House rules encoded here:
  · Hairlines, never borders. Nothing gets an outlined rounded box.
  · Gold is the only accent that appears on every card. Category colour is
    confined to the rail, so a mixed feed still reads as one publication.
  · Type over photography always carries a soft shadow; type over a flat
    panel never does.
  · Small print is never smaller than T.micro (19px @1080) — below that it is
    decoration pretending to be information.
"""
from __future__ import annotations

from PIL import Image, ImageDraw

from . import typo, surface as sfx
from .tokens import (C, Role, T, Grid, category, alpha, mix, Ease, Brand)
from .content import Story, Edition


# ─────────────────────────────────────────────────────────────────────────────
#  MASTHEAD — the brand signature. Identical on every format.
# ─────────────────────────────────────────────────────────────────────────────

def masthead(sf: sfx.Surface, x: float, y: float, w: float,
             right_top: str = '', right_bot: str = '',
             scale: float = 1.0, on_photo: bool = False,
             rule_below: bool = True) -> float:
    """Logo mark + wordmark + tagline, with optional right-aligned meta."""
    mark = 68 * scale
    sh = (0, 2 * scale, 7 * scale, (0, 0, 0, 150)) if on_photo else None

    sfx.paste_logo(sf, x, y, mark, glow=0.13 if on_photo else 0.0)

    tx = x + mark + 20 * scale
    f_name = typo.font('kn', int(T.h4[0] * 0.80 * scale))
    f_tag = typo.font('kn_var', int(T.micro[0] * 1.10 * scale), weight=600)

    typo.draw_text(sf.img, Brand.name, sf.s(tx), sf.s(y + mark * 0.53),
                   typo.font('kn', int(sf.s(T.h4[0] * 0.80 * scale))),
                   Role.text_hi, shadow=_ss(sh, sf))
    typo.draw_text(sf.img, Brand.tagline, sf.s(tx), sf.s(y + mark * 0.92),
                   typo.font('kn_var', int(sf.s(T.micro[0] * 1.10 * scale)), weight=600),
                   C.gold_500, shadow=_ss(sh, sf))

    if right_top:
        typo.draw_text(sf.img, right_top, sf.s(x + w), sf.s(y + mark * 0.47),
                       typo.font('kn_var', int(sf.s(T.meta[0] * scale)), weight=600),
                       Role.text, anchor_x='r', shadow=_ss(sh, sf))
    if right_bot:
        typo.draw_text(sf.img, right_bot, sf.s(x + w), sf.s(y + mark * 0.88),
                       typo.font('kn_var', int(sf.s(T.micro[0] * scale)), weight=400),
                       Role.text_dim if not on_photo else Role.text, anchor_x='r',
                       shadow=_ss(sh, sf))

    bottom = y + mark
    if rule_below:
        bottom += 20 * scale
        sfx.gilded_rule(sf, x, bottom, x + w, 1.25 * scale,
                        on_photo=on_photo)
        bottom += 2
    return bottom


def _ss(sh, sf):
    """Scale a shadow spec into device pixels."""
    if not sh:
        return None
    dx, dy, blur, col = sh
    return (dx * sf.ss, dy * sf.ss, blur * sf.ss, col)


# ─────────────────────────────────────────────────────────────────────────────
#  EYEBROW — category rail + label. Replaces the outlined pill.
# ─────────────────────────────────────────────────────────────────────────────

def eyebrow(sf: sfx.Surface, x: float, y: float, w: float, story: Story,
            scale: float = 1.0, on_photo: bool = False,
            show_location: bool = True) -> float:
    """▌ ಅಪರಾಧ ವರದಿ   CRIME ·············· ಬ್ರಹ್ಮಾವರ"""
    cat = category(story.category)
    rail_h = 34 * scale
    sh = _ss((0, 2, 6, (0, 0, 0, 160)), sf) if on_photo else None

    # Live / breaking take a solid chip; everything else takes the quiet rail.
    cx = x
    if story.is_live:
        cx = _chip(sf, x, y, 'ನೇರ ಪ್ರಸಾರ', C.red_500, Role.text_hi, scale, dot=True) + 14 * scale
    elif story.category == 'breaking' and story.is_breaking:
        cx = _chip(sf, x, y, 'ಬ್ರೇಕಿಂಗ್', C.red_500, Role.text_hi, scale, dot=True) + 14 * scale
    else:
        sf.draw.rectangle([sf.s(x), sf.s(y), sf.s(x + Grid.rail * scale) - 1,
                           sf.s(y + rail_h) - 1], fill=cat['rail'])
        cx = x + Grid.rail * scale + 16 * scale

    f_kn = typo.font('kn_var', int(sf.s(T.meta[0] * scale)), weight=700)
    bl = y + rail_h * 0.72
    cx = typo.draw_text(sf.img, cat['kn'], sf.s(cx), sf.s(bl), f_kn,
                        Role.text_hi, shadow=sh) / sf.ss + 16 * scale

    f_en = typo.font_for(cat['en'], 'latin', int(sf.s(T.eyebrow[0] * scale)), weight=680)
    cx = typo.draw_text(sf.img, cat['en'], sf.s(cx), sf.s(bl - 1 * scale), f_en,
                        C.gold_500, tracking=T.eyebrow[2],
                        shadow=sh) / sf.ss

    # A caller that sets the location somewhere more prominent — the thumbnail
    # puts it at the foot of the column in the accent, because "which town"
    # is the reason a local viewer clicks — turns it off here rather than
    # printing the same words twice on one card.
    if story.location and show_location:
        typo.draw_text(sf.img, story.location, sf.s(x + w), sf.s(bl),
                       typo.font('kn_var', int(sf.s(T.meta[0] * scale)), weight=500),
                       Role.text if on_photo else Role.text_dim,
                       anchor_x='r', shadow=sh)
    return y + rail_h


def _chip(sf, x, y, label, bg, fg, scale=1.0, dot=False) -> float:
    f = typo.font('kn_var', int(sf.s(T.meta[0] * scale)), weight=700)
    tw = typo.text_width(label, f) / sf.ss
    pad = 15 * scale
    h = 34 * scale
    dot_w = 20 * scale if dot else 0
    w = tw + pad * 2 + dot_w
    sf.draw.rectangle([sf.s(x), sf.s(y), sf.s(x + w) - 1, sf.s(y + h) - 1], fill=bg)
    if dot:
        r = 5 * scale
        cyy = y + h / 2
        sf.draw.ellipse([sf.s(x + pad - r), sf.s(cyy - r),
                         sf.s(x + pad + r), sf.s(cyy + r)], fill=Role.text_hi)
    typo.draw_text(sf.img, label, sf.s(x + pad + dot_w), sf.s(y + h * 0.71), f, fg)
    return x + w


# ─────────────────────────────────────────────────────────────────────────────
#  HEADLINE / DECK
# ─────────────────────────────────────────────────────────────────────────────

def headline(sf: sfx.Surface, x: float, y: float, w: float, text: str,
             size_hi: int, size_lo: int, max_h: float, max_lines: int = 4,
             color=Role.text_hi, on_photo: bool = False,
             leading: float = None, align: str = 'left') -> tuple[float, int]:
    lead = leading if leading else T.h1[1]
    b = typo.fit(text, 'kn', int(sf.s(size_hi)), int(sf.s(size_lo)),
                 sf.s(w), sf.s(max_h), lead, align=align, max_lines=max_lines)
    sh = (0, sf.s(3), sf.s(16), (0, 0, 0, 175)) if on_photo else None
    typo.draw_block(sf.img, b, sf.s(x), sf.s(y), color, shadow=sh, box_w=sf.s(w))
    return (y + b.height / sf.ss, int(b.f.size / sf.ss))


def deck(sf: sfx.Surface, x: float, y: float, w: float, text: str,
         size: int = None, color=C.paper_200, on_photo: bool = False,
         max_lines: int = 3, weight: int = 450) -> float:
    size = size or T.deck[0]
    b = typo.fit(text, 'kn_var', int(sf.s(size)), int(sf.s(size * 0.78)),
                 sf.s(w), sf.s(size * T.deck[1] * max_lines),
                 T.deck[1], weight=weight, max_lines=max_lines)
    sh = (0, sf.s(2), sf.s(11), (0, 0, 0, 150)) if on_photo else None
    typo.draw_block(sf.img, b, sf.s(x), sf.s(y), color, shadow=sh, box_w=sf.s(w))
    return y + b.height / sf.ss


# ─────────────────────────────────────────────────────────────────────────────
#  FACT LIST — numbered, ruled, no bullets-in-boxes
# ─────────────────────────────────────────────────────────────────────────────

def factlist(sf: sfx.Surface, x: float, y: float, w: float, points: list[str],
             size: int = None, gap: float = 22, rules: bool = True,
             numeral_color=C.gold_500, text_color=C.paper_100,
             indent: float = 62, max_h: float = 1e9) -> float:
    """01 ─ point one
       02 ─ point two"""
    size = size or T.body[0]
    # Shrink to fit the space we were given, uniformly across all items.
    for s in range(int(size), int(size * 0.72), -1):
        f = typo.font('kn_var', int(sf.s(s)), weight=440)
        blocks = [typo.layout(p, f, sf.s(w - indent), T.body[1]) for p in points]
        total = sum(b.height / sf.ss for b in blocks) + gap * (len(points) - 1)
        if total <= max_h:
            break
    f_num = typo.font('latin', int(sf.s(size * 0.80)), weight=760)

    cy = y
    for i, (p, b) in enumerate(zip(points, blocks)):
        if i and rules:
            sfx.rule(sf, x, cy - gap / 2, x + w, Role.hairline_soft, 1.0)
        bl = cy + b.first_rise / sf.ss * 0.92
        typo.draw_text(sf.img, f'{i + 1:02d}', sf.s(x), sf.s(bl), f_num,
                       numeral_color, tracking=0.02)
        sfx.rule(sf, x + 2, bl - size * 0.20, x + indent - 20,
                 alpha(numeral_color, 0.42), 1.5)
        typo.draw_block(sf.img, b, sf.s(x + indent), sf.s(cy), text_color,
                        box_w=sf.s(w - indent))
        cy += b.height / sf.ss + gap
    return cy - gap


# ─────────────────────────────────────────────────────────────────────────────
#  TAKEAWAY — advisory strip. A gold rule, not a yellow box.
# ─────────────────────────────────────────────────────────────────────────────

def takeaway(sf: sfx.Surface, x: float, y: float, w: float, text: str,
             label: str = 'ಗಮನಿಸಿ', size: int = None, accent=C.gold_500) -> float:
    size = size or T.body_sm[0]
    f_lab = typo.font('kn_var', int(sf.s(size * 0.80)), weight=760)
    f = typo.font('kn_var', int(sf.s(size)), weight=460)
    pad = 26
    b = typo.layout(text, f, sf.s(w - pad - 22), T.body[1])
    lab_h = size * 1.5
    h = lab_h + b.height / sf.ss + 12
    sfx.panel(sf, [x, y, x + w, y + h], alpha(accent, 0.055))
    sfx.gilded_vrule(sf, x, y, y + h, 3,
                     lo=mix(accent, (0, 0, 0), 0.18),
                     hi=mix(accent, (255, 255, 255), 0.10))
    typo.draw_text(sf.img, label.upper() if label.isascii() else label,
                   sf.s(x + pad), sf.s(y + lab_h * 0.68), f_lab, accent,
                   tracking=0.06 if label.isascii() else 0)
    typo.draw_block(sf.img, b, sf.s(x + pad), sf.s(y + lab_h), C.paper_100,
                    box_w=sf.s(w - pad - 22))
    return y + h


# ─────────────────────────────────────────────────────────────────────────────
#  PROVENANCE — the disclosure line under a photograph
# ─────────────────────────────────────────────────────────────────────────────

def credit_strip(sf: sfx.Surface, x: float, y: float, w: float, story: Story,
                 color=None, align_right_extra: str = '') -> float:
    """Image nature + caption + photographer. Small, quiet, always present."""
    line = story.credit_line
    if not line:
        return y
    f = typo.font('kn_var', int(sf.s(T.micro[0])), weight=420)
    col = color or alpha(C.paper_200, 0.78)
    b = typo.layout(line, f, sf.s(w - (170 if align_right_extra else 0)), 1.34)
    typo.draw_block(sf.img, b, sf.s(x), sf.s(y), col,
                    shadow=(0, sf.s(1), sf.s(6), (0, 0, 0, 170)))
    if align_right_extra:
        typo.draw_text(sf.img, align_right_extra, sf.s(x + w),
                       sf.s(y + b.first_rise / sf.ss), f, col, anchor_x='r',
                       shadow=(0, sf.s(1), sf.s(6), (0, 0, 0, 170)))
    return y + b.height / sf.ss


def sourceline(sf: sfx.Surface, x: float, y: float, w: float, story: Story,
               show_status: bool = True, scale: float = 1.0) -> float:
    """ಮೂಲ: … on the left, verification status on the right.

    The status is printed whatever it says. A card that admits it is still
    being checked is worth more than one that pretends otherwise."""
    f = typo.font('kn_var', int(sf.s(T.micro[0] * scale)), weight=460)
    bl = y + T.micro[0] * scale * 0.86
    right_w = 0.0
    if show_status:
        st = story.status_kn
        col = {'confirmed': C.gold_500, 'official': C.sea_400,
               'developing': C.paper_300, 'unconfirmed': C.red_400}[story.status]
        right_w = typo.text_width(st, f) / sf.ss + 26 * scale
        r = 4.5 * scale
        cyy = bl - T.micro[0] * scale * 0.30
        sf.draw.ellipse([sf.s(x + w - right_w + 6 * scale - r), sf.s(cyy - r),
                         sf.s(x + w - right_w + 6 * scale + r), sf.s(cyy + r)],
                        fill=col)
        typo.draw_text(sf.img, st, sf.s(x + w), sf.s(bl), f, col, anchor_x='r')
    typo.draw_text(sf.img,
                   typo.ellipsize(story.source_line, f, sf.s(w - right_w - 24)),
                   sf.s(x), sf.s(bl), f, Role.text_faint)
    return bl + T.micro[0] * scale * 0.4


# ─────────────────────────────────────────────────────────────────────────────
#  FOOTER
# ─────────────────────────────────────────────────────────────────────────────

def footer(sf: sfx.Surface, x: float, y: float, w: float,
           left: str = Brand.handle, right: str = '',
           handle_gold: bool = True) -> float:
    sfx.faded_rule(sf, x, y, x + w, Role.hairline, 1.0)
    y += 22
    f_h = typo.font_for(left, 'latin', int(sf.s(T.meta[0])), weight=700)
    typo.draw_text(sf.img, left, sf.s(x), sf.s(y + T.meta[0] * 0.82), f_h,
                   C.gold_500 if handle_gold else Role.text_hi,
                   tracking=0.015)
    if right:
        typo.draw_text(sf.img, right, sf.s(x + w), sf.s(y + T.meta[0] * 0.82),
                       typo.font_for(right, 'kn_var', int(sf.s(T.micro[0])), weight=460),
                       Role.text_dim, anchor_x='r')
    return y + T.meta[0] * 1.1


# ─────────────────────────────────────────────────────────────────────────────
#  DATA & QUOTE
# ─────────────────────────────────────────────────────────────────────────────

def stat_row(sf: sfx.Surface, x: float, y: float, w: float,
             stats: list[tuple[str, str]], accent=C.gold_500) -> float:
    """Big numerals with a Kannada label beneath. Separated by hairlines, not
    boxes — numbers are already loud enough."""
    n = max(1, len(stats))
    colw = w / n
    f_v = typo.font('latin', int(sf.s(T.h2[0])), weight=760, width=92)  # numerals only
    f_l = typo.font('kn_var', int(sf.s(T.micro[0] * 1.06)), weight=520)
    h = 0.0
    for i, (val, lab) in enumerate(stats):
        cx = x + colw * i
        if i:
            sfx.vrule(sf, cx - 1, y + 4, y + T.h2[0] * 1.5, Role.hairline, 1.0)
        typo.draw_text(sf.img, val, sf.s(cx + (18 if i else 0)),
                       sf.s(y + T.h2[0] * 0.80), f_v, accent)
        lb = typo.layout(lab, f_l, sf.s(colw - 30), 1.32)
        typo.draw_block(sf.img, lb, sf.s(cx + (18 if i else 0)),
                        sf.s(y + T.h2[0] * 1.02), Role.text_dim)
        h = max(h, T.h2[0] * 1.02 + lb.height / sf.ss)
    return y + h


def pullquote(sf: sfx.Surface, x: float, y: float, w: float, text: str,
              attrib: str = '', size: int = None, accent=C.gold_500) -> float:
    size = size or T.h3[0]
    sfx.vrule(sf, x, y, y + 10, accent, 3)     # placeholder, redrawn to height
    f = typo.font('kn_serif', int(sf.s(size)))
    b = typo.layout(f'"{text}"', f, sf.s(w - 46), 1.34)
    typo.draw_block(sf.img, b, sf.s(x + 46), sf.s(y), Role.text_hi, box_w=sf.s(w - 46))
    cy = y + b.height / sf.ss
    sfx.vrule(sf, x, y, cy, accent, 3)
    if attrib:
        cy += 26
        typo.draw_text(sf.img, f'— {attrib}', sf.s(x + 46), sf.s(cy),
                       typo.font('kn_var', int(sf.s(T.meta[0])), weight=600),
                       C.gold_500)
        cy += 10
    return cy


# ─────────────────────────────────────────────────────────────────────────────
#  BACKGROUND TREATMENTS
# ─────────────────────────────────────────────────────────────────────────────

def horizon(sf: sfx.Surface, y: float, intensity: float = 0.5):
    """A soft sunset band across the page — the logo's horizon, abstracted.
    Used on cards with no photograph so they still feel like this channel."""
    sfx.radial_glow(sf, sf.w * 0.5, y, sf.w * 0.85, C.gold_600, 0.09 * intensity)
    sfx.radial_glow(sf, sf.w * 0.5, y, sf.w * 0.40, C.gold_300, 0.12 * intensity)
    sfx.gilded_rule(sf, sf.w * 0.06, y, sf.w * 0.94, 1.0)


def page_base(sf: sfx.Surface, tone: float = 1.0):
    """Base ink with a faint vertical lift, so large flat areas breathe."""
    sfx.vgradient(sf, 0, sf.h, C.ink_900, C.ink_950, 1.0, 1.0)
    sfx.radial_glow(sf, sf.w * 0.5, sf.h * 0.18, sf.w * 1.15, C.ink_700, 0.30 * tone)
    # A whisper of grounding at the foot — lit from above, anchored below,
    # the light logic of a photographed page rather than a flat fill.
    sfx.radial_glow(sf, sf.w * 0.5, sf.h * 1.02, sf.w * 0.95, C.ink_950, 0.22 * tone)
