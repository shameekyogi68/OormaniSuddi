"""
ಊರ್ಮನಿ ಸುದ್ದಿ — what people are searching today, and which of it is ours. D86.
===============================================================================
`scripts/trending_tags.py` writes `inbox/trends_<date>.json` every morning
from Google Trends (Karnataka first, then India); the trend-scout agent adds
what it finds trending on Instagram and YouTube, which publish no feed.

A trend is only ever put on a post that is ABOUT it. That is not caution for
its own sake:

  * YouTube treats hashtags and tags unrelated to the video as misleading
    metadata — the video is removed and the channel takes a strike.
  * Instagram reads at most five hashtags since December 2025, and ranks a
    post by how the people it is shown to behave. A trend that is not the
    story sends it to people who swipe past in a second, and that is the
    signal that stops it being shown to anyone else.

So a trend earns its place by matching words in the story's own copy — the
same test the picture desk uses (`stock._mentions`). An unrelated trend gets
the channel less reach, not more.
"""
from __future__ import annotations

import json
import os
from datetime import date as _date

from .content import Story
from .tokens import Limits

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(ROOT, 'inbox')


def path_for(day: str | None = None) -> str:
    return os.path.join(INBOX, f'trends_{day or _date.today().isoformat()}.json')


def load(day: str | None = None) -> list[dict]:
    """Today's trend items, or [] when the morning fetch has not run."""
    try:
        with open(path_for(day), encoding='utf-8') as fh:
            return json.load(fh).get('items', [])
    except (OSError, ValueError):
        return []


def _text(story: Story) -> str:
    return ' '.join(filter(None, [
        story.headline, story.reel_line, getattr(story, '_hook', ''),
        story.deck, story.takeaway, story.location, *(story.points or [])]))


# Words too common to say what a story is about. "ಕನ್ನಡ" is in ದಕ್ಷಿಣ ಕನ್ನಡ,
# and "result" is in every exam story — neither makes #BiggBossKannada or
# #IbpsPoPrelimsResult ours.
_COMMON = {'ಕನ್ನಡ', 'ಕರ್ನಾಟಕ', 'ಸುದ್ದಿ', 'ಭಾರತ', 'ಇಂದು', 'news', 'result',
           'results', 'live', 'today', 'india', 'karnataka', 'south', 'north',
           'national', 'team', 'match', 'score', 'update', 'kannada'}


def matches(story: Story, item: dict) -> list[str]:
    """The words of `item` this story actually says. [] means not ours.

    The whole trend phrase, said in the story, is enough. Otherwise a
    multi-word trend needs two of its distinctive words: one shared word is
    a coincidence, two is the same subject.
    """
    from .stock import _mentions
    text = _text(story)
    low = text.lower()
    term = (item.get('term') or '').strip()
    if term and _mentions(low, term.lower()):
        return [term]
    words = [w for w in item.get('match', [])
             if w != term and len(w.strip()) >= 3
             and w.strip().lower() not in _COMMON and not w.strip().isdigit()]
    hit = [w for w in words if _mentions(low, w.lower())]
    need = 1 if len(term.split()) <= 1 else 2
    return hit if len(hit) >= need else []


def for_story(story: Story, platform: str = 'instagram',
              items: list[dict] | None = None) -> list[str]:
    """Trending tags this story may honestly carry, strongest first."""
    items = load() if items is None else items
    scored = []
    for it in items:
        plats = it.get('platforms') or ['instagram', 'youtube']
        if platform not in plats or not it.get('tag'):
            continue
        hit = matches(story, it)
        if hit:
            scored.append((len(hit), it.get('rank', 99), it['tag']))
    scored.sort(key=lambda x: (-x[0], x[1]))
    out: list[str] = []
    for _, _, tag in scored:
        if tag.lower() not in {t.lower() for t in out}:
            out.append(tag)
    return out[:Limits.trend_tags_max]


def keywords_for(story: Story, items: list[dict] | None = None) -> list[str]:
    """Search phrases (not hashtags) of matched trends, for the YouTube tags
    field and the caption's keyword line."""
    items = load() if items is None else items
    out = []
    for it in items:
        if matches(story, it):
            term = (it.get('term') or '').strip()
            if term and term not in out:
                out.append(term)
    return out[:Limits.trend_tags_max * 2]
