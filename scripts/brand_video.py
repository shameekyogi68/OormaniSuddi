#!/usr/bin/env python3
"""
Brand a video with the ಊರ್ಮನಿ ಸುದ್ದಿ masthead overlay for the entire runtime.

Two-step process:
  1. Render a transparent PNG masthead overlay at the video's resolution (PIL).
  2. Composite it onto every frame via ffmpeg's overlay filter (copy audio).

Per SKILL.md §1.3: Brand masthead at the TOP for the entire runtime — logo,
ಊರ್ಮನಿ ಸುದ್ದಿ wordmark, gold tagline, all on a soft dark veil fading down
from the top edge. No bottom-corner watermark.

Usage:
    python3 scripts/brand_video.py <input.mp4> [output.mp4]
"""
from __future__ import annotations

import os
import sys
import subprocess
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PIL import Image, ImageDraw, ImageFilter
import numpy as np
from brand.surface import Surface, paste_logo, gilded_rule, logo
from brand.tokens import Brand, C, Role, T, Grid
from brand import typo


def _probe(path: str) -> dict:
    """Get video width, height, fps, duration from ffprobe."""
    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_streams', '-show_format', path
    ]
    out = subprocess.check_output(cmd, text=True)
    data = json.loads(out)
    vstream = next(s for s in data['streams'] if s['codec_type'] == 'video')
    w, h = int(vstream['width']), int(vstream['height'])
    # Parse frame rate
    fps_str = vstream.get('r_frame_rate', '30/1')
    num, den = map(int, fps_str.split('/'))
    fps = num / den if den else 30
    duration = float(data['format'].get('duration', 0))
    return {'w': w, 'h': h, 'fps': fps, 'duration': duration}


def render_overlay(w: int, h: int, out_path: str) -> str:
    """Render a transparent PNG overlay with the ಊರ್ಮನಿ ಸುದ್ದಿ masthead.

    The overlay has:
    - A soft dark veil gradient fading from the top (~12-15% of frame)
    - The round logo at top-left
    - ಊರ್ಮನಿ ಸುದ್ದಿ wordmark in white
    - ನಮ್ಮ ಊರು  •  ನಮ್ಮ ಧ್ವನಿ tagline in gold
    - A gilded rule hairline under the masthead
    """
    # Create a transparent RGBA image at the video's native resolution
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))

    # ── Soft dark scrim at top ─────────────────────────────────────────────
    # A veil that fades from ~70% opacity black at the very top to fully
    # transparent at about 12% of the frame height. Smoothstep curve.
    veil_h = int(h * 0.14)
    veil = np.zeros((veil_h, w, 4), dtype=np.float64)
    t = np.linspace(0.0, 1.0, veil_h)
    # Smoothstep out: opaque at top, transparent at bottom
    alpha_curve = 1.0 - (t * t * (3.0 - 2.0 * t))
    veil[..., 0] = C.ink_950[0]
    veil[..., 1] = C.ink_950[1]
    veil[..., 2] = C.ink_950[2]
    veil[..., 3] = (alpha_curve * 0.68 * 255.0)[:, None]
    overlay.alpha_composite(
        Image.fromarray(veil.astype(np.uint8), 'RGBA'), (0, 0))

    # ── Scale factor relative to 1080-wide reference ────────────────────
    # At 3840 wide, everything is ~3.56× the reference. Scale all sizes
    # so the masthead reads the same relative proportion.
    sf_ratio = w / 1080.0

    margin = int(72 * sf_ratio)  # Match Grid.margin scaled
    mark_size = int(68 * sf_ratio)  # Logo diameter
    y_top = int(22 * sf_ratio)

    # ── Logo (round circle variant with subtle gold glow) ─────────────
    lg = logo(mark_size, 'circle')
    # Soft glow behind the logo
    glow_r = int(mark_size * 0.95)
    glow_cx = margin + mark_size // 2
    glow_cy = y_top + mark_size // 2
    # Simple radial glow
    glow_d = glow_r * 2
    gx0 = max(0, glow_cx - glow_r)
    gy0 = max(0, glow_cy - glow_r)
    gx1 = min(w, glow_cx + glow_r)
    gy1 = min(h, glow_cy + glow_r)
    xx = (np.arange(gx0 - (glow_cx - glow_r), gx1 - (glow_cx - glow_r), dtype=np.float64) - glow_r)[None, :]
    yy = (np.arange(gy0 - (glow_cy - glow_r), gy1 - (glow_cy - glow_r), dtype=np.float64) - glow_r)[:, None]
    d = np.sqrt(xx ** 2 + yy ** 2) / glow_r
    ga = np.clip(1.0 - d, 0, 1) ** 2.4 * 0.13 * 255.0
    glay = np.zeros((gy1 - gy0, gx1 - gx0, 4), dtype=np.float64)
    glay[..., 0] = C.gold_500[0]
    glay[..., 1] = C.gold_500[1]
    glay[..., 2] = C.gold_500[2]
    glay[..., 3] = ga
    overlay.alpha_composite(Image.fromarray(glay.astype(np.uint8), 'RGBA'), (gx0, gy0))
    overlay.alpha_composite(lg, (margin, y_top))

    # ── Wordmark: ಊರ್ಮನಿ ಸುದ್ದಿ ─────────────────────────────────────────
    tx = margin + mark_size + int(20 * sf_ratio)
    font_size_name = int(T.h4[0] * 0.80 * sf_ratio)
    f_name = typo.font('kn', font_size_name)
    shadow_spec = (0, int(2 * sf_ratio), int(7 * sf_ratio), (0, 0, 0, 150))

    # Draw shadow first
    name_baseline = y_top + int(mark_size * 0.53)
    _draw_with_shadow(overlay, Brand.name, tx, name_baseline,
                      f_name, Role.text_hi, shadow_spec)

    # ── Tagline: ನಮ್ಮ ಊರು  •  ನಮ್ಮ ಧ್ವನಿ ────────────────────────────
    font_size_tag = int(T.micro[0] * 1.10 * sf_ratio)
    f_tag = typo.font('kn_var', font_size_tag, weight=600)
    tag_baseline = y_top + int(mark_size * 0.92)
    _draw_with_shadow(overlay, Brand.tagline, tx, tag_baseline,
                      f_tag, C.gold_500, shadow_spec)

    # ── Gilded rule ─────────────────────────────────────────────────────
    # We render this manually since Surface isn't available on a raw Image.
    rule_y = y_top + mark_size + int(18 * sf_ratio)
    rule_x0 = margin
    rule_x1 = w - margin
    _draw_gilded_rule(overlay, rule_x0, rule_y, rule_x1,
                      weight=max(2, int(1.5 * sf_ratio)))

    # ── Save transparent PNG ─────────────────────────────────────────────
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    overlay.save(out_path, 'PNG')
    print(f'✓ Overlay rendered → {out_path}  ({w}×{h})')
    return out_path


def _draw_with_shadow(img: Image.Image, text: str, x: int, baseline: int,
                      f, fill, shadow: tuple):
    """Draw text with a blurred shadow on a transparent image."""
    dx, dy, blur, scol = shadow
    w_text = typo.text_width(text, f)
    rise, drop = typo.ink_extents(text, f)
    pad = int(blur * 3 + 10)

    # Shadow layer
    sw, sh = int(w_text + pad * 2), int(rise + drop + pad * 2)
    slay = Image.new('RGBA', (sw, sh), (0, 0, 0, 0))
    sd = ImageDraw.Draw(slay)
    safe_text = typo.safe(text, f)
    sd.text((pad + dx, pad + rise + dy), safe_text, font=f, fill=scol, anchor='ls')
    slay = slay.filter(ImageFilter.GaussianBlur(blur))
    img.alpha_composite(slay, (int(x - pad), int(baseline - rise - pad)))

    # Main text
    d = ImageDraw.Draw(img)
    d.text((x, baseline), safe_text, font=f, fill=fill, anchor='ls')


def _draw_gilded_rule(img: Image.Image, x0: int, y: int, x1: int, weight: int = 2):
    """Draw a gilded rule (gold gradient hairline) directly onto an RGBA image."""
    W = x1 - x0
    if W <= 0:
        return
    t = np.abs(np.linspace(-1.0, 1.0, W))
    c_lo, c_hi = C.gold_600, C.gold_400
    rgbv = np.stack([c_hi[i] + (c_lo[i] - c_hi[i]) * t for i in range(3)], 1)
    a_mid, a_end = 0.42, 0.04
    a = (a_mid + (a_end - a_mid) * t ** 1.6) * 255.0
    band = np.concatenate([rgbv, a[:, None]], 1)[None, :, :]
    band = np.repeat(band, weight, 0)
    rule_img = Image.fromarray(band.astype(np.uint8), 'RGBA')
    img.alpha_composite(rule_img, (x0, y))


def brand_video(src_path: str, dst_path: str | None = None) -> str:
    """Overlay the ಊರ್ಮನಿ ಸುದ್ದಿ masthead on every frame of a video."""

    info = _probe(src_path)
    w, h = info['w'], info['h']
    duration = info['duration']
    print(f'Video: {w}×{h}, {info["fps"]} fps, {duration:.1f}s')

    # Work directory next to the source file
    src_dir = os.path.dirname(os.path.abspath(src_path))
    base = os.path.splitext(os.path.basename(src_path))[0]
    work_dir = os.path.join(src_dir, '_work')
    os.makedirs(work_dir, exist_ok=True)

    # 1. Render the overlay PNG
    overlay_path = os.path.join(work_dir, f'{base}_overlay.png')
    render_overlay(w, h, overlay_path)

    # 2. Composite via ffmpeg
    if dst_path is None:
        dst_path = os.path.join(src_dir, f'{base}_branded.mp4')

    print(f'⏳ Compositing overlay onto video ({duration:.0f}s, {w}×{h})…')
    print(f'   This will take a while on a {w}×{h} video.')

    cmd = [
        'ffmpeg', '-y',
        '-i', src_path,
        '-i', overlay_path,
        '-filter_complex', '[0:v][1:v]overlay=0:0:format=auto',
        '-c:v', 'h264_videotoolbox',   # Hardware encoder on Apple Silicon
        '-b:v', '60M',                 # Match the source bitrate (~61 Mbps)
        '-color_range', 'tv',
        '-colorspace', 'bt709',
        '-color_primaries', 'bt709',
        '-color_trc', 'bt709',
        '-c:a', 'copy',                # Keep audio untouched
        '-movflags', '+faststart',
        dst_path
    ]

    print(f'   cmd: {" ".join(cmd[:6])}…')
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _, stderr = proc.communicate()

    if proc.returncode != 0:
        print(f'✗ ffmpeg failed (exit {proc.returncode})')
        print(stderr.decode('utf-8', errors='replace')[-2000:])
        sys.exit(1)

    # File size
    size_mb = os.path.getsize(dst_path) / (1024 * 1024)
    print(f'✓ Branded video saved → {dst_path}  ({size_mb:.0f} MB)')
    return dst_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 scripts/brand_video.py <input.mp4> [output.mp4]')
        sys.exit(1)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    brand_video(src, dst)
