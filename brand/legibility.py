"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Legibility, enforced
====================================
The design system had 4.5 and 3.0 written into `tokens.Limits` and nothing
reading them. This module is what reads them.

Two things are checked, and both are arithmetic rather than taste:

  * **Contrast.** Every colour the house sets type in, against every ground it
    can land on, measured as a WCAG 2.1 ratio. Gold 500 on ink is 10.7:1 and
    excellent; the same gold on paper is about 1.7:1 and unreadable, which is
    why `Role.accent_on_paper` exists — and why nothing should be allowed to
    reach for `Role.accent` on a light ground again by accident.

  * **Effective size.** Everything here is designed at 1080 wide and consumed
    at 400 or less: a carousel cover is about 150px in the grid, a reel's first
    frame about 200px in the feed, a YouTube thumbnail about 210px. A 19px
    provenance line on a 1080 canvas is 2.6px in a carousel grid — it is not
    small, it is absent. Kannada needs more of this margin than Latin does,
    because a conjunct stacks two consonants into the same body height.

Neither of these is a judgement. Both were being made by eye, at 100% zoom, on
a 27-inch screen, which is the one viewing condition no reader of this channel
has ever been in.
"""
from __future__ import annotations

from .tokens import C, Role, T, Limits


# ─────────────────────────────────────────────────────────────────────────────
#  CONTRAST  (WCAG 2.1 relative luminance)
# ─────────────────────────────────────────────────────────────────────────────

def _channel(v: int) -> float:
    c = v / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(colour) -> float:
    """Relative luminance of an RGB or RGBA tuple, 0..1. Alpha is ignored —
    a translucent colour must be composited first; see `over()`."""
    r, g, b = colour[0], colour[1], colour[2]
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def over(fg, bg):
    """Composite an RGBA colour over an opaque ground, returning RGB.

    A hairline at 14% alpha is not a 14%-contrast colour; it is whatever it
    becomes once it is sitting on the page. Checking the raw token would pass
    things the reader never sees.
    """
    if len(fg) < 4:
        return (fg[0], fg[1], fg[2])
    a = fg[3] / 255.0
    return tuple(round(fg[i] * a + bg[i] * (1 - a)) for i in range(3))


def ratio(fg, bg) -> float:
    """WCAG contrast ratio, 1.0 .. 21.0. Order does not matter."""
    f = luminance(over(fg, bg))
    b = luminance(bg)
    hi, lo = max(f, b), min(f, b)
    return (hi + 0.05) / (lo + 0.05)


def passes(fg, bg, large: bool = False) -> bool:
    """4.5:1 for body, 3:1 for display sizes — the WCAG AA split."""
    floor = Limits.gold_on_light_min if large else Limits.contrast_min
    return ratio(fg, bg) >= floor


# ─────────────────────────────────────────────────────────────────────────────
#  THE PAIRS THE HOUSE ACTUALLY SETS
#  Each row is (name, foreground token, ground token, is_display).
#  A pair that is not in this table is a pair no template is allowed to set.
# ─────────────────────────────────────────────────────────────────────────────

PAIRS = [
    # ── type on the ink page ──────────────────────────────────────────────
    ('headline on page',        Role.text_hi,          Role.page,        True),
    ('headline on surface',     Role.text_hi,          Role.surface,     True),
    ('deck on page',            Role.text,             Role.page,        False),
    ('deck on surface',         Role.text,             Role.surface,     False),
    ('body on surface_alt',     Role.text,             Role.surface_alt, False),
    ('meta on page',            Role.text_dim,         Role.page,        False),
    ('meta on surface',         Role.text_dim,         Role.surface,     False),
    # ── the accent ────────────────────────────────────────────────────────
    ('gold on page',            Role.accent,           Role.page,        False),
    ('gold on surface',         Role.accent,           Role.surface,     False),
    ('gold bright on page',     Role.accent_bright,    Role.page,        False),
    # Gold NEVER goes on paper. Bronze does. This is the pair that would have
    # shipped on a light greeting ground without a test.
    ('accent on paper',         Role.accent_on_paper,  C.paper_50,       False),
    ('accent on paper_100',     Role.accent_on_paper,  C.paper_100,      False),
    # ── type on paper (broadsheet, greeting light themes) ─────────────────
    ('ink on paper',            Role.on_paper_hi,      C.paper_50,       False),
    ('ink body on paper',       Role.on_paper,         C.paper_50,       False),
    ('ink dim on paper',        Role.on_paper_dim,     C.paper_50,       False),
    # ── alert ─────────────────────────────────────────────────────────────
    ('alert on page',           Role.alert,            Role.page,        True),
    ('paper on alert',          C.paper_0,             Role.alert,       False),
]

# Pairs that must FAIL — encoded so the rule is a test, not a comment. If
# someone "fixes" gold-on-paper by brightening the gold, this fires.
FORBIDDEN = [
    ('gold on paper', Role.accent, C.paper_50),
    ('gold on paper_100', Role.accent, C.paper_100),
]


def audit_tokens() -> list[str]:
    """Every house colour pair, measured. Returns failures, empty when clean."""
    out: list[str] = []
    for name, fg, bg, large in PAIRS:
        r = ratio(fg, bg)
        floor = Limits.gold_on_light_min if large else Limits.contrast_min
        if r < floor:
            out.append(
                f'{name}: {r:.2f}:1 against a floor of {floor:.1f}:1. '
                f'Either darken the ground, lighten the type, or put the type '
                f'on a scrim — do not ship it and hope.')
    for name, fg, bg in FORBIDDEN:
        r = ratio(fg, bg)
        if r >= Limits.gold_on_light_min:
            out.append(
                f'{name} now measures {r:.2f}:1. This pair is meant to be '
                f'illegible — if the token changed, Role.accent_on_paper and '
                f'this table both need revisiting, deliberately.')
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  EFFECTIVE SIZE  —  what the type measures where it is read
# ─────────────────────────────────────────────────────────────────────────────

# Width, in device pixels, at which each deliverable is actually first seen.
# These are the sizes that decide whether anyone opens it, not the sizes it
# was designed at.
FEED_WIDTH = {
    'post':       420,   # IG feed, single column on a phone
    'square':     150,   # carousel thumbnail in the profile grid
    'story':      420,   # full-screen, but chrome-crowded
    'reel':       200,   # the Reels grid / the first frame in a feed
    'thumb':      210,   # YouTube mobile search row
    'broadsheet': 300,   # a WhatsApp forward before it is tapped
    'forward':    300,
    'yt_post':    380,
    'bulletin':   420,
    'bulletin_4k': 420,
}


def effective_px(size_px: float, format_key: str, canvas_w: int | None = None) -> float:
    """What a `size_px` type size measures on the screen it is read on."""
    from .tokens import fmt
    w = canvas_w if canvas_w else fmt(format_key).w
    seen = FEED_WIDTH.get(format_key, 400)
    return size_px * seen / float(w)


def size_report(format_key: str) -> list[tuple[str, float, float, bool]]:
    """Every step of the type ramp, at the size this format is really seen.

    Returns (name, designed px, effective px, legible).
    """
    rows = []
    for name in ('display', 'h1', 'h2', 'h3', 'h4', 'deck', 'body', 'body_sm',
                 'meta', 'caption', 'eyebrow', 'micro', 'nano'):
        size = getattr(T, name)[0]
        eff = effective_px(size, format_key)
        rows.append((name, float(size), eff, eff >= Limits.min_effective_px))
    return rows


# The step each format's DECISIVE line is set at — the one that has to survive
# first sight, because it is the line that decides whether the post is opened
# at all. Everything below it is read after the tap, which is a different and
# much more forgiving viewing condition.
#
# Not every step needs to clear the floor. A provenance line at 2.6px in a
# profile grid is fine; what would not be fine is the disclosure existing ONLY
# there, which is why Photo.disclosure also goes into the caption.
PRIMARY_STEP = {
    'post':       'h1',
    'square':     'h3',      # carousel slides carry a smaller head
    'story':      'h1',
    'reel':       'display', # the reel_line, set big
    'thumb':      'display', # the hook
    'broadsheet': 'h2',
    'forward':    'h1',
    'yt_post':    'h2',
    'bulletin':   'h1',
    'bulletin_4k': 'h1',
}


def audit_sizes(format_key: str, used: tuple[str, ...] = ()) -> list[str]:
    """Check the line that has to survive first sight.

    `used` overrides which ramp steps are judged. The default is the format's
    decisive step alone: this is a legibility gate on the line that sells the
    post, not a complaint that small print is small.
    """
    steps = used or (PRIMARY_STEP.get(format_key, 'h1'),)
    out: list[str] = []
    for name, designed, eff, ok in size_report(format_key):
        if name not in steps:
            continue
        if not ok:
            out.append(
                f'{format_key}: the {name} step is {designed:.0f}px on the '
                f'canvas but {eff:.1f}px where this format is first seen '
                f'({FEED_WIDTH.get(format_key, 400)}px wide) — below the '
                f'{Limits.min_effective_px:.0f}px floor at which a Kannada '
                f'conjunct still separates. Nobody reads this line before '
                f'deciding whether to open the post.')
    return out


# Ramp steps that carry MEANING rather than decoration, and the format each
# is really read on. These must clear the floor at the width the post is
# opened at — not at the width it is glanced at in a grid, which is a
# different and much harsher test that only the headline has to pass.
#
# nano is on this list because it carries the photo credit line, and the photo
# credit line is the IT Rules synthetic-content disclosure. A disclosure below
# the legibility floor is not a disclosure.
MEANINGFUL_STEPS = ('body', 'body_sm', 'meta', 'caption', 'micro', 'nano')
READ_AT = 'post'          # an opened 4:5 post on a phone


def audit_small_print() -> list[str]:
    """Every step that carries meaning, at the width it is actually read."""
    out: list[str] = []
    for name in MEANINGFUL_STEPS:
        size = float(getattr(T, name)[0])
        eff = effective_px(size, READ_AT)
        if eff < Limits.min_effective_px:
            out.append(
                f'type step {name} is {size:.0f}px on the canvas and '
                f'{eff:.2f}px on an opened post, below the '
                f'{Limits.min_effective_px:.0f}px floor. This step carries '
                f'copy somebody has to read — for nano that includes the photo '
                f'credit, which is the synthetic-content disclosure.')
    return out


def first_sight(format_key: str) -> tuple[str, float, float]:
    """(step, designed px, effective px) for the line that sells the post."""
    step = PRIMARY_STEP.get(format_key, 'h1')
    designed = float(getattr(T, step)[0])
    return step, designed, effective_px(designed, format_key)
