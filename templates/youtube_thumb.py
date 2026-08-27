"""YouTube thumbnail — 1280×720, designed to survive a 6× reduction.\n\nIn a feed this is about 210 px wide, so the headline is set enormous and capped\nat a few words. Type that looks right at full size is unreadable where it\nactually matters."""
from __future__ import annotations

import os
from PIL import Image

from brand import typo, components as cp
from brand.surface import (Surface, scrim, rule, vrule, panel, place_photo, grain,
                           radial_glow, paste_logo, duotone, house_grade, cover)
from brand.tokens import (C, Role, T, Grid, fmt, category, alpha, Grade,
                          Brand)
from brand.content import Story, Edition

# In a YouTube feed a thumbnail is about 210 px wide. Past roughly seven words
# the Kannada stops being readable there, whatever size it looks at full scale.
THUMB_WORD_LIMIT = 7



def youtube_thumb(story: Story, path: str, hook: str = '',
                  format_key: str = 'thumb') -> str:
    story.validate()
    F = fmt(format_key)
    W, H = F.w, F.h
    sl, st_, sr, sb = F.safe
    text = (hook or story.headline).strip()
    words = text.split()
    if len(words) > THUMB_WORD_LIMIT:
        print(f'  ⚠ thumbnail text is {len(words)} words; at feed size only about '
              f'{THUMB_WORD_LIMIT} stay legible. Pass hook="…" with a shorter line.')

    sf = Surface(W, H, F.ss)
    cp.page_base(sf, 0.5)

    split = W * 0.46
    if story.photo and os.path.exists(story.photo.path):
        place_photo(sf, story.photo.path, (0, 0, W, H), focal=story.photo.focal,
                    strength=1.0)
        # Fade the picture out to the left so the type sits on clean ink.
        lay = sf.layer()
        import numpy as _np
        ramp = _np.zeros((1, W * F.ss, 4), dtype=_np.float32)
        # The ramp must be near-solid everywhere the headline runs and gone by
        # the time it reaches the subject, or the type sits on picture detail.
        x0 = (split + 46) * F.ss
        x1 = W * 0.82 * F.ss
        u = _np.clip((_np.arange(W * F.ss) - x0) / (x1 - x0), 0, 1)
        a = 1.0 - (u * u * (3 - 2 * u))
        ramp[0, :, 0], ramp[0, :, 1], ramp[0, :, 2] = C.ink_950
        ramp[0, :, 3] = a * 0.98 * 255
        sf.img.alpha_composite(Image.fromarray(
            _np.repeat(ramp, H * F.ss, 0).astype('uint8'), 'RGBA'), (0, 0))
        scrim(sf, H * 0.62, H, C.ink_950, 0.0, 0.55, curve=1.8)

    m = sl
    cw = split - m + 40

    cat = category(story.category)
    panel(sf, [m, st_ + 6, m + 6, st_ + 44], cat['rail'])
    typo.draw_text(sf.img, cat['kn'], sf.s(m + 20), sf.s(st_ + 38),
                   typo.font('kn_var', sf.s(30), weight=760), Role.text_hi,
                   shadow=(0, sf.s(2), sf.s(8), (0, 0, 0, 180)))

    b = typo.fit(text, 'kn', sf.s(126), sf.s(62), sf.s(cw),
                 sf.s(H - st_ - sb - 96), 1.16, max_lines=4)
    ty = st_ + 76
    typo.draw_block(sf.img, b, sf.s(m), sf.s(ty), Role.text_hi,
                    shadow=(0, sf.s(4), sf.s(20), (0, 0, 0, 210)), box_w=sf.s(cw))

    # Brand mark bottom-left; the bottom-right is where the duration chip goes.
    paste_logo(sf, m, H - sb - 6, 66, glow=0.16)
    typo.draw_text(sf.img, Brand.name, sf.s(m + 80), sf.s(H - sb + 30),
                   typo.font('kn', sf.s(30)), Role.text_hi,
                   shadow=(0, sf.s(2), sf.s(8), (0, 0, 0, 190)))
    typo.draw_text(sf.img, story.location or 'ಕರಾವಳಿ', sf.s(m + 80), sf.s(H - sb + 60),
                   typo.font('kn_var', sf.s(23), weight=560), C.gold_500,
                   shadow=(0, sf.s(2), sf.s(8), (0, 0, 0, 190)))

    grain(sf, Grade.grain * 0.7, Grade.grain_shadow_bias)
    return sf.save(path)
