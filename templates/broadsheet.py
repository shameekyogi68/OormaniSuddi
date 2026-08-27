"""Broadsheet — the day's edition as a single front page."""
from __future__ import annotations

import os
from PIL import Image

from brand import typo, components as cp
from brand.surface import (Surface, scrim, rule, vrule, panel, place_photo, grain,
                           radial_glow, paste_logo, duotone, house_grade, cover)
from brand.tokens import (C, Role, T, Grid, fmt, category, alpha, Grade,
                          Brand,
                          Brand)
from brand.content import Story, Edition



def broadsheet(edition: Edition, path: str) -> str:
    edition.validate()
    F = fmt('broadsheet')
    W, H = F.w, F.h
    m = 64
    cw = W - 2 * m
    sf = Surface(W, H, F.ss)
    cp.page_base(sf, 0.45)

    lead = edition.stories[0]
    rest = edition.stories[1:]

    # ── masthead: the serif lockup, used only here ───────────────────────
    y = 56
    paste_logo(sf, m, y, 76)
    typo.draw_text(sf.img, Brand.name, sf.s(m + 94), sf.s(y + 46),
                   typo.font('kn_serif', sf.s(52)), Role.text_hi)
    typo.draw_text(sf.img, Brand.tagline, sf.s(m + 96), sf.s(y + 76),
                   typo.font('kn_var', sf.s(T.micro[0]), weight=600), C.gold_500)
    typo.draw_text(sf.img, edition.date_kn, sf.s(m + cw), sf.s(y + 40),
                   typo.font('kn_var', sf.s(T.meta[0]), weight=650), Role.text,
                   anchor_x='r')
    typo.draw_text(sf.img, f'{edition.strapline}  •  ಆವೃತ್ತಿ {edition.edition_no}',
                   sf.s(m + cw), sf.s(y + 74),
                   typo.font('kn_var', sf.s(T.micro[0]), weight=460), Role.text_dim,
                   anchor_x='r')
    y += 96
    rule(sf, m, y, m + cw, alpha(C.gold_500, 0.55), 2.0)
    y += 4
    rule(sf, m, y + 5, m + cw, alpha(C.gold_500, 0.28), 1.0)
    y += 34

    # ── lead story ───────────────────────────────────────────────────────
    y = cp.eyebrow(sf, m, y, cw, lead)
    y += 26
    y, _ = cp.headline(sf, m, y, cw, lead.headline, 74, 46, H * 0.19,
                       max_lines=3, leading=1.22)
    y += 24
    if lead.photo and os.path.exists(lead.photo.path):
        ph = H * 0.26
        place_photo(sf, lead.photo.path, (m, y, m + cw, y + ph),
                    focal=lead.photo.focal, radius=Grid.radius_soft)
        y += ph + 14
        if lead.credit_line:
            cb = typo.layout(lead.credit_line,
                             typo.font('kn_var', sf.s(T.nano[0]), weight=420),
                             sf.s(cw), 1.34)
            typo.draw_block(sf.img, cb, sf.s(m), sf.s(y), alpha(C.paper_300, 0.9),
                            box_w=sf.s(cw))
            y += cb.height / sf.ss
        y += 22
    if lead.deck:
        y = cp.deck(sf, m, y, cw, lead.deck, size=T.body[0], max_lines=3,
                    color=C.paper_200) + 22

    rule(sf, m, y, m + cw, Role.hairline, 1.0)
    y += 30

    # ── secondary stories, two columns ───────────────────────────────────
    foot_top = H - 52 - T.meta[0] * 1.1 - 22
    if rest:
        cols = 2
        gut = 40
        colw = (cw - gut * (cols - 1)) / cols
        block_top = y
        # Leave real room for the source line that sits above the footer rule;
        # a column that runs into it is the classic broadsheet collision.
        avail = foot_top - 92 - y
        items = rest[:4]

        # Measure first, so rows are as tall as their content rather than a
        # fixed fraction — the difference between a page and a template.
        # Cap each headline so a whole CELL fits its share of the block —
        # capping only the headline lets the kicker and the byline push the
        # last row straight through the footer.
        nrows = (len(items) + cols - 1) // cols
        CELL_FURNITURE = 36 + 44
        cell_cap = max(96.0, (avail - 30 * (nrows - 1)) / nrows - CELL_FURNITURE)

        cells = []
        for st in items:
            hb = typo.fit(st.headline, 'kn', sf.s(38), sf.s(24), sf.s(colw),
                          sf.s(cell_cap), 1.26, max_lines=4)
            cells.append((st, hb, CELL_FURNITURE + hb.height / sf.ss))

        rows = [cells[k:k + cols] for k in range(0, len(cells), cols)]
        row_h = [max(c[2] for c in r) for r in rows]
        slack = avail - sum(row_h) - 30 * (len(rows) - 1)
        pad = max(0.0, slack / max(1, len(rows) - 1)) if len(rows) > 1 else 0.0

        cy = block_top
        for r_i, row in enumerate(rows):
            if r_i:
                rule(sf, m, cy - 15, m + cw, Role.hairline_soft, 1.0)
            for c_i, (st, hb, ch) in enumerate(row):
                cx = m + c_i * (colw + gut)
                cat = category(st.category)
                panel(sf, [cx, cy, cx + 4, cy + 22], cat['rail'])
                typo.draw_text(sf.img, cat['kn'], sf.s(cx + 14), sf.s(cy + 19),
                               typo.font('kn_var', sf.s(T.nano[0]), weight=740),
                               C.gold_500)
                typo.draw_block(sf.img, hb, sf.s(cx), sf.s(cy + 36), Role.text_hi,
                                box_w=sf.s(colw))
                ly = cy + 36 + hb.height / sf.ss + 22
                typo.draw_text(sf.img, f'{st.location}  •  {st.status_kn}',
                               sf.s(cx), sf.s(ly),
                               typo.font('kn_var', sf.s(T.nano[0]), weight=480),
                               Role.text_faint)
            cy += row_h[r_i] + ((30 + pad) if r_i < len(rows) - 1 else 0)
        for c_i in range(1, cols):
            vrule(sf, m + c_i * (colw + gut) - gut / 2, block_top - 4,
                  min(cy - 6, foot_top - 100), Role.hairline, 1.0)

    seen: list[str] = []
    for st in edition.stories:
        for s_ in st.sources:
            if s_ not in seen:
                seen.append(s_)
    f_src = typo.font('kn_var', sf.s(T.nano[0]), weight=440)
    typo.draw_text(sf.img, typo.ellipsize('ಮೂಲ: ' + ' • '.join(seen), f_src,
                                          sf.s(cw)),
                   sf.s(m), sf.s(foot_top - 30), f_src, Role.text_faint)
    cp.footer(sf, m, foot_top, cw, right=Brand.coverage)
    grain(sf, Grade.grain, Grade.grain_shadow_bias)
    return sf.save(path)
