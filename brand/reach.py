"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Reach, as arithmetic rather than hope
=====================================================
The production system is good. The distribution system was a posting schedule.
This is the missing layer, and it rests on one correction:

    Reach here is not views. It is how many people in the taluks this channel
    covers see a story they can use, and then send it to somebody in the same
    taluk.

Forty thousand views from Bengaluru is a miss. Two thousand in one taluk is a
local media position. Every number below is built for the second one.

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not know any place names. Every place in this project lives in
`brand/copy.PLACE_TAGS` and nowhere else, and this module reads that registry
without adding to it, exactly as `tokens.Limits` is the only home for numbers.
A second list of towns would drift from the first within a month, and then the
hashtags, the forwards and the relevance score would disagree about where
Byndoor is.

WHAT IT REFUSES TO DO
---------------------
It does not score virality and it does not rank by predicted views. A system
that optimises for reach alone walks a local newsroom into crime and outrage,
because those win on every engagement signal — which is the same drift D68
caps. This scores LOCAL USEFULNESS: who is affected, how near, how soon, and
whether the reader can act on it.
"""
from __future__ import annotations

from dataclasses import dataclass

from .content import Story
from .tokens import Limits


# ─────────────────────────────────────────────────────────────────────────────
#  WHERE A STORY LANDS
#  Read from the existing registry. Never extended here.
# ─────────────────────────────────────────────────────────────────────────────

def place_of(story: Story) -> str:
    """The named place this story belongs to, or '' — from copy.PLACE_TAGS.

    Delegates entirely. If a place is missing, it is missing from the registry
    and that is where it gets added, once, for hashtags and forwards and this
    at the same time.
    """
    from .copy import _place_token
    return _place_token(story.location or '')


def places_covered(edition) -> dict[str, list[int]]:
    """Which places this edition speaks to, and which stories reach each.

    The unit a forward travels in. Somebody in Kundapura sends the Kundapura
    story to a Kundapura group; they do not send a district round-up, because
    a round-up is nobody's in particular.
    """
    out: dict[str, list[int]] = {}
    for i, st in enumerate(edition.stories, 1):
        p = place_of(st)
        if p:
            out.setdefault(p, []).append(i)
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  LOCAL RELEVANCE
#  Four questions a reader asks before forwarding anything: is this my town,
#  is it now, does it affect people like me, and is there something to do.
# ─────────────────────────────────────────────────────────────────────────────

# Categories by how much of a taluk they touch. Not a quality judgement — a
# weather warning is not "better" than a culture story, it simply reaches more
# people who need it on the day it runs.
BREADTH = {
    'weather': 1.0,      # everyone outdoors, everyone with a roof
    'civic': 0.9,        # roads, water, power, offices
    'health': 0.85,
    'education': 0.8,    # every household with a school-age child
    'breaking': 0.9,
    'crime': 0.5,        # high attention, narrow usefulness
    'farm': 0.6,
    'culture': 0.7,      # identity travels further than its audience size
    'sport': 0.4,
    'obituary': 0.5,     # narrow, but intensely relevant to those it reaches
    'explainer': 0.6,
}

# Copy that tells a reader what to DO. The difference between a story people
# read and a story people send to their family, and the single strongest
# forward predictor there is.
ACTIONABLE = (
    'ಸಂಪರ್ಕಿಸಿ', 'ಕೊನೆಯ ದಿನ', 'ಅರ್ಜಿ', 'ನೋಂದಣಿ', 'ಸಹಾಯವಾಣಿ',
    'ಎಚ್ಚರಿಕೆ', 'ಸೂಚನೆ', 'ಬಂದ್', 'ರದ್ದು', 'ಮುಂದೂಡ', 'ಬದಲಾವಣೆ',
    'ತೆರೆದಿರುತ್ತದೆ', 'ಲಭ್ಯ', 'ಉಚಿತ', 'ವೇಳಾಪಟ್ಟಿ', 'ಪರೀಕ್ಷೆ', 'ಫಲಿತಾಂಶ',
)


@dataclass
class Relevance:
    score: float                  # 0..1
    band: str                     # high | medium | low
    place: str
    actionable: bool
    why: list[str]

    def __str__(self) -> str:
        return f'{self.band.upper()} {self.score:.2f} — ' + '; '.join(self.why)


def relevance(story: Story) -> Relevance:
    """How useful this story is to somebody living in its taluk.

    Deterministic, from fields the story already carries. No model, no
    prediction, nothing that drifts between runs — this feeds a format
    decision, and a format decision that changes on a re-render is a bug.
    """
    why: list[str] = []
    score = 0.0

    breadth = BREADTH.get(story.category, 0.5)
    score += breadth * 0.35
    why.append(f'{story.category} reaches ~{breadth:.0%} of a taluk')

    place = place_of(story)
    if place:
        score += 0.25
        why.append(f'names {place}')
    else:
        why.append('NO PLACE — nobody can tell whether this is their town')

    # Something to do. Checked across the copy a reader actually sees.
    text = ' '.join(filter(None, [story.headline, story.deck, story.takeaway,
                                  *story.points]))
    actionable = any(w in text for w in ACTIONABLE)
    if actionable:
        score += 0.25
        why.append('tells the reader what to do')

    # Now, or it is an archive entry. `is_breaking` is derived from the
    # publish timestamp and cannot be asserted (D22), so this cannot be gamed.
    if story.is_breaking or story.category in ('weather', 'breaking'):
        score += 0.15
        why.append('time-sensitive')

    score = min(1.0, score)
    band = 'high' if score >= 0.70 else ('medium' if score >= 0.45 else 'low')
    return Relevance(round(score, 2), band, place, actionable, why)


# ─────────────────────────────────────────────────────────────────────────────
#  FORMAT
#  Not every story is a reel. Making one of each from everything is how a small
#  account splits its own test audience six ways and looks mediocre in all six.
# ─────────────────────────────────────────────────────────────────────────────

# What each kind of story is best as, when the editor has not said (D92).
# A notice is read and screenshotted, so it goes in ಸುದ್ದಿ ಸಾರ; a story with
# weather or a match in it is quick news. Breaking news is decided from the
# clock, not from this table. The editor's word always wins.
SEGMENT_BY_CATEGORY = {
    'weather':   'speed',
    'culture':   'speed',
    'sport':     'speed',
    'crime':     'saara',       # read carefully, not glanced at (D68)
    'civic':     'saara',       # a notice is read, not watched
    'health':    'saara',
    'education': 'saara',
    'farm':      'saara',
    'obituary':  'saara',       # dignity: no reel, no hook, no CTA
    'explainer': 'saara',
}


def suggest_segment(story: Story) -> tuple[str, str]:
    """(segment, why) — the desk's proposal, which the editor confirms."""
    if story.category == 'breaking' and story.is_breaking:
        return 'mukhya', 'breaking, inside the window — its own post, with a picture'
    seg = SEGMENT_BY_CATEGORY.get(story.category, 'saara')
    rel = relevance(story)
    if seg == 'speed' and (rel.band == 'low' or not rel.place):
        return 'saara', ('quick news needs a place and local weight; '
                         + ('; '.join(rel.why) or 'no place named'))
    return seg, f'{story.category} — {"quick news" if seg == "speed" else "read, not watched"}'


# ─────────────────────────────────────────────────────────────────────────────
#  THE FOLD
#  Instagram truncates a caption at about 125 characters behind "... more".
#  A coastal story whose town name sits past that is invisible to the people
#  it was written for.
# ─────────────────────────────────────────────────────────────────────────────

def place_before_fold(story: Story, caption: str) -> tuple[bool, str]:
    """Is the town name inside the window a reader actually sees?"""
    from .copy import FOLD
    place = place_of(story)
    if not place:
        return False, 'no place on the story at all'
    head = caption[:FOLD]
    if place in head:
        return True, f'{place} at character {head.index(place)}'
    at = caption.find(place)
    where = f'character {at}' if at >= 0 else 'nowhere in the caption'
    return False, (f'{place} appears at {where}, past the {FOLD}-character '
                   f'fold. Nobody sees it without tapping "more".')


# ─────────────────────────────────────────────────────────────────────────────
#  THE DAY, AS A REACH DECISION
# ─────────────────────────────────────────────────────────────────────────────

def plan(edition) -> dict:
    """What this edition should actually publish, and to whom."""
    rows = []
    for i, st in enumerate(edition.stories, 1):
        rel = relevance(st)
        seg, why = suggest_segment(st)
        rows.append({
            'story': i,
            'headline': st.headline[:60],
            'place': rel.place,
            'category': st.category,
            'relevance': rel.score,
            'band': rel.band,
            'segment': st.segment,
            'suggested': seg,
            'why': why,
        })
    return {'stories': rows, 'places': places_covered(edition)}


def report(edition) -> str:
    """The reach view of a day, as something readable at 07:40."""
    p = plan(edition)
    out = ['# Reach plan', '']
    places = p['places']
    if places:
        out.append('**Places this edition speaks to** — the unit a forward '
                   'travels in:')
        out.append('')
        for place, ids in sorted(places.items()):
            out.append(f'- **{place}** — '
                       + ', '.join(f'story {i}' for i in ids))
        out.append('')
    unplaced = [r for r in p['stories'] if not r['place']]
    if unplaced:
        out += ['> ⚠️ ' + ', '.join(f'story {r["story"]}' for r in unplaced)
                + ' name no place. Nobody scrolling can tell whether it is '
                  'about their town, and nobody forwards what is not theirs.',
                '']
    out += ['| # | place | category | relevance | runs in | desk would say |',
            '|---|---|---|--:|---|---|']
    for r in p['stories']:
        out.append(f'| {r["story"]} | {r["place"] or "—"} | {r["category"]} | '
                   f'{r["relevance"]:.2f} {r["band"]} | {r["segment"] or "—"} | '
                   f'{r["suggested"]} |')
    out.append('')
    return '\n'.join(out) + '\n'
