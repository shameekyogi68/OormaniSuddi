"""
ಊರ್ಮನಿ ಸುದ್ದಿ — the news layer on a real-footage Reel (D96).
============================================================
The footage is the story; this is the type that rides on it, in the Paper &
Red look (D92), laid out around Instagram's own interface (tokens.ReelsChrome):

  0 – 2 s    HOOK      the news in huge type, before anyone can swipe
  2 s –      TOP BAND  the red bug, place and date — below the "← Reels" header
             STORY     one paper card above the caption, left of the buttons:
                       ಬ್ರೇಕಿಂಗ್ / kicker, the headline, ONE fact at a time,
                       the footage credit — nothing smaller than 28 px
  last 2 s   END CARD  source, footage credit, who verified it, follow

Every text box is checked against the forbidden regions and the layout
refuses rather than draws over them. The reel that prompted this (MRPL,
2026-09-30) had its masthead under the header, its date under the camera
icon and its card under the like/share column.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFilter

from . import paper as pp
from . import typo
from .content import ContentError, asserts_guilt
from .surface import Surface
from .tokens import Brand, C, Paper as P, ReelsChrome as RC

MIN_TYPE = 28          # px at 1080 wide; the smallest text on any frame


@dataclass
class News:
    headline: str
    place: str = ''
    date: str = ''
    kicker: str = 'ಬ್ರೇಕಿಂಗ್'
    hook: str = ''                       # 2–5 words; defaults to the ink half
    facts: list[str] = field(default_factory=list)
    credit: str = ''                     # "ವೀಡಿಯೊ ಕೃಪೆ: …" — required
    source: str = ''
    verified_by: str = ''
    category: str = ''
    convicted: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> 'News':
        known = set(cls.__dataclass_fields__)
        extra = set(d) - known
        if extra:
            raise ContentError(f'news: unknown field(s) {sorted(extra)}; '
                               f'valid: {sorted(known)}')
        return cls(**d)

    def validate(self) -> 'News':
        if not self.headline.strip():
            raise ContentError('news.headline is required')
        if not self.credit.strip():
            raise ContentError('news.credit is required — whose footage is this? '
                               '"ವೀಡಿಯೊ ಕೃಪೆ: ಊರ್ಮನಿ ಸುದ್ದಿ" if ours')
        if not self.source.strip():
            raise ContentError('news.source is required (D55): who said so?')
        if self.category in ('crime', 'breaking') and not self.convicted:
            for where, text in (('headline', self.headline), ('hook', self.hook)):
                hits = asserts_guilt(text)
                if hits:
                    raise ContentError(
                        f'news.{where} states guilt as fact ({", ".join(hits)}); '
                        'it travels alone — write it as an allegation (D29)')
        return self

    @property
    def hook_text(self) -> str:
        return self.hook.strip() or pp.split_headline(self.headline)[0].rstrip(':')

    @property
    def ink_only(self) -> bool:
        head = self.headline + ' ' + self.hook
        return (self.category in pp.INK_ONLY
                or any(w in head for w in pp.DEATH_WORDS))


# ─────────────────────────────────────────────────────────────────────────────
#  THE FORBIDDEN REGIONS
# ─────────────────────────────────────────────────────────────────────────────

def forbidden(W: int, H: int) -> list[tuple[str, tuple[float, float, float, float]]]:
    f = W / 1080
    return [('the "← Reels" header', (0, 0, W, RC.top * f)),
            ('the caption and comment bar', (0, RC.bottom * f, W, H)),
            ('the like / share buttons', (RC.rail_x * f, RC.rail_top * f, W, RC.bottom * f))]


def check(boxes: dict[str, tuple], W: int, H: int) -> None:
    """Refuse any text box that touches Instagram's own interface."""
    for name, (x0, y0, x1, y1) in boxes.items():
        for what, (a0, b0, a1, b1) in forbidden(W, H):
            if x0 < a1 and x1 > a0 and y0 < b1 and y1 > b0:
                raise ContentError(f'{name} overlaps {what}: {tuple(round(v) for v in (x0, y0, x1, y1))}')


def _sf(W: int, H: int, bg=(0, 0, 0, 0)) -> Surface:
    return Surface(W, H, 2, bg=bg)


def _out(sf: Surface) -> Image.Image:
    return sf.img.resize((sf.w, sf.h), Image.Resampling.LANCZOS)


# ─────────────────────────────────────────────────────────────────────────────
#  THE FRAMES
# ─────────────────────────────────────────────────────────────────────────────

def hook(n: News, W: int = 1080, H: int = 1920) -> tuple[Image.Image, dict]:
    f = W / 1080
    m = P.margin * f
    sf = _sf(W, H)
    shade = Image.new('RGBA', (W * 2, H * 2), (0, 0, 0, 0))
    ImageDraw.Draw(shade).rectangle((0, 0, W * 2, int(H * 2 * 0.46)),
                                    fill=(0, 0, 0, 120))
    sf.img.alpha_composite(shade.filter(ImageFilter.GaussianBlur(70)))
    y = (RC.top + 170) * f
    kf = typo.font('kn', sf.s(36 * f), weight=pp.HEAD_WEIGHT)
    kw = typo.text_width(n.kicker, kf) / sf.ss + 40 * f
    pp._rect(sf, (m, y, m + kw, y + 58 * f), C.red_500)
    typo.draw_text(sf.img, n.kicker, sf.s(m + 20 * f), sf.s(y + 42 * f), kf, C.paper_0)
    b = typo.fit(n.hook_text, 'kn', sf.s(118 * f), sf.s(76 * f),
                 sf.s(RC.rail_x * f - m), sf.s(320 * f), 1.15,
                 weight=pp.HEAD_WEIGHT, max_lines=2)
    top = y + 90 * f
    bot = typo.draw_block(sf.img, b, sf.s(m), sf.s(top), C.paper_0,
                          shadow=(0, sf.s(4), sf.s(22), (0, 0, 0, 220))) / sf.ss
    boxes = {'hook kicker': (m, y, m + kw, y + 58 * f),
             'hook': (m, top, m + b.width / sf.ss, bot)}
    check(boxes, W, H)
    return _out(sf), boxes


def top_band(n: News, W: int = 1080, H: int = 1920) -> tuple[Image.Image, dict]:
    f = W / 1080
    m = P.margin * f
    sf = _sf(W, H)
    y = (RC.top + 10) * f
    right = pp.bug(sf, m, y, int(P.bug_reel * f))
    line = '  ·  '.join(x for x in (n.place, n.date) if x)
    boxes = {'bug': (m, y, right, y + P.bug_reel * 1.9 * f)}
    if line:
        lf = typo.font_for(line, 'kn_var', sf.s(30 * f), weight=680)
        base = y + 110 * f
        typo.draw_text(sf.img, line, sf.s(m), sf.s(base), lf, C.paper_0,
                       shadow=(0, sf.s(2), sf.s(8), (0, 0, 0, 210)))
        boxes['place and date'] = (m, base - 30 * f,
                                   m + typo.text_width(line, lf) / sf.ss, base + 8 * f)
    check(boxes, W, H)
    return _out(sf), boxes


def story(n: News, fact: int | None = None, W: int = 1080, H: int = 1920
          ) -> tuple[Image.Image, dict]:
    """The paper card, sized to its copy and pinned just above the caption."""
    f = W / 1080
    m = P.margin * f
    x0, x1 = m, (RC.rail_x - 24) * f
    w, pad = x1 - x0, 28 * f
    text = n.facts[fact] if fact is not None and n.facts else ''

    def lay(sf_):
        y = 96 * f
        y = pp.headline(sf_, x0 + pad, y, w - 2 * pad, n.headline, 280 * f,
                        hi=int(58 * f), lo=int(44 * f), ink_only=n.ink_only)
        if text:
            y += 18 * f
            pp._rect(sf_, (x0 + pad, y, x1 - pad, y + 2 * f), C.paper_200)
            pp._rect(sf_, (x0 + pad, y + 24 * f, x0 + pad + 12 * f, y + 36 * f), C.gold_600)
            y = pp.body(sf_, x0 + pad + 28 * f, y + 12 * f, w - 2 * pad - 28 * f,
                        text, size=int(38 * f), weight=600, fill=C.ink_800,
                        max_h=150 * f, lo=int(MIN_TYPE * f))
        return y + 58 * f

    probe = _sf(W, H)
    card_h = lay(probe)
    y0 = RC.bottom * f - 40 * f - card_h
    sf = _sf(W, H)
    pp._rect(sf, (x0, y0, x1, y0 + card_h), C.paper_50)
    pp._rect(sf, (x0, y0, x1, y0 + 8 * f), C.gold_500)
    kf = typo.font('kn', sf.s(32 * f), weight=pp.HEAD_WEIGHT)
    kw = typo.text_width(n.kicker, kf) / sf.ss + 36 * f
    pp._rect(sf, (x0 + pad, y0 + 26 * f, x0 + pad + kw, y0 + 76 * f), C.red_500)
    typo.draw_text(sf.img, n.kicker, sf.s(x0 + pad + 18 * f), sf.s(y0 + 62 * f), kf, C.paper_0)
    if n.place:
        pf = typo.font_for(n.place, 'kn_var', sf.s(30 * f), weight=680)
        typo.draw_text(sf.img, typo.ellipsize(n.place, pf, sf.s(w - kw - 3 * pad)),
                       sf.s(x0 + pad + kw + 16 * f), sf.s(y0 + 62 * f), pf, C.ink_500)
    # the card, shifted into place
    body = _sf(W, H)
    lay(body)
    sf.img.alpha_composite(body.img, (0, int(sf.s(y0))))
    cf = typo.font_for(n.credit, 'kn_var', sf.s(MIN_TYPE * f), weight=560)
    typo.draw_text(sf.img, typo.ellipsize(n.credit, cf, sf.s(w - 2 * pad)),
                   sf.s(x0 + pad), sf.s(y0 + card_h - 20 * f), cf, C.ink_500)
    boxes = {'story card': (x0, y0, x1, y0 + card_h)}
    check(boxes, W, H)
    return _out(sf), boxes


def end_card(n: News, W: int = 1080, H: int = 1920) -> tuple[Image.Image, dict]:
    """Source, footage credit and verification get a whole frame here —
    never a line too small to read under the story."""
    f = W / 1080
    m = P.margin * f
    right = (RC.rail_x - 40) * f
    sf = _sf(W, H, bg=(*C.paper_50, 255))
    pp.roundlogo(sf, (m + right) / 2 - 160 * f, 380 * f, 320 * f)
    tl = typo.layout(Brand.tagline.replace('  •  ', ' · '),
                     typo.font('kn', sf.s(68 * f), weight=pp.HEAD_WEIGHT),
                     sf.s(right - m), 1.2, align='center')
    typo.draw_block(sf.img, tl, sf.s(m), sf.s(760 * f), C.ink_950, box_w=sf.s(right - m))
    y = 930 * f
    pp._rect(sf, (m + 40 * f, y, right, y + 3 * f), C.ink_950)
    y += 64 * f
    rows = [('ಮೂಲ', n.source), ('ವೀಡಿಯೊ', n.credit.split(':', 1)[-1].strip()),
            ('ಪರಿಶೀಲನೆ', n.verified_by)]
    for k, v in rows:
        if not v:
            continue
        pp.meta(sf, m + 40 * f, y, k, C.gold_800, size=int(34 * f), weight=760)
        pp.meta(sf, m + 280 * f, y, v, C.ink_950, size=int(34 * f), weight=560,
                max_w=right - m - 280 * f)
        y += 62 * f
    ff = typo.font('kn', sf.s(44 * f), weight=pp.HEAD_WEIGHT)
    txt = f'ಫಾಲೋ ಮಾಡಿ  {Brand.handle}'
    tw = typo.text_width(txt, ff) / sf.ss + 80 * f
    cx = (m + right) / 2
    by = max(y + 40 * f, 1230 * f)
    pp._rect(sf, (cx - tw / 2, by, cx + tw / 2, by + 90 * f), C.gold_500)
    typo.draw_text(sf.img, txt, sf.s(cx), sf.s(by + 60 * f), ff, C.ink_950, anchor_x='c')
    boxes = {'follow': (cx - tw / 2, by, cx + tw / 2, by + 90 * f),
             'rows': (m + 40 * f, 930 * f, right, y)}
    check(boxes, W, H)
    return _out(sf), boxes


def schedule(n: News, story_start: float, outro_start: float
             ) -> list[tuple[str, int | None, float, float]]:
    """(layer, fact index, from, to) for every news layer on the timeline.
    The hook holds the opening; the facts share what is left before the end
    card, each on screen at least ReelsChrome.fact_min_seconds."""
    out = [('hook', None, 0.0, story_start)]
    span = max(0.0, outro_start - story_start)
    facts = list(range(len(n.facts))) or [None]
    fit = max(1, int(span // RC.fact_min_seconds))
    facts = facts[:fit]
    step = span / len(facts)
    for k, fi in enumerate(facts):
        out.append(('story', fi, story_start + k * step, story_start + (k + 1) * step))
    out.append(('top', None, story_start, outro_start))
    return out
