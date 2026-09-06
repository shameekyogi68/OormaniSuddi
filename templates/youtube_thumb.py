"""YouTube thumbnail — 1280×720, designed to survive a 6× reduction.

In a feed this is about 210 px wide, so the headline is set enormous and capped
at a few words. Type that looks right at full size is unreadable where it
actually matters — and a thumbnail nobody can read is a thumbnail nobody clicks,
which is the whole job.

It is built in the SAME frame language as the 16:9 bulletin it fronts: an ink
column on the left carrying the type, the photograph full-height on the right,
a gold seam between them. Two reasons, both practical:

  * the type sits on solid ground rather than on picture detail, so it is
    legible by construction instead of by luck with a particular photograph;
  * the thumbnail and the first frame of the video are recognisably the same
    publication, which is what makes a channel look like a channel.

An earlier cut laid the photo full-bleed, set the hook on ONE line shrunk to
fit, and put the deck under it. At feed size the deck was gone entirely and a
long hook had shrunk to roughly 40px — about 6px on screen. Hence the line cap
and the word warning below: this template would rather refuse to be clever than
render something that cannot be read.
"""
from __future__ import annotations

import os

from brand import typo, components as cp
from brand.surface import Surface, panel, vrule, place_photo, grain
from brand.tokens import C, Role, T, Grid, fmt, category, alpha, Grade, Brand
from brand.content import Story, ContentError, asserts_guilt

# In a YouTube feed a thumbnail is about 210 px wide. Past roughly seven words
# the Kannada stops being readable there, whatever size it looks at full scale.
THUMB_WORD_LIMIT = 7

# The type column, as a fraction of the frame. Wider than the bulletin's 0.46:
# a thumbnail carries a handful of very large words rather than a headline and
# a deck, and those words need the measure.
PANEL_W = 0.55

# The floor the hook is allowed to shrink to. 76px at 1280 is ~12px at feed
# size, which is about as small as Kannada survives. Below this the answer is
# a shorter hook, not smaller type — so `fit` stops here and the warning above
# tells the editor which one they have.
HOOK_HI, HOOK_LO = 152, 76


def youtube_thumb(story: Story, path: str, hook: str = '',
                  format_key: str = 'thumb') -> str:
    story.validate()
    F = fmt(format_key)
    W, H = F.w, F.h
    sl, st_, sr, sb = F.safe

    text = (hook or story.headline).strip()

    # `hook` REPLACES the headline on the thumbnail, so it inherits the
    # headline's exposure without inheriting its guard. Story.validate()
    # cannot see it — it is not a Story field — and the guilt check it runs
    # over `headline` and `reel_line` exists precisely because those travel
    # alone "in a thumbnail, a forward, a search result". This is that
    # thumbnail. An editor reaching for a punchier line under deadline is
    # exactly who the check is for, so it is enforced here, on the same terms
    # and with no way round it. See DECISIONS.md D29–D30.
    if story.category in ('crime', 'breaking') and not story.convicted:
        hits = asserts_guilt(text)
        if hits:
            raise ContentError(
                f'the thumbnail hook states guilt as fact ({", ".join(hits)}) '
                'about someone who has not been convicted. The hook replaces '
                'the headline on the thumbnail and is read entirely on its own, '
                'so the headline being careful does not cover it. Rewrite the '
                'hook as an allegation: ಆರೋಪ / ಆರೋಪಿ / ಶಂಕಿತ, or ಪ್ರಕರಣ ದಾಖಲು.')

    words = text.split()
    if len(words) > THUMB_WORD_LIMIT:
        print(f'  ⚠ thumbnail text is {len(words)} words; at feed size only about '
              f'{THUMB_WORD_LIMIT} stay legible. Pass hook="…" with a shorter line.')

    sf = Surface(W, H, F.ss)
    cp.page_base(sf, 0.5)

    pw = int(W * PANEL_W)
    pad = 30

    # ── The photograph, full height on the right ─────────────────────────────
    # Full height rather than full bleed then half-covered: the subject of a
    # news photograph is usually in the middle of the frame, and covering the
    # middle is what the old full-bleed layout did. Same reasoning as D38.
    if story.photo and os.path.exists(story.photo.path):
        place_photo(sf, story.photo.path, (pw, 0, W, H),
                    focal=story.photo.focal, strength=1.0)

    # The column, then a sliver of light on the seam and the brand rule — so
    # the type has its own ground and the join is a designed edge rather than
    # a place where the picture happens to stop.
    panel(sf, (0, 0, pw, H), alpha(C.ink_950, 0.988))
    vrule(sf, pw - 2, 0, H, alpha(C.paper_50, 0.16), 1.0)
    vrule(sf, pw, 0, H, C.gold_500, 3.0)

    cw = pw - sl - pad

    # ── Column furniture ─────────────────────────────────────────────────────
    # On solid ground none of this needs a shadow to survive.
    bottom = cp.masthead(sf, sl, st_, cw, on_photo=False, scale=0.62,
                         rule_below=False)

    eb_y = bottom + 24
    # The location is set at the foot in the accent instead, so it is not
    # printed twice down the same column.
    cp.eyebrow(sf, sl, eb_y, cw, story, scale=1.05, on_photo=False,
               show_location=False)

    # ── The hook ─────────────────────────────────────────────────────────────
    # Three lines is the cap. A fourth line at this measure means the type has
    # come down far enough that the feed swallows it.
    foot_h = int(T.meta[0] * 1.15 * 1.4)
    top = eb_y + 34 * 1.05 + 26
    room = (H - sb - foot_h - 18) - top

    b = typo.fit(text, 'kn', sf.s(HOOK_HI), sf.s(HOOK_LO), sf.s(cw),
                 sf.s(room), 1.16, max_lines=3)
    # Optically centred in the space it has. A video scene top-aligns so the
    # headline does not hop about from scene to scene, but a thumbnail is one
    # frame on its own — leaving a short hook hanging with a third of the
    # column empty under it just looks unfinished.
    slack = max(0.0, room - b.height / sf.ss)
    typo.draw_block(sf.img, b, sf.s(sl), sf.s(top + slack * 0.42), Role.text_hi,
                    box_w=sf.s(cw))

    # ── Foot of the column: where, and who ───────────────────────────────────
    # The location is the reason a local viewer clicks, so it is set in the
    # accent rather than buried in dim grey.
    fy = H - sb
    # …unless the hook already says where. A good hook usually leads with the
    # town, and printing it again two inches below is the kind of small
    # duplication that makes a card look automatic. Fall back to the coverage
    # word so the corner is never empty.
    place = story.location or Brand.coverage
    if story.location and story.location in text:
        place = Brand.coverage if Brand.coverage not in text else ''
    if place:
        typo.draw_text(sf.img, place, sf.s(sl), sf.s(fy),
                       typo.font('kn_var', sf.s(int(T.meta[0] * 1.15)), weight=700),
                       C.gold_400)
    typo.draw_text(sf.img, Brand.handle, sf.s(pw - pad), sf.s(fy),
                   typo.font('latin', sf.s(int(T.meta[0] * 1.05)), weight=740),
                   alpha(C.paper_200, 0.92), anchor_x='r', tracking=0.015)

    grain(sf, Grade.grain * 0.7, Grade.grain_shadow_bias)
    return sf.save(path)


__all__ = ['youtube_thumb']
