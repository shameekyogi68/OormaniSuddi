"""
ಊರ್ಮನಿ ಸುದ್ದಿ — brand system
============================
The engine. The templates that use it live in `templates/`.
Read STANDARDS.md before changing anything here.

    from brand import Story, Photo, Edition
    import templates as TP;  TP.render('saara', edition, 'out/day')

Layers, bottom up:
    tokens      colour, type scale, grid, formats, motion constants
    typo        Kannada-safe text engine (baselines, wrapping, fitting)
    surface     canvas, house photo grade, scrims, grain, hairlines
    components  masthead, eyebrow, provenance, footer
    paper       the Paper & Red page every news slide is drawn on (D92)
    content     Story / Photo / Edition, the contract, the clock, legal guards
    copy        captions, hashtags, forwards, alt text, the publishing plan
    motion      the reel engine
    speednews   ಸ್ಪೀಡ್ ನ್ಯೂಸ್, the 9:16 roundup reel (D81)
    animate     the scan-wipe carousel videos (D98–D100)
    voice       narration and the pronunciation normaliser (D53)
    qa          preflight and output audit
    review      the Chief Editor gate, APPROVAL.md, the sign-off (D62, D108)
    dispatch    which desks are due, and their receipts (D87, D95)
"""
from .content import (Story, Photo, Edition, ContentError, IST,
                      now, freeze, frozen, parse_dt)
from .motion import render_reel, plan_durations
from .qa import preflight, inspect, audit, compliance
from .copy import for_story as copy_for_story, for_edition as copy_for_edition
from .tokens import C, Role, T, Grid, FORMATS, fmt, CATEGORIES, category, Limits

__all__ = [
    'Story', 'Photo', 'Edition', 'ContentError', 'IST',
    'now', 'freeze', 'frozen', 'parse_dt',
    'render_reel', 'plan_durations',
    'preflight', 'inspect', 'audit', 'compliance',
    'copy_for_story', 'copy_for_edition',
    'C', 'Role', 'T', 'Grid', 'FORMATS', 'fmt', 'CATEGORIES', 'category',
    'Limits',
]
