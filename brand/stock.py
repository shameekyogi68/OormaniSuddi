"""
ಊರ್ಮನಿ ಸುದ್ದಿ — the picture desk, when nobody is at it.
==========================================================
House rule 2026-09-17-03 says every carousel slide carries a photograph, and
the gate enforces it as `IMG-04`. `draft_edition.py` never attaches one — it
copies text and nothing else — so without this module every auto-drafted
morning is held at the gate on four counts before a person has read a word.

This picks a frame from `assets/stock/` — catalogued, evergreen, generated
images the channel owns — by scoring each one against the story's own words
(D85). `python3 -m brand.stock editions/X.json` prints that evidence.

WHAT IT WILL NOT DO
-------------------
Attach a picture it cannot defend. `docs/AI_BRIEF.md` has always said a
loosely related stock image is worse than an honest plate, and that is still
true — a fishing harbour on a school story is a lie told in pictures. So a
story only gets a frame when words in its own copy — scored by where they
sit — map to one. Anything else is left bare for the gate to stop and a person to
answer, which is the same shape as every other judgement call in this system.

The frame is labelled the way `assets/stock/CATALOG.md` specifies and
`Story.validate()` requires: `nature='ai'` because these were generated,
`licence='own'`, and a caption that says ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ — a representative
image — because that is what it is.
"""
from __future__ import annotations

import os
import re

from .content import Photo, Story, Edition
from .tokens import Limits

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOCK_DIR = os.path.join(ROOT, 'assets', 'stock')

# House rule 2026-09-17-05: `Photo.disclosure` already prints ಎಐ ರಚಿತ ಚಿತ್ರ,
# so the credit is the channel and the caption only says what the frame is —
# a representative image, not a picture of this event.
CREDIT = 'ಊರ್ಮನಿ ಸುದ್ದಿ'
CAPTION = 'ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ'

# Kannada (and a few Latin) words that point at ONE frame. Each word names
# the ACTION or OBJECT the frame shows — never a whole category — because
# house rule 2026-09-20-01 is that a picture matches what happened, not what
# kind of story it is. A word that could describe three different scenes
# (ವಿದ್ಯಾರ್ಥಿ, ಸಭೆ, ಸಾವು) is left out on purpose: it matched the wrong frame
# more often than the right one. D85.
KEYWORD_FRAMES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ('ambulance_emergency_response_town.jpg',
     ('ಅಪಘಾತ', 'ಆಂಬ್ಯುಲೆನ್ಸ್', 'ತುರ್ತು ಚಿಕಿತ್ಸೆ', 'ಗಾಯಗೊಂಡ', 'ಗಾಯಾಳು')),
    ('health_hospital_campus_outpatients.jpg',
     ('ಆಸ್ಪತ್ರೆ', 'ಜ್ವರ', 'ಡೆಂಗ್ಯೂ', 'ಮಲೇರಿಯಾ', 'ಚಿಕಿತ್ಸೆ', 'ರೋಗ',
      'ಸಾಂಕ್ರಾಮಿಕ', 'ವೈದ್ಯ', 'ಆರೋಗ್ಯ ಕೇಂದ್ರ')),
    ('coastal_storm_sea_warning.jpg',
     ('ಚಂಡಮಾರುತ', 'ಅಲೆ', 'ಕಡಲ್ಕೊರೆತ', 'ಆರೆಂಜ್ ಅಲರ್ಟ್', 'ರೆಡ್ ಅಲರ್ಟ್',
      'ಸಮುದ್ರ ಪ್ರಕ್ಷುಬ್ಧ')),
    ('crime_scene_police_cordon.jpg',
     ('ಘಟನಾ ಸ್ಥಳ', 'ಮಹಜರು', 'ಶವ', 'ಹಲ್ಲೆ')),
    ('civic_flooded_road_villagers_complaint.jpg',
     ('ಪ್ರವಾಹ', 'ಜಲಾವೃತ', 'ಚರಂಡಿ', 'ನೀರು ನಿಂತ', 'ಕೆಸರು')),
    ('coastal_ghats_monsoon_homestead.jpg',
     ('ಮಳೆ', 'ಮುಂಗಾರು', 'ಹವಾಮಾನ', 'ಯೆಲ್ಲೋ ಅಲರ್ಟ್')),
    ('coastal_fishing_harbour_docks.jpg',
     ('ಮೀನುಗಾರ', 'ಮೀನುಗಾರಿಕೆ', 'ಬಂದರು', 'ದೋಣಿ', 'ಬೋಟ್')),
    ('coastal_shore_net_fishing.jpg',
     ('ಕೈರಂಪಣಿ', 'ರಂಪಣಿ', 'ಬಲೆ ಎಳೆ', 'ಕಡಲತೀರದಲ್ಲಿ ಮೀನುಗಾರಿಕೆ', 'ಸಾಂಪ್ರದಾಯಿಕ ಮೀನುಗಾರ')),
    ('coastal_shipyard_boatbuilding_dock.jpg',
     ('ಹಡಗು', 'ಶಿಪ್‌ಯಾರ್ಡ್', 'ಬಂದರು ಕಾಮಗಾರಿ', 'ಜೆಟ್ಟಿ')),
    ('coastal_beach_tourism_island_boat.jpg',
     ('ಪ್ರವಾಸಿ', 'ಪ್ರವಾಸೋದ್ಯಮ', 'ದ್ವೀಪ', 'ಬೀಚ್', 'ಕಡಲತೀರ')),
    ('coastal_vented_dam_river_water.jpg',
     ('ಅಣೆಕಟ್ಟು', 'ಕಿಂಡಿ', 'ನದಿ', 'ಕುಡಿಯುವ ನೀರು')),
    ('traffic_police_highway_patrol.jpg',
     ('ಸಂಚಾರ ಪೊಲೀಸ್', 'ಹೆಲ್ಮೆಟ್', 'ದಂಡ', 'ತಪಾಸಣೆ', 'ಸಂಚಾರ ನಿಯಮ')),
    ('police_dog_squad_investigation.jpg',
     ('ಕೊಲೆ', 'ಕಳವು', 'ಕಳ್ಳತನ', 'ದರೋಡೆ', 'ನಾಪತ್ತೆ', 'ಶ್ವಾನ ದಳ')),
    # police_cctv_surveillance_monitoring.jpg is NOT offered: a legible "Burglary Case: 142/2023" label — a case record that does not exist. Found by the
    # package-inspector agent, 2026-09-25. Back only after regeneration with no text.
    # coastal_court_complex_judiciary.jpg is NOT offered: a court sign reading "… ನ್ಯಾಯಾಲಯ, ಕುಂದಾಪುರ" — a named town on every court story. Found by the
    # package-inspector agent, 2026-09-25. Back only after regeneration with no text.
    ('forest_dept_timber_seizure_inspection.jpg',
     ('ಅರಣ್ಯ ಇಲಾಖೆ', 'ಮರಗಳ್ಳ', 'ದಿಮ್ಮಿ', 'ಮರ ಸಾಗಾಟ')),
    ('wildlife_leopard_trap_forest_cage.jpg',
     ('ಚಿರತೆ', 'ಹುಲಿ', 'ಕಾಡಾನೆ', 'ಕಾಡುಪ್ರಾಣಿ', 'ಬೋನು')),
    ('student_exam_results_counselling_portal.jpg',
     ('ಫಲಿತಾಂಶ', 'ಸೀಟು', 'ಸೀಟ್', 'ಕೌನ್ಸೆಲಿಂಗ್', 'ಸಿಇಟಿ', 'ಪಿಜಿಸಿಇಟಿ',
      'ನೀಟ್', 'ಪ್ರವೇಶ ಪರೀಕ್ಷೆ', 'ಕೆಇಎ', 'CET', 'PGCET', 'NEET', 'KEA')),
    ('education_scholarship_certificate_ceremony.jpg',
     ('ವಿದ್ಯಾರ್ಥಿವೇತನ', 'ಪ್ರತಿಭಾ ಪುರಸ್ಕಾರ', 'ಪ್ರಮಾಣಪತ್ರ ವಿತರಣೆ', 'ಸನ್ಮಾನ')),
    ('sports_high_school_girls_wrestling.jpg', ('ಕುಸ್ತಿ',)),
    ('sports_karate_championship_gold.jpg', ('ಕರಾಟೆ',)),
    ('coastal_traditional_kambala_race.jpg', ('ಕಂಬಳ', 'ಕೋಣಗಳ ಓಟ')),
    ('rural_weekly_market_farmers_shandy.jpg',
     ('ರೈತ', 'ಕೃಷಿ', 'ಬೆಳೆ', 'ಸಂತೆ', 'ವಾರದ ಸಂತೆ', 'ವಾರದಸಂತೆ', 'ತರಕಾರಿ',
      'ಮಾರುಕಟ್ಟೆ')),
    ('coastal_badagutittu_yakshagana_performance.jpg',
     ('ಯಕ್ಷಗಾನ', 'ಬಯಲಾಟ', 'ಮೇಳ')),
    ('kannada_sahitya_sambhrama_stage.jpg',
     ('ಸಾಹಿತ್ಯ', 'ಕೃತಿ ಬಿಡುಗಡೆ', 'ಲೋಕಾರ್ಪಣೆ', 'ಪುಸ್ತಕ', 'ಕವಿಗೋಷ್ಠಿ')),
    ('political_party_meeting_convention.jpg',
     ('ಪದಗ್ರಹಣ', 'ಸಮಾವೇಶ', 'ಕಾರ್ಯಕಾರಿಣಿ', 'ಕಾರ್ಯಕರ್ತರ ಸಭೆ')),
    ('temple_ganahoma_vedic_ritual.jpg',
     ('ಹೋಮ', 'ಬ್ರಹ್ಮಕಲಶ', 'ಗಣಹೋಮ')),
    ('ganeshotsava_idol_devotional_pooja.jpg',
     ('ಗಣೇಶೋತ್ಸವ', 'ಗಣಪತಿ', 'ಚತುರ್ಥಿ')),
    ('coastal_shiva_temple_linga_darshana.jpg',
     ('ಶಿವ', 'ಶಿವರಾತ್ರಿ', 'ಲಿಂಗ')),
    ('lpg_biometric_ekyc_counter.jpg',
     ('ಇಕೆವೈಸಿ', 'ಇ-ಕೆವೈಸಿ', 'ಕೆವೈಸಿ', 'ಬಯೋಮೆಟ್ರಿಕ್', 'ಬೆರಳಚ್ಚು', 'eKYC', 'KYC')),
    ('composite_lpg_gas_cylinder.jpg',
     ('ಸಿಲಿಂಡರ್', 'ಎಲ್‌ಪಿಜಿ', 'ಅಡುಗೆ ಅನಿಲ', 'LPG')),
    # taluk_revenue_office_files.jpg is NOT offered: its generated signs read
    # "ತಾಲೂಕು ಕಚೇರಿ, ಕುಂದಾಪುರ" and a nameplate names an officer who does not
    # exist ("ಕೆ. ಶಿವರಾಮ್, ಕಂದಾಯ ನಿರೀಕ್ಷಕರು"). Found on the Byndoor reel,
    # 2026-09-24. A fake named official is a defamation risk to every real
    # one; it comes back only after it is regenerated with no text at all.
    ('civic_stray_dogs_street_menace.jpg',
     ('ಬೀದಿನಾಯಿ', 'ನಾಯಿ ಕಡಿತ', 'ರೇಬಿಸ್')),
    ('coastal_event_site_police_inspection.jpg',
     ('ಬಂದೋಬಸ್ತ್', 'ಪೂರ್ವಸಿದ್ಧತೆ', 'ಸ್ಥಳ ಪರಿಶೀಲನೆ')),
    ('coastal_nh66_highway_traffic.jpg',
     ('ಹೆದ್ದಾರಿ', 'ಸೇತುವೆ', 'ಬಸ್', 'ಟ್ರಾಫಿಕ್', 'ವಾಹನ ಸಂಚಾರ')),
)

# Frames that carry AI-made text a reader would take as fact — a town, a
# name, an institution, a registration, a case number — or show something
# that may not have happened. Never attached automatically. Audited frame by
# frame by the systems-steward agent, 2026-09-26 (D91); a frame comes off
# this list only when it is regenerated with no text at all.
WITHDRAWN: dict[str, str] = {
    'ambulance_emergency_response_town.jpg': 'road sign ಬ್ರಹ್ಮಾವರ/ಉಡುಪಿ, named shops, a number plate',
    'civic_stray_dogs_street_menace.jpg': '"Udupi Bakery" and named shops',
    'coastal_airport_runway_flight.jpg': 'a real airline livery',
    'coastal_beach_tourism_island_boat.jpg': 'a boat name on the hull',
    'coastal_court_complex_judiciary.jpg': 'court sign naming ಕುಂದಾಪುರ',
    'coastal_fishing_harbour_docks.jpg': 'boat registration numbers',
    'coastal_nh66_highway_traffic.jpg': 'garbled road signs, a named bus',
    'coastal_shiva_temple_linga_darshana.jpg': 'a garbled inscription on the lintel',
    'crime_scene_police_cordon.jpg': 'police tape text, a number plate',
    'education_scholarship_certificate_ceremony.jpg': 'banner naming a university',
    'forest_dept_timber_seizure_inspection.jpg': 'log numbers, seizure stickers, a plate',
    'health_hospital_campus_outpatients.jpg': 'garbled Kannada sign on the building',
    'kannada_sahitya_sambhrama_stage.jpg': 'a dated event banner and a named portrait',
    'police_cctv_surveillance_monitoring.jpg': '"Burglary Case 142/2023"',
    'police_dog_squad_investigation.jpg': 'police tape text, a number plate',
    'political_party_meeting_convention.jpg': 'a Bengaluru conference banner, a party-like seal',
    'sports_high_school_girls_wrestling.jpg': 'a named championship, school and year',
    'sports_karate_championship_gold.jpg': 'a named tournament, university and winner',
    'taluk_revenue_office_files.jpg': 'ಕುಂದಾಪುರ office sign and a fake officer nameplate',
    'traffic_police_highway_patrol.jpg': 'jeep reads "UDUPI TRAFFIC", a plate',
    'wildlife_leopard_trap_forest_cage.jpg': 'a leopard already in the cage; a warning sign',
}

# Where a word sits says how much it is about. A word in the headline is what
# the story IS; a word in the third bullet may be context ("despite the
# rain…"). A frame has to earn `Limits.stock_match_min` points — a headline
# word on its own, or the same idea in the deck AND the facts.
FIELD_WEIGHT = {'headline': 3, 'reel_line': 3, 'hook': 3,
                'deck': 2, 'points': 1, 'takeaway': 1}


def _exists(name: str) -> bool:
    return os.path.exists(os.path.join(STOCK_DIR, name))


def _mentions(text: str, word: str) -> bool:
    """True when a WORD of `text` is `word` or grows out of it.

    Kannada agglutinates, so a plain `in` test is the natural reach — and it
    is wrong: `ದರ` (price) sits inside `ವಿಚಾರದಲ್ಲಿ` (on the matter of), which
    put a farmers-market photograph on a story about a political row the
    first time this ran. Matching per word, from the start of the word, keeps
    ಮಳೆ → ಮಳೆಯಿಂದ while refusing the accidental middles.

    A two-word key (ರೆಡ್ ಅಲರ್ಟ್) is matched as a phrase that starts at a word
    boundary. Split per word, as this once was, it could never match at all.
    """
    if ' ' in word:
        return re.search(r'(?:^|\s)' + re.escape(word), text) is not None
    return any(w.startswith(word) for w in text.split())


def _fields(story: Story) -> dict[str, str]:
    return {
        'headline': story.headline or '',
        'reel_line': story.reel_line or '',
        'hook': getattr(story, '_hook', '') or '',
        'deck': story.deck or '',
        'points': ' '.join(story.points or []),
        'takeaway': story.takeaway or '',
    }


def candidates(story: Story, taken: set | None = None) -> list[dict]:
    """Every frame with any claim on this story, best first, with the words
    that earned it — the evidence the picture desk reads before it accepts
    one. `eligible` is False below the floor or when already used today."""
    taken = taken or set()
    fields = _fields(story)
    out = []
    for order, (name, words) in enumerate(KEYWORD_FRAMES):
        if not _exists(name) or name in WITHDRAWN:
            continue
        score, hits = 0, []
        for w in words:
            best = max((FIELD_WEIGHT[f] for f, txt in fields.items()
                        if txt and _mentions(txt, w)), default=0)
            if best:
                score += best
                hits.append(w)
        if not score:
            continue
        out.append({'frame': name, 'score': score, 'words': hits,
                    'order': order,
                    'eligible': (score >= Limits.stock_match_min
                                 and name not in taken)})
    out.sort(key=lambda c: (-c['score'], -len(c['words']), c['order']))
    return out


def frame_for(story: Story, taken: set | None = None) -> str:
    """The stock filename this story earns, or '' if none does.

    The BEST-scoring frame wins, not the first one listed: a story about an
    ambulance delayed by a flooded road used to get whichever of the two came
    first in the table. There is no category fallback any more — a category
    is what a story is filed under, not what happened in it, and matching on
    it is the lazy match house rule 2026-09-20-01 forbids. Nothing earned →
    '' → the gate holds the slide and a fresh frame is made for it. D85.

    `taken` is the frames already used elsewhere in the same edition. Two
    slides of one carousel carrying the identical photograph reads as a
    broken render, so a frame is used once and the next candidate is tried.
    """
    for c in candidates(story, taken):
        if c['eligible']:
            return c['frame']
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


def main(argv: list[str] | None = None) -> int:
    """Print, per story, the frames that have a claim on it and why."""
    import sys
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print('usage: python3 -m brand.stock editions/DATE.json')
        return 2
    ed = Edition.load(args[0])
    taken: set = set()
    for i, st in enumerate(ed.stories, 1):
        print(f'\n{i}. {st.headline}')
        if st.photo is not None:
            print(f'   chosen already: {st.photo.path}')
            taken.add(os.path.basename(st.photo.path))
            continue
        cands = candidates(st, taken)
        if not cands:
            print('   no stock frame has a claim — generate a fresh one')
        for c in cands[:4]:
            mark = '✓' if c['eligible'] else '·'
            print(f"   {mark} {c['score']:>2}  {c['frame']}  ← {', '.join(c['words'])}")
        pick = frame_for(st, taken)
        if pick:
            taken.add(pick)
        else:
            print(f'   → below the floor ({Limits.stock_match_min}): '
                  f'generate a fresh frame')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
