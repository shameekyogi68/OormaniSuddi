"""ಮುಖ್ಯ ಸುದ್ದಿ — one breaking or top story, as a 4:5 carousel (D92).

Photo cover → ಏನಾಗಿದೆ? → source and corrections. Always a picture: a real
one first, and a generated one only after the editor was asked and said
generate (photo_plan "ai", photo.approved_by). No picture, no render.
"""
from __future__ import annotations

import os

from brand import paper as pp
from brand import typo
from brand.content import ContentError, Story, url_host
from brand.tokens import Brand, Paper as P, category, fmt


def _points_size(sf, items, w, max_h) -> int:
    for size in range(P.body + 6, 33, -2):
        f = typo.font('kn_var', sf.s(size), weight=600)
        h = sum(typo.layout(t, f, sf.s(w), P.body_lead).height / sf.ss + 62
                for t in items)
        if h <= max_h:
            return size
    return 34


def mukhya(story: Story, outdir: str, k: int = 1, prefix: str = 'mukhya'
           ) -> list[str]:
    """Render one story's set. Returns three paths."""
    story.validate()
    if not story.photo or not os.path.exists(story.photo.path or ''):
        raise ContentError(
            'ಮುಖ್ಯ ಸುದ್ದಿ needs a picture (IMG-04). Ask the editor: a real '
            'photograph, or generate one? Record the answer in photo_plan.')
    F = fmt('post')
    W, H, m = F.w, F.h, P.margin
    cw = W - 2 * m
    os.makedirs(outdir, exist_ok=True)
    stem = f'{prefix}_{k}'
    breaking = story.category == 'breaking' and story.is_breaking
    paths: list[str] = []

    # ── cover ──────────────────────────────────────────────────────────────
    sf = pp.page(W, H)
    ph = P.photo_4x5
    pp.photo(sf, story.photo, (0, 0, W, ph))
    pp.sunline(sf, ph)
    pp.bug(sf, m, 52)
    y = pp.kicker(sf, m, ph + 52, story, breaking=breaking)
    bottom = H - P.footer_h - 64
    y = pp.headline(sf, m, y + 28, cw, story.headline, bottom - y - 28,
                    ink_only=pp.ink_only(story))
    pp.meta(sf, m, min(y + 46, H - P.footer_h - 22), story.source_line,
            max_w=cw)
    pp.edge_tab(sf, P.photo_4x5 / 2)
    pp.footer(sf, '1/3', 'ಏನಾಗಿದೆ?', seam=(False, True))
    paths.append(os.path.join(outdir, f'{stem}_01_cover.jpg'))
    sf.save(paths[-1])

    # ── ಏನಾಗಿದೆ? ───────────────────────────────────────────────────────────
    sf = pp.page(W, H)
    pp.bug(sf, m, 44, 28)
    place = (story.location or '').strip() or Brand.coverage
    pp.meta(sf, W - m, 82, category(story.category)['kn']
            if pp.leads_with_place(story)
            else f'{category(story.category)["kn"]}  /  {place}', anchor='r')
    t = typo.layout('ಏನಾಗಿದೆ?', typo.font('kn', weight=pp.HEAD_WEIGHT, size=sf.s(80)), sf.s(cw), 1.2)
    yb = typo.draw_block(sf.img, t, sf.s(m), sf.s(176), pp.INK) / sf.ss
    pp.accent(sf, m, yb + 26)
    y = yb + 26 + 8 + 56
    items = [p for p in story.points if p.strip()] or (
        [story.deck] if story.deck else [])
    tail = story.takeaway.strip()
    room = H - P.footer_h - 40 - y - (150 if tail else 0)
    size = _points_size(sf, items, cw - 96, room)
    for i, text in enumerate(items, 1):
        pp.chip(sf, m, y + 2, i, 30)
        y = pp.body(sf, m + 96, y, cw - 96, text, size=size, weight=600) + 30
        if i < len(items):
            pp._rect(sf, (m + 96, y, W - m, y + 2), pp.RULE)
            y += 32
    if tail:
        y += 20
        pp._rect(sf, (m, y, m + 6, y + 96), pp.GOLD)
        pp.body(sf, m + 28, y, cw - 28, tail, size=36, weight=700,
                fill=pp.BODY, max_h=110, lo=28)
    pp.landing(sf, P.photo_4x5 / 2)          # the cover's tab sits on its photo
    pp.edge_tab(sf)
    pp.footer(sf, '2/3', 'ಮೂಲ', seam=(True, True))
    paths.append(os.path.join(outdir, f'{stem}_02_points.jpg'))
    sf.save(paths[-1])

    # ── source & corrections ───────────────────────────────────────────────
    sf = pp.page(W, H)
    pp.roundlogo(sf, (W - 240) / 2, 150, 240)
    tl = typo.layout(Brand.tagline.replace('  •  ', ' · '),
                     typo.font('kn', weight=pp.HEAD_WEIGHT, size=sf.s(56)), sf.s(cw), 1.2, align='center')
    yb = typo.draw_block(sf.img, tl, sf.s(m), sf.s(446), pp.INK,
                         box_w=sf.s(cw)) / sf.ss
    pp.meta(sf, W / 2, yb + 58, f'{Brand.follow_kn} — {Brand.handle}',
            size=32, anchor='c', max_w=cw)
    y = yb + 120
    pp._rect(sf, (m, y, W - m, y + 3), pp.INK)
    y += 60
    url = next((u for u in story.source_urls if u), '')
    rows = [('ಮೂಲ', ' · '.join(story.sources)),
            ('ಲಿಂಕ್', url_host(url) or 'ಸ್ವಂತ ವರದಿ'),
            ('ಚಿತ್ರ', story.photo.disclosure),
            ('ತಿದ್ದುಪಡಿ', 'ತಪ್ಪು ಕಂಡರೆ ತಿಳಿಸಿ — ಪರಿಶೀಲಿಸಿ ಸರಿಪಡಿಸುತ್ತೇವೆ')]
    if Brand.whatsapp_url:
        rows.append(('ವಾಟ್ಸ್‌ಆ್ಯಪ್', Brand.whatsapp_url.replace('https://', '')))
    for key, val in rows:
        pp.meta(sf, m, y, key, pp.GOLD_TYPE, size=30, weight=720)
        pp.meta(sf, m + 200, y, val, pp.INK, size=30, max_w=cw - 200)
        pp._rect(sf, (m, y + 24, W - m, y + 25), pp.RULE)
        y += 68
    pp.grievance(sf, H - P.footer_h - 30)
    pp.landing(sf)
    pp.footer(sf, '3/3', seam=(True, False))
    paths.append(os.path.join(outdir, f'{stem}_03_source.jpg'))
    sf.save(paths[-1])
    return paths
