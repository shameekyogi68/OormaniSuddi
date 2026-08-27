"""Text card — 4:5 with no photograph.\n\nFor orders, advisories and results, where a stock picture would add nothing\ntrue. The headline sits high and the detail is anchored to the foot, with the\nbrand horizon in the air between."""
from __future__ import annotations

import os
from PIL import Image

from brand import typo, components as cp
from brand.surface import (Surface, scrim, rule, vrule, panel, place_photo, grain,
                           radial_glow, paste_logo, duotone, house_grade, cover)
from brand.tokens import (C, Role, T, Grid, fmt, category, alpha, Grade,
                          Brand)
from brand.content import Story, Edition



def text_card(story: Story, path: str, format_key: str = 'post') -> str:
    """4:5 with no photograph — for orders, advisories and results, where a
    stock picture would add nothing true.

    The headline sits high and the detail is anchored to the foot, with the
    horizon glow in the air between. A text card that flows top-down ends with
    a third of the frame empty, which reads as a mistake rather than as space.
    """
    story.validate()
    F = fmt(format_key)
    W, H = F.w, F.h
    m = Grid.margin
    cw = W - 2 * m

    sf = Surface(W, H, F.ss)
    cp.page_base(sf, 0.5)

    foot_top = H - 58 - T.meta[0] * 1.1 - 22
    src_top = foot_top - 30 - T.micro[0] * 1.26

    top = cp.masthead(sf, m, 52, cw, right_top=story.date_kn,
                      right_bot=f'{story.day_kn} • {story.time_kn}') + 76

    # ── foot-anchored detail block ───────────────────────────────────────
    foot_stack = []
    fy_bottom = src_top - 44
    if story.takeaway:
        f_t = typo.font('kn_var', sf.s(T.body_sm[0]), weight=460)
        tb = typo.layout(story.takeaway, f_t, sf.s(cw - 48), T.body_sm[1])
        foot_stack.append(('take', tb,
                           T.body_sm[0] * 1.46 + tb.height / sf.ss + 14))
    if story.points:
        gap = 34
        f_f = typo.font('kn_var', sf.s(T.body[0]), weight=440)
        fb = [typo.layout(pt, f_f, sf.s(cw - 62), T.body[1]) for pt in story.points]
        foot_stack.insert(0, ('facts', fb,
                              sum(b.height / sf.ss for b in fb) + gap * (len(fb) - 1)))
    if story.numbers:
        foot_stack.insert(0, ('stats', story.numbers, T.h2[0] * 1.02 + 46))

    foot_h = sum(x[2] for x in foot_stack) + 46 * max(0, len(foot_stack) - 1)
    foot_y = fy_bottom - foot_h

    # ── headline region ──────────────────────────────────────────────────
    head_room = (foot_y - 60) - top - 34 - 40
    y = cp.eyebrow(sf, m, top, cw, story) + 40
    hb = typo.fit(story.headline, 'kn', sf.s(T.display[0]), sf.s(T.h3[0]),
                  sf.s(cw), sf.s(head_room * (0.68 if story.deck else 0.92)),
                  T.display[1], max_lines=4)
    typo.draw_block(sf.img, hb, sf.s(m), sf.s(y), Role.text_hi, box_w=sf.s(cw))
    y += hb.height / sf.ss
    if story.deck:
        y += 34
        y = cp.deck(sf, m, y, cw, story.deck, max_lines=3)

    # The horizon sits in the air between the headline and the detail.
    cp.horizon(sf, (y + foot_y) / 2 + 10, 1.0)
    radial_glow(sf, W * 0.5, (y + foot_y) / 2 + 10, W * 0.60, C.gold_600, 0.12)

    # ── draw the foot stack ──────────────────────────────────────────────
    fy = foot_y
    for i, (kind, payload, h) in enumerate(foot_stack):
        if i:
            fy += 46
        rule(sf, m, fy - 24, m + cw, Role.hairline, 1.0)
        if kind == 'stats':
            cp.stat_row(sf, m, fy, cw, payload)
        elif kind == 'facts':
            gap = 34
            f_num = typo.font('latin', sf.s(T.body[0] * 0.80), weight=760)
            cy = fy
            for j, b in enumerate(payload):
                if j:
                    rule(sf, m, cy - gap / 2, m + cw, Role.hairline_soft, 1.0)
                bl = cy + b.first_rise / sf.ss * 0.94
                nw = typo.draw_text(sf.img, f'{j + 1:02d}', sf.s(m), sf.s(bl),
                                    f_num, C.gold_500, tracking=0.02) / sf.ss
                rule(sf, nw + 9, bl - T.body[0] * 0.22, m + 46,
                     alpha(C.gold_500, 0.5), 1.5)
                typo.draw_block(sf.img, b, sf.s(m + 62), sf.s(cy), C.paper_100,
                                box_w=sf.s(cw - 62))
                cy += b.height / sf.ss + gap
        else:
            cp.takeaway(sf, m, fy, cw, story.takeaway)
        fy += h

    cp.sourceline(sf, m, src_top, cw, story)
    cp.footer(sf, m, foot_top, cw, right=story.dateline or Brand.coverage)
    grain(sf, Grade.grain, Grade.grain_shadow_bias)
    return sf.save(path)
