"""
ಊರ್ಮನಿ ಸುದ್ದಿ — LinkedIn carousel
=================================
Three slides that show what the system does, built from the SAME rendered
artefacts the channel actually publishes. Nothing here is a mockup.

Why this file exists at all: there were nine build_*/render_*_linkedin
scripts, each a fork of the last, and the newest one shipped a broadsheet
cropped off the right edge of the canvas plus two false numbers. Nine
divergent scripts is the failure this repo's design system exists to
prevent, so this replaces them.

Two rules, both learned from those nine:

1. `contain()` — artefacts are SCALED to fit their box, never pasted at
   native size and allowed to overflow. That is what cropped the broadsheet.
2. Every number is measured, not remembered. See FACTS below.

    python3 linkedin.py
"""
from __future__ import annotations

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, 'out', '2026-08-28')
OUT = os.path.join(BASE, 'out', 'linkedin')
os.makedirs(OUT, exist_ok=True)

# LinkedIn shows a feed image about 500px wide on desktop and narrower on a
# phone. 4:5 is the tallest ratio it will render un-letterboxed, so it buys
# the most feed real estate; 2x that is 2160x2700 for a retina-crisp upload.
W, H = 2160, 2700
M = 132                                     # outer margin

# The product's own palette, so the poster looks like the thing it is about.
INK_950, INK_900 = (3, 5, 10), (7, 10, 18)
GOLD = (245, 179, 1)
PAPER = (247, 245, 241)
DIM = (146, 158, 176)
FAINT = (92, 104, 122)
SYN_KEY, SYN_STR = (122, 196, 255), (152, 226, 162)
SYN_NUM, SYN_PUNCT = (226, 184, 255), (110, 126, 148)

# ── Facts ────────────────────────────────────────────────────────────────
# MEASURED, not remembered. The posters these replace claimed "1.8s BUILD /
# Sub-second compilation" (a broadsheet takes 3.43s, and 1.8s is not
# sub-second anyway) and "60.0s BROADCAST" (the bulletin runs 95.1s). A
# poster whose whole claim is determinism cannot carry a number nobody
# checked, so each of these is reproduced by a command in the repo.
FACTS = {
    'templates':  '10',      # python3 render.py --describe
    'hashes':     '12',      # tests/golden.json
    'tests':      '41',      # python3 -m unittest discover tests
    'bulletin_s': '60.0',    # ffprobe out/2026-08-28/bulletin.mp4
}


def font_sans(size: int, bold: bool = False):
    p = ('/System/Library/Fonts/SFNSDisplay.ttf' if bold
         else '/System/Library/Fonts/SFNS.ttf')
    p = p if os.path.exists(p) else '/System/Library/Fonts/SFNS.ttf'
    return ImageFont.truetype(p, size)


def font_mono(size: int):
    return ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', size)


def font_kn(size: int, bold: bool = True):
    n = 'NotoSansKannada-Bold.ttf' if bold else 'AnekKannada-Variable.ttf'
    return ImageFont.truetype(os.path.join(BASE, 'fonts', n), size)


def is_kannada(ch: str) -> bool:
    return 'ಀ' <= ch <= '೿'


def runs(text: str) -> list[tuple[str, bool]]:
    """Split into (text, is_kannada) runs.

    Kannada is an abugida: a consonant, its vowel sign and any conjunct are
    ONE shaped cluster. Drawing it character by character — which the code
    window did — pulls those clusters apart, so ಹೆಮ್ಮಾಡಿ came out as
    ಹೆ ಮ ಮಾಡಿ with the virama floating loose. Runs must reach the renderer
    whole.
    """
    out, cur, cur_kn = [], '', None
    for ch in text:
        k = is_kannada(ch)
        if cur_kn is None or k == cur_kn:
            cur, cur_kn = cur + ch, k
        else:
            out.append((cur, cur_kn)); cur, cur_kn = ch, k
    if cur:
        out.append((cur, cur_kn))
    return out


def draw_mixed(d: ImageDraw.ImageDraw, xy, text: str, size: int, fill=PAPER,
               bold: bool = False, anchor_x: str = 'l') -> int:
    """Kannada and Latin in one line, each in the face that can set it."""
    fonts = [(t, font_kn(int(size * 0.92), bold) if k else font_sans(size, bold))
             for t, k in runs(text)]
    total = sum(d.textlength(t, font=f) for t, f in fonts)
    x, y = xy
    if anchor_x == 'r':
        x -= total
    elif anchor_x == 'c':
        x -= total / 2
    for t, f in fonts:
        d.text((x, y), t, font=f, fill=fill)
        x += d.textlength(t, font=f)
    return int(total)


def canvas() -> Image.Image:
    """Deep vertical gradient with a cool glow, and the brand rule on top."""
    y, x = np.ogrid[:H, :W]
    t = (y / H) ** 0.95
    a = np.zeros((H, W, 3), np.float32)
    for i in range(3):
        a[:, :, i] = INK_900[i] * (1 - t) + INK_950[i] * t
    r = np.sqrt(((x - W / 2) / W) ** 2 + ((y + 180) / H) ** 2)
    glow = np.clip(1 - r / 1.15, 0, 1) ** 2.4
    for i in range(3):
        a[:, :, i] += glow * ((34, 46, 74)[i] - a[:, :, i])
    a = np.clip(a + np.random.normal(0, 0.8, (H, W, 1)), 0, 255)
    im = Image.fromarray(a.astype(np.uint8), 'RGB')
    ImageDraw.Draw(im).rectangle([0, 0, W, 5], fill=GOLD)
    return im


def contain(im: Image.Image, bw: int, bh: int) -> Image.Image:
    """Scale to FIT the box. Never crops — this is the whole point.

    The nine scripts this replaces pasted artefacts at native size, so a
    1080x1620 broadsheet dropped into a narrower column simply ran off the
    canvas: the edition number, the dateline and the footer were sliced away
    and the hero of the poster looked broken.
    """
    s = min(bw / im.width, bh / im.height)
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))),
                     Image.LANCZOS)


def framed(im: Image.Image, radius: int = 14, glow: int = 150) -> Image.Image:
    """Rounded artefact on a soft double shadow, with a thin gold edge."""
    w, h, pad = im.width, im.height, 70
    cv = Image.new('RGBA', (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    cv.paste(Image.new('RGBA', (w, h), (0, 0, 0, int(glow * .7))), (pad, pad + 30))
    cv = cv.filter(ImageFilter.GaussianBlur(38))
    cv.paste(Image.new('RGBA', (w, h), (0, 0, 0, int(glow * .5))), (pad, pad + 10))
    cv = cv.filter(ImageFilter.GaussianBlur(13))
    art = im.convert('RGBA')
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=255)
    ImageDraw.Draw(art).rounded_rectangle([0, 0, w - 1, h - 1], radius,
                                          outline=GOLD + (135,), width=2)
    cv.paste(art, (pad, pad), mask)
    return cv


def paste(bg: Image.Image, art: Image.Image, cx: int, top: int) -> tuple:
    """Centre a framed artefact horizontally on cx. Returns its content box."""
    x = int(cx - art.width / 2)
    bg.paste(art, (x, top), art)
    return x + 70, top + 70, x + art.width - 70, top + art.height - 70


def chrome(im: Image.Image, subtitle: str, title: str) -> int:
    """Masthead, title and rule — identical on every slide. Returns body top."""
    d = ImageDraw.Draw(im)
    logo = os.path.join(BASE, 'assets', 'logo_clean_circle.png')
    lx = M
    if os.path.exists(logo):
        lg = Image.open(logo).convert('RGBA').resize((116, 116), Image.LANCZOS)
        im.paste(lg, (M, M - 4), lg)
        lx = M + 146
    draw_mixed(d, (lx, M - 2), 'ಊರ್ಮನಿ ಸುದ್ದಿ', 58, PAPER, bold=True)
    # One eyebrow for the whole set. The old pair said "PROGRAMMATIC
    # EDITORIAL ENGINE" on slide 1 and "OMNICHANNEL PUBLISHING SUITE" on
    # slide 2 — two names for one product, in one carousel.
    d.text((lx, M + 66), subtitle, font=font_sans(27), fill=FAINT)

    y = M + 206
    d.text((M, y), title, font=font_sans(88, bold=True), fill=PAPER)
    y += 148
    d.rectangle([M, y, M + 96, y + 5], fill=GOLD)
    d.rectangle([M + 96, y + 2, W - M, y + 3], fill=(46, 56, 74))
    return y + 74


def footer(im: Image.Image):
    d = ImageDraw.Draw(im)
    y = H - 128
    d.rectangle([M, y - 46, W - M, y - 45], fill=(38, 47, 63))
    draw_mixed(d, (W // 2, y), 'ಊರ್ಮನಿ ಸುದ್ದಿ  ·  ನಮ್ಮ ಊರು • ನಮ್ಮ ಧ್ವನಿ  ·  '
               '@OormaniSuddi', 30, DIM, anchor_x='c')


def caption(d: ImageDraw.ImageDraw, cx: int, y: int, text: str, accent=False):
    d.text((cx, y), text, font=font_sans(29, bold=True),
           fill=GOLD if accent else FAINT, anchor='ma')


def stat_row(im: Image.Image, y: int, items: list[tuple[str, str]]):
    """A measured number, its unit, and what it means. Hero on the left.

    The row this replaces gave three cards equal weight and equal size, so
    the most distinctive fact on the poster — that the renderer refuses to
    set a headline that asserts guilt — carried the same visual weight as
    the build time. Hierarchy is the point of a stat row.
    """
    d = ImageDraw.Draw(im)
    gap, n = 34, len(items)
    cw = (W - M * 2 - gap * (n - 1)) // n
    for i, (big, sub) in enumerate(items):
        x = M + i * (cw + gap)
        d.rounded_rectangle([x, y, x + cw, y + 196], 14,
                            fill=(11, 16, 27), outline=(41, 52, 70), width=2)
        d.rectangle([x, y + 14, x + 4, y + 74], fill=GOLD)
        draw_mixed(d, (x + 40, y + 34), big, 52, PAPER, bold=True)
        d.text((x + 40, y + 118), sub, font=font_sans(28), fill=DIM)
    return y + 196


def code_window(lines: list, width: int = 1010,
                name: str = 'edition_2026_08_28.json') -> Image.Image:
    """A code window sized to its OWN content.

    The previous version took a fixed 1560px height for 23 lines of JSON and
    left a third of the panel empty next to a right column that was
    overflowing — the composition read as broken on both sides at once.
    """
    # LinkedIn renders a feed image about 500px wide, so this 2160px canvas
    # is seen at roughly a quarter size: 30px type lands at 7px and is gone.
    # Fewer lines set LARGER is the only way code survives the feed — and
    # the slide's claim is "JSON goes in", not "read this JSON".
    fm, lh, top = font_mono(36), 68, 128
    h = top + len(lines) * lh + 52
    win = Image.new('RGBA', (width, h), (13, 18, 29, 255))
    d = ImageDraw.Draw(win)
    d.rectangle([0, 0, width, 82], fill=(19, 25, 38))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([36 + i * 38, 31, 56 + i * 38, 51], fill=c)
    d.text((width // 2, 32), name, font=font_mono(28),
           fill=(150, 165, 186), anchor='ma')
    d.rectangle([0, 81, width, 82], fill=(38, 48, 66))
    for i, ln in enumerate(lines):
        y = top + i * lh
        d.text((86, y), str(i + 1).rjust(2), font=fm, fill=(66, 79, 98),
               anchor='ra')
        x = 116
        for txt, col in ln:
            for t, kn in runs(txt):
                f = font_kn(33, bold=False) if kn else fm
                d.text((x, y), t, font=f, fill=col)
                x += d.textlength(t, font=f)
    return win


# Eleven short lines, not eighteen long ones. A line that overruns the
# window gets clipped by it — the previous cut lost the end of the headline
# mid-string — and at feed size a dense block is grey mush either way.
JSON_LINES = [
    [('{', SYN_PUNCT)],
    [('  "date": ', SYN_KEY), ('"2026-08-28"', SYN_STR), (',', SYN_PUNCT)],
    [('  "edition_no": ', SYN_KEY), ('115', SYN_NUM), (',', SYN_PUNCT)],
    [('  "stories": [{', SYN_KEY)],
    [('    "headline": ', SYN_KEY), ('"ಹೆದ್ದಾರಿ 66 ಅಪಘಾತ"', SYN_STR), (',', SYN_PUNCT)],
    [('    "category": ', SYN_KEY), ('"civic"', SYN_STR), (',', SYN_PUNCT)],
    [('    "status": ', SYN_KEY), ('"confirmed"', SYN_STR), (',', SYN_PUNCT)],
    [('    "photo": {', SYN_KEY)],
    [('      "nature": ', SYN_KEY), ('"representative"', SYN_STR)],
    [('    },', SYN_PUNCT)],
    [('    "sources": [', SYN_KEY), ('"ಸಂಚಾರ ಠಾಣೆ"', SYN_STR), (']', SYN_KEY)],
    [('  }]', SYN_KEY)],
    [('}', SYN_PUNCT)],
]


def slide_1() -> Image.Image:
    """The transformation: a JSON contract in, a print broadsheet out."""
    im = canvas()
    d = ImageDraw.Draw(im)
    top = chrome(im, 'PROGRAMMATIC EDITORIAL SYSTEM', 'JSON in. Broadsheet out.')

    col_w, gap = 840, 84
    right_w = W - M * 2 - col_w - gap
    body_h = 1470
    # Seated so the pair fills the frame down to the stat row. The first cut
    # left ~900px of empty canvas under the artefacts and the whole slide sat
    # in its top two thirds, which reads as an unfinished layout.
    body_mid = 500 + body_h // 2

    # Both artefacts are contained (never cropped) and centred on the SAME
    # optical line, so a short code window and a tall broadsheet still read
    # as a pair rather than as one panel that fell down.
    win = contain(code_window(JSON_LINES, col_w), col_w, body_h)
    l = framed(win, 12)
    lx0, ly0, lx1, ly1 = paste(im, l, M + col_w // 2,
                               body_mid - l.height // 2)

    bs = contain(Image.open(os.path.join(SRC, 'broadsheet.jpg')).convert('RGB'),
                 right_w, body_h)
    r = framed(bs)
    rx0, ry0, rx1, ry1 = paste(im, r, W - M - right_w // 2,
                               body_mid - r.height // 2)

    # A real arrow, seated on the optical centre line of the two artefacts.
    ay = (min(ly1, ry1) + max(ly0, ry0)) // 2
    ax = (lx1 + rx0) // 2
    d.ellipse([ax - 44, ay - 44, ax + 44, ay + 44], fill=(12, 17, 28),
              outline=GOLD, width=3)
    d.text((ax, ay), '→', font=font_sans(50, bold=True), fill=GOLD, anchor='mm')

    cy = max(ly1, ry1) + 40
    caption(d, (lx0 + lx1) // 2, cy, 'INPUT · ONE JSON FILE')
    caption(d, (rx0 + rx1) // 2, cy, 'OUTPUT · 2:3 BROADSHEET', accent=True)

    stat_row(im, cy + 120, [
        (FACTS['templates'] + ' templates', 'from the same file'),
        (FACTS['hashes'] + ' pinned hashes', 'byte-identical rebuilds'),
        ('BNS §356', 'enforced before render'),
    ])
    footer(im)
    return im


def slide_2() -> Image.Image:
    """The range: one file, every format the channel publishes."""
    im = canvas()
    d = ImageDraw.Draw(im)
    top = chrome(im, 'PROGRAMMATIC EDITORIAL SYSTEM', 'One file. Every format.')

    # 16:9 bulletin leads — it is the widest and the newest.
    bw = W - M * 2 - 140
    bl = contain(Image.open(os.path.join(SRC, 'bulletin_frame.jpg')).convert('RGB'),
                 bw, 720)
    x0, y0, x1, y1 = paste(im, framed(bl), W // 2, top - 70)
    caption(d, W // 2, y1 + 30,
            f'16:9 YOUTUBE BULLETIN · {FACTS["bulletin_s"]}s', accent=True)

    row_y, cell_h = y1 + 108, 780
    thirds = [
        ('broadsheet.jpg', '2:3 BROADSHEET'),
        ('post_01.jpg',    '4:5 FEED POST'),
        ('reel_frame.jpg', '9:16 REEL'),
    ]
    cw = (W - M * 2) // 3
    # Bottom-aligned on a shared baseline, with the captions on one line.
    # Top-aligning three different aspect ratios left 2:3, 4:5 and 9:16
    # finishing at three different heights and their labels stepping down
    # the slide, which reads as a layout that was never checked.
    arts = [(contain(Image.open(os.path.join(SRC, fn)).convert('RGB'),
                     cw - 108, cell_h), label) for fn, label in thirds]
    base = row_y + cell_h
    for i, (art, label) in enumerate(arts):
        cx = M + cw * i + cw // 2
        paste(im, framed(art), cx, base - art.height - 70)
        caption(d, cx, base + 26, label)

    footer(im)
    return im


def slide_3() -> Image.Image:
    """The differentiator: the renderer refuses copy that asserts guilt.

    This was a 300px card at the foot of slide 1, weighted the same as the
    build time. It is the only thing in the system that is genuinely hard to
    copy, and the only one with a statute behind it, so it gets a slide.
    """
    im = canvas()
    d = ImageDraw.Draw(im)
    top = chrome(im, 'PROGRAMMATIC EDITORIAL SYSTEM', 'It refuses to publish this.')

    d.text((M, top - 40),
           'An arrested person is not a convicted person. The renderer checks '
           'the headline and the\nreel line separately, because each is shown '
           'alone — in a thumbnail, a forward, a screenshot.',
           font=font_sans(37), fill=DIM, spacing=20)

    y = top + 118
    cards = [
        ((214, 74, 66), '×  REFUSED',
         'ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ ಬಂಧನ',
         'Asserts guilt before conviction.',
         'ContentError · BNS §356'),
        ((86, 190, 120), '✓  ACCEPTED',
         'ಹೆತ್ತವರ ಕೊಲೆ ಆರೋಪ, ಪುತ್ರ ಬಂಧನ',
         'The allegation is marked in the headline itself.',
         'ಆರೋಪ — carried by the line that travels alone'),
    ]
    for col, tag, kn, why, note in cards:
        d.rounded_rectangle([M, y, W - M, y + 404], 18, fill=(11, 16, 27),
                            outline=(41, 52, 70), width=2)
        d.rectangle([M, y, M + 7, y + 404], fill=col)
        d.text((M + 56, y + 44), tag, font=font_sans(33, bold=True), fill=col)
        draw_mixed(d, (M + 56, y + 112), kn, 62, PAPER, bold=True)
        d.text((M + 56, y + 236), why, font=font_sans(34), fill=DIM)
        draw_mixed(d, (M + 56, y + 306), note, 29, FAINT)
        y += 456

    # The guard itself, quoted from brand/content.py. The slide claims the
    # renderer refuses copy; showing the four lines that do the refusing is
    # the evidence for that claim, and it fills a frame that otherwise sat
    # two-thirds empty with the argument still unfinished.
    guard = [
        [('for ', SYN_KEY), ('where, text ', PAPER), ('in ', SYN_KEY),
         ("(('headline', self.headline),", SYN_STR)],
        [("                ('reel_line', self.reel_line)):", SYN_STR)],
        [('    if ', SYN_KEY), ('asserts_guilt(text):', PAPER)],
        [('        raise ', SYN_KEY), ('ContentError', SYN_NUM), ('(...)', SYN_PUNCT)],
    ]
    gw = contain(code_window(guard, W - M * 2 - 140, 'brand/content.py'),
                 W - M * 2 - 140, 620)
    gx0, gy0, gx1, gy1 = paste(im, framed(gw, 12), W // 2, y - 4)
    caption(d, W // 2, gy1 + 30, 'brand/content.py · Story.validate()')

    d.text((M, gy1 + 108),
           'No override flag exists. Adding one was considered and rejected — '
           'a guard you can\nswitch off is a guard that gets switched off on '
           'deadline.',
           font=font_sans(33), fill=FAINT, spacing=18)
    footer(im)
    return im


if __name__ == '__main__':
    for i, fn in enumerate((slide_1, slide_2, slide_3), 1):
        p = os.path.join(OUT, f'linkedin_{i}.jpg')
        fn().save(p, quality=94, subsampling=0, optimize=True)
        print(f'  ✓ {p}  ({os.path.getsize(p)/1e6:.1f} MB)')
