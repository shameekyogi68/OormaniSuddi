"""ಸ್ಪೀಡ್ ನ್ಯೂಸ್ — the day's stories as one 9:16 quick-news reel.

A place and one line per story, read by the anchor while it is on screen,
with a counter and progress segments so the viewer knows how many are left.
A thin face over `brand.speednews`, which holds the engine. See D81.
"""
from __future__ import annotations

from brand.speednews import render_roundup, items_for, plan, Timeline

__all__ = ['render_roundup', 'items_for', 'plan', 'Timeline']
