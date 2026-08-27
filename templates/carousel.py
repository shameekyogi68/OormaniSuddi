"""Carousel — the day's bulletin as a swipeable set.\n\nCover → one slide per story → sources and follow."""
from __future__ import annotations

import os
from PIL import Image

from brand import typo, components as cp
from brand.surface import (Surface, scrim, rule, vrule, panel, place_photo, grain,
                           radial_glow, paste_logo, duotone, house_grade, cover,
                           editorial_plate)
from brand.tokens import (C, Role, T, Grid, fmt, category, alpha, Grade,
                          Brand,
                          Brand)
from brand.content import Story, Edition



def _progress(sf: Surface, m: float, cw: float, y: float, i: int, n: int):
    """Segmented progress bar. Tells the reader how much is left — the single
    cheapest thing you can do to raise carousel completion."""
    gap = 6
    seg = (cw - gap * (n - 1)) / n
    for k in range(n):
        x = m + k * (seg + gap)
        col = C.gold_500 if k <= i else alpha(C.paper_50, 0.18)
        panel(sf, [x, y, x + seg, y + 3], col)


def carousel(edition: Edition, outdir: str, prefix: str = 'carousel') -> list[str]:
    """Cover → one slide per story → sources & follow. Square 1080."""
    edition.validate()
    F = fmt('square')
    W, H = F.w, F.h
    m = Grid.margin
    cw = W - 2 * m
    n = len(edition.stories) + 2
    paths: list[str] = []
    os.makedirs(outdir, exist_ok=True)

    # ── cover ────────────────────────────────────────────────────────────
    lead = edition.stories[0]
    sf = Surface(W, H, F.ss)
    cp.page_base(sf)
    if lead.photo and os.path.exists(lead.photo.path):
        place_photo(sf, lead.photo.path, (0, 0, W, H), focal=lead.photo.focal)
        scrim(sf, 0, 260, C.ink_950, 0.80, 0.0, curve=1.5)
        scrim(sf, H * 0.24, H, C.ink_950, 0.0, 0.97, curve=1.9)
    else:
        cp.horizon(sf, H * 0.7, 1.0)

    cp.masthead(sf, m, 52, cw, right_top=edition.date_kn,
                right_bot=edition.strapline, on_photo=True)

    fy = H - 62
    fy -= 30
    typo.draw_text(sf.img, 'ಸ್ವೈಪ್ ಮಾಡಿ', sf.s(m), sf.s(fy),
                   typo.font('kn_var', sf.s(T.meta[0]), weight=620), C.gold_500,
                   shadow=(0, sf.s(1), sf.s(8), (0, 0, 0, 180)))
    typo.draw_text(sf.img, '→', sf.s(m + 122), sf.s(fy),
                   typo.font('latin', sf.s(T.meta[0] * 1.2), weight=700), C.gold_500)
    typo.draw_text(sf.img, f'{len(edition.stories)} ಸುದ್ದಿಗಳು', sf.s(m + cw), sf.s(fy),
                   typo.font('kn_var', sf.s(T.meta[0]), weight=500), C.paper_200,
                   anchor_x='r', shadow=(0, sf.s(1), sf.s(8), (0, 0, 0, 180)))
    fy -= 46

    tb = typo.fit(edition.strapline_title if hasattr(edition, 'strapline_title')
                  else lead.headline, 'kn', sf.s(T.h1[0]), sf.s(T.h3[0]),
                  sf.s(cw), sf.s(H * 0.34), T.h1[1], max_lines=4)
    typo.draw_block(sf.img, tb, sf.s(m), sf.s(fy - tb.height / sf.ss), Role.text_hi,
                    shadow=(0, sf.s(3), sf.s(18), (0, 0, 0, 180)), box_w=sf.s(cw))
    ey = fy - tb.height / sf.ss - 40
    cp.eyebrow(sf, m, ey - 34, cw, lead, on_photo=True)
    grain(sf, Grade.grain, Grade.grain_shadow_bias)
    paths.append(sf.save(os.path.join(outdir, f'{prefix}_01_cover.jpg')))

    # ── story slides ─────────────────────────────────────────────────────
    for i, st in enumerate(edition.stories):
        sf = Surface(W, H, F.ss)
        cp.page_base(sf, 0.5)
        top = 52
        _progress(sf, m, cw, top, i + 1, n)
        y = top + 30

        # EVERY slide carries a visual. With a photograph it is the
        # photograph; without one it is an editorial plate, which is visibly a
        # graphic. A carousel where some slides are pictures and others are
        # bare type reads as an unfinished set.
        has_photo = bool(st.photo and os.path.exists(st.photo.path))
        # Same height either way: a carousel where the graphic slides are
        # shorter than the photographed ones has a visibly ragged rhythm as you
        # swipe through it.
        ph = H * 0.36
        if has_photo:
            place_photo(sf, st.photo.path, (m, y, m + cw, y + ph),
                        focal=st.photo.focal, radius=Grid.radius_soft)
            credit = st.credit_line
        else:
            editorial_plate(sf, (m, y, m + cw, y + ph),
                            category(st.category), seed=st.headline,
                            radius=Grid.radius_soft)
            credit = 'ಗ್ರಾಫಿಕ್ಸ್  •  ' + Brand.name
        cy = y + ph + 16
        if credit:
            cb = typo.layout(credit,
                             typo.font('kn_var', sf.s(T.nano[0]), weight=420),
                             sf.s(cw), 1.34)
            typo.draw_block(sf.img, cb, sf.s(m), sf.s(cy), alpha(C.paper_300, 0.9),
                            box_w=sf.s(cw))
            cy += cb.height / sf.ss
        y = cy + 34

        foot_top = H - 58 - T.meta[0] * 1.1 - 22
        src_top = foot_top - 28 - T.micro[0] * 1.26
        y = cp.eyebrow(sf, m, y, cw, st)
        y += 28
        room = src_top - 40 - y

        y, _ = cp.headline(sf, m, y, cw, st.headline, T.h2[0], T.h4[0] * 0.86,
                           room * (0.50 if st.deck else 0.72), max_lines=4,
                           leading=T.h2[1])
        if st.deck:
            y += 26
            cp.deck(sf, m, y, cw, st.deck, size=T.body[0],
                    max_lines=4, color=C.paper_200)

        cp.sourceline(sf, m, src_top, cw, st)
        cp.footer(sf, m, foot_top, cw,
                  right=f'{i + 1} / {len(edition.stories)}')
        grain(sf, Grade.grain, Grade.grain_shadow_bias)
        paths.append(sf.save(os.path.join(outdir, f'{prefix}_{i + 2:02d}.jpg')))

    # ── closing slide: every source, then the follow ─────────────────────
    sf = Surface(W, H, F.ss)
    cp.page_base(sf, 0.4)
    cp.horizon(sf, H * 0.82, 1.0)
    _progress(sf, m, cw, 52, n - 1, n)

    y = 52 + 30 + 24
    paste_logo(sf, (W - 132) / 2, y, 132, glow=0.20)
    y += 132 + 44
    b = typo.layout(Brand.name, typo.font('kn', sf.s(T.h2[0])), sf.s(cw),
                    T.h2[1], align='center')
    typo.draw_block(sf.img, b, sf.s(m), sf.s(y), Role.text_hi, box_w=sf.s(cw))
    y += b.height / sf.ss + 16
    typo.draw_text(sf.img, Brand.tagline, sf.s(W / 2), sf.s(y + 22),
                   typo.font('kn_var', sf.s(T.meta[0]), weight=600), C.gold_500,
                   anchor_x='c')
    y += 76

    rule(sf, m, y, m + cw, Role.hairline, 1.0)
    y += 34
    typo.draw_text(sf.img, Brand.sources_kn, sf.s(m), sf.s(y),
                   typo.font('kn_var', sf.s(T.micro[0]), weight=700), C.gold_500)
    y += 26
    seen: list[str] = []
    for st in edition.stories:
        for s_ in st.sources:
            if s_ not in seen:
                seen.append(s_)
    sb = typo.layout(' • '.join(seen),
                     typo.font('kn_var', sf.s(T.body_sm[0] * 0.92), weight=440),
                     sf.s(cw), 1.5)
    typo.draw_block(sf.img, sb, sf.s(m), sf.s(y), C.paper_200, box_w=sf.s(cw))
    y += sb.height / sf.ss + 34
    rule(sf, m, y, m + cw, Role.hairline, 1.0)

    foot_top = H - 58 - T.meta[0] * 1.1 - 22
    cy = foot_top - 118
    typo.draw_text(sf.img, 'ಪ್ರತಿದಿನದ ಕರಾವಳಿ ಸುದ್ದಿಗಾಗಿ', sf.s(W / 2), sf.s(cy),
                   typo.font('kn_var', sf.s(T.body_sm[0]), weight=460),
                   C.paper_200, anchor_x='c')
    typo.draw_text(sf.img, Brand.handle, sf.s(W / 2), sf.s(cy + 62),
                   typo.font('latin', sf.s(T.h3[0]), weight=760), C.gold_500,
                   anchor_x='c', tracking=0.01)
    # IT Rules 2021 Part III: a news publisher must name a Grievance Officer
    # and publish contact details. It also reinforces exactly the trust
    # positioning the rest of this system is built on.
    g = Brand.grievance_line()
    if g:
        typo.draw_text(sf.img, g, sf.s(W / 2), sf.s(foot_top - 26),
                       typo.font_for(g, 'kn_var', sf.s(T.nano[0]), weight=440),
                       Role.text_faint, anchor_x='c')
    cp.footer(sf, m, foot_top, cw, left=Brand.coverage,
              right=edition.date_kn, handle_gold=False)
    grain(sf, Grade.grain, Grade.grain_shadow_bias)
    paths.append(sf.save(os.path.join(outdir, f'{prefix}_{n:02d}_sources.jpg')))
    return paths
