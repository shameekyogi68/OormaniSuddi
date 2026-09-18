"""
ಊರ್ಮನಿ ಸುದ್ದಿ — ಸ್ಪೀಡ್ ನ್ಯೂಸ್: the day's stories as one quick-news reel.
==========================================================================
The format every Kannada news channel runs as "speed news": each story is a
place and one line, read by the anchor while it is on screen, and the next
one is already coming. It is not the lead-story reel (D39) with more stories
bolted on — that was tried as `scripts/render_roundup_reel.py`, and watching
it frame by frame is how every rule below was arrived at. See D81.

WHAT MAKES IT QUICK
  * Every story is cut to its own measured narration, not to a floor. The
    first attempt held each story for at least 4.6s whatever was said, then
    closed on eight seconds of a logo on black — 51s for eight headlines, and
    the last eight were the ones a viewer swipes on.
  * A counter and a segmented progress bar, so the viewer knows it is story
    3 of 8 and that the next one is two seconds away. That is the whole
    retention mechanism of the format, and the first attempt had neither.
  * The end card is a two-second follow, not a speech.

WHAT MAKES IT LOOK EDITED
  * The wipe moves PICTURES only. The first attempt wiped whole frames, so
    the gold edge sliced through Kannada headlines mid-akshara on every cut.
    Here each story's text is gone before the wipe starts and arrives after
    it lands, and the chrome — brand, counter, progress, disclosure — sits
    above the transition and never moves.
  * It is laid out in the REELS safe zone, fmt('reel'). The first attempt
    used fmt('story'), whose right margin is 72px, so headlines ran under the
    like/comment/share rail, and the handle footer sat under the caption.

WHAT KEEPS IT HONEST
  * Every word the anchor says goes through `voice._spoken`, the normaliser
    that learned ₹, initials and decimals the hard way (D53). The first
    attempt called the TTS engine raw and skipped all of it.
  * Every frame showing a generated picture carries its disclosure on a
    solid label, legible at phone size — not 18px of grey over a crowd.
  * The sound effects are the house set (brand/sfx.py, D82): synthesised
    here, registered as `own`, each one tied to a picture edit.
  * Loudness is measured and corrected in two passes to the house −14 LUFS.
    Single-pass loudnorm on a clip this short landed at −11.8.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw

from . import typo
from .content import Edition, Story
from .copy import _leads_with_place
from .motion import KenBurns, _transition, _h264_encode_args, _mux
from .surface import Surface, editorial_plate, grain, logo
from .tokens import C, Brand, Motion, alpha, category, fmt, Limits

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S2 = 2                      # text tiles are drawn at 2x and downsampled

# Scene timing, derived from Motion so the numbers live in one place (D56).
LEAD_FIRST = 0.10           # the first story is already speaking at frame 0
LEAD_NEXT = Motion.speed_cross + 0.04
TAIL = Motion.speed_gap + Motion.speed_cross


@dataclass
class Item:
    story: Story
    place: str
    line: str               # what is on screen
    spoken: str             # what the anchor says — already normalised
    vo: str = ''            # narration file
    vo_dur: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
#  COPY → WHAT IS SAID AND SHOWN
# ─────────────────────────────────────────────────────────────────────────────

_LATIN_DATELINE = re.compile(r'^[A-Za-z][A-Za-z .]{1,24}:\s*')


def screen_line(st: Story) -> str:
    """The one line this story gets on screen.

    `reel_line` when the desk wrote one, the headline otherwise. A leading
    Latin dateline — "Karkala: ಜ್ವರದಿಂದ…", which is how Udayavani titles
    arrive — is dropped, because the place chip already carries the place and
    a mixed-script opener reads as a pasted headline rather than a card.
    """
    line = (st.reel_line or st.headline or '').strip()
    rest = _LATIN_DATELINE.sub('', line)
    if rest != line and typo.has_kannada(rest):
        line = rest
    return line.rstrip('.। ')


def place_of(st: Story) -> str:
    return (st.location or '').strip() or Brand.coverage


def spoken_text(place: str, line: str) -> str:
    """Place, a full stop, the line — through the house normaliser.

    The full stop is the anchor's beat after the dateline; a colon was being
    read as nothing at all. The place is not said twice when the line already
    opens with it.
    """
    from .voice import _spoken
    said = line if _leads_with_place(line, place) else f'{place}. {line}'
    return _spoken(said.rstrip('.। ') + '.')


def items_for(edition: Edition) -> list[Item]:
    out = []
    for st in edition.stories:
        place, line = place_of(st), screen_line(st)
        out.append(Item(st, place, line, spoken_text(place, line)))
    return out


END_SPOKEN = 'ಫಾಲೋ ಮಾಡಿ, ಊರ್ಮನಿ ಸುದ್ದಿ.'


# ─────────────────────────────────────────────────────────────────────────────
#  TIMING
# ─────────────────────────────────────────────────────────────────────────────

def story_seconds(i: int, vo_dur: float) -> float:
    """As long as the story is SAID, never less.

    `speed_story_max` is not applied here. The first real render capped
    stories at 6.0s while two of the narrations ran past that, which puts the
    next story's voice on top of this one's — the anchor talking over
    himself. A line too long for speed news is a copy problem, reported by
    `long_lines()`, and fixed with a reel_line.
    """
    lead = LEAD_FIRST if i == 0 else LEAD_NEXT
    return round(max(Motion.speed_story_min, lead + vo_dur + TAIL), 2)


def long_lines(items: list['Item'], durs: list[float]) -> list[str]:
    return [it.line for it, d in zip(items, durs) if d > Motion.speed_story_max]


def plan(vo_durs: list[float], end_vo: float,
         cap: float = Limits.reel_target_max) -> tuple[list[float], float, int]:
    """(story durations, end-card duration, how many stories fit).

    Stories are in edition order, which is priority order, so when the day
    runs long it is the tail that goes — and the caller is told, rather than
    the reel quietly overrunning the cap the gate will then fail it on.
    """
    end = round(max(Motion.speed_end, end_vo + 0.45), 2)
    XF = Motion.speed_cross
    durs = [story_seconds(i, d) for i, d in enumerate(vo_durs)]
    n = len(durs)
    while n > 1 and sum(durs[:n]) + end - n * XF > cap:
        n -= 1
    return durs[:n], end, n


# ─────────────────────────────────────────────────────────────────────────────
#  DRAWING
#  The grammar is broadcast speed news: the picture is full bleed and keeps
#  moving; each story arrives on a lower-third BAND that sweeps in from the
#  left with the place tag sitting on its top edge; the chrome above never
#  moves. Square corners and one gold accent throughout (STANDARDS, Rule 3) —
#  the first cut used rounded pills, which is exactly what the house rules out.
# ─────────────────────────────────────────────────────────────────────────────

def _ease_out(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return 1 - (1 - u) ** 3


def _ease_back(u: float) -> float:
    u = min(1.0, max(0.0, u))
    c = 1.4
    return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2


def _tile(w: int, h: int, draw) -> Image.Image:
    """Draw at 2x into a transparent tile and bring it down to size."""
    big = Image.new('RGBA', (w * S2, h * S2), (0, 0, 0, 0))
    draw(big)
    return big.resize((w, h), Image.Resampling.LANCZOS)


def _tag(text: str, f_size: int, bg, fg, pad_x: int = 18, h: int | None = None,
         weight: int | None = None) -> Image.Image:
    """A square-cornered label: gold on ink, or ink on gold."""
    fam = 'kn' if weight is None else 'kn_var'
    f = typo.font(fam, f_size, weight)
    w = int(typo.text_width(text, f) + pad_x * 2)
    h = h or int(f_size * 1.55)

    def draw(im):
        s = S2
        ImageDraw.Draw(im).rectangle((0, 0, w * s, h * s), fill=bg)
        typo.draw_text(im, text, pad_x * s, (h * 0.5 + f_size * 0.36) * s,
                       typo.font(fam, f_size * s, weight), fg)
    return _tile(w, h, draw)


class Layout:
    """Where everything goes (D81, D83).

    The right margin is the Reels action rail, from fmt('reel'). Top and
    bottom are speed news's own, measured against Instagram's chrome: the
    lead-reel values (230 / 480) left the first redesign bunched into the
    middle of the frame with dead bands above and below it.
    """

    def __init__(self, W: int, H: int):
        F = fmt('reel')
        self.W, self.H = W, H
        self.sl, _st, self.sr, _sb = F.safe
        self.st = Motion.speed_top
        self.sb = Motion.speed_bottom
        self.x0 = self.sl
        self.x1 = W - self.sr              # clear of the action rail
        self.top_x1 = W - self.sl          # the rail does not reach the top band
        self.bottom = H - self.sb          # clear of the caption overlay
        self.cw = self.x1 - self.x0
        self.win_top = self.st + 150       # under the chrome


def _scrims(W: int, H: int) -> Image.Image:
    """For a story with no photograph: darken the plate under the chrome and
    the band, the same on every such scene."""
    ys = np.arange(H, dtype=np.float32)
    top = np.clip(1.0 - ys / (H * 0.25), 0, 1) ** 1.25 * 0.70
    low = np.clip((ys - H * 0.55) / (H * 0.25), 0, 1) * 0.80
    a = np.maximum(top, low)
    col = np.zeros((H, 1, 4), np.uint8)
    col[:, 0, :3] = C.ink_950
    col[:, 0, 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(np.repeat(col, W, 1), 'RGBA')


def _backdrop(path: str, W: int, H: int) -> Image.Image:
    """The same photograph, blurred and darkened, filling the frame behind
    the picture window — so a square or wide picture sits in a frame that
    belongs to it rather than in black bars."""
    from PIL import ImageFilter
    from .surface import cover
    im = cover(Image.open(path).convert('RGB'), W // 4, H // 4, (0.5, 0.5))
    im = im.filter(ImageFilter.GaussianBlur(10)).resize((W, H),
                                                        Image.Resampling.BICUBIC)
    shade = Image.new('RGB', (W, H), C.ink_950)
    return Image.blend(im, shade, 0.62).convert('RGBA')


def _disclosure_tag(photo, max_w: int) -> Image.Image | None:
    """The honesty label for a picture, on solid ground (D57)."""
    text = photo.disclosure if photo else ''
    if not text:
        return None
    f = typo.font('kn_var', 24, 540)
    text = typo.ellipsize(text, f, max_w - 36, sep='  •  ')
    return _tag(text, 24, (*C.ink_950, 200), (*C.paper_50, 255),
                pad_x=16, h=42, weight=540)


class StorySlate:
    """One story: the WHOLE picture in a window, and a band beneath it that
    is only on screen while no wipe is (D83).

    The first redesign laid every photograph full bleed. The day's pictures
    are square and wide — 1:1, 1.7:1, 1.96:1 — so filling a 9:16 frame cut
    away 44% of a square one's width and 71% of the widest, and then the
    band covered the lower half of what was left. Here the picture is fitted
    whole, as large as the frame allows, and the band starts where it ends.
    """

    def __init__(self, it: Item, L: Layout, index: int, dur: float):
        self.it, self.L, self.i, self.dur = it, L, index, dur
        self._text()
        self._picture(index)
        self._band()
        self.disclosure = _disclosure_tag(it.story.photo, self.win_w - 24)

    def _text(self):
        L, it = self.L, self.it
        cat = category(it.story.category)
        # The place is the hook — it is what stops somebody in Kundapura —
        # so it is the loudest thing after the headline: ink on gold.
        self.place_tag = _tag(it.place, 40, (*C.gold_500, 255), (*C.ink_950, 255),
                              pad_x=20, h=64)
        self.cat_tag = _tag(cat['kn'], 26, (*C.ink_900, 235), (*C.paper_200, 255),
                            pad_x=14, h=40, weight=620)
        head = typo.fit(it.line, 'kn', 80 * S2, 54 * S2, L.cw * S2,
                        3 * 80 * 1.22 * S2, leading=1.22, max_lines=3)
        self.hh = int(head.height / S2) + 12
        self.head = _tile(L.cw, self.hh, lambda im: typo.draw_block(
            im, head, 0, 0, (*C.paper_50, 255), box_w=L.cw * S2))
        src = typo.ellipsize('ಮೂಲ: ' + ' · '.join(it.story.sources[:2]),
                             typo.font('kn_var', 25, 480), L.cw)
        self.src = _tile(L.cw, 38, lambda im: typo.draw_text(
            im, src, 0, 28 * S2, typo.font('kn_var', 25 * S2, 480),
            (*C.paper_300, 255)))
        self.pad_top, self.gap = 58, 14
        self.text_h = self.pad_top + self.hh + self.gap + self.src.height

    def _picture(self, index: int):
        L, st = self.L, self.it.story
        room = L.bottom - self.text_h - L.win_top     # tallest the window may be
        self.kb = None
        if st.photo and os.path.exists(st.photo.path):
            w, h = Image.open(st.photo.path).size
            a = w / h
            ww, wh = L.W, int(round(L.W / a))
            if wh > room:                              # fit whole, never crop
                wh, ww = room, int(round(room * a))
            self.win_w, self.win_h = ww, wh
            self.win_x = (L.W - ww) // 2
            self.bg = _backdrop(st.photo.path, L.W, L.H)
            self.kb = KenBurns(st.photo.path, ww, wh, focal=st.photo.focal,
                               zoom=Motion.speed_push, drift=0.0,
                               direction=1 if index % 2 == 0 else -1)
        else:
            self.win_w, self.win_h, self.win_x = L.W, room, 0
            sf = Surface(L.W, L.H, 1)
            editorial_plate(sf, (0, 0, L.W, L.H), category(st.category),
                            seed=st.headline)
            grain(sf, 4.0, 0.55)
            self.bg = sf.img.convert('RGBA')
        # Centred in the room above the band. A wide picture then has the
        # blurred backdrop above and below it, instead of pulling the headline
        # up after it and leaving the foot of the frame empty.
        self.win_y = L.win_top + (room - self.win_h) // 2

    def _band(self):
        L = self.L
        # The text is pinned to the same line on every story — the caption
        # line — so the headline never jumps as the pictures change, and the
        # frame is used top to bottom rather than bunched in the middle.
        self.band_y = L.bottom - self.text_h
        self.head_y = self.band_y + self.pad_top
        self.src_y = self.head_y + self.hh + self.gap
        self.tag_y = self.band_y - self.place_tag.height // 2
        band = Image.new('RGBA', (L.W, L.H - self.band_y), (*C.ink_950, 226))
        ImageDraw.Draw(band).rectangle((0, 0, L.W, 3), fill=(*C.gold_500, 255))
        self.band = band

    def picture(self, t: float) -> Image.Image:
        f = self.bg.copy()
        if self.kb is not None:
            f.alpha_composite(self.kb.frame(t / self.dur).convert('RGBA'),
                              (self.win_x, self.win_y))
        return f

    def text_alpha(self, t: float, is_first: bool) -> tuple[float, float]:
        """(opacity, rise px) of the headline. Gone before the next wipe,
        back only once this one has landed."""
        XF = Motion.speed_cross
        if is_first:
            a_in, rise = 1.0, 0.0            # headline on frame 0 (D39)
        else:
            e = _ease_out((t - XF - 0.10) / 0.22)
            a_in, rise = e, 26 * (1 - e)
        u_out = min(1.0, max(0.0, (self.dur - XF - t) / 0.14))
        return a_in * u_out, rise

    def draw(self, f: Image.Image, t: float, is_first: bool):
        """The band sweeps in, the tag drops onto it, the headline rises,
        the source line follows — about 0.4s, and all of it before the
        anchor is two words in."""
        XF, L = Motion.speed_cross, self.L
        out = min(1.0, max(0.0, (self.dur - XF - t) / 0.14))
        if out <= 0.0:
            return
        k = 99.0 if is_first else t - XF      # time since the wipe landed
        sweep = _ease_out(k / 0.22)
        if sweep > 0:
            w = max(1, int(L.W * sweep))
            f.alpha_composite(_fade(self.band.crop((0, 0, w, self.band.height)), out),
                              (0, self.band_y))
        tag = _ease_back((k - 0.08) / 0.24)
        if tag > 0:
            dy = int(18 * (1 - min(1.0, tag)))
            a = min(1.0, tag) * out
            f.alpha_composite(_fade(self.place_tag, a), (L.x0, self.tag_y - dy))
            f.alpha_composite(_fade(self.cat_tag, a),
                              (L.x0 + self.place_tag.width + 12,
                               self.tag_y + (self.place_tag.height - self.cat_tag.height) // 2 - dy))
        a, rise = self.text_alpha(t, is_first)
        if a > 0.002:
            f.alpha_composite(_fade(self.head, a), (L.x0, int(self.head_y + rise)))
        s = _ease_out((k - 0.24) / 0.2) * out
        if s > 0.002:
            f.alpha_composite(_fade(self.src, s), (L.x0, self.src_y))


class EndSlate:
    """Two seconds: the logo lands, the name and handle rise, one line."""

    def __init__(self, L: Layout, dur: float):
        self.L, self.dur = L, dur
        W, H = L.W, L.H
        sf = Surface(W, H, 1)
        grain(sf, 4.0, 0.55)
        base = Image.new('RGBA', (W, H), (*C.ink_950, 255))
        base.alpha_composite(sf.img.convert('RGBA'))
        self.base = base
        self.logo = logo(280, 'circle')
        self.cy = int(H * 0.30)
        name = _tile(W, 96, lambda im: typo.draw_text(
            im, Brand.name, W * S2 / 2, 76 * S2, typo.font('kn', 70 * S2),
            (*C.paper_50, 255), anchor_x='c'))
        handle = _tile(W, 80, lambda im: typo.draw_text(
            im, Brand.handle, W * S2 / 2, 60 * S2, typo.font('latin', 56 * S2, 700),
            (*C.gold_500, 255), anchor_x='c'))
        follow = _tag('ಫಾಲೋ ಮಾಡಿ', 40, (*C.gold_500, 255), (*C.ink_950, 255),
                      pad_x=34, h=72)
        tail = _tile(W, 56, lambda im: typo.draw_text(
            im, Brand.follow_kn, W * S2 / 2, 40 * S2,
            typo.font('kn_var', 32 * S2, 520), (*C.paper_300, 255), anchor_x='c'))
        y = self.cy + 330
        self.rows = [(name, (0, y), 0.18), (handle, (0, y + 100), 0.28),
                     (follow, ((W - follow.width) // 2, y + 210), 0.40),
                     (tail, (0, y + 306), 0.50)]

    def picture(self, t: float) -> Image.Image:
        f = self.base.copy()
        s = 0.62 + 0.38 * _ease_back(t / 0.42)
        lg = self.logo.resize((max(1, int(280 * s)),) * 2, Image.Resampling.LANCZOS)
        f.alpha_composite(_fade(lg, min(1.0, t / 0.18)),
                          ((self.L.W - lg.width) // 2, self.cy + (280 - lg.height) // 2))
        for img, (x, y), t0 in self.rows:
            e = _ease_out((t - t0) / 0.3)
            if e > 0.002:
                f.alpha_composite(_fade(img, e), (x, int(y + 22 * (1 - e))))
        return f


class Chrome:
    """Everything that stays put while the pictures change."""

    def __init__(self, L: Layout, n: int, date_kn: str):
        self.L, self.n = L, n

        def brand(im):
            s = S2
            im.alpha_composite(logo(70 * s, 'circle'), (0, 0))
            typo.draw_text(im, Brand.name, 88 * s, 46 * s, typo.font('kn', 36 * s),
                           (*C.paper_50, 255), shadow=(0, 2 * s, 8 * s, (0, 0, 0, 190)))
        self.brand = _tile(420, 72, brand)
        self.label = _tag('ಸ್ಪೀಡ್ ನ್ಯೂಸ್', 26, (*C.gold_500, 255), (*C.ink_950, 255),
                          pad_x=12, h=40)
        self.date = _tile(420, 40, lambda im: typo.draw_text(
            im, date_kn, 0, 30 * S2, typo.font('kn_var', 26 * S2, 560),
            (*C.paper_200, 255), shadow=(0, 2 * S2, 8 * S2, (0, 0, 0, 190))))
        self.counters = [self._counter(i + 1) for i in range(n)]

    def _counter(self, k: int) -> Image.Image:
        num, of = f'{k}', f'/{self.n}'
        f1, f2 = typo.font('latin', 54, 780), typo.font('latin', 34, 600)
        w = int(typo.text_width(num, f1) + typo.text_width(of, f2) + 8)

        def draw(im):
            s = S2
            w1 = typo.text_width(num, typo.font('latin', 54 * s, 780))
            typo.draw_text(im, num, 0, 54 * s, typo.font('latin', 54 * s, 780),
                           (*C.paper_50, 255), shadow=(0, 2 * s, 8 * s, (0, 0, 0, 190)))
            typo.draw_text(im, of, w1 + 4 * s, 54 * s, typo.font('latin', 34 * s, 600),
                           (*C.gold_400, 255), shadow=(0, 2 * s, 8 * s, (0, 0, 0, 190)))
        return _tile(w, 70, draw)

    def progress(self, frame: Image.Image, idx: int, p: float, end: bool):
        """Segments, one per story — filled, filling, or still to come."""
        L = self.L
        gap, y, h = 8, L.st, 6
        span = L.top_x1 - L.x0
        seg = (span - gap * (self.n - 1)) / self.n
        d = ImageDraw.Draw(frame)
        for k in range(self.n):
            x0 = L.x0 + k * (seg + gap)
            d.rectangle((x0, y, x0 + seg, y + h), fill=(*C.paper_50, 64))
            fill = 1.0 if (end or k < idx) else (p if k == idx else 0.0)
            if fill > 0:
                d.rectangle((x0, y, x0 + max(1, seg * fill), y + h),
                            fill=(*C.gold_500, 255))

    def draw(self, frame: Image.Image, idx: int, p: float, end: bool):
        L = self.L
        self.progress(frame, idx, p, end)
        if end:
            return
        y = L.st + 20
        frame.alpha_composite(self.brand, (L.x0, y))
        frame.alpha_composite(self.label, (L.x0 + 88, y + 66))
        frame.alpha_composite(self.date, (L.x0 + 88 + self.label.width + 14, y + 66))
        c = self.counters[idx]
        frame.alpha_composite(c, (L.top_x1 - c.width, y))


def _fade(tile: Image.Image, a: float) -> Image.Image:
    if a >= 0.999:
        return tile
    out = tile.copy()
    out.putalpha(tile.getchannel('A').point(lambda v, _a=a: int(v * _a)))
    return out


class Timeline:
    """Every scene placed in time, and the frame at any moment of it.

    Separate from the encoder so a frame can be looked at — or tested — on
    its own: the rule that no wipe ever cuts a headline is a property of
    `frame(t)`, and it is asserted there rather than hoped for in the video.
    """

    def __init__(self, items: list[Item], durs: list[float], end_d: float,
                 date_kn: str, W: int, H: int):
        self.L = L = Layout(W, H)
        self.W, self.H = W, H
        self.n = len(items)
        self.slates = [StorySlate(it, L, i, d)
                       for i, (it, d) in enumerate(zip(items, durs))]
        self.scenes = self.slates + [EndSlate(L, end_d)]
        XF = Motion.speed_cross
        self.starts, t0 = [], 0.0
        for sc in self.scenes:
            self.starts.append(t0)
            t0 += sc.dur - XF
        self.total = round(t0 + XF, 2)
        self.scrim = _scrims(W, H)
        self.chrome = Chrome(L, self.n, date_kn)

    def _base(self, i: int, t_local: float) -> Image.Image:
        sc = self.scenes[i]
        f = sc.picture(t_local).copy()
        if isinstance(sc, StorySlate) and sc.kb is None:
            f.alpha_composite(self.scrim)
        return f

    def at(self, t: float) -> tuple[int, bool, int]:
        """(scene that owns t, inside a wipe, story the chrome is showing)."""
        XF = Motion.speed_cross
        cur = max(i for i, s0 in enumerate(self.starts) if t >= s0 - 1e-9)
        wiping = cur > 0 and t < self.starts[cur] + XF
        shown = cur - 1 if (wiping and t - self.starts[cur] < XF * 0.5) else cur
        return cur, wiping, shown

    def text_opacity(self, t: float) -> float:
        cur, _w, _s = self.at(t)
        if cur >= self.n:
            return 0.0
        return self.slates[cur].text_alpha(t - self.starts[cur], cur == 0)[0]

    def band_on(self, t: float) -> bool:
        """Is any part of a story's band drawn at t — the test's handle on
        'nothing of the story block is on screen during a wipe'."""
        cur, wiping, _s = self.at(t)
        if cur >= self.n or wiping:
            return False
        sl = self.slates[cur]
        tl = t - self.starts[cur]
        return (cur == 0 or tl - Motion.speed_cross > 0) and \
            tl < sl.dur - Motion.speed_cross

    def frame(self, t: float) -> Image.Image:
        XF, L = Motion.speed_cross, self.L
        cur, wiping, shown = self.at(t)
        if wiping:
            f = _transition(self._base(cur - 1, t - self.starts[cur - 1]),
                            self._base(cur, t - self.starts[cur]),
                            (t - self.starts[cur]) / XF, self.W, self.H)
        else:
            f = self._base(cur, t - self.starts[cur])
        is_end = shown >= self.n
        if not is_end and self.slates[shown].disclosure is not None:
            # Inside the picture window's corner: the label sits ON the
            # picture it describes, which is the whole point of it (D57).
            sl = self.slates[shown]
            f.alpha_composite(sl.disclosure, (sl.win_x + 12, sl.win_y + 12))
        if cur < self.n and not wiping:
            self.slates[cur].draw(f, t - self.starts[cur], cur == 0)
        p = 0.0
        if not is_end:
            p = min(1.0, max(0.0, (t - self.starts[shown]) / self.scenes[shown].dur))
        self.chrome.draw(f, min(shown, self.n - 1), p, is_end)
        return f


# ─────────────────────────────────────────────────────────────────────────────
#  THE COVER
#  Not a frame of the video. The shelf shows a reel cover at two sizes: the
#  profile grid crops it to the centre 3:4 and shows it about a third of a
#  screen wide, and the Reels tab shows the whole 9:16. The first cover was
#  frame 0.8 — a three-line headline that shrinks to ~25px on the grid, with
#  a "1/8" counter and a progress bar that mean nothing on a still. This is a
#  title card: one huge word, the date, how many stories and how long, and
#  the TOWNS — the hook for a hyperlocal channel — all inside the 3:4 crop.
# ─────────────────────────────────────────────────────────────────────────────

def cover_safe(W: int, H: int) -> tuple[int, int]:
    """(top, bottom) of the profile grid's centre 3:4 crop."""
    crop_h = int(W * 4 / 3)
    top = (H - crop_h) // 2
    return top, top + crop_h


def render_cover(items: list[Item], date_kn: str, seconds: float, path: str,
                 W: int, H: int) -> dict:
    """Draw the cover and return where each element landed (for the tests)."""
    lead = items[0].story
    top, bot = cover_safe(W, H)
    pad = 84
    f = Image.new('RGBA', (W, H), (*C.ink_950, 255))
    if lead.photo and os.path.exists(lead.photo.path):
        f = KenBurns(lead.photo.path, W, H, focal=lead.photo.focal,
                     zoom=0.0).frame(1.0).convert('RGBA')
    ys = np.arange(H, dtype=np.float32)
    a = 0.40 + 0.52 * np.clip((ys - top) / (bot - top), 0, 1) ** 0.9
    a = np.maximum(a, np.clip(1 - ys / (top + 260), 0, 1) * 0.85)
    col = np.zeros((H, 1, 4), np.uint8)
    col[:, 0, :3] = C.ink_950
    col[:, 0, 3] = (np.clip(a, 0, 0.94) * 255).astype(np.uint8)
    f.alpha_composite(Image.fromarray(np.repeat(col, W, 1), 'RGBA'))
    boxes = {}

    y = top + 70
    f.alpha_composite(logo(104, 'circle'), (pad, y))
    f.alpha_composite(_tile(560, 80, lambda im: typo.draw_text(
        im, Brand.name, 0, 60 * S2, typo.font('kn', 48 * S2), (*C.paper_50, 255))),
        (pad + 124, y + 14))
    boxes['brand'] = (pad, y, pad + 684, y + 104)

    y = top + 300
    n, secs = len(items), int(round(seconds))
    kicker = _tag(f'ಇಂದಿನ {n} ಸುದ್ದಿ  ·  {secs} ಸೆಕೆಂಡ್', 36, (*C.gold_500, 255),
                  (*C.ink_950, 255), pad_x=22, h=62)
    f.alpha_composite(kicker, (pad, y))
    y += kicker.height + 26
    title = typo.fit('ಸ್ಪೀಡ್ ನ್ಯೂಸ್', 'kn', 176 * S2, 120 * S2, (W - 2 * pad) * S2,
                     200 * S2, leading=1.1, max_lines=1)
    th = int(title.height / S2) + 16
    f.alpha_composite(_tile(W - 2 * pad, th, lambda im: typo.draw_block(
        im, title, 0, 0, (*C.paper_50, 255), box_w=(W - 2 * pad) * S2,
        shadow=(0, 4 * S2, 22 * S2, (0, 0, 0, 200)))), (pad, y))
    boxes['title'] = (pad, y, W - pad, y + th)
    y += th + 10
    ImageDraw.Draw(f).rectangle((pad, y, pad + 180, y + 6), fill=(*C.gold_500, 255))
    y += 36
    f.alpha_composite(_tile(W - 2 * pad, 56, lambda im: typo.draw_text(
        im, date_kn, 0, 42 * S2, typo.font('kn_var', 40 * S2, 600),
        (*C.paper_200, 255))), (pad, y))
    y += 96

    # The towns, in the order they come — the reason somebody here stops.
    places, x, row_y = [], pad, y
    for it in items:
        if it.place not in places:
            places.append(it.place)
    for p in places[:8]:
        tg = _tag(p, 38, (*C.ink_950, 225), (*C.gold_400, 255), pad_x=20, h=66)
        if x + tg.width > W - pad:
            x, row_y = pad, row_y + tg.height + 14
        f.alpha_composite(tg, (x, row_y))
        ImageDraw.Draw(f).rectangle((x, row_y, x + 5, row_y + tg.height),
                                    fill=(*C.gold_500, 255))
        x += tg.width + 14
    boxes['places'] = (pad, y, W - pad, row_y + 66)
    y = row_y + 66 + 44

    lead_line = typo.fit(items[0].line, 'kn', 54 * S2, 42 * S2, (W - 2 * pad) * S2,
                         2 * 54 * 1.25 * S2, leading=1.24, max_lines=2)
    lh = int(lead_line.height / S2) + 12
    if y + lh <= bot - 90:
        f.alpha_composite(_tile(W - 2 * pad, lh, lambda im: typo.draw_block(
            im, lead_line, 0, 0, (*C.paper_50, 235), box_w=(W - 2 * pad) * S2,
            shadow=(0, 2 * S2, 12 * S2, (0, 0, 0, 200)))), (pad, y))
        boxes['lead'] = (pad, y, W - pad, y + lh)

    disc = _disclosure_tag(lead.photo, W - 2 * pad)
    if disc is not None:
        dy = bot - 40 - disc.height
        f.alpha_composite(disc, (pad, dy))
        boxes['disclosure'] = (pad, dy, pad + disc.width, dy + disc.height)
    f.convert('RGB').save(path, quality=93, subsampling=0, optimize=True)
    return boxes


# ─────────────────────────────────────────────────────────────────────────────
#  AUDIO
# ─────────────────────────────────────────────────────────────────────────────

def master_loudness(src: str, dst: str, target: float = Limits.lufs,
                    tp: float = Limits.true_peak_dbtp, lra: float = 9.0) -> dict:
    """Two-pass EBU R128 to the house target. Returns the measured input.

    One pass of loudnorm runs in dynamic mode and guesses; on a clip under a
    minute it overshot to −11.8 LUFS, so the platform turned it down and it
    sounded squashed against everything around it. Measure, then correct
    linearly.
    """
    r = subprocess.run(
        ['ffmpeg', '-hide_banner', '-nostats', '-i', src, '-af',
         f'loudnorm=I={target}:TP={tp}:LRA={lra}:print_format=json',
         '-f', 'null', '-'], capture_output=True, text=True, check=True)
    m = json.loads(r.stderr[r.stderr.rindex('{'):r.stderr.rindex('}') + 1])
    subprocess.run(
        ['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-af',
         f'loudnorm=I={target}:TP={tp}:LRA={lra}:'
         f'measured_I={m["input_i"]}:measured_TP={m["input_tp"]}:'
         f'measured_LRA={m["input_lra"]}:measured_thresh={m["input_thresh"]}:'
         f'offset={m["target_offset"]}:linear=true,'
         # A hair of headroom linear mode cannot promise: it measured
         # -1.4 dBTP against -1.5 on the first render.
         f'alimiter=limit={10 ** ((tp - 0.2) / 20):.3f}:level=disabled',
         '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', dst], check=True)
    return m


def _bed_path() -> str:
    """The music bed, only if the licence register allows it (D74)."""
    try:
        from .music import allowed_paths
        for p in allowed_paths('bed'):
            full = p if os.path.isabs(p) else os.path.join(BASE, p)
            if os.path.exists(full):
                return full
    except Exception:
        pass
    return ''


def sfx_cues(starts: list[float], n: int) -> list[tuple[str, float, float]]:
    """(effect, when, gain) — every hit tied to a picture edit, not a guess.

    open    frame 0, under the anchor's first word: a low, short hit.
    whoosh  centred on every wipe, travelling with it left to right.
    tick    as each headline lands — quiet, under the first syllable.
    outro   as the follow card's logo arrives.

    Gains are relative to the voice before mastering, and deliberately low:
    in speed news the anchor is the programme and the effects are punctuation.
    """
    XF = Motion.speed_cross
    cues = [('open', 0.0, 0.42)]
    for i in range(1, n + 1):
        cues.append(('whoosh', starts[i] + XF / 2 - 0.21, 0.34))
        if i < n:
            cues.append(('tick', starts[i] + XF + 0.10, 0.22))
    cues.append(('outro', starts[n] + XF + 0.02, 0.46))
    return [(k, max(0.0, t), g) for k, t, g in cues]


def _sfx_paths() -> dict[str, str]:
    """Only effects the licence register allows (D82)."""
    try:
        from .music import allowed_paths
        out = {}
        for p in allowed_paths('sfx'):
            full = p if os.path.isabs(p) else os.path.join(BASE, p)
            if os.path.exists(full):
                out[os.path.splitext(os.path.basename(p))[0]] = full
        return out
    except Exception:
        return {}


def _audio(items: list[Item], starts: list[float], total: float, end_vo: str,
           work: str) -> str:
    n = len(items)
    ins, parts, voice, fx = [], [], [], []
    k = 0
    for i, it in enumerate(items):
        lead = LEAD_FIRST if i == 0 else LEAD_NEXT
        ms = int(round((starts[i] + lead) * 1000))
        ins += ['-i', it.vo]
        parts.append(f'[{k}:a]aresample=48000,adelay={ms}|{ms}[v{k}]')
        voice.append(f'[v{k}]')
        k += 1
    ms = int(round((starts[n] + Motion.speed_cross + 0.30) * 1000))
    ins += ['-i', end_vo]
    parts.append(f'[{k}:a]aresample=48000,adelay={ms}|{ms}[v{k}]')
    voice.append(f'[v{k}]')
    k += 1
    parts.append(f'{"".join(voice)}amix=inputs={len(voice)}:normalize=0[vo]')

    paths = _sfx_paths()
    for name, when, gain in sfx_cues(starts, n):
        if name not in paths:
            continue
        ms = int(round(when * 1000))
        ins += ['-i', paths[name]]
        parts.append(f'[{k}:a]aresample=48000,volume={gain},'
                     f'adelay={ms}|{ms}[f{k}]')
        fx.append(f'[f{k}]')
        k += 1

    layers = ['[vo]']
    if fx:
        parts.append(f'{"".join(fx)}amix=inputs={len(fx)}:normalize=0[fx]')
        layers.append('[fx]')

    bed = _bed_path()
    if bed:
        end_start = starts[n]
        ins += ['-stream_loop', '-1', '-i', bed]
        # Under the anchor, up for the end card, then away.
        parts.append(
            f'[{k}:a]aresample=48000,atrim=0:{total:.2f},'
            f"volume='if(gte(t,{end_start:.2f}),0.26,0.11)':eval=frame,"
            f'afade=t=out:st={max(0.0, total - 0.9):.2f}:d=0.9[bed]')
        layers.append('[bed]')
    parts.append(f'{"".join(layers)}amix=inputs={len(layers)}:duration=longest:'
                 f'normalize=0,apad,atrim=0:{total:.2f}[a]')
    mix = os.path.join(work, 'mix.wav')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *ins,
                    '-filter_complex', ';'.join(parts), '-map', '[a]',
                    '-ac', '2', '-c:a', 'pcm_s16le', mix], check=True)
    out = os.path.join(work, 'mastered.wav')
    master_loudness(mix, out)
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  RENDER
# ─────────────────────────────────────────────────────────────────────────────

def tighten(src: str, dst: str, tempo: float = Motion.speed_tempo) -> str:
    """Trim the silence the TTS engine pads each clip with, and set the pace.

    Measured on 2026-09-18: every Google clip ends on ~0.38s of nothing. Eight
    stories of that is three seconds of dead air in a 45-second reel, which is
    the difference between eight stories fitting and seven. Only the ENDS are
    trimmed — the beat after the place name, inside the clip, is the anchor's
    pause and it stays.
    """
    edge = 'silenceremove=start_periods=1:start_threshold=-40dB:start_silence=0.03'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-af',
                    f'{edge},areverse,{edge},areverse,atempo={tempo}',
                    '-ar', '48000', '-ac', '1', '-c:a', 'pcm_s16le', dst],
                   check=True)
    return dst


def _narrate(items: list[Item], work: str) -> tuple[str, float]:
    from .voice import _synth_one, get_audio_duration
    for k, it in enumerate(items, 1):
        raw = os.path.join(work, f'vo_{k:02d}.mp3')
        _synth_one(it.spoken, raw, 'google', None, None)
        it.vo = tighten(raw, os.path.join(work, f'vo_{k:02d}.wav'))
        it.vo_dur = get_audio_duration(it.vo)
    raw = os.path.join(work, 'vo_end.mp3')
    _synth_one(END_SPOKEN, raw, 'google', None, None)
    end = tighten(raw, os.path.join(work, 'vo_end.wav'))
    return end, get_audio_duration(end)


def render_roundup(edition: Edition, path: str, fps: int = Motion.fps) -> dict:
    """Render the speed-news reel. Returns what was made and what was left out."""
    edition.validate()
    if len(edition.stories) < Limits.roundup_min_stories:
        raise ValueError(
            f'a speed-news reel needs at least {Limits.roundup_min_stories} '
            f'stories; this edition has {len(edition.stories)}. Render the '
            f'lead-story reel instead.')
    F = fmt('reel')
    W, H = F.w, F.h
    L = Layout(W, H)
    stem = os.path.splitext(os.path.basename(path))[0]
    work = os.path.join(BASE, 'build', f'speednews_{stem}')
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)

    items = items_for(edition)
    print(f'  narrating {len(items)} stories …')
    end_vo, end_dur = _narrate(items, work)
    durs, end_d, n = plan([it.vo_dur for it in items], end_dur)
    dropped = items[n:]
    items = items[:n]
    for line in long_lines(items, durs):
        print(f'  ⚠ "{line[:34]}…" is spoken over {Motion.speed_story_max:.0f}s — '
              f'write a shorter reel_line for speed news')
    if dropped:
        print(f'  ⚠ {len(dropped)} story(ies) left out to stay under '
              f'{Limits.reel_target_max:.0f}s — the carousel still carries them')

    tl = Timeline(items, durs, end_d, edition.date_kn, W, H)
    n_frames = int(round(tl.total * fps))
    print(f'  {n} stories · {tl.total:.1f}s · '
          + ' + '.join(f'{d:.1f}' for d in durs) + f' + end {end_d:.1f}')

    raw = os.path.join(work, 'video.mp4')
    enc = subprocess.Popen([
        'ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo',
        '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', 'pipe:0',
        *_h264_encode_args(), '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
        raw], stdin=subprocess.PIPE)
    for k in range(n_frames):
        t = k / fps
        enc.stdin.write(tl.frame(t).convert('RGB').tobytes())
        if k % 90 == 0 or k == n_frames - 1:
            print(f'    frame {k + 1}/{n_frames}  ({t:5.1f}s)', end='\r')
    enc.stdin.close()
    enc.wait()
    print()
    total, starts = tl.total, tl.starts

    audio = _audio(items, starts, total, end_vo, work)
    _mux(raw, audio, path)

    # The shelf tile: story one with its headline up.
    cov = os.path.splitext(path)[0] + '_cover.jpg'
    render_cover(items, edition.date_kn, total, cov, W, H)

    shutil.rmtree(work, ignore_errors=True)
    print(f'  ✓ {os.path.basename(path)}  ({total:.1f}s, {n} stories)  '
          f'+ {os.path.basename(cov)}')
    return {'path': path, 'cover': cov, 'seconds': total, 'stories': n,
            'dropped': [it.story.headline for it in dropped],
            'spoken': [it.spoken for it in items] + [END_SPOKEN]}
