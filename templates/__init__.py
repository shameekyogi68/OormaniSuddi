"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Template registry
=================================
One file per template, plus a machine-readable description of every one.

This registry exists so a tool that has never seen this codebase — including an
AI given a pile of news copy — can answer three questions without guessing:

    which template does this story want?      → choose(story)  /  TEMPLATES[k].when
    what fields must I supply?                → TEMPLATES[k].requires / accepts
    what will be rejected, and why?           → TEMPLATES[k].limits

`registry.json` is this same table, dumped for anything that is not Python.
Regenerate it with `python3 -m templates --dump`.

Adding a template: write `templates/<name>.py`, add a Spec below, re-dump the
JSON, and add a row to docs/TEMPLATES.md. Nothing else needs to know.
"""
from __future__ import annotations

import importlib
import json
import os
from dataclasses import dataclass, field, asdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass
class Spec:
    """Everything a caller needs to use one template correctly."""
    key: str
    module: str
    entry: str
    takes: str                  # 'story' | 'edition'
    format: str                 # a key in brand.tokens.FORMATS
    size: tuple[int, int]
    produces: str               # 'file' | 'files'
    summary: str
    when: str                   # the rule for choosing this template
    requires: list[str] = field(default_factory=list)
    accepts: list[str] = field(default_factory=list)
    limits: dict = field(default_factory=dict)
    notes: str = ''

    def fn(self):
        return getattr(importlib.import_module(f'templates.{self.module}'), self.entry)

    def __call__(self, *a, **kw):
        return self.fn()(*a, **kw)


_COMMON = ['headline', 'category', 'sources', 'status', 'published_at']

TEMPLATES: dict[str, Spec] = {t.key: t for t in [
    Spec(key='report_card', module='report_card', entry='report_card',
         takes='story', format='post', size=(1080, 1350), produces='file',
         summary='The flagship 4:5 news post: full-bleed photograph over an '
                 'editorial stack.',
         when='The default for almost everything. With a photograph it leads '
              'on the picture; without one it draws an editorial plate, so the '
              'post still has a visual.',
         requires=_COMMON,
         accepts=['photo', 'deck', 'points', 'takeaway', 'location', 'dateline',
                  'reporter'],
         limits={'headline_chars': 78, 'deck_chars': 190, 'points': 3,
                 'point_chars': 150},
         notes='Drops content in editorial order when it cannot fit everything: '
               'advisory, then standfirst, then facts from the bottom. On '
               'weather / health / civic / breaking the advisory survives '
               'instead, because the helpline is the point.'),

    Spec(key='text_card', module='text_card', entry='text_card',
         takes='story', format='post', size=(1080, 1350), produces='file',
         summary='4:5 typographic poster with no photograph.',
         when='Only when you deliberately want a pure typographic poster with '
              'no visual at all. For an ordinary story with no photograph, use '
              'report_card — it draws a plate.',
         requires=_COMMON,
         accepts=['deck', 'points', 'takeaway', 'numbers', 'location', 'dateline'],
         limits={'headline_chars': 78, 'deck_chars': 190, 'points': 3},
         notes='Sets the headline much larger than report_card, because it has '
               'the whole frame.'),

    Spec(key='quote_card', module='quote_card', entry='quote_card',
         takes='story', format='square', size=(1080, 1080), produces='file',
         summary='A single voice on a duotone bed.',
         when='Use when the story IS somebody\'s words — a statement, an order '
              'read out, a reaction.',
         requires=_COMMON + ['quote'],
         accepts=['photo', 'location'],
         limits={'quote_chars': 240},
         notes='quote is a two-item list: [text, attribution]. The photograph, '
               'if any, is flattened to two tones so it cannot fight the words.'),

    Spec(key='stat_card', module='stat_card', entry='stat_card',
         takes='story', format='square', size=(1080, 1080), produces='file',
         summary='Big numerals with Kannada labels.',
         when='Use when the story IS the number — rainfall totals, budgets, '
              'turnout, case counts.',
         requires=_COMMON + ['numbers'],
         accepts=['deck', 'location'],
         limits={'headline_chars': 70, 'numbers': 3},
         notes='numbers is a list of [value, label] pairs. Three reads best; '
               'four starts to crowd.'),

    Spec(key='story_card', module='story_card', entry='story_card',
         takes='story', format='story', size=(1080, 1920), produces='file',
         summary='9:16 still for Instagram Stories and WhatsApp status.',
         when='One per edition, usually the lead. Also the right format for a '
              'single urgent alert.',
         requires=_COMMON,
         accepts=['photo', 'deck', 'location'],
         limits={'headline_chars': 78},
         notes='Critical content stays inside a 72/250/72/340 safe inset. The '
               'band below it carries the handle rather than dead black.'),

    Spec(key='youtube_thumb', module='youtube_thumb', entry='youtube_thumb',
         takes='story', format='thumb', size=(1280, 720), produces='file',
         summary='16:9 thumbnail built to survive a 6× reduction.',
         when='One per video. Pass a short hook=, NOT the headline.',
         requires=_COMMON,
         accepts=['photo', 'location', 'hook'],
         limits={'hook_chars': 34, 'hook_words': 7},
         notes='In a YouTube feed this is about 210 px wide. Anything longer '
               'than about seven words stops being readable there, and the '
               'renderer warns when you exceed it.'),

    Spec(key='carousel', module='carousel', entry='carousel',
         takes='edition', format='square', size=(1080, 1080), produces='files',
         summary="The day's bulletin as a swipeable set: cover → one slide per "
                 'story → sources and follow.',
         when='One per edition. This is the highest-reach format for a daily '
              'round-up.',
         requires=['stories', 'date', 'edition_no', 'strapline'],
         accepts=[],
         limits={'stories': 6},
         notes='Returns a list of paths. Slides carry a segmented progress bar; '
               'a slide whose story has no photograph is set as a statement '
               'card rather than left half-empty.'),

    Spec(key='broadsheet', module='broadsheet', entry='broadsheet',
         takes='edition', format='broadsheet', size=(1080, 1620), produces='file',
         summary="The day's edition as a single front page.",
         when='One per edition, for readers who want everything at a glance. '
              'Also the best thing to forward on WhatsApp.',
         requires=['stories', 'date', 'edition_no', 'strapline'],
         accepts=[],
         limits={'stories': 5},
         notes='Lead story plus up to four in two columns; column cells are as '
               'tall as their content, not a fixed fraction.'),

    Spec(key='bulletin', module='bulletin', entry='bulletin',
         takes='edition', format='bulletin', size=(1920, 1080), produces='file',
         summary='16:9 long-form bulletin for YouTube.',
         when='One per edition. This is what the youtube_thumb is FOR — a '
              'vertical clip under 60s is a Short, and Shorts do not take a '
              'custom thumbnail.',
         requires=['stories', 'date', 'edition_no', 'strapline'],
         accepts=['target_seconds'],
         limits={'stories': 8, 'reel_line_chars': 46},
         notes='Same engine as the reel at a landscape aspect: the type lays '
               'out as a broadcast lower-third instead of a full-height column. '
               'Opens the 1,000-subs + 4,000-watch-hours monetisation path, '
               'which a Shorts-only channel cannot realistically reach.'),

    Spec(key='reel', module='reel', entry='render_reel',
         takes='edition', format='reel', size=(1080, 1920), produces='file',
         summary='9:16 Short of the LEAD story, with mastered audio.',
         when='One per edition — the lead only. The carousel and the 16:9 '
              'bulletin carry the rest. Opens on the news, not a logo sting.',
         requires=['stories', 'date', 'edition_no', 'strapline'],
         accepts=['target_seconds', 'voice', 'voiceover', 'bgm'],
         limits={'stories': 1, 'reel_line_chars': 46,
                 'target_seconds_min': 8, 'target_seconds_max': 45},
         notes='A reel is a glance in a vertical feed: one story, no sting, '
               'headline on frame 0. Writes reel_cover.jpg — set that as the '
               'Instagram / Shorts cover. Write a reel_line of ~45 chars. '
               'Audio is normalised to -14 LUFS / -1.5 dBTP. Pass voice= a '
               'brand.voice.VoiceTrack to cut the reel from MEASURED '
               'narration: one card per spoken beat, every cut landing '
               'between sentences, and target_seconds no longer applies '
               'because the length is the narration\'s. voiceover= is the '
               'older bare-path form, which can only guess where to cut.'),
    Spec(key='greeting', module='greeting', entry='greeting',
         takes='greeting', format='story', size=(1080, 1920), produces='files',
         summary='A festival wish designed as a poster, not a bulletin: '
                 'centred, gold foil, ornament, signed by the channel.',
         when='Festival and occasion wishes only — Gauri-Ganesha, Deepavali, '
              'Ugadi, Rajyotsava, Eid, Christmas and the like. Never for news: '
              'a news story set in this template reads as a celebration.',
         requires=['kind: "greeting"', 'occasion'],
         accepts=['wish', 'salutation', 'blessing', 'theme', 'photo',
                  'keep_clear', 'sign_label', 'date', 'tags', 'slug'],
         limits={'occasion_chars': 30, 'wish_chars': 26,
                 'salutation_chars': 34, 'blessing_chars': 96,
                 'themes': 'sacred lights harvest rajyotsava national serene'},
         notes='Renders wish_9x16.jpg, wish_4x5.jpg and wish_1x1.jpg plus '
               'wish_copy.txt. A photograph MUST declare keep_clear — the band '
               'of the image, as fractions of its height, that holds the deity '
               'or subject — and no type is ever set inside it: the solver '
               'moves the picture, frames it in an arch, or refuses. An AI '
               'image is labelled on the poster and in the caption '
               'automatically. See DECISIONS.md D54.'),
]}


# ─────────────────────────────────────────────────────────────────────────────
#  CHOOSING
# ─────────────────────────────────────────────────────────────────────────────

def choose(story) -> str:
    """Which single-story template this story wants.

    Explicit beats clever — pass a template name if you know it. These defaults
    are right often enough to save an argument every time.
    """
    if getattr(story, 'quote', None):
        return 'quote_card'
    if getattr(story, 'numbers', None) and not getattr(story, 'photo', None):
        return 'stat_card'
    # report_card for everything else, photo or not: without a photograph it
    # draws an editorial plate, so every post in the feed carries a visual.
    # text_card is still there when you deliberately want a pure text poster.
    return 'report_card'


def get(key: str) -> Spec:
    if key not in TEMPLATES:
        raise KeyError(f'unknown template {key!r}; choose from {sorted(TEMPLATES)}')
    return TEMPLATES[key]


def render(key: str, subject, path: str, **kw):
    """Render by name. `subject` is a Story or an Edition, per spec.takes."""
    return get(key)(subject, path, **kw)


def as_dict() -> dict:
    return {k: asdict(v) for k, v in TEMPLATES.items()}


def dump_json(path: str | None = None) -> str:
    path = path or os.path.join(BASE, 'templates', 'registry.json')
    with open(path, 'w') as f:
        json.dump(as_dict(), f, indent=2, ensure_ascii=False)
        f.write('\n')
    return path


# Convenience re-exports, so `from templates import report_card` still works.
def __getattr__(name):
    if name in TEMPLATES:
        return TEMPLATES[name].fn()
    raise AttributeError(name)


__all__ = ['TEMPLATES', 'Spec', 'choose', 'get', 'render', 'as_dict', 'dump_json']
