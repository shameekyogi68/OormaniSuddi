#!/usr/bin/env python3
"""Brand title cards and lower thirds as PNG (Pillow + raqm, so Kannada conjuncts shape correctly).

Never render Kannada with ffmpeg drawtext: it does not shape conjuncts.
CLI:  python3 make_cards.py <project.json> [--preview]   -> renders into <work>/cards and prints paths.
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

from common import C, FONT_BODY, FONT_TITLE, ROOT, fit_filter, probe, run

if not features.check("raqm"):
    raise SystemExit("Pillow was built without raqm: Kannada would render with broken conjuncts. Fix Pillow first.")


def font(path, size, weight=None):
    f = ImageFont.truetype(str(path), int(size), layout_engine=ImageFont.Layout.RAQM)
    if weight is not None:
        axes = f.get_variation_axes()
        f.set_variation_by_axes([weight if a["name"] == b"Weight" else a["default"] for a in axes])
    return f


def fitted(text, path, size, max_w, weight=None):
    f = font(path, size, weight)
    while f.getlength(text) > max_w and size > 12:
        size *= 0.94
        f = font(path, size, weight)
    return f


def grab_frame(clip, t, W, H, out_png):
    info = probe(clip)
    t = min(max(t, 0.0), max(info["duration"] - 0.1, 0.0))
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", clip, "-frames:v", "1",
         "-vf", fit_filter(info, W, H), out_png], log=False)
    return out_png


def backdrop(frame_png, W, H):
    img = Image.open(frame_png).convert("RGB").resize((W, H), Image.LANCZOS)
    img = img.filter(ImageFilter.GaussianBlur(W * 0.012))
    img = Image.blend(Image.new("RGB", (W, H), C.ink_950), img, 0.42)
    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse([-W * 0.25, -H * 0.35, W * 1.25, H * 1.35], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(H * 0.18))
    return Image.composite(img, Image.new("RGB", (W, H), C.ink_950), vig).convert("RGBA")


def paste_logo(img, logo_path, d, cx, top):
    logo = Image.open(logo_path).convert("RGBA").resize((d, d), Image.LANCZOS)
    pad = int(d * 0.25)
    glow = Image.new("RGBA", (d + 2 * pad, d + 2 * pad), (0, 0, 0, 0))
    tint = Image.new("RGBA", logo.size, C.gold_400 + (255,))
    glow.paste(tint, (pad, pad), logo.split()[3])
    glow = glow.filter(ImageFilter.GaussianBlur(d * 0.06))
    glow.putalpha(glow.split()[3].point(lambda a: int(a * 0.5)))
    img.alpha_composite(glow, (cx - d // 2 - pad, top - pad))
    img.alpha_composite(logo, (cx - d // 2, top))


def centred(draw, text, f, y_top, W, fill):
    l, t, r, b = draw.textbbox((0, 0), text, font=f)
    draw.text(((W - (r - l)) / 2 - l, y_top - t), text, font=f, fill=fill)
    return y_top + (b - t)


def title_card(frame_png, out_png, W, H, logo_path, title, lines, kind="intro"):
    img = backdrop(frame_png, W, H)
    d = int(H * (0.292 if kind == "intro" else 0.256))
    top = int(H * (0.083 if kind == "intro" else 0.098))
    paste_logo(img, logo_path, d, W // 2, top)
    draw = ImageDraw.Draw(img)
    y = top + d + int(H * 0.062)
    tf = fitted(title, FONT_TITLE, H * (0.047 if kind == "intro" else 0.054), W * 0.86)
    y = centred(draw, title, tf, y, W, C.gold_400) + int(H * 0.034)
    hw, th = int(W * 0.16), max(2, H // 480)
    draw.rectangle([W // 2 - hw, y, W // 2 + hw, y + th], fill=C.gold_400 + (235,))
    y += th + int(H * 0.03)
    for k, line in enumerate(lines):
        lf = fitted(line, FONT_BODY, H * 0.036, W * 0.86, weight=500)
        y = centred(draw, line, lf, y, W, C.paper_50) + int(H * 0.022)
    img.convert("RGB").save(out_png)
    return out_png


def lower_third(out_png, W, H, title, subtitle=""):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tf = fitted(title, FONT_TITLE, H * 0.042, W * 0.6)
    sf = fitted(subtitle, FONT_BODY, H * 0.028, W * 0.6, weight=500) if subtitle else None
    x = int(W * 0.056)
    text_w = max(tf.getlength(title), sf.getlength(subtitle) if sf else 0)
    band_w = int(x + text_w + W * 0.12)
    y0, y1 = int(H * 0.765), int(H * 0.915)
    band = Image.new("RGBA", (band_w, y1 - y0), C.ink_950 + (0,))
    fade = int(W * 0.08)
    alpha = Image.new("L", (band_w, 1))
    for px in range(band_w):
        alpha.putpixel((px, 0), int(158 * min(1.0, (band_w - px) / fade)))
    band.putalpha(alpha.resize(band.size))
    img.alpha_composite(band, (0, y0))
    draw = ImageDraw.Draw(img)
    bar_h = int(H * 0.09)
    by = (y0 + y1) // 2 - bar_h // 2
    draw.rectangle([int(W * 0.042), by, int(W * 0.042) + max(4, W // 320), by + bar_h], fill=C.gold_400 + (255,))
    l, t, r, b = draw.textbbox((0, 0), title, font=tf)
    ty = by - t if sf else (y0 + y1) // 2 - (b - t) // 2 - t
    draw.text((x - l, ty), title, font=tf, fill=C.paper_50 + (255,))
    if sf:
        l2, t2, _, b2 = draw.textbbox((0, 0), subtitle, font=sf)
        draw.text((x - l2, by + bar_h - (b2 - t2) - t2), subtitle, font=sf, fill=C.gold_400 + (255,))
    img.save(out_png)
    return out_png


def _date_lines(spec):
    from datetime import date
    from brand.content import KN_DAYS, KN_MONTHS
    if not spec.get("date"):
        return "", ""
    d = date.fromisoformat(spec["date"])
    top, bot = f"{d.day} {KN_MONTHS[d.month - 1]} {d.year}", KN_DAYS[d.weekday()]
    if spec.get("time"):
        hh, mm = (int(v) for v in spec["time"].split(":"))
        if 4 <= hh < 12:
            part = "ಬೆಳಿಗ್ಗೆ"
        elif 12 <= hh < 16:
            part = "ಮಧ್ಯಾಹ್ನ"
        elif 16 <= hh < 20:
            part = "ಸಂಜೆ"
        else:
            part = "ರಾತ್ರಿ"
        bot += f" • {part} {hh % 12 or 12}:{mm:02d}"
    return top, bot


def masthead_overlay(out_png, W, H, spec):
    """The reel masthead (brand.components.masthead: logo + wordmark + tagline, date on the right)
    across the top of a 16:9 frame on a soft top veil, exactly as reels carry it."""
    from brand.components import masthead
    from brand.surface import Surface, scrim
    fs = W / 1920.0
    top, bot = _date_lines(spec)
    top, bot = spec.get("right_top", top), spec.get("right_bot", bot)
    scale = spec.get("scale", 1.05) * fs
    x, y = 96 * fs, 54 * fs
    sf = Surface(W, H, 2, bg=(0, 0, 0, 0))
    scrim(sf, 0, y + 68 * scale + 90 * fs, C.ink_950, spec.get("scrim", 0.62), 0.0, curve=1.5)
    masthead(sf, x, y, W - 2 * x, right_top=top, right_bot=bot, scale=scale, on_photo=True, rule_below=False)
    sf.img.resize((W, H), Image.LANCZOS).save(out_png)
    return out_png


def render_all(cfg):
    """Returns {'intro', 'outro', 'masthead': png, 'lt': [png, ...]} under <work>/cards."""
    W, H = cfg["resolution"]
    out = cfg["work"] / "cards"
    out.mkdir(parents=True, exist_ok=True)
    logo = ROOT / cfg["logo"]
    res = {"lt": [], "masthead": masthead_overlay(out / "masthead.png", W, H, cfg["masthead"])}
    for kind in ("intro", "outro"):
        c = cfg["cards"][kind]
        seg = cfg["segments"][-1 if kind == "outro" else 0]
        clip, t = c.get("bg") or [seg["clip"], (seg["in"] + seg["out"]) / 2]
        frame = grab_frame(cfg["footage"] / clip, t, W, H, out / f"bg_{kind}.png")
        res[kind] = title_card(frame, out / f"{kind}.png", W, H, logo, c["title"], c.get("lines", []), kind)
    for k, lt in enumerate(cfg["lower_thirds"]):
        res["lt"].append(lower_third(out / f"lt_{k}.png", W, H, lt["title"], lt.get("subtitle", "")))
    return res


if __name__ == "__main__":
    import argparse
    from build import load_config
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    for k, v in render_all(load_config(a.project, a.preview)).items():
        print(k, v)
