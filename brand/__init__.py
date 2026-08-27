"""
ಊರ್ಮನಿ ಸುದ್ದಿ — brand system
============================
The engine. The templates that use it live in `templates/`.
Read STANDARDS.md before changing anything here.

    from brand import Story, Photo, Edition
    import templates as TP;  TP.render('report_card', story, 'card.jpg')

Layers, bottom up:
    tokens      colour, type scale, grid, formats, motion constants
    typo        Kannada-safe text engine (baselines, wrapping, fitting)
    surface     canvas, house photo grade, scrims, grain, hairlines
    components  masthead, eyebrow, fact list, provenance, footer
    content     Story / Photo / Edition, the contract, the clock, legal guards
    copy        captions, hashtags, YouTube metadata, alt text
    motion      the reel engine (driven by templates/reel.py)
    qa          preflight and output audit
"""
from .content import (Story, Photo, Edition, ContentError, IST,
                      now, freeze, frozen, parse_dt)
from .motion import render_reel, plan_durations
from .qa import preflight, inspect, audit, compliance
from .copy import for_story as copy_for_story, for_edition as copy_for_edition
from .tokens import C, Role, T, Grid, FORMATS, fmt, CATEGORIES, category

__all__ = [
    'Story', 'Photo', 'Edition', 'ContentError', 'IST',
    'now', 'freeze', 'frozen', 'parse_dt',
    'render_reel', 'plan_durations',
    'preflight', 'inspect', 'audit', 'compliance',
    'copy_for_story', 'copy_for_edition',
    'C', 'Role', 'T', 'Grid', 'FORMATS', 'fmt', 'CATEGORIES', 'category',
]
