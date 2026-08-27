"""Quote card — a single voice, given room.\n\nThe picture is reduced to a duotone bed so it supports the words instead of\narguing with them."""
from __future__ import annotations

import os
from PIL import Image

from brand import typo, components as cp
from brand.surface import (Surface, scrim, rule, vrule, panel, place_photo, grain,
                           radial_glow, paste_logo, duotone, house_grade, cover)
from brand.tokens import (C, Role, T, Grid, fmt, category, alpha, Grade)
from brand.content import Story, Edition



def quote_card(story: Story, path: str, format_key: str = 'square') -> str:
    """A single voice, given room. The picture is reduced to a duotone bed so
    it supports the words instead of arguing with them."""
    story.validate()
    if not story.quote:
        raise ValueError('quote_card needs story.quote = (text, attribution)')
    F = fmt(format_key)
    W, H = F.w, F.h
    m = Grid.margin_l
    cw = W - 2 * m

    sf = Surface(W, H, F.ss)
    cp.page_base(sf, 0.4)

    if story.photo and os.path.exists(story.photo.path):
        im = cover(Image.open(story.photo.path), W * F.ss, H * F.ss,
                   story.photo.focal)
        im = duotone(house_grade(im, strength=0.7), C.ink_950, C.ink_500)
        sf.img.alpha_composite(im.convert('RGBA'), (0, 0))
        # Enough veil to seat the type, not so much that the bed disappears.
        scrim(sf, 0, H * 0.34, C.ink_950, 0.72, 0.34, curve=1.4)
        scrim(sf, H * 0.34, H, C.ink_950, 0.34, 0.86, curve=1.5)

    top = cp.masthead(sf, m, 48, cw, right_top=story.date_kn,
                      right_bot=story.location, on_photo=True)

    foot_top = H - 58 - T.meta[0] * 1.1 - 22
    src_top = foot_top - 30 - T.micro[0] * 1.26

    text, attrib = story.quote
    region_top, region_bot = top + 70, src_top - 96
    f_q = typo.fit(text, 'kn_serif', sf.s(T.h1[0]), sf.s(T.h4[0] * 0.86),
                   sf.s(cw - 62), sf.s((region_bot - region_top) * 0.82), 1.32,
                   max_lines=7)
    qh = f_q.height / sf.ss
    qy = region_top + ((region_bot - region_top) - qh - 60) * 0.40

    # An oversized opening quote, set behind the words — the one piece of
    # ornament this system allows, because it does a job: it tells you at a
    # glance that you are reading somebody's words rather than ours.
    typo.draw_text(sf.img, '“', sf.s(m + 6), sf.s(qy + 96),
                   typo.font('latin_srf', sf.s(300), weight=700),
                   alpha(C.gold_500, 0.16))

    vrule(sf, m, qy - 8, qy + qh + 8, C.gold_500, 3)
    typo.draw_block(sf.img, f_q, sf.s(m + 62), sf.s(qy), Role.text_hi,
                    shadow=(0, sf.s(2), sf.s(16), (0, 0, 0, 180)), box_w=sf.s(cw - 62))

    ay = qy + qh + 52
    rule(sf, m + 62, ay - 26, m + 62 + 90, alpha(C.gold_500, 0.7), 2.0)
    typo.draw_text(sf.img, attrib, sf.s(m + 62), sf.s(ay + 12),
                   typo.font_for(attrib, 'kn_var', sf.s(T.meta[0] * 1.16),
                                 weight=650),
                   C.gold_500, shadow=(0, sf.s(1), sf.s(8), (0, 0, 0, 180)))
    if story.headline:
        typo.draw_text(sf.img, story.headline, sf.s(m + 62), sf.s(ay + 52),
                       typo.font_for(story.headline, 'kn_var', sf.s(T.micro[0]),
                                     weight=460),
                       alpha(C.paper_200, 0.85),
                       shadow=(0, sf.s(1), sf.s(8), (0, 0, 0, 180)))

    cp.sourceline(sf, m, src_top, cw, story)
    cp.footer(sf, m, foot_top, cw, right=story.location or '')
    grain(sf, Grade.grain, Grade.grain_shadow_bias)
    return sf.save(path)
