"""Stat card — when the story IS the number."""
from __future__ import annotations

import os
from PIL import Image

from brand import typo, components as cp
from brand.surface import (Surface, scrim, rule, vrule, panel, place_photo, grain,
                           radial_glow, paste_logo, duotone, house_grade, cover)
from brand.tokens import (C, Role, T, Grid, fmt, category, alpha, Grade)
from brand.content import Story, Edition



def stat_card(story: Story, path: str, format_key: str = 'square') -> str:
    """When the story is the number."""
    story.validate()
    F = fmt(format_key)
    W, H = F.w, F.h
    m = Grid.margin
    cw = W - 2 * m

    sf = Surface(W, H, F.ss)
    cp.page_base(sf, 0.6)

    foot_top = H - 58 - T.meta[0] * 1.1 - 22
    src_top = foot_top - 30 - T.micro[0] * 1.26

    top = cp.masthead(sf, m, 48, cw, right_top=story.date_kn,
                      right_bot=f'{story.day_kn} • {story.time_kn}') + 62

    blurb_h = 0.0
    if story.deck:
        db = typo.fit(story.deck, 'kn_var', sf.s(T.body[0]), sf.s(T.body[0] * 0.82),
                      sf.s(cw), sf.s(T.body[0] * T.body[1] * 3), T.body[1],
                      weight=450, max_lines=3)
        blurb_h = db.height / sf.ss

    stats_h = T.h2[0] * 1.02 + 48 if story.numbers else 0
    low_h = stats_h + (54 + blurb_h if blurb_h else 0)
    low_y = (src_top - 46) - low_h

    y = cp.eyebrow(sf, m, top, cw, story) + 34
    hb = typo.fit(story.headline, 'kn', sf.s(T.h1[0]), sf.s(T.h4[0]), sf.s(cw),
                  sf.s((low_y - 70) - y), T.h1[1], max_lines=3)
    typo.draw_block(sf.img, hb, sf.s(m), sf.s(y), Role.text_hi, box_w=sf.s(cw))

    cp.horizon(sf, (y + hb.height / sf.ss + low_y) / 2, 0.85)

    if story.numbers:
        rule(sf, m, low_y - 30, m + cw, Role.hairline, 1.0)
        ny = cp.stat_row(sf, m, low_y, cw, story.numbers)
        rule(sf, m, ny + 26, m + cw, Role.hairline, 1.0)
    if blurb_h:
        typo.draw_block(sf.img, db, sf.s(m), sf.s(low_y + stats_h + 54),
                        C.paper_200, box_w=sf.s(cw))

    cp.sourceline(sf, m, src_top, cw, story)
    cp.footer(sf, m, foot_top, cw, right=story.location or '')
    grain(sf, Grade.grain, Grade.grain_shadow_bias)
    return sf.save(path)
