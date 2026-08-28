"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Content model & the genuineness contract
========================================================
Premium look is craft. Premium *trust* is structure — and structure is the part
a template can enforce. This module makes the honest thing the easy thing:

  * You cannot render a card without saying where the picture came from and
    whether it shows the actual scene. If it does not, the card prints
    "ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ" (representative image) and there is no flag to suppress it.
  * "ಬ್ರೇಕಿಂಗ್" is computed from the publish timestamp, never asserted. Once a
    story is older than BREAKING_WINDOW_H it stops wearing the red treatment,
    automatically.
  * "LIVE" requires an actual live stream URL.
  * A story that has not been confirmed says so, in Kannada, on the card.
  * At least one source must be named.

None of this makes the design worse. Real broadsheets carry all of it, and the
credit line at the foot of a photograph is part of why they look authoritative.
"""
from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
BREAKING_WINDOW_H = 12          # after this, a story is news, not breaking
FILE_PHOTO_LABEL_DAYS = 2       # older imagery must be labelled as archive

# How each image provenance is disclosed on the card.
IMAGE_NATURE = {
    'actual':         ('', ''),                                  # from the scene — no label needed
    'file':           ('ಸಂಗ್ರಹ ಚಿತ್ರ', 'FILE PHOTO'),
    'representative': ('ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ', 'REPRESENTATIVE IMAGE'),
    'handout':        ('ಹಂಚಿಕೆ ಚಿತ್ರ', 'HANDOUT'),
    'graphic':        ('ಗ್ರಾಫಿಕ್ಸ್', 'GRAPHIC'),
    'ai':             ('ಎಐ ರಚಿತ ಚಿತ್ರ', 'AI-GENERATED ILLUSTRATION'),
}

STATUS = {
    'confirmed':   ('ದೃಢಪಟ್ಟ ವರದಿ', 'CONFIRMED'),
    'developing':  ('ಬೆಳವಣಿಗೆಯಲ್ಲಿದೆ', 'DEVELOPING'),
    'unconfirmed': ('ಪರಿಶೀಲನೆಯಲ್ಲಿದೆ', 'UNVERIFIED — BEING CHECKED'),
    'official':    ('ಅಧಿಕೃತ ಪ್ರಕಟಣೆ', 'OFFICIAL RELEASE'),
}

KN_MONTHS = ['ಜನವರಿ', 'ಫೆಬ್ರವರಿ', 'ಮಾರ್ಚ್', 'ಏಪ್ರಿಲ್', 'ಮೇ', 'ಜೂನ್',
             'ಜುಲೈ', 'ಆಗಸ್ಟ್', 'ಸೆಪ್ಟೆಂಬರ್', 'ಅಕ್ಟೋಬರ್', 'ನವೆಂಬರ್', 'ಡಿಸೆಂಬರ್']
KN_DAYS = ['ಸೋಮವಾರ', 'ಮಂಗಳವಾರ', 'ಬುಧವಾರ', 'ಗುರುವಾರ', 'ಶುಕ್ರವಾರ', 'ಶನಿವಾರ', 'ಭಾನುವಾರ']


# ─────────────────────────────────────────────────────────────────────────────
#  CLOCK
#  Everything time-dependent goes through now(), never datetime.now() directly,
#  so a render can be made reproducible. Two things depend on the wall clock —
#  whether a story still counts as breaking, and the default publish time — and
#  both would otherwise make identical content produce different output on
#  different days, which defeats the point of a golden test.
# ─────────────────────────────────────────────────────────────────────────────

_FROZEN: datetime | None = None


def now() -> datetime:
    """Current time in IST, or the frozen instant if one is set.

    Set OORMANI_NOW to an ISO-8601 timestamp to freeze the clock for a whole
    process — that is how the reference renders stay reproducible.
    """
    if _FROZEN is not None:
        return _FROZEN
    env = os.environ.get('OORMANI_NOW')
    if env:
        return parse_dt(env)
    return datetime.now(IST)


def freeze(when: datetime | str | None) -> None:
    """Pin the clock process-wide. freeze(None) restores the real clock."""
    global _FROZEN
    _FROZEN = parse_dt(when) if isinstance(when, str) else when


@contextlib.contextmanager
def frozen(when: datetime | str):
    """with frozen('2026-08-25T09:40+05:30'): ..."""
    prev = _FROZEN
    freeze(when)
    try:
        yield
    finally:
        freeze(prev)


def parse_dt(v) -> datetime:
    """Accept an ISO-8601 string or a datetime; always return tz-aware IST."""
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=IST)
    d = datetime.fromisoformat(str(v).replace('Z', '+00:00'))
    return d if d.tzinfo else d.replace(tzinfo=IST)


CATEGORIES_KEYS: list[str] = []   # filled below from tokens, kept here so
# schema generation has one import to reach for.


# ─────────────────────────────────────────────────────────────────────────────
#  CRIMINAL REPORTING GUARDS
#
#  These are legal obligations in India, not stylistic preferences, so they are
#  enforced by the type system rather than written in a guide nobody rereads on
#  a deadline. All of them are general rules about how any crime story may be
#  written — none of them know anything about a particular story.
# ─────────────────────────────────────────────────────────────────────────────

# Verbs that assert a person DID the act. Publishing these about someone who has
# been arrested but not convicted is a defamation exposure under BNS §356, and
# once the matter is before a court, a contempt exposure.
GUILT_ASSERTING = [
    'ಕೊಂದ', 'ಕೊಲೆ ಮಾಡಿದ', 'ಹತ್ಯೆ ಮಾಡಿದ', 'ಕದ್ದ', 'ಕಳವು ಮಾಡಿದ',
    'ಮೋಸ ಮಾಡಿದ', 'ವಂಚಿಸಿದ', 'ಅತ್ಯಾಚಾರ ಮಾಡಿದ', 'ಹಲ್ಲೆ ಮಾಡಿದ',
    'ಸುಲಿಗೆ ಮಾಡಿದ', 'ದರೋಡೆ ಮಾಡಿದ', 'ಲಂಚ ಪಡೆದ', 'ಸುಟ್ಟ',
]

# Any one of these makes the sentence an allegation rather than a finding.
ALLEGATION_MARKERS = [
    'ಆರೋಪ', 'ಆರೋಪಿ', 'ಆರೋಪಿತ', 'ಶಂಕಿತ', 'ಎನ್ನಲಾಗಿದೆ', 'ಎಂದು ಆರೋಪಿಸಲಾಗಿದೆ',
    'ಪ್ರಕರಣ ದಾಖಲು', 'ದೂರು ದಾಖಲು', 'ತನಿಖೆ',
]

# Categories where a conviction has actually happened, so plain past tense is
# accurate and no allegation marker is needed.
CONVICTED_STATUSES = {'convicted'}


def asserts_guilt(text: str) -> list[str]:
    """Guilt-asserting verbs present in `text` with no allegation marker."""
    if any(m in text for m in ALLEGATION_MARKERS):
        return []
    return [v for v in GUILT_ASSERTING if v in text]


class ContentError(ValueError):
    """Raised when a card would misrepresent something. Not catchable by
    convenience — fix the story, not the exception."""


# What you are allowed to do with a picture. 'own' means the channel shot it.
LICENCES = {
    'own':          'ಸ್ವಂತ ಚಿತ್ರ',
    'licensed':     'ಪರವಾನಗಿ ಪಡೆದ ಚಿತ್ರ',
    'cc':           'ಕ್ರಿಯೇಟಿವ್ ಕಾಮನ್ಸ್',
    'public-domain': 'ಸಾರ್ವಜನಿಕ ವಲಯ',
    'handout':      'ಅಧಿಕೃತ ಹಂಚಿಕೆ',
    'fair-dealing': 'ನ್ಯಾಯಸಮ್ಮತ ಬಳಕೆ',
}


@dataclass
class Photo:
    path: str
    nature: str = 'representative'
    credit: str = ''                    # photographer / agency / "ವರದಿಗಾರರಿಂದ"
    licence: str = ''                   # one of LICENCES — REQUIRED
    source_url: str = ''                # where it came from, if not our own
    caption: str = ''                   # what the picture actually shows
    focal: tuple[float, float] = (0.5, 0.42)
    taken_at: datetime | None = None

    @classmethod
    def from_dict(cls, d: dict) -> 'Photo':
        d = dict(d)
        extra = set(d) - set(cls.__dataclass_fields__)
        if extra:
            raise ContentError(f'unknown photo field(s) {sorted(extra)}')
        if d.get('focal'):
            d['focal'] = tuple(d['focal'])
        if d.get('taken_at'):
            d['taken_at'] = parse_dt(d['taken_at'])
        return cls(**d)

    def validate(self):
        if self.nature not in IMAGE_NATURE:
            raise ContentError(f'unknown image nature {self.nature!r}; '
                               f'choose from {sorted(IMAGE_NATURE)}')
        if not self.credit:
            raise ContentError(
                f'{self.path}: every photograph needs a credit. Use the '
                'photographer, the agency, or "ಊರ್ಮನಿ ಸುದ್ದಿ ವರದಿಗಾರರಿಂದ".')
        if not self.licence:
            raise ContentError(
                f'{self.path}: every photograph needs a licence — one of '
                f'{sorted(LICENCES)}. Crediting a picture is not the same as '
                'having the right to publish it, and a credit that says the '
                'channel owns it when it does not is a false attribution on '
                'top of an infringement.')
        if self.licence not in LICENCES:
            raise ContentError(f'{self.path}: unknown licence {self.licence!r}; '
                               f'choose from {sorted(LICENCES)}')
        if self.licence != 'own' and not self.source_url:
            raise ContentError(
                f'{self.path}: licence is {self.licence!r}, so record where it '
                'came from in source_url. If the channel shot it, use '
                "licence='own'.")
        if self.nature == 'actual' and not self.caption:
            raise ContentError(
                f'{self.path}: a photo claiming to show the actual scene must '
                'carry a caption saying what it shows.')

    @property
    def label(self) -> str:
        return IMAGE_NATURE[self.nature][0]


@dataclass
class Story:
    headline: str
    category: str = 'explainer'
    deck: str = ''                       # standfirst, 1–2 lines
    points: list[str] = field(default_factory=list)
    photo: Photo | None = None
    location: str = ''
    dateline: str = ''                   # bureau, e.g. "ಬ್ರಹ್ಮಾವರ ವರದಿ"
    reporter: str = ''
    sources: list[str] = field(default_factory=list)
    status: str = 'developing'
    published_at: datetime = field(default_factory=now)
    live_url: str = ''
    takeaway: str = ''                   # advisory / what the reader should do
    numbers: list[tuple[str, str]] = field(default_factory=list)  # (value, label)
    quote: tuple[str, str] | None = None                          # (text, attribution)
    correction: str = ''                 # if this card corrects an earlier one
    reel_line: str = ''                  # short headline for video; see AI_BRIEF
    reel_support: str = ''               # supporting sentence for reel scene

    # ── criminal-reporting flags ──────────────────────────────────────────
    # Set these and the system refuses to render identifying detail. They are
    # deliberately blunt: the cost of a false positive is a vaguer card, the
    # cost of a false negative is an offence.
    involves_minor: bool = False         # JJ Act 2015 §74
    sexual_offence: bool = False         # POCSO §23 / BNS §72
    convicted: bool = False              # a court has actually convicted

    # Renderer hints, not content. Set by from_dict(); see docs/AI_BRIEF.md.
    _template: str | None = field(default=None, repr=False, compare=False)
    _hook: str = field(default='', repr=False, compare=False)

    # ── validation ────────────────────────────────────────────────────────
    def validate(self) -> 'Story':
        if not self.headline.strip():
            raise ContentError('headline is required')
        if self.status not in STATUS:
            raise ContentError(f'unknown status {self.status!r}')
        if not self.sources:
            raise ContentError(
                'name at least one source. If it is your own reporting, say so: '
                'sources=["ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ"].')
        if self.photo:
            self.photo.validate()
            if (self.photo.nature == 'actual' and self.photo.taken_at
                    and self.published_at - self.photo.taken_at
                    > timedelta(days=FILE_PHOTO_LABEL_DAYS)):
                raise ContentError(
                    'photo is older than the file-photo window but is marked '
                    "'actual'; change nature to 'file'.")
        if self.live_url and not self.live_url.startswith('http'):
            raise ContentError('live_url must be a real stream URL, or empty')
        # The criminal-reporting guards run BEFORE the breaking demotion below.
        # Demotion is a presentation decision — it drops the red treatment on a
        # story that has aged out of the window. It must never relax a legal
        # guard: a card asserting guilt is a defamation exposure whether it is
        # two hours old or two days old, and checking after the demotion meant
        # the same copy passed simply because the render happened the next day.
        self._check_criminal_reporting()
        if self.category == 'breaking' and not self.is_breaking:
            # Not an error — just quietly demote, and say so.
            self.category = 'explainer'
        return self

    # ── the criminal-reporting contract ───────────────────────────────────
    @property
    def _all_copy(self) -> str:
        return ' '.join(filter(None, [self.headline, self.deck, self.takeaway,
                                      self.reel_line, *self.points]))

    def _check_criminal_reporting(self):
        """Legal obligations, enforced by the type system.

        These are general rules about how ANY crime story may be written. None
        of them knows anything about a particular story, and none can be
        switched off — a guideline that can be waived on a deadline is a
        guideline that gets waived on a deadline.
        """
        copy = self._all_copy

        # 1 · Guilt may not be asserted before conviction. BNS §356 (defamation)
        #     and contempt once the matter is sub judice.
        if self.category in ('crime', 'breaking') and not self.convicted:
            # Checked field by field, not over the concatenated copy. An
            # allegation marker buried in the third bullet does not make a
            # headline safe: the headline is what travels — a thumbnail, a
            # WhatsApp forward, a screenshot — and it travels ALONE, without the
            # bullet that qualified it. The same is true of reel_line, which is
            # the only text on its scene. Checking the joined string let
            # "ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ ಬಂಧನ" through because the deck happened to
            # say ಆರೋಪಿ, which is precisely the exposure this guard exists for.
            for where, text in (('headline', self.headline),
                                ('reel_line', self.reel_line)):
                hits = asserts_guilt(text)
                if hits:
                    raise ContentError(
                        f'the {where} states guilt as fact ({", ".join(hits)}) '
                        'about someone who has not been convicted. It is read on '
                        'its own — in a thumbnail, a forward, a search result — '
                        'so a qualifier elsewhere in the story does not reach it. '
                        f'Rewrite the {where} itself as an allegation: ಆರೋಪ / '
                        'ಆರೋಪಿ / ಶಂಕಿತ, or ಪ್ರಕರಣ ದಾಖಲು. Set convicted=True only '
                        'if a court has actually convicted.')
            hits = asserts_guilt(copy)
            if hits:
                raise ContentError(
                    f'this crime story states guilt as fact ({", ".join(hits)}) '
                    'about someone who has not been convicted. Rewrite it as an '
                    'allegation — add ಆರೋಪ / ಆರೋಪಿ / ಶಂಕಿತ, or say ಪ್ರಕರಣ ದಾಖಲು — '
                    'or set convicted=True if a court has actually convicted.')

        # 2 · A child in conflict with law, or a child victim, may not be
        #     identified. JJ Act 2015 §74.
        if self.involves_minor:
            if self.photo and self.photo.nature == 'actual':
                raise ContentError(
                    'involves_minor is set, so an actual photograph of the scene '
                    "may identify the child. Use nature='representative', a "
                    'graphic, or no picture.')
            named = [p for p in self.points if _looks_like_name(p)]
            if named or _looks_like_name(self.headline) or _looks_like_name(self.deck):
                raise ContentError(
                    'involves_minor is set: remove names and ages. JJ Act 2015 '
                    '§74 makes identifying a child in conflict with law, or a '
                    'child victim, an offence.')

        # 3 · Victims of sexual offences may not be identified.
        #     POCSO 2012 §23, BNS §72.
        if self.sexual_offence:
            if self.photo and self.photo.nature in ('actual', 'handout'):
                raise ContentError(
                    'sexual_offence is set: a photograph of the actual scene or '
                    'a handout may identify the victim. Use a representative '
                    'image or a graphic.')
            if self.location and _is_granular_place(self.location):
                raise ContentError(
                    f'sexual_offence is set but location is {self.location!r}, '
                    'which is granular enough to identify the victim. Use the '
                    'district or taluk only.')
            if _looks_like_name(copy):
                raise ContentError(
                    'sexual_offence is set: remove names and ages from the copy.')
        return self

    # ── derived, never asserted ───────────────────────────────────────────
    @property
    def is_breaking(self) -> bool:
        age = now() - self.published_at
        return age <= timedelta(hours=BREAKING_WINDOW_H) and age.total_seconds() >= -60

    @property
    def is_live(self) -> bool:
        return bool(self.live_url)

    @property
    def status_kn(self) -> str:
        return STATUS[self.status][0]

    @property
    def date_kn(self) -> str:
        d = self.published_at
        return f'{d.day} {KN_MONTHS[d.month - 1]} {d.year}'

    @property
    def time_kn(self) -> str:
        d = self.published_at
        h24 = d.hour
        ampm = 'ಬೆಳಿಗ್ಗೆ' if 4 <= h24 < 12 else ('ಮಧ್ಯಾಹ್ನ' if 12 <= h24 < 16
                                                 else ('ಸಂಜೆ' if 16 <= h24 < 20 else 'ರಾತ್ರಿ'))
        h = h24 % 12 or 12
        return f'{ampm} {h}:{d.minute:02d}'

    @property
    def day_kn(self) -> str:
        return KN_DAYS[self.published_at.weekday()]

    @property
    def source_line(self) -> str:
        return 'ಮೂಲ: ' + ' • '.join(self.sources)

    @property
    def credit_line(self) -> str:
        """The disclosure strip that sits under every photograph."""
        if not self.photo:
            return ''
        bits: list[str] = []
        for b in (self.photo.label, self.photo.caption):
            b = (b or '').strip()
            # A caption that only restates the nature label is noise.
            if b and b not in bits:
                bits.append(b)
        if self.photo.credit:
            # 'ಕೃಪೆ:' (courtesy), not 'ಚಿತ್ರ:' (image) — every nature label
            # above already ends in ಚಿತ್ರ, so a second 'ಚಿತ್ರ:' here read as
            # ...ಚಿತ್ರ • ಚಿತ್ರ: ..., the same word twice back to back.
            # ಕೃಪೆ is also the standard Kannada press credit line.
            bits.append(f'ಕೃಪೆ: {self.photo.credit}')
        return '  •  '.join(bits)


    # ── JSON in / JSON out ────────────────────────────────────────────────
    @classmethod
    def from_dict(cls, d: dict) -> 'Story':
        """Build a Story from plain JSON. This is the door any other tool
        comes through, so it is forgiving about shape and strict about truth:
        unknown keys are rejected loudly rather than silently ignored, because
        a typo'd `source` that leaves `sources` empty would otherwise render a
        card with no attribution."""
        d = dict(d)
        known = {f for f in cls.__dataclass_fields__}
        extra = set(d) - known - {'photo', 'template', 'hook'}
        if extra:
            raise ContentError(
                f'unknown field(s) {sorted(extra)}. Valid fields: '
                f'{sorted(known)}. Did you mean one of those?')
        tpl = d.pop('template', None)
        hook = d.pop('hook', '')
        if d.get('photo'):
            d['photo'] = Photo.from_dict(d['photo'])
        if 'published_at' in d and d['published_at'] is not None:
            d['published_at'] = parse_dt(d['published_at'])
        if d.get('quote') is not None:
            q = d['quote']
            if len(q) != 2:
                raise ContentError('quote must be [text, attribution]')
            d['quote'] = (q[0], q[1])
        if d.get('numbers'):
            d['numbers'] = [tuple(n) for n in d['numbers']]
        obj = cls(**d)
        # Carried alongside rather than inside the dataclass: they are
        # instructions to the renderer, not facts about the story.
        obj._template = tpl
        obj._hook = hook
        return obj

    def to_dict(self) -> dict:
        d = {k: v for k, v in asdict(self).items() if not k.startswith('_')}
        if self._template:
            d['template'] = self._template
        if self._hook:
            d['hook'] = self._hook
        d['published_at'] = self.published_at.isoformat()
        if self.photo and self.photo.taken_at:
            d['photo']['taken_at'] = self.photo.taken_at.isoformat()
        return d


def _looks_like_name(text: str) -> bool:
    """A crude check for a person named with an age — the commonest way a
    report identifies someone. Deliberately over-eager: on a story flagged as
    involving a minor, a false positive costs a rewrite and a false negative
    costs an offence."""
    import re
    return bool(re.search(r'\(\s*\d{1,2}\s*\)', text))


# Words that mark a place small enough to identify an individual within it.
_GRANULAR = ['ನಗರ', 'ಗ್ರಾಮ', 'ಬಡಾವಣೆ', 'ಕಾಲೋನಿ', 'ರಸ್ತೆ', 'ಶಾಲೆ', 'ಕಾಲೇಜು']


def _is_granular_place(place: str) -> bool:
    return any(w in place for w in _GRANULAR)


@dataclass
class Edition:
    """A day's bulletin — drives the carousel, the reel and the broadsheet from
    one object, so the three never drift out of sync."""
    stories: list[Story]
    date: datetime = field(default_factory=now)
    edition_no: int = 1
    strapline: str = ''      # falls back to tokens.Brand.bulletin

    def validate(self) -> 'Edition':
        for s in self.stories:
            s.validate()
        return self

    @property
    def date_kn(self) -> str:
        d = self.date
        return f'{d.day} {KN_MONTHS[d.month - 1]} {d.year}'

    def __post_init__(self):
        if not self.strapline:
            from .tokens import Brand
            self.strapline = Brand.bulletin

    @classmethod
    def from_dict(cls, d: dict) -> 'Edition':
        d = dict(d)
        extra = set(d) - set(cls.__dataclass_fields__)
        if extra:
            raise ContentError(
                f'unknown edition field(s) {sorted(extra)}. Valid: '
                f'{sorted(cls.__dataclass_fields__)}')
        d['stories'] = [Story.from_dict(s) for s in d.get('stories', [])]
        if not d['stories']:
            raise ContentError('an edition needs at least one story')
        if 'date' in d and d['date'] is not None:
            d['date'] = parse_dt(d['date'])
        return cls(**d)

    @classmethod
    def load(cls, path: str) -> 'Edition':
        """Read an edition from a JSON file and validate it."""
        import json
        with open(path, encoding='utf-8') as f:
            return cls.from_dict(json.load(f)).validate()

    def to_dict(self) -> dict:
        return {'date': self.date.isoformat(), 'edition_no': self.edition_no,
                'strapline': self.strapline,
                'stories': [s.to_dict() for s in self.stories]}


from .tokens import CATEGORIES as _CATS  # noqa: E402
CATEGORIES_KEYS[:] = sorted(_CATS)
