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
    solid pill, legible at phone size — not 18px of grey over a crowd.
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
# ─────────────────────────────────────────────────────────────────────────────

def _tile(w: int, h: int, draw) -> Image.Image:
    """Draw at 2x into a transparent tile and bring it down to size."""
    big = Image.new('RGBA', (w * S2, h * S2), (0, 0, 0, 0))
    draw(big)
    return big.resize((w, h), Image.Resampling.LANCZOS)


def _pill(d: ImageDraw.ImageDraw, box, fill):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=(y1 - y0) / 2, fill=fill)


class Layout:
    """Where everything goes, from the REELS safe zone (D81)."""

    def __init__(self, W: int, H: int):
        F = fmt('reel')
        self.W, self.H = W, H
        self.sl, self.st, self.sr, self.sb = F.safe
        self.x0 = self.sl
        self.x1 = W - self.sr              # clear of the action rail
        self.top_x1 = W - self.sl          # the rail does not reach the top band
        self.bottom = H - self.sb          # clear of the caption overlay
        self.cw = self.x1 - self.x0


def _scrims(W: int, H: int) -> Image.Image:
    """The same darkening on every scene, so a cut never changes the frame's
    brightness. Top for the chrome, bottom for the story block."""
    a = np.zeros(H, np.float32)
    ys = np.arange(H, dtype=np.float32)
    # Top: enough under the brand row and the disclosure pill to hold them
    # on a sunlit signboard. Bottom: full strength BY the headline, not below
    # it — the first cut ramped from 0.40H to 0.92H, which left a three-line
    # headline sitting on half-strength shade over a busy market crowd.
    top = np.clip(1.0 - ys / (H * 0.30), 0, 1) ** 1.25 * 0.82
    u = np.clip((ys - H * 0.34) / (H * 0.24), 0, 1)
    bot = (u * u * (3 - 2 * u)) * 0.86
    bot = np.maximum(bot, np.clip((ys - H * 0.58) / (H * 0.30), 0, 1) * 0.96)
    a = np.maximum(top, bot)
    col = np.zeros((H, 1, 4), np.uint8)
    col[:, 0, :3] = C.ink_950
    col[:, 0, 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(np.repeat(col, W, 1), 'RGBA')


def _photo_plate(st: Story, W: int, H: int, direction: int):
    if st.photo and os.path.exists(st.photo.path):
        return KenBurns(st.photo.path, W, H, focal=st.photo.focal,
                        direction=direction)
    sf = Surface(W, H, 1)
    editorial_plate(sf, (0, 0, W, H), category(st.category), seed=st.headline)
    grain(sf, 4.0, 0.55)
    return sf.img.convert('RGB')


class StorySlate:
    """One story: a moving picture, and a text block that is only on screen
    while no wipe is."""

    def __init__(self, it: Item, L: Layout, index: int, dur: float):
        self.it, self.L, self.i, self.dur = it, L, index, dur
        self.photo = _photo_plate(it.story, L.W, L.H, 1 if index % 2 == 0 else -1)
        self.block, self.block_xy = self._block()
        self.disclosure = self._disclosure()

    def picture(self, t: float) -> Image.Image:
        if isinstance(self.photo, KenBurns):
            return self.photo.frame(t / self.dur).convert('RGBA')
        return self.photo.convert('RGBA')

    def _block(self):
        L, it = self.L, self.it
        cat = category(it.story.category)
        chip_f = typo.font('kn', 38)
        cat_f = typo.font('kn_var', 28, 560)
        src_f = typo.font('kn_var', 25, 470)
        head = typo.fit(it.line, 'kn', 88 * S2, 56 * S2, L.cw * S2,
                        3 * 88 * 1.26 * S2, leading=1.24, max_lines=3)
        chip_w = int(typo.text_width(it.place, chip_f) + 44)
        chip_h = 60
        src = 'ಮೂಲ: ' + ' · '.join(it.story.sources[:2])
        src = typo.ellipsize(src, src_f, L.cw)
        gap1, gap2 = 30, 24
        head_h = head.height / S2
        h = int(chip_h + gap1 + head_h + gap2 + 34)
        w = L.cw

        def draw(im):
            d = ImageDraw.Draw(im)
            s = S2
            _pill(d, (0, 0, chip_w * s, chip_h * s), (*C.gold_500, 255))
            typo.draw_text(im, it.place, 22 * s, 43 * s,
                           typo.font('kn', 38 * s), (*C.ink_950, 255))
            typo.draw_text(im, cat['kn'], (chip_w + 20) * s, 42 * s,
                           typo.font('kn_var', 28 * s, 600), (*C.paper_50, 235),
                           shadow=(0, 2 * s, 8 * s, (0, 0, 0, 200)))
            typo.draw_block(im, head, 0, (chip_h + gap1) * s, (*C.paper_50, 255),
                            shadow=(0, 3 * s, 16 * s, (0, 0, 0, 205)),
                            box_w=L.cw * s)
            typo.draw_text(im, src, 0, (chip_h + gap1 + head_h + gap2 + 26) * s,
                           typo.font('kn_var', 25 * s, 470),
                           (*C.paper_300, 255),
                           shadow=(0, 2 * s, 8 * s, (0, 0, 0, 200)))

        tile = _tile(w, h, draw)
        return tile, (L.x0, L.bottom - h)

    def _disclosure(self) -> Image.Image | None:
        """The honesty label for THIS picture, on solid ground (D57)."""
        ph = self.it.story.photo
        text = ph.disclosure if ph else ''
        if not text:
            return None
        L = self.L
        f = typo.font('kn_var', 24, 520)
        text = typo.ellipsize(text, f, L.top_x1 - L.x0 - 40, sep='  •  ')
        w = int(typo.text_width(text, f) + 36)
        h = 44

        def draw(im):
            d = ImageDraw.Draw(im)
            s = S2
            _pill(d, (0, 0, w * s, h * s), (*C.ink_950, 176))
            typo.draw_text(im, text, 18 * s, 30 * s, typo.font('kn_var', 24 * s, 520),
                           (*C.paper_50, 255))
        return _tile(w, h, draw)

    def text_alpha(self, t: float, is_first: bool) -> tuple[float, float]:
        """(opacity, rise px). Gone before the next wipe, back after this one."""
        XF = Motion.speed_cross
        if is_first:
            a_in, rise = 1.0, 0.0            # headline on frame 0 (D39)
        else:
            # From the moment the wipe has LANDED, never during it — the
            # first cut began at 55% of the wipe, over a half-old picture.
            u = min(1.0, max(0.0, (t - XF) / 0.20))
            e = 1 - (1 - u) ** 3
            a_in, rise = e, 22 * (1 - e)
        u_out = min(1.0, max(0.0, (self.dur - XF - t) / 0.14))
        return a_in * u_out, rise


class EndSlate:
    """Two seconds: the logo, the name, the handle, one follow line."""

    def __init__(self, L: Layout, dur: float):
        self.L, self.dur = L, dur
        W, H = L.W, L.H
        sf = Surface(W, H, 1)
        grain(sf, 4.0, 0.55)
        base = sf.img.convert('RGBA')
        d = ImageDraw.Draw(base)
        d.rectangle((0, 0, W, H), fill=(*C.ink_950, 255))
        lg = logo(260, 'circle')
        base.alpha_composite(lg, ((W - 260) // 2, int(H * 0.33)))
        cy = int(H * 0.33) + 300
        typo.draw_text(base, Brand.name, W / 2, cy + 60, typo.font('kn', 68),
                       (*C.paper_50, 255), anchor_x='c')
        typo.draw_text(base, Brand.handle, W / 2, cy + 150,
                       typo.font('latin', 56, 700), (*C.gold_500, 255), anchor_x='c')
        typo.draw_text(base, Brand.follow_kn, W / 2, cy + 226,
                       typo.font('kn_var', 34, 520), (*C.paper_200, 255), anchor_x='c')
        self.img = base

    def picture(self, t: float) -> Image.Image:
        return self.img


class Chrome:
    """Everything that stays put while the pictures change."""

    def __init__(self, L: Layout, n: int, date_kn: str):
        self.L, self.n = L, n
        W = L.W

        def brand(im):
            s = S2
            im.alpha_composite(logo(64 * s, 'circle'), (0, 0))
            typo.draw_text(im, Brand.name, 82 * s, 32 * s, typo.font('kn', 34 * s),
                           (*C.paper_50, 255), shadow=(0, 2 * s, 8 * s, (0, 0, 0, 190)))
            typo.draw_text(im, f'ಸ್ಪೀಡ್ ನ್ಯೂಸ್  ·  {date_kn}', 82 * s, 66 * s,
                           typo.font('kn_var', 26 * s, 600), (*C.gold_400, 255),
                           shadow=(0, 2 * s, 8 * s, (0, 0, 0, 190)))
        self.brand = _tile(620, 80, brand)
        self.counters = [self._counter(i + 1) for i in range(n)]

    def _counter(self, k: int) -> Image.Image:
        num, of = f'{k}', f'/{self.n}'
        f1, f2 = typo.font('latin', 50, 760), typo.font('latin', 34, 600)
        w = int(typo.text_width(num, f1) + typo.text_width(of, f2) + 8)

        def draw(im):
            s = S2
            w1 = typo.text_width(num, typo.font('latin', 50 * s, 760))
            typo.draw_text(im, num, 0, 50 * s, typo.font('latin', 50 * s, 760),
                           (*C.paper_50, 255), shadow=(0, 2 * s, 8 * s, (0, 0, 0, 190)))
            typo.draw_text(im, of, w1 + 4 * s, 50 * s, typo.font('latin', 34 * s, 600),
                           (*C.paper_300, 255), shadow=(0, 2 * s, 8 * s, (0, 0, 0, 190)))
        return _tile(w, 64, draw)

    def progress(self, frame: Image.Image, idx: int, p: float, end: bool):
        """Segments, one per story — filled, filling, or still to come."""
        L = self.L
        gap, y, h = 8, L.st, 7
        span = L.top_x1 - L.x0
        seg = (span - gap * (self.n - 1)) / self.n
        d = ImageDraw.Draw(frame)
        for k in range(self.n):
            x0 = L.x0 + k * (seg + gap)
            d.rounded_rectangle((x0, y, x0 + seg, y + h), radius=h / 2,
                                fill=(*C.paper_50, 70))
            fill = 1.0 if (end or k < idx) else (p if k == idx else 0.0)
            if fill > 0:
                d.rounded_rectangle((x0, y, x0 + max(h, seg * fill), y + h),
                                    radius=h / 2, fill=(*C.gold_500, 255))

    def draw(self, frame: Image.Image, idx: int, p: float, end: bool):
        L = self.L
        self.progress(frame, idx, p, end)
        if end:
            return
        frame.alpha_composite(self.brand, (L.x0, L.st + 30))
        c = self.counters[idx]
        frame.alpha_composite(c, (L.top_x1 - c.width, L.st + 34))


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
        if isinstance(sc, StorySlate):
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
            f.alpha_composite(self.slates[shown].disclosure, (L.x0, L.st + 128))
        if cur < self.n:
            sl = self.slates[cur]
            a, rise = sl.text_alpha(t - self.starts[cur], cur == 0)
            if a > 0.002:
                x, y = sl.block_xy
                f.alpha_composite(_fade(sl.block, a), (x, int(y + rise)))
        p = 0.0
        if not is_end:
            p = min(1.0, max(0.0, (t - self.starts[shown]) / self.scenes[shown].dur))
        self.chrome.draw(f, min(shown, self.n - 1), p, is_end)
        return f


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
        for p in allowed_paths():
            full = p if os.path.isabs(p) else os.path.join(BASE, p)
            if os.path.exists(full):
                return full
    except Exception:
        pass
    return ''


def _audio(items: list[Item], starts: list[float], end_start: float,
           end_vo: str, total: float, work: str) -> str:
    ins, parts, labels = [], [], []
    for k, (it, s0) in enumerate(zip(items, starts)):
        lead = LEAD_FIRST if k == 0 else LEAD_NEXT
        ms = int(round((s0 + lead) * 1000))
        ins += ['-i', it.vo]
        parts.append(f'[{k}:a]aresample=48000,adelay={ms}|{ms}[v{k}]')
        labels.append(f'[v{k}]')
    k = len(items)
    ms = int(round((end_start + 0.18) * 1000))
    ins += ['-i', end_vo]
    parts.append(f'[{k}:a]aresample=48000,adelay={ms}|{ms}[v{k}]')
    labels.append(f'[v{k}]')
    voice = f'{"".join(labels)}amix=inputs={len(labels)}:normalize=0[vo]'
    parts.append(voice)

    bed = _bed_path()
    mix = os.path.join(work, 'mix.wav')
    if bed:
        k += 1
        ins += ['-stream_loop', '-1', '-i', bed]
        # Under the anchor, then up for the end card, then away.
        parts.append(
            f'[{k}:a]aresample=48000,atrim=0:{total:.2f},'
            f"volume='if(gte(t,{end_start:.2f}),0.30,0.12)':eval=frame,"
            f'afade=t=out:st={max(0.0, total - 0.9):.2f}:d=0.9[bed]')
        parts.append('[vo][bed]amix=inputs=2:duration=longest:normalize=0,'
                     f'atrim=0:{total:.2f}[a]')
    else:
        parts.append(f'[vo]apad,atrim=0:{total:.2f}[a]')
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

    audio = _audio(items, starts[:n], starts[n], end_vo, total, work)
    _mux(raw, audio, path)

    # The shelf tile: story one with its headline up.
    cov = os.path.splitext(path)[0] + '_cover.jpg'
    tl.frame(0.8).convert('RGB').save(cov, quality=92, subsampling=0,
                                      optimize=True)

    shutil.rmtree(work, ignore_errors=True)
    print(f'  ✓ {os.path.basename(path)}  ({total:.1f}s, {n} stories)  '
          f'+ {os.path.basename(cov)}')
    return {'path': path, 'cover': cov, 'seconds': total, 'stories': n,
            'dropped': [it.story.headline for it in dropped],
            'spoken': [it.spoken for it in items] + [END_SPOKEN]}
