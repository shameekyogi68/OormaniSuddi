"""
ಊರ್ಮನಿ ಸುದ್ದಿ — the scan wipe: an animated twin of any finished slide (D98, D99).
=================================================================================
A carousel on Instagram may be videos. This turns a finished slide JPEG into a
short video, choreographed the way a premium editorial brand moves type:

* **Lines flow, they do not queue.** Each line is revealed left to right
  through a soft feathered edge, behind a thin gold light — the logo's sun
  passing over the paper. Lines start a fraction after the line above, so the
  page fills like a wave; a headline line lands slower than a point and
  settles up a few pixels; where one block ends and the next begins there is
  a beat.
* **A cover is never blank.** The feed and the profile grid show the first
  frame, and a stranger gives a post one second. So on a cover the
  photograph and the headline are there at frame 0, and everything after
  them is revealed.
* **The hold is what gets read.** The finished slide holds long enough to
  read (`Motion.read_rate`, estimated from the lines of type), between a
  floor and a ceiling.
* **The slide asks to be swiped.** While it holds, the swipe chevrons — on
  the red edge tab and in the footer — nudge right every few seconds.
* **The loop has no seam.** An Instagram carousel video loops until the
  reader swipes; the last half-second dissolves back to the first frame.

It works from the PICTURE, not from the template: it finds the lines of text
in the slide, so every slide the engine makes — ಸುದ್ದಿ ಸಾರ index, story,
sources, ಮುಖ್ಯ ಸುದ್ದಿ — animates the same way, and so will any slide added
later. The held frame IS the static slide.

Never done: reveal Kannada letter by letter — cutting through a conjunct shows
broken shapes, so a line is always wiped whole and soft.
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
from dataclasses import dataclass

import numpy as np
from PIL import Image

from .tokens import C, Motion as M, Paper as P

FPS = M.fps
TOP_STATIC = 140          # the bug, date and the rule under them
TAB_W = 44                # the right-edge swipe tab
LAND_W = 24               # the left-edge landing mark (D100)
INK_DIFF = 40             # summed RGB distance from the paper that counts as ink
MERGE_GAP = 3             # rows of paper that still belong to one line
PAD = (3, 4)              # rows kept above / below a line, for anti-aliasing
MAX_LINE = 160            # taller than this is two lines whose letters touch
BIG = 60                  # px; a line this tall is display type (a headline)
BLOCK_GAP = 40            # px of paper between two lines that starts a new block
CHARS_PER_H = 2.5         # Kannada characters per line-height of width, measured
                          # on the fixture: 288 estimated for 285 typed


@dataclass
class Band:
    y0: int
    y1: int               # exclusive
    x0: int
    x1: int
    rule: bool = False    # a hairline: it comes in with the line below it

    @property
    def h(self) -> int:
        return self.y1 - self.y0

    @property
    def big(self) -> bool:
        return self.h >= BIG


def _ink(a: np.ndarray, paper) -> np.ndarray:
    return np.abs(a.astype(np.int16) - np.array(paper, np.int16)).sum(axis=2) > INK_DIFF


def _box(mask: np.ndarray):
    ys, xs = np.nonzero(mask)
    if ys.size < 20:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def analyse(im: Image.Image, cover: bool = False) -> dict:
    """Where the photograph is, every line of text below the chrome, which of
    them are there from the first frame, and where the swipe chevrons are."""
    a = np.asarray(im.convert('RGB'))
    H, W, _ = a.shape
    # The footer is paper on every slide; the middle of a photo cover is not.
    paper = tuple(int(v) for v in a[H - 20, 4])
    ink = _ink(a, paper)
    ink[:, W - TAB_W:] = False                           # the swipe tab is chrome
    ink[:, :LAND_W] = False                              # so is the landing mark
    foot = H - P.footer_h
    rows_cov = ink.mean(axis=1)

    # A photograph: coverage stays high from the very top (light sky can dip
    # for a few rows, so it is judged on average) and ends where it collapses
    # back to paper.
    photo_end = 0
    if rows_cov[:60].mean() > 0.7:
        y = 200
        while y < foot and rows_cov[y] > 0.3:
            y += 1
        if y > 200 and rows_cov[:y].mean() > 0.7:
            photo_end = y
    # The gold sunline that closes the photograph.
    sun = None
    if photo_end:
        gold = np.abs(a[photo_end - 30:photo_end].astype(np.int16)
                      - np.array(C.gold_500, np.int16)).sum(axis=2) < 90
        g_rows = np.nonzero(gold.mean(axis=1) > 0.9)[0]
        if g_rows.size:
            sun = (photo_end - 30 + int(g_rows.min()), photo_end - 30 + int(g_rows.max()) + 1)
    top = photo_end if photo_end else TOP_STATIC

    rows = ink.sum(axis=1) >= 3
    bands: list[Band] = []
    y = top
    while y < foot:
        if not rows[y]:
            y += 1
            continue
        y0, gap = y, 0
        while y < foot and (rows[y] or gap < MERGE_GAP):
            gap = 0 if rows[y] else gap + 1
            y += 1
        y1 = y - gap
        for ya, yb in _split(ink, y0, y1):
            cols = np.nonzero(ink[ya:yb].any(axis=0))[0]
            if cols.size:
                bands.append(Band(ya, yb, int(cols[0]), int(cols[-1]) + 1,
                                  rule=(yb - ya) < 8))
        y += 1

    # A cover is COMPLETE at frame 0 (D101): Instagram takes the post's
    # thumbnail from the first video, and a grid tile that shows half a cover
    # is a tile nobody taps. Nothing on it is revealed; light passes over it.
    static: list[int] = list(range(len(bands))) if cover else []

    # The ಸುದ್ದಿ ಸಾರ cover's teaser rows (D104): a hairline, then a line that
    # opens with a red place name. Found from the picture, like everything
    # here, so the running order follows however many stories the day has.
    teasers: list[tuple[int, int, int]] = []
    if cover:
        # Hairlines are the light rule colour across most of the measure —
        # the black rule under the header is not one, so the lead's kicker
        # (red, small, under that black rule) is never taken for a teaser.
        x0m, x1m = P.margin, W - P.margin
        rule_c = np.array(C.paper_200, np.int16)
        near = np.abs(a[:foot, x0m:x1m].astype(np.int16) - rule_c).sum(axis=2) < 25
        hair = np.nonzero(near.mean(axis=1) > 0.8)[0]
        red_px = np.abs(a.astype(np.int16) - np.array(C.red_500, np.int16)).sum(axis=2) < 120
        for k, b in enumerate(bands):
            if b.rule or b.big:
                continue
            if red_px[b.y0:b.y1, b.x0:b.x0 + 60].mean() < 0.08:
                continue
            above = hair[(hair < b.y0) & (hair >= b.y0 - 40)]
            if not above.size:
                continue
            top_ = int(above.max()) + 3
            below = hair[hair > b.y1]
            nxt = min([int(below.min()) - 1] if below.size else [foot]
                      + ([bands[k + 1].y0 - 3] if k + 1 < len(bands) else []))
            bot = min(nxt, b.y1 + (b.y0 - top_))
            teasers.append((top_, bot, b.x0))

    # The swipe chevrons: white on the red edge tab, red in the footer.
    red = np.array(C.red_500, np.int16)
    is_red = np.abs(a.astype(np.int16) - red).sum(axis=2) < 90
    tab = _box(is_red[:, W - TAB_W:])
    tab_chev = None
    if tab:
        tab = (W - TAB_W + tab[0], tab[1], W, tab[3])
        # The chevron only — inside the tab's rounded corners.
        tab_chev = (tab[0] + 10, tab[1] + 10, W, tab[3] - 10)
    fx0, fy0 = W - P.margin - 24, foot + 18
    fchev = _box(is_red[fy0:H - 10, fx0:W - P.margin + 4])
    if fchev:
        fchev = (fx0 + fchev[0] - 3, fy0 + fchev[1] - 3,
                 min(W, fx0 + fchev[2] + 3 + M.anim_nudge_px + 2), fy0 + fchev[3] + 3)

    chars = sum((b.x1 - b.x0) / max(1, b.h) * CHARS_PER_H for b in bands if not b.rule)
    return {'paper': paper, 'photo_end': photo_end, 'sun': sun, 'bands': bands,
            'static': static, 'teasers': teasers, 'tab': tab, 'tab_chevron': tab_chev,
            'footer_chevron': fchev,
            'chars': round(chars), 'top': top, 'foot': foot, 'size': (W, H)}


def _split(ink: np.ndarray, y0: int, y1: int) -> list[tuple[int, int]]:
    """Cut a band that is really several lines at the quietest row between
    them. Big Kannada headlines have ascenders that touch the line above."""
    if y1 - y0 <= MAX_LINE:
        return [(y0, y1)]
    prof = np.convolve(ink[y0:y1].sum(axis=1).astype(float), np.ones(5) / 5, 'same')
    h = y1 - y0
    lo, hi = int(h * 0.3), int(h * 0.7)
    cut = y0 + lo + int(np.argmin(prof[lo:hi]))
    return _split(ink, y0, cut) + _split(ink, cut, y1)


# ─────────────────────────────────────────────────────────────────────────────
#  EASING
# ─────────────────────────────────────────────────────────────────────────────

def _bezier(x1: float, y1: float, x2: float, y2: float, n: int = 2001):
    """A CSS cubic-bezier as a lookup: u (time) → progress."""
    s = np.linspace(0, 1, 20001)
    bx = 3 * (1 - s) ** 2 * s * x1 + 3 * (1 - s) * s ** 2 * x2 + s ** 3
    by = 3 * (1 - s) ** 2 * s * y1 + 3 * (1 - s) * s ** 2 * y2 + s ** 3
    return np.interp(np.linspace(0, 1, n), bx, by)


# A gentle start and a long, slow settle: the line arrives, then glides in.
_GLIDE = _bezier(0.25, 0.0, 0.0, 1.0)


def _glide(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return float(_GLIDE[int(u * (len(_GLIDE) - 1))])


def _smooth(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def _nudge(t: float, starts: list[float]) -> float:
    """px the chevrons are pushed right at `t`: two soft taps, the second
    smaller — a hand pointing the way, not a bounce."""
    for s in starts:
        v = (t - s) / 0.8
        if 0 <= v < 0.45:
            return M.anim_nudge_px * math.sin(math.pi * v / 0.45) ** 2
        if 0.5 <= v < 0.9:
            return 0.55 * M.anim_nudge_px * math.sin(math.pi * (v - 0.5) / 0.4) ** 2
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
#  CHOREOGRAPHY
# ─────────────────────────────────────────────────────────────────────────────

def plan(info: dict, cover: bool = False) -> dict:
    """When everything happens. Returns per-band (start, duration), the
    photograph's fade, the sunline's draw, the hold and the total."""
    W = info['size'][0]
    bands, static = info['bands'], set(info['static'])
    photo, sun = info['photo_end'], info['sun']
    fade = bool(photo) and not cover
    if cover:
        sun = None                                  # already drawn
    t = M.anim_start
    photo_at = (t, M.anim_photo) if fade else None
    sun_at = None
    if sun:
        sun_at = (t + (M.anim_photo * 0.55 if fade else 0), M.anim_sun)
        t = sun_at[0] + M.anim_sun * 0.45

    # A cover is finished from frame 0 and nothing passes over it (D104: the
    # owner did not like the light sweeping a finished page).
    moving = [] if cover else [i for i, b in enumerate(bands)
                               if not b.rule and i not in static]
    gaps, prev = [], None
    for i in moving:
        b = bands[i]
        if prev is None:
            g = 0.0
        else:
            p = bands[prev]
            g = M.anim_head_gap if (b.big and p.big) else M.anim_gap
            if b.y0 - p.y1 > BLOCK_GAP or b.big != p.big:
                g += M.anim_beat
        gaps.append(g)
        prev = i

    def dur(b: Band) -> float:
        if b.big:
            return M.anim_head_line
        w = min(1.0, (b.x1 - b.x0) / (W * 0.85))
        return M.anim_line_min + (M.anim_line_max - M.anim_line_min) * w

    if moving:
        last = dur(bands[moving[-1]])
        room = M.anim_reveal_max - t - last
        if sum(gaps) > room > 0:                      # a full slide: flow faster
            k = room / sum(gaps)
            gaps = [g * k for g in gaps]

    sched: dict[int, tuple[float, float]] = {}
    for i, g in zip(moving, gaps):
        t += g
        sched[i] = (t, dur(bands[i]))
    # A hairline draws itself just ahead of the line below it.
    for i, b in enumerate(bands):
        if b.rule and not cover and i not in static:
            nxt = next((sched[j] for j in range(i + 1, len(bands)) if j in sched), None)
            prv = next((sched[j] for j in range(i - 1, -1, -1) if j in sched), None)
            s = (nxt[0] - 0.08) if nxt else (prv[0] + 0.1 if prv else M.anim_start)
            sched[i] = (max(0.0, s), 0.5)

    ends = [s + d for s, d in sched.values()]
    if photo_at:
        ends.append(sum(photo_at))
    if sun_at:
        ends.append(sum(sun_at))
    reveal = max(ends + [M.anim_start])
    hold = min(M.anim_hold_max, max(M.anim_hold, info['chars'] / M.read_rate))
    total = reveal + hold + M.anim_out
    order = None
    teasers = info.get('teasers') or []
    if cover and teasers:
        # Whole rounds of the running order — every teaser, then a rest beat
        # — so the loop comes round in step with it.
        rnd = (len(teasers) + 1) * M.anim_order_step
        k = max(1, math.ceil((hold - M.anim_order_start) / rnd))
        if M.anim_order_start + k * rnd - reveal > M.anim_hold_max:   # never past the ceiling
            k = max(1, math.floor((M.anim_hold_max + reveal - M.anim_order_start) / rnd))
        total = M.anim_order_start + k * rnd + M.anim_out
        hold = total - reveal - M.anim_out
        order = {'start': M.anim_order_start, 'step': M.anim_order_step,
                 'rounds': k, 'end': M.anim_order_start + k * rnd}
    nudges = []
    if not order:
        n = reveal + 0.6
        while n + 0.8 < total - M.anim_out - 0.4:
            nudges.append(n)
            n += M.anim_nudge
    return {'bands': sched, 'photo': photo_at, 'sun': sun_at, 'reveal': reveal,
            'hold': hold, 'total': total, 'nudges': nudges, 'order': order}


# ─────────────────────────────────────────────────────────────────────────────
#  DRAWING
# ─────────────────────────────────────────────────────────────────────────────

def _shift_x(block: np.ndarray, dx: float, fill: np.ndarray) -> np.ndarray:
    """`block` moved right by a fractional `dx`, the gap filled with `fill`."""
    i, fr = int(dx), dx - int(dx)

    def at(k):
        out = np.empty_like(block)
        out[:] = fill
        if k < block.shape[1]:
            out[:, k:] = block[:, :block.shape[1] - k]
        return out
    return at(i) if fr < 1e-3 else (1 - fr) * at(i) + fr * at(i + 1)


def _chevron(full: np.ndarray, box, ground, mark, dx: float) -> np.ndarray:
    """The chevron in `box` re-drawn `dx` px to the right on its own ground."""
    x0, y0, x1, y1 = box
    reg = full[y0:y1, x0:x1].astype(np.float32)
    g, m = np.array(ground, np.float32), np.array(mark, np.float32)
    span = float(np.abs(m - g).sum())
    alpha = np.clip(np.abs(reg - g).sum(axis=2) / span, 0, 1)[..., None]
    # Never past its own ground: the tab's chevron sits near the screen edge.
    cols = np.nonzero(alpha[..., 0].max(axis=0) > 0.1)[0]
    if cols.size:
        dx = min(dx, max(0.0, alpha.shape[1] - 1 - cols[-1] - 3.0))
    alpha = _shift_x(alpha, dx, np.zeros(1, np.float32))
    return g + alpha * (m - g)


def _running(full: np.ndarray, paper: np.ndarray, teasers, order: dict,
             t: float) -> np.ndarray | None:
    """The running order at `t`: one teaser lit with a soft gold underlay
    and a red tick, or None when no teaser is lit. The type is never
    touched — the underlay goes only where the page is paper."""
    if not order or t < order['start'] or t >= order['end']:
        return None
    step, n = order['step'], len(teasers)
    i = int((t - order['start']) / step) % (n + 1)
    if i == n:                                      # the rest beat
        return None
    u = ((t - order['start']) % step) / step
    a = _smooth(u / 0.25) * (1 - _smooth((u - 0.75) / 0.25))
    if a <= 0.01:
        return None
    y0, y1, x0 = teasers[i]
    W = full.shape[1]
    c0, c1 = max(0, x0 - 16), min(W - TAB_W, W - x0 + 16)
    f = full.copy()
    reg = full[y0:y1, c0:c1]
    ink = (np.abs(reg - paper).sum(axis=2, keepdims=True) > 60)
    gold = np.array(C.gold_500, np.float32)
    f[y0:y1, c0:c1] = np.where(ink, reg, reg + M.anim_order_tint * a * (gold - reg))
    tx0 = max(0, x0 - 22)
    tick = full[y0 + 8:y1 - 8, tx0:tx0 + M.anim_order_tick]
    f[y0 + 8:y1 - 8, tx0:tx0 + M.anim_order_tick] = \
        tick + a * (np.array(C.red_500, np.float32) - tick)
    return f


def animate(src: str, dst: str, fps: int = FPS, cover: bool | None = None) -> dict:
    """Write `dst` (.mp4, 4:5, silent AAC track for platform compatibility).
    `cover` defaults to the file name: a slide called *_cover is a cover."""
    if cover is None:
        cover = '_cover' in os.path.basename(src)
    im = Image.open(src).convert('RGB')
    info = analyse(im, cover=cover)
    W, H = info['size']
    bands, foot = info['bands'], info['foot']
    photo_end, sun = info['photo_end'], info['sun']
    tl = plan(info, cover=cover)

    full = np.asarray(im).astype(np.float32)
    paper = np.array(info['paper'], np.float32)
    gold = np.array(C.gold_500, np.float32)

    # The first frame (D101). A cover is the finished slide: it is the
    # thumbnail. Any other slide is paper, the chrome, and a faint pencil
    # outline of its own layout — never a blank page — which the ink then
    # wipes in over.
    base = np.empty_like(full)
    base[:] = paper
    if not photo_end:
        base[:TOP_STATIC] = full[:TOP_STATIC]
    base[foot:] = full[foot:]
    if cover:
        base[:] = full
    else:
        for b in bands:
            ya, yb = max(0, b.y0 - PAD[0]), min(foot, b.y1 + PAD[1])
            c0, c1 = max(0, b.x0 - 6), min(W - TAB_W, b.x1 + 6)
            base[ya:yb, c0:c1] = paper + M.anim_ghost * (full[ya:yb, c0:c1] - paper)
    if info['tab']:
        x0, y0, x1, y1 = info['tab']
        base[y0:y1, x0:x1] = full[y0:y1, x0:x1]
    # The landing mark is there at frame 0: it is what the previous slide's
    # tab meets while the reader is still swiping.
    edge = full[:, :LAND_W]
    red_edge = np.abs(edge - np.array(C.red_500, np.float32)).sum(axis=2) < 90
    base[:, :LAND_W][red_edge] = edge[red_edge]

    # Each line, cut once, with paper below it to rise from.
    crops = {}
    for i, b in enumerate(bands):
        if i in tl['bands']:
            rise = 0 if b.rule else (M.anim_rise if b.big else M.anim_rise * 0.5)
            ya, yb = max(0, b.y0 - PAD[0]), min(foot, b.y1 + PAD[1])
            c0, c1 = max(0, b.x0 - 6), min(W - TAB_W, b.x1 + 6)
            blk = full[ya:yb, c0:c1]
            # Where the letters are along the line: the light rides on them
            # and goes out across the gaps between words and blocks.
            col = (np.abs(blk - paper).sum(axis=2) > INK_DIFF).any(axis=0).astype(np.float32)
            col = np.convolve(col, np.ones(25, np.float32), 'same') > 0
            col = np.convolve(col.astype(np.float32), np.ones(15, np.float32) / 15, 'same')
            crops[i] = (ya, yb, c0, c1, rise, blk, col)

    F, L = float(M.anim_feather), float(M.anim_light)

    def frame(t: float) -> np.ndarray:
        f = base.copy()
        if tl['photo']:
            u = _glide((t - tl['photo'][0]) / tl['photo'][1])
            if u > 0:
                top = sun[0] if sun else photo_end
                f[:top] = base[:top] + u * (full[:top] - base[:top])
        if tl['sun'] and sun:
            u = _glide((t - tl['sun'][0]) / tl['sun'][1])
            x = int(W * u)
            if x > 0:
                f[sun[0]:sun[1], :x] = full[sun[0]:sun[1], :x]
        for i, (s, d) in tl['bands'].items():
            u = (t - s) / d
            if u <= 0:
                continue
            ya, yb, c0, c1, rise, blk, col = crops[i]
            b = bands[i]
            e = _glide(u)
            front = b.x0 + e * (b.x1 - b.x0 + F)
            xs = np.arange(c0, c1, dtype=np.float32)
            a = np.clip((front - xs) / F, 0, 1)[None, :, None]
            dy = rise * (1 - e)
            hb = yb - ya
            r1 = min(foot, yb + int(math.ceil(rise)) + 1)
            canvas = np.empty((r1 - ya, c1 - c0, 3), np.float32)
            di, fr = int(dy), dy - int(dy)

            def shifted(k):
                canvas[:] = paper
                n = max(0, min(hb, (r1 - ya) - k))
                canvas[k:k + n] = blk[:n]
                return canvas.copy()
            src_ = shifted(di) if fr < 1e-3 else (1 - fr) * shifted(di) + fr * shifted(di + 1)
            if not cover:
                reg = f[ya:r1, c0:c1]
                f[ya:r1, c0:c1] = reg + a * (np.minimum(reg, src_) - reg)
            # The gold light at the front of the wipe: a thin line with a halo,
            # gone by the time the line is whole.
            if not b.rule and u < 1:
                xc = front - F * 0.5
                # Revealing: the light is gone as the line completes. Lighting a
                # finished cover: it swells and fades as it passes.
                fade = (math.sin(math.pi * u) if cover
                        else 1 - _smooth((u - 0.5) / 0.5))
                fade *= float(np.clip((b.x1 + 4 - xc) / 40.0, 0, 1))
                if fade > 0.01:
                    prof = (0.9 * np.exp(-((xs - xc) / L) ** 2)
                            + 0.22 * np.exp(-((xs - xc) / (L * 4)) ** 2)) * fade * col
                    y0g = ya + int(dy) + 3
                    y1g = min(foot, yb + int(dy) - 3)
                    if y1g > y0g:
                        reg = f[y0g:y1g, c0:c1]
                        f[y0g:y1g, c0:c1] = reg + np.clip(prof, 0, 1)[None, :, None] * (gold - reg)
        return f

    def held(dx: float) -> np.ndarray:
        if dx <= 0.05:
            return full
        f = full.copy()
        if info['tab_chevron']:
            x0, y0, x1, y1 = info['tab_chevron']
            f[y0:y1, x0:x1] = _chevron(full, info['tab_chevron'], C.red_500, C.paper_0, dx)
        if info['footer_chevron']:
            x0, y0, x1, y1 = info['footer_chevron']
            f[y0:y1, x0:x1] = _chevron(full, info['footer_chevron'], paper, C.red_500, dx)
        return f

    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
           '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
           '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-b:a', '64k', '-shortest', '-movflags', '+faststart', dst]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def put(a: np.ndarray):
        p.stdin.write(np.clip(a + 0.5, 0, 255).astype(np.uint8).tobytes())

    still = np.clip(full + 0.5, 0, 255).astype(np.uint8).tobytes()
    reveal, total = tl['reveal'], tl['total']
    out_at = total - M.anim_out
    for k in range(int(round(total * fps))):
        t = k / fps
        if t < reveal:
            put(frame(t))
        elif t < out_at:
            lit = _running(full, paper, info['teasers'], tl['order'], t)
            dx = _nudge(t, tl['nudges'])
            if lit is not None:
                put(lit)
            elif dx > 0.05:
                put(held(dx))
            else:
                p.stdin.write(still)
        else:                                   # back to the first frame
            v = _smooth((t - out_at) / M.anim_out)
            put(full + v * (base - full))
    p.stdin.close()
    p.wait()
    if p.returncode:
        raise RuntimeError(f'ffmpeg failed on {src}')
    return {'path': dst, 'seconds': round(total, 2), 'reveal': round(reveal, 2),
            'hold': round(tl['hold'], 2), 'lines': len(bands),
            'static': len(info['static']), 'photo': bool(photo_end), 'cover': cover}


def _animate_one(args: tuple[str, str]) -> str:
    """Worker for multiprocessing: animate a single slide."""
    src, dst = args
    animate(src, dst)
    return dst


def animate_all(paths: list[str]) -> list[str]:
    """An .mp4 beside every slide .jpg; returns the video paths.

    Uses multiprocessing to animate slides in parallel across CPU cores.
    Each slide's ffmpeg encode is CPU-bound and fully independent, so
    parallel execution is safe and gives a near-linear speedup.
    """
    import multiprocessing

    jobs: list[tuple[str, str]] = []
    for p in paths:
        if p.lower().endswith(('.jpg', '.jpeg')):
            jobs.append((p, os.path.splitext(p)[0] + '.mp4'))
    if not jobs:
        return []
    # One worker per slide, capped at the CPU count. On the 8-core machine
    # with 8 slides this runs ~7× faster than the sequential loop.
    #
    # Workers are spawned (macOS), and a spawned worker re-imports the
    # program that started it. A program read from stdin or typed at a prompt
    # cannot be re-imported: every worker then dies on start-up and the pool
    # replaces it forever — a render that hangs with no error. So the pool is
    # used only when the program is a real file; otherwise one at a time.
    main = sys.modules.get('__main__')
    path = getattr(main, '__file__', None)
    workers = min(len(jobs), multiprocessing.cpu_count())
    if workers <= 1 or not path or not os.path.isfile(path):
        return [_animate_one(j) for j in jobs]
    with multiprocessing.Pool(workers) as pool:
        out = pool.map(_animate_one, jobs)
    return out
