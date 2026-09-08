"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Typography engine
=================================
Kannada is the hard case and everything here exists to serve it.

Three rules this module enforces so callers cannot get them wrong:

1. BASELINE DRAWING.  Kannada vowel signs (ೀ ೈ ೊ) climb far above the headline
   and subscript consonants (್ತ ್ರ ್ದ) hang far below the baseline. Positioning
   text by its bounding box — which is what `draw.text((x, y), ...)` does —
   makes every line jump by a different amount depending on which matras it
   happens to contain. We always draw with anchor='ls' onto a computed
   baseline, so lines sit on a true grid and nothing is ever clipped.

2. NO MANUAL TRACKING ON KANNADA.  Letter-spacing means drawing glyph by glyph,
   which destroys the shaping raqm does for conjuncts — ಸುದ್ದಿ becomes ಸು ದ ್ ದಿ.
   Tracking is silently ignored for any string containing Kannada.

3. MEASURED, NOT GUESSED.  Line height comes from the face's real vertical
   metrics times a leading multiplier, never from a hard-coded pixel number.
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .tokens import FONTS, Grid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_KANNADA = re.compile(r'[ಀ-೿]')


def has_kannada(s: str) -> bool:
    return bool(_KANNADA.search(s))


# ─────────────────────────────────────────────────────────────────────────────
#  GLYPH SAFETY
#
#  A codepoint the face does not carry renders as .notdef — the empty box. It
#  is silent: nothing raises, the layout still measures, and the box only shows
#  up when somebody watches the finished video. That is exactly how "▪" and
#  "⚠" reached published reels: NONE of the four faces here carries either,
#  including SF, so every badge pill shipped with a tofu box in front of it.
#
#  The fix is structural rather than a one-time find-and-replace, because the
#  next decorative character somebody types would fail the same silent way.
#  Every measurement and every draw funnels through here, so what is measured
#  is exactly what is drawn, and nothing uncovered can reach a frame:
#
#    * A SYMBOL or PUNCTUATION mark the face lacks is substituted from
#      _SUBSTITUTE (which only ever maps to characters all four faces carry),
#      or dropped when it is pure decoration with no equivalent.
#    * A LETTER or COMBINING MARK the face lacks is left alone and reported.
#      Dropping it would silently change the meaning of Kannada copy, which is
#      a far worse failure than a visible box — so it is raised to preflight
#      instead, where a human can see it.
# ─────────────────────────────────────────────────────────────────────────────

# Only maps to characters verified present in all of Noto Sans Kannada, Anek
# Kannada, Noto Serif Kannada and SF. Keep it that way.
_SUBSTITUTE = {
    '▪': '•', '▫': '•', '■': '•', '□': '•', '◾': '•', '◽': '•',
    '●': '•', '⬤': '•', '◦': '•', '‧': '·', '∙': '·',
    '▸': '›', '▶': '›', '►': '›', '➤': '›', '➔': '›', '→': '›', '⟶': '›',
    '▹': '›', '»': '»', '☞': '›',
    '⚠': '', '⚡': '', '★': '', '☆': '', '✓': '', '✔': '', '✗': '', '✘': '',
    '❗': '', '❕': '', '‼': '!', '⁉': '!?',
    '︎': '', '️': '',        # emoji / text variation selectors
    '​': '', '‌': '', '‍': '',   # ZWSP / ZWNJ / ZWJ
}


@lru_cache(maxsize=16)
def _coverage(path: str) -> frozenset | None:
    """Every codepoint the face at `path` can actually render.

    Read once per face with fontTools and cached. Returns None if the table
    cannot be read, which makes every check below fail open — a font we cannot
    introspect is left exactly as it is rather than having its text mangled.
    """
    try:
        from fontTools.ttLib import TTFont
        cps: set[int] = set()
        with TTFont(path, fontNumber=0, lazy=True) as tt:
            for table in tt['cmap'].tables:
                cps |= set(table.cmap.keys())
        return frozenset(cps)
    except Exception:
        return None


def covers(f, ch: str) -> bool:
    """Can this font render this character?"""
    cov = _coverage(getattr(f, 'path', '') or '')
    return True if cov is None else (ord(ch) in cov)


@lru_cache(maxsize=4096)
def _safe(s: str, path: str) -> tuple[str, tuple]:
    """(renderable text, letters the face is missing).

    Cached on (text, face) because it runs inside every measure and every
    draw — including once per line per frame — and the answer never changes.
    """
    cov = _coverage(path)
    if cov is None or not s:
        return s, ()
    DROP = '\x00'            # sentinel: a character removed, not replaced
    out, missing = [], []
    for ch in s:
        if ord(ch) in cov:
            out.append(ch)
            continue
        if ch in _SUBSTITUTE:
            sub = _SUBSTITUTE[ch]
            # A substitute is only useful if THIS face has it too.
            out.append(sub if (sub and all(ord(c) in cov for c in sub)) else DROP)
            continue
        cat = unicodedata.category(ch)
        if cat[0] in ('S', 'P', 'C', 'Z'):
            out.append(DROP)        # decoration the face lacks: remove it
        else:
            out.append(ch)          # a letter or mark: keep it, and report it
            missing.append(ch)
    txt = ''.join(out)
    if DROP in txt:
        # Close the hole a removed character left, taking ONE adjacent space
        # with it so " ⚠ ಸೂಚನೆ" becomes "ಸೂಚನೆ" and not "  ಸೂಚನೆ". Only the
        # whitespace this function created is touched: spacing the designer
        # wrote — the double space either side of the tagline's bullet, for
        # one — has to survive untouched, or every still in the house moves.
        txt = re.sub(rf'{DROP}+ | {DROP}+|{DROP}+', '', txt)
    return txt, tuple(dict.fromkeys(missing))


def safe(s: str, f) -> str:
    """The renderable form of `s` in face `f`. Idempotent."""
    if not s:
        return s
    return _safe(s, getattr(f, 'path', '') or '')[0]


def missing_glyphs(s: str, f) -> tuple:
    """Letters/marks in `s` that face `f` cannot render. Empty is the good case."""
    if not s:
        return ()
    return _safe(s, getattr(f, 'path', '') or '')[1]


# ─────────────────────────────────────────────────────────────────────────────
#  FONT BOOK
# ─────────────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=512)
def font(family: str = 'kn', size: int = 40, weight: int | None = None,
         width: int | None = None) -> ImageFont.FreeTypeFont:
    """Resolve a font. `weight`/`width` only apply to variable faces (kn_var).

    weight: 100..800 (Thin..ExtraBold)   width: 75..125 (condensed..extended)
    """
    path = FONTS.get(family, FONTS['kn'])
    if not os.path.isabs(path):
        path = os.path.join(BASE_DIR, path)
    f = ImageFont.truetype(path, int(size))
    if weight is not None or width is not None:
        try:
            axes = f.get_variation_axes()
            vals = [a['default'] for a in axes]
            for i, a in enumerate(axes):
                nm = a['name'].decode() if isinstance(a['name'], bytes) else a['name']
                if nm == 'Weight' and weight is not None:
                    vals[i] = max(a['minimum'], min(a['maximum'], weight))
                elif nm == 'Width' and width is not None:
                    vals[i] = max(a['minimum'], min(a['maximum'], width))
                elif nm == 'Optical Size':
                    # Track the optical-size axis to the point size, so small
                    # type gets its wider, sturdier cut and display type gets
                    # the tighter one. Free refinement on SF; ignored elsewhere.
                    vals[i] = max(a['minimum'], min(a['maximum'], size))
            f.set_variation_by_axes(vals)
        except Exception:
            pass          # static face — the default weight is what we get
    return f


_LATIN_FALLBACK = {'latin': 'kn_var', 'latin_alt': 'kn_var', 'latin_srf': 'kn_serif'}


def font_for(text: str, family: str = 'latin', size: int = 40,
             weight: int | None = None, width: int | None = None):
    """Like font(), but swaps in a Kannada face when the string needs one.

    SF and Georgia have no Kannada coverage, so any Kannada passed to them
    renders as tofu boxes. Anything drawn from user-supplied copy must go
    through here rather than font(), because you cannot know in advance which
    script a location name or a strapline will be in.
    """
    if has_kannada(text):
        family = _LATIN_FALLBACK.get(family, family)
    return font(family, size, weight, width)


# A scratch canvas used only for measurement.
_M = ImageDraw.Draw(Image.new('L', (8, 8)))


def line_height(f: ImageFont.FreeTypeFont, leading: float = 1.35,
                lines: list[str] | None = None) -> int:
    """Distance between consecutive baselines.

    Deliberately NOT taken from the face's nominal ascent+descent. Kannada
    fonts declare enormous vertical metrics to reserve room for stacked matras
    that most lines never use — AnekKannada reports 1.68em — so a nominal
    leading of 1.4 would set the text at 2.35x its own size and the list items
    would read further apart inside themselves than from each other.

    Instead: leading is a multiple of the em, and then we guarantee that no
    descender of one line can ever touch an ascender of the next, by measuring
    the real ink of the lines we are actually about to set.
    """
    lh = f.size * leading
    if lines and len(lines) > 1:
        need = 0.0
        prev_drop = ink_extents(lines[0], f)[1]
        for ln in lines[1:]:
            rise, drop = ink_extents(ln, f)
            need = max(need, prev_drop + rise)
            prev_drop = drop
        lh = max(lh, need + f.size * 0.10)
    return int(round(lh))


def text_width(s: str, f, tracking: float = 0.0) -> float:
    s = safe(s, f)
    if not s:
        return 0.0
    w = _M.textlength(s, font=f)
    if tracking and not has_kannada(s):
        w += tracking * f.size * (len(s) - 1)
    return w


def ink_extents(s: str, f) -> tuple[float, float]:
    """(rise above baseline, drop below baseline) of the actual inked pixels."""
    s = safe(s, f)
    if not s:
        return (0.0, 0.0)
    x0, y0, x1, y1 = _M.textbbox((0, 0), s, font=f, anchor='ls')
    return (-y0, y1)


# ─────────────────────────────────────────────────────────────────────────────
#  WRAPPING
# ─────────────────────────────────────────────────────────────────────────────

def _greedy(words: list[str], f, max_w: float, tracking: float) -> list[str]:
    lines, cur = [], ''
    for w in words:
        trial = f'{cur} {w}'.strip()
        if not cur or text_width(trial, f, tracking) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def wrap(text: str, f, max_w: float, tracking: float = 0.0,
         balance: bool = True) -> list[str]:
    """Wrap to max_w. With balance=True, even out the ragged edge so the last
    line is never a lonely orphan word — the single most visible difference
    between a designed headline and an automatic one."""
    out: list[str] = []
    for para in text.split('\n'):
        para = para.strip()
        if not para:
            out.append('')
            continue
        words = para.split()
        lines = _greedy(words, f, max_w, tracking)
        if balance and len(lines) > 1:
            lines = _balance(words, f, max_w, tracking, len(lines))
        out.extend(lines)
    return out


def _balance(words, f, max_w, tracking, target_n) -> list[str]:
    """Find the narrowest measure that still yields `target_n` lines, then keep
    the candidate with the flattest ragged edge."""
    best, best_score = None, float('inf')
    for pct in range(100, 62, -2):
        w = max_w * pct / 100.0
        cand = _greedy(words, f, w, tracking)
        if len(cand) != target_n:
            continue
        widths = [text_width(l, f, tracking) for l in cand]
        longest = max(widths) or 1.0
        # penalise variance across lines, and punish a very short final line hard
        var = sum((longest - x) ** 2 for x in widths) / len(widths)
        tail = (1.0 - widths[-1] / longest) ** 2 * longest * longest * 0.9
        score = var + tail
        if score < best_score:
            best, best_score = cand, score
    return best or _greedy(words, f, max_w, tracking)


def ellipsize(text: str, f, max_w: float, sep: str = ' • ') -> str:
    """Trim a joined list until it fits, cutting whole items where possible."""
    if text_width(text, f) <= max_w:
        return text
    if sep in text:
        parts = text.split(sep)
        while len(parts) > 1:
            parts.pop()
            cand = sep.join(parts) + ' …'
            if text_width(cand, f) <= max_w:
                return cand
    out = text
    while out and text_width(out + '…', f) > max_w:
        out = out[:-1]
    return out.rstrip() + '…'


# ─────────────────────────────────────────────────────────────────────────────
#  TEXT BLOCK
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Block:
    """A laid-out run of text. Height is exact; nothing clips."""
    lines: list[str]
    f: ImageFont.FreeTypeFont
    lh: int
    tracking: float = 0.0
    align: str = 'left'            # left | center | right
    max_w: float = 0.0

    first_rise: float = 0.0        # ink above the first baseline
    last_drop: float = 0.0         # ink below the last baseline

    @property
    def n(self) -> int:
        return len(self.lines)

    @property
    def height(self) -> int:
        """Visual height from the top of the first line's ink to the bottom of
        the last line's ink. Use this for layout, not n * lh."""
        if not self.lines:
            return 0
        return int(round(self.first_rise + (self.n - 1) * self.lh + self.last_drop))

    @property
    def width(self) -> float:
        return max((text_width(l, self.f, self.tracking) for l in self.lines), default=0.0)

    def baselines(self, top: float) -> list[float]:
        """Baseline y for each line, given the block's visual top edge."""
        y0 = top + self.first_rise
        return [y0 + i * self.lh for i in range(self.n)]


def layout(text: str, f, max_w: float, leading: float = 1.35,
           tracking: float = 0.0, align: str = 'left',
           balance: bool = True) -> Block:
    # Wrap the text the face can actually set, so Block.lines is what a viewer
    # will really see — otherwise a dropped symbol makes the stored line and
    # the drawn line disagree, and every QA check reads the wrong one.
    text = safe(text, f)
    lines = wrap(text, f, max_w, tracking, balance) if max_w else text.split('\n')
    lh = line_height(f, leading, lines)
    # Rise/drop from the real ink, floored at the Kannada headline height so a
    # line that happens to carry no tall matra still sits on the same grid.
    r0 = ink_extents(lines[0], f)[0] if lines else 0.0
    d1 = ink_extents(lines[-1], f)[1] if lines else 0.0
    return Block(lines=lines, f=f, lh=lh, tracking=tracking, align=align,
                 max_w=max_w or 0.0,
                 first_rise=max(r0, f.size * 0.74),
                 last_drop=max(d1, f.size * 0.10))


def fit(text: str, family: str, size_hi: int, size_lo: int, max_w: float,
        max_h: float, leading: float = 1.35, tracking: float = 0.0,
        weight: int | None = None, width: int | None = None,
        align: str = 'left', max_lines: int | None = None,
        step: int = 2) -> Block:
    """Largest size in [size_lo, size_hi] whose block fits (max_w x max_h).

    Automated news copy varies wildly in length; this is what keeps a
    seven-word headline and a twenty-word headline both looking designed."""
    last = None
    size_hi, size_lo = int(size_hi), int(size_lo)
    for s in range(size_hi, size_lo - 1, -step):
        f = font(family, s, weight, width)
        b = layout(text, f, max_w, leading, tracking, align)
        last = b
        if b.height <= max_h and (max_lines is None or b.n <= max_lines):
            return b
    return last


# ─────────────────────────────────────────────────────────────────────────────
#  DRAWING
# ─────────────────────────────────────────────────────────────────────────────

def _needs_layer(fill) -> bool:
    """True when the fill is translucent and must be composited, not drawn.

    PIL's ImageDraw REPLACES the target pixel, including its alpha, at the
    glyph core — it does not blend. So text drawn straight onto the canvas with
    a 10%-alpha fill writes (r, g, b, 26) into an otherwise opaque image, and
    the final .convert('RGB') then throws that 26 away and keeps the colour at
    FULL strength. Translucent type therefore has to go via its own layer.
    """
    return isinstance(fill, (tuple, list)) and len(fill) == 4 and fill[3] < 255


def _draw_line(d: ImageDraw.ImageDraw, x: float, baseline: float, s: str,
               f, fill, tracking: float):
    # The last gate before ink hits the canvas. Every path into the rasteriser
    # passes through here, so nothing the face cannot render ever gets drawn.
    s = safe(s, f)
    if not s:
        return
    if tracking and not has_kannada(s):
        cx = x
        for ch in s:
            d.text((cx, baseline), ch, font=f, fill=fill, anchor='ls')
            cx += _M.textlength(ch, font=f) + tracking * f.size
    else:
        d.text((x, baseline), s, font=f, fill=fill, anchor='ls')


def _composite_lines(target: Image.Image, draw_calls, fill):
    """Render translucent text on its own layer, then composite it properly."""
    lay = Image.new('RGBA', target.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    opaque = (fill[0], fill[1], fill[2], 255)
    for x, baseline, s, f, tracking in draw_calls:
        _draw_line(ld, x, baseline, s, f, opaque, tracking)
    lay.putalpha(lay.getchannel('A').point(lambda v: v * fill[3] // 255))
    target.alpha_composite(lay)


def draw_block(target: Image.Image, block: Block, x: float, top: float, fill,
               shadow: tuple | None = None, box_w: float | None = None,
               opacity: float = 1.0) -> float:
    """Draw `block` with its visual top edge at `top`. Returns the bottom edge.

    shadow = (dx, dy, blur, (r,g,b,a)) — a soft drop shadow rendered on its own
    layer so it never darkens the glyphs themselves. Use it whenever type sits
    over photography; never use it on type over a flat panel.
    """
    if not block.lines:
        return top
    bw = box_w if box_w is not None else block.width
    bls = block.baselines(top)

    if shadow:
        dx, dy, blur, scol = shadow
        pad = int(blur * 3 + max(abs(dx), abs(dy)) + 8)
        lw = int(bw + pad * 2)
        lh_ = int(block.height + pad * 2)
        lay = Image.new('RGBA', (lw, lh_), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        for i, line in enumerate(block.lines):
            lx = _align_x(pad, bw, line, block)
            _draw_line(ld, lx + dx, pad + (bls[i] - top) + dy, line, block.f, scol,
                       block.tracking)
        lay = lay.filter(ImageFilter.GaussianBlur(blur))
        target.alpha_composite(lay, (int(x - pad), int(top - pad)))

    if _needs_layer(fill):
        _composite_lines(target, [
            (_align_x(x, bw, line, block), bls[i], line, block.f, block.tracking)
            for i, line in enumerate(block.lines)], fill)
    elif opacity >= 0.999:
        d = ImageDraw.Draw(target)
        for i, line in enumerate(block.lines):
            _draw_line(d, _align_x(x, bw, line, block), bls[i], line, block.f,
                       fill, block.tracking)
    else:
        lay = Image.new('RGBA', target.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        for i, line in enumerate(block.lines):
            _draw_line(ld, _align_x(x, bw, line, block), bls[i], line, block.f,
                       fill, block.tracking)
        target.alpha_composite(Image.blend(
            Image.new('RGBA', target.size, (0, 0, 0, 0)), lay, opacity))
    return top + block.height


def _align_x(x: float, bw: float, line: str, block: Block) -> float:
    if block.align == 'left':
        return x
    lw = text_width(line, block.f, block.tracking)
    if block.align == 'center':
        return x + (bw - lw) / 2.0
    return x + (bw - lw)


def draw_text(target: Image.Image, s: str, x: float, baseline: float, f, fill,
              tracking: float = 0.0, anchor_x: str = 'l',
              shadow: tuple | None = None):
    """Single-line convenience. `baseline` is a true baseline, not a box top."""
    w = text_width(s, f, tracking)
    if anchor_x == 'c':
        x -= w / 2
    elif anchor_x == 'r':
        x -= w
    if shadow:
        dx, dy, blur, scol = shadow
        pad = int(blur * 3 + 8)
        rise, drop = ink_extents(s, f)
        lay = Image.new('RGBA', (int(w + pad * 2), int(rise + drop + pad * 2)), (0, 0, 0, 0))
        _draw_line(ImageDraw.Draw(lay), pad + dx, pad + rise + dy, s, f, scol, tracking)
        lay = lay.filter(ImageFilter.GaussianBlur(blur))
        target.alpha_composite(lay, (int(x - pad), int(baseline - rise - pad)))
    if _needs_layer(fill):
        _composite_lines(target, [(x, baseline, s, f, tracking)], fill)
    else:
        _draw_line(ImageDraw.Draw(target), x, baseline, s, f, fill, tracking)
    return x + w
