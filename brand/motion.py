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
from PIL import Image

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
    return BULLETIN if format_key == 'bulletin' else REEL


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
        dx = (pw - cw) * (0.5 + self.drift * self.dir * (e - 0.5))
        dy = (ph - ch) * 0.5
        box = (dx, dy, dx + cw, dy + ch)
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
                 pace: Pace = REEL):
        self.st, self.W, self.H, self.ss, self.dur = story, W, H, ss, dur
        self.i, self.n, self.safe = index, total, safe
        self.pace = pace
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
        sf = Surface(W, H, ss, bg=(0, 0, 0, 0))
        scrim(sf, 0, st_ + 30, C.ink_950, 0.88 if self.kb else 0.62, 0.0, curve=1.5)
        if H > W:
            if self.kb is not None:
                scrim(sf, H * 0.30, H * 0.86, C.ink_950, 0.0, 0.94, curve=1.6)
                scrim(sf, H * 0.86, H, C.ink_950, 0.94, 0.99, curve=1.0)
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
            vrule(sf, pw - 2, 0, H, alpha(C.paper_50, 0.16), 1.0)
            vrule(sf, pw, 0, H, C.gold_500, 3.0)

        if H > W:
            cp.masthead(sf, sl, st_ - 118, W - sl * 2, right_top=self.st.date_kn,
                        right_bot=self.st.time_kn, on_photo=self.kb is not None,
                        scale=0.92)
        else:
            # Everything that is furniture — lockup, date, time — lives in
            # the column. It used to be set over the photograph on the right,
            # where it landed on a hospital signboard and became unreadable
            # while also obscuring the picture it was sitting on. The column
            # is a solid ground, so none of it needs a shadow to survive.
            pw = self.panel_w
            by = st_ - 6
            right = pw - Motion.panel_pad
            cp.masthead(sf, sl, by, int(right - sl), on_photo=False,
                        scale=0.72, rule_below=False)
            fd = typo.font_for(self.st.date_kn, 'kn_var', sf.s(27), weight=650)
            ft = typo.font_for(self.st.time_kn, 'kn_var', sf.s(22), weight=440)
            typo.draw_text(sf.img, self.st.date_kn, sf.s(right), sf.s(by + 32),
                           fd, Role.text_hi, anchor_x='r')
            rule(sf, right - 168, by + 52, right, alpha(C.gold_500, 0.45), 1.0)
            typo.draw_text(sf.img, self.st.time_kn, sf.s(right), sf.s(by + 88),
                           ft, Role.text_dim, anchor_x='r')
            # Only the handle sits on the picture now, so the foot veil can
            # be shallow — enough to carry gold type over a bright desk
            # without taking another slice out of the photograph.
            scrim(sf, H * 0.90, H, C.ink_950, 0.0, 0.80, curve=1.8)
        if H > W:
            # Portrait only: the band the platform covers still carries the
            # brand, because it is visible on a paused reel and on every repost.
            band = H - sb
            rule(sf, sl, band + 54, W - sl, Role.hairline_soft, 1.0)
            typo.draw_text(sf.img, Brand.handle, sf.s(W / 2), sf.s(band + 122),
                           typo.font('latin', sf.s(40), weight=760), C.gold_500,
                           anchor_x='c', tracking=0.015)
            typo.draw_text(sf.img, Brand.tagline, sf.s(W / 2), sf.s(band + 168),
                           typo.font('kn_var', sf.s(26), weight=520),
                           Role.text_dim, anchor_x='c')
        else:
            typo.draw_text(sf.img, Brand.handle, sf.s(W - sl), sf.s(H - sb + 34),
                           typo.font('latin', sf.s(26), weight=740), C.gold_500,
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
        # Portrait keeps clear of Instagram's right action rail. Landscape has
        # no chrome, but a headline set the full 1920 wide is unreadable, so it
        # is measured to a column instead.
        cw = (int(self.panel_w - sl - Motion.panel_pad) if landscape
              else (W - sl - sr))
        # The type scale is calibrated for a 1080-WIDE portrait frame. Most
        # YouTube viewing is on a phone, where a 1920x1080 video plays about
        # 400px wide — so a 19px source line lands at roughly 4px and is simply
        # gone. Everything small gets scaled up in landscape.
        ts = 1.38 if landscape else 1.0

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

        cap_h = int(T.micro[0] * ts * 1.5) + 6 if st.credit_line else 0
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
        region_top = (st_ + 120) if landscape else (st_ + 220)
        # The photo credit belongs on the PHOTO, above the panel, which is also
        # where it reads correctly as a caption.
        # cap_h is reserved in BOTH orientations now. It used to be excluded
        # in landscape because the credit sat on the photograph; now that it
        # is in the column, a four-line deck ran straight over it.
        head_room = (block_bottom - region_top - eb_h - 34 * ts - cap_h
                     - ((d_blk.height / ss + 34 * ts) if d_blk is not None else 0))
        # A narrower column needs a slightly smaller headline and more lines
        # to work with; it has the whole frame height to spend them in.
        hi = 76 if landscape else 96
        hb = typo.fit(head_txt, 'kn', ss * hi, ss * T.h4[0], ss * cw,
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
            landscape=landscape, cw=cw, ts=ts, bottom=bottom, src_y=src_y,
            block_bottom=block_bottom, head_txt=head_txt, sup_txt=sup_txt,
            d_blk=d_blk, cap_h=cap_h, eb_h=eb_h,
            region_top=region_top, hb=hb, block_h=block_h, y=y)

    def _sprites(self) -> list[Sprite]:
        m = self._m
        W, H, ss = self.W, self.H, self.ss
        sl, st_, sr, sb = self.safe
        st = self.st
        landscape, cw, ts = m.landscape, m.cw, m.ts
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
            cap_y = (min(y + block_h + 20,
                         src_y - 36 * ts - cap_h - 12) if landscape
                     else (y - cap_h - 22))

            def cap(sf, _w=cap_w):
                b = typo.layout(st.credit_line,
                                typo.font('kn_var', sf.s(T.micro[0] * ts),
                                          weight=420),
                                sf.s(_w), 1.34)
                # It sits on the solid column in landscape and on the scrim
                # in portrait, so it needs no shadow of its own either way.
                sh = None
                typo.draw_block(sf.img, b, 0, 0, alpha(C.paper_300, 0.94),
                                shadow=sh, box_w=sf.s(_w))
            out.append(Sprite(_sprite_from(cap, cap_w, cap_h, ss, 0, 0).img,
                              int(cap_x), int(cap_y),
                              t_in=0.34, dur=0.5, rise=12))

        def eb(sf):
            cp.eyebrow(sf, 0, 0, cw, st, scale=ts,
                       on_photo=self.kb is not None)
        out.append(Sprite(_sprite_from(eb, cw, eb_h + 6, ss, 0, 0).img, sl, int(y),
                          t_in=0.08, dur=0.5, rise=14, wipe=True))
        y += eb_h + 34 * ts

        lh = hb.lh / ss
        for k, line in enumerate(hb.lines):
            def one(sf, _l=line, _b=hb):
                typo.draw_text(sf.img, _l, 0, sf.s(_b.first_rise / ss),
                               typo.font('kn', _b.f.size), Role.text_hi,
                               shadow=(0, sf.s(3), sf.s(16), (0, 0, 0, 190)))
            out.append(Sprite(
                _sprite_from(one, cw, int(lh + hb.first_rise / ss) + 14, ss, 0, 0).img,
                sl, int(y + k * lh),
                t_in=0.28 + k * Motion.text_stagger, dur=Motion.text_in, rise=34))
        y += hb.height / ss + 34 * ts

        if d_blk is not None:
            def dk(sf, _b=d_blk):
                typo.draw_block(sf.img, _b, 0, 0, C.paper_200, box_w=sf.s(cw),
                                shadow=(0, sf.s(2), sf.s(12), (0, 0, 0, 170)))
            out.append(Sprite(
                _sprite_from(dk, cw, int(d_blk.height / ss) + 12, ss, 0, 0).img,
                sl, int(y), t_in=0.30 + len(hb.lines) * Motion.text_stagger + 0.14,
                dur=Motion.text_in, rise=24))

        # Meta row. It closes the COLUMN now, not the whole frame, with a
        # hairline above it so the type block ends on a defined edge.
        meta_w = cw

        pad = 36 * ts if landscape else 0

        def src(sf):
            if landscape:
                rule(sf, 0, 0, meta_w, alpha(C.paper_50, 0.13), 1.0)
            cp.sourceline(sf, 0, pad, meta_w, st, scale=ts)
        out.append(Sprite(
            _sprite_from(src, meta_w, int(T.micro[0] * ts * 1.9 + pad),
                         ss, 0, 0).img,
            sl, int(src_y - pad), t_in=0.95, dur=0.5, rise=10))
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
    def __init__(self, edition: Edition, W: int, H: int, ss: int, dur: float, safe):
        self.W, self.H, self.ss, self.dur, self.safe = W, H, ss, dur, safe
        self.ed = edition
        self.bed = self._bed()
        self.sprites = self._sprites()

    def _bed(self):
        sf = Surface(self.W, self.H, self.ss)
        cp.page_base(sf, 0.8)
        cp.horizon(sf, self.H * 0.74, 1.0)
        radial_glow(sf, self.W * 0.5, self.H * 0.76, self.W * 0.8, C.gold_600, 0.14)
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
            typo.draw_text(sf.img, Brand.coverage,
                           sf.s(cw / 2), sf.s(34),
                           typo.font('kn_var', sf.s(28), weight=480),
                           Role.text_dim, anchor_x='c')
        out.append(Sprite(_sprite_from(where, cw, 60, ss, 0, 0).img, sl, y + 366,
                          t_in=0.70, dur=0.5, rise=14))
        return out

    def frame(self, t: float) -> Image.Image:
        f = self.bed.copy()
        p = phase(t, 0.0, 0.8, Ease.out_back)
        size = int(230 * (0.80 + 0.20 * p))
        lg = Image.open(os.path.join(BASE, 'assets', 'logo_clean_circle.png')) \
            .convert('RGBA').resize((size, size), Image.Resampling.LANCZOS)
        if p < 1:
            lg.putalpha(lg.getchannel('A').point(lambda v: int(v * clamp01(p * 1.5))))
        f.alpha_composite(lg, ((self.W - size) // 2, int(self.H * 0.30) - size // 2))
        for s in self.sprites:
            s.draw(f, t)
        return f


# ─────────────────────────────────────────────────────────────────────────────
#  TIMELINE & RENDER
# ─────────────────────────────────────────────────────────────────────────────

def _sweep(frame: Image.Image, p: float, W: int, H: int) -> Image.Image:
    """A gold light-sweep wipe. Used only between scenes, and only for a few
    frames — a transition you notice is a transition that is too long."""
    e = Ease.in_out_cubic(clamp01(p))
    x = int((-0.35 + 1.7 * e) * W)
    band = int(W * 0.30)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    a = np.zeros((1, W, 4), np.float32)
    xs = np.arange(W)
    d = np.clip(1.0 - np.abs(xs - x) / band, 0, 1) ** 2
    a[0, :, 0], a[0, :, 1], a[0, :, 2] = C.gold_400
    a[0, :, 3] = d * 190
    lay = Image.fromarray(np.repeat(a, H, 0).astype('uint8'), 'RGBA')
    out = frame.copy()
    out.alpha_composite(lay)
    return out


def _progress_bar(frame: Image.Image, p: float, W: int, y: int = 0):
    """A thin gold rule that fills across the video, flush to the top edge.

    It used to sit at y=58, which is clear of the masthead in a 9:16 frame and
    runs straight through the logo in a 16:9 one, because landscape has no
    platform chrome to clear and so places the masthead much higher. Flush to
    the edge is both safe at every aspect and how broadcast does it.
    """
    h = 4
    d = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    d.paste((*C.paper_50, 34), (0, 0, W, h))
    d.paste((*C.gold_500, 255), (0, 0, max(1, int(W * clamp01(p))), h))
    frame.alpha_composite(d, (0, y))


def render_reel(edition: Edition, path: str, format_key: str = 'reel',
                target_seconds: float | None = 30.0, ss: int = 2,
                fps: int = Motion.fps, bgm: str | None = None,
                sfx_dir: str | None = None, keep_frames: bool = False) -> str:
    """Render the day's edition as video and master the audio.

    Drives both the 9:16 reel and the 16:9 bulletin: same engine, different
    `Pace`. See DECISIONS.md D37 for why the bulletin carries the deck.
    """
    edition.validate()
    F = fmt(format_key)
    W, H, safe = F.w, F.h, F.safe

    pace = pace_for(format_key)
    if pace.name == 'bulletin':
        pace, intro_d, holds, outro_d, used, _t = plan_bulletin(
            edition, target=target_seconds)
    else:
        intro_d, holds, outro_d, used = plan_durations(
            edition, target=target_seconds, pace=pace)
    stories = edition.stories[:used]
    XF = Motion.scene_cross

    if used < len(edition.stories):
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
    for st, shown in zip(stories, holds):
        need = scene_need(st, pace)
        if need > shown + 0.05:
            print(f'  ⚠ "{reel_line(st)[:38]}…" needs {need:.1f}s to read but '
                  f'the scene caps at {shown:.1f}s — {need - shown:.1f}s short. '
                  f'Shorten reel_line or reel_support.')

    print(f'  building scenes … intro {intro_d:.1f}s + '
          f'{" + ".join(f"{h:.1f}" for h in holds)}s + outro {outro_d:.1f}s')

    scenes: list[Scene] = [BrandSting(edition, W, H, ss, intro_d)]
    for i, (st, d) in enumerate(zip(stories, holds)):
        scenes.append(StoryScene(st, W, H, ss, d, i, len(stories), safe,
                                 direction=1 if i % 2 == 0 else -1, pace=pace))
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
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
        '-maxrate', '12M', '-bufsize', '24M',
        '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '4.2',
        '-x264-params', 'ref=4:bframes=3',
        '-movflags', '+faststart', raw], stdin=subprocess.PIPE)

    for k in range(n_frames):
        t = k / fps
        # which scene(s) are live
        cur = 0
        for i, s0 in enumerate(starts):
            if t >= s0:
                cur = i
        sc = scenes[cur]
        lt = t - starts[cur]
        f = sc.frame(min(lt, sc.dur))

        nxt = cur + 1
        if nxt < len(scenes) and t >= starts[nxt]:
            p = clamp01((t - starts[nxt]) / XF)
            g = scenes[nxt].frame(t - starts[nxt])
            f = Image.blend(f, g, Ease.in_out_cubic(p))
            if 0.12 < p < 0.88:
                f = _sweep(f, (p - 0.12) / 0.76, W, H)

        _progress_bar(f, t / total, W)
        enc.stdin.write(f.convert('RGB').tobytes())
        if k % 60 == 0 or k == n_frames - 1:
            print(f'    frame {k + 1}/{n_frames}  ({t:5.1f}s)', end='\r')
    enc.stdin.close()
    enc.wait()
    print(f'\n  ✓ picture locked')

    audio = _master_audio(total, starts, holds, intro_d, bgm, sfx_dir)
    out = _mux(raw, audio, path)
    if not keep_frames and os.path.exists(raw):
        os.remove(raw)
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  AUDIO
# ─────────────────────────────────────────────────────────────────────────────

def _master_audio(total: float, starts: list[float], holds: list[float],
                  intro_d: float, bgm: str | None, sfx_dir: str | None) -> str:
    """Score + hits, ducked under each headline, normalised for the platforms."""
    bgm = bgm or os.path.join(BASE, 'assets', 'news_bgm.mp3')
    sfx_dir = sfx_dir or os.path.join(BASE, 'sfx')
    out = os.path.join(BASE, 'build', '_reel_audio.wav')

    hits = [os.path.join(sfx_dir, n) for n in
            ('news_impact.wav', 'whoosh.wav', 'tech_ping.wav')]
    hits = [h for h in hits if os.path.exists(h)]
    if not os.path.exists(bgm):
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi',
                        '-i', f'anullsrc=r=48000:cl=stereo', '-t', str(total),
                        out], check=True)
        return out

    ins = ['-i', bgm] + [x for h in hits for x in ('-i', h)]
    parts, mixes = [], []

    # Score: trimmed, faded, and pulled down a little under every scene change
    # so the hit and the headline have room to land.
    duck = ''
    for s0 in starts[1:]:
        duck += (f",volume=enable='between(t,{max(0, s0 - 0.15):.2f},"
                 f"{s0 + 0.85:.2f})':volume=0.42")
    parts.append(f'[0:a]atrim=0:{total:.2f},asetpts=N/SR/TB,'
                 f'afade=t=in:st=0:d=0.6,'
                 f'afade=t=out:st={max(0, total - 1.8):.2f}:d=1.8,'
                 f'volume=0.62{duck}[bgm]')
    mixes.append('[bgm]')

    def hit(idx: int, at: float, gain: float, tag: str):
        parts.append(f'[{idx}:a]adelay={int(at * 1000)}|{int(at * 1000)},'
                     f'volume={gain}[{tag}]')
        mixes.append(f'[{tag}]')

    k = 0
    if hits:
        hit(1, 0.02, 1.0, f'h{k}'); k += 1          # opener
    for j, s0 in enumerate(starts[1:-1]):
        if len(hits) >= 2:
            hit(2, max(0, s0 - 0.18), 0.9, f'h{k}'); k += 1     # whoosh into scene
        if len(hits) >= 3:
            hit(3, s0 + 0.30, 0.55, f'h{k}'); k += 1            # ping on headline
    if hits:
        hit(1, max(0, starts[-1] - 0.10), 0.85, f'h{k}'); k += 1

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
