#!/usr/bin/env python3
"""
Brand a thumbnail image with the ಊರ್ಮನಿ ಸುದ್ದಿ masthead.

Draws the full masthead (logo + wordmark + tagline + gilded rule) at the top
of the thumbnail over a soft dark veil, exactly matching the house style for
long-format video (SKILL.md §1.3: brand masthead at TOP for the entire runtime).

Usage:
    python3 scripts/brand_thumbnail.py <input.png> [output.png]

If no output path is given, saves to <input>_branded.png alongside the original.
"""
from __future__ import annotations

import os
import sys

# Resolve project root so brand imports work.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PIL import Image
from brand.surface import Surface, scrim, paste_logo, gilded_rule
from brand.tokens import Brand, C, Role, T, Grid
from brand import typo


def brand_thumbnail(src_path: str, dst_path: str | None = None) -> str:
    """Add the ಊರ್ಮನಿ ಸುದ್ದಿ masthead to a thumbnail image."""

    img = Image.open(src_path).convert('RGBA')
    w, h = img.size  # 1280 × 720 for YT thumbnails

    # ── Build a Surface at the thumbnail's native resolution (no supersample
    #    waste on a file that is already 1280×720). ss=1 means all coordinates
    #    are 1:1 pixel coordinates.
    sf = Surface(w, h, ss=1, bg=(0, 0, 0, 0))
    sf.img = img.copy()

    # ── Soft dark scrim fading down from the top, so white text is legible
    #    over any photograph. Covers the top ~18% of the frame.
    veil_h = int(h * 0.18)
    scrim(sf, 0, veil_h, C.ink_950, a0=0.72, a1=0.0, curve=1.6)

    # ── Masthead: logo mark + wordmark + tagline + gilded rule.
    #    Scale to fit the thumbnail — 1280px is wider than the 1080 reference,
    #    so we scale up slightly.
    scale_factor = w / 1080.0
    margin = int(48 * scale_factor)
    mark_size = int(56 * scale_factor)
    y_top = int(18 * scale_factor)

    # Logo
    paste_logo(sf, margin, y_top, mark_size, glow=0.10)

    # Wordmark: ಊರ್ಮನಿ ಸುದ್ದಿ
    tx = margin + mark_size + int(16 * scale_factor)
    f_name = typo.font('kn', int(T.h4[0] * 0.72 * scale_factor))
    shadow = (0, 2, 6, (0, 0, 0, 180))
    typo.draw_text(sf.img, Brand.name, tx, y_top + int(mark_size * 0.53),
                   f_name, Role.text_hi, shadow=shadow)

    # Tagline: ನಮ್ಮ ಊರು  •  ನಮ್ಮ ಧ್ವನಿ
    f_tag = typo.font('kn_var', int(T.micro[0] * 1.0 * scale_factor), weight=600)
    typo.draw_text(sf.img, Brand.tagline, tx, y_top + int(mark_size * 0.90),
                   f_tag, C.gold_500, shadow=shadow)

    # Gilded rule under the masthead
    rule_y = y_top + mark_size + int(12 * scale_factor)
    cw = w - 2 * margin
    gilded_rule(sf, margin, rule_y, margin + cw, weight=1.5, on_photo=True)

    # ── Save
    if dst_path is None:
        base, ext = os.path.splitext(src_path)
        dst_path = f'{base}_branded{ext}'
    os.makedirs(os.path.dirname(os.path.abspath(dst_path)), exist_ok=True)
    result = sf.img.convert('RGB')
    result.save(dst_path, quality=95, optimize=True)
    print(f'✓ Branded thumbnail saved → {dst_path}')
    return dst_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 scripts/brand_thumbnail.py <input.png> [output.png]')
        sys.exit(1)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    brand_thumbnail(src, dst)
