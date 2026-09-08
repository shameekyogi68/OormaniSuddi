"""Reel / Short — 9:16 video of the LEAD story.

Opens on the news, not a logo sting. The carousel and the 16:9 bulletin
carry the rest of the edition. See DECISIONS.md D39.

A thin template face over `brand.motion`, which holds the engine: eased
sprite reveals, Ken Burns, scene timing from reading speed, and the audio
master. Kept separate because the engine is 600 lines of motion machinery
that the still templates have no use for.

When the caller passes a `voice=` VoiceTrack, the reel is cut from the
MEASURED narration instead of from reading time alone — one card per spoken
beat, each held exactly as long as its own sentence. `reel_cards` and
`reel_min_spans` are the contract the voice engine synthesizes against.

See STANDARDS.md §7.
"""
from __future__ import annotations

from brand.motion import (render_reel, plan_durations, reading_seconds,
                          reel_cards, reel_min_spans, card_read_seconds, Card)

__all__ = ['render_reel', 'plan_durations', 'reading_seconds',
           'reel_cards', 'reel_min_spans', 'card_read_seconds', 'Card']
