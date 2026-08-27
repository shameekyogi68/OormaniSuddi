"""Story card — 9:16 for Stories and WhatsApp status.\n\nFlows bottom-up from the safe area: on a 9:16 canvas a top-down flow always\nleaves a dead band above the platform reply bar."""
from __future__ import annotations

import os
from PIL import Image

from brand import typo, components as cp
from brand.surface import (Surface, scrim, rule, vrule, panel, place_photo, grain,
                           radial_glow, paste_logo, duotone, house_grade, cover)
from brand.tokens import (C, Role, T, Grid, fmt, category, alpha, Grade,
                          Brand)
from brand.content import Story, Edition



def story_card(story: Story, path: str, format_key: str = 'story') -> str:
    """9:16 for Stories / WhatsApp status.

    Flows bottom-up from the safe area, not top-down from the picture: on a
    9:16 canvas a top-down flow always leaves a dead band above the platform's
    reply bar, and that band is the first thing that makes a story look
    unfinished.
    """
    story.validate()
    F = fmt(format_key)
    W, H = F.w, F.h
    sl, st_, sr, sb = F.safe
    m = Grid.margin
    cw = W - 2 * m

    sf = Surface(W, H, F.ss)
    cp.page_base(sf)

    safe_bottom = H - sb
    src_top = safe_bottom - T.micro[0] * 1.26 - 6
    content_bottom = src_top - 46

    # measure upward
    d_blk = None
    if story.deck:
        d_blk = typo.fit(story.deck, 'kn_var', sf.s(T.deck[0]), sf.s(T.deck[0] * 0.8),
                         sf.s(cw), sf.s(T.deck[0] * T.deck[1] * 3), T.deck[1],
                         weight=450, max_lines=3)
    h_blk = typo.fit(story.headline, 'kn', sf.s(T.h1[0]), sf.s(T.h4[0]),
                     sf.s(cw), sf.s(H * 0.24), T.h1[1], max_lines=5)

    stack_h = 34 + 40 + h_blk.height / sf.ss
    if d_blk is not None:
        stack_h += 30 + d_blk.height / sf.ss
    stack_top = content_bottom - stack_h

    cap_blk = None
    if story.photo and story.credit_line:
        cap_blk = typo.layout(story.credit_line,
                              typo.font('kn_var', sf.s(T.micro[0]), weight=420),
                              sf.s(cw), 1.34)
    photo_bottom = stack_top - 34 - ((cap_blk.height / sf.ss + 20) if cap_blk else 0)

    if story.photo and os.path.exists(story.photo.path):
        box_b = photo_bottom + 40
        place_photo(sf, story.photo.path, (0, 0, W, box_b),
                    focal=story.photo.focal,
                    fade_bottom=1.0 - (photo_bottom * 0.58) / box_b)
        scrim(sf, 0, st_ + 60, C.ink_950, 0.86, 0.0, curve=1.5)
        scrim(sf, photo_bottom * 0.55, box_b, C.ink_950, 0.0, 0.55, curve=1.8)
    else:
        cp.horizon(sf, H * 0.70, 0.9)

    cp.masthead(sf, m, st_ - 116, cw, right_top=story.date_kn,
                right_bot=story.time_kn, on_photo=bool(story.photo))

    if cap_blk is not None:
        typo.draw_block(sf.img, cap_blk, sf.s(m), sf.s(photo_bottom + 20),
                        alpha(C.paper_300, 0.9), box_w=sf.s(cw))

    y = cp.eyebrow(sf, m, stack_top, cw, story) + 40
    typo.draw_block(sf.img, h_blk, sf.s(m), sf.s(y), Role.text_hi, box_w=sf.s(cw))
    y += h_blk.height / sf.ss
    if d_blk is not None:
        y += 30
        typo.draw_block(sf.img, d_blk, sf.s(m), sf.s(y), C.paper_200, box_w=sf.s(cw))

    cp.sourceline(sf, m, src_top, cw, story)

    # The band below the safe area belongs to the platform's own UI, but it is
    # visible on WhatsApp status and on a paused Reel, so it carries the brand
    # rather than a rectangle of dead black.
    by = safe_bottom + (H - safe_bottom) * 0.46
    rule(sf, m, by - 34, m + cw, Role.hairline_soft, 1.0)
    typo.draw_text(sf.img, Brand.handle, sf.s(W / 2), sf.s(by + 8),
                   typo.font('latin', sf.s(T.meta[0] * 1.1), weight=740),
                   C.gold_500, anchor_x='c', tracking=0.015)
    typo.draw_text(sf.img, Brand.tagline, sf.s(W / 2), sf.s(by + 48),
                   typo.font('kn_var', sf.s(T.micro[0]), weight=520),
                   Role.text_dim, anchor_x='c')

    grain(sf, Grade.grain, Grade.grain_shadow_bias)
    return sf.save(path)
