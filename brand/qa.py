"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Preflight & output QA
=====================================
A standard nobody can check is a wish. These are the checks.

`preflight(story, format)` runs before rendering and catches the things that
make a card look amateur no matter how good the template is — a headline too
long to set large, mixed numeral systems, a thumbnail nobody can read at feed
size, a "BREAKING" flag on yesterday's news.

`inspect(path, format)` runs on the rendered file and catches delivery
problems — wrong dimensions, crushed blacks, blown highlights, a file too
large for the platform.

Neither raises. They report, because a sub-editor should be able to overrule a
guideline; what they must not be able to do is overrule it by accident.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import numpy as np
from PIL import Image

from .tokens import fmt, T, Brand
from .content import Story, BREAKING_WINDOW_H

KN_DIGITS = re.compile(r'[೦-೯]')
LAT_DIGITS = re.compile(r'[0-9]')

# Longest headline that can still be set at a commanding size, per format.
HEADLINE_BUDGET = {
    'post': 78, 'square': 70, 'story': 78, 'reel': 62,
    'thumb': 34, 'broadsheet': 74, 'forward': 78, 'yt_post': 70,
}

# Platform upload ceilings we care about, in MB.
SIZE_CEILING = {'post': 8.0, 'square': 8.0, 'story': 8.0, 'reel': 8.0,
                'thumb': 2.0, 'broadsheet': 8.0, 'forward': 5.0, 'yt_post': 8.0}


@dataclass
class Report:
    ok: list[str] = field(default_factory=list)
    warn: list[str] = field(default_factory=list)
    fail: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.fail

    def show(self, title: str = '') -> 'Report':
        if title:
            print(f'\n  {title}')
        for m in self.fail:
            print(f'    ✗ {m}')
        for m in self.warn:
            print(f'    ! {m}')
        if not self.fail and not self.warn:
            print('    ✓ clean')
        return self


def compliance() -> Report:
    """Channel-level obligations, checked once per run rather than per story."""
    r = Report()
    # What matters to a reader with a complaint is that SOME route is
    # published and answered. The channel publishes its Instagram DM and the
    # WhatsApp number in its bio, which is what its one person actually
    # reads; naming an officer who does not exist would look more compliant
    # and serve the reader less. So this warns when there is no route at all,
    # not when there is no name. See tokens.Brand.grievance_line.
    if not Brand.grievance_line():
        r.warn.append(
            'no contact route published. IT Rules 2021 Part III requires a '
            'news publisher to publish contact details, acknowledge a '
            'complaint within 24h and dispose of it in 15 days. With '
            'Brand.handle blank, no card or caption carries any route at all.')
    return r


def preflight(story: Story, format_key: str = 'post', hook: str = '') -> Report:
    r = Report()
    budget = HEADLINE_BUDGET.get(format_key, 78)

    # A thumbnail is judged on the line it will actually carry.
    display = hook or story.headline
    n = len(display)
    if n > budget * 1.45:
        r.fail.append(f'headline is {n} characters; {format_key} can only set '
                      f'about {budget} at a commanding size. Cut it or move the '
                      f'detail into the deck.')
    elif n > budget:
        r.warn.append(f'headline is {n} characters against a budget of {budget} '
                      f'for {format_key}; it will be set smaller than ideal.')

    if format_key == 'thumb' and len(display.split()) > 7:
        r.warn.append('a thumbnail is read at about 210px wide — pass a short '
                      'hook= rather than the full headline.')

    # Mixed numeral systems inside one card look like a mistake, because they are.
    joined = ' '.join([story.headline, story.deck, *story.points,
                       story.takeaway or ''])
    if KN_DIGITS.search(joined) and LAT_DIGITS.search(joined):
        r.fail.append('this card mixes Kannada numerals (೧೨೩) with Latin ones '
                      '(123). Pick one; the house style is Latin, which is what '
                      'Kannada broadcast and print use for figures.')

    if story.deck and len(story.deck) > 190:
        r.warn.append(f'deck is {len(story.deck)} characters; a standfirst that '
                      'runs past ~180 stops being a standfirst.')

    for i, p in enumerate(story.points):
        if len(p) > 150:
            r.warn.append(f'fact {i + 1} is {len(p)} characters — it will set '
                          'small. Split it or shorten it.')

    if len(story.points) > 4:
        r.warn.append(f'{len(story.points)} facts; a 4:5 card carries three '
                      'comfortably and the template will drop the rest.')

    if story.category == 'breaking' and not story.is_breaking:
        r.warn.append(f'story is older than {BREAKING_WINDOW_H}h, so the '
                      'breaking treatment has been dropped automatically.')

    if story.photo and story.photo.licence == 'fair-dealing':
        r.warn.append(
            'photo licence is fair-dealing — defensible for reporting current '
            'events, but keep a note of why. It is a defence, not a permission.')

    if story.category == 'crime' and not (story.involves_minor
                                          or story.sexual_offence):
        r.warn.append(
            'crime story: confirm nobody involved is a minor and no sexual '
            'offence is alleged. If either is true, set involves_minor / '
            'sexual_offence — the identity guards only run when you do.')

    if story.photo and story.photo.nature == 'ai':
        r.warn.append('AI-generated imagery will be labelled "ಎಐ ರಚಿತ ಚಿತ್ರ" on '
                      'the card. Prefer a real photograph, or no photograph.')

    if not story.reel_line and len(story.headline) > 46:
        r.warn.append(
            f'headline is {len(story.headline)} chars and there is no reel_line. '
            f'In a reel that needs about {len(story.headline) / 7.0:.0f}s on '
            f'screen to be readable. Add a reel_line of ~45 characters.')

    if story.status == 'unconfirmed':
        r.warn.append('status is unconfirmed — the card will say so in Kannada. '
                      'That is correct; just make sure you meant it.')

    if not story.location:
        r.warn.append('no location: coastal readers scan for the place name '
                      'first, and the eyebrow will look unbalanced without it.')

    if story.photo and story.photo.nature in ('actual', 'handout') \
            and not story.photo.caption:
        r.warn.append('a photograph of the actual scene should say what it shows.')

    return r


def inspect(path: str, format_key: str = 'post') -> Report:
    r = Report()
    F = fmt(format_key)
    if not os.path.exists(path):
        r.fail.append(f'{path} was not written')
        return r

    im = Image.open(path)
    if im.size != (F.w, F.h):
        r.fail.append(f'{os.path.basename(path)} is {im.width}x{im.height}, '
                      f'expected {F.w}x{F.h}')

    mb = os.path.getsize(path) / 1e6
    ceil_ = SIZE_CEILING.get(format_key, 8.0)
    if mb > ceil_:
        r.warn.append(f'{mb:.1f} MB exceeds the {ceil_:.0f} MB target for '
                      f'{format_key}; it will be recompressed on upload.')

    a = np.asarray(im.convert('RGB')).astype(np.float32)
    lum = (a * np.array([0.2126, 0.7152, 0.0722])).sum(2)

    crushed = float((lum < 2).mean())
    if crushed > 0.55:
        r.warn.append(f'{crushed * 100:.0f}% of the frame is at absolute black. '
                      'Flat black bands look like a rendering failure on OLED '
                      'phones — check the page base is drawing.')
    blown = float((lum > 253).mean())
    if blown > 0.06:
        r.warn.append(f'{blown * 100:.0f}% of the frame is clipped white.')

    # A card with nothing bright on it has no focal point.
    if float(lum.max()) < 150:
        r.warn.append('nothing on this card is brighter than mid-grey; it will '
                      'disappear in a bright feed.')

    return r


def audit(pairs: list[tuple[str, str]]) -> bool:
    """Run inspect() over (path, format) pairs. Returns True when all clean."""
    allok = True
    for path, key in pairs:
        rep = inspect(path, key)
        if rep.fail or rep.warn:
            rep.show(os.path.basename(path))
        allok = allok and rep.clean
    return allok
