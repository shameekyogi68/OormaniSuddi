"""Bulletin — the day's edition as a 16:9 long-form video for YouTube.

Why this exists: the channel was producing a 16:9 thumbnail for a video that
did not exist. Its only video output was a sub-60s vertical clip, which YouTube
treats as a Short — and Shorts pull a frame rather than use a custom thumbnail.
So the best-engineered artefact in the set had nothing to sit on, and the
realistic monetisation path (1,000 subs + 4,000 watch hours) was closed.

This is the same motion engine at a different aspect: `brand.motion` lays the
type out as a broadcast lower-third when the frame is wider than it is tall.
Scene pacing is the reel's, minus the vertical safe zones — landscape has no
platform chrome to dodge, so scenes can carry a little more.

See STANDARDS.md §7 and docs/DECISIONS.md D29.
"""
from __future__ import annotations

from brand.content import Edition
from brand.motion import render_reel


def bulletin(edition: Edition, path: str, target_seconds: float | None = None,
             **kw) -> str:
    """Render the edition as a 16:9 bulletin.

    `target_seconds` is a ceiling as it is everywhere else — scenes are never
    compressed below reading speed. Left as None, the bulletin runs as long as
    the copy needs, which for a four-story edition is typically 45-70s.
    """
    return render_reel(edition, path, format_key='bulletin',
                       target_seconds=target_seconds, **kw)


__all__ = ['bulletin']
