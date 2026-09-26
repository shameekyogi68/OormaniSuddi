"""ಸುದ್ದಿ ಸಾರ — the day's text bulletin (D92).

Index cover → one slide per story → sources and follow. 4:5, Paper & Red,
and no pictures, ever: a photograph on a saara story is not drawn. That is the
format's promise — the words, quickly, with where they came from.
"""
from __future__ import annotations

import os

from brand import paper as pp
from brand import typo
from brand.content import Edition
from brand.tokens import Brand, Paper as P, fmt

TITLE = 'ಸುದ್ದಿ ಸಾರ'


def _header(sf, date_kn: str) -> float:
    """The running head on every inside slide. Returns its bottom."""
    m = P.margin
    pp.bug(sf, m, 44, 28)
    pp.meta(sf, sf.w - m, 82, f'{TITLE}  ·  {date_kn}', anchor='r')
    y = 124
    pp._rect(sf, (m, y, sf.w - m, y + 3), pp.INK)
    pp.accent(sf, m, y + 7, 160, 6)
    return y + 13


def _points_fit(sf, items: list[str], x: float, y: float, w: float,
                max_h: float) -> int:
    """The largest body size at which every point fits `max_h`."""
    for size in range(P.body - 2, 31, -2):
        f = typo.font('kn_var', sf.s(size), weight=520)
        h = 0.0
        for t in items:
            h += typo.layout(t, f, sf.s(w), P.body_lead).height / sf.ss + 26
        if h <= max_h:
            return size
    return 32


def saara(edition: Edition, outdir: str, prefix: str = 'saara') -> list[str]:
    """Render the ಸುದ್ದಿ ಸಾರ set. `edition` carries the saara stories only."""
    edition.validate()
    F = fmt('post')
    W, H, m = F.w, F.h, P.margin
    cw = W - 2 * m
    stories = edition.stories
    n = len(stories) + 2
    os.makedirs(outdir, exist_ok=True)
    paths: list[str] = []

    # ── cover: the index ────────────────────────────────────────────────────
    sf = pp.page(W, H)
    pp.bug(sf, m, 52)
    pp.meta(sf, W - m, 92, edition.date_kn, anchor='r')
    title = typo.layout(TITLE, typo.font('kn', weight=pp.HEAD_WEIGHT, size=sf.s(120)), sf.s(cw), 1.1)
    typo.draw_block(sf.img, title, sf.s(m), sf.s(150), pp.INK)
    pp.meta(sf, m, 352, f'ಇಂದಿನ {len(stories)} ಮುಖ್ಯ ಸುದ್ದಿಗಳು, ಒಂದೇ ನೋಟದಲ್ಲಿ',
            size=34, weight=520)
    y = 396
    pp._rect(sf, (m, y, W - m, y + 3), pp.INK)
    pp.accent(sf, m, y + 7, 160, 6)
    top, bottom = y + 44, H - P.footer_h - 28
    indent = 84
    for size in range(44, 29, -2):          # one size for every entry
        f = typo.font('kn', weight=pp.HEAD_WEIGHT, size=sf.s(size))
        blocks = [typo.layout(s.headline, f, sf.s(cw - indent), 1.26)
                  for s in stories]
        need = sum(b.height / sf.ss + 36 + 34 for b in blocks) - 34
        if need <= bottom - top:
            break
    y = top
    for i, (st, b) in enumerate(zip(stories, blocks), 1):
        pp.chip(sf, m, y + 2, i, 26)
        place = (st.location or '').strip() or Brand.coverage
        pp.meta(sf, m + indent, y + 22, place, pp.RED, size=24, weight=700)
        yb = typo.draw_block(sf.img, b, sf.s(m + indent), sf.s(y + 36), pp.INK,
                             box_w=sf.s(cw - indent)) / sf.ss
        y = yb + 18
        if i < len(stories):
            pp._rect(sf, (m + indent, y, W - m, y + 2), pp.RULE)
            y += 16
    pp.footer(sf, f'1/{n}')
    paths.append(sf.save(os.path.join(outdir, f'{prefix}_01_cover.jpg')) or
                 os.path.join(outdir, f'{prefix}_01_cover.jpg'))

    # ── one slide per story ─────────────────────────────────────────────────
    for i, st in enumerate(stories, 1):
        sf = pp.page(W, H)
        y = _header(sf, edition.date_kn) + 44
        pp.kicker(sf, m, y, st)
        pp.meta(sf, W - m, y + 30, f'{i:02d} / {len(stories):02d}',
                pp.GOLD_TYPE, size=30, weight=720, anchor='r')
        y = pp.headline(sf, m, y + 76, cw, st.headline, 380, hi=84, lo=60,
                        ink_only=pp.ink_only(st))
        pp.accent(sf, m, y + 30)
        y += 30 + 8 + 40
        items = [p for p in st.points if p.strip()] or ([st.deck] if st.deck else [])
        src_base = H - P.footer_h - 30
        if items:
            size = _points_fit(sf, items, m + 36, y, cw - 36, src_base - 40 - y)
            for t in items:
                pp._rect(sf, (m, y + size * 0.5, m + 14, y + size * 0.5 + 14),
                         pp.GOLD_MARK)
                y = pp.body(sf, m + 36, y, cw - 36, t, size=size, weight=520,
                            fill=pp.BODY) + 26
        pp.meta(sf, m, src_base, st.source_line, max_w=cw)
        pp.footer(sf, f'{i + 1}/{n}')
        p = os.path.join(outdir, f'{prefix}_{i + 1:02d}.jpg')
        sf.save(p)
        paths.append(p)

    # ── sources & follow ────────────────────────────────────────────────────
    sf = pp.page(W, H)
    _header(sf, edition.date_kn)
    pp.roundlogo(sf, (W - 200) / 2, 200, 200)
    t = typo.layout('ಇಂದಿನ ಸುದ್ದಿ ಸಾರ ಇಷ್ಟೇ', typo.font('kn', weight=pp.HEAD_WEIGHT, size=sf.s(64)),
                    sf.s(cw), 1.2, align='center')
    yb = typo.draw_block(sf.img, t, sf.s(m), sf.s(446), pp.INK,
                         box_w=sf.s(cw)) / sf.ss
    pp.meta(sf, W / 2, yb + 56, 'ಉಪಯುಕ್ತ ಅನಿಸಿದರೆ ಸೇವ್ ಮಾಡಿ, ಊರಿನವರಿಗೆ ಕಳುಹಿಸಿ',
            size=34, anchor='c')
    y = yb + 110
    pp._rect(sf, (m, y, W - m, y + 3), pp.INK)
    pp.meta(sf, m, y + 56, Brand.sources_kn, pp.GOLD_TYPE, size=30, weight=720)
    y += 110
    for i, st in enumerate(stories, 1):
        url = next((u for u in st.source_urls if u), '')
        where = url.split('/')[2] if url.startswith('http') else ''
        line = ' · '.join(x for x in (' / '.join(st.sources), where) if x)
        pp.meta(sf, m, y, f'{i:02d}', pp.GREY, size=28, weight=720)
        pp.meta(sf, m + 64, y, line, pp.BODY, size=28, max_w=cw - 64)
        y += 50
    pp.grievance(sf, H - P.footer_h - 30)
    pp.footer(sf, f'{n}/{n}')
    p = os.path.join(outdir, f'{prefix}_{n:02d}_sources.jpg')
    sf.save(p)
    paths.append(p)
    return paths
