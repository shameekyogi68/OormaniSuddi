"""Reel / Short — 9:16 video of the day's edition.

A thin template face over `brand.motion`, which holds the engine: eased
sprite reveals, Ken Burns, scene timing from reading speed, and the audio
master. Kept separate because the engine is 600 lines of motion machinery
that the still templates have no use for.

See STANDARDS.md §7.
"""
from __future__ import annotations

from brand.motion import render_reel, plan_durations, reading_seconds

__all__ = ['render_reel', 'plan_durations', 'reading_seconds']
