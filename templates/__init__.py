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

There are three news formats and a greeting (D92). Adding a fourth news
format is a decision, not a file: write it down in docs/DECISIONS.md first.
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
    # The three news formats (D92). A story runs in exactly one of them, named
    # by its `segment`: speed → roundup, saara → saara, mukhya → mukhya.
    Spec(key='saara', module='saara', entry='saara',
         takes='edition', format='post', size=(1080, 1350), produces='files',
         summary='ಸುದ್ದಿ ಸಾರ — the day\'s text bulletin: index cover → one slide '
                 'per story → sources and follow. No pictures, ever.',
         when='Stories with segment "saara". The everyday digest: useful, '
              'quick to read, forwarded. Needs Limits.saara_min_stories to '
              'Limits.saara_max_stories stories.',
         requires=['stories', 'date', 'segment: "saara"'],
         accepts=['deck', 'points', 'location', 'category'],
         limits={'stories_min': 2, 'stories_max': 6, 'points': 3},
         notes='Paper & Red (D92). A photograph on a saara story is ignored. '
               'Writes saara_01_cover.jpg, saara_02.jpg … saara_NN_sources.jpg, '
               'saara_copy.txt and saara_caption.txt.'),
    Spec(key='mukhya', module='mukhya', entry='mukhya',
         takes='story', format='post', size=(1080, 1350), produces='files',
         summary='ಮುಖ್ಯ ಸುದ್ದಿ — one breaking or top story: photo cover → '
                 'ಏನಾಗಿದೆ? → source and corrections.',
         when='Stories with segment "mukhya": breaking news, or the day\'s '
              'story that deserves its own post. Always a picture — a real '
              'one first; AI only when the editor was asked and said generate '
              '(photo_plan "ai", photo.approved_by).',
         requires=_COMMON + ['photo', 'segment: "mukhya"'],
         accepts=['deck', 'points', 'location', 'takeaway'],
         limits={'per_day': 2, 'points': 3},
         notes='Paper & Red (D92). A breaking story\'s kicker is the red '
               'ಬ್ರೇಕಿಂಗ್ block, computed from published_at, never asserted. '
               'Writes mukhya_<k>_01_cover.jpg, _02_points.jpg, _03_source.jpg '
               'and mukhya_<k>_copy.txt / _caption.txt.'),
    Spec(key='roundup', module='roundup', entry='render_roundup',
         takes='edition', format='reel', size=(1080, 1920), produces='file',
         summary='ಸ್ಪೀಡ್ ನ್ಯೂಸ್ — the day\'s stories as one quick-news reel.',
         when='Stories with segment "speed": the day\'s quick hits, three or '
              'more. A place and one line per story, spoken by the anchor '
              'while it is on screen. A story without a picture gets a '
              'type-only frame.',
         requires=['stories', 'date', 'edition_no', 'strapline'],
         limits={'stories_min': 3, 'reel_line_chars': 46,
                 'target_seconds_max': 45},
         notes='Each story is cut to its own measured narration (2.8–6.0s), '
               'with a counter and one progress segment per story. The wipe '
               'moves pictures only: story text is gone before it starts and '
               'returns after it lands, so a cut never slices a headline. Laid '
               'out in the Reels safe zone, clear of the action rail and the '
               'caption. Every word spoken goes through the TTS normaliser; '
               'audio is measured and corrected in two passes to -14 LUFS. '
               'When the day runs past 45s the tail stories are left out and '
               'reported. Paper & Red (D92). Writes '
               'roundup_cover.jpg and roundup_caption.txt.'),
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
    """The format a story runs in — read off its segment (D92)."""
    from brand.content import SEGMENTS
    return SEGMENTS.get(getattr(story, 'segment', ''), ('', 'saara'))[1]


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


# Convenience re-exports, so `from templates import saara` works.
def __getattr__(name):
    if name in TEMPLATES:
        return TEMPLATES[name].fn()
    raise AttributeError(name)


__all__ = ['TEMPLATES', 'Spec', 'choose', 'get', 'render', 'as_dict', 'dump_json']
