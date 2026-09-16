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

# The shape of an edition file. Bumped when a field is added or its meaning
# changes, so an edition written last year can be read — or refused — knowingly
# rather than crashing on a key nobody remembers adding. Editions written
# before this existed have no key and are read as version 1.
#   1  pre-lock
#   2  source_urls required on sourced stories (D55)
#   3  verified_by / verified_at (D59)
SCHEMA_VERSION = 3

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
#
# The list is a FLOOR, not a proof. Kannada builds the same assertion several
# ways — the bare past (ಕೊಂದ), the participle (ಕೊಂದು), the perfective
# (ಕೊಂದಿದ್ದಾನೆ), the verbal noun (ಕೊಲೆಗೈದ) — and an earlier version carried only
# the first of each, which is why tests/legal_corpus.json now measures what
# gets through instead of assuming nothing does. See D61.
GUILT_ASSERTING = [
    # killing
    'ಕೊಂದ', 'ಕೊಂದು', 'ಕೊಂದಿದ್ದಾನೆ', 'ಕೊಂದಿದ್ದಾಳೆ', 'ಕೊಂದಿದ್ದಾರೆ',
    'ಕೊಲೆ ಮಾಡಿದ', 'ಕೊಲೆಗೈದ', 'ಹತ್ಯೆ ಮಾಡಿದ', 'ಹತ್ಯೆಗೈದ',
    # theft
    'ಕದ್ದ', 'ಕದ್ದಿದ್ದಾನೆ', 'ಕದ್ದಿದ್ದಾರೆ', 'ಕಳವು ಮಾಡಿದ', 'ಕಳ್ಳತನ ಮಾಡಿದ',
    # cheating / fraud
    'ಮೋಸ ಮಾಡಿದ', 'ವಂಚಿಸಿದ', 'ವಂಚನೆ ಮಾಡಿದ', 'ವಂಚಿಸಿದ್ದಾನೆ',
    # sexual offences
    'ಅತ್ಯಾಚಾರ ಮಾಡಿದ', 'ಅತ್ಯಾಚಾರಗೈದ', 'ಲೈಂಗಿಕ ದೌರ್ಜನ್ಯ ಎಸಗಿದ',
    # assault / violence
    'ಹಲ್ಲೆ ಮಾಡಿದ', 'ಹಲ್ಲೆಗೈದ', 'ಥಳಿಸಿದ', 'ಇರಿದ', 'ಚುಚ್ಚಿ ಕೊಂದ',
    # robbery / extortion
    'ಸುಲಿಗೆ ಮಾಡಿದ', 'ದರೋಡೆ ಮಾಡಿದ', 'ಸುಲಿಗೆಗೈದ',
    # bribery / corruption
    'ಲಂಚ ಪಡೆದ', 'ಲಂಚ ಸ್ವೀಕರಿಸಿದ', 'ಹಣ ದೋಚಿದ', 'ದುರುಪಯೋಗ ಮಾಡಿದ',
    # arson / destruction
    'ಸುಟ್ಟ', 'ಬೆಂಕಿ ಹಚ್ಚಿದ', 'ನಾಶ ಮಾಡಿದ',
    # abduction / trafficking
    'ಅಪಹರಿಸಿದ', 'ಅಪಹರಣ ಮಾಡಿದ', 'ಸಾಗಾಟ ಮಾಡಿದ',
    # the flat noun-phrase forms that read as findings
    'ಅಪರಾಧಿ', 'ದೋಷಿ',
]

# Any one of these makes the sentence an allegation rather than a finding.
ALLEGATION_MARKERS = [
    'ಆರೋಪ', 'ಆರೋಪಿ', 'ಆರೋಪಿತ', 'ಶಂಕಿತ', 'ಶಂಕೆ', 'ಎನ್ನಲಾಗಿದೆ',
    'ಎಂದು ಆರೋಪಿಸಲಾಗಿದೆ', 'ಎಂದು ಹೇಳಲಾಗಿದೆ',
    'ಪ್ರಕರಣ ದಾಖಲು', 'ಪ್ರಕರಣ ದಾಖಲಾಗಿದೆ', 'ದೂರು ದಾಖಲು', 'ದೂರು ದಾಖಲಾಗಿದೆ',
    'ತನಿಖೆ', 'ವಿಚಾರಣೆ',
]

# Categories where a conviction has actually happened, so plain past tense is
# accurate and no allegation marker is needed.
CONVICTED_STATUSES = {'convicted'}


def asserts_guilt(text: str) -> list[str]:
    """Guilt-asserting verbs present in `text` with no allegation marker.

    A marker anywhere in the SAME field clears that field. This is deliberate:
    the field is the unit that travels alone (D29), so "ಕೊಲೆ ಆರೋಪಿ ಬಂಧನ" is
    safe while "ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ" with ಆರೋಪಿ only in the deck is not.
    """
    if any(m in text for m in ALLEGATION_MARKERS):
        return []
    return [v for v in GUILT_ASSERTING if v in text]


class ContentError(ValueError):
    """Raised when a card would misrepresent something. Not catchable by
    convenience — fix the story, not the exception."""


# Own reporting is the only source that does not need a URL. Everything else
# must point at a page, a notice, or a document the editor can reopen.
OWN_REPORTING = 'ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ'


def is_own_reporting(sources: list[str]) -> bool:
    return any(OWN_REPORTING in (s or '') for s in sources)


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
        # Generated pictures, including reused stock, must wear the AI stamp.
        # Labelling them ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ while the credit whispers "AI ಚಿತ್ರ"
        # is concealment under the IT Rules synthetic-content rules. D57.
        credit_l = (self.credit or '').upper()
        generated = (
            'ಎಐ' in (self.credit or '')
            or 'AI ಚಿತ್ರ' in (self.credit or '')
            or 'AI ' in credit_l
            or credit_l.startswith('AI')
        )
        if generated and self.nature not in ('ai', 'graphic'):
            raise ContentError(
                f'{self.path}: this credit names an AI image but nature is '
                f'{self.nature!r}. Generated pictures, including stock, must '
                "use nature='ai' so the frame says ಎಐ ರಚಿತ ಚಿತ್ರ.")

    @property
    def label(self) -> str:
        return IMAGE_NATURE[self.nature][0]

    @property
    def disclosure(self) -> str:
        """The line that must appear on any card showing THIS photograph.

        Per-photo, not per-story. A reel's fact cards and its end card show
        gallery images and the hero respectively, and until this existed only
        the lead card disclosed anything — so an AI-generated picture could be
        on screen for twenty seconds with nothing saying so. Under the IT
        Rules 2021 amendments on synthetically generated information, the
        label has to travel with the image, not with the story.
        """
        bits: list[str] = []
        for b in (self.label, self.caption):
            b = (b or '').strip()
            # A caption that only restates the nature label is noise.
            if b and b not in bits:
                bits.append(b)
        if self.credit:
            # 'ಕೃಪೆ:' (courtesy), not 'ಚಿತ್ರ:' (image) — every nature label
            # already ends in ಚಿತ್ರ, so a second 'ಚಿತ್ರ:' here read as
            # ...ಚಿತ್ರ • ಚಿತ್ರ: ..., the same word twice back to back.
            # ಕೃಪೆ is also the standard Kannada press credit line.
            bits.append(f'ಕೃಪೆ: {self.credit}')
        return '  •  '.join(bits)

    @property
    def is_synthetic(self) -> bool:
        """True when this image was generated rather than photographed."""
        return self.nature in ('ai', 'graphic')


@dataclass
class Story:
    headline: str
    category: str = 'explainer'
    deck: str = ''                       # standfirst, 1–2 lines
    points: list[str] = field(default_factory=list)
    photo: Photo | None = None
    gallery: list[Photo] = field(default_factory=list)  # additional photos for dynamic multi-scene video
    location: str = ''
    dateline: str = ''                   # bureau, e.g. "ಬ್ರಹ್ಮಾವರ ವರದಿ"
    reporter: str = ''
    sources: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    # Who opened the source and confirmed the facts, and when. Not a rendering
    # input — it never appears on a card — but the Chief Editor gate refuses to
    # write APPROVAL.md without it, which is the second half of D55: no source,
    # no claim; no human verification, no publication. See D59.
    verified_by: str = ''
    verified_at: datetime | None = None
    status: str = 'developing'
    published_at: datetime = field(default_factory=now)
    live_url: str = ''
    takeaway: str = ''                   # advisory / what the reader should do
    numbers: list[tuple[str, str]] = field(default_factory=list)  # (value, label)
    quote: tuple[str, str] | None = None                          # (text, attribution)
    correction: str = ''                 # if this card corrects an earlier one
    # The edition date this story continues, e.g. "2026-09-14". A road that was
    # closed and has reopened is a second story, and saying so is worth more
    # than either half alone: it tells a reader this channel followed up, which
    # is the difference between a feed and a paper.
    #
    # It is NOT a licence to split one small story across three days. The rule
    # is new information or nothing — `follows_up` with no new fact is padding,
    # and padding is what teaches an audience to stop reading. See D72.
    follows_up: str = ''
    reel_line: str = ''                  # short headline for video; see AI_BRIEF
    reel_support: str = ''               # supporting sentence for reel scene
    # Short on-screen forms of `points`, for the reel's fact cards. Same idea
    # as reel_line: a print fact is written to be read at leisure, and a
    # narrated reel card is glanced at while a voice is already delivering the
    # same fact faster than anyone can read it. Index-matched to `points`;
    # a blank or missing entry falls back to the full point. See D51.
    reel_points: list[str] = field(default_factory=list)
    is_reel: bool = True                 # whether to produce an individual reel (10/10 editorial score)
    narration_script: str = ''           # broadcast-grade spoken news anchor script

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
        from .tokens import CATEGORIES as _CATS
        if self.category not in _CATS:
            raise ContentError(
                f'unknown category {self.category!r}; choose from {sorted(_CATS)}. '
                'Unknown names used to fall back silently to explainer styling.')
        if not self.sources:
            raise ContentError(
                'name at least one source. If it is your own reporting, say so: '
                f'sources=["{OWN_REPORTING}"].')
        if not is_own_reporting(self.sources):
            urls = [u for u in self.source_urls if (u or '').strip()]
            if not urls:
                raise ContentError(
                    'every sourced story needs at least one source_url the editor '
                    f'can reopen, or mark it as own reporting: sources=["{OWN_REPORTING}"]. '
                    'A named source without a URL is how invented detail gets a dateline.')
            for u in urls:
                if not u.startswith('http'):
                    raise ContentError(
                        f'source_url {u!r} must be a real http(s) URL')
        if self.category == 'obituary' and len(self.sources) < 2 and not is_own_reporting(self.sources):
            raise ContentError(
                'an obituary needs two independent sources, or own reporting. '
                'False death reports are a recurring local-media failure.')
        if self.photo:
            self.photo.validate()
            if (self.photo.nature == 'actual' and self.photo.taken_at
                    and self.published_at - self.photo.taken_at
                    > timedelta(days=FILE_PHOTO_LABEL_DAYS)):
                raise ContentError(
                    'photo is older than the file-photo window but is marked '
                    "'actual'; change nature to 'file'.")
        for p in self.gallery:
            p.validate()
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
        """The disclosure strip for the HERO photograph.

        Delegates to Photo.disclosure so a gallery frame shown on a fact card
        and the hero shown on the lead card are labelled by the same code.
        """
        return self.photo.disclosure if self.photo else ''

    @property
    def has_synthetic_imagery(self) -> bool:
        """True if ANY image this story can put on screen was generated."""
        return any(p.is_synthetic for p in self.all_photos)

    @property
    def all_photos(self) -> list['Photo']:
        """Every photograph this story can put on screen, hero first."""
        return ([self.photo] if self.photo else []) + list(self.gallery)


    # ── JSON in / JSON out ────────────────────────────────────────────────
    @classmethod
    def from_dict(cls, d: dict) -> 'Story':
        """Build a Story from plain JSON. This is the door any other tool
        comes through, so it is forgiving about shape and strict about truth:
        unknown keys are rejected loudly rather than silently ignored, because
        a typo'd `source` that leaves `sources` empty would otherwise render a
        card with no attribution."""
        d = dict(d)
        if 'reel' in d and 'is_reel' not in d:
            d['is_reel'] = d.pop('reel')
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
        if d.get('gallery'):
            d['gallery'] = [Photo.from_dict(p) for p in d['gallery']]
        if 'published_at' in d and d['published_at'] is not None:
            d['published_at'] = parse_dt(d['published_at'])
        if d.get('verified_at'):
            d['verified_at'] = parse_dt(d['verified_at'])
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
        d['verified_at'] = (self.verified_at.isoformat()
                            if self.verified_at else None)
        if self.photo and self.photo.taken_at:
            d['photo']['taken_at'] = self.photo.taken_at.isoformat()
        return d

    # ── the verification record ───────────────────────────────────────────
    @property
    def is_verified(self) -> bool:
        """True when a named person says they opened the sources and checked.

        Deliberately not inferred from `status`: 'confirmed' is what the CARD
        says about the news, and a model can write that. This is what a person
        says about their own work, and only a person can fill it in.
        """
        return bool((self.verified_by or '').strip())

    @property
    def verification_line(self) -> str:
        if not self.is_verified:
            return ''
        who = self.verified_by.strip()
        when = f' · {self.verified_at:%Y-%m-%d %H:%M}' if self.verified_at else ''
        return f'{who}{when}'


import re as _re

# The shapes a report uses to pin an age to a person. Any of them, next to a
# name, identifies someone. All three shipped in real coastal copy:
#   "ರಮೇಶ್ (15)"        the bracketed age
#   "15 ವರ್ಷದ ಬಾಲಕ"     the attributive age
#   "೧೫ ವರ್ಷದ"          the same in Kannada numerals
_AGE_SHAPES = [
    _re.compile(r'\(\s*[\d೦-೯]{1,2}\s*\)'),
    _re.compile(r'[\d೦-೯]{1,2}\s*ವರ್ಷ'),
    _re.compile(r'[\d೦-೯]{1,2}\s*ರ\s*ಬಾಲ'),
]


def _looks_like_name(text: str) -> bool:
    """A crude check for a person named with an age — the commonest way a
    report identifies someone. Deliberately over-eager: on a story flagged as
    involving a minor, a false positive costs a rewrite and a false negative
    costs an offence."""
    return any(p.search(text) for p in _AGE_SHAPES)


# Words that mark a place small enough to identify an individual within it.
# Coastal Karnataka adds forms a generic Indian list misses — ಪೇಟೆ for a market
# town, ಮಠ / ದೇವಸ್ಥಾನ for a temple neighbourhood, ಕ್ರಾಸ್ for a junction that
# everybody local can point at.
_GRANULAR = [
    'ನಗರ', 'ಗ್ರಾಮ', 'ಬಡಾವಣೆ', 'ಕಾಲೋನಿ', 'ರಸ್ತೆ', 'ಶಾಲೆ', 'ಕಾಲೇಜು',
    'ಪೇಟೆ', 'ಕ್ರಾಸ್', 'ಜಂಕ್ಷನ್', 'ವಾರ್ಡ್', 'ಬೀದಿ', 'ಓಣಿ', 'ಮನೆ',
    'ದೇವಸ್ಥಾನ', 'ಮಠ', 'ಚರ್ಚ್', 'ಮಸೀದಿ', 'ಹಾಸ್ಟೆಲ್', 'ಆಶ್ರಮ',
    'ಅಂಗನವಾಡಿ', 'ಪಂಚಾಯಿತಿ',
]


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
    schema_version: int = SCHEMA_VERSION

    def validate(self) -> 'Edition':
        if self.schema_version > SCHEMA_VERSION:
            raise ContentError(
                f'this edition declares schema_version {self.schema_version}, '
                f'but this checkout understands {SCHEMA_VERSION}. Update the '
                'code rather than editing the number down.')
        for s in self.stories:
            s.validate()
        return self

    @property
    def unverified(self) -> list[Story]:
        """Stories no named person has confirmed. D59."""
        return [s for s in self.stories if not s.is_verified]

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
        return {'schema_version': self.schema_version,
                'date': self.date.isoformat(), 'edition_no': self.edition_no,
                'strapline': self.strapline,
                'stories': [s.to_dict() for s in self.stories]}


from .tokens import CATEGORIES as _CATS  # noqa: E402
CATEGORIES_KEYS[:] = sorted(_CATS)
