"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Post copy
=========================
Renders the words that go around the artwork: the Instagram caption, the
hashtag set, the YouTube title and description, alt text, a WhatsApp forward
and an X post.

Why this exists: the design system produced finished artwork and nothing you
could actually post with it, so every card still needed a human to write copy
before it could go out. On both platforms the copy is most of what drives
discovery — Instagram has indexed caption text for keyword search since 2024,
and YouTube ranks largely on title and description.

Everything here is derived from `Story` / `Edition` fields. Nothing knows about
any particular day's news, and nothing is templated to a specific story.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

from .content import Story, Edition, IMAGE_NATURE, STATUS
from .tokens import Brand, CATEGORIES, category

# Instagram shows roughly this much before the "… more" fold. The first line has
# to earn the tap on its own.
FOLD = 125
IG_CAPTION_MAX = 2200
IG_HASHTAG_MAX = 30           # platform hard limit
X_MAX = 280
YT_TITLE_MAX = 100            # hard limit; ~60 is what actually displays
YT_DESC_MAX = 5000

# Structural markers. Deliberately few — a caption peppered with emoji reads as
# a personal account, not a newsroom.
M_PLACE, M_TIME, M_SOURCE, M_NOTE = '📍', '🕐', '📌', '⚠️'


# ─────────────────────────────────────────────────────────────────────────────
#  HASHTAGS
# ─────────────────────────────────────────────────────────────────────────────

# Per-category tags. Extend this rather than writing tags into a story.
CATEGORY_TAGS = {
    'breaking':  ['BreakingNews', 'ಬ್ರೇಕಿಂಗ್‌ನ್ಯೂಸ್'],
    'crime':     ['CrimeNews', 'ಅಪರಾಧಸುದ್ದಿ'],
    'weather':   ['WeatherAlert', 'ಹವಾಮಾನ', 'KarnatakaRains'],
    'civic':     ['CivicNews', 'ಆಡಳಿತ'],
    'health':    ['HealthNews', 'ಆರೋಗ್ಯ'],
    'education': ['EducationNews', 'ಶಿಕ್ಷಣ'],
    'culture':   ['Culture', 'ಸಂಸ್ಕೃತಿ'],
    'sport':     ['Sports', 'ಕ್ರೀಡೆ'],
    'farm':      ['Agriculture', 'ಕೃಷಿ'],
    'obituary':  ['Obituary', 'ನಿಧನ'],
    'explainer': ['Explainer', 'ವಿಶ್ಲೇಷಣೆ'],
}

# Always-on brand and region tags.
CORE_TAGS = ['OormaniSuddi', 'ಕರಾವಳಿ', 'CoastalKarnataka', 'KannadaNews',
             'ಕನ್ನಡಸುದ್ದಿ', 'Karnataka']

# Latin equivalents for places we cover, so a Kannada location also produces a
# searchable English tag. Add to it as coverage grows; unknown places simply
# fall back to the Kannada tag alone.
PLACE_TAGS = {
    'ಉಡುಪಿ': 'Udupi', 'ಕುಂದಾಪುರ': 'Kundapura', 'ಬೈಂದೂರು': 'Byndoor',
    'ಒತ್ತಿನೆನೆ': 'Ottinene', 'ಬ್ರಹ್ಮಾವರ': 'Brahmavara', 'ಕಾರ್ಕಳ': 'Karkala', 'ಮಣಿಪಾಲ': 'Manipal',
    'ಮಲ್ಪೆ': 'Malpe', 'ಕಾಪು': 'Kaup', 'ಹೆಬ್ರಿ': 'Hebri',
    'ಮಂಗಳೂರು': 'Mangaluru', 'ದಕ್ಷಿಣ ಕನ್ನಡ': 'DakshinaKannada',
    'ಉತ್ತರ ಕನ್ನಡ': 'UttaraKannada', 'ಶಿರಸಿ': 'Sirsi', 'ಭಟ್ಕಳ': 'Bhatkal',
    'ಕುಮಟಾ': 'Kumta', 'ಹೊನ್ನಾವರ': 'Honnavar', 'ಬೆಂಗಳೂರು': 'Bengaluru',
}


def _leads_with_place(line: str, place: str) -> bool:
    """True when `line` already opens with the place name, in any of the forms a
    Kannada headline uses it: bare, with a colon, or as part of a compound."""
    if not place:
        return False
    head = line.strip()[:len(place) + 2].strip()
    return head.startswith(place.strip())


def _tagify(s: str) -> str:
    """A single token safe to use after a #."""
    s = re.sub(r'[^\wಀ-೿]+', '', s.strip())
    return s


def hashtags(story: Story, limit: int = 12) -> list[str]:
    """Category + place + core, de-duplicated and capped.

    Ordered by specificity: the tags most likely to reach the right people come
    first, because that is the order a reader skims and the order that survives
    if you trim the list.
    """
    out: list[str] = []

    def add(tag: str):
        t = _tagify(tag)
        if t and t.lower() not in {x.lower() for x in out}:
            out.append(t)

    for part in re.split(r'[\/|,·•]| - ', story.location or ''):
        part = part.strip()
        if not part:
            continue
        add(part)
        if part in PLACE_TAGS:
            add(PLACE_TAGS[part])

    for t in CATEGORY_TAGS.get(story.category, []):
        add(t)
    for t in CORE_TAGS:
        add(t)
    return out[:min(limit, IG_HASHTAG_MAX)]


# ─────────────────────────────────────────────────────────────────────────────
#  PIECES
# ─────────────────────────────────────────────────────────────────────────────

def hook(story: Story) -> str:
    """The first line — everything Instagram shows before the fold."""
    line = (story.reel_line or story.headline).strip()
    if len(line) <= FOLD:
        return line
    cut = line[:FOLD]
    for sep in ('. ', '? ', '! ', ': ', ' — ', ' '):
        if sep in cut:
            return cut.rsplit(sep, 1)[0].rstrip(' :—-') + '…'
    return cut.rstrip() + '…'


def dateline(story: Story) -> str:
    bits = []
    if story.location:
        bits.append(f'{M_PLACE} {story.location}')
    bits.append(f'{M_TIME} {story.date_kn} · {story.time_kn}')
    return '  '.join(bits)


def source_line(story: Story) -> str:
    return f'{M_SOURCE} ಮೂಲ: ' + ' · '.join(story.sources)


def status_line(story: Story) -> str:
    kn, en = STATUS[story.status]
    return f'ಸ್ಥಿತಿ: {kn}'


def photo_note(story: Story) -> str:
    """The image disclosure, in words, for the caption."""
    if not story.photo:
        return 'ಕೃಪೆ: ಗ್ರಾಫಿಕ್ಸ್ — ' + Brand.name
    kn = IMAGE_NATURE[story.photo.nature][0]
    # 'ಕೃಪೆ:' (courtesy), matching content.py::credit_line — every nature
    # label already ends in ಚಿತ್ರ, so 'ಚಿತ್ರ: <credit>' repeated the word.
    bits = [b for b in (kn, f'ಕೃಪೆ: {story.photo.credit}') if b]
    return ' · '.join(bits)


def alt_text(story: Story) -> str:
    """Alt text for the rendered card.

    Describes the CARD, not just the photograph, because that is what a screen
    reader user is being shown. Free to produce and it also helps Instagram
    understand the image.
    """
    cat = category(story.category)
    parts = [f'{Brand.name} — {cat["kn"]} ಸುದ್ದಿ ಕಾರ್ಡ್.']
    parts.append(story.headline.rstrip('.') + '.')
    if story.photo and story.photo.caption:
        parts.append(f'ಚಿತ್ರದಲ್ಲಿ: {story.photo.caption.rstrip(".")}.')
    elif story.photo:
        parts.append(f'{IMAGE_NATURE[story.photo.nature][0]}.')
    else:
        parts.append('ಚಿತ್ರವಿಲ್ಲ; ಬ್ರಾಂಡ್ ಗ್ರಾಫಿಕ್ಸ್ ಫಲಕ.')
    return ' '.join(parts)


# ─────────────────────────────────────────────────────────────────────────────
#  ASSEMBLED COPY
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PostCopy:
    hook: str
    instagram: str
    hashtags: list[str]
    alt_text: str
    whatsapp: str
    x_post: str
    youtube_title: str = ''
    youtube_description: str = ''
    youtube_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _join(blocks: list[str]) -> str:
    return '\n\n'.join(b.strip() for b in blocks if b and b.strip())


def instagram_caption(story: Story, tags: list[str] | None = None) -> str:
    tags = tags if tags is not None else hashtags(story)
    blocks = [hook(story)]

    if story.deck and story.deck.strip() not in blocks[0]:
        blocks.append(story.deck.strip())

    if story.points:
        blocks.append('\n'.join(f'▪ {p.strip()}' for p in story.points))

    if story.takeaway:
        blocks.append(f'{M_NOTE} {story.takeaway.strip()}')

    if story.correction:
        blocks.append(f'ತಿದ್ದುಪಡಿ: {story.correction.strip()}')

    blocks.append(_join([dateline(story), status_line(story),
                         photo_note(story), source_line(story)]).replace('\n\n', '\n'))

    g = Brand.grievance_line()
    if g:
        blocks.append(g)

    blocks.append(' '.join(f'#{t}' for t in tags))

    cap = _join(blocks)
    if len(cap) > IG_CAPTION_MAX:                 # trim the facts, never the sourcing
        over = len(cap) - IG_CAPTION_MAX
        if story.points:
            trimmed = story.points[:-1]
            cap = instagram_caption(
                Story(**{**story.to_dict(), 'points': trimmed,
                         'published_at': story.published_at,
                         'photo': story.photo}), tags)
    return cap


def whatsapp_text(story: Story) -> str:
    """Plain text for forwarding. No hashtags, no markers that render as boxes
    on older Android keyboards; WhatsApp is where regional news actually
    travels, and it travels as text."""
    blocks = [f'*{story.headline.strip()}*']
    if story.deck:
        blocks.append(story.deck.strip())
    if story.points:
        blocks.append('\n'.join(f'• {p.strip()}' for p in story.points))
    if story.takeaway:
        blocks.append(story.takeaway.strip())
    meta = [b for b in (story.location, f'{story.date_kn} · {story.time_kn}')
            if b]
    blocks.append(' · '.join(meta))
    blocks.append('ಮೂಲ: ' + ' · '.join(story.sources))
    blocks.append(f'— {Brand.name} · {Brand.handle}')
    return _join(blocks)


def x_post(story: Story) -> str:
    line = (story.reel_line or story.headline).strip()
    tail = f'\n\n{Brand.handle}'
    room = X_MAX - len(tail) - 2
    # Only prefix the place when the line does not already open with it —
    # a headline written as "ಕುಂದಾಪುರ: …" must not become "ಕುಂದಾಪುರ: ಕುಂದಾಪುರ: …".
    if story.location and not _leads_with_place(line, story.location):
        prefix = f'{story.location}: '
        if len(prefix) + len(line) <= room:
            line = prefix + line
    if len(line) > room:
        line = line[:room - 1].rstrip() + '…'
    return line + tail


# ─────────────────────────────────────────────────────────────────────────────
#  YOUTUBE
# ─────────────────────────────────────────────────────────────────────────────

def youtube_title(subject: Story | Edition, kind: str = 'short') -> str:
    """A title that still reads in a search result.

    ~60 characters is what actually displays; the 100-character limit is where
    it gets cut off, not where it stops being read.
    """
    if isinstance(subject, Edition):
        lead = subject.stories[0]
        base = (lead.reel_line or lead.headline).strip().rstrip('.')
        title = f'{base} | {subject.date_kn} {Brand.bulletin}'
    else:
        base = (subject.reel_line or subject.headline).strip().rstrip('.')
        loc = (f'{subject.location} | ' if subject.location
               and not _leads_with_place(base, subject.location) else '')
        title = f'{loc}{base}'
    if kind == 'short' and '#Shorts' not in title:
        if len(title) + 8 <= YT_TITLE_MAX:
            title += ' #Shorts'
    return title[:YT_TITLE_MAX]


def youtube_description(subject: Story | Edition) -> str:
    stories = subject.stories if isinstance(subject, Edition) else [subject]
    date_kn = subject.date_kn if isinstance(subject, Edition) else stories[0].date_kn

    blocks = [f'{Brand.name} · {Brand.tagline}', f'{Brand.bulletin} — {date_kn}']

    for i, st in enumerate(stories, 1):
        seg = [f'{i}. {st.headline.strip()}']
        if st.deck:
            seg.append(f'   {st.deck.strip()}')
        for p in st.points[:3]:
            seg.append(f'   • {p.strip()}')
        meta = [b for b in (st.location, STATUS[st.status][0]) if b]
        if meta:
            seg.append('   ' + ' · '.join(meta))
        seg.append('   ಮೂಲ: ' + ' · '.join(st.sources))
        if st.photo:
            seg.append('   ' + photo_note(st))
        blocks.append('\n'.join(seg))

    g = Brand.grievance_line()
    if g:
        blocks.append(g)
    blocks.append(f'ಫಾಲೋ ಮಾಡಿ: Instagram {Brand.handle}')
    blocks.append(' '.join(f'#{t}' for t in
                           hashtags(stories[0], limit=15)))
    desc = _join(blocks)
    return desc[:YT_DESC_MAX]


def youtube_tags(subject: Story | Edition, limit: int = 20) -> list[str]:
    stories = subject.stories if isinstance(subject, Edition) else [subject]
    out: list[str] = []
    for st in stories:
        for t in hashtags(st, limit=10):
            if t.lower() not in {x.lower() for x in out}:
                out.append(t)
    return out[:limit]


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def for_story(story: Story) -> PostCopy:
    tags = hashtags(story)
    return PostCopy(
        hook=hook(story),
        instagram=instagram_caption(story, tags),
        hashtags=tags,
        alt_text=alt_text(story),
        whatsapp=whatsapp_text(story),
        x_post=x_post(story),
        youtube_title=youtube_title(story, 'short'),
        youtube_description=youtube_description(story),
        youtube_tags=youtube_tags(story),
    )


def for_edition(edition: Edition) -> PostCopy:
    """Copy for the carousel / reel / bulletin, which cover the whole edition."""
    lead = edition.stories[0]
    tags = hashtags(lead, limit=14)
    heads = '\n'.join(f'▪ {s.headline.strip()}' for s in edition.stories)
    seen: list[str] = []
    for s in edition.stories:
        for src in s.sources:
            if src not in seen:
                seen.append(src)

    blocks = [f'{edition.date_kn} · {Brand.bulletin}', heads]
    g = Brand.grievance_line()
    blocks.append(f'{M_SOURCE} ಮೂಲ: ' + ' · '.join(seen))
    if g:
        blocks.append(g)
    blocks.append(' '.join(f'#{t}' for t in tags))

    return PostCopy(
        hook=f'{edition.date_kn} · {Brand.bulletin}',
        instagram=_join(blocks),
        hashtags=tags,
        alt_text=(f'{Brand.name} {Brand.bulletin} — {edition.date_kn}. '
                  f'{len(edition.stories)} ಸುದ್ದಿಗಳ ಸಂಗ್ರಹ.'),
        whatsapp=_join([f'*{Brand.name} · {edition.date_kn}*', heads.replace('▪', '•'),
                        'ಮೂಲ: ' + ' · '.join(seen), f'— {Brand.handle}']),
        x_post=x_post(lead),
        youtube_title=youtube_title(edition, 'long'),
        youtube_description=youtube_description(edition),
        youtube_tags=youtube_tags(edition),
    )
