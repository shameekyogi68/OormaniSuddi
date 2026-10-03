"""
ಊರ್ಮನಿ ಸುದ್ದಿ — the scan wipe: an animated twin of any finished slide (D98).
============================================================================
A carousel on Instagram may be videos. This turns a finished slide JPEG into a
short video where every line of text is revealed left to right behind a thin
gold edge, top to bottom, and the finished slide then holds still (an
Instagram video in a carousel loops until the reader swipes, so the hold is
what gets read).

It works from the PICTURE, not from the template: it finds the lines of text
in the slide, so every slide the engine makes — ಸುದ್ದಿ ಸಾರ index, story,
sources, ಮುಖ್ಯ ಸುದ್ದಿ — animates the same way, and so will any slide added
later. The last frame IS the static slide.

What stays still: the red bug and date at the top, the footer, the swipe tab.
What fades: a photograph. What is never done: reveal Kannada letter by letter
— cutting through a conjunct shows broken shapes, so everything is wiped as a
whole line.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw

from .tokens import C, Motion as M, Paper as P

FPS = 30
TOP_STATIC = 140          # the bug, date and the rule under them
TAB_W = 44                # the right-edge swipe tab
INK_DIFF = 40             # summed RGB distance from the paper that counts as ink
MERGE_GAP = 3             # rows of paper that still belong to one line
PAD = (3, 4)              # rows kept above / below a line, for anti-aliasing


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


def _ink(a: np.ndarray, paper) -> np.ndarray:
    return np.abs(a.astype(np.int16) - np.array(paper, np.int16)).sum(axis=2) > INK_DIFF


def analyse(im: Image.Image) -> dict:
    """Where the photograph is, and every line of text below the chrome."""
    a = np.asarray(im.convert('RGB'))
    H, W, _ = a.shape
    # The footer is paper on every slide; the middle of a photo cover is not.
    paper = tuple(int(v) for v in a[H - 20, 4])
    ink = _ink(a, paper)
    ink[:, W - TAB_W:] = False                           # the swipe tab is chrome
    foot = H - P.footer_h
    cover = ink.mean(axis=1)

    # A photograph: coverage stays high from the very top (light sky can dip
    # for a few rows, so it is judged on average) and ends where it collapses
    # back to paper.
    photo_end = 0
    if cover[:60].mean() > 0.7:
        y = 200
        while y < foot and cover[y] > 0.3:
            y += 1
        if y > 200 and cover[:y].mean() > 0.7:
            photo_end = y
    top = photo_end if photo_end else TOP_STATIC

    rows = ink[:, :W].sum(axis=1) >= 3
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
    return {'paper': paper, 'photo_end': photo_end, 'bands': bands,
            'top': top, 'foot': foot, 'size': (W, H)}


MAX_LINE = 160            # taller than this is two lines whose letters touch


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


def _timeline(bands: list[Band], has_photo: bool, W: int):
    """[(start, duration)] per band; hairlines share the next line's start."""
    n = sum(1 for b in bands if not b.rule) or 1
    gap = min(M.anim_gap, (M.anim_reveal_max - M.anim_line_max) / max(1, n - 1))
    t0 = M.anim_start + (M.anim_photo * 0.6 if has_photo else 0)
    out, k = [], 0
    for i, b in enumerate(bands):
        if b.rule:
            nxt = next((j for j in range(i + 1, len(bands)) if not bands[j].rule), None)
            start = t0 + (k * gap if nxt is not None else max(0, k - 1) * gap)
            out.append((start, M.anim_line_min))
            continue
        w = (b.x1 - b.x0) / W
        dur = M.anim_line_min + (M.anim_line_max - M.anim_line_min) * min(1.0, w / 0.9)
        out.append((t0 + k * gap, dur))
        k += 1
    return out


def _io(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2


def animate(src: str, dst: str, fps: int = FPS) -> dict:
    """Write `dst` (.mp4, 4:5, silent AAC track for platform compatibility)."""
    im = Image.open(src).convert('RGB')
    info = analyse(im)
    W, H = info['size']
    paper, bands = info['paper'], info['bands']
    photo_end, foot = info['photo_end'], info['foot']
    full = im.convert('RGBA')

    # What is on screen before anything is revealed: paper, plus the chrome.
    base = Image.new('RGBA', (W, H), (*paper, 255))
    if not photo_end:
        base.paste(full.crop((0, 0, W, TOP_STATIC)), (0, 0))
        base.paste(full.crop((W - TAB_W, 0, W, H)), (W - TAB_W, 0))
    base.paste(full.crop((0, foot, W, H)), (0, foot))
    if photo_end:
        base.paste(full.crop((W - TAB_W, photo_end, W, foot)), (W - TAB_W, photo_end))

    sched = _timeline(bands, bool(photo_end), W)
    end = max([s + d for s, d in sched] + [M.anim_start + M.anim_photo])
    total = end + M.anim_hold
    n_reveal = int(end * fps) + 1

    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
           '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
           '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-b:a', '64k', '-shortest', '-movflags', '+faststart', dst]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    edge = (*C.gold_500, 255)
    for k in range(n_reveal):
        t = k / fps
        f = base.copy()
        if photo_end:
            u = _io((t - M.anim_start) / M.anim_photo)
            if u > 0:
                ph = full.crop((0, 0, W, photo_end)).copy()
                ph.putalpha(int(255 * u))
                f.alpha_composite(ph, (0, 0))
        for b, (s, d) in zip(bands, sched):
            u = _io((t - s) / d)
            if u <= 0:
                continue
            ya, yb = max(0, b.y0 - PAD[0]), min(foot, b.y1 + PAD[1])
            w = max(1, int((b.x1 - b.x0 + 8) * u))
            x0 = max(0, b.x0 - 4)
            f.alpha_composite(full.crop((x0, ya, x0 + w, yb)), (x0, ya))
            if 0 < u < 1 and not b.rule:
                ImageDraw.Draw(f).rectangle(
                    (x0 + w - M.anim_edge, ya + 4, x0 + w, yb - 4), fill=edge)
        p.stdin.write(f.convert('RGB').tobytes())
    last = full.convert('RGB').tobytes()
    for _ in range(int(M.anim_hold * fps)):          # the finished slide, still
        p.stdin.write(last)
    p.stdin.close()
    p.wait()
    return {'path': dst, 'seconds': round(total, 2), 'lines': len(bands),
            'photo': bool(photo_end)}


def animate_all(paths: list[str]) -> list[str]:
    """An .mp4 beside every slide .jpg; returns the video paths."""
    out = []
    for p in paths:
        if p.lower().endswith(('.jpg', '.jpeg')):
            dst = os.path.splitext(p)[0] + '.mp4'
            animate(p, dst)
            out.append(dst)
    return out
