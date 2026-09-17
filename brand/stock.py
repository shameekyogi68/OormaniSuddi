"""
ಊರ್ಮನಿ ಸುದ್ದಿ — the picture desk, when nobody is at it.
==========================================================
House rule 2026-09-17-03 says every carousel slide carries a photograph, and
the gate enforces it as `IMG-04`. `draft_edition.py` never attaches one — it
copies text and nothing else — so without this module every auto-drafted
morning is held at the gate on four counts before a person has read a word.

This picks a frame from `assets/stock/`, which is 24 catalogued, evergreen,
generated images the channel owns.

WHAT IT WILL NOT DO
-------------------
Attach a picture it cannot defend. `docs/AI_BRIEF.md` has always said a
loosely related stock image is worse than an honest plate, and that is still
true — a fishing harbour on a school story is a lie told in pictures. So a
story only gets a frame when its own category, or a word in its own copy,
maps to one. Anything else is left bare for the gate to stop and a person to
answer, which is the same shape as every other judgement call in this system.

The frame is labelled the way `assets/stock/CATALOG.md` specifies and
`Story.validate()` requires: `nature='ai'` because these were generated,
`licence='own'`, and a caption that says ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ — a representative
image — because that is what it is.
"""
from __future__ import annotations

import os

from .content import Photo, Story, Edition

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOCK_DIR = os.path.join(ROOT, 'assets', 'stock')

CREDIT = 'AI ಚಿತ್ರ — ಊರ್ಮನಿ ಸುದ್ದಿ'
CAPTION = 'ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ (ಎಐ ರಚಿತ ಚಿತ್ರ)'

# Kannada words that point at ONE frame more precisely than the category can.
# Checked before the category, because "ಜ್ವರ" is a better signal than
# "health" and "ಕಳವು" is a better signal than "crime". Same shape as
# `draft_edition.CATEGORY_HINTS`: a floor, not a classifier.
KEYWORD_FRAMES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ('ambulance_emergency_response_town.jpg',
     ('ಅಪಘಾತ', 'ಆಂಬ್ಯುಲೆನ್ಸ್', 'ತುರ್ತು', 'ಗಾಯ')),
    ('health_hospital_campus_outpatients.jpg',
     ('ಆಸ್ಪತ್ರೆ', 'ಜ್ವರ', 'ಸಾವು', 'ಚಿಕಿತ್ಸೆ', 'ಆರೋಗ್ಯ', 'ರೋಗ', 'ಸಾಂಕ್ರಾಮಿಕ',
      'ದಾಖಲು', 'ವೈದ್ಯ')),
    ('coastal_storm_sea_warning.jpg',
     ('ಚಂಡಮಾರುತ', 'ಅಲೆ', 'ಕಡಲ್ಕೊರೆತ', 'ಆರೆಂಜ್', 'ರೆಡ್ ಅಲರ್ಟ್')),
    ('crime_scene_police_cordon.jpg',
     ('ಘಟನಾ', 'ಮಹಜರು', 'ಶವ', 'ಹಲ್ಲೆ')),
    ('civic_flooded_road_villagers_complaint.jpg',
     ('ಪ್ರವಾಹ', 'ಜಲಾವೃತ', 'ಚರಂಡಿ', 'ನೀರು ನಿಂತ', 'ಕೆಸರು')),
    ('coastal_ghats_monsoon_homestead.jpg',
     ('ಮಳೆ', 'ಮುಂಗಾರು', 'ಗಾಳಿ', 'ಹವಾಮಾನ', 'ಚಂಡಮಾರುತ')),
    ('coastal_fishing_harbour_docks.jpg',
     ('ಮೀನುಗಾರ', 'ಬಂದರು', 'ದೋಣಿ', 'ಸಮುದ್ರ')),
    ('coastal_vented_dam_river_water.jpg',
     ('ಅಣೆಕಟ್ಟು', 'ಕಿಂಡಿ', 'ನದಿ', 'ಕುಡಿಯುವ ನೀರು')),
    ('traffic_police_highway_patrol.jpg',
     ('ಹೆದ್ದಾರಿ', 'ಸಂಚಾರ', 'ವಾಹನ', 'ಹೆಲ್ಮೆಟ್')),
    ('police_dog_squad_investigation.jpg',
     ('ಕೊಲೆ', 'ಕಳವು', 'ದರೋಡೆ', 'ತನಿಖೆ', 'ನಾಪತ್ತೆ')),
    ('police_cctv_surveillance_monitoring.jpg',
     ('ಸಿಸಿಟಿವಿ', 'ವಂಚನೆ', 'ಸೈಬರ್', 'ಆನ್‌ಲೈನ್', 'ಮೋಸ')),
    ('coastal_court_complex_judiciary.jpg',
     ('ನ್ಯಾಯಾಲಯ', 'ಕೋರ್ಟ್', 'ಜಾಮೀನು', 'ಶಿಕ್ಷೆ', 'ವಿಚಾರಣೆ')),
    ('forest_dept_timber_seizure_inspection.jpg',
     ('ಅರಣ್ಯ', 'ಮರ', 'ದಿಮ್ಮಿ', 'ಕಾಡು')),
    ('wildlife_leopard_trap_forest_cage.jpg',
     ('ಚಿರತೆ', 'ಹುಲಿ', 'ಆನೆ', 'ಕಾಡುಪ್ರಾಣಿ', 'ಬೋನು')),
    ('education_scholarship_certificate_ceremony.jpg',
     ('ವಿದ್ಯಾರ್ಥಿ', 'ಶಾಲೆ', 'ಕಾಲೇಜು', 'ಪರೀಕ್ಷೆ', 'ಫಲಿತಾಂಶ', 'ವಿದ್ಯಾರ್ಥಿವೇತನ')),
    ('rural_weekly_market_farmers_shandy.jpg',
     ('ರೈತ', 'ಕೃಷಿ', 'ಬೆಳೆ', 'ಸಂತೆ', 'ತರಕಾರಿ', 'ದರ', 'ಬೆಲೆ')),
    ('coastal_badagutittu_yakshagana_performance.jpg',
     ('ಯಕ್ಷಗಾನ', 'ಬಯಲಾಟ', 'ಮೇಳ', 'ಕಲಾವಿದ')),
    ('temple_ganahoma_vedic_ritual.jpg',
     ('ಹೋಮ', 'ಬ್ರಹ್ಮಕಲಶ', 'ಪೂಜೆ', 'ಜಾತ್ರೆ', 'ಉತ್ಸವ')),
    ('ganeshotsava_idol_devotional_pooja.jpg',
     ('ಗಣೇಶ', 'ಗಣಪತಿ', 'ಚತುರ್ಥಿ')),
    ('coastal_shiva_temple_linga_darshana.jpg',
     ('ಶಿವ', 'ದೇವಸ್ಥಾನ', 'ದರ್ಶನ', 'ಶಿವರಾತ್ರಿ')),
    ('taluk_revenue_office_files.jpg',
     ('ಕಚೇರಿ', 'ಕಂದಾಯ', 'ಲೋಕಾಯುಕ್ತ', 'ದಾಖಲೆ', 'ಅರ್ಜಿ', 'ಪಂಚಾಯಿತಿ')),
    ('civic_stray_dogs_street_menace.jpg',
     ('ಬೀದಿನಾಯಿ', 'ನಾಯಿ', 'ರೇಬಿಸ್')),
    ('coastal_event_site_police_inspection.jpg',
     ('ಸಭೆ', 'ಭೇಟಿ', 'ಸಿದ್ಧತೆ', 'ಪರಿಶೀಲನೆ', 'ಬಂದೋಬಸ್ತ್')),
    ('coastal_nh66_highway_traffic.jpg',
     ('ರಸ್ತೆ', 'ಸೇತುವೆ', 'ಬಸ್', 'ಪ್ರಯಾಣ')),
)

# The fallback, once no word in the story matched. One frame per category and
# only where a category has an honest one: `sport` and `obituary` have none
# in this library, and inventing a match for them is the thing this module
# refuses to do.
CATEGORY_FRAMES = {
    'weather':   'coastal_ghats_monsoon_homestead.jpg',
    'crime':     'police_dog_squad_investigation.jpg',
    'health':    'ambulance_emergency_response_town.jpg',
    'education': 'education_scholarship_certificate_ceremony.jpg',
    'culture':   'temple_ganahoma_vedic_ritual.jpg',
    'farm':      'rural_weekly_market_farmers_shandy.jpg',
    'civic':     'taluk_revenue_office_files.jpg',
    'breaking':  'coastal_nh66_highway_traffic.jpg',
}


def _exists(name: str) -> bool:
    return os.path.exists(os.path.join(STOCK_DIR, name))


def _mentions(text: str, word: str) -> bool:
    """True when a WORD of `text` is `word` or grows out of it.

    Kannada agglutinates, so a plain `in` test is the natural reach — and it
    is wrong: `ದರ` (price) sits inside `ವಿಚಾರದಲ್ಲಿ` (on the matter of), which
    put a farmers-market photograph on a story about a political row the
    first time this ran. Matching per word, from the start of the word, keeps
    ಮಳೆ → ಮಳೆಯಿಂದ while refusing the accidental middles.
    """
    return any(w.startswith(word) for w in text.split())


def frame_for(story: Story, taken: set | None = None) -> str:
    """The stock filename this story earns, or '' if none does.

    `taken` is the frames already used elsewhere in the same edition. Two
    slides of one carousel carrying the identical photograph reads as a
    broken render, so a frame is used once and the next candidate is tried.
    """
    taken = taken or set()
    text = ' '.join(filter(None, [
        story.headline, story.deck, story.takeaway, *story.points]))
    for name, words in KEYWORD_FRAMES:
        if name in taken or not _exists(name):
            continue
        if any(_mentions(text, w) for w in words):
            return name
    name = CATEGORY_FRAMES.get(story.category, '')
    if name and name not in taken and _exists(name):
        return name
    return ''


def photo_for(story: Story, taken: set | None = None) -> Photo | None:
    """A labelled Photo for this story, or None when nothing fits.

    Labelled as the catalogue specifies and as `Story.validate()` requires:
    generated frames wear `nature='ai'`, so the card and the caption both say
    ಎಐ ರಚಿತ ಚಿತ್ರ. Never `representative` — that word is for a real
    photograph of a similar scene, and these are not photographs.
    """
    name = frame_for(story, taken)
    if not name:
        return None
    return Photo(path=os.path.join('assets', 'stock', name), nature='ai',
                 credit=CREDIT, licence='own', caption=CAPTION)


def illustrate(edition: Edition) -> tuple[int, list[str]]:
    """Give every bare story a frame it can defend.

    Returns (how many were filled, headlines left bare). A story left bare is
    not a failure of this function — it is the honest answer when the library
    holds nothing that belongs with it, and the gate will stop the package so
    a person can choose. Stories that already carry a photograph are never
    touched: somebody chose that one.
    """
    filled, bare = 0, []
    taken = {os.path.basename(st.photo.path)
             for st in edition.stories if st.photo is not None}
    for st in edition.stories:
        if st.photo is not None:
            continue
        p = photo_for(st, taken)
        if p is None:
            bare.append(st.headline)
            continue
        st.photo = p
        taken.add(os.path.basename(p.path))
        filled += 1
    return filled, bare
