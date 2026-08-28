"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Design Tokens
=============================
Single source of truth for colour, type, grid, format and motion.
Nothing in this project should hard-code a colour, a font size or a margin.
Every value here is expressed in *final delivery pixels* (the 1080-wide space);
Surface handles supersampling, so layout code never thinks about it.

Palette is sampled from the channel logo, not invented:
  ink    #05070C .. #1B2333   the silhouette black-navy of the palms/gopura
  gold   #F5B301             the Arabian-Sea sunset disc  (logo 11.9% of pixels)
  red    #C81E1E             the ಸುದ್ದಿ speed-strokes     (logo  4.5% of pixels)
  paper  #F7F5F1             the logo's warm white, not pure #FFF
"""
from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
#  COLOUR
# ─────────────────────────────────────────────────────────────────────────────

def rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgba(h: str, a: float) -> tuple[int, int, int, int]:
    r, g, b = rgb(h)
    return (r, g, b, max(0, min(255, round(a * 255))))


def mix(c1, c2, t: float):
    """Linear blend of two RGB(A) tuples. t=0 → c1, t=1 → c2."""
    n = min(len(c1), len(c2))
    return tuple(round(c1[i] + (c2[i] - c1[i]) * t) for i in range(n))


def alpha(c, a: float):
    return (c[0], c[1], c[2], max(0, min(255, round(a * 255))))


class C:
    """Brand colour ramps. Use the semantic names below in preference to these."""
    # Ink — the page. Cool, slightly blue-black, matching the logo silhouettes.
    ink_950 = rgb('#03050A')
    ink_900 = rgb('#070A12')
    ink_850 = rgb('#0B1019')
    ink_800 = rgb('#101724')
    ink_700 = rgb('#18202F')
    ink_600 = rgb('#232D40')
    ink_500 = rgb('#36435C')
    ink_400 = rgb('#5A6880')
    ink_300 = rgb('#8794A8')

    # Paper — warm off-white, the logo's white is not #FFFFFF
    paper_0   = rgb('#FFFFFF')
    paper_50  = rgb('#F7F5F1')
    paper_100 = rgb('#EDEAE3')
    paper_200 = rgb('#D8D3C8')
    paper_300 = rgb('#B6AFA1')

    # Gold — the sunset. The single brand accent.
    gold_300 = rgb('#FFDE7A')
    gold_400 = rgb('#FFC93C')
    gold_500 = rgb('#F5B301')
    gold_600 = rgb('#D2930A')
    gold_700 = rgb('#96690A')

    # Signal red — reserved for genuinely breaking / alert states.
    red_400 = rgb('#E8443F')
    red_500 = rgb('#C81E1E')
    red_600 = rgb('#9E1414')

    # Sea — secondary, for civic / administrative stories.
    sea_400 = rgb('#2E8BA8')
    sea_500 = rgb('#0E5C7A')
    sea_600 = rgb('#08425A')

    # Supporting hues for the category rail only.
    amber_500  = rgb('#D97706')
    teal_500   = rgb('#0F766E')
    indigo_500 = rgb('#3F4A9E')
    plum_500   = rgb('#6D3A6B')
    moss_500   = rgb('#3F6B34')


# Semantic roles — layout code should reach for these.
class Role:
    page          = C.ink_950
    surface       = C.ink_900
    surface_alt   = C.ink_850
    hairline      = alpha(C.paper_50, 0.14)
    hairline_soft = alpha(C.paper_50, 0.07)
    hairline_gold = alpha(C.gold_500, 0.38)

    text_hi       = C.paper_0        # headlines
    text          = C.paper_100      # deck / body on ink
    text_dim      = C.ink_300        # meta, captions
    text_faint    = C.ink_400        # provenance small print

    on_paper_hi   = C.ink_950
    on_paper      = C.ink_800
    on_paper_dim  = C.ink_500

    accent        = C.gold_500
    accent_bright = C.gold_400
    alert         = C.red_500


# ─────────────────────────────────────────────────────────────────────────────
#  BRAND STRINGS
#  Every piece of standing copy lives here. Scattering these as literals across
#  templates is how a channel ends up with three different spellings of its own
#  coverage area on three different cards.
# ─────────────────────────────────────────────────────────────────────────────

class Brand:
    name      = 'ಊರ್ಮನಿ ಸುದ್ದಿ'
    tagline   = 'ನಮ್ಮ ಊರು  •  ನಮ್ಮ ಧ್ವನಿ'
    handle    = '@OormaniSuddi'
    # One word, not a list of towns. A list dates itself the moment you cover
    # somewhere that is not on it.
    coverage  = 'ಕರಾವಳಿ'
    bulletin  = 'ಕರಾವಳಿ ಬುಲೆಟಿನ್'
    follow_kn = 'ಪ್ರತಿದಿನದ ಕರಾವಳಿ ಸುದ್ದಿಗಾಗಿ ಫಾಲೋ ಮಾಡಿ'
    sources_kn = 'ಈ ಆವೃತ್ತಿಯ ಮೂಲಗಳು'

    # ── Publisher details ────────────────────────────────────────────────
    grievance_officer = ''
    grievance_email   = ''
    contact_email     = ''
    corrections_kn    = 'ತಿದ್ದುಪಡಿ ಅಥವಾ ಮಾಹಿತಿಗೆ ಸಂಪರ್ಕಿಸಿ'

    @classmethod
    def grievance_line(cls) -> str:
        """The line printed on the closing slide and in captions."""
        if cls.grievance_officer and cls.grievance_email:
            return (f'{cls.corrections_kn}: {cls.grievance_officer} · '
                    f'{cls.grievance_email}')
        if cls.grievance_email:
            return f'{cls.corrections_kn}: {cls.grievance_email}'
        if cls.handle:
            return f'{cls.corrections_kn}: Instagram DM {cls.handle}'
        return ''


# ─────────────────────────────────────────────────────────────────────────────
#  CATEGORY REGISTRY
#  The rail colour is the *only* place category colour is allowed to appear.
#  Gold stays the constant brand accent on every card — that consistency is
#  what makes a feed read as one publication rather than a pile of posts.
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIES: dict[str, dict] = {
    'breaking':  {'kn': 'ಬ್ರೇಕಿಂಗ್',        'en': 'BREAKING',    'rail': C.red_500},
    'crime':     {'kn': 'ಅಪರಾಧ ವರದಿ',      'en': 'CRIME',       'rail': C.red_600},
    'weather':   {'kn': 'ಹವಾಮಾನ',          'en': 'WEATHER',     'rail': C.amber_500},
    'civic':     {'kn': 'ಆಡಳಿತ',            'en': 'CIVIC',       'rail': C.sea_500},
    'health':    {'kn': 'ಆರೋಗ್ಯ',           'en': 'HEALTH',      'rail': C.teal_500},
    'education': {'kn': 'ಶಿಕ್ಷಣ',            'en': 'EDUCATION',   'rail': C.indigo_500},
    'culture':   {'kn': 'ಸಂಸ್ಕೃತಿ',          'en': 'CULTURE',     'rail': C.gold_600},
    'sport':     {'kn': 'ಕ್ರೀಡೆ',            'en': 'SPORT',       'rail': C.moss_500},
    'farm':      {'kn': 'ಕೃಷಿ',              'en': 'AGRICULTURE', 'rail': C.moss_500},
    'obituary':  {'kn': 'ನಿಧನ ವಾರ್ತೆ',      'en': 'OBITUARY',    'rail': C.plum_500},
    'explainer': {'kn': 'ವಿಶ್ಲೇಷಣೆ',         'en': 'EXPLAINER',   'rail': C.sea_400},
}


def category(key: str) -> dict:
    return CATEGORIES.get(key, CATEGORIES['explainer'])


# ─────────────────────────────────────────────────────────────────────────────
#  TYPOGRAPHY
#  Hand-tuned scale (roughly 1.22 ratio, snapped to even numbers) at the
#  1080-wide reference. Kannada needs more leading than Latin because the
#  vowel signs sit well above the headline and matras hang below the baseline.
# ─────────────────────────────────────────────────────────────────────────────

class T:
    """size, leading-multiplier, tracking (em, Latin only)"""
    # Leading is a multiple of the EM, not of the face's nominal metrics.
    # Kannada display type wants ~1.26em; Kannada body wants ~1.52em because
    # the matras need air to stay readable at a phone's arm's length.
    display  = (104, 1.22, 0.000)   # cover cards, thumbnails
    h1       = ( 78, 1.26, 0.000)   # primary headline, 4:5 post
    h2       = ( 64, 1.28, 0.000)
    h3       = ( 52, 1.30, 0.000)
    h4       = ( 42, 1.34, 0.000)
    deck     = ( 34, 1.44, 0.000)   # standfirst under the headline
    body     = ( 30, 1.52, 0.000)   # fact list, carousel body
    body_sm  = ( 27, 1.50, 0.000)
    meta     = ( 24, 1.36, 0.014)   # date, location, byline
    caption  = ( 22, 1.42, 0.010)   # photo caption
    eyebrow  = ( 21, 1.20, 0.140)   # ALL-CAPS Latin kicker — wide tracking
    micro    = ( 19, 1.30, 0.050)   # provenance small print
    nano     = ( 16, 1.30, 0.060)


# Font families → (file, default weight, default width)
FONTS = {
    # Primary Kannada. Noto shapes every conjunct correctly; it is the only
    # face allowed for headlines.
    'kn':        'fonts/NotoSansKannada-Bold.ttf',
    # Variable Kannada. Weight 100-800, Width 75-125. Used for anything that
    # needs a weight other than bold — decks, body, meta.
    'kn_var':    'fonts/AnekKannada-Variable.ttf',
    # Kannada serif, for pull-quotes and the broadsheet masthead.
    'kn_serif':  'fonts/NotoSerifKannada-Bold.ttf',
    # Latin. SF is the cleanest neutral available on this machine.
    'latin':     '/System/Library/Fonts/SFNS.ttf',
    'latin_alt': '/System/Library/Fonts/HelveticaNeue.ttc',
    'latin_srf': '/System/Library/Fonts/Supplemental/Georgia.ttf',
}


# ─────────────────────────────────────────────────────────────────────────────
#  GRID
# ─────────────────────────────────────────────────────────────────────────────

class Grid:
    unit     = 6      # baseline unit; every vertical offset is a multiple
    margin   = 72     # side margin on 1080-wide formats
    margin_l = 88     # generous margin, for quote/stat cards
    gutter   = 28
    rail     = 5      # width of the category rail
    radius   = 0      # house style is square corners. Rounding is opt-in.
    radius_soft = 10  # only for photo tiles and chips


def snap(v: float) -> int:
    """Snap a vertical position to the baseline unit."""
    return int(round(v / Grid.unit) * Grid.unit)


# ─────────────────────────────────────────────────────────────────────────────
#  FORMATS
#  safe = (left, top, right, bottom) inset within which *critical* content
#  must live so platform chrome never covers it.
# ─────────────────────────────────────────────────────────────────────────────

class Format:
    def __init__(self, key, w, h, ss, safe, note=''):
        self.key, self.w, self.h, self.ss, self.safe, self.note = key, w, h, ss, safe, note

    @property
    def size(self):
        return (self.w, self.h)

    def __repr__(self):
        return f'<Format {self.key} {self.w}x{self.h} @{self.ss}x>'


FORMATS = {
    # Instagram / Facebook feed. The workhorse.
    'post':      Format('post', 1080, 1350, 2, (72, 72, 72, 72),
                        'IG feed 4:5 — the tallest crop the feed allows'),
    'square':    Format('square', 1080, 1080, 2, (72, 72, 72, 72),
                        'Carousel slides, X, LinkedIn'),
    # Story / Reel / Short. Chrome is brutal here.
    'story':     Format('story', 1080, 1920, 2, (72, 250, 72, 340),
                        'IG story — top chrome ~230px, bottom reply bar ~320px'),
    'reel':      Format('reel', 1080, 1920, 2, (72, 230, 220, 480),
                        'IG Reel / YT Short — right action rail 200px, '
                        'bottom caption block up to 470px'),
    # YouTube
    'thumb':     Format('thumb', 1280, 720, 2, (48, 40, 48, 96),
                        'YT thumbnail — bottom-right 190x60 hidden by duration chip'),
    'yt_post':   Format('yt_post', 1080, 1080, 2, (72, 72, 72, 72), 'YT community post'),
    # Print-feel broadsheet, for the daily round-up
    'broadsheet': Format('broadsheet', 1080, 1620, 2, (64, 56, 64, 56),
                         'Daily edition 2:3 broadsheet'),
    # WhatsApp forward — small file, high legibility
    'forward':   Format('forward', 1080, 1350, 2, (72, 72, 72, 72), 'WhatsApp status/forward'),
    # Landscape video. No platform chrome to dodge, so the safe inset is purely
    # typographic margin.
    'bulletin':  Format('bulletin', 1920, 1080, 1, (96, 72, 96, 84),
                        'YouTube long-form bulletin 16:9'),
}


def fmt(key: str) -> Format:
    return FORMATS[key]


# ─────────────────────────────────────────────────────────────────────────────
#  PHOTO HOUSE GRADE
#  One look across every card. This is what makes a feed feel authored.
#  Values are deliberately gentle — the point is consistency, not an Instagram
#  filter. Documentary images must still read as documentary.
# ─────────────────────────────────────────────────────────────────────────────

class Grade:
    exposure    = 0.00    # stops
    contrast    = 0.16    # S-curve strength, 0..1
    saturation  = 0.88    # slight pull-back; news, not tourism
    rolloff     = 0.18    # filmic highlight shoulder — skies compress, not clip
    shadow_tint = C.ink_700      # cool the shadows toward brand ink
    shadow_amt  = 0.22
    high_tint   = rgb('#FFE2A8')  # warm the highlights toward the sunset
    high_amt    = 0.14
    grain       = 5.0     # sigma of luminance grain at 1080-scale
    grain_shadow_bias = 0.6   # more grain in shadows, like real film
    vignette    = 0.22
    clarity     = 0.35    # local contrast via unsharp on a wide radius


# ─────────────────────────────────────────────────────────────────────────────
#  MOTION  (reels / shorts)
# ─────────────────────────────────────────────────────────────────────────────

class Motion:
    fps         = 30
    # Durations in seconds
    text_in     = 0.62
    text_stagger= 0.075   # per line
    scene_cross = 0.40
    logo_in     = 0.90

    # ── reading, measured honestly ────────────────────────────────────────
    # 11 chars/sec was wishful. Kannada is an abugida: one akshara carries a
    # consonant, its vowel and often a conjunct, so a 70-character headline is
    # ~40 aksharas, and a viewer reading it for the FIRST time on a moving
    # video manages about 3-4 aksharas a second. That is ~7 characters/sec.
    # At the old number every scene ran roughly four times too fast to read.
    read_rate   = 7.0     # Kannada characters per second, first read, on video
    build_in    = 1.4     # stagger + rise before the last line is even up
    settle      = 0.8     # beat after reading, before the cut
    hold_min    = 5.0     # no scene is ever shorter than this
    hold_max    = 12.0

    # A reel line longer than this cannot be read comfortably in one scene.
    reel_line_budget = 46          # characters
    # Support text is only shown when the headline leaves genuine room.
    support_budget   = 62

    kb_zoom     = 0.11    # Ken Burns total scale travel
    kb_drift    = 0.035   # lateral drift as a fraction of frame width


class Ease:
    """t in [0,1] → eased t."""
    @staticmethod
    def linear(t): return t

    @staticmethod
    def out_expo(t): return 1.0 if t >= 1 else 1 - pow(2, -10 * t)

    @staticmethod
    def out_quint(t): return 1 - pow(1 - t, 5)

    @staticmethod
    def out_cubic(t): return 1 - pow(1 - t, 3)

    @staticmethod
    def in_out_cubic(t):
        return 4 * t ** 3 if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2

    @staticmethod
    def out_back(t, s=1.70158):
        return 1 + (s + 1) * pow(t - 1, 3) + s * pow(t - 1, 2)

    @staticmethod
    def in_out_sine(t):
        import math
        return -(math.cos(math.pi * t) - 1) / 2


def clamp01(t: float) -> float:
    return 0.0 if t < 0 else (1.0 if t > 1 else t)


def phase(t: float, start: float, dur: float, ease=Ease.out_quint) -> float:
    """Normalised, eased progress of a sub-animation inside a timeline."""
    if dur <= 0:
        return 1.0 if t >= start else 0.0
    return ease(clamp01((t - start) / dur))
