"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Surface & imaging
=================================
The canvas, the house photo grade, and the primitives that replace the
outlined-rounded-box habit with things that actually look printed:

  * scrim()    an eased gradient veil, so a photo dissolves into the page
               instead of ending at a visible seam
  * rule()     a hairline, not a border
  * grain()    fine luminance noise; flat digital black is the cheapest-looking
               thing on a phone screen, and grain is what kills it
  * place_photo() the single house grade every image passes through

Everything is drawn at `ss`x and downsampled once, at the end, with Lanczos.
Layout code always speaks in final delivery pixels.
"""
from __future__ import annotations

import os
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

from .tokens import Grade, Role, C, alpha, mix, Ease, clamp01

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─────────────────────────────────────────────────────────────────────────────
#  SURFACE
# ─────────────────────────────────────────────────────────────────────────────

class Surface:
    """A supersampled RGBA canvas. All coordinates passed in are in final
    delivery pixels; the surface multiplies by `ss` internally."""

    def __init__(self, w: int, h: int, ss: int = 2, bg=Role.page):
        self.w, self.h, self.ss = w, h, ss
        self.img = Image.new('RGBA', (w * ss, h * ss),
                             bg if len(bg) == 4 else (*bg, 255))

    # -- coordinate helpers ---------------------------------------------------
    def s(self, v):
        """Scale a scalar or a sequence into device pixels."""
        if isinstance(v, (list, tuple)):
            return [x * self.ss for x in v]
        return v * self.ss

    @property
    def draw(self) -> ImageDraw.ImageDraw:
        return ImageDraw.Draw(self.img)

    def layer(self) -> Image.Image:
        return Image.new('RGBA', self.img.size, (0, 0, 0, 0))

    def merge(self, lay: Image.Image, at=(0, 0)):
        self.img.alpha_composite(lay, (int(at[0] * self.ss), int(at[1] * self.ss)))

    # -- output ---------------------------------------------------------------
    def finish(self) -> Image.Image:
        out = self.img
        if self.ss != 1:
            out = out.resize((self.w, self.h), Image.Resampling.LANCZOS)
        return out.convert('RGB')

    def save(self, path: str, quality: int = 95, target_kb: int | None = None):
        img = self.finish()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.jpg', '.jpeg'):
            # 4:4:4 chroma — Kannada matras are thin and coloured type on a red
            # rail turns to mush under the default 4:2:0 subsampling.
            img.save(path, 'JPEG', quality=quality, subsampling=0,
                     optimize=True, progressive=True)
            if target_kb:
                _fit_to_size(img, path, target_kb, quality)
        else:
            img.save(path, optimize=True)
        return path


def _fit_to_size(img: Image.Image, path: str, target_kb: int,
                 start_quality: int = 95) -> None:
    """Bring a forward-bound JPEG under its target without wrecking the type.

    A broadsheet is the format meant to grow this channel, and it grows it by
    being forwarded on rural mobile data. A 5 MB file does not get forwarded;
    it gets left in the chat. Quality 95 at 4:4:4 is the right choice for a
    card someone opens — it is the wrong choice for a file someone sends.

    Quality comes down in steps first, because that costs the least. Chroma
    subsampling is the last resort and is stepped to 4:2:2, never 4:2:0:
    Kannada matras are one or two pixels wide and 4:2:0 is what turns a
    coloured conjunct on the category rail into a smear.
    """
    import os as _os
    ceiling = target_kb * 1024
    if _os.path.getsize(path) <= ceiling:
        return
    for q in range(start_quality - 5, 63, -6):
        img.save(path, 'JPEG', quality=q, subsampling=0,
                 optimize=True, progressive=True)
        if _os.path.getsize(path) <= ceiling:
            return
    for q in (78, 72, 66):
        img.save(path, 'JPEG', quality=q, subsampling=1,   # 4:2:2
                 optimize=True, progressive=True)
        if _os.path.getsize(path) <= ceiling:
            return
    # Still over. Stop rather than degrade further — past this the honest
    # diagnosis is that the card carries more picture than a forward can, and
    # qa.inspect() will say so. Silently shipping mush would be worse.


# ─────────────────────────────────────────────────────────────────────────────
#  GRADIENTS & SCRIMS
# ─────────────────────────────────────────────────────────────────────────────

def _dither(a: np.ndarray, amt: float = 0.6) -> np.ndarray:
    """Break up 8-bit banding in long gradients."""
    n = np.random.default_rng(7).uniform(-amt, amt, a.shape[:2])[..., None]
    return np.clip(a + n, 0, 255)


def vgradient(sf: Surface, y0: float, y1: float, c_top, c_bot,
              a_top: float = 1.0, a_bot: float = 1.0, ease=None):
    """Vertical gradient band drawn onto the surface."""
    ss = sf.ss
    Y0, Y1 = int(y0 * ss), int(y1 * ss)
    h = max(1, Y1 - Y0)
    t = np.linspace(0.0, 1.0, h)
    if ease:
        t = np.array([ease(float(x)) for x in t])
    rgbv = np.stack([np.full(h, c_top[i]) + (c_bot[i] - c_top[i]) * t for i in range(3)], 1)
    av = (np.full(h, a_top) + (a_bot - a_top) * t) * 255.0
    band = np.concatenate([rgbv, av[:, None]], 1)[:, None, :]
    band = np.repeat(band, sf.w * ss, axis=1)
    band[..., :3] = _dither(band[..., :3])
    sf.img.alpha_composite(
        Image.fromarray(band.astype(np.uint8), 'RGBA'), (0, Y0))


def scrim(sf: Surface, y0: float, y1: float, color=C.ink_950,
          a0: float = 0.0, a1: float = 1.0, curve: float = 2.2):
    """The workhorse. A veil that dissolves a photograph into the page.

    The ramp is a smoothstep on a power-shaped input, not a plain power curve.
    A plain power curve saves all of its darkening for the last few percent, so
    the picture is still 25% visible right where the type begins and then snaps
    shut. Smoothstep is flat at both ends: invisible where it starts, and
    already solid a little before it finishes, which is what makes the join
    impossible to locate."""
    ss = sf.ss
    Y0, Y1 = int(y0 * ss), int(y1 * ss)
    h = max(1, Y1 - Y0)
    u = np.linspace(0.0, 1.0, h) ** (curve * 0.5)
    t = u * u * (3.0 - 2.0 * u)
    av = (a0 + (a1 - a0) * t) * 255.0
    band = np.zeros((h, 1, 4))
    band[..., 0], band[..., 1], band[..., 2] = color[0], color[1], color[2]
    band[..., 3] = av[:, None]
    band = np.repeat(band, sf.w * ss, axis=1)
    sf.img.alpha_composite(Image.fromarray(band.astype(np.uint8), 'RGBA'), (0, Y0))


def radial_glow(sf: Surface, cx: float, cy: float, radius: float, color,
                a_center: float = 0.5):
    """A soft light bloom — used behind the logo mark and under headlines to
    lift them off the page without a box."""
    ss = sf.ss
    R = int(radius * ss)
    if R <= 0:
        return
    # Build only the part of the bloom that actually lands on the canvas.
    # A glow is usually far wider than the frame it lifts — page_base asks for
    # 1.15× the page width — so the full 2R square is mostly off-canvas waste.
    # At 1080 that was merely wasteful; at 3840 the square reaches 17664² and
    # PIL refuses it as a decompression bomb, which is why the 4K bulletin
    # could not render at all. The falloff is still measured from the true
    # centre and radius, so on-canvas pixels are unchanged.
    W, H = sf.img.size
    x0, y0 = int(cx * ss) - R, int(cy * ss) - R
    ix0, iy0 = max(0, x0), max(0, y0)
    ix1, iy1 = min(W, x0 + 2 * R), min(H, y0 + 2 * R)
    if ix1 <= ix0 or iy1 <= iy0:
        return

    # float64 throughout, as the unclipped version was: the falloff is raised
    # to 2.4 and then truncated to uint8, and in float32 a scattering of pixels
    # lands on the other side of a rounding boundary. That is invisible to the
    # eye and still a different image to the golden hash.
    xx = (np.arange(ix0 - x0, ix1 - x0, dtype=np.float64) - R)[None, :]
    yy = (np.arange(iy0 - y0, iy1 - y0, dtype=np.float64) - R)[:, None]
    d = np.sqrt(xx ** 2 + yy ** 2) / R
    a = np.clip(1.0 - d, 0, 1) ** 2.4 * a_center * 255.0

    lay = np.zeros((iy1 - iy0, ix1 - ix0, 4), dtype=np.float64)
    lay[..., 0], lay[..., 1], lay[..., 2] = color[0], color[1], color[2]
    lay[..., 3] = a
    sf.img.alpha_composite(Image.fromarray(lay.astype(np.uint8), 'RGBA'),
                           (ix0, iy0))


def grain(sf: Surface, sigma: float = 4.0, shadow_bias: float = 0.55):
    """Two-frequency luminance grain over the whole surface.

    A fine layer (the emulsion's bite) plus a soft coarse layer — the same
    noise, blurred wide, at low amplitude — which gives the clumpy, layered
    structure of real film instead of uniform static. More in the shadows,
    like film. This is the difference between 'rendered' and 'printed'."""
    a = np.asarray(sf.img).astype(np.float32)
    rng = np.random.default_rng(20260825)
    n = rng.normal(0.0, sigma, a.shape[:2]).astype(np.float32)
    coarse = np.asarray(Image.fromarray(
        np.clip(n * 16 + 128, 0, 255).astype(np.uint8), 'L')
        .filter(ImageFilter.GaussianBlur(max(2, a.shape[1] // 90)))
    ).astype(np.float32)
    coarse = (coarse - 128.0) / 16.0
    n = n + coarse * 0.15
    lum = a[..., :3].mean(2) / 255.0
    weight = (1.0 - lum) * shadow_bias + (1.0 - shadow_bias)
    a[..., :3] += (n * weight)[..., None]
    sf.img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def rule(sf: Surface, x0: float, y: float, x1: float, color=Role.hairline,
         weight: float = 1.0):
    """A hairline. `weight` is in final pixels and may be fractional — at ss=2
    a 0.5px rule is a real, crisp half-pixel line after downsampling."""
    ss = sf.ss
    lay = sf.layer()
    ImageDraw.Draw(lay).rectangle(
        [x0 * ss, y * ss, x1 * ss, y * ss + max(1, round(weight * ss)) - 1],
        fill=color)
    sf.img.alpha_composite(lay)


def _taper_rule(sf: Surface, x0: float, y: float, x1: float, c_lo, c_hi,
                weight: float, a_end: float, a_mid: float):
    """Shared engine for gilded_rule / faded_rule: a horizontal rule whose
    colour ramps lo→hi→lo and whose alpha tapers to nothing at both ends.
    Drawn with the same dither as the gradients so it never bands."""
    ss = sf.ss
    W = int(x1 * ss) - int(x0 * ss)
    if W <= 0:
        return
    t = np.abs(np.linspace(-1.0, 1.0, W))
    rgbv = np.stack([
        c_hi[i] + (c_lo[i] - c_hi[i]) * t for i in range(3)], 1)
    a = (a_mid + (a_end - a_mid) * t ** 1.6) * 255.0
    band = np.concatenate([rgbv, a[:, None]], 1)[None, :, :]
    band = np.repeat(band, max(1, round(weight * ss)), 0)
    band[..., :3] = _dither(band[..., :3], 0.6)
    lay = Image.new('RGBA', (W, band.shape[0]), (0, 0, 0, 0))
    sf.img.alpha_composite(
        Image.fromarray(band.astype(np.uint8), 'RGBA'), (int(x0 * ss), int(y * ss)))


def gilded_rule(sf: Surface, x0: float, y: float, x1: float,
                weight: float = 1.25, on_photo: bool = False):
    """An engraved gold hairline: brighter at its centre, dissolving into the
    page at both ends. Still one hairline, still one accent — the luxury is
    that it looks machined rather than stamped."""
    _taper_rule(sf, x0, y, x1, C.gold_600, C.gold_400, weight,
                0.04, 0.42 if on_photo else 0.36)


def faded_rule(sf: Surface, x0: float, y: float, x1: float,
               color=Role.hairline, weight: float = 1.0, a_mid: float = 0.16):
    """A paper hairline whose ends taper away, like the printed rule of a
    quality masthead — no hard start or stop to catch the eye."""
    _taper_rule(sf, x0, y, x1, color[:3], color[:3], weight, 0.0, a_mid)


def gilded_vrule(sf: Surface, x: float, y0: float, y1: float,
                 weight: float = 3, a_mid: float = 0.95,
                 lo=None, hi=None):
    """The vertical twin of gilded_rule, for quote bars and takeaway rails."""
    lo = lo or C.gold_600
    hi = hi or C.gold_400
    ss = sf.ss
    H = int(y1 * ss) - int(y0 * ss)
    if H <= 0:
        return
    t = np.abs(np.linspace(-1.0, 1.0, H))
    rgbv = np.stack([
        hi[i] + (lo[i] - hi[i]) * t for i in range(3)], 1)
    a = (a_mid + (0.30 * a_mid - a_mid) * t ** 1.6) * 255.0
    band = np.concatenate([rgbv, a[:, None]], 1)[:, None, :]
    band = np.repeat(band, max(1, round(weight * ss)), 1)
    sf.img.alpha_composite(
        Image.fromarray(band.astype(np.uint8), 'RGBA'), (int(x * ss), int(y0 * ss)))


def vrule(sf: Surface, x: float, y0: float, y1: float, color, weight: float = 1.0):
    ss = sf.ss
    lay = sf.layer()
    ImageDraw.Draw(lay).rectangle(
        [x * ss, y0 * ss, x * ss + max(1, round(weight * ss)) - 1, y1 * ss], fill=color)
    sf.img.alpha_composite(lay)


def panel(sf: Surface, box, fill, radius: float = 0, outline=None, weight: float = 1.0):
    ss = sf.ss
    lay = sf.layer()
    d = ImageDraw.Draw(lay)
    b = [box[0] * ss, box[1] * ss, box[2] * ss, box[3] * ss]
    if radius:
        d.rounded_rectangle(b, radius=radius * ss, fill=fill,
                            outline=outline, width=max(1, round(weight * ss)))
    else:
        d.rectangle(b, fill=fill, outline=outline, width=max(1, round(weight * ss)))
    sf.img.alpha_composite(lay)


def soft_shadow(sf: Surface, box, blur: float = 26, dy: float = 10,
                a: float = 0.55, radius: float = 0):
    ss = sf.ss
    pad = int((blur * 3 + abs(dy)) * ss)
    w = int((box[2] - box[0]) * ss) + pad * 2
    h = int((box[3] - box[1]) * ss) + pad * 2
    lay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    inner = [pad, pad + dy * ss, w - pad, h - pad + dy * ss]
    if radius:
        d.rounded_rectangle(inner, radius=radius * ss, fill=(0, 0, 0, int(a * 255)))
    else:
        d.rectangle(inner, fill=(0, 0, 0, int(a * 255)))
    lay = lay.filter(ImageFilter.GaussianBlur(blur * ss))
    sf.img.alpha_composite(lay, (int(box[0] * ss) - pad, int(box[1] * ss) - pad))


# ─────────────────────────────────────────────────────────────────────────────
#  PHOTOGRAPHY — the house grade
# ─────────────────────────────────────────────────────────────────────────────

def _scurve(x: np.ndarray, amount: float) -> np.ndarray:
    """Filmic contrast. Pivots at 0.5, preserves both ends — no clipped blacks
    or blown highlights, which is what a plain contrast bump does."""
    if amount <= 0:
        return x
    k = 1.0 + amount * 6.0
    y = 1.0 / (1.0 + np.exp(-k * (x - 0.5)))
    lo = 1.0 / (1.0 + np.exp(k * 0.5))
    hi = 1.0 / (1.0 + np.exp(-k * 0.5))
    y = (y - lo) / (hi - lo)
    return x * (1 - amount) + y * amount


def house_grade(im: Image.Image, g: Grade = Grade, strength: float = 1.0,
                mono: bool = False) -> Image.Image:
    """The one grade every photograph in this brand passes through.

    Deliberately gentle. It exists to make a feed of images from many different
    cameras and stringers read as one publication — not to stylise the news.
    """
    im = im.convert('RGB')
    a = np.asarray(im).astype(np.float32) / 255.0

    if g.exposure:
        a = np.clip(a * (2.0 ** (g.exposure * strength)), 0, 1)

    a = _scurve(a, g.contrast * strength)

    lum = (a * np.array([0.2126, 0.7152, 0.0722])).sum(2, keepdims=True)
    if mono:
        a = np.repeat(lum, 3, 2)
    else:
        sat = 1.0 + (g.saturation - 1.0) * strength
        a = np.clip(lum + (a - lum) * sat, 0, 1)

    # Split tone: cool shadows toward brand ink, warm highlights toward sunset.
    sh = np.clip(1.0 - lum * 2.0, 0, 1) ** 1.5
    hl = np.clip(lum * 2.0 - 1.0, 0, 1) ** 1.5
    st = np.array(g.shadow_tint, dtype=np.float32) / 255.0
    ht = np.array(g.high_tint, dtype=np.float32) / 255.0
    a = a + sh * (st - a) * (g.shadow_amt * strength)
    a = a + hl * (ht - a) * (g.high_amt * strength)
    a = np.clip(a, 0, 1)

    im = Image.fromarray((a * 255).astype(np.uint8), 'RGB')

    if g.clarity:
        # Local contrast on a wide radius — adds presence without haloing.
        im = Image.blend(im, im.filter(ImageFilter.UnsharpMask(
            radius=int(min(im.size) * 0.02) or 2, percent=110, threshold=3)),
            g.clarity * strength)

    if g.vignette:
        w, h = im.size
        yy, xx = np.mgrid[0:h, 0:w]
        # Elliptical (normalised to each axis' half-extent) so the fall-off is
        # even on any aspect — a 9:16 crop gets the same corner darkening as
        # a 16:9 one.
        d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        v = np.clip(1.0 - (d - 0.55) / 0.85, 0, 1) ** 1.1
        v = 1.0 - (1.0 - v) * (g.vignette * strength)
        im = Image.fromarray(
            np.clip(np.asarray(im).astype(np.float32) * v[..., None], 0, 255)
            .astype(np.uint8), 'RGB')

    if g.rolloff:
        # Filmic highlight shoulder. Above the knee the response is compressed
        # toward 1.0 asymptotically, so skies and highlights hold tone instead
        # of flattening into a digital white. Blended by amount, like the rest.
        a = np.asarray(im).astype(np.float32) / 255.0
        knee, amt = 0.82, g.rolloff * strength
        shoulder = knee + (1.0 - knee) * (1.0 - np.exp(-(np.clip(a - knee, 0, 1)
                                                          / max(1e-4, (1.0 - knee)))))
        a = np.where(a > knee, a * (1 - amt) + shoulder * amt, a)
        im = Image.fromarray((a * 255).astype(np.uint8), 'RGB')
    return im


def cover(im: Image.Image, w: int, h: int, focal=(0.5, 0.42),
          zoom: float = 1.0) -> Image.Image:
    """Crop-to-fill around a focal point.

    Default focal y is 0.42, not 0.5: in news photography the subject's face
    and the action sit above centre, and a naive centre crop decapitates people.
    """
    sc = max(w / im.width, h / im.height) * zoom
    nw, nh = max(w, int(im.width * sc)), max(h, int(im.height * sc))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    cx = int((nw - w) * clamp01(focal[0]))
    cy = int((nh - h) * clamp01(focal[1]))
    return im.crop((cx, cy, cx + w, cy + h))


def place_photo(sf: Surface, path: str, box, focal=(0.5, 0.42),
                zoom: float = 1.0, strength: float = 1.0, mono: bool = False,
                radius: float = 0, grade: bool = True,
                fade_bottom: float = 0.0, fade_top: float = 0.0
                ) -> Image.Image | None:
    """Grade, crop and paste a photograph into `box` (final-pixel coords).

    `fade_bottom` (0..1) fades the picture's own alpha to nothing over that
    fraction of its height. Fading the IMAGE is not the same as painting a dark
    veil over it: a veil is one particular colour and will always mismatch the
    page underneath by a shade, leaving a faint band exactly where you were
    trying to hide the join. An alpha fade lets whatever is beneath come
    through, so there is no join to find.
    """
    if not path or not os.path.exists(path):
        return None
    ss = sf.ss
    W = int((box[2] - box[0]) * ss)
    H = int((box[3] - box[1]) * ss)
    im = Image.open(path)
    im = cover(im, W, H, focal, zoom)
    if grade:
        im = house_grade(im, strength=strength, mono=mono)
    im = im.convert('RGBA')

    if fade_bottom or fade_top:
        a = np.ones(H, dtype=np.float32)
        if fade_bottom > 0:
            n = max(1, int(H * fade_bottom))
            u = np.linspace(0.0, 1.0, n)
            a[H - n:] = 1.0 - (u * u * (3.0 - 2.0 * u))
        if fade_top > 0:
            n = max(1, int(H * fade_top))
            u = np.linspace(0.0, 1.0, n)
            a[:n] = np.minimum(a[:n], u * u * (3.0 - 2.0 * u))
        mask = np.repeat((a * 255).astype(np.uint8)[:, None], W, axis=1)
        m = Image.fromarray(mask, 'L')
        if radius:
            rm = Image.new('L', (W, H), 0)
            ImageDraw.Draw(rm).rounded_rectangle([0, 0, W - 1, H - 1],
                                                 radius=radius * ss, fill=255)
            m = Image.fromarray(np.minimum(np.asarray(m), np.asarray(rm)), 'L')
        im.putalpha(m)
    elif radius:
        m = Image.new('L', (W, H), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, W - 1, H - 1],
                                            radius=radius * ss, fill=255)
        im.putalpha(m)

    sf.img.alpha_composite(im, (int(box[0] * ss), int(box[1] * ss)))
    return im


def duotone(im: Image.Image, dark, light) -> Image.Image:
    """Map luminance onto a two-colour ramp. Used only for backgrounds behind
    heavy type (quote cards, stat cards) where a full-colour photo would fight
    the words."""
    g = np.asarray(im.convert('L')).astype(np.float32) / 255.0
    d = np.array(dark, np.float32)
    l = np.array(light, np.float32)
    out = d + (l - d) * g[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB')


def logo(size: int, variant: str = 'circle') -> Image.Image:
    p = os.path.join(BASE_DIR, 'assets',
                     'logo_clean_circle.png' if variant == 'circle' else 'logo_clean_card.png')
    return Image.open(p).convert('RGBA').resize((size, size), Image.Resampling.LANCZOS)


def paste_logo(sf: Surface, x: float, y: float, size: float, variant='circle',
               glow: float = 0.0):
    ss = sf.ss
    if glow:
        radial_glow(sf, x + size / 2, y + size / 2, size * 0.95, C.gold_500, glow)
    lg = logo(int(size * ss), variant)
    sf.img.alpha_composite(lg, (int(x * ss), int(y * ss)))


# ─────────────────────────────────────────────────────────────────────────────
#  EDITORIAL PLATE — a designed visual for a story with no honest photograph
# ─────────────────────────────────────────────────────────────────────────────

def editorial_plate(sf: Surface, box, cat: dict, seed: str = '',
                    radius: float = 0, label: str = '', show_word: bool = False):
    """A branded plate for a story that has no honest photograph.

    Every slide needs something to look at, but a story with no picture must
    not be given a fake one. This is deliberately, visibly a GRAPHIC: the
    logo's horizon reduced to its geometry — a ruled sea, a gold sun on the
    horizon line, a category-tinted sky — with the category word set large and
    faint behind it.

    An earlier version rendered a soft photographic sunset. It was dropped: a
    blurry gradient sun reads as a bad photograph rather than as a designed
    plate, and a bad photograph is exactly what this exists to avoid.

    **It is a family, not one drawing.** With seventeen stock images and seven
    taluks, a photo-less story is not an exception — and one identical plate
    appearing four times in a carousel is the thing that makes a feed look
    generated. Every variable below is drawn from a stable digest of the
    headline, so a given story's plate is the same forever (the golden test
    depends on that) while two stories never share one. The grammar does not
    vary: ink sky lifted toward the category hue, a gold disc ON the horizon
    line, a ruled sea, a broken glint. Only the weather does. D66.
    """
    ss = sf.ss
    x0, y0, x1, y1 = [v * ss for v in box]
    W, H = int(x1 - x0), int(y1 - y0)
    if W <= 0 or H <= 0:
        return

    rail = cat.get('rail', C.sea_500)
    # NOT hash(): Python randomises string hashing per process, so the plate's
    # variation changed on every run and the golden test failed the moment it
    # was blessed. A stable digest keeps one story's plate identical forever.
    rnd = np.random.default_rng(
        zlib.crc32(seed.encode('utf-8')) if seed else 11)
    # The horizon rides with the aspect. On a 9:16 frame a horizon at mid-height
    # lands exactly where the headline sits, so on tall plates it goes high and
    # the ruled sea fills the lower half behind the type.
    aspect = H / max(1, W)
    # Horizon and sun position both ride with the aspect.
    #   portrait  — horizon high, sun centre-left; type fills the lower half
    #   square    — horizon mid
    #   landscape — horizon high AND the sun pushed right, so it counterweights
    #               the left-aligned headline instead of leaving the right third
    #               of a 16:9 frame empty
    landscape = aspect < 0.8
    horizon = 0.34 if aspect > 1.15 else (0.44 if aspect > 0.8 else 0.40)
    # The aspect decides where the horizon BELONGS; the seed moves it within a
    # band narrow enough that the type below it still has its room.
    horizon = float(np.clip(horizon + rnd.uniform(-0.035, 0.035), 0.28, 0.50))

    # Which coast this plate is. Each is the same geometry under different
    # weather — the variation a reader notices, and none of it photographic.
    mood = int(rnd.integers(0, 4))      # 0 clear · 1 banded · 2 overcast · 3 night

    # ── sky: ink, lifted toward the category hue near the horizon ────────
    yy = np.linspace(0.0, 1.0, H)[:, None]
    # How far the sky lifts toward the category hue, and how far the sea does.
    # Night keeps almost all of the ink; overcast lifts least of the four but
    # sits flatter, which is what reads as weather rather than as a bug.
    lift, wet = {0: (0.42, 0.16), 1: (0.50, 0.19),
                 2: (0.30, 0.13), 3: (0.20, 0.09)}[mood]
    top = np.array(C.ink_950, np.float32)
    mid = np.array(mix(C.ink_850, rail, lift), np.float32)
    sea = np.array(mix(C.ink_900, rail, wet), np.float32)
    deep = np.array(C.ink_950, np.float32)
    t_sky = np.clip(yy / horizon, 0, 1) ** 1.5
    t_sea = np.clip((yy - horizon) / (1 - horizon), 0, 1) ** 0.8
    plate = np.where(yy < horizon, top + (mid - top) * t_sky,
                     sea + (deep - sea) * t_sea)
    plate = np.repeat(plate[:, None, :], W, axis=1)
    # Dithered, like every other long gradient in the house — an undithered
    # plate sky bands exactly where the eye is drawn to the horizon.
    plate = _dither(plate, 0.6)
    im = Image.fromarray(np.clip(plate, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')

    d = ImageDraw.Draw(im, 'RGBA')
    hy = int(horizon * H)

    # ── the sky's weather ────────────────────────────────────────────────
    # Ruled bands, in the same engraved language as the sea, so a cloud is
    # drawn the way the water is drawn. Never soft, never photographic.
    if mood in (1, 2):
        n_band = int(rnd.integers(3, 6)) if mood == 1 else int(rnd.integers(5, 9))
        for b in range(n_band):
            # Bands crowd the lower sky. Spread evenly to the top they read as
            # a ruled grid; gathered near the horizon they read as cloud lying
            # over the sea, which is what a coastal evening actually looks
            # like — and it leaves the upper sky clear for the headline.
            t = (b + float(rnd.uniform(0.0, 0.6))) / n_band
            by = int(hy * (0.34 + 0.60 * (t ** 0.75)))
            bh = max(1, int(ss * (2.2 if mood == 1 else 1.3)))
            # A band is a SEGMENT, never a full rule: it starts somewhere and
            # ends somewhere, both varying, and never spans the whole frame.
            bw = W * float(rnd.uniform(0.18, 0.56))
            bx0 = float(rnd.uniform(-0.06, 1.06 - bw / W)) * W
            # Alpha varies per band; a stack at one value is a diagram.
            a_band = float(rnd.uniform(0.016, 0.034 if mood == 1 else 0.026))
            d.rectangle([int(bx0), by, int(bx0 + bw), by + bh - 1],
                        fill=alpha(C.paper_50, a_band))
    elif mood == 3:
        # Night: a scatter of single-pixel stars, thinning toward the horizon
        # so the sky still reads as having depth.
        for _ in range(int(rnd.integers(26, 46))):
            sx = int(rnd.uniform(0, W))
            t = float(rnd.uniform(0, 1)) ** 1.8      # crowd the top
            sy = int(t * hy * 0.88)
            a_star = 0.30 * (1.0 - sy / max(1.0, hy)) + 0.06
            sr = max(1, int(ss * 0.7))
            d.rectangle([sx, sy, sx + sr - 1, sy + sr - 1],
                        fill=alpha(C.paper_50, a_star))

    # ── ruled sea: subtle engraved horizon gradient ──────────────────────
    # Calm water carries fewer, wider-spaced rules; a rough sea carries more.
    rules_max = {0: 8, 1: 10, 2: 11, 3: 6}[mood]
    y, gap, k = hy + int(H * 0.040), H * 0.024, 0
    while y < H and k < rules_max:
        w = max(1, int(ss * 0.6))
        d.rectangle([0, y, W, y + w - 1],
                    fill=alpha(C.paper_50, max(0.01, 0.05 / (1.0 + k * 0.4))))
        gap *= 1.4 if mood != 2 else 1.28
        y += int(gap)
        k += 1

    # ── the sun: a crisp disc sitting ON the horizon, small ──────────────
    # Size and glow ride with the weather: a clear evening disc is larger and
    # warmer, an overcast one is small and barely lit, a night one is a moon.
    base_r = 0.038 if landscape else 0.052
    r = max(2, int(W * base_r * {0: 1.14, 1: 1.0, 2: 0.82, 3: 0.72}[mood]
                   * float(rnd.uniform(0.92, 1.08))))
    # The disc stays on its side of the frame — that placement counterweights
    # the type and is not a thing to randomise — but not at the same pixel.
    cx = int(W * ((0.70 if landscape else 0.30) + float(rnd.uniform(-0.07, 0.07))))
    disc = C.gold_500 if mood != 3 else mix(C.gold_300, C.paper_50, 0.45)
    glow_a = {0: 0.32, 1: 0.26, 2: 0.15, 3: 0.12}[mood]
    glow = Image.new('RGBA', (r * 8, r * 8), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([r * 3, r * 3, r * 5, r * 5],
                                 fill=alpha(disc, glow_a))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(r * 1.2)),
                       (cx - r * 4, hy - r * 4))
    d.ellipse([cx - r, hy - r, cx + r, hy + r], fill=(*disc, 255))

    # ── the sun's reflection: a broken gold glint down the sea ───────────
    # Stippled dashes directly under the sun, narrowing and fading with
    # distance — the one move that makes the plate read as a *scene*.
    # A calm sea holds a long glint; a rough or overcast one breaks it up.
    n_glint = {0: 8, 1: 7, 2: 5, 3: 6}[mood]
    glint_a = {0: 0.38, 1: 0.34, 2: 0.20, 3: 0.22}[mood]
    gy = hy + int(H * 0.022)
    gw, step = r * 1.35, int(H * 0.016)
    j = 0
    while gy < H - 2 and j < n_glint:
        fw = gw * (1.0 - 0.10 * j) * (0.55 + 0.45 * float(rnd.uniform(0, 1)))
        fx = cx + float(rnd.uniform(-0.18, 0.18)) * gw
        a_ref = max(0.0, glint_a - j * 0.052)
        if fw >= 1 and a_ref > 0.02:
            hh = max(1, int(ss * 0.8))
            d.rectangle([int(fx - fw), gy, int(fx + fw), gy + hh - 1],
                        fill=alpha(C.gold_400 if mood != 3 else C.gold_300,
                                   a_ref))
        gy += step
        j += 1

    # ── a headland, on the side the sun is not ───────────────────────────
    # A flat horizon from edge to edge reads as a diagram. One low silhouette
    # makes it a coast — drawn as a hard-edged polygon, not a blurred mass,
    # because the whole plate is engraved rather than photographed. Present on
    # most plates, absent on some, so even the silhouette is not a signature.
    if float(rnd.uniform(0, 1)) < 0.72:
        far_side = 0 if cx > W * 0.5 else 1          # opposite the disc
        hw = int(W * float(rnd.uniform(0.20, 0.38)))
        peak = int(H * float(rnd.uniform(0.022, 0.050)))
        shoulder = int(peak * float(rnd.uniform(0.30, 0.62)))
        if far_side == 0:
            pts = [(0, hy), (0, hy - shoulder),
                   (int(hw * 0.42), hy - peak), (hw, hy)]
        else:
            pts = [(W, hy), (W, hy - shoulder),
                   (W - int(hw * 0.42), hy - peak), (W - hw, hy)]
        d.polygon(pts, fill=alpha(C.ink_950, 0.82))

    # ── the horizon rule, drawn over the sun so it reads as a horizon ────
    d.rectangle([0, hy, W, hy + max(1, ss)], fill=alpha(C.gold_400, 0.62))

    if radius:
        m = Image.new('L', (W, H), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, W - 1, H - 1],
                                            radius=radius * ss, fill=255)
        im.putalpha(m)
    sf.img.alpha_composite(im, (int(x0), int(y0)))

    # The category word is OFF by default: on a card the eyebrow already names
    # the category two lines below, and repeating it in 100px ghost type is
    # decoration, not structure. Turn it on where the plate stands alone.
    if show_word:
        from . import typo
        txt = label or cat['kn']
        if landscape:
            # Upper left, where a 16:9 plate is otherwise empty sky.
            f = typo.font('kn', int(H * 0.155))
            typo.draw_text(sf.img, txt, x0 + W * 0.055, y0 + H * 0.30, f,
                           alpha(C.paper_50, 0.085))
        else:
            f = typo.font('kn', int(H * 0.165))
            tw = typo.text_width(txt, f)
            typo.draw_text(sf.img, txt, x0 + (W - tw) / 2, y0 + H * 0.90, f,
                           alpha(C.paper_50, 0.10))
