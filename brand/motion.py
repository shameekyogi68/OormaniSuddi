"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Reel / Shorts engine
====================================
What makes a news reel look edited rather than generated:

  * NOTHING CUTS ON.  Every element arrives on an eased curve with a small
    rise and a per-line stagger. Hard-appearing text is the single loudest
    signal that a video was assembled by a script.
  * KEN BURNS IS EASED.  A linear zoom reads as a slideshow; a slow-in slow-out
    zoom with a little lateral drift reads as a camera move.
  * DURATION FOLLOWS READING TIME.  A scene holds for as long as its Kannada
    actually takes to read, floored at Motion.hold_min. Fixed 8.5s slots either
    bore the viewer or cut them off mid-sentence.
  * SAFE ZONES ARE REAL.  Instagram parks its action rail over the right 200px
    and its caption over the bottom ~470px. Anything there is decoration.
  * ONE STATIC LAYER PER SCENE.  Type is rendered once at 2x and reused every
    frame as a sprite; only the photograph is recomputed. That is the whole
    reason this runs in a couple of minutes instead of an hour.

Audio is mastered, not just mixed: the score ducks under each headline hit and
the whole thing is normalised to -14 LUFS / -1.5 dBTP, which is what Instagram
and YouTube expect. Anything hotter gets turned down by the platform and comes
back sounding squashed.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import numpy as np
from dataclasses import dataclass, replace, field
from types import SimpleNamespace
from PIL import Image, ImageDraw

from . import typo, components as cp
from .surface import (Surface, scrim, rule, panel, vgradient,
                      place_photo, grain, cover,
                      house_grade, paste_logo, radial_glow, vrule,
                      editorial_plate)
from .tokens import (C, Role, T, Grid, fmt, category, alpha, Grade, Motion,
                     Ease, clamp01, phase, Brand)
from .content import Story, Edition

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─────────────────────────────────────────────────────────────────────────────
#  TIMING
# ─────────────────────────────────────────────────────────────────────────────

def reading_seconds(*texts: str) -> float:
    """How long this much Kannada actually takes to read on a phone."""
    n = sum(len(t) for t in texts if t)
    return n / Motion.read_rate


def reel_line(story: Story) -> str:
    """The line a reel scene shows.

    A print headline is not a video headline. `reel_line` lets an editor write
    a short one; without it we fall back to the headline and the scene simply
    runs as long as that headline needs.
    """
    return (getattr(story, 'reel_line', '') or story.headline).strip()


def support_line(story: Story, head_secs: float) -> str:
    """A second line providing essential context, without overloading reading time."""
    explicit = (getattr(story, 'reel_support', '') or '').strip()
    if explicit:
        return explicit
    if head_secs > 5.5:
        return ''
    txt = (story.deck or (story.points[0] if story.points else '')).strip()
    if not txt or len(txt) > Motion.support_budget:
        return ''
    # …and only if it actually fits. support_budget (62 chars) and hold_max
    # (12s) were set independently, so a 46-char headline plus a 62-char deck
    # asks for ~16s of a 12s scene: the automatic path was manufacturing copy
    # the ceiling then cut off mid-sentence. A support line the viewer cannot
    # finish is worse than no support line, so it is dropped rather than shown
    # and truncated. An explicit reel_support is left to the editor — it warns
    # at render time instead.
    room = Motion.hold_max - Motion.build_in - Motion.settle - head_secs
    if reading_seconds(txt) * 0.9 > room:
        return ''
    return txt


@dataclass(frozen=True)
class Pace:
    """How a scene is timed, and what copy it carries.

    A reel and a bulletin are the same engine at two different viewing
    contracts. A reel is a glance in a vertical feed, so it shows the
    reel_line alone and caps at 12s — past that the viewer has swiped. A
    bulletin was opened on purpose on YouTube, so it shows the print headline
    AND the deck (the carousel's payload) and lets a scene run as long as that
    honestly takes. Neither ever compresses below reading speed.
    """
    name: str
    hold_max: float
    deck_lines: int
    full_headline: bool   # bulletin uses the print headline, reel the reel_line
    body_discount: float  # support skims; a deck that IS the story does not
    fill: int = 0         # facts promoted into the body to clear the floor


REEL = Pace('reel', Motion.hold_max, 2, False, 0.9)
BULLETIN = Pace('bulletin', Motion.bulletin_hold_max,
                Motion.bulletin_deck_lines, True, 1.0)


def pace_for(format_key: str) -> Pace:
    return BULLETIN if format_key in ('bulletin', 'bulletin_4k') else REEL


def head_line(story: Story, pace: Pace = REEL) -> str:
    """The headline a scene shows.

    A reel gets the short reel_line; a bulletin gets the print headline,
    because a 16:9 frame has the column for it and the extra words are
    information the viewer came for.
    """
    if pace.full_headline:
        return story.headline.strip()
    return reel_line(story)


def body_line(story: Story, head_secs: float, pace: Pace = REEL) -> str:
    """The copy under the headline.

    On a reel this is optional support, shown only when the headline leaves
    room. On a bulletin it is the point of the format: the deck, plus however
    many facts `pace.fill` has promoted.
    """
    if not pace.full_headline:
        return support_line(story, head_secs)
    blocks = [(story.deck or '').strip()]
    blocks += [p.strip() for p in story.points[:pace.fill]]
    blocks = [b for b in blocks if b]
    if not blocks and story.points:
        blocks = [story.points[0].strip()]
    return '  '.join(blocks)


def scene_need(story: Story, pace: Pace = REEL) -> float:
    """Seconds this scene's copy actually needs, BEFORE the hold_max ceiling.

    Kept separate from scene_seconds() so the renderer can compare the two and
    report a scene that has been clamped short rather than cutting the viewer
    off mid-sentence without saying so.
    """
    head = head_line(story, pace)
    hs = reading_seconds(head)
    body = body_line(story, hs, pace)
    return (Motion.build_in + hs
            + reading_seconds(body) * pace.body_discount + Motion.settle)


def scene_seconds(story: Story,
                  pace: Pace = REEL) -> tuple[float, str, str]:
    """(duration, headline shown, body shown) — honest about reading time."""
    head = head_line(story, pace)
    body = body_line(story, reading_seconds(head), pace)
    need = scene_need(story, pace)
    return (max(Motion.hold_min, min(need, pace.hold_max)), head, body)


def plan_durations(edition: Edition, intro: float = 1.9, outro: float = 3.0,
                   target: float | None = None, pace: Pace = REEL
                   ) -> tuple[float, list[float], float, int]:
    """Scene lengths from reading time.

    Returns (intro, holds, outro, n_stories_used).

    A `target` is a CEILING, not a quota. The old version scaled every scene by
    body/sum(holds) to hit the target exactly, which is how four stories ended
    up at 6.3 seconds each when they needed twenty. Nothing is ever compressed
    below what it takes to read; if the content will not fit the target, we
    drop stories from the end and say so.
    """
    holds = [scene_seconds(s, pace)[0] for s in edition.stories]
    used = len(holds)
    if target:
        while used > 1 and intro + sum(holds[:used]) + outro > target:
            used -= 1
    return intro, holds[:used], outro, used


def plan_bulletin(edition: Edition, intro: float = 1.9, outro: float = 3.0,
                  target: float | None = None
                  ) -> tuple[Pace, float, list[float], float, int, float]:
    """Decide how much of each story the bulletin carries.

    Returns (pace, intro, holds, outro, used, total).

    The length is DERIVED, never padded. A bulletin starts with the headline
    and the deck, which on real four-story copy already runs 84-97s. Facts are
    promoted into the body only while the whole thing still falls short of the
    60s floor — a floor that exists because YouTube treats sub-60s video as a
    Short and pulls its own frame instead of the thumbnail we render.

    `target` is a CEILING, exactly as it is everywhere else in this module:
    stories are dropped from the end to fit it and nothing is ever compressed
    below the time its copy takes to read.

    An earlier version scaled every hold proportionally to land on the target.
    It was wrong in both directions and silent in both. At `--bulletin-seconds
    60` a four-story edition needing 21.5 / 23.1 / 15.9 / 18.8s was shown at
    15.5 / 16.6 / 11.5 / 13.5 — every scene cut below reading time, guarded
    only by `hold_min`, which is a floor on a scene and says nothing about
    whether THIS scene's copy fits. At 120 it padded every scene by 65%, which
    D37 forbids for the same reason a thin edition is not padded. Worse, the
    short-scene warning was suppressed whenever a target was set — so the one
    run that needed the warning was the one run that could not produce it.

    If even every fact leaves it short, it stays short and the renderer says
    so. A thin edition is a thin edition; padding it would be the video
    equivalent of the guilt-assertion override this project refuses to add.
    """
    best = None
    for fill in (0, 1, 2):
        pace = replace(BULLETIN, fill=fill)
        i, holds, o, used = plan_durations(edition, intro, outro, target, pace)
        total = i + sum(holds) + o
        best = (pace, i, holds, o, used, total)
        if total >= Motion.bulletin_floor:
            break

    return best


# ─────────────────────────────────────────────────────────────────────────────
#  SPRITES — pre-rendered static layers
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Sprite:
    """A pre-rendered RGBA layer plus how it animates in."""
    img: Image.Image
    x: int
    y: int
    t_in: float = 0.0
    dur: float = Motion.text_in
    rise: float = 26.0                 # px it travels upward as it arrives
    ease: object = Ease.out_quint
    wipe: bool = False                 # reveal left-to-right behind a mask

    def draw(self, target: Image.Image, t: float):
        p = phase(t, self.t_in, self.dur, self.ease)
        if p <= 0.001:
            return
        im = self.img
        if self.wipe and p < 1.0:
            w = max(1, int(im.width * p))
            im = im.crop((0, 0, w, im.height))
        dy = int(self.rise * (1.0 - p))
        if p < 1.0:
            a = im.getchannel('A').point(lambda v, _p=p: int(v * _p))
            im = im.copy()
            im.putalpha(a)
        target.alpha_composite(im, (self.x, self.y + dy))


def _sprite_from(draw_fn, W: int, H: int, ss: int, x: int, y: int, **kw) -> Sprite:
    """Render `draw_fn(surface)` into a transparent tile and pack it."""
    sf = Surface(W, H, ss, bg=(0, 0, 0, 0))
    draw_fn(sf)
    img = sf.img.resize((W, H), Image.Resampling.LANCZOS) if ss != 1 else sf.img
    return Sprite(img=img, x=x, y=y, **kw)


# ─────────────────────────────────────────────────────────────────────────────
#  KEN BURNS
# ─────────────────────────────────────────────────────────────────────────────

class KenBurns:
    """An eased, drifting crop over a pre-graded plate."""

    def __init__(self, path: str, w: int, h: int, focal=(0.5, 0.42),
                 zoom: float = Motion.kb_zoom, drift: float = Motion.kb_drift,
                 direction: int = 1, fade_bottom: float = 0.0):
        self.w, self.h = w, h
        self.zoom, self.drift, self.dir = zoom, drift, direction
        big_w = int(w * (1 + zoom + abs(drift)))
        big_h = int(h * (1 + zoom + abs(drift)))
        im = cover(Image.open(path), big_w, big_h, focal)
        self.plate = house_grade(im).convert('RGB')
        self.fade = None
        if fade_bottom > 0:
            a = np.ones(h, dtype=np.float32)
            n = max(1, int(h * fade_bottom))
            u = np.linspace(0.0, 1.0, n)
            a[h - n:] = 1.0 - (u * u * (3.0 - 2.0 * u))
            self.fade = Image.fromarray(
                np.repeat((a * 255).astype(np.uint8)[:, None], w, 1), 'L')

    def frame(self, p: float) -> Image.Image:
        e = Ease.in_out_sine(clamp01(p))
        sc = 1.0 + self.zoom * (1.0 - e)          # settle INTO the frame
        cw, ch = self.w * sc, self.h * sc
        pw, ph = self.plate.size
        # Clamped to the plate. The plate is int(size * (1 + travel)), so when
        # a window has exactly the photograph's shape (speed news, D83) the
        # crop can overhang it by a fraction of a pixel, and PIL refuses a
        # negative offset outright rather than rounding it.
        cw, ch = min(cw, pw), min(ch, ph)
        dx = max(0.0, (pw - cw) * (0.5 + self.drift * self.dir * (e - 0.5)))
        dy = max(0.0, (ph - ch) * 0.5)
        box = (dx, dy, min(pw, dx + cw), min(ph, dy + ch))
        im = self.plate.resize((self.w, self.h), Image.Resampling.BICUBIC, box)
        if self.fade is not None:
            im = im.convert('RGBA')
            im.putalpha(self.fade)
        return im


# ─────────────────────────────────────────────────────────────────────────────
#  SCENES
# ─────────────────────────────────────────────────────────────────────────────

class Scene:
    dur: float = 3.0

    def frame(self, t: float) -> Image.Image:
        raise NotImplementedError


class BrandSting(Scene):
    """The opener. Deliberately short — a long logo animation is a scroll cue."""

    def __init__(self, edition: Edition, W: int, H: int, ss: int, dur: float):
        self.W, self.H, self.ss, self.dur = W, H, ss, dur
        self.ed_date = edition.date_kn
        self.ed_strap = edition.strapline
        self.bed = self._bed()
        self.sprites = self._sprites()

    def _bed(self) -> Image.Image:
        sf = Surface(self.W, self.H, self.ss)
        cp.page_base(sf, 0.9)
        # Frame 0 is the profile-grid tile and the default cover. The first cut
        # of this opened at 13/255 mean luminance — a near-black square in the
        # grid, which reads as a dead post. Lifted deliberately.
        radial_glow(sf, self.W * 0.5, self.H * 0.40, self.W * 1.25, C.gold_700, 0.34)
        radial_glow(sf, self.W * 0.5, self.H * 0.40, self.W * 0.62, C.gold_600, 0.30)
        radial_glow(sf, self.W * 0.5, self.H * 0.40, self.W * 0.30, C.gold_500, 0.20)
        cp.horizon(sf, self.H * 0.615, 1.0)
        grain(sf, Grade.grain, Grade.grain_shadow_bias)
        return sf.img.resize((self.W, self.H), Image.Resampling.LANCZOS).convert('RGBA')

    def _sprites(self) -> list[Sprite]:
        W, H, ss = self.W, self.H, self.ss
        out = []

        big = 96 if H > W else 78

        def name(sf):
            b = typo.layout(Brand.name, typo.font('kn', sf.s(big)),
                            sf.s(W - 140), 1.2, align='center')
            typo.draw_block(sf.img, b, sf.s(70), sf.s(10), Role.text_hi,
                            box_w=sf.s(W - 140))
        out.append(_sprite_from(name, W, 160, ss, 0, int(H * 0.545),
                                t_in=0.30, dur=0.55, rise=30))

        def tag(sf):
            typo.draw_text(sf.img, Brand.tagline, sf.s(W / 2), sf.s(38),
                           typo.font('kn_var', sf.s(38), weight=620), C.gold_500,
                           anchor_x='c')
        out.append(_sprite_from(tag, W, 70, ss, 0, int(H * 0.545) + 130,
                                t_in=0.46, dur=0.55, rise=20))

        def strap(sf):
            f = typo.font('kn_var', sf.s(30), weight=560)
            txt = f'{self.ed_date}  •  {self.ed_strap}'
            tw = typo.text_width(txt, f) / ss
            x = (W - tw - 56) / 2
            panel(sf, [x, 0, x + tw + 56, 62], alpha(C.paper_50, 0.06))
            vrule(sf, x, 0, 62, C.gold_500, 3)
            typo.draw_text(sf.img, txt, sf.s(x + 28), sf.s(43), f, C.paper_100)
        out.append(_sprite_from(strap, W, 80, ss, 0, int(H * 0.545) + 210,
                                t_in=0.62, dur=0.55, rise=16))
        return out

    def frame(self, t: float) -> Image.Image:
        f = self.bed.copy()
        # logo: scales in on a back-ease, then settles
        p = phase(t, 0.0, Motion.logo_in, Ease.out_back)
        size = int(300 * (0.86 + 0.14 * p))
        lg = Image.open(os.path.join(BASE, 'assets', 'logo_clean_circle.png')) \
            .convert('RGBA').resize((size, size), Image.Resampling.LANCZOS)
        if p < 1.0:
            # Starts at 0.55 opacity, not 0 — a cover frame has to have
            # something on it.
            lg.putalpha(lg.getchannel('A').point(
                lambda v: int(v * clamp01(0.55 + 0.45 * p))))
        cx, cy = self.W // 2, int(self.H * 0.40)
        f.alpha_composite(lg, (cx - size // 2, cy - size // 2))
        for s in self.sprites:
            s.draw(f, t)
        return f


def _badge_mark(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float,
                colour, alert: bool):
    """The mark at the head of a badge pill — DRAWN, never typed.

    This exists because the typed version did not work and could not be made
    to work. "▪" is in none of the four house faces and not in SF either; "⚠"
    is in SF alone, and a badge carrying Kannada is set in a Kannada face by
    `font_for`, so it never reached SF. Both shipped as empty boxes on every
    reel. A drawn shape has no font to be missing from.
    """
    if alert:
        # A warning triangle with its bar and dot, drawn to the same optical
        # weight as the square so the two badges sit on one baseline.
        h = r * 2.05
        w = r * 2.25
        d.polygon([(cx, cy - h * 0.52), (cx + w * 0.5, cy + h * 0.46),
                   (cx - w * 0.5, cy + h * 0.46)], fill=colour)
    else:
        d.rounded_rectangle((cx - r, cy - r, cx + r, cy + r),
                            radius=max(1.0, r * 0.28), fill=colour)


class StoryScene(Scene):
    """Full-bleed picture with the type seated over its lower half.

    The earlier cut of this split the frame into a photo band and a text band.
    On a 9:16 canvas that wastes the format: you get a letterboxed picture and
    a headline too small to read at arm's length. Broadcast does the opposite —
    the picture fills the frame and the words live on it — so that is what this
    does, with the scrim doing the work that a black band used to.
    """

    def __init__(self, story: Story, W: int, H: int, ss: int, dur: float,
                 index: int, total: int, safe, direction: int = 1,
                 pace: Pace = REEL, chapter_idx: int = 0,
                 chapter_names: list[str] | None = None):
        self.st, self.W, self.H, self.ss, self.dur = story, W, H, ss, dur
        self.i, self.n, self.safe = index, total, safe
        self.pace = pace
        self.chapter_idx = chapter_idx
        self.chapter_names = chapter_names
        # Frame scale. The design is drawn for a 1080-wide portrait frame and
        # a 1920-wide landscape one; anything larger is the SAME design at a
        # multiple of that size, so every fixed measure is multiplied by it.
        # 1.0 for reel and the 1080p bulletin, so those are untouched.
        self.fs = (W / 1920.0) if W > H else (W / 1080.0)
        # In landscape the type takes a column on the left and the picture
        # gets the whole right-hand region at FULL height, rather than being
        # laid full-bleed and then half-covered. Cropping a 4:3 source to
        # this near-square region keeps about three quarters of it; the old
        # full-width-then-cover kept about a third, and threw away the middle
        # of the frame, which is where the subject usually is.
        self.panel_w = int(W * Motion.panel_width) if W > H else 0
        self.photo_x = self.panel_w
        self.photo_w = W - self.panel_w
        self.kb = None
        if story.photo and os.path.exists(story.photo.path):
            self.kb = KenBurns(story.photo.path, self.photo_w, H,
                               focal=story.photo.focal, direction=direction)
        # Measured first: in landscape the panel's depth follows the type,
        # so _over() cannot draw it until the block has been fitted.
        self._m = self._measure()
        self.bed = self._bed()
        self.over = self._over()
        self.sprites = self._sprites()

    def _bed(self) -> Image.Image:
        sf = Surface(self.W, self.H, self.ss)
        cp.page_base(sf, 0.5)
        if self.kb is None:
            # No honest picture, so the frame gets the same editorial plate the
            # cards use: visibly a graphic, and consistent with the rest of the
            # set. An earlier version left these scenes as a bare glow and they
            # read as empty next to the photographed ones.
            editorial_plate(sf, (self.photo_x, 0, self.W, self.H),
                            category(self.st.category), seed=self.st.headline,
                            show_word=self.W > self.H)
        grain(sf, Grade.grain, Grade.grain_shadow_bias)
        return sf.img.resize((self.W, self.H), Image.Resampling.LANCZOS).convert('RGBA')

    def _over(self) -> Image.Image:
        """Scrims and masthead — everything that sits on the moving picture."""
        W, H, ss = self.W, self.H, self.ss
        sl, st_, sr, sb = self.safe
        fs = self.fs
        sf = Surface(W, H, ss, bg=(0, 0, 0, 0))
        scrim(sf, 0, st_ + 30 * fs, C.ink_950, 0.88 if self.kb else 0.62, 0.0, curve=1.5)
        if H > W:
            # Same ramp as the fact cards, so a cut between the two does not
            # change how dark the bottom of the frame is. They used to differ
            # (0.30→0.86 here, 0.36→0.88 there) and the mismatch showed as a
            # small brightness jump on every transition.
            if self.kb is not None:
                scrim(sf, H * 0.30, H * 0.62, C.ink_950, 0.0, 0.72, curve=1.5)
                scrim(sf, H * 0.62, H * 0.90, C.ink_950, 0.72, 0.97, curve=1.2)
                scrim(sf, H * 0.90, H, C.ink_950, 0.97, 0.99, curve=1.0)
            else:
                scrim(sf, H * 0.42, H * 0.90, C.ink_950, 0.0, 0.90, curve=1.5)
        else:
            # ── Landscape: a real lower-third ─────────────────────────────
            # Earlier cuts veiled the picture with a gradient and set the type
            # on top. On a busy coastal photograph the headline then sits over
            # rocks and surf and never looks clean, however dark the veil is.
            # Broadcast solves it with a PANEL: the picture stops, the panel
            # begins, and the type is on its own ground. The defined edge is
            # most of what reads as produced rather than overlaid.
            # The panel runs the full HEIGHT down the left instead of the
            # full WIDTH across the bottom. Same reasoning as D36 — the type
            # gets its own ground and the defined edge is what reads as
            # produced — but spending the frame's width rather than its
            # height, so the picture keeps its people whole. See D38.
            pw = self.panel_w
            panel(sf, (0, 0, pw, H), alpha(C.ink_950, 0.988))
            # a sliver of light on the seam, then the brand rule, so the
            # column does not simply butt against the photograph
            vrule(sf, pw - 2 * fs, 0, H, alpha(C.paper_50, 0.16), 1.0 * fs)
            vrule(sf, pw, 0, H, C.gold_500, 3.0 * fs)

        if H > W:
            cp.masthead(sf, sl, st_ - 118 * fs, W - sl * 2, right_top=self.st.date_kn,
                        right_bot=self.st.time_kn, on_photo=self.kb is not None,
                        scale=0.92 * fs)
        else:
            # Everything that is furniture — lockup, date, time — lives in
            # the column. It used to be set over the photograph on the right,
            # where it landed on a hospital signboard and became unreadable
            # while also obscuring the picture it was sitting on. The column
            # is a solid ground, so none of it needs a shadow to survive.
            pw = self.panel_w
            by = st_ - 6 * fs
            right = pw - Motion.panel_pad * fs
            cp.masthead(sf, sl, by, int(right - sl), on_photo=False,
                        scale=0.72 * fs, rule_below=False)
            fd = typo.font_for(self.st.date_kn, 'kn_var', sf.s(27 * fs), weight=650)
            ft = typo.font_for(self.st.time_kn, 'kn_var', sf.s(22 * fs), weight=440)
            typo.draw_text(sf.img, self.st.date_kn, sf.s(right), sf.s(by + 32 * fs),
                           fd, Role.text_hi, anchor_x='r')
            rule(sf, right - 168 * fs, by + 52 * fs, right,
                 alpha(C.gold_500, 0.45), 1.0 * fs)
            typo.draw_text(sf.img, self.st.time_kn, sf.s(right), sf.s(by + 88 * fs),
                           ft, Role.text_dim, anchor_x='r')
            # Only the handle sits on the picture now, so the foot veil can
            # be shallow — enough to carry gold type over a bright desk
            # without taking another slice out of the photograph.
            scrim(sf, H * 0.90, H, C.ink_950, 0.0, 0.80, curve=1.8)
        if H > W:
            # Portrait only: the band the platform covers still carries the
            # brand, because it is visible on a paused reel and on every repost.
            band = H - sb
            rule(sf, sl, band + 54 * fs, W - sl, Role.hairline_soft, 1.0 * fs)
            typo.draw_text(sf.img, Brand.handle, sf.s(W / 2), sf.s(band + 122 * fs),
                           typo.font('latin', sf.s(40 * fs), weight=760), C.gold_500,
                           anchor_x='c', tracking=0.015)
            typo.draw_text(sf.img, Brand.tagline, sf.s(W / 2), sf.s(band + 168 * fs),
                           typo.font('kn_var', sf.s(26 * fs), weight=520),
                           Role.text_dim, anchor_x='c')
        else:
            typo.draw_text(sf.img, Brand.handle, sf.s(W - sl), sf.s(H - sb + 34 * fs),
                           typo.font('latin', sf.s(26 * fs), weight=740), C.gold_500,
                           anchor_x='r', tracking=0.015)
        return sf.img.resize((W, H), Image.Resampling.LANCZOS)

    def _measure(self):
        """Fit the type, then decide how deep the lower-third has to be.

        Kept out of `_sprites` because in landscape the panel is sized by the
        block it holds, and `_over()` draws that panel before the sprites are
        built. Measuring once, here, is what stops the two from disagreeing —
        a panel that does not match its type is the failure D36 was written
        about, arriving from the other side.
        """
        W, H, ss = self.W, self.H, self.ss
        sl, st_, sr, sb = self.safe
        st = self.st
        landscape = W > H
        fs = self.fs
        # Portrait keeps clear of Instagram's right action rail. Landscape has
        # no chrome, but a headline set the full 1920 wide is unreadable, so it
        # is measured to a column instead.
        cw = (int(self.panel_w - sl - Motion.panel_pad * fs) if landscape
              else (W - sl - sr))
        # The type scale is calibrated for a 1080-WIDE portrait frame. Most
        # YouTube viewing is on a phone, where a 1920x1080 video plays about
        # 400px wide — so a 19px source line lands at roughly 4px and is simply
        # gone. Everything small gets scaled up in landscape.
        #
        # `self.fs` is the FRAME scale on top of that: a 4K bulletin is the
        # same design at twice the size, so every fixed measure doubles with
        # it. Without this a 3840-wide render kept 1920-sized type and the
        # column came out two-thirds empty — which is what the first
        # `bulletin_4k` cut actually did.
        ts = (1.38 if landscape else 1.0) * fs

        bottom = H - sb
        src_y = bottom - T.micro[0] * ts * 1.5
        block_bottom = src_y - 40 * ts

        # What this scene shows, and for how long, are decided together in
        # scene_seconds() — so the type on screen is never more than the time
        # on screen can carry.
        _dur, head_txt, sup_txt = scene_seconds(st, self.pace)
        d_blk = None
        if sup_txt:
            dk = int(T.deck[0] * ts)
            # How many lines the body gets. On a reel the body is optional
            # support, so it stays out of the headline's way. On a bulletin
            # the deck IS what the viewer came for — a 16:9 frame that showed
            # only the headline would be a Short with black bars, which is the
            # thing this format exists to stop being. See DECISIONS.md D37.
            dl = self.pace.deck_lines if landscape else 2
            d_blk = typo.fit(sup_txt, 'kn_var', ss * dk, ss * int(dk * 0.8),
                             ss * cw, ss * dk * T.deck[1] * dl, T.deck[1],
                             weight=450, max_lines=dl)

        # The credit is LAID OUT, not assumed to be one line. It was given a
        # fixed one-line tile — `micro * ts * 1.5 + 6` — while being wrapped to
        # the full column width, so a credit long enough to wrap (an AI label
        # plus a caption is easily 60 characters) had its second line sliced
        # through the middle by the edge of its own sprite. Over a busy
        # photograph the sliced line read as noise rather than as text, which
        # is why it survived this long.
        c_blk = None
        if st.credit_line:
            c_blk = typo.layout(
                st.credit_line,
                typo.font('kn_var', int(ss * T.micro[0] * ts * 1.05), weight=470),
                ss * cw, 1.34)
            if c_blk.n > 2:      # never let the label push the headline down
                c_blk = typo.layout(
                    typo.ellipsize(st.credit_line, c_blk.f, ss * cw * 2),
                    c_blk.f, ss * cw, 1.34)
        cap_h = int(c_blk.height / ss) + 8 if c_blk is not None else 0
        eb_h = int(44 * ts)
        # Where the block can actually begin. In landscape that is inside the
        # lower-third panel, not near the top of the frame — measuring from the
        # frame top let `fit` choose a headline far too tall for the panel, and
        # the block then overran the meta row at the foot.
        # A fixed panel took 53% of the frame however little copy the scene
        # carried, so a two-line deck still threw away the bottom half of the
        # photograph — on the Manipal frame the subject sat directly under it.
        # The headline is fitted against the DEEPEST panel we would ever
        # allow, so `fit` can never choose a size the panel cannot hold; the
        # panel is then pulled down to whatever the block actually needs.
        # See DECISIONS.md D38.
        # The column is full height, so the block starts under the masthead
        # rather than inside a slab, and the meta row anchors its foot.
        region_top = (st_ + 120 * fs) if landscape else (st_ + 220 * fs)
        # The photo credit belongs on the PHOTO, above the panel, which is also
        # where it reads correctly as a caption.
        # cap_h is reserved in BOTH orientations now. It used to be excluded
        # in landscape because the credit sat on the photograph; now that it
        # is in the column, a four-line deck ran straight over it.
        head_room = (block_bottom - region_top - eb_h - 34 * ts - cap_h
                     - ((d_blk.height / ss + 34 * ts) if d_blk is not None else 0))
        # A narrower column needs a slightly smaller headline and more lines
        # to work with; it has the whole frame height to spend them in.
        hi = int((76 if landscape else 96) * fs)
        hb = typo.fit(head_txt, 'kn', ss * hi, ss * int(T.h4[0] * fs), ss * cw,
                      ss * head_room, T.h1[1], max_lines=5 if landscape else 4)

        # These must be the SAME steps _sprites() actually advances by, or
        # block_h under-measures the block. It used to read `44 + 34`, which
        # is right only when ts == 1.0 — in landscape ts is 1.38, so the real
        # block ran ~60px lower than this claimed and anything positioned
        # from it landed on the deck. Portrait is unaffected: eb_h is 44 and
        # 34 * 1.0 is 34, exactly the old numbers.
        block_h = (eb_h + 34 * ts + hb.height / ss
                   + ((34 * ts + d_blk.height / ss)
                      if d_blk is not None else 0))
        # Seated at the foot of the safe area whether or not there is a photo,
        # so a mixed reel does not have its headline jumping up and down the
        # frame from scene to scene.
        y = block_bottom - block_h

        # Top-aligned under the masthead: stable from scene to scene, where
        # centring would make the headline hop about as block heights vary.
        if landscape:
            y = region_top

        return SimpleNamespace(
            landscape=landscape, cw=cw, ts=ts, fs=fs, bottom=bottom, src_y=src_y,
            block_bottom=block_bottom, head_txt=head_txt, sup_txt=sup_txt,
            d_blk=d_blk, cap_h=cap_h, c_blk=c_blk, eb_h=eb_h,
            region_top=region_top, hb=hb, block_h=block_h, y=y)

    def _sprites(self) -> list[Sprite]:
        m = self._m
        W, H, ss = self.W, self.H, self.ss
        sl, st_, sr, sb = self.safe
        st = self.st
        landscape, cw, ts, fs = m.landscape, m.cw, m.ts, m.fs
        bottom, src_y, block_bottom = m.bottom, m.src_y, m.block_bottom
        head_txt, sup_txt, d_blk = m.head_txt, m.sup_txt, m.d_blk
        cap_h, eb_h = m.cap_h, m.eb_h
        region_top = m.region_top
        hb, block_h, y = m.hb, m.block_h, m.y
        out: list[Sprite] = []

        if cap_h:
            # "ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ" is an honesty label, not decoration: it is how
            # a reader knows this is a representative picture and not the
            # scene itself. On the photograph it landed on a sunlit desk and
            # became invisible, and no shadow fixes every frame. So in
            # landscape it goes in the column, above the meta row, where it
            # is legible by construction and the picture stays clean.
            cap_x = sl
            cap_w = cw
            # Seated just under the block it belongs to, not at a fixed
            # offset from the foot: a four-line deck ends far lower than a
            # two-line one, and a fixed position left the credit jammed
            # against the last line. Clamped so it can never reach the meta
            # row, which head_room has already reserved the space for.
            cap_y = (min(y + block_h + 20 * fs,
                         src_y - 36 * ts - cap_h - 12 * fs) if landscape
                     else (y - cap_h - 22 * fs))

            def cap(sf, _w=cap_w, _b=m.c_blk):
                b = _b          # the block _measure() sized this tile for
                # In landscape it sits on the solid column and needs nothing.
                # In portrait it sits ABOVE the copy block — high enough that
                # the scrim has barely begun — so on a bright, busy frame it
                # was 19px of dim grey over a sunlit crowd and simply could
                # not be read. It is an honesty label ("ಎಐ ರಚಿತ ಚಿತ್ರ",
                # "ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ"); a label the reader cannot read does not
                # discharge the obligation it exists for.
                sh = None if landscape else (0, sf.s(1), sf.s(9), (0, 0, 0, 215))
                typo.draw_block(sf.img, b, 0, 0,
                                alpha(C.paper_300, 0.94 if landscape else 1.0),
                                shadow=sh, box_w=sf.s(_w))
            out.append(Sprite(_sprite_from(cap, cap_w, cap_h, ss, 0, 0).img,
                              int(cap_x), int(cap_y),
                              t_in=0.34, dur=0.5, rise=12 * fs))

        def eb(sf):
            cp.eyebrow(sf, 0, 0, cw, st, scale=ts,
                       on_photo=self.kb is not None)
        out.append(Sprite(_sprite_from(eb, cw, int(eb_h + 6 * fs), ss, 0, 0).img, sl, int(y),
                          t_in=0.08, dur=0.5, rise=14 * fs, wipe=True))
        y += eb_h + 34 * ts

        lh = hb.lh / ss
        for k, line in enumerate(hb.lines):
            def one(sf, _l=line, _b=hb):
                typo.draw_text(sf.img, _l, 0, sf.s(_b.first_rise / ss),
                               typo.font('kn', _b.f.size), Role.text_hi,
                               shadow=(0, sf.s(3), sf.s(16), (0, 0, 0, 190)))
            out.append(Sprite(
                _sprite_from(one, cw, int(lh + hb.first_rise / ss) + int(14 * fs), ss, 0, 0).img,
                sl, int(y + k * lh),
                t_in=0.28 + k * Motion.text_stagger, dur=Motion.text_in, rise=34 * fs))
        y += hb.height / ss + 34 * ts

        if d_blk is not None:
            def dk(sf, _b=d_blk):
                typo.draw_block(sf.img, _b, 0, 0, C.paper_200, box_w=sf.s(cw),
                                shadow=(0, sf.s(2), sf.s(12), (0, 0, 0, 170)))
            out.append(Sprite(
                _sprite_from(dk, cw, int(d_blk.height / ss) + int(12 * fs), ss, 0, 0).img,
                sl, int(y), t_in=0.30 + len(hb.lines) * Motion.text_stagger + 0.14,
                dur=Motion.text_in, rise=24 * fs))

        # Meta row. It closes the COLUMN now, not the whole frame, with a
        # hairline above it so the type block ends on a defined edge.
        meta_w = cw

        pad = 36 * ts if landscape else 0

        def src(sf):
            if landscape:
                rule(sf, 0, 0, meta_w, alpha(C.paper_50, 0.13), 1.0 * fs)
            cp.sourceline(sf, 0, pad, meta_w, st, scale=ts)
        out.append(Sprite(
            _sprite_from(src, meta_w, int(T.micro[0] * ts * 1.9 + pad),
                         ss, 0, 0).img,
            sl, int(src_y - pad), t_in=0.95, dur=0.5, rise=10 * fs))
        return out

    def frame(self, t: float) -> Image.Image:
        f = self.bed.copy()
        if self.kb:
            f.alpha_composite(self.kb.frame(t / self.dur).convert('RGBA'),
                              (self.photo_x, 0))
        f.alpha_composite(self.over, (0, 0))
        for s in self.sprites:
            s.draw(f, t)
        return f


class ChapterScene(Scene):
    """Deep-dive chapter scene: focuses on a key fact or public advisory.

    Shows Ken Burns camera motion (alternating angle or gallery photo),
    top masthead with chapter tracker, and a structured lower-third card
    with a badge pill and high-legibility Kannada text.
    """

    def __init__(self, story: Story, W: int, H: int, ss: int, dur: float,
                 badge: str, text: str, chapter_idx: int, total_chapters: int,
                 chapter_names: list[str] | None = None, safe=None,
                 photo_path: str | None = None, direction: int = 1,
                 is_alert: bool = False, pace: Pace = REEL,
                 photo=None):
        self.st, self.W, self.H, self.ss, self.dur = story, W, H, ss, dur
        self.badge = badge
        self.text = text
        self.chapter_idx = chapter_idx
        self.total_chapters = total_chapters
        self.chapter_names = chapter_names
        self.safe = safe
        self.is_alert = is_alert
        self.pace = pace
        self.fs = (W / 1920.0) if W > H else (W / 1080.0)
        self.panel_w = int(W * Motion.panel_width) if W > H else 0
        self.photo_x = self.panel_w
        self.photo_w = W - self.panel_w

        # Resolve the photograph AND the object it came from together, so the
        # picture on screen and the label under it can never describe
        # different images. Falling back to the hero for the picture while
        # leaving the label blank is what let an AI-generated gallery frame
        # hold the frame for twenty seconds with nothing disclosing it.
        shown = None
        if photo is not None and os.path.exists(getattr(photo, 'path', '')):
            shown = photo
        elif photo_path and os.path.exists(photo_path):
            shown = next((p for p in self.st.all_photos if p.path == photo_path), None)
        elif self.st.photo and os.path.exists(self.st.photo.path):
            shown = self.st.photo
        self.shown = shown
        pic = shown.path if shown is not None else None
        self.kb = None
        if pic:
            focal = shown.focal or (0.5, 0.45)
            self.kb = KenBurns(pic, self.photo_w, H, focal=focal, direction=direction)

        self.bed = self._bed()
        self.over = self._over()
        self.sprites = self._sprites()

    def _bed(self) -> Image.Image:
        sf = Surface(self.W, self.H, self.ss)
        cp.page_base(sf, 0.5)
        if self.kb is None:
            editorial_plate(sf, (self.photo_x, 0, self.W, self.H),
                            category(self.st.category), seed=self.badge + self.text,
                            show_word=self.W > self.H)
        grain(sf, Grade.grain, Grade.grain_shadow_bias)
        return sf.img.resize((self.W, self.H), Image.Resampling.LANCZOS).convert('RGBA')

    def _over(self) -> Image.Image:
        W, H, ss = self.W, self.H, self.ss
        sl, st_, sr, sb = self.safe
        fs = self.fs
        sf = Surface(W, H, ss, bg=(0, 0, 0, 0))
        scrim(sf, 0, st_ + 30 * fs, C.ink_950, 0.88 if self.kb else 0.62, 0.0, curve=1.5)

        if H > W:
            # Portrait: the copy block sits over the lower third, so the veil
            # has to be dense enough there to carry white Kannada over ANY
            # frame — wet sand at midday and a lit shopfront included, which
            # are the two the old 0.0→0.95 ramp lost. The ramp starts higher
            # and reaches full depth before the badge, so contrast is a
            # property of the layout rather than a property of the photograph.
            if self.kb is not None:
                scrim(sf, H * 0.30, H * 0.62, C.ink_950, 0.0, 0.72, curve=1.5)
                scrim(sf, H * 0.62, H * 0.90, C.ink_950, 0.72, 0.97, curve=1.2)
                scrim(sf, H * 0.90, H, C.ink_950, 0.97, 0.99, curve=1.0)
            else:
                scrim(sf, H * 0.42, H * 0.90, C.ink_950, 0.0, 0.90, curve=1.5)
            cp.masthead(sf, sl, st_ - 118 * fs, W - sl * 2, right_top=self.st.date_kn,
                        right_bot=self.st.time_kn, on_photo=self.kb is not None,
                        scale=0.92 * fs)
            band = H - sb
            rule(sf, sl, band + 54 * fs, W - sl, Role.hairline_soft, 1.0 * fs)
            typo.draw_text(sf.img, Brand.handle, sf.s(W / 2), sf.s(band + 122 * fs),
                           typo.font('latin', sf.s(40 * fs), weight=760), C.gold_500,
                           anchor_x='c', tracking=0.015)
            typo.draw_text(sf.img, Brand.tagline, sf.s(W / 2), sf.s(band + 168 * fs),
                           typo.font('kn_var', sf.s(26 * fs), weight=520),
                           Role.text_dim, anchor_x='c')
        else:
            # Landscape
            pw = self.panel_w
            panel(sf, (0, 0, pw, H), alpha(C.ink_950, 0.988))
            vrule(sf, pw - 2 * fs, 0, H, alpha(C.paper_50, 0.16), 1.0 * fs)
            vrule(sf, pw, 0, H, C.gold_500, 3.0 * fs)
            by = st_ - 6 * fs
            right = pw - Motion.panel_pad * fs
            cp.masthead(sf, sl, by, int(right - sl), on_photo=False,
                        scale=0.72 * fs, rule_below=False)
            fd = typo.font_for(self.st.date_kn, 'kn_var', sf.s(27 * fs), weight=650)
            ft = typo.font_for(self.st.time_kn, 'kn_var', sf.s(22 * fs), weight=440)
            typo.draw_text(sf.img, self.st.date_kn, sf.s(right), sf.s(by + 32 * fs),
                           fd, Role.text_hi, anchor_x='r')
            rule(sf, right - 168 * fs, by + 52 * fs, right,
                 alpha(C.gold_500, 0.45), 1.0 * fs)
            typo.draw_text(sf.img, self.st.time_kn, sf.s(right), sf.s(by + 88 * fs),
                           ft, Role.text_dim, anchor_x='r')
            scrim(sf, H * 0.90, H, C.ink_950, 0.0, 0.80, curve=1.8)
            typo.draw_text(sf.img, Brand.handle, sf.s(W - sl), sf.s(H - sb + 34 * fs),
                           typo.font('latin', sf.s(26 * fs), weight=740), C.gold_500,
                           anchor_x='r', tracking=0.015)
        return sf.img.resize((W, H), Image.Resampling.LANCZOS)

    def _sprites(self) -> list[Sprite]:
        W, H, ss = self.W, self.H, self.ss
        sl, st_, sr, sb = self.safe
        fs = self.fs
        landscape = W > H
        cw = (int(self.panel_w - sl - Motion.panel_pad * fs) if landscape else (W - sl - sr))
        ts = (1.38 if landscape else 1.0) * fs

        out: list[Sprite] = []

        bottom = H - sb
        src_y = bottom - T.micro[0] * ts * 1.5

        # Type scale. A fact card is read at arm's length on a phone in a
        # scrolling feed, exactly like the headline card that precedes it —
        # so it is set at a comparable size. The previous ceiling of 46px
        # against a 96px headline made every card after the first look like a
        # caption, which is the "fonts are not on size" complaint: not one
        # wrong value, but two scenes drawn to two different scales.
        #
        # Bounded by the space between the masthead and the meta row rather
        # than by a fixed 340px, so a short fact is set BIG instead of small
        # in a half-empty block.
        region_top = st_ + (120 * fs if landscape else 300 * fs)
        avail_h = max(int(180 * ts), int(src_y - region_top - 96 * ts))
        blk = typo.fit(self.text, 'kn_var',
                       size_hi=int(Motion.reel_card_hi * ts),
                       size_lo=int(Motion.reel_card_lo * ts),
                       max_w=cw, max_h=avail_h, leading=1.38, weight=600,
                       max_lines=Motion.reel_card_lines)

        badge_h = int(52 * ts)
        gap = int(30 * ts)
        total_block_h = badge_h + gap + blk.height

        # The disclosure for the picture THIS card is showing. Legally this is
        # the important one: the fact cards are where the AI-generated gallery
        # frames appear, and they carried no label at all. See D49.
        cred = self.shown.disclosure if self.shown is not None else ''
        c_blk = None
        if cred:
            c_blk = typo.layout(
                cred,
                typo.font('kn_var', int(ss * T.micro[0] * ts * 1.05), weight=470),
                ss * cw, 1.34)
            if c_blk.n > 2:
                c_blk = typo.layout(
                    typo.ellipsize(cred, c_blk.f, ss * cw * 2), c_blk.f,
                    ss * cw, 1.34)
        cap_h = int(c_blk.height / ss) + 8 if c_blk is not None else 0

        # Seated on the meta row, so the block always closes on the same edge
        # however many lines it runs to. Anchoring the TOP instead let a short
        # card float with a hole beneath it and a long one crowd the source
        # line — the cards visibly disagreed with each other from scene to
        # scene, which is most of why the sequence read as unfinished.
        y = src_y - Motion.reel_block_foot * ts - total_block_h

        # 1. Badge pill
        def draw_badge(sf):
            f_bd = typo.font('kn_var', int(sf.s(Motion.reel_badge_size * ts)), weight=700)
            pad_x = sf.s(26 * ts)
            mark_r = sf.s(7.0 * ts)
            mark_gap = sf.s(14 * ts)
            tw = typo.text_width(self.badge, f_bd)
            bw = pad_x * 2 + mark_r * 2 + mark_gap + tw
            bh = sf.s(badge_h)
            d = ImageDraw.Draw(sf.img)
            if self.is_alert:
                fill_col = (195, 45, 30, 240)
                out_col = (255, 90, 75, 255)
                txt_col = C.paper_50
            else:
                fill_col = (*C.gold_500, 240)
                out_col = (*C.gold_400, 255)
                txt_col = C.ink_950
            d.rounded_rectangle((0, 0, bw, bh), radius=int(bh * 0.5),
                                fill=fill_col, outline=out_col,
                                width=max(1, int(sf.s(1.2 * fs))))
            _badge_mark(d, pad_x + mark_r, bh * 0.5, mark_r, txt_col, self.is_alert)
            rise_bd, _ = typo.ink_extents(self.badge, f_bd)
            typo.draw_text(sf.img, self.badge, pad_x + mark_r * 2 + mark_gap,
                           (bh + rise_bd) * 0.50, f_bd, txt_col)

        out.append(Sprite(_sprite_from(draw_badge, cw, badge_h + int(10 * fs), ss, 0, 0).img,
                          sl, int(y), t_in=0.10, dur=0.45, rise=16 * fs, wipe=True))

        # 2. Text Block Sprites (cinematic line stagger)
        y_text = y + badge_h + gap
        lh = blk.lh / ss
        for k, line in enumerate(blk.lines):
            def one_line(sf, _l=line, _b=blk):
                # weight 600, the same weight `fit` measured this block at. It
                # used to draw at 620, so every line was set slightly wider
                # than the width the wrap was computed against and long lines
                # crept past the measure.
                typo.draw_text(sf.img, _l, 0, sf.s(_b.first_rise / ss),
                               typo.font('kn_var', _b.f.size, weight=600), Role.text_hi,
                               shadow=(0, sf.s(3), sf.s(18), (0, 0, 0, 205)))
            out.append(Sprite(
                _sprite_from(one_line, cw, int(lh + blk.first_rise / ss) + int(14 * fs), ss, 0, 0).img,
                sl, int(y_text + k * lh),
                t_in=0.22 + k * Motion.text_stagger, dur=Motion.text_in, rise=28 * fs))

        # 3. The image disclosure, seated above the badge.
        if c_blk is not None:
            def cap(sf, _b=c_blk, _w=cw):
                sh = None if landscape else (0, sf.s(1), sf.s(9), (0, 0, 0, 215))
                typo.draw_block(sf.img, _b, 0, 0,
                                alpha(C.paper_300, 0.94 if landscape else 1.0),
                                shadow=sh, box_w=sf.s(_w))
            out.append(Sprite(_sprite_from(cap, cw, cap_h, ss, 0, 0).img,
                              sl, int(y - cap_h - 20 * fs),
                              t_in=0.30, dur=0.5, rise=12 * fs))

        # 4. Sourceline Sprite
        pad = 36 * ts if landscape else 0
        def src(sf):
            if landscape:
                rule(sf, 0, 0, cw, alpha(C.paper_50, 0.13), 1.0 * fs)
            cp.sourceline(sf, 0, pad, cw, self.st, scale=ts)
        out.append(Sprite(
            _sprite_from(src, cw, int(T.micro[0] * ts * 1.9 + pad), ss, 0, 0).img,
            sl, int(src_y - pad), t_in=0.85, dur=0.45, rise=10 * fs))

        return out

    def frame(self, t: float) -> Image.Image:
        f = self.bed.copy()
        if self.kb:
            f.alpha_composite(self.kb.frame(t / self.dur).convert('RGBA'),
                              (self.photo_x, 0))
        f.alpha_composite(self.over, (0, 0))
        for s in self.sprites:
            s.draw(f, t)
        return f


class OutroScene(Scene):
    """The end card.

    It used to be 2.4 seconds of a near-black panel, which was survivable. On
    a narrated reel it carries the whole spoken sign-off — eight or nine
    seconds — and nine seconds of a dead black frame at the end of a video is
    where the retention graph falls off a cliff. So it keeps the story's
    photograph behind it, pushed in slowly and held well down, and the brand
    sits on a picture rather than on nothing.
    """

    def __init__(self, edition: Edition, W: int, H: int, ss: int, dur: float,
                 safe, photo=None):
        self.W, self.H, self.ss, self.dur, self.safe = W, H, ss, dur, safe
        self.ed = edition
        self.kb = None
        self.shown = None
        if photo is not None and os.path.exists(getattr(photo, 'path', '')):
            self.shown = photo
            self.kb = KenBurns(photo.path, W, H,
                               focal=getattr(photo, 'focal', (0.5, 0.45)),
                               zoom=Motion.kb_zoom * 0.7, direction=1)
        self.bed = self._bed()
        self.veil = self._veil()
        self.sprites = self._sprites()

    def _bed(self):
        sf = Surface(self.W, self.H, self.ss)
        cp.page_base(sf, 0.8)
        cp.horizon(sf, self.H * 0.74, 1.0)
        radial_glow(sf, self.W * 0.5, self.H * 0.76, self.W * 0.8, C.gold_600, 0.14)
        if self.kb is None:
            grain(sf, Grade.grain, Grade.grain_shadow_bias)
        return sf.img.resize((self.W, self.H), Image.Resampling.LANCZOS).convert('RGBA')

    def _veil(self):
        """What sits over the photograph so the wordmark reads cleanly."""
        if self.kb is None:
            return None
        sf = Surface(self.W, self.H, self.ss, bg=(0, 0, 0, 0))
        # Deep and even: this is a brand card, not a news card, so the picture
        # is atmosphere and must never compete with the handle.
        scrim(sf, 0, self.H * 0.34, C.ink_950, 0.93, 0.80, curve=1.2)
        scrim(sf, self.H * 0.34, self.H, C.ink_950, 0.80, 0.95, curve=1.1)
        radial_glow(sf, self.W * 0.5, self.H * 0.30, self.W * 0.85, C.gold_600, 0.13)
        grain(sf, Grade.grain, Grade.grain_shadow_bias)
        return sf.img.resize((self.W, self.H), Image.Resampling.LANCZOS).convert('RGBA')

    def _sprites(self):
        W, H, ss = self.W, self.H, self.ss
        sl, st_, sr, sb = self.safe
        cw = W - sl * 2
        out = []
        y = int(H * 0.46)

        big = 84 if H > W else 66

        def nm(sf):
            b = typo.layout(Brand.name, typo.font('kn', sf.s(big)),
                            sf.s(cw), 1.2, align='center')
            typo.draw_block(sf.img, b, 0, 0, Role.text_hi, box_w=sf.s(cw))
        out.append(Sprite(_sprite_from(nm, cw, 140, ss, 0, 0).img, sl, y,
                          t_in=0.10, dur=0.5, rise=24))

        def cta(sf):
            typo.draw_text(sf.img, Brand.follow_kn,
                           sf.s(cw / 2), sf.s(36),
                           typo.font('kn_var', sf.s(34), weight=520),
                           C.paper_200, anchor_x='c')
        out.append(Sprite(_sprite_from(cta, cw, 70, ss, 0, 0).img, sl, y + 150,
                          t_in=0.34, dur=0.5, rise=18))

        def handle(sf):
            typo.draw_text(sf.img, Brand.handle, sf.s(cw / 2), sf.s(72),
                           typo.font('latin', sf.s(76 if H > W else 58),
                                     weight=780), C.gold_500,
                           anchor_x='c', tracking=0.01)
        out.append(Sprite(_sprite_from(handle, cw, 110, ss, 0, 0).img, sl, y + 226,
                          t_in=0.52, dur=0.55, rise=22))

        def where(sf):
            # A gold hairline over the coverage word, so the card closes on a
            # defined edge instead of trailing off into the dark. At 28px dim
            # grey with 140px of nothing above it, this line simply read as
            # something left over rather than as the last line of a card.
            rule(sf, cw * 0.5 - 54, 8, cw * 0.5 + 54, alpha(C.gold_500, 0.55), 2.0)
            typo.draw_text(sf.img, Brand.coverage,
                           sf.s(cw / 2), sf.s(58),
                           typo.font('kn_var', sf.s(31), weight=520),
                           C.paper_200, anchor_x='c')
        out.append(Sprite(_sprite_from(where, cw, 84, ss, 0, 0).img, sl, y + 344,
                          t_in=0.70, dur=0.5, rise=14))

        # The end card now holds a photograph (D47), so it discloses it like
        # every other card that shows one.
        #
        # Placed ABOVE the safe line, not below it. Instagram parks its caption
        # over the bottom ~470px, so a disclosure sitting there is covered on
        # the platform this reel is mainly made for — and a label the viewer
        # cannot see does not disclose anything. Set quieter than the lockup
        # but not faint: legibility is the whole function.
        if self.shown is not None and self.shown.disclosure:
            cb = typo.layout(self.shown.disclosure,
                             typo.font('kn_var', int(ss * T.micro[0] * 0.95),
                                       weight=450),
                             ss * cw, 1.32, align='center')
            ch = int(cb.height / ss) + 10

            def cred(sf, _b=cb, _w=cw):
                typo.draw_block(sf.img, _b, 0, 0, alpha(C.paper_200, 0.92),
                                shadow=(0, sf.s(1), sf.s(9), (0, 0, 0, 215)),
                                box_w=sf.s(_w))
            cred_y = min(y + 452, (H - sb) - ch - 16)
            out.append(Sprite(_sprite_from(cred, cw, ch, ss, 0, 0).img,
                              sl, int(cred_y),
                              t_in=0.88, dur=0.5, rise=10))
        return out

    def frame(self, t: float) -> Image.Image:
        f = self.bed.copy()
        if self.kb is not None:
            f.alpha_composite(self.kb.frame(t / self.dur).convert('RGBA'), (0, 0))
            f.alpha_composite(self.veil, (0, 0))
        p = phase(t, 0.0, 0.70, Ease.out_back)
        p_live = clamp01(t / max(0.1, self.dur))
        # Subtle continuous cinematic expansion (1.0 -> 1.035) ensures the frame never freezes or feels stuck
        scale = (0.82 + 0.18 * p) * (1.0 + 0.035 * p_live)
        size = int(round(230 * scale))
        if not hasattr(self, '_logo_cached'):
            self._logo_cached = Image.open(os.path.join(BASE, 'assets', 'logo_clean_circle.png')).convert('RGBA')
        lg = self._logo_cached.resize((size, size), Image.Resampling.LANCZOS)
        if p < 1:
            lg.putalpha(lg.getchannel('A').point(lambda v: int(v * clamp01(p * 1.5))))
        f.alpha_composite(lg, ((self.W - size) // 2, int(self.H * 0.30) - size // 2))
        for s in self.sprites:
            s.draw(f, t)
        return f


# ─────────────────────────────────────────────────────────────────────────────
#  TIMELINE & RENDER
# ─────────────────────────────────────────────────────────────────────────────

def _transition(prev: Image.Image, nxt: Image.Image, p: float,
                W: int, H: int) -> Image.Image:
    """The cut between two scenes.

    A soft-edged WIPE, not a dissolve. A dissolve superimposes two
    photographs, and for its whole length the frame is a double exposure of
    two crowds — the single thing that most made these read as auto-generated
    rather than edited. A wipe shows one picture or the other at every pixel,
    which is what a news cutting room actually does.

    The leading edge carries a narrow gold rim: enough to read as a deliberate
    device at 30fps, far short of the full-frame gold wash that used to flash
    over the whole picture and crush the photograph underneath it.
    """
    e = Ease.in_out_cubic(clamp01(p))
    soft = max(2.0, W * 0.038)              # the wipe's soft edge, in px
    edge = -soft + e * (W + 2 * soft)       # where the boundary is now

    xs = np.arange(W, dtype=np.float32)
    # 1 where the new frame is fully in, 0 where the old one still is.
    m = np.clip((edge - xs) / soft + 0.5, 0.0, 1.0)
    # Smoothstep, so the boundary has no visible hard line.
    m = m * m * (3.0 - 2.0 * m)

    mask = Image.fromarray(
        np.repeat((m * 255).astype(np.uint8)[None, :], H, 0), 'L')
    out = Image.composite(nxt, prev, mask)

    # A rim of light riding the boundary — brightest at mid-wipe, gone by the
    # ends so the transition never announces itself at a cut point.
    rim = np.exp(-((xs - edge) / (soft * 0.70)) ** 2)
    strength = np.sin(np.pi * clamp01(p)) ** 0.85
    lay = np.zeros((1, W, 4), np.float32)
    lay[0, :, 0], lay[0, :, 1], lay[0, :, 2] = C.gold_400
    lay[0, :, 3] = rim * 108.0 * strength
    out.alpha_composite(Image.fromarray(
        np.repeat(lay, H, 0).astype('uint8'), 'RGBA'))
    return out


def _progress_bar(frame: Image.Image, p: float, W: int, y: int = 0,
                  fs: float = 1.0):
    """A thin gold rule that fills across the video, flush to the top edge.

    It used to sit at y=58, which is clear of the masthead in a 9:16 frame and
    runs straight through the logo in a 16:9 one, because landscape has no
    platform chrome to clear and so places the masthead much higher. Flush to
    the edge is both safe at every aspect and how broadcast does it.

    `fs` is the frame scale, so the bar keeps its weight relative to the frame
    rather than thinning to a hairline on a 4K master.
    """
    h = max(2, int(round(4 * fs)))
    d = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    d.paste((*C.paper_50, 34), (0, 0, W, h))
    d.paste((*C.gold_500, 255), (0, 0, max(1, int(W * clamp01(p))), h))
    frame.alpha_composite(d, (0, y))


@dataclass
class Card:
    """One card of a reel: one picture, one badge, one thought, one beat.

    This is the single spine the whole reel is built on. `brand.voice` reads
    it to decide how many spoken beats to synthesize; this module reads it to
    decide how many scenes to draw. Because both come from the same list, the
    sentence being spoken is always the sentence on screen — which is exactly
    what the previous design could not guarantee, since it derived the picture
    from a total duration and the speech from the story separately.

    `key` matches brand.voice.card_keys() one for one. Do not change one
    without the other.
    """
    key: str
    kind: str              # 'lead' | 'fact' | 'advisory' | 'outro'
    text: str = ''
    badge: str = ''
    is_alert: bool = False
    photo: object = None   # a Photo for this card's picture, or None


# Badge wording per category. No decorative characters: the marker in front of
# a badge is DRAWN as a shape by `_badge_mark`, never typed. Every glyph that
# was previously typed there — ▪ and ⚠ — is absent from all four house faces
# AND from SF, so each of them shipped as an empty box on every reel.
_BADGE = {
    'incident': ('ಘಟನಾ ಸ್ಥಳದ ವಿವರ', 'ತನಿಖಾ ಪ್ರಗತಿ ಹಾಗೂ ಕ್ರಮ', 'ಸ್ಥಳ ಪರಿಶೀಲನೆ ಹಾಗೂ ಕ್ರಮ'),
    'default':  ('ಪ್ರಮುಖ ವಿದ್ಯಮಾನ', 'ಹಿನ್ನೆಲೆ ಹಾಗೂ ವಿವರ', 'ವಿಶೇಷ ಮಾಹಿತಿ'),
}


def _story_chapter_defs(st: Story) -> list[tuple[str, str, str, bool]]:
    """Build (chapter_name, badge_label, text, is_alert) for multi-chapter breakdown."""
    cat = st.category
    incident = cat in ('civic', 'crime', 'accident')
    labels = _BADGE['incident' if incident else 'default']

    defs: list[tuple[str, str, str, bool]] = [
        ("ಮುಖ್ಯಾಂಶ", "ಬ್ರೇಕಿಂಗ್ ಮುಖ್ಯಾಂಶ", head_line(st, REEL), False)
    ]

    pts = [p.strip() for p in (st.points or []) if p.strip()]
    shorts = list(getattr(st, 'reel_points', []) or [])

    if len(pts) >= 1:
        c1_name = "ಸ್ಥಳ ವಿವರ" if incident else "ಪ್ರಮುಖ ವಿವರ"
        c1_text = shorts[0].strip() if len(shorts) > 0 and shorts[0].strip() else pts[0]
        defs.append((c1_name, labels[0], c1_text, False))

    if len(pts) >= 2:
        c2_name = "ತನಿಖಾ ವಿವರ" if incident else "ಮುಖ್ಯ ಅಂಶ"
        c2_text = shorts[1].strip() if len(shorts) > 1 and shorts[1].strip() else pts[1]
        defs.append((c2_name, labels[1], c2_text, False))

    if (st.takeaway or '').strip():
        badge_txt = 'ಸಾರ್ವಜನಿಕ ಎಚ್ಚರಿಕೆ' if incident else 'ಸಾರ್ವಜನಿಕ ಪ್ರಕಟಣೆ'
        defs.append(("ಜಾಗೃತಿ", badge_txt, st.takeaway.strip(), True))
    elif len(pts) >= 3:
        c3_name = "ಜಾಗೃತಿ" if incident else "ವಿಶೇಷ ಮಾಹಿತಿ"
        c3_text = shorts[2].strip() if len(shorts) > 2 and shorts[2].strip() else pts[2]
        defs.append((c3_name, labels[min(2, len(labels) - 1)], c3_text, False))

    return defs


def reel_cards(story: Story) -> list[Card]:
    """The cards this story becomes, in order — including the outro.

    Mirrors brand.voice.card_keys() exactly.
    """
    incident = story.category in ('civic', 'crime', 'accident')
    labels = _BADGE['incident' if incident else 'default']
    gallery = list(getattr(story, 'gallery', []) or [])

    cards = [Card(key='lead', kind='lead', text=head_line(story, REEL),
                  badge='', photo=story.photo)]

    facts = [p.strip() for p in story.points if p.strip()]
    shorts = list(getattr(story, 'reel_points', []) or [])
    for i, p in enumerate(facts):
        pic = gallery[i] if i < len(gallery) else None
        # The card shows the short form when the editor wrote one. The VOICE
        # still carries the full point either way, so nothing is lost from the
        # reel — only from the frame, which is the point. See D51.
        on_card = (shorts[i].strip() if i < len(shorts) and shorts[i].strip()
                   else p)
        cards.append(Card(key=f'fact{i}', kind='fact', text=on_card,
                          badge=labels[min(i, len(labels) - 1)], photo=pic))

    if (story.takeaway or '').strip():
        pic = gallery[len(facts)] if len(facts) < len(gallery) else None
        badge_txt = 'ಸಾರ್ವಜನಿಕ ಎಚ್ಚರಿಕೆ' if incident else 'ಸಾರ್ವಜನಿಕ ಪ್ರಕಟಣೆ'
        cards.append(Card(key='advisory', kind='advisory',
                          text=story.takeaway.strip(),
                          badge=badge_txt, is_alert=True, photo=pic))

    cards.append(Card(key='signoff', kind='outro'))
    return cards


def card_read_seconds(card: Card) -> float:
    """How long this card must stay up for its Kannada to be readable.

    Passed to the voice engine as a floor on the beat, because a TTS voice
    reads Kannada far faster than a viewer meeting the sentence for the first
    time on a moving picture. Without it the cut lands the moment the voice
    stops and the reel feels rushed even when it is perfectly in sync.
    """
    if card.kind == 'outro':
        return Motion.reel_outro
    return (Motion.build_in + reading_seconds(card.text) * Motion.reel_read_ease
            + Motion.settle)


def reel_min_spans(story: Story) -> dict[str, float]:
    """{beat key: seconds it needs on screen} — the contract with brand.voice."""
    return {c.key: card_read_seconds(c) for c in reel_cards(story)}


def audit_sync(video: str, cuts: list[float], vo_path: str,
               tol: float = 0.12) -> tuple[bool, list[str]]:
    """Check, on the FINISHED file, that every cut lands between sentences.

    This module's whole claim is that the card on screen is the sentence being
    spoken. A claim nobody measures is a wish, so it is measured: the rendered
    narration is scanned for its actual silences, and every cut time is
    required to fall inside one. A cut in the middle of a word is then a test
    failure rather than something a viewer notices after publication.

    Returns (ok, notes).
    """
    notes: list[str] = []
    try:
        vd = float(subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'csv=p=0', video], capture_output=True, text=True,
            check=True).stdout.strip())
        out = subprocess.run(
            ['ffmpeg', '-hide_banner', '-i', vo_path, '-af',
             'silencedetect=n=-45dB:d=0.35', '-f', 'null', '-'],
            capture_output=True, text=True).stderr
    except Exception as e:
        return True, [f'sync audit skipped ({e})']

    import re as _re
    starts = [float(x) for x in _re.findall(r'silence_start: ([\d.]+)', out)]
    ends = [float(x) for x in _re.findall(r'silence_end: ([\d.]+)', out)]
    pauses = list(zip(starts, ends))
    if not pauses:
        return True, ['sync audit: no pauses detected in the narration']

    bad = []
    for i, c in enumerate(cuts, 1):
        if not any(a - tol <= c <= b + tol for a, b in pauses):
            near = min(pauses, key=lambda p: min(abs(c - p[0]), abs(c - p[1])))
            bad.append(f'cut {i} at {c:.2f}s is mid-sentence '
                       f'(nearest pause {near[0]:.2f}–{near[1]:.2f}s)')
    if bad:
        notes += bad
    else:
        notes.append(f'sync audit: all {len(cuts)} cuts land between sentences')
    notes.append(f'picture {vd:.2f}s')
    return (not bad), notes


def _write_cover(scenes: list, path: str, H: int, W: int):
    """The shelf tile: the first story card with its headline up.

    Instagram and YouTube Shorts both use this if you set it; leaving the
    default (frame 0, a logo) is a scroll-past.
    """
    story_scenes = [sc for sc in scenes if isinstance(sc, StoryScene)]
    if not story_scenes:
        return
    sc0 = story_scenes[0]
    t_cover = min(max(1.35, Motion.build_in), max(0.4, sc0.dur * 0.55))
    cover_path = os.path.splitext(path)[0] + '_cover.jpg'
    os.makedirs(os.path.dirname(os.path.abspath(cover_path)) or '.', exist_ok=True)
    sc0.frame(t_cover).convert('RGB').save(
        cover_path, quality=92, subsampling=0, optimize=True)
    # A 16:9 bulletin already has a purpose-built thumbnail — yt_thumbnail.jpg,
    # set at a size that survives the feed. Telling an editor to use this
    # landscape frame as "the IG / Shorts cover" would send them to the wrong
    # file for the wrong platform, so the note follows the aspect.
    where = ('IG / Shorts cover' if H > W
             else 'in-video still — the YouTube thumbnail is yt_thumbnail.jpg')
    print(f'  ✓ cover {os.path.basename(cover_path)}  ({where})')


def _h264_encode_args() -> list[str]:
    """Hardware encode on Apple Silicon; software x264 everywhere else."""
    import sys
    if sys.platform == 'darwin':
        return ['-c:v', 'h264_videotoolbox', '-b:v', '12M', '-profile:v', 'high']
    return [
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
        '-maxrate', '12M', '-bufsize', '24M',
        '-profile:v', 'high', '-level', '4.2',
        '-x264-params', 'ref=4:bframes=3',
    ]


def _encode_frames(scenes: list, starts: list[float], total: float,
                   n_frames: int, fps: int, W: int, H: int,
                   frame_scale: float, XF: float) -> str:
    """Draw every frame and pipe it into x264. Shared by both reel paths."""
    raw = os.path.join(BASE, 'build', '_reel_video.mp4')
    os.makedirs(os.path.dirname(raw), exist_ok=True)

    # Frames are piped straight into ffmpeg. Writing 900 JPEGs to disk and
    # reading them back costs more than the drawing does.
    enc = subprocess.Popen([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
        '-r', str(fps), '-i', 'pipe:0',
        # Both platforms re-encode on upload, so what matters is the quality
        # of what they re-encode FROM. 3 Mbps was leaving quality on the table.
        *_h264_encode_args(),
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', raw], stdin=subprocess.PIPE)

    for k in range(n_frames):
        t = k / fps

        in_trans = False
        for i in range(1, len(scenes)):
            s_tr = starts[i]
            if s_tr <= t < s_tr + XF:
                p = clamp01((t - s_tr) / XF)
                f_prev = scenes[i - 1].frame(min(t - starts[i - 1], scenes[i - 1].dur))
                f_next = scenes[i].frame(min(t - s_tr, scenes[i].dur))
                f = _transition(f_prev, f_next, p, W, H)
                in_trans = True
                break

        if not in_trans:
            cur = 0
            for i, s0 in enumerate(starts):
                if t >= s0:
                    cur = i
            sc = scenes[cur]
            f = sc.frame(min(t - starts[cur], sc.dur))

        _progress_bar(f, t / total, W, fs=frame_scale)
        enc.stdin.write(f.convert('RGB').tobytes())
        if k % 60 == 0 or k == n_frames - 1:
            print(f'    frame {k + 1}/{n_frames}  ({t:5.1f}s)', end='\r')
    enc.stdin.close()
    enc.wait()
    print(f'\n  ✓ picture locked')
    return raw


def _render_narrated_reel(edition: Edition, path: str, voice, *, W: int, H: int,
                          safe, ss: int, fps: int, frame_scale: float,
                          bgm, sfx_dir, keep_frames: bool, pace: Pace) -> str:
    """A reel whose every cut is placed from the measured narration.

    The timeline is not a design decision here — it is arithmetic on the audio:

        scene i starts at  segment[i].start - lead_in
        scene i runs for   segment[i].span + crossfade

    which puts the crossfade INTO the silence between two sentences, brings
    each card up `lead_in` before its sentence begins, and leaves the last
    card standing for the tail after the final word. Nothing here can drift,
    because there is no second clock to drift against.
    """
    st = edition.stories[0]
    cards = reel_cards(st)
    segs = list(voice.segments)

    # The two lists are generated from the same spine (reel_cards /
    # voice.card_keys), so they normally match exactly. If a beat went missing
    # — an engine dropped a clip, an editor's script had nothing for a card —
    # keep only the cards that actually have speech, rather than showing a
    # card in silence or speaking over the wrong picture.
    by_key = {c.key: c for c in cards}
    plan = [(by_key[s.key], s) for s in segs if s.key in by_key]
    if not plan:
        raise ValueError('the narration has no beat matching any reel card')
    if len(plan) != len(segs):
        missing = [s.key for s in segs if s.key not in by_key]
        print(f'  ⚠ narration beats with no card: {", ".join(missing)} — '
              f'their audio would play over the wrong picture, so they have '
              f'been dropped.')

    XF = Motion.scene_cross
    lead_in = voice.lead_in

    print(f'  narration-locked: {len(plan)} cards from {len(segs)} spoken beats')
    scenes: list[Scene] = []
    dirs = [1, -1, 2, -2]
    for i, (card, seg) in enumerate(plan):
        dur = seg.span + XF
        if card.kind == 'outro':
            # The end card keeps the story's own picture behind it, so the
            # longest static moment of the reel is not a black rectangle.
            scenes.append(OutroScene(edition, W, H, ss, dur, safe,
                                     photo=st.photo))
        elif card.kind == 'lead':
            scenes.append(StoryScene(st, W, H, ss, dur, 0, 1, safe,
                                     direction=dirs[0], pace=pace))
        else:
            pic = None
            if card.photo is not None and os.path.exists(card.photo.path):
                pic = card.photo.path
            scenes.append(ChapterScene(
                st, W, H, ss, dur, badge=card.badge, text=card.text,
                chapter_idx=i, total_chapters=len(plan), safe=safe,
                photo_path=pic, direction=dirs[i % len(dirs)],
                is_alert=card.is_alert, pace=pace, photo=card.photo))
        hold = seg.span
        print(f'    {i + 1}. {card.key:9} {hold:5.2f}s  '
              f'({seg.speech:.2f}s spoken + {seg.gap:.2f}s beat)  '
              f'"{(card.text or "—")[:34]}"')

    # The scene clock and the audio clock, stated once so they cannot diverge.
    starts = [seg.start - lead_in for _c, seg in plan]
    total = starts[-1] + scenes[-1].dur
    n_frames = int(round(total * fps))
    print(f'  total {total:.1f}s · {n_frames} frames · {W}x{H} @{fps}fps '
          f'· narration {voice.duration:.1f}s')

    _write_cover(scenes, path, H, W)
    raw = _encode_frames(scenes, starts, total, n_frames, fps, W, H,
                         frame_scale, XF)
    audio = _master_narrated_audio(total, plan, lead_in, bgm, sfx_dir, voice)
    out = _mux(raw, audio, path)
    if not keep_frames and os.path.exists(raw):
        os.remove(raw)

    ok, notes = audit_sync(out, starts[1:], voice.path)
    for n in notes:
        print(f'  {"✓" if ok else "✗"} {n}')
    if not ok:
        print('  ✗ this reel cuts mid-sentence. That is the fault the '
              'narration-locked timeline exists to prevent — do not publish '
              'it without looking at why.')
    return out


def render_reel(edition: Edition, path: str, format_key: str = 'reel',
                target_seconds: float | None = None, ss: int | None = None,
                fps: int = Motion.fps, bgm: str | None = None,
                sfx_dir: str | None = None, keep_frames: bool = False,
                voiceover: str | None = None, voice=None) -> str:
    """Render the day's edition as video and master the audio.

    Drives both the 9:16 reel and the 16:9 bulletin: same engine, different
    `Pace`. See DECISIONS.md D37 for why the bulletin carries the deck, and
    D39 for why a reel is the lead story with no logo sting.

    `voice` is a brand.voice.VoiceTrack — a narration whose per-beat
    boundaries have been MEASURED. Given one, the reel is cut from those
    boundaries: one card per spoken beat, each held for exactly as long as
    its own sentence takes, so the card on screen is always the sentence in
    the viewer's ear. `voiceover` (a bare path) is the older, unmeasured
    form; it still works, but it can only place cuts by guessing.
    """
    edition.validate()
    F = fmt(format_key)
    W, H, safe = F.w, F.h, F.safe
    # The design is drawn for a 1080-wide portrait frame and a 1920-wide
    # landscape one; a larger format is the same design scaled up.
    frame_scale = (W / 1920.0) if W > H else (W / 1080.0)
    # A format that is already at 2x delivery resolution does not also need a
    # 2x supersampled canvas — that is a 4x pixel bill for antialiasing the
    # eye cannot resolve. `bulletin_4k` declares ss=1 for exactly this reason;
    # honour it rather than overriding it with the parameter default.
    if ss is None:
        ss = F.ss

    pace = pace_for(format_key)
    XF = Motion.scene_cross

    # ── The narrated reel: the picture is cut from the speech ─────────────
    # Everything below this branch is the older path, which decides scene
    # lengths from reading time alone. When a measured VoiceTrack is present
    # we do not guess at all: each card gets exactly its own beat's span, and
    # the whole timeline is a restatement of the audio.
    if voice is not None and pace.name != 'bulletin' and getattr(voice, 'segments', None):
        return _render_narrated_reel(
            edition, path, voice, W=W, H=H, safe=safe, ss=ss, fps=fps,
            frame_scale=frame_scale, bgm=bgm, sfx_dir=sfx_dir,
            keep_frames=keep_frames, pace=pace)

    if pace.name == 'bulletin':
        pace, intro_d, holds, outro_d, used, _t = plan_bulletin(
            edition, target=target_seconds)
        stories = edition.stories[:used]
    else:
        # D39: a reel is ONE story. The carousel and the 16:9 bulletin carry
        # the rest of the edition. Four headlines in 30s is a slideshow the
        # viewer swipes off; a 12–18s lead with the news on frame 0 is what
        # the platforms actually distribute.
        lead_ed = replace(edition, stories=edition.stories[:1])
        if voiceover and os.path.exists(voiceover):
            from .voice import get_audio_duration
            vdur = get_audio_duration(voiceover)
            if vdur > 1.0:
                intro_d = Motion.reel_intro
                outro_d = Motion.reel_outro
                holds = [round(vdur + 0.85, 2)]
                used = 1
            else:
                intro_d, holds, outro_d, used = plan_durations(
                    lead_ed, intro=Motion.reel_intro, outro=Motion.reel_outro,
                    target=target_seconds, pace=pace)
        else:
            intro_d, holds, outro_d, used = plan_durations(
                lead_ed, intro=Motion.reel_intro, outro=Motion.reel_outro,
                target=target_seconds, pace=pace)
        stories = edition.stories[:used]
        if used < len(edition.stories):
            print(f'  · reel is the lead story only '
                  f'({len(edition.stories) - used} more on the carousel / bulletin)')

    if pace.name == 'bulletin' and used < len(edition.stories):
        print(f'  ⚠ {len(edition.stories) - used} storie(s) dropped: they will not '
              f'fit {target_seconds:.0f}s at a readable pace. Shorten the '
              f'headlines with reel_line, or raise the target.')
    # A reel scene shows the reel_line alone, so a long headline with no
    # reel_line is a real problem there. A bulletin shows the print headline
    # on purpose, so the same check would be pure noise.
    if pace.name != 'bulletin':
        long_ones = [s for s in stories
                     if not s.reel_line
                     and len(s.headline) > Motion.reel_line_budget]
        if long_ones:
            print(f'  ⚠ {len(long_ones)} headline(s) over '
                  f'{Motion.reel_line_budget} chars with no reel_line — those '
                  f'scenes have to run long to stay readable.')

    # hold_max is a ceiling, so a scene needing more than it is silently cut
    # short and the viewer never finishes reading. That is the exact failure
    # this module exists to prevent, so it is reported rather than swallowed:
    # the fix is shorter copy, not a longer reel.
    # Unconditionally. A target is exactly when a scene is most likely to be
    # short, so suppressing this under a target silenced the only case it was
    # written for.
    for st, shown in zip(stories, holds):
        need = scene_need(st, pace)
        if need > shown + 0.05:
            print(f'  ⚠ "{reel_line(st)[:38]}…" needs {need:.1f}s to read but '
                  f'the scene caps at {shown:.1f}s — {need - shown:.1f}s short. '
                  f'Shorten reel_line or reel_support.')

    print(f'  building scenes … intro {intro_d:.1f}s + '
          f'{" + ".join(f"{h:.1f}" for h in holds)}s + outro {outro_d:.1f}s')

    scenes: list[Scene] = []
    if intro_d > 0.05:
        scenes.append(BrandSting(edition, W, H, ss, intro_d))

    is_deep_reel = (pace.name != 'bulletin' and len(stories) == 1 and holds[0] > 18.0)
    if is_deep_reel:
        st = stories[0]
        ch_defs = _story_chapter_defs(st)
        K = len(ch_defs)
        if K >= 2:
            # Preserve total hold by accounting for (K - 1) additional crossfades
            sum_dur = holds[0] + (K - 1) * XF
            ch0_dur = min(18.0, max(12.0, sum_dur * 0.28))
            rem_dur = (sum_dur - ch0_dur) / (K - 1)
            ch_durs = [ch0_dur] + [rem_dur] * (K - 1)
            ch_names = [name for name, _, _, _ in ch_defs]
            dirs = [1, 2, -1, -2]
            gallery = getattr(st, 'gallery', []) or []

            # Chapter 0: Hook / Headline
            scenes.append(StoryScene(st, W, H, ss, ch_durs[0], 0, 1, safe,
                                     direction=dirs[0], pace=pace,
                                     chapter_idx=0, chapter_names=ch_names))

            # Chapters 1..K-1: Deep dive cards
            for k in range(1, K):
                name, badge, text, is_alert = ch_defs[k]
                pic = None
                photo_obj = None
                if k - 1 < len(gallery) and os.path.exists(gallery[k - 1].path):
                    photo_obj = gallery[k - 1]
                    pic = photo_obj.path
                scenes.append(ChapterScene(
                    st, W, H, ss, ch_durs[k], badge=badge, text=text,
                    chapter_idx=k, total_chapters=K, chapter_names=ch_names,
                    safe=safe, photo_path=pic, direction=dirs[k % len(dirs)],
                    is_alert=is_alert, pace=pace, photo=photo_obj))
            print(f'  ✓ dynamic multi-chapter breakdown: {K} chapters '
                  f'({" ▸ ".join(ch_names)})')
        else:
            scenes.append(StoryScene(st, W, H, ss, holds[0], 0, 1, safe,
                                     direction=1, pace=pace))
    else:
        for i, (st, d) in enumerate(zip(stories, holds)):
            scenes.append(StoryScene(st, W, H, ss, d, i, len(stories), safe,
                                     direction=1 if i % 2 == 0 else -1, pace=pace))

    if outro_d > 0.05:
        scenes.append(OutroScene(edition, W, H, ss, outro_d, safe))

    starts, t0 = [], 0.0
    for sc in scenes:
        starts.append(t0)
        t0 += sc.dur - XF
    total = t0 + XF
    n_frames = int(round(total * fps))
    print(f'  total {total:.1f}s · {n_frames} frames · {W}x{H} @{fps}fps')
    if pace.name == 'bulletin':
        if pace.fill:
            print(f'    · {pace.fill} fact(s) per story promoted into the body '
                  f'to clear the {Motion.bulletin_floor:.0f}s floor')
        if total < Motion.bulletin_floor:
            print(f'  ⚠ {total:.1f}s is under {Motion.bulletin_floor:.0f}s, so '
                  f'YouTube will treat this as a Short and pull its own frame '
                  f'instead of yt_thumbnail.jpg. This edition does not have '
                  f'the copy for a long-form bulletin — add a story or write '
                  f'fuller decks. It has NOT been padded.')
        elif total > Motion.bulletin_ceiling:
            print(f'  ⚠ {total:.1f}s is over {Motion.bulletin_ceiling:.0f}s. '
                  f'Nothing is truncated, but that is a long watch for a local '
                  f'bulletin — consider fewer stories or tighter decks.')

    _write_cover(scenes, path, H, W)
    raw = _encode_frames(scenes, starts, total, n_frames, fps, W, H,
                         frame_scale, XF)
    audio = _master_audio(total, starts, holds, intro_d, bgm, sfx_dir, voiceover=voiceover)
    out = _mux(raw, audio, path)
    if not keep_frames and os.path.exists(raw):
        os.remove(raw)
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  AUDIO
# ─────────────────────────────────────────────────────────────────────────────

def _sfx_set(sfx_dir: str | None = None) -> dict:
    """The broadcast hits — only ones the licence register allows.

    This used to reach first for sfx/pro_*.wav, which have no licence record
    anywhere and sit beside a deleted folder of numbered third-party files.
    A hit nobody can account for is a Content ID claim nobody can answer, so
    the set is now the house one from brand/sfx.py, registered as `own`, and
    anything not allowed in assets/LICENCES.json is simply not played. D82.
    `sfx_dir` is kept for callers; it no longer widens what may be used.
    """
    from .music import allowed_paths
    ok = {os.path.basename(p): os.path.join(BASE, p)
          for p in allowed_paths('sfx')}

    def pick(name):
        p = ok.get(name)
        return p if p and os.path.exists(p) else None
    return {'impact': pick('open.wav'), 'whoosh': pick('whoosh.wav'),
            'ping': pick('tick.wav'), 'outro': pick('outro.wav')}


def _master_narrated_audio(total: float, plan: list, lead_in: float,
                           bgm: str | None, sfx_dir: str | None, voice) -> str:
    """Score, hits and narration for a reel cut from its own speech.

    Two things here are different from the unmeasured path, and both were
    audible faults rather than refinements:

    DUCKING IS COMPUTED ONCE, NOT STACKED. The old filter chained a
    `volume=0.22` across the whole voiceover and then a `volume=0.45` at every
    scene start — and ffmpeg applies chained volume filters MULTIPLICATIVELY,
    so the music dropped to 0.099 at each cut and jumped back up between them.
    That pumping is what made the score sound like it was breathing against
    the anchor. Here the bed is ducked to one level for the span of each
    spoken beat and released in the gaps, so the music actually lifts between
    sentences the way a broadcast bed does.

    HITS LAND ON THE CUT. Because every cut time is known exactly, the whoosh
    is centred on the wipe rather than fired at a scene index that only
    roughly corresponded to one.
    """
    bgm = bgm or os.path.join(BASE, 'assets', 'news_bgm.mp3')
    sfx_dir = sfx_dir or os.path.join(BASE, 'sfx')
    out = os.path.join(BASE, 'build', '_reel_audio.wav')
    S = _sfx_set(sfx_dir)
    XF = Motion.scene_cross

    if not os.path.exists(bgm):
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi',
                        '-i', 'anullsrc=r=48000:cl=stereo', '-t', str(total),
                        out], check=True)
        return out

    files = [bgm, voice.path]
    for key in ('impact', 'whoosh', 'ping', 'outro'):
        if S[key] and S[key] not in files:
            files.append(S[key])
    idx = {p: i for i, p in enumerate(files)}
    ins = [x for p in files for x in ('-i', p)]

    parts, mixes = [], []

    # ── the bed, ducked per spoken beat ───────────────────────────────────
    # One enable window per beat, each setting the SAME level, so no two
    # windows can multiply. A short pre-roll and release keep the duck from
    # chopping at the edges.
    duck = ''
    for _card, seg in plan:
        a = max(0.0, seg.start - 0.28)
        b = min(total, seg.start + seg.speech + 0.34)
        if b > a:
            duck += f",volume=enable='between(t,{a:.2f},{b:.2f})':volume={Motion.bgm_duck}"

    fade_out = max(0.0, total - 0.85)
    parts.append(f'[{idx[bgm]}:a]aloop=loop=-1:size=2e9,atrim=0:{total:.2f},'
                 f'asetpts=N/SR/TB,'
                 f'afade=t=in:st=0:d=0.6,'
                 f'afade=t=out:st={fade_out:.2f}:d=0.85,'
                 f'volume={Motion.bgm_level}{duck}[bgm]')
    mixes.append('[bgm]')

    # ── the narration ─────────────────────────────────────────────────────
    # Already laid out with its own lead-in and gaps by synthesize_track, so
    # it drops in at t=0 with no delay of its own. A gentle compressor keeps
    # the anchor at a constant level under the bed rather than riding up and
    # down with the TTS engine's own dynamics.
    parts.append(f'[{idx[voice.path]}:a]'
                 f'acompressor=threshold=0.09:ratio=3:attack=12:release=220:makeup=1.6,'
                 f'highpass=f=80,'
                 f'volume={Motion.vo_level}[vo]')
    mixes.append('[vo]')

    def hit(key: str, at: float, gain: float, tag: str):
        p = S.get(key)
        if not p or at < 0 or at >= total:
            return
        ms = int(max(0.0, at) * 1000)
        parts.append(f'[{idx[p]}:a]adelay={ms}|{ms},volume={gain}[{tag}]')
        mixes.append(f'[{tag}]')

    k = 0
    hit('impact', 0.02, 0.92, f'h{k}'); k += 1

    # One whoosh per cut, centred on the wipe. `plan` is card-aligned, so
    # starts[i] is exactly where scene i's wipe begins.
    for i in range(1, len(plan)):
        cut_at = plan[i][1].start - lead_in
        last = (i == len(plan) - 1)
        hit('whoosh', cut_at + XF * 0.5 - 0.16, 0.72, f'h{k}'); k += 1
        if last:
            # The outro ident lands as the wordmark arrives, not at the cut.
            hit('outro', cut_at + XF + 0.12, 0.90, f'h{k}'); k += 1
        else:
            hit('ping', cut_at + XF + 0.10, 0.34, f'h{k}'); k += 1

    parts.append(''.join(mixes) +
                 f'amix=inputs={len(mixes)}:duration=first:normalize=0,'
                 f'atrim=0:{total:.2f},'
                 f'loudnorm=I=-14:TP=-1.5:LRA=9,'
                 f'alimiter=level_in=1:level_out=0.97:limit=0.85:'
                 f'attack=4:release=60:level=disabled[a]')

    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *ins,
                    '-filter_complex', ';'.join(parts), '-map', '[a]',
                    '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', out],
                   check=True)
    return out


def _master_audio(total: float, starts: list[float], holds: list[float],
                  intro_d: float, bgm: str | None, sfx_dir: str | None,
                  voiceover: str | None = None) -> str:
    """Score + hits + optional voiceover, ducked under speech, normalised for platforms."""
    bgm = bgm or os.path.join(BASE, 'assets', 'news_bgm.mp3')
    sfx_dir = sfx_dir or os.path.join(BASE, 'sfx')
    out = os.path.join(BASE, 'build', '_reel_audio.wav')

    sfx_impact = os.path.join(sfx_dir, 'pro_impact.wav')
    if not os.path.exists(sfx_impact):
        sfx_impact = os.path.join(sfx_dir, 'news_impact.wav')

    sfx_whoosh = os.path.join(sfx_dir, 'pro_whoosh.wav')
    if not os.path.exists(sfx_whoosh):
        sfx_whoosh = os.path.join(sfx_dir, 'whoosh.wav')

    sfx_ping = os.path.join(sfx_dir, 'tech_ping.wav')

    sfx_outro = os.path.join(sfx_dir, 'pro_outro_hit.wav')
    if not os.path.exists(sfx_outro):
        sfx_outro = os.path.join(sfx_dir, 'pro_news_ident.wav')
    if not os.path.exists(sfx_outro):
        sfx_outro = sfx_impact

    sfx_candidates = [sfx_impact, sfx_whoosh, sfx_ping, sfx_outro]
    sfx_files = []
    sfx_map = {}
    for s in sfx_candidates:
        if s and os.path.exists(s) and s not in sfx_map:
            sfx_map[s] = 1 + len(sfx_files)
            sfx_files.append(s)

    if not os.path.exists(bgm):
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi',
                        '-i', f'anullsrc=r=48000:cl=stereo', '-t', str(total),
                        out], check=True)
        return out

    ins = ['-i', bgm] + [x for s in sfx_files for x in ('-i', s)]
    has_vo = bool(voiceover and os.path.exists(voiceover))
    vo_idx = -1
    if has_vo:
        ins += ['-i', voiceover]
        vo_idx = (len(ins) // 2) - 1

    parts, mixes = [], []

    vo_delay = 0.25
    vo_dur = 0.0
    if has_vo:
        from .voice import get_audio_duration
        vo_dur = get_audio_duration(voiceover)
    vo_end = vo_delay + vo_dur if has_vo else 0.0

    duck = ''
    if has_vo and vo_end > 0.5:
        duck = f",volume=enable='between(t,0.15,{vo_end:.2f})':volume=0.22"
    for s0 in (starts[1:-1] if len(starts) > 2 else starts[1:]):
        duck += (f",volume=enable='between(t,{max(0, s0 - 0.15):.2f},"
                 f"{s0 + 0.85:.2f})':volume=0.45")

    # BGM: smooth fade in, natural swell after speech finishes, and smooth 0.6s fade out at the end
    bgm_fade_start = max(0.0, total - 0.60)
    parts.append(f'[0:a]atrim=0:{total:.2f},asetpts=N/SR/TB,'
                 f'afade=t=in:st=0:d=0.5,'
                 f'afade=t=out:st={bgm_fade_start:.2f}:d=0.60,'
                 f'volume=0.65{duck}[bgm]')
    mixes.append('[bgm]')

    if has_vo:
        parts.append(f'[{vo_idx}:a]adelay={int(vo_delay * 1000)}|{int(vo_delay * 1000)},volume=1.28[vo]')
        mixes.append('[vo]')

    def hit(s_file: str, at: float, gain: float, tag: str):
        if s_file in sfx_map:
            idx = sfx_map[s_file]
            parts.append(f'[{idx}:a]adelay={int(at * 1000)}|{int(at * 1000)},'
                         f'volume={gain}[{tag}]')
            mixes.append(f'[{tag}]')

    k = 0
    # 1. Opener hit
    hit(sfx_impact, 0.02, 0.95, f'h{k}'); k += 1

    # 2. Story transitions
    story_starts = starts[1:-1] if intro_d > 0.05 else starts[:-1]
    for j, s0 in enumerate(story_starts):
        if intro_d > 0.05 or j > 0:
            hit(sfx_whoosh, max(0, s0 - 0.18), 0.85, f'h{k}'); k += 1
        hit(sfx_ping, s0 + 0.30, 0.50, f'h{k}'); k += 1

    # 3. Outro transition
    if len(starts) > 1:
        outro_start = starts[-1]
        # Whoosh as the gold sweep cross-fade begins
        hit(sfx_whoosh, max(0, outro_start - 0.18), 0.85, f'h{k}'); k += 1
        # Resonant broadcast outro hit as "ಊರ್ಮನಿ ಸುದ್ದಿ" lands
        hit(sfx_outro, outro_start + 0.10, 0.95, f'h{k}'); k += 1

    # -14 LUFS / -1.5 dBTP is what Instagram and YouTube normalise to. Delivering
    # hotter than that just means the platform turns it down, and loud material
    # turned down sounds flat.
    parts.append(''.join(mixes) +
                 f'amix=inputs={len(mixes)}:duration=first:normalize=0,'
                 f'atrim=0:{total:.2f},'
                 f'loudnorm=I=-14:TP=-1.5:LRA=9,'
                 f'alimiter=level_in=1:level_out=0.97:limit=0.85:'
                 f'attack=4:release=60:level=disabled[a]')

    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *ins,
                    '-filter_complex', ';'.join(parts), '-map', '[a]',
                    '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', out],
                   check=True)
    return out


def _mux(video: str, audio: str, path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', video, '-i', audio,
                    '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                    '-shortest', '-movflags', '+faststart', path], check=True)
    return path
