"""ಸುದ್ದಿ ಸಾರ — the day's text bulletin (D92).

Front-page cover (the lead story + one-line teasers, D103) → one slide per
story → sources and follow. 4:5, Paper & Red,
and no pictures, ever: a photograph on a saara story is not drawn. That is the
format's promise — the words, quickly, with where they came from.
"""
from __future__ import annotations

import os

from brand import paper as pp
from brand import typo
from brand.content import ContentError, Edition
from brand.tokens import Brand, Paper as P, category, fmt

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


SWIPE = 'ಪೂರ್ಣ ಸುದ್ದಿಗೆ ಸ್ವೈಪ್ ಮಾಡಿ'
BAR_H = 76


def _swipe_bar(sf, y: float):
    """The cover's call to swipe: a red bar across the foot of the slide.
    The first covers had none, and readers stopped at slide one."""
    m = P.margin
    pp._rect(sf, (m, y, sf.w - m, y + BAR_H), pp.RED)
    f = typo.font('kn', weight=pp.HEAD_WEIGHT, size=sf.s(34))
    typo.draw_text(sf.img, SWIPE, sf.s(m + 28), sf.s(y + BAR_H / 2 + 12), f,
                   pp.WHITE)
    pp.chevron(sf, sf.w - m - 44, y + BAR_H / 2, 30, pp.WHITE, 5)


# The cover (D103).
LEAD_HI = 124         # px, the largest a lead headline is set
TEASE_LABEL = 36      # "ಇನ್ನಷ್ಟು ಇಂದು"
TEASE_H = 62          # one teaser line
TEASE_GAP = 18        # the hairline and the air above a teaser


def _teaser(st) -> tuple[str, str]:
    """(place, the rest) for one teaser row: the headline's own place when it
    opens with one ("ಕೋಟ: …"), else the story's location, else its category."""
    a, b = pp.split_headline(st.headline)
    if b:
        return a.rstrip(':：').strip(), b
    place = (st.location or '').strip() or category(st.category)['kn']
    text = st.headline.strip()
    if text.startswith(place):
        text = text[len(place):].lstrip(' :：,-–')
    return place, text


def _one_line(text: str, f, max_w: float) -> str:
    """As much of `text` as fits on one line, cut at a word — never inside an
    akshara, where a cut shows a broken conjunct."""
    if typo.text_width(text, f) <= max_w:
        return text
    words = text.split()
    while len(words) > 1:
        words.pop()
        cand = ' '.join(words).rstrip(',;:–-') + '…'
        if typo.text_width(cand, f) <= max_w:
            return cand
    return ''


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

    # ── cover: ಮುಖಪುಟ — the lead story, then the rest as one-line teasers ──
    # D103. The index cover set every headline at the same weight: on a
    # six-story day it was a wall of bold text with nothing to look at first,
    # grey texture in the profile grid, and it gave the whole day away so
    # readers stopped at slide one (2026-09-27). Now the edition's FIRST story
    # leads, set as a headline; each other story is one line — its place in
    # red, then as much of the rest as fits, cut at a word. Its own slide
    # carries it in full.
    sf = pp.page(W, H)
    pp.bug(sf, m, 52)
    pp.meta(sf, W - m, 92, edition.date_kn, anchor='r')
    pp.meta(sf, m, 196, f'{TITLE}  ·  ಇಂದಿನ {len(stories)} ಸುದ್ದಿ', pp.RED,
            size=32, weight=760)
    pp._rect(sf, (m, 222, W - m, 225), pp.INK)
    pp.accent(sf, m, 229, 160, 6)

    lead, rest = stories[0], stories[1:]
    bottom = H - P.footer_h - 28 - BAR_H - 24
    rows_h = (TEASE_LABEL + len(rest) * (TEASE_H + TEASE_GAP)) if rest else 0
    teasers_top = bottom - rows_h                 # pinned above the swipe bar
    y = pp.kicker(sf, m, 268, lead)
    head_room = teasers_top - 44 - (y + 18)
    if head_room < 2 * pp.HEAD_FLOOR * P.head_lead:
        raise ContentError(
            'the ಸುದ್ದಿ ಸಾರ cover cannot hold the lead and every teaser — '
            'move a story to ಸ್ಪೀಡ್ ನ್ಯೂಸ್, or shorten the lead headline')
    # The lead takes the room the day leaves it: up to LEAD_HI on a light day,
    # down to the house floor on a full one.
    y = pp.headline(sf, m, y + 18, cw, lead.headline, head_room, hi=LEAD_HI,
                    lo=60, ink_only=pp.ink_only(lead))
    assert y + 44 <= teasers_top + 1, f'the lead overran the teasers by {y + 44 - teasers_top:.0f}px'

    if rest:
        y = teasers_top
        pp.meta(sf, m, y + 26, 'ಇನ್ನಷ್ಟು ಇಂದು', pp.GREY, size=26, weight=700)
        y += TEASE_LABEL
        fp = typo.font('kn', weight=pp.HEAD_WEIGHT, size=sf.s(34))
        fr = typo.font('kn_var', weight=600, size=sf.s(32))
        for st in rest:
            pp._rect(sf, (m, y, W - m, y + 2), pp.RULE)
            y += TEASE_GAP
            place, line = _teaser(st)
            wp = typo.text_width(place, fp) / sf.ss
            typo.draw_text(sf.img, place, sf.s(m), sf.s(y + 38), fp, pp.RED)
            if line:
                line = _one_line(line, fr, sf.s(cw - wp - 20))
                typo.draw_text(sf.img, line, sf.s(m + wp + 20), sf.s(y + 38),
                               fr, pp.BODY)
            y += TEASE_H
        assert y <= bottom + 1, f'the teasers overran the footer by {y - bottom:.0f}px'
    _swipe_bar(sf, H - P.footer_h - 28 - BAR_H)
    pp.edge_tab(sf)
    pp.footer(sf, f'1/{n}', seam=(False, True))
    p = os.path.join(outdir, f'{prefix}_01_cover.jpg')
    sf.save(p)
    paths.append(p)

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
        pp.meta(sf, m, src_base, st.source_line, max_w=cw * 0.55)
        nxt = stories[i] if i < len(stories) else None
        nxt_label = ('ಮುಂದೆ: ' + ((nxt.location or '').strip() or Brand.coverage)
                     if nxt else 'ಮೂಲಗಳು')
        pp.landing(sf)
        pp.edge_tab(sf)
        pp.footer(sf, f'{i + 1}/{n}', nxt_label, seam=(True, True))
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
    if pp.join_line():
        pp.meta(sf, W / 2, yb + 104, pp.join_line(), pp.GOLD_TYPE, size=28,
                weight=640, anchor='c', max_w=cw)
    y = yb + 140
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
    pp.landing(sf)
    pp.footer(sf, f'{n}/{n}', seam=(True, False))
    p = os.path.join(outdir, f'{prefix}_{n:02d}_sources.jpg')
    sf.save(p)
    paths.append(p)
    return paths
