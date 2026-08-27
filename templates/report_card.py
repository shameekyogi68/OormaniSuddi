"""Report card — the flagship 4:5 news post.\n\nAny story with an honest photograph. Copy decides the composition: a short\nheadline earns a bigger picture, a long one takes the space it needs and the\npicture yields. See STANDARDS.md §6."""
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



def _fit_editorial(sf: Surface, story: Story, cw: float, avail: float,
                   points: list[str], use_deck: bool, use_take: bool,
                   scale: float = 1.0):
    """Fit eyebrow + headline + deck + facts + takeaway into `avail` pixels.
    Returns a plan dict, or None if it will not fit legibly."""
    G = dict(eyebrow=30 * scale, head=24 * scale, deck=30 * scale, take=26 * scale)
    eyebrow_h = 34 * scale
    room = avail - eyebrow_h - G['eyebrow']
    if room <= 0:
        return None

    head_cap = room * (0.54 if not points else 0.46)
    h_blk = typo.fit(story.headline, 'kn', sf.s(T.h1[0] * scale), sf.s(T.h4[0] * scale),
                     sf.s(cw), sf.s(head_cap), T.h1[1], max_lines=4)
    used = h_blk.height / sf.ss

    d_blk = None
    if use_deck and story.deck:
        deck_cap = min(room * 0.19, T.deck[0] * scale * T.deck[1] * 2)
        d_blk = typo.fit(story.deck, 'kn_var', sf.s(T.deck[0] * scale),
                         sf.s(T.deck[0] * scale * 0.76), sf.s(cw),
                         sf.s(deck_cap), T.deck[1], weight=450, max_lines=2)
        if d_blk.height / sf.ss > deck_cap + 2:
            return None
        used += G['head'] + d_blk.height / sf.ss

    t_blk, take_h = None, 0.0
    if use_take and story.takeaway:
        f_t = typo.font('kn_var', sf.s(T.body_sm[0] * scale), weight=460)
        t_blk = typo.layout(story.takeaway, f_t, sf.s(cw - 48 * scale), T.body_sm[1])
        take_h = T.body_sm[0] * scale * 1.46 + t_blk.height / sf.ss + 14 * scale
        used += G['take'] + take_h

    f_blocks, facts_h, fact_size = [], 0.0, 0
    if points:
        facts_room = room - used - G['deck']
        gap = 34 * scale
        floor = int(T.body[0] * scale * 0.78)
        for s_ in range(int(T.body[0] * scale), floor - 1, -1):
            f = typo.font('kn_var', sf.s(s_), weight=440)
            cand = [typo.layout(p, f, sf.s(cw - 62 * scale), T.body[1]) for p in points]
            tot = sum(b.height / sf.ss for b in cand) + gap * (len(cand) - 1)
            if tot <= facts_room:
                f_blocks, facts_h, fact_size = cand, tot, s_
                break
        if not f_blocks:
            return None
        used += G['deck'] + facts_h

    total = eyebrow_h + G['eyebrow'] + used
    if total > avail + 1:
        return None
    return dict(G=G, eyebrow_h=eyebrow_h, head=h_blk, deck=d_blk,
                facts=f_blocks, fact_size=fact_size, take=t_blk,
                take_h=take_h, total=total, points=points)


# On these stories the advisory IS the story — the helpline number matters more
# to a reader in the rain than the third supporting fact does.
ALERT_CATEGORIES = {'weather', 'health', 'civic', 'breaking'}


# Editorial drop-priority. When a card cannot hold everything, this is the order
# in which a sub-editor would cut. Ordinarily the advisory goes first, then the
# standfirst, then facts from the bottom; the headline is never cut. On an alert
# the order inverts around the advisory.
def _variants(story: Story):
    n = len(story.points)
    keeps_advice = bool(story.takeaway) and story.category in ALERT_CATEGORIES

    yield (story.points, True, True)

    if keeps_advice:
        # cut facts and the standfirst before the number people need to call
        for k in range(n - 1, -1, -1):
            yield (story.points[:k], True, True)
        for k in range(n, -1, -1):
            yield (story.points[:k], False, True)
        yield (story.points, True, False)
    else:
        if story.takeaway:
            yield (story.points, True, False)
        if story.deck:
            yield (story.points, False, True)
            yield (story.points, False, False)
        for k in range(n - 1, 0, -1):
            yield (story.points[:k], True, True)
            yield (story.points[:k], True, False)

    yield ([], True, True)
    yield ([], True, False)


def report_card(story: Story, path: str, format_key: str = 'post') -> str:
    """The flagship 4:5 news card. Copy decides the composition."""
    story.validate()
    F = fmt(format_key)
    W, H = F.w, F.h
    m = Grid.margin
    cw = W - 2 * m

    sf = Surface(W, H, F.ss)
    cp.page_base(sf)

    foot_top = H - 58 - T.meta[0] * 1.1 - 22
    src_top = foot_top - 30 - T.micro[0] * 1.26
    content_bottom = src_top - 36

    # The credit becomes a proper caption line sitting on the page just under
    # the picture, not floating over it — always legible, unmistakably editorial.
    # A story with no honest photograph still gets a picture — a plate that is
    # visibly a graphic. Every post in the feed then has something to look at,
    # without anyone being shown a stock photo dressed as reporting.
    has_photo = bool(story.photo and os.path.exists(story.photo.path))
    plate_credit = '' if has_photo else 'ಗ್ರಾಫಿಕ್ಸ್  •  ಊರ್ಮನಿ ಸುದ್ದಿ'

    cap_blk = None
    if story.photo and story.credit_line:
        cap_blk = typo.layout(story.credit_line,
                              typo.font('kn_var', sf.s(T.micro[0]), weight=420),
                              sf.s(cw), 1.34)
    if cap_blk is None and plate_credit:
        cap_blk = typo.layout(plate_credit,
                              typo.font('kn_var', sf.s(T.micro[0]), weight=420),
                              sf.s(cw), 1.34)
    CREDIT_GAP = (18 + cap_blk.height / sf.ss + 34) if cap_blk else 46
    # A plate is an illustration, not a photograph: it should sit as a band at
    # the head of the card, not dominate it the way a good picture earns to.
    PB_HI = int(H * (0.62 if has_photo else 0.36))
    PB_LO = int(H * 0.355)
    plan = photo_bottom = None
    for pts, use_deck, use_take in _variants(story):
        for pb in range(PB_HI, PB_LO - 1, -8):
            got = _fit_editorial(sf, story, cw,
                                 content_bottom - (pb + CREDIT_GAP),
                                 pts, use_deck, use_take)
            if got:
                plan, photo_bottom = got, pb
                break
        if plan:
            break
    if not plan:                       # headline-only fallback; always succeeds
        photo_bottom = PB_LO
        plan = _fit_editorial(sf, story, cw,
                              content_bottom - (photo_bottom + CREDIT_GAP),
                              [], False, False)

    # Any leftover goes to the picture, so no card ends with a dead gap.
    slack = (content_bottom - (photo_bottom + CREDIT_GAP)) - plan['total']
    if slack > 0:
        ceiling = int(H * (0.72 if has_photo else 0.38))
        photo_bottom += min(slack, max(0, ceiling - photo_bottom))
    stack_top = photo_bottom + CREDIT_GAP
    G = plan['G']

    # ── photograph ───────────────────────────────────────────────────────
    pb_box = photo_bottom + 30
    if has_photo:
        place_photo(sf, story.photo.path, (0, 0, W, pb_box),
                    focal=story.photo.focal, strength=1.0,
                    fade_bottom=1.0 - (photo_bottom * 0.60) / pb_box)
        scrim(sf, 0, 250, C.ink_950, 0.84, 0.0, curve=1.5)
        # Just enough veil over the lower picture to seat the caption.
        scrim(sf, photo_bottom * 0.50, pb_box, C.ink_950, 0.0, 0.55, curve=1.8)
    else:
        # No bottom scrim: the plate's own sea already resolves to the page
        # colour, so it dissolves by construction. Scrimming it only erased the
        # ruled-sea texture that makes it look drawn rather than empty.
        editorial_plate(sf, (0, 0, W, pb_box), category(story.category),
                        seed=story.headline)
        scrim(sf, 0, 250, C.ink_950, 0.66, 0.0, curve=1.5)

    cp.masthead(sf, m, 52, cw, right_top=story.date_kn,
                right_bot=f'{story.day_kn} • {story.time_kn}',
                on_photo=True)

    if cap_blk is not None:
        typo.draw_block(sf.img, cap_blk, sf.s(m), sf.s(photo_bottom + 18),
                        alpha(C.paper_300, 0.92), box_w=sf.s(cw))

    # ── editorial stack ──────────────────────────────────────────────────
    y = stack_top
    y = cp.eyebrow(sf, m, y, cw, story)
    y += G['eyebrow']

    typo.draw_block(sf.img, plan['head'], sf.s(m), sf.s(y), Role.text_hi, box_w=sf.s(cw))
    y += plan['head'].height / sf.ss

    if plan['deck'] is not None:
        y += G['head']
        typo.draw_block(sf.img, plan['deck'], sf.s(m), sf.s(y), C.paper_200,
                        box_w=sf.s(cw))
        y += plan['deck'].height / sf.ss

    if plan['facts']:
        y += G['deck']
        rule(sf, m, y - G['deck'] * 0.52, m + cw, Role.hairline, 1.0)
        gap = 34
        f_num = typo.font('latin', sf.s(plan['fact_size'] * 0.80), weight=760)
        for i, b in enumerate(plan['facts']):
            if i:
                rule(sf, m, y - gap / 2, m + cw, Role.hairline_soft, 1.0)
            bl = y + b.first_rise / sf.ss * 0.94
            nw = typo.draw_text(sf.img, f'{i + 1:02d}', sf.s(m), sf.s(bl), f_num,
                                C.gold_500, tracking=0.02) / sf.ss
            rule(sf, nw + 9, bl - plan['fact_size'] * 0.22, m + 46,
                 alpha(C.gold_500, 0.5), 1.5)
            typo.draw_block(sf.img, b, sf.s(m + 62), sf.s(y), C.paper_100,
                            box_w=sf.s(cw - 62))
            y += b.height / sf.ss + gap
        y -= gap

    if plan['take'] is not None:
        y += G['take']
        cp.takeaway(sf, m, y, cw, story.takeaway)

    cp.sourceline(sf, m, src_top, cw, story)
    cp.footer(sf, m, foot_top, cw, left=Brand.handle,
              right=story.dateline or Brand.coverage)

    grain(sf, Grade.grain, Grade.grain_shadow_bias)
    return sf.save(path)
