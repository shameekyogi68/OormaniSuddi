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

from .tokens import fmt, T, Brand, Limits
from .content import Story, BREAKING_WINDOW_H

KN_DIGITS = re.compile(r'[೦-೯]')
LAT_DIGITS = re.compile(r'[0-9]')

# Longest headline that can still be set at a commanding size, per format.
HEADLINE_BUDGET = {
    'post': Limits.headline_chars, 'square': 70, 'story': Limits.headline_chars,
    'reel': 62, 'thumb': 34, 'broadsheet': 74, 'forward': Limits.headline_chars,
    'yt_post': 70,
}

# Platform upload ceilings we care about, in MB.
SIZE_CEILING = {'post': 8.0, 'square': 8.0, 'story': 8.0, 'reel': 8.0,
                'thumb': 2.0, 'broadsheet': 8.0, 'forward': 5.0, 'yt_post': 8.0}
# WhatsApp is the growth route — warn long before the upload ceiling. A 5 MB
# broadsheet is a file that does not get forwarded on rural data, which makes
# an 8 MB ceiling the wrong number for the format that is supposed to grow the
# channel. Both numbers come off Limits.forward_target_kb.
SIZE_WARN = {'broadsheet': Limits.forward_target_kb / 1000.0 * 1.6,
             'forward': Limits.forward_target_kb / 1000.0}


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
    # Legibility is a channel-level property of the token system, not of one
    # story, so it is measured once. Limits.contrast_min had been sitting in
    # tokens.py with nothing reading it; this is what reads it.
    from . import legibility
    for msg in legibility.audit_tokens():
        r.fail.append(f'contrast: {msg}')
    if not Brand.grievance_named():
        r.fail.append(
            'IT Rules 2021 Part III requires a named Grievance Officer and a '
            'watched contact. Fill Brand.grievance_officer and '
            'Brand.grievance_phone or Brand.grievance_email in brand/tokens.py '
            'before publishing. The Instagram-DM fallback on cards is not '
            'compliance.')
    elif not Brand.grievance_line():
        r.fail.append(
            'no contact route published. With Brand.handle blank, no card or '
            'caption carries any route at all.')
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

    if story.deck and len(story.deck) > Limits.deck_chars:
        r.warn.append(f'deck is {len(story.deck)} characters against the '
                      f'{Limits.deck_chars}-character budget in tokens.Limits; '
                      'a standfirst that runs past it stops being a standfirst.')

    for i, p in enumerate(story.points):
        if len(p) > Limits.point_chars:
            r.warn.append(f'fact {i + 1} is {len(p)} characters against the '
                          f'{Limits.point_chars}-character budget — it will set '
                          'small. Split it or shorten it.')

    if len(story.points) > Limits.points_max + 1:
        r.warn.append(f'{len(story.points)} facts; a 4:5 card carries '
                      f'{Limits.points_max} comfortably and the template will '
                      'drop the rest.')

    # The line that decides whether the post is opened at all, measured at the
    # size it is actually first seen — not at 100% on a desktop screen.
    from . import legibility
    for msg in legibility.audit_sizes(format_key):
        r.warn.append(msg)

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

    # Every image that can reach the screen — hero AND gallery — is checked,
    # not just the hero. A reel's fact cards are drawn from the gallery, and
    # for a long time those were the frames with no label on them at all.
    synthetic = [p for p in story.all_photos if p.is_synthetic]
    if synthetic:
        r.warn.append(
            f'{len(synthetic)} of {len(story.all_photos)} image(s) are '
            f'generated, not photographed. Each will carry "ಎಐ ರಚಿತ ಚಿತ್ರ" on '
            f'every card that shows it, and the caption repeats it. Prefer a '
            f'real photograph, or no photograph.')
    undisclosed = [p for p in story.all_photos if not p.disclosure.strip()]
    if undisclosed:
        r.fail.append(
            f'{len(undisclosed)} image(s) would appear on screen with no '
            f'disclosure line: {", ".join(os.path.basename(p.path) for p in undisclosed)}. '
            f'Every image carries its provenance on the card that shows it — '
            f'give it a credit, and a nature other than "actual".')

    # A fact card is glanced at while the anchor is already delivering the
    # same fact at roughly twice reading speed, so a print-length point on a
    # reel frame is copy the viewer cannot finish. reel_points is the fix.
    long_facts = [i for i, p in enumerate(story.points)
                  if len(p) > 80 and not (i < len(story.reel_points)
                                          and story.reel_points[i].strip())]
    if long_facts:
        r.warn.append(
            f'fact(s) {", ".join(str(i + 1) for i in long_facts)} run past 80 '
            f'characters with no reel_points short form. On a narrated reel '
            f'card that is more copy than the viewer can read before the voice '
            f'has moved on — write a ~60-character reel_points entry for each. '
            f'The voice still carries the full point.')

    if not story.reel_line and len(story.headline) > Limits.reel_line_chars:
        r.warn.append(
            f'headline is {len(story.headline)} chars and there is no reel_line. '
            f'In a reel that needs about {len(story.headline) / 7.0:.0f}s on '
            f'screen to be readable. Add a reel_line of ~'
            f'{Limits.reel_line_chars} characters.')

    # Every string that will be SET, checked against the faces that will set
    # it. A codepoint no face carries renders as .notdef — the empty box — and
    # nothing anywhere else raises, so this is the only place it can be caught
    # before a viewer sees it. typo.safe() already substitutes or drops
    # decoration; what is reported here is copy that would lose meaning.
    from . import typo
    copy_faces = [('kn', story.headline), ('kn', story.reel_line),
                  ('kn_var', story.deck), ('kn_var', story.takeaway or ''),
                  ('kn_var', story.reel_support),
                  ('kn_var', story.credit_line if story.photo else '')]
    copy_faces += [('kn_var', p) for p in story.points]
    seen: set[str] = set()
    for fam, txt in copy_faces:
        if not txt:
            continue
        gone = typo.missing_glyphs(txt, typo.font_for(txt, fam, 40))
        seen.update(gone)
    if seen:
        r.fail.append(
            'these characters have no glyph in the house faces and would be '
            f'set as empty boxes: {" ".join(sorted(seen))}. Replace them in '
            'the copy — the renderer will not invent a substitute for a '
            'letter, because dropping one changes what the sentence says.')

    if story.status == 'unconfirmed':
        r.warn.append('status is unconfirmed — the card will say so in Kannada. '
                      'That is correct; just make sure you meant it.')

    if not story.location:
        r.warn.append('no location: coastal readers scan for the place name '
                      'first, and the eyebrow will look unbalanced without it.')

    if story.photo and story.photo.nature in ('actual', 'handout') \
            and not story.photo.caption:
        r.warn.append('a photograph of the actual scene should say what it shows.')

    # ─────────────────────────────────────────────────────────────────────────
    # YouTube Monetization (AdSense Green Dollar) & Legal Safeguards
    # ─────────────────────────────────────────────────────────────────────────
    DEMONETIZATION_TRIGGERS = [
        'ರಕ್ತಸಿಕ್ತ', 'ಘೋರ ರಕ್ತಪಾತ', 'ರುಂಡಚೆಂಡಾಡಿದ', 'ತುಂಡು ತುಂಡಾಗಿ ಕತ್ತರಿಸಿದ',
        'ಬರ್ಬರ ಹತ್ಯೆ', 'ಕ್ರೂರವಾಗಿ ಕೊಚ್ಚಿ', 'ಹೆಣಗಳ ರಾಶಿ',
    ]
    for trig in DEMONETIZATION_TRIGGERS:
        if trig in joined:
            r.warn.append(
                f'YouTube Monetization Guard: "{trig}" detected in story copy. '
                'Sensationalized/graphic violence terms can trigger YouTube Yellow Dollar '
                '(limited ads). Use sober journalistic language.')

    MINOR_TERMS = ['ಬಾಲಕ', 'ಬಾಲಕಿ', 'ಅಪ್ರಾಪ್ತ', 'ಶಾಲಾ ವಿದ್ಯಾರ್ಥಿ', 'ಮಗು']
    if story.category == 'crime' and any(term in joined for term in MINOR_TERMS) and not story.involves_minor:
        r.warn.append(
            'Legal Guard (POCSO / JJ Act): Story mentions minors/children in a crime context '
            'but involves_minor is not set to true. Set involves_minor: true to protect legal compliance.')

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
    warn_mb = SIZE_WARN.get(format_key)
    if warn_mb and mb > warn_mb:
        r.warn.append(
            f'{mb:.2f} MB is heavy for a WhatsApp forward of {format_key}; '
            f'target under {int(warn_mb * 1000)} KB so it actually gets sent.')

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
