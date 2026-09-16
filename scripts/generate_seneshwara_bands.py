#!/usr/bin/env python3
"""
Generate broadcast lower-third live bands for:
ಸಾರ್ವಜನಿಕ ಶ್ರೀ ಗಣೇಶೋತ್ಸವ ಸಮಿತಿ ಮಹತೋಭಾರ ಶ್ರೀ ಸೇನೇಶ್ವರ ದೇವಸ್ಥಾನ ಬೈಂದೂರು
ಕಾರ್ಯಕಾರಿ ಸಮಿತಿ – 2026

Quality: SS=3 (3× supersample), premultiplied downsample, broadcast-grade type.
Each band is a separate 1920×1080 transparent PNG overlay for OBS / vMix / StreamYard.
"""
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from brand import typo
from brand import ornament as orn
from brand.surface import Surface, rule, gilded_vrule, logo, cover, house_grade
from brand.tokens import C, Brand, mix, alpha

W, H = 1920, 1080
SS = 3                  # 3× supersample — the sharpness floor for broadcast Kannada
MARGIN = 72
SHADOW = (0, 3 * SS, 12 * SS, (0, 0, 0, 160))

EVENT_LINE = "ಸಾರ್ವಜನಿಕ ಶ್ರೀ ಗಣೇಶೋತ್ಸವ ಸಮಿತಿ ಮಹತೋಭಾರ ಶ್ರೀ ಸೇನೇಶ್ವರ ದೇವಸ್ಥಾನ ಬೈಂದೂರು  •  ಕಾರ್ಯಕಾರಿ ಸಮಿತಿ – 2026"

BANDS_DATA = [
    {"id": "01", "slug": "gauravadhyaksharu",
     "designation": "ಗೌರವಾಧ್ಯಕ್ಷರು",
     "names": ["ಬಿ. ಗಣೇಶ್ ಕಾರಂತ್"]},
    {"id": "02", "slug": "adhyaksharu",
     "designation": "ಅಧ್ಯಕ್ಷರು",
     "names": ["ಸುಧಾಕರ್ ದೇವಾಡಿಗ ಯಡ್ತರೆ"]},
    {"id": "03", "slug": "upadhyaksharu",
     "designation": "ಉಪಾಧ್ಯಕ್ಷರು",
     "names": ["ಗುರುಪ್ರಕಾಶ್", "ಹಿರಿಯ ದೇವಾಡಿಗ"]},
    {"id": "04", "slug": "pradhana_karyadarshi",
     "designation": "ಪ್ರಧಾನ ಕಾರ್ಯದರ್ಶಿ",
     "names": ["ಚಂದ್ರ ಪೂಜಾರಿ ಯಡ್ತರೆ"]},
    {"id": "05", "slug": "jothe_karyadarshigalu",
     "designation": "ಜೊತೆ ಕಾರ್ಯದರ್ಶಿಗಳು",
     "names": ["ನಾಗರಾಜ ಪಿ. ಯಡ್ತರೆ", "ಶಿವ", "ಸುಬ್ರಹ್ಮಣ್ಯ ಶೆಟ್ಟಿ"]},
    {"id": "06", "slug": "sanghatana_karyadarshigalu",
     "designation": "ಸಂಘಟನಾ ಕಾರ್ಯದರ್ಶಿಗಳು",
     "names": ["ರವೀಂದ್ರ ಶ್ಯಾನುಭಾಗ್", "ಶ್ಯಾಮ್ ಶೆಟ್", "ರವೀಂದ್ರ ಜಿ.", "ಸುಶಾಂತ್ ಆಚಾರ್"]},
    {"id": "07", "slug": "gaurava_lekka_parishodhakaru",
     "designation": "ಗೌರವ ಲೆಕ್ಕ ಪರಿಶೋಧಕರು",
     "names": ["ಸುರೇಶ ಬಟ್ವಾಡಿ"]},
    {"id": "08", "slug": "karyakrama_ustuvari",
     "designation": "ಕಾರ್ಯಕ್ರಮ ಉಸ್ತುವಾರಿ",
     "names": ["ಪಿ. ದಯಾನಂದ", "ಸದಾಶಿವ ಮೊಗವೀರ", "ಶಂಕರ ಮೊಗವೀರ"]},
]


# ─────────────────────────────────────────────────────────────────────────────
#  FORMAT & FINISH
# ─────────────────────────────────────────────────────────────────────────────

def read_format(path="LIVE BG.png") -> tuple[int, tuple]:
    with Image.open(path) as im:
        a = np.asarray(im.convert("RGBA"))
    opaque = np.where(a[..., 3].max(axis=1) > 0)[0]
    top = int(opaque.min())
    vals, counts = np.unique(a[top:, :, :3].reshape(-1, 3), axis=0,
                             return_counts=True)
    return top, tuple(int(v) for v in vals[counts.argmax()])


def finish(img: Image.Image, top: int | None = None) -> Image.Image:
    """Premultiplied-alpha downsample → clean edges on live camera."""
    a = np.asarray(img).astype(np.float32) / 255.0
    pm = np.concatenate([a[..., :3] * a[..., 3:4], a[..., 3:4]], -1)
    pm_img = Image.fromarray((pm * 255 + 0.5).astype(np.uint8), "RGBA")
    s = np.asarray(pm_img.resize((W, H), Image.Resampling.LANCZOS)
                   ).astype(np.float32) / 255.0
    al = s[..., 3:4]
    col = np.where(al > 1e-4, s[..., :3] / np.maximum(al, 1e-4), 0.0)
    out = (np.concatenate([np.clip(col, 0, 1), al], -1) * 255 + 0.5
           ).astype(np.uint8)
    if top is not None:
        out[:top] = 0
        out[top:, :, 3] = 255
    out[out[..., 3] == 0] = 0
    return Image.fromarray(out, "RGBA")


# ─────────────────────────────────────────────────────────────────────────────
#  BAND GROUND — richer than the reference, same principle
# ─────────────────────────────────────────────────────────────────────────────

def band_ground(sf: Surface, top: int, colour: tuple):
    bh = H - top
    hi = mix(colour, C.red_600, 0.40)
    lo = mix(colour, C.ink_950, 0.42)
    t = np.linspace(0.0, 1.0, bh * SS, dtype=np.float32)
    t = t * t * (3 - 2 * t)
    rows = np.stack([hi[i] + (lo[i] - hi[i]) * t for i in range(3)], -1)
    arr = np.empty((bh * SS, W * SS, 4), np.float32)
    arr[..., :3] = rows[:, None, :]
    rng = np.random.default_rng(1956)
    arr[..., :3] += rng.normal(0.0, 1.6, (bh * SS, W * SS, 1)
                               ).astype(np.float32)
    arr[..., 3] = 255
    sf.img.alpha_composite(
        Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA"),
        (0, top * SS))


def band_glow(sf: Surface, top: int, cx: float, cy: float,
              rx: float, ry: float, color, a: float):
    """A warm radial glow inside the band — gives depth under the logo."""
    bh = H - top
    ys = (np.arange(bh * SS, dtype=np.float32) + 0.5) / SS + top
    xs = (np.arange(W * SS, dtype=np.float32) + 0.5) / SS
    d = np.sqrt(((xs[None, :] - cx) / rx) ** 2 +
                ((ys[:, None] - cy) / ry) ** 2)
    tt = np.clip(1.0 - d, 0.0, 1.0)
    sf.img.alpha_composite(
        orn._tint(tt * tt * (3 - 2 * tt) * 255.0, color, a),
        (0, top * SS))


def top_edge(sf: Surface, top: int):
    rule(sf, 0, top, W, (*C.gold_500, 255), 3.0)
    rule(sf, 0, top, W, (*mix(C.gold_300, C.paper_0, 0.3), 170), 1.0)
    rule(sf, 0, top + 3, W, (*C.ink_950, 90), 1.0)


# ─────────────────────────────────────────────────────────────────────────────
#  LOGO — ringed, same as the reference live overlay
# ─────────────────────────────────────────────────────────────────────────────

def ringed_logo(sf: Surface, cx: float, cy: float, d: float):
    ring = 6
    S = int((d + 2 * ring + 24) * SS)
    lay = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    c = S / 2
    r_out = (d / 2 + ring) * SS
    # contact shadow
    sh = Image.new("L", (S, S), 0)
    ImageDraw.Draw(sh).ellipse(
        [c - r_out, c - r_out + 4 * SS, c + r_out, c + r_out + 4 * SS],
        fill=150)
    sh = sh.filter(ImageFilter.GaussianBlur(5 * SS))
    lay.alpha_composite(orn._tint(np.asarray(sh, np.float32), (0, 0, 0), 1.0))
    dr = ImageDraw.Draw(lay)
    dr.ellipse([c - r_out, c - r_out, c + r_out, c + r_out],
               fill=(*C.gold_500, 255))
    r_in = r_out - 1.5 * SS
    dr.ellipse([c - r_in, c - r_in, c + r_in, c + r_in],
               outline=(*mix(C.gold_300, C.paper_0, 0.35), 200), width=SS)
    lg = logo(int(d * SS))
    lay.alpha_composite(lg, (int(c - d * SS / 2), int(c - d * SS / 2)))
    orn._paste(sf, lay, cx * SS - c, cy * SS - c)


# ─────────────────────────────────────────────────────────────────────────────
#  CHANNEL BRAND BLOCK — left side of the band
# ─────────────────────────────────────────────────────────────────────────────

def build_brand_block(sf: Surface, top: int, bh: int) -> float:
    d = min(150, bh - 34)
    lcx = MARGIN + d / 2 + 6
    lcy = top + bh / 2
    band_glow(sf, top, lcx, lcy, 260, bh * 0.9, C.gold_500, 0.10)
    ringed_logo(sf, lcx, lcy, d)

    f_name = typo.font("kn", int(58 * SS))
    f_tag = typo.font("kn_var", int(30 * SS), weight=560)
    tx = MARGIN + d + 12 + 30
    typo.draw_text(sf.img, Brand.name,
                   tx * SS, (top + 88) * SS, f_name, C.paper_0, shadow=SHADOW)
    typo.draw_text(sf.img, Brand.tagline,
                   tx * SS, (top + 140) * SS, f_tag, C.gold_300, shadow=SHADOW)
    w_name = typo.text_width(Brand.name, f_name) / SS
    w_tag = typo.text_width(Brand.tagline, f_tag) / SS
    div_x = tx + max(w_name, w_tag) + 40
    gilded_vrule(sf, div_x, top + 28, H - 28, weight=1.6, a_mid=0.85)
    return div_x


# ─────────────────────────────────────────────────────────────────────────────
#  NAME TILE — frosted glass-style rounded tile (uniform for all counts)
# ─────────────────────────────────────────────────────────────────────────────

def name_tile(sf: Surface, x: float, y: float, w: float, h: float,
              text: str, font, colour: tuple):
    """Rounded frosted tile with inner top-edge highlight for broadcast depth."""
    lay = Image.new("RGBA", (int(w * SS), int(h * SS)), (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    R = 10 * SS
    # body
    body_col = (*mix(colour, C.ink_900, 0.55), 230)
    dr.rounded_rectangle([0, 0, int(w * SS) - 1, int(h * SS) - 1],
                         radius=R, fill=body_col,
                         outline=(*C.gold_500, 140), width=max(1, SS))
    # inner top highlight — subtle lit edge
    hi_lay = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(hi_lay)
    hd.rounded_rectangle([SS, SS, int(w * SS) - SS, int(h * SS // 3)],
                         radius=R, fill=(*C.paper_50, 22))
    lay.alpha_composite(hi_lay)

    # optically centred text
    rise, drop = typo.ink_extents(text, font)
    cy = (h * SS) / 2
    baseline = cy + (rise - drop) / 2
    typo.draw_text(lay, text, (w * SS) / 2, baseline, font,
                   C.paper_0, anchor_x="c", shadow=SHADOW)
    orn._paste(sf, lay, x * SS, y * SS)


def desig_plate(sf: Surface, x: float, y: float, w: float, h: float,
                text: str, font):
    """The gold designation plate — solid, broadcast authority."""
    lay = Image.new("RGBA", (int(w * SS), int(h * SS)), (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    R = 10 * SS
    # gold fill with a subtle vertical gradient (brighter top)
    arr = np.zeros((int(h * SS), int(w * SS), 4), np.uint8)
    gold_hi = C.gold_400
    gold_lo = C.gold_600
    t = np.linspace(0.0, 1.0, int(h * SS), dtype=np.float32)
    for c in range(3):
        arr[:, :, c] = np.clip(
            gold_hi[c] + (gold_lo[c] - gold_hi[c]) * t[:, None], 0, 255
        ).astype(np.uint8)
    arr[:, :, 3] = 250
    grad = Image.fromarray(arr, "RGBA")
    # mask to rounded rect
    mask = Image.new("L", (int(w * SS), int(h * SS)), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, int(w * SS) - 1, int(h * SS) - 1], radius=R, fill=255)
    grad.putalpha(mask)
    lay.alpha_composite(grad)
    # border
    dr = ImageDraw.Draw(lay)
    dr.rounded_rectangle([0, 0, int(w * SS) - 1, int(h * SS) - 1],
                         radius=R,
                         outline=(*C.gold_300, 255), width=max(1, SS))
    # inner top highlight
    hi_lay = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    ImageDraw.Draw(hi_lay).rounded_rectangle(
        [2 * SS, 1 * SS, int(w * SS) - 2 * SS, int(h * SS // 3)],
        radius=R, fill=(*C.paper_0, 40))
    lay.alpha_composite(hi_lay)
    # text
    rise, drop = typo.ink_extents(text, font)
    cy = (h * SS) / 2
    baseline = cy + (rise - drop) / 2
    typo.draw_text(lay, text, (w * SS) / 2, baseline, font,
                   C.ink_950, anchor_x="c")
    orn._paste(sf, lay, x * SS, y * SS)


# ─────────────────────────────────────────────────────────────────────────────
#  BUILD ONE BAND
# ─────────────────────────────────────────────────────────────────────────────

def build_single_band(item: dict, top: int, colour: tuple) -> Image.Image:
    sf = Surface(W, H, SS, bg=(0, 0, 0, 0))
    bh = H - top
    band_ground(sf, top, colour)

    # ── left: channel branding ────────────────────────────────────────────
    div_x = build_brand_block(sf, top, bh)

    # ── right content area ────────────────────────────────────────────────
    cx0 = div_x + 28
    cx1 = W - MARGIN
    cw = cx1 - cx0

    # eyebrow — event title across the top of the content area
    f_eye = typo.font("kn_var", int(24 * SS), weight=620)
    eye_y = top + 36
    typo.draw_text(sf.img, EVENT_LINE,
                   (cx0 + cw / 2) * SS, eye_y * SS, f_eye,
                   C.gold_300, anchor_x="c", shadow=SHADOW)

    # accent rule under the eyebrow
    ry = top + 58
    rule(sf, cx0 + 10, ry, cw - 20, (*C.gold_500, 80), 1.0)
    rule(sf, cx0 + 60, ry, cw - 120, (*C.gold_400, 140), 0.8)

    # ── designation + names ───────────────────────────────────────────────
    desig = item["designation"]
    names = item["names"]
    n = len(names)

    # designation plate — UNIFORM fixed width across ALL bands for visual consistency
    dw = 290
    dh = 58
    dx = cx0 + 6
    dy = top + 82
    dpt = 25
    f_desig = typo.font("kn", int(dpt * SS))
    while typo.text_width(desig, f_desig) / SS > (dw - 24) and dpt > 16:
        dpt -= 1
        f_desig = typo.font("kn", int(dpt * SS))
    desig_plate(sf, dx, dy, dw, dh, desig, f_desig)

    # separator — locked to the exact same x-coordinate across all 8 bands
    sep = dx + dw + 18
    gilded_vrule(sf, sep, dy - 6, dy + dh + 6, weight=1.6, a_mid=0.75)

    # names zone — ALL names use tiles with auto-fitted fonts for perfect fit & uniformity
    nx0 = sep + 18
    nw = cx1 - nx0

    if n == 1:
        # single name — wide tile, same frosted-glass style
        pt = 40
        f_nm = typo.font("kn", int(pt * SS))
        while typo.text_width(names[0], f_nm) / SS > (nw - 40) and pt > 24:
            pt -= 1
            f_nm = typo.font("kn", int(pt * SS))
        name_tile(sf, nx0, dy, nw, dh, names[0], f_nm, colour)

    elif n == 2:
        gap = 20
        tw = (nw - gap) / 2
        for i, name in enumerate(names):
            pt = 34
            f_nm = typo.font("kn", int(pt * SS))
            while typo.text_width(name, f_nm) / SS > (tw - 24) and pt > 20:
                pt -= 1
                f_nm = typo.font("kn", int(pt * SS))
            name_tile(sf, nx0 + i * (tw + gap), dy, tw, dh, name, f_nm, colour)

    elif n == 3:
        gap = 16
        tw = (nw - 2 * gap) / 3
        for i, name in enumerate(names):
            pt = 28
            f_nm = typo.font("kn", int(pt * SS))
            while typo.text_width(name, f_nm) / SS > (tw - 20) and pt > 18:
                pt -= 1
                f_nm = typo.font("kn", int(pt * SS))
            name_tile(sf, nx0 + i * (tw + gap), dy, tw, dh, name, f_nm, colour)

    elif n == 4:
        gap = 12
        tw = (nw - 3 * gap) / 4
        for i, name in enumerate(names):
            pt = 24
            f_nm = typo.font("kn", int(pt * SS))
            while typo.text_width(name, f_nm) / SS > (tw - 18) and pt > 16:
                pt -= 1
                f_nm = typo.font("kn", int(pt * SS))
            name_tile(sf, nx0 + i * (tw + gap), dy, tw, dh, name, f_nm, colour)

    top_edge(sf, top)
    return finish(sf.img, top)


# ─────────────────────────────────────────────────────────────────────────────
#  BUG + BADGE — identical to the reference overlay
# ─────────────────────────────────────────────────────────────────────────────

def build_bug() -> Image.Image:
    sf = Surface(W, H, SS, bg=(0, 0, 0, 0))
    ringed_logo(sf, W - MARGIN - 52 - 6, MARGIN + 52 - 12, 104)
    return finish(sf.img)


def build_badge() -> Image.Image:
    sf = Surface(W, H, SS, bg=(0, 0, 0, 0))
    f_live = typo.font("latin", int(28 * SS), weight=800)
    f_kn = typo.font("kn_var", int(28 * SS), weight=640)
    ph, pad, dot, gap = 54, 24, 14, 14
    w_live = typo.text_width("LIVE", f_live) / SS
    w_kn = typo.text_width("ನೇರ ಪ್ರಸಾರ", f_kn) / SS
    pw = pad + dot + gap + w_live + 16 + 2 + 16 + w_kn + pad
    x0, y0 = MARGIN, 56
    lay = Image.new("RGBA", (int(pw * SS), int(ph * SS)), (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    dr.rounded_rectangle([0, 0, pw * SS - 1, ph * SS - 1],
                         radius=ph * SS / 2,
                         fill=(*C.red_500, 245),
                         outline=(*C.red_400, 255), width=2 * SS)
    cy = ph * SS / 2
    ddx = (pad + dot / 2) * SS
    dr.ellipse([ddx - dot * SS / 2, cy - dot * SS / 2,
                ddx + dot * SS / 2, cy + dot * SS / 2],
               fill=(*C.paper_0, 255))
    xl = (pad + dot + gap) * SS
    r_live, _ = typo.ink_extents("LIVE", f_live)
    typo.draw_text(lay, "LIVE", xl, cy + r_live / 2, f_live, C.paper_0)
    xs = xl + (w_live + 16) * SS
    dr.rectangle([xs, cy - 14 * SS, xs + 2 * SS, cy + 14 * SS],
                 fill=(*C.paper_0, 150))
    r_kn, _ = typo.ink_extents("ನೇರ ಪ್ರಸಾರ", f_kn)
    typo.draw_text(lay, "ನೇರ ಪ್ರಸಾರ", xs + 18 * SS, cy + r_kn * 0.42,
                   f_kn, C.paper_0)
    orn._paste(sf, lay, x0 * SS, y0 * SS)
    return finish(sf.img)


# ─────────────────────────────────────────────────────────────────────────────
#  PREVIEW + MAIN
# ─────────────────────────────────────────────────────────────────────────────

def preview(layers: list[Image.Image], path: str):
    sample = os.path.join(ROOT, "assets", "stock",
                          "ganeshotsava_idol_devotional_pooja.jpg")
    if not os.path.exists(sample):
        sample = os.path.join(ROOT, "assets", "stock",
                              "temple_ganahoma_vedic_ritual.jpg")
    if os.path.exists(sample):
        with Image.open(sample) as src:
            frame = house_grade(cover(src, W, H)).convert("RGBA")
    else:
        frame = Image.new("RGBA", (W, H), (40, 40, 48, 255))
    for lay in layers:
        frame.alpha_composite(lay)
    frame.convert("RGB").save(path, quality=93)


def main():
    top, colour = read_format("LIVE BG.png")
    out_dir = os.path.join("out", "live", "seneshwara_ganapathi_2026")
    os.makedirs(out_dir, exist_ok=True)

    bug = build_bug()
    badge = build_badge()

    print(f"Generating 8 Live Bands (SS={SS}) in {out_dir}…")
    for item in BANDS_DATA:
        band_img = build_single_band(item, top, colour)

        # Full 1920×1080 Transparent Overlay (Band + Bug + Badge)
        full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        full.alpha_composite(band_img)
        full.alpha_composite(bug)
        full.alpha_composite(badge)
        full.save(os.path.join(out_dir,
                               f"band_{item['id']}_{item['slug']}_full.png"),
                  optimize=True)

        print(f"  ✓ [{item['id']}] {item['designation']}: "
              f"{', '.join(item['names'])}")

    print("\n✓ All 8 Live Bands generated.")


if __name__ == "__main__":
    main()
