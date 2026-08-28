"""Bulletin — the day's edition as a 16:9 long-form video for YouTube.

Why this exists: the channel was producing a 16:9 thumbnail for a video that
did not exist. Its only video output was a sub-60s vertical clip, which YouTube
treats as a Short — and Shorts pull a frame rather than use a custom thumbnail.
So the best-engineered artefact in the set had nothing to sit on, and the
realistic monetisation path (1,000 subs + 4,000 watch hours) was closed.

This is the same motion engine at a different aspect AND a different pace.
`brand.motion` lays the type out as a broadcast lower-third when the frame is
wider than it is tall, and drives it with `motion.BULLETIN` rather than
`motion.REEL`:

  * the scene shows the PRINT headline and the DECK, not the one-line
    reel_line — the carousel's payload, which is what the viewer opened a
    long-form video to get;
  * a scene may run to 30s rather than 12s, because a bulletin is watched on
    purpose while a reel is glanced at in a feed.

That is what makes the length come out right on its own. On real four-story
copy it runs 84-97s — inside YouTube's long-form zone — with nothing padded
and nothing cut. See DECISIONS.md D37.
"""
from __future__ import annotations

from brand.content import Edition
from brand.motion import render_reel


def bulletin(edition: Edition, path: str, target_seconds: float | None = None,
             **kw) -> str:
    """Render the edition as a 16:9 bulletin.

    `target_seconds` is a ceiling as it is everywhere else — scenes are never
    compressed below reading speed. Left as None (the normal case) the bulletin
    runs as long as the decks need, which on a four-story edition lands at
    roughly 60-120s. Under 60s it says so rather than padding: YouTube treats
    sub-60s video as a Short and pulls its own frame instead of the thumbnail.
    """
    return render_reel(edition, path, format_key='bulletin',
                       target_seconds=target_seconds, **kw)


__all__ = ['bulletin']
