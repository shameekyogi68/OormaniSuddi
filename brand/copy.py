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
from .tokens import Brand, CATEGORIES, category, Limits

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
# Kannada and hyperlocal first: a 15-day-old account competing on
# #BreakingNews is invisible. The people who will actually watch live in
# the tagged place.
CATEGORY_TAGS = {
    'breaking':  ['ಬ್ರೇಕಿಂಗ್‌ನ್ಯೂಸ್', 'UdupiNews'],
    'crime':     ['ಅಪರಾಧಸುದ್ದಿ', 'CrimeNews'],
    'weather':   ['ಹವಾಮಾನ', 'WeatherAlert', 'KarnatakaRains'],
    'civic':     ['ಆಡಳಿತ', 'CivicNews'],
    'health':    ['ಆರೋಗ್ಯ', 'HealthNews'],
    'education': ['ಶಿಕ್ಷಣ', 'EducationNews'],
    'culture':   ['ಸಂಸ್ಕೃತಿ', 'Culture'],
    'sport':     ['ಕ್ರೀಡೆ', 'Sports'],
    'farm':      ['ಕೃಷಿ', 'Agriculture'],
    'obituary':  ['ನಿಧನ', 'Obituary'],
    'explainer': ['ವಿಶ್ಲೇಷಣೆ', 'Explainer'],
}

# Always-on. Small pool, right people. Mega-tags (#Karnataka, #KannadaNews)
# put a new channel in a feed with millions of posts and a 0.2% chance of
# being picked; they go last, and only if there is room.
CORE_TAGS = ['oormanisuddi', 'ಕರಾವಳಿ', 'ಕರಾವಳಿಸುದ್ದಿ', 'KaravaliNews']
WIDE_TAGS = ['CoastalKarnataka', 'ಕನ್ನಡಸುದ್ದಿ', 'KannadaNews', 'Karnataka']

# Latin equivalents for places we cover, so a Kannada location also produces a
# searchable English tag. Add to it as coverage grows; unknown places simply
# fall back to the Kannada tag alone.
PLACE_TAGS = {
    'ಉಡುಪಿ': 'Udupi', 'ಕುಂದಾಪುರ': 'Kundapura', 'ಬೈಂದೂರು': 'Byndoor',
    'ಒತ್ತಿನೆನೆ': 'Ottinene', 'ಬ್ರಹ್ಮಾವರ': 'Brahmavara', 'ಕಾರ್ಕಳ': 'Karkala', 'ಮಣಿಪಾಲ': 'Manipal',
    'ಮಲ್ಪೆ': 'Malpe', 'ಕಾಪು': 'Kaup', 'ಹೆಬ್ರಿ': 'Hebri',
    'ಹೆಮ್ಮಾಡಿ': 'Hemmadi', 'ಗಂಗೊಲ್ಲಿ': 'Gangolli', 'ಕೋಡಿ': 'Kodi',
    'ಮಂಗಳೂರು': 'Mangaluru', 'ದಕ್ಷಿಣ ಕನ್ನಡ': 'DakshinaKannada',
    'ಉತ್ತರ ಕನ್ನಡ': 'UttaraKannada', 'ಶಿರಸಿ': 'Sirsi', 'ಭಟ್ಕಳ': 'Bhatkal',
    'ಕುಮಟಾ': 'Kumta', 'ಹೊನ್ನಾವರ': 'Honnavar', 'ಬೆಂಗಳೂರು': 'Bengaluru',
    'ಉಡುಪಿ ಜಿಲ್ಲೆ': 'Udupi', 'ಉಳ್ಳಾಲ': 'Ullal',
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


def hashtags(story: Story, limit: int = 8) -> list[str]:
    """Place + category + brand, de-duplicated and capped.

    Ordered by specificity: the tags most likely to reach the right people come
    first, because that is the order a reader skims and the order that survives
    if you trim the list. Default 8 — Instagram has not ranked a 30-tag block
    since 2021, and a new account using mega-tags is sorted into a pool it
    cannot win.
    """
    out: list[str] = []

    def add(tag: str):
        t = _tagify(tag)
        if t and t.lower() not in {x.lower() for x in out}:
            out.append(t)

    loc = story.location or ''
    for part in re.split(r'[\/|,·•]| - ', loc):
        part = part.strip()
        if not part:
            continue
        add(part)
        if part in PLACE_TAGS:
            add(PLACE_TAGS[part])
            add(PLACE_TAGS[part] + 'News')

    # Substring match so "ಉಡುಪಿ ಜಿಲ್ಲೆ" still produces #Udupi and #UdupiNews.
    for kn, en in PLACE_TAGS.items():
        if kn and kn in loc:
            add(kn)
            add(en)
            add(en + 'News')
            add(kn.replace(' ', '') + 'ಸುದ್ದಿ')

    for t in CATEGORY_TAGS.get(story.category, []):
        add(t)
    for t in CORE_TAGS:
        add(t)
    for t in WIDE_TAGS:
        if len(out) >= limit:
            break
        add(t)
    return out[:min(limit, IG_HASHTAG_MAX)]


def edition_hashtags(edition: Edition, limit: int = 28) -> list[str]:
    """Places and categories from ALL stories in the edition, de-duplicated and capped.

    House rule 2026-09-17-07: a carousel is an edition, not a single story;
    its hashtags must represent all towns and topics featured in the swipe set.
    """
    out: list[str] = []

    def add(tag: str):
        t = _tagify(tag)
        if t and t.lower() not in {x.lower() for x in out}:
            out.append(t)

    # 1. Locations for every story in the edition
    for st in edition.stories:
        loc = st.location or ''
        for part in re.split(r'[\/|,·•]| - ', loc):
            part = part.strip()
            if not part:
                continue
            add(part)
            if part in PLACE_TAGS:
                add(PLACE_TAGS[part])
                add(PLACE_TAGS[part] + 'News')
        for kn, en in PLACE_TAGS.items():
            if kn and kn in loc:
                add(kn)
                add(en)
                add(en + 'News')
                add(kn.replace(' ', '') + 'ಸುದ್ದಿ')

    # 2. Categories for every story in the edition
    for st in edition.stories:
        for t in CATEGORY_TAGS.get(st.category, []):
            add(t)

    # 3. Channel core tags
    for t in CORE_TAGS:
        add(t)

    # 4. Regional wide tags
    for t in WIDE_TAGS:
        if len(out) >= limit:
            break
        add(t)

    return out[:min(limit, IG_HASHTAG_MAX)]


# ─────────────────────────────────────────────────────────────────────────────
#  PIECES
# ─────────────────────────────────────────────────────────────────────────────

def _place_token(location: str) -> str:
    """The shortest named place inside a location string, for search."""
    loc = (location or '').strip()
    if not loc:
        return ''
    for kn in PLACE_TAGS:
        if kn and kn in loc:
            return kn
    return re.split(r'[\/|,·•]| - ', loc)[0].strip()


# ── Kannada case marking ─────────────────────────────────────────────────────
# Kannada case markers are BOUND morphemes: they agglutinate onto the noun and
# take a linking stem with them. Writing them as free-standing words — "ಉಡುಪಿ
# ನಲ್ಲಿ" for ಉಡುಪಿಯಲ್ಲಿ — is the Kannada equivalent of "Udupi in", and it went
# out on the first comment of every weather post.
#
# The linking stem is decided by the noun's final vowel, and the same three
# stems serve every suffix we need:
#
#   ends ಿ ೀ ೆ ೇ ೈ   → + ಯ     ಉಡುಪಿ  → ಉಡುಪಿಯ…    ಜಿಲ್ಲೆ → ಜಿಲ್ಲೆಯ…
#   ends ು ೂ         → + ಿನ    ಮಂಗಳೂರು → ಮಂಗಳೂರಿನ…  (the ು is replaced)
#   ends ಾ, or a bare consonant carrying inherent 'a'
#                    → + ದ     ಕುಂದಾಪುರ → ಕುಂದಾಪುರದ…  ಕುಮಟಾ → ಕುಮಟಾದ…
#
# Anything else — an independent vowel letter, a virama, a Latin name — returns
# '' and the caller falls back to a phrasing that needs no case marker at all.
# Guessing morphology for a place we cannot analyse would put broken Kannada in
# front of readers, which is worse than a slightly plainer sentence.
_KN_FRONT   = 'ಿೀೆೇೈ'
_KN_BACK_U  = 'ುೂ'
_KN_MATRAS  = 'ಾಿೀುೂೃೆೇೈೊೋೌ್'


def _oblique_stem(word: str) -> str:
    """The stem a Kannada case suffix attaches to, or '' if we cannot tell."""
    w = word.strip()
    if not w:
        return ''
    last = w[-1]
    if last in _KN_FRONT:
        return w + 'ಯ'
    if last in _KN_BACK_U:
        return w[:-1] + 'ಿನ'
    if last == 'ಾ':
        return w + 'ದ'
    if last in _KN_MATRAS:          # ೃ ೊ ೋ ೌ ್ — not confident, say so
        return ''
    if '\u0c85' <= last <= '\u0c94':   # independent vowel letter
        return ''
    if '\u0c95' <= last <= '\u0cb9':   # consonant, inherent 'a'
        return w + 'ದ'
    return ''                        # Latin, digits, punctuation


def _inflect(place: str, suffix: str) -> str:
    """`place` + a Kannada case suffix, inflecting only its last word.

    "ಉಡುಪಿ ಜಿಲ್ಲೆ" takes the marker on ಜಿಲ್ಲೆ, not on ಉಡುಪಿ. Returns '' when the
    stem cannot be determined, so callers can choose another phrasing.
    """
    p = (place or '').strip()
    if not p:
        return ''
    head, _, last = p.rpartition(' ')
    stem = _oblique_stem(last)
    if not stem:
        return ''
    return (head + ' ' if head else '') + stem + suffix


def locative(place: str) -> str:
    """ಉಡುಪಿ → ಉಡುಪಿಯಲ್ಲಿ ("in Udupi"). '' if it cannot be formed."""
    return _inflect(place, 'ಲ್ಲಿ')


def belonging(place: str) -> str:
    """ಉಡುಪಿ → ಉಡುಪಿಯವರಾ ("are you an Udupi person?"). '' if not formable."""
    return _inflect(place, 'ವರಾ')


def hook(story: Story) -> str:
    """The first line — everything Instagram shows before the fold.

    Prefers the thumbnail `hook`, then `reel_line`, then the headline. Prefixes
    the place when it is not already in the line: Instagram search matches this
    window, and a coastal story that does not name the town here is invisible
    to the people it is for.
    """
    line = (getattr(story, '_hook', '') or story.reel_line or story.headline).strip()
    short = _place_token(story.location or '')
    if short and short not in line and not _leads_with_place(line, short):
        candidate = f'{short}: {line}'
        if len(candidate) <= FOLD:
            line = candidate
    if len(line) <= FOLD:
        return line
    cut = line[:FOLD]
    for sep in ('. ', '? ', '! ', ': ', ' — ', ' '):
        if sep in cut:
            return cut.rsplit(sep, 1)[0].rstrip(' :—-') + '…'
    return cut.rstrip() + '…'


def cta(story: Story) -> str:
    """One line that asks for a comment or a share — the signals the
    algorithm actually distributes on. Crime stories ask to share, not to
    opine; weather asks what is happening in your town."""
    if story.category == 'crime':
        return 'ಈ ಸುದ್ದಿ ಊರಿಗೆ ತಲುಪಲಿ — ಶೇರ್ ಮಾಡಿ.'
    if story.category == 'weather':
        return 'ನಿಮ್ಮ ಊರಿನ ಪರಿಸ್ಥಿತಿ ಹೇಗಿದೆ? ಕಾಮೆಂಟ್ ಮಾಡಿ.'
    if story.category == 'obituary':
        return 'ಮತ್ತಷ್ಟು ಕರಾವಳಿ ಸುದ್ದಿಗೆ ಫಾಲೋ ಮಾಡಿ.'
    return 'ನಿಮಗೆ ಏನನ್ನಿಸುತ್ತೆ? ಕಾಮೆಂಟ್ ಮಾಡಿ · ಊರಿಗೆ ತಲುಪಲಿ ಎಂದು ಶೇರ್ ಮಾಡಿ.'


def first_comment(story: Story) -> str:
    """Paste this as the FIRST comment the moment the post goes up.

    Instagram treats an early comment as a conversation starter; the post
    then gets shown to more of the same audience. A question beats a
    restatement of the headline.
    """
    loc = _place_token(story.location or '') or Brand.coverage
    if story.category == 'weather':
        where = locative(loc)
        return (f'{where} ಈಗ ಹೇಗಿದೆ? ರಿಪ್ಲೈ ಮಾಡಿ.' if where
                else f'{loc} — ಈಗ ಅಲ್ಲಿ ಹೇಗಿದೆ? ರಿಪ್ಲೈ ಮಾಡಿ.')
    if story.category == 'crime':
        return f'{loc} — ಮೂಲ: ಸತ್ಯಾಧಾರಿತ ವರದಿ. ಇನ್ನಷ್ಟು ಕರಾವಳಿ ಸುದ್ದಿಗೆ ಫಾಲೋ ಮಾಡಿ.'
    whose = belonging(loc)
    return (f'ನೀವು {whose}? ರಿಪ್ಲೈ ಮಾಡಿ — {Brand.handle}' if whose
            else f'{loc} — ನಿಮ್ಮ ಊರಾ? ರಿಪ್ಲೈ ಮಾಡಿ — {Brand.handle}')


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
    instagram: str
    youtube_title: str = ''
    youtube_description: str = ''
    youtube_tags: list[str] = field(default_factory=list)
    hook: str = ''
    hashtags: list[str] = field(default_factory=list)
    alt_text: str = ''
    whatsapp: str = ''
    x_post: str = ''
    first_comment: str = ''

    def to_dict(self) -> dict:
        return {
            'instagram': self.instagram,
            'whatsapp': self.whatsapp,
            'first_comment': self.first_comment,
            'youtube_title': self.youtube_title,
            'youtube_description': self.youtube_description,
            'youtube_tags': self.youtube_tags,
        }


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

    # Continuity. A reader who saw the first report is told this is the same
    # story moving, and a reader who did not is told there is more behind it.
    # Both are reasons to follow rather than to scroll.
    if story.follows_up:
        blocks.append(f'ಈ ಹಿಂದಿನ ವರದಿಯ ಮುಂದುವರಿಕೆ ({story.follows_up}).')

    blocks.append(cta(story))

    blocks.append(_join([dateline(story), status_line(story),
                         photo_note(story), source_line(story)]).replace('\n\n', '\n'))

    g = Brand.grievance_line()
    if g:
        blocks.append(g)
    if Brand.voice_disclosure_kn:
        blocks.append(Brand.voice_disclosure_kn)

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
    g = Brand.grievance_line()
    if g:
        blocks.append(g)
    if Brand.whatsapp_url:
        blocks.append(Brand.whatsapp_url)
    blocks.append(f'— {Brand.name} · {Brand.handle}')
    return _join(blocks)


def taluk_forwards(edition) -> dict[str, str]:
    """One WhatsApp forward per place this edition actually covers.

    The reason this exists rather than a single district round-up: people
    forward what is THEIRS. Somebody in Kundapura sends the Kundapura story
    into a Kundapura group, with their own name attached to it. Nobody
    forwards a seven-taluk digest, because a digest is nobody's in particular
    and there is no group it obviously belongs in.

    Same stories, same facts, same sourcing — re-cut so the first line names
    the reader's town. The places come from PLACE_TAGS, which is the one
    registry of place names in this project; nothing here invents a town.
    """
    from .reach import places_covered
    out: dict[str, str] = {}
    covered = places_covered(edition)
    if not covered:
        return out

    for place, ids in sorted(covered.items()):
        stories = [edition.stories[i - 1] for i in ids]
        lines = [f'*{place} — {edition.date_kn}*', '']
        for st in stories:
            lines.append(f'*{st.headline.strip()}*')
            if st.deck:
                lines.append(st.deck.strip())
            for pt in st.points[:2]:
                lines.append(f'• {pt.strip()}')
            if st.takeaway:
                lines.append(st.takeaway.strip())
            lines.append('')
        seen: list[str] = []
        for st in stories:
            for s_ in st.sources:
                if s_ not in seen:
                    seen.append(s_)
        lines.append('ಮೂಲ: ' + ' · '.join(seen))
        g = Brand.grievance_line()
        if g:
            lines.append(g)
        if Brand.whatsapp_url:
            lines.append(Brand.whatsapp_url)
        lines.append(f'— {Brand.name} · {Brand.handle}')
        out[place] = '\n'.join(l for l in lines if l is not None).strip()
    return out


def edition_whatsapp(edition: Edition, instagram_url: str | None = None) -> str:
    """Tailored WhatsApp group / broadcast digest for the daily edition.

    Numbered emoji bullets, location prefixes, direct Instagram CTA
    (never mentioning 'photos' when AI imagery is used), source credits, and
    brand handle. House rule 2026-09-17-08.
    """
    emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    items = []
    for i, s in enumerate(edition.stories):
        num = emojis[i] if i < len(emojis) else f'{i+1}️⃣'
        loc = f'*{s.location}*: ' if s.location else ''
        head = s.headline.strip()
        if s.location and head.startswith(f'{s.location}:'):
            head = head[len(f'{s.location}:'):].strip()
        items.append(f'{num} {loc}{head}')
    headlines_block = '\n'.join(items)

    seen: list[str] = []
    for s in edition.stories:
        for src in s.sources:
            if src not in seen:
                seen.append(src)

    link_target = instagram_url or '[ಇನ್‌ಸ್ಟಾಗ್ರಾಮ್ ಪೋಸ್ಟ್ ಲಿಂಕ್]'

    tagline = Brand.tagline.replace('  •  ', ' • ')
    blocks = [
        f'🌾 *{Brand.name} · {edition.date_kn}*\n{tagline}',
        f'ಇಂದಿನ ಪ್ರಮುಖ ಕರಾವಳಿ ಮುಖ್ಯಾಂಶಗಳು:\n\n{headlines_block}',
        f'📲 *ಪೂರ್ಣ ವರದಿ ಹಾಗೂ ವಿವರಣೆಗಾಗಿ ಇನ್‌ಸ್ಟಾಗ್ರಾಮ್ ಲಿಂಕ್ ನೋಡಿ:*\n👉 {link_target}',
        f'📌 ಮೂಲ: ' + ' · '.join(seen),
        f'— {Brand.handle}',
    ]
    return '\n\n'.join(blocks)


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

    Do not append #Shorts. YouTube classifies Shorts by aspect ratio and
    duration; the hashtag wastes the characters that search actually shows
    and reads as spam in a result.
    """
    if isinstance(subject, Edition):
        lead = subject.stories[0]
        base = (getattr(lead, '_hook', '') or lead.reel_line
                or lead.headline).strip().rstrip('.')
        title = f'{base} | {subject.date_kn} {Brand.bulletin}'
    else:
        base = (getattr(subject, '_hook', '') or subject.reel_line
                or subject.headline).strip().rstrip('.')
        loc = (f'{subject.location} | ' if subject.location
               and not _leads_with_place(base, subject.location) else '')
        title = f'{loc}{base}'
    return title[:YT_TITLE_MAX]


def youtube_description(subject: Story | Edition) -> str:
    stories = subject.stories if isinstance(subject, Edition) else [subject]
    date_kn = subject.date_kn if isinstance(subject, Edition) else stories[0].date_kn
    lead = stories[0]

    # First two lines are the search snippet. Lead with the story, not the
    # brand — YouTube matches keywords here, and "ಊರ್ಮನಿ ಸುದ್ದಿ · ನಮ್ಮ ಊರು"
    # is a phrase nobody searches for.
    blocks = [hook(lead)]
    if lead.deck and lead.deck.strip() not in blocks[0]:
        blocks.append(lead.deck.strip())
    blocks.append(f'{Brand.name} · {Brand.tagline}')
    blocks.append(f'{Brand.bulletin} — {date_kn}')

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
    blocks.append(Brand.channels_block())
    blocks.append(f'Subscribe · {Brand.name} · {Brand.handle}')
    # Engagement CTA — drive the comment signal that the algorithm needs.
    # Zero comments across 16/17 videos (Sept 2026 audit) was a primary reason
    # for algorithmic suppression. A direct Kannada question prompts replies.
    blocks.append('💬 ನಿಮ್ಮ ಅಭಿಪ್ರಾಯ ಏನು? ಕಮೆಂಟ್ ಮಾಡಿ!')
    # YouTube shows the first three hashtags above the title. Place tags
    # already lead the list.
    blocks.append(' '.join(f'#{t}' for t in
                           hashtags(stories[0], limit=8)))
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

# ─────────────────────────────────────────────────────────────────────────────
#  PUBLISHING PLAN
# ─────────────────────────────────────────────────────────────────────────────

# Coastal Karnataka engagement windows, IST. These are STARTING positions from
# the shape of the day here — the fishing and commute morning, the lunch break,
# the evening after work — not measured truth about this account. Once the
# channel has its own analytics, move them to what the analytics say. A plan
# that is written down is a plan you can correct; the one that was retyped by
# hand every morning drifted instead.
#
# Two rules do the real work:
#   * reels are spaced at least 2.5h apart, because two of ours in one window
#     compete with each other rather than with anyone else;
#   * AI-card reels are Instagram-only (Rule 7). YouTube gets real footage.
# Peak engagement windows, IST — starting positions, not measured truth.
REEL_MIN_GAP_MIN = Limits.reel_gap_min
REEL_SLOTS = list(Limits.reel_slots)


def _reel_times(n: int) -> list[str]:
    """Upload times for n reels, never closer together than the gap rule.

    Four is the documented shape of a day. Beyond that the times simply keep
    stepping by the gap — spacing is preserved, but a fifth and sixth reel are
    landing late enough that the plan is telling you to publish fewer, better.
    """
    out: list[str] = []
    for i in range(n):
        if i < len(REEL_SLOTS):
            out.append(REEL_SLOTS[i])
            continue
        prev = out[-1]
        m = min(int(prev[:2]) * 60 + int(prev[3:]) + REEL_MIN_GAP_MIN,
                23 * 60 + 45)
        out.append(f'{m // 60:02d}:{m % 60:02d}')
    return out


@dataclass(frozen=True)
class Slot:
    at: str          # HH:MM IST
    asset: str       # the file to upload
    platform: str
    what: str
    why: str


def publishing_plan(n_reels: int, has_bulletin: bool = False,
                    has_carousel: bool = True, has_story_card: bool = True,
                    has_broadsheet: bool = True,
                    carousel_last: str = '',
                    bulletin_is_footage: bool = False,
                    has_roundup: bool = False) -> list[Slot]:
    """The day's upload order, derived from what was actually rendered.

    AI-card reels are Instagram-only. The 16:9 AI bulletin is off by default
    and is never scheduled to YouTube unless `bulletin_is_footage` is True.
    D55 / AGENTS Rule 7.
    """
    plan: list[Slot] = []
    if has_bulletin:
        if bulletin_is_footage:
            plan.append(Slot(
                Limits.bulletin_slot, 'bulletin.mp4', 'YouTube',
                'Long-form bulletin (16:9) — set yt_thumbnail.jpg as the thumbnail',
                'Real footage only. Posted first so it has the full day to '
                'gather watch time on the 4,000-hour path.'))
        else:
            plan.append(Slot(
                Limits.bulletin_slot, 'bulletin.mp4',
                'HOLD — not for YouTube',
                'AI bulletin rendered internally. Do not upload to YouTube.',
                'Rule 7: YouTube suppresses AI TTS slideshows (37 vs 397 views). '
                'Keep this file as a record, or post to Instagram only if asked.'))
    if has_carousel:
        last = carousel_last or 'carousel_06_sources.jpg'
        plan.append(Slot(
            Limits.carousel_slot, f'carousel_01_cover.jpg … {last}',
            'Instagram',
            'Carousel — the whole edition, swipeable',
            'The morning scroll. A carousel is the only format that gets a '
            'second impression when someone does not swipe the first time.'))
    if has_story_card:
        plan.append(Slot(
            Limits.story_slot, 'story_9x16.jpg', 'Instagram Story / WhatsApp',
            'Story card pointing at the carousel',
            'Posted just after, so the people who open Stories first are sent '
            'to a post that already exists.'))

    if has_roundup:
        # The day's reel when it is speed news (D81). It takes the first reel
        # window; any single-story reels follow it.
        plan.append(Slot(
            _reel_times(1)[0], 'roundup.mp4  (cover: roundup_cover.jpg)',
            'Instagram Reels',
            'ಸ್ಪೀಡ್ ನ್ಯೂಸ್ — the day in one reel. Caption: roundup_caption.txt',
            'Instagram only (Rule 7). Set roundup_cover.jpg as the cover; it '
            'is story one with its headline up, not frame 0.'))

    for i, at in enumerate(_reel_times(n_reels + (1 if has_roundup else 0))
                           [1 if has_roundup else 0:]):
        n = i + 1
        plan.append(Slot(
            at, f'reel_{n:02d}.mp4  (cover: reel_{n:02d}_cover.jpg)',
            'Instagram Reels',
            f'Reel {n} — caption and first comment in reel_{n:02d}_copy.txt',
            'Instagram only. Do not cross-post this AI reel to YouTube Shorts '
            'unless the editor explicitly overrides for a story with no tape. '
            'Set the cover frame; paste the first comment immediately.'))

    if has_broadsheet:
        plan.append(Slot(
            Limits.broadsheet_slot, 'broadsheet.jpg', 'WhatsApp / Telegram',
            "The day's front page, as a forward",
            'Forwards are where a local channel actually grows. Paste the '
            'WhatsApp text from MASTER_COPY.md. Aim under 300 KB.'))

    return sorted(plan, key=lambda s: s.at)


def plan_text(plan: list[Slot], date_kn: str = '') -> str:
    """The plan as something you can read down at 7am."""
    out = [f'ಊರ್ಮನಿ ಸುದ್ದಿ — publishing plan{"  ·  " + date_kn if date_kn else ""}',
           'All times IST. Windows are starting positions — move them to '
           'whatever your own analytics say once you have a month of them.', '']
    for s in plan:
        out.append(f'{s.at}  {s.platform}')
        out.append(f'        {s.what}')
        out.append(f'        file: {s.asset}')
        out.append(f'        why:  {s.why}')
        out.append('')
    return '\n'.join(out).rstrip() + '\n'


# ─────────────────────────────────────────────────────────────────────────────
#  THE CAPTION FILE
#  House rule 2026-09-17-06. Every post already ships a `_copy.txt` that
#  carries the caption, the first comment, the WhatsApp forward and the
#  YouTube fields under banner headings — a working sheet to read. Posting is
#  a different job: at 08:00 on a phone you want one file whose entire
#  contents are the thing you paste, so select-all is always the right move
#  and there is nothing to accidentally paste with it.
# ─────────────────────────────────────────────────────────────────────────────

# Which platform a post belongs to, by its own file stem. The AI-card formats
# are Instagram's; only the 16:9 bulletin and its thumbnail are YouTube's —
# AGENTS rule 7, YouTube gets real footage, not card reels.
YOUTUBE_POSTS = ('bulletin', 'youtube_thumb', 'yt_thumb')


def platform_of(name: str) -> str:
    """'youtube' or 'instagram', decided from a post's file stem."""
    n = (name or '').lower()
    return 'youtube' if any(k in n for k in YOUTUBE_POSTS) else 'instagram'


def caption_text(c: PostCopy, platform: str = 'instagram') -> str:
    """The paste-ready caption for one post, and nothing else.

    No banner rules, no section headings, no first comment, no WhatsApp
    forward — those live in `_copy.txt` and `MASTER_COPY.md`, which is what
    they are for. A caption file that carries anything but the caption is a
    caption file somebody eventually pastes the wrong half of.

    YouTube is the one exception, and only because it has to be: a title
    cannot go in the description box. Three labelled fields is the smallest
    honest shape for a video post.
    """
    if platform == 'youtube':
        return (f'TITLE\n{c.youtube_title.strip()}\n\n'
                f'DESCRIPTION\n{c.youtube_description.strip()}\n\n'
                f'TAGS\n{", ".join(c.youtube_tags)}\n')
    return c.instagram.strip() + '\n'


def for_story(story: Story) -> PostCopy:
    tags = hashtags(story)
    return PostCopy(
        hook=hook(story),
        instagram=instagram_caption(story, tags),
        hashtags=tags,
        alt_text=alt_text(story),
        whatsapp=whatsapp_text(story),
        x_post=x_post(story),
        first_comment=first_comment(story),
        youtube_title=youtube_title(story, 'short'),
        youtube_description=youtube_description(story),
        youtube_tags=youtube_tags(story),
    )


def for_roundup(edition: Edition, seconds: float = 0.0) -> PostCopy:
    """Copy for the ಸ್ಪೀಡ್ ನ್ಯೂಸ್ reel — the day's stories in one video (D81).

    Not `for_edition`, whose second line is "ಸ್ವೈಪ್ ಮಾಡಿ": a reel has nothing
    to swipe. Every story is listed with its PLACE first, because the place
    is what makes somebody in Kundapura stop scrolling, and the caption
    carries both disclosures the video owes — a synthetic anchor, and
    generated pictures where there are any.
    """
    lead = edition.stories[0]
    n = len(edition.stories)
    hook_line = hook(lead)
    when = f', {round(seconds)} ಸೆಕೆಂಡಿನಲ್ಲಿ' if seconds >= 1 else ''
    heads = []
    for s in edition.stories:
        place = (s.location or '').strip() or Brand.coverage
        line = (s.reel_line or s.headline).strip()
        heads.append(f'▪ {line}' if _leads_with_place(line, place)
                     else f'▪ {place}: {line}')
    seen: list[str] = []
    for s in edition.stories:
        for src in s.sources:
            if src not in seen:
                seen.append(src)
    blocks = [hook_line, f'ಇಂದಿನ {n} ಕರಾವಳಿ ಸುದ್ದಿ{when}.', '\n'.join(heads),
              cta(lead), f'{M_SOURCE} ಮೂಲ: ' + ' · '.join(seen)]
    if any(s.photo is not None and s.photo.nature == 'ai' for s in edition.stories):
        blocks.append('ಈ ವೀಡಿಯೊದ ಚಿತ್ರಗಳು ಎಐ ರಚಿತ ಸಾಂದರ್ಭಿಕ ಚಿತ್ರಗಳು.')
    if Brand.voice_disclosure_kn:
        blocks.append(Brand.voice_disclosure_kn)
    g = Brand.grievance_line()
    if g:
        blocks.append(g)
    tags = edition_hashtags(edition, limit=12)
    blocks.append(' '.join(f'#{t}' for t in tags))
    return PostCopy(
        hook=hook_line,
        instagram=_join(blocks),
        hashtags=tags,
        alt_text=(f'{Brand.name} ಸ್ಪೀಡ್ ನ್ಯೂಸ್ — {edition.date_kn}. '
                  f'{n} ಸುದ್ದಿಗಳು. {lead.headline}'),
        whatsapp=edition_whatsapp(edition),
        x_post=x_post(lead),
        first_comment=first_comment(lead),
    )


def for_edition(edition: Edition) -> PostCopy:
    """Copy for the carousel / bulletin. The reel uses for_story(lead).

    The first line is the lead story's hook, never the date. A caption that
    opens "28 ಆಗಸ್ಟ್ · ಕರಾವಳಿ ಬುಲೆಟಿನ್" is a scroll-past; the news has to
    earn the tap on its own, the same rule as a single-story caption.
    """
    lead = edition.stories[0]
    tags = edition_hashtags(edition, limit=28)
    hook_line = hook(lead)
    heads = '\n'.join(f'▪ {s.headline.strip()}' for s in edition.stories)
    seen: list[str] = []
    for s in edition.stories:
        for src in s.sources:
            if src not in seen:
                seen.append(src)

    n = len(edition.stories)
    blocks = [
        hook_line,
        f'ಸ್ವೈಪ್ ಮಾಡಿ — ಇಂದಿನ {n} ಸುದ್ದಿ.',
        heads,
        cta(lead),
    ]
    g = Brand.grievance_line()
    blocks.append(f'{M_SOURCE} ಮೂಲ: ' + ' · '.join(seen))
    if g:
        blocks.append(g)
    blocks.append(' '.join(f'#{t}' for t in tags))

    return PostCopy(
        hook=hook_line,
        instagram=_join(blocks),
        hashtags=tags,
        alt_text=(f'{Brand.name} {Brand.bulletin} — {edition.date_kn}. '
                  f'{n} ಸುದ್ದಿಗಳ ಸಂಗ್ರಹ. {lead.headline}'),
        whatsapp=edition_whatsapp(edition),
        x_post=x_post(lead),
        first_comment=first_comment(lead),
        youtube_title=youtube_title(edition, 'long'),
        youtube_description=youtube_description(edition),
        youtube_tags=youtube_tags(edition),
    )
