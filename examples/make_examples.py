#!/usr/bin/env python3
"""Reference set — one of every template, from one day's stories.

Read this file as the worked example of how to feed the system: the shape of a
Story, how photographs are declared honestly, and which template suits which
kind of news.
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brand.content import Story, Photo, Edition, IST
import templates as TP

NOW = datetime(2026, 8, 25, 9, 40, tzinfo=IST)
OUT = 'out/reference'

# ── 1 · crime, with a picture that is NOT of the actual scene ───────────────
crime = Story(
    # Allegation framing, in the headline itself. The headline travels alone —
    # a thumbnail, a forward, a screenshot — so it must carry its own ಆರೋಪ
    # rather than lean on the ಆರೋಪಿ in the deck below it.
    headline='ಬ್ರಹ್ಮಾವರ: ಹೆತ್ತವರ ಕೊಲೆ ಆರೋಪ, ಪುತ್ರ ಬಂಧನ',
    category='crime',
    deck='ಗಾಂಧಿನಗರದ ಮನೆಯಲ್ಲಿ ನಡೆದ ಘಟನೆ; ದಂಪತಿ ಸ್ಥಳದಲ್ಲೇ ಸಾವು. ಆರೋಪಿ ಪುತ್ರನನ್ನು ಕೆಲವೇ ಗಂಟೆಗಳಲ್ಲಿ ವಶಕ್ಕೆ ಪಡೆದ ಪೊಲೀಸರು.',
    points=[
        'ಮೃತರು: ಮೆಹಬೂಬ್ ಅಲಿ (62) ಹಾಗೂ ಪತ್ನಿ ಸಂಶದ್ ಬೇಗಂ (56), ಗಾಂಧಿನಗರ ನಿವಾಸಿಗಳು.',
        'ಕೌಟುಂಬಿಕ ವಿವಾದದ ವೇಳೆ ಮಾತಿನ ಚಕಮಕಿ ತೀವ್ರಗೊಂಡು ಹಲ್ಲೆ ನಡೆದಿದೆ ಎಂದು ಪ್ರಾಥಮಿಕ ತನಿಖೆ ತಿಳಿಸಿದೆ.',
        'ಆರೋಪಿ ಪುತ್ರನನ್ನು ಬ್ರಹ್ಮಾವರ ಠಾಣಾ ಪೊಲೀಸರು ಬಂಧಿಸಿದ್ದು, ಕೊಲೆ ಪ್ರಕರಣ ದಾಖಲಾಗಿದೆ.',
    ],
    photo=Photo('assets/brahmavara_crime_scene.jpg', nature='representative',
                credit='ಊರ್ಮನಿ ಸುದ್ದಿ ಸಂಗ್ರಹ', licence='own', focal=(0.5, 0.46)),
    location='ಬ್ರಹ್ಮಾವರ', dateline='ಬ್ರಹ್ಮಾವರ ವರದಿ',
    sources=['ಬ್ರಹ್ಮಾವರ ಠಾಣೆ', 'ಉಡುಪಿ ಜಿಲ್ಲಾ ಪೊಲೀಸ್'],
    status='confirmed', published_at=NOW - timedelta(hours=2),
)

# ── 2 · weather, with an advisory the reader can act on ────────────────────
weather = Story(
    headline='ಕರಾವಳಿಗೆ ಆರೆಂಜ್ ಅಲರ್ಟ್: ಇಂದು ಮತ್ತು ನಾಳೆ ಭಾರಿ ಮಳೆ, ಬಿರುಗಾಳಿ ಸಾಧ್ಯತೆ',
    category='weather',
    deck='ಉಡುಪಿ ಮತ್ತು ದಕ್ಷಿಣ ಕನ್ನಡ ಜಿಲ್ಲೆಗಳಿಗೆ ಹವಾಮಾನ ಇಲಾಖೆಯಿಂದ ಎಚ್ಚರಿಕೆ ಪ್ರಕಟ.',
    points=[
        'ಗಂಟೆಗೆ 40-50 ಕಿ.ಮೀ ವೇಗದ ಗಾಳಿ ಬೀಸುವ ಸಾಧ್ಯತೆ ಇದೆ ಎಂದು ಇಲಾಖೆ ತಿಳಿಸಿದೆ.',
        'ಮೀನುಗಾರರು ಆಗಸ್ಟ್ 27ರವರೆಗೆ ಸಮುದ್ರಕ್ಕೆ ಇಳಿಯದಂತೆ ಸೂಚನೆ ನೀಡಲಾಗಿದೆ.',
        'ತಗ್ಗು ಪ್ರದೇಶಗಳಲ್ಲಿ ನೀರು ನಿಲ್ಲುವ ಸಾಧ್ಯತೆ; ಜಿಲ್ಲಾಡಳಿತ ನಿಗಾ ಇರಿಸಿದೆ.',
    ],
    takeaway='ತುರ್ತು ಸಹಾಯಕ್ಕೆ ಜಿಲ್ಲಾ ವಿಪತ್ತು ನಿರ್ವಹಣಾ ಕೊಠಡಿ 1077 ಸಂಪರ್ಕಿಸಿ.',
    photo=Photo('assets/udupi_coastal_storm.jpg', nature='representative',
                credit='ಊರ್ಮನಿ ಸುದ್ದಿ ಸಂಗ್ರಹ', licence='own', focal=(0.5, 0.5)),
    location='ಉಡುಪಿ ಜಿಲ್ಲೆ', dateline='ಜಿಲ್ಲಾ ವರದಿ',
    sources=['ಭಾರತೀಯ ಹವಾಮಾನ ಇಲಾಖೆ', 'ಉಡುಪಿ ಜಿಲ್ಲಾಡಳಿತ'],
    status='official', published_at=NOW - timedelta(hours=1),
)

# ── 3 · a government order — no photograph, because none would be honest ───
order = Story(
    headline='ಈದ್ ಮಿಲಾದ್ ರಜೆ ಆಗಸ್ಟ್ 25ಕ್ಕೆ ಮರುನಿಗದಿ',
    category='civic',
    deck='ಜಿಲ್ಲಾಧಿಕಾರಿಗಳ ಪ್ರಸ್ತಾವನೆಯಂತೆ ಸರ್ಕಾರದಿಂದ ಆದೇಶ ಹೊರಡಿಸಲಾಗಿದೆ.',
    points=[
        'ಉಡುಪಿ ಜಿಲ್ಲೆಯ ಎಲ್ಲಾ ಸರ್ಕಾರಿ ಕಚೇರಿಗಳಿಗೆ ಆಗಸ್ಟ್ 25ರಂದು ಸಾರ್ವತ್ರಿಕ ರಜೆ ಅನ್ವಯ.',
        'ಶಾಲಾ-ಕಾಲೇಜುಗಳಿಗೂ ಇದೇ ದಿನಾಂಕದಂದು ರಜೆ ಘೋಷಿಸಲಾಗಿದೆ.',
        'ಅಗತ್ಯ ಸೇವೆಗಳು ಹಾಗೂ ಆಸ್ಪತ್ರೆಗಳಿಗೆ ಈ ಆದೇಶ ಅನ್ವಯಿಸುವುದಿಲ್ಲ.',
    ],
    location='ಉಡುಪಿ ಜಿಲ್ಲೆ', dateline='ಜಿಲ್ಲಾಡಳಿತ ವರದಿ',
    sources=['ಉಡುಪಿ ಜಿಲ್ಲಾಧಿಕಾರಿ ಕಚೇರಿ ಪ್ರಕಟಣೆ'],
    status='official', published_at=NOW - timedelta(hours=5),
)

# ── 4 · numbers ────────────────────────────────────────────────────────────
numbers = Story(
    headline='ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ ಈ ಮುಂಗಾರಿನ ಮಳೆ ಲೆಕ್ಕ',
    category='weather',
    deck='ಜೂನ್ 1ರಿಂದ ಆಗಸ್ಟ್ 24ರವರೆಗಿನ ಅಧಿಕೃತ ಅಂಕಿ-ಅಂಶಗಳು.',
    numbers=[('3,412', 'ಮಿ.ಮೀ ಒಟ್ಟು ಮಳೆ'), ('+18%', 'ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಹೆಚ್ಚು'),
             ('7', 'ಜಿಲ್ಲೆಯ ತಾಲ್ಲೂಕುಗಳು')],
    location='ಉಡುಪಿ ಜಿಲ್ಲೆ',
    sources=['ಕರ್ನಾಟಕ ರಾಜ್ಯ ನೈಸರ್ಗಿಕ ವಿಕೋಪ ಉಸ್ತುವಾರಿ ಕೇಂದ್ರ'],
    status='official', published_at=NOW - timedelta(hours=6),
)

# ── 5 · a quote ────────────────────────────────────────────────────────────
quote = Story(
    headline='ಮೀನುಗಾರರ ಸುರಕ್ಷತೆಗೆ ಆದ್ಯತೆ',
    category='civic',
    quote=('ಹವಾಮಾನ ಎಚ್ಚರಿಕೆ ಇರುವವರೆಗೆ ಯಾರೂ ಸಮುದ್ರಕ್ಕೆ ಇಳಿಯಬಾರದು. '
           'ಜಿಲ್ಲಾಡಳಿತ ಎಲ್ಲಾ ಬಂದರುಗಳಲ್ಲಿ ನಿಗಾ ಇರಿಸಿದೆ.',
           'ಉಡುಪಿ ಜಿಲ್ಲಾಧಿಕಾರಿ'),
    photo=Photo('assets/udupi_coastal_storm.jpg', nature='representative',
                credit='ಊರ್ಮನಿ ಸುದ್ದಿ ಸಂಗ್ರಹ', licence='own', focal=(0.5, 0.45)),
    location='ಉಡುಪಿ',
    sources=['ಜಿಲ್ಲಾಡಳಿತ ಪತ್ರಿಕಾಗೋಷ್ಠಿ'],
    status='confirmed', published_at=NOW - timedelta(hours=4),
)

# ── 6 · health ─────────────────────────────────────────────────────────────
health = Story(
    headline='ಕಸ್ತೂರ್ಬಾ ಆಸ್ಪತ್ರೆ ಆರೋಗ್ಯ ಕಾರ್ಡ್ ನೋಂದಣಿಗೆ ಆಗಸ್ಟ್ 31 ಕೊನೆ ದಿನ',
    category='health',
    deck='ಚಿಕಿತ್ಸೆ ಮತ್ತು ತಪಾಸಣೆಯಲ್ಲಿ ರಿಯಾಯಿತಿ ಪಡೆಯಲು ನೋಂದಣಿ ಅಗತ್ಯ.',
    points=[
        'ಮಣಿಪಾಲ ಕಸ್ತೂರ್ಬಾ ಆಸ್ಪತ್ರೆಯಲ್ಲಿ ನೇರವಾಗಿ ಅಥವಾ ಆನ್‌ಲೈನ್‌ನಲ್ಲಿ ನೋಂದಣಿ ಮಾಡಬಹುದು.',
        'ಆಧಾರ್ ಕಾರ್ಡ್ ಮತ್ತು ವಿಳಾಸ ದೃಢೀಕರಣ ದಾಖಲೆ ಕಡ್ಡಾಯ.',
    ],
    photo=Photo('assets/manipal_kmc_hospital.jpg', nature='representative',
                credit='ಊರ್ಮನಿ ಸುದ್ದಿ ಸಂಗ್ರಹ', licence='own', focal=(0.5, 0.44)),
    location='ಮಣಿಪಾಲ', dateline='ಆರೋಗ್ಯ ವರದಿ',
    sources=['ಕಸ್ತೂರ್ಬಾ ಆಸ್ಪತ್ರೆ ಪ್ರಕಟಣೆ'],
    status='official', published_at=NOW - timedelta(hours=7),
)

edition = Edition(stories=[weather, crime, order, health], date=NOW,
                  edition_no=112, strapline='ಕರಾವಳಿ ಬುಲೆಟಿನ್')


def main():
    os.makedirs(OUT, exist_ok=True)
    made = []
    made.append(TP.render('report_card',   crime,   f'{OUT}/01_report_crime.jpg'))
    made.append(TP.render('report_card',   weather, f'{OUT}/02_report_weather.jpg'))
    made.append(TP.render('text_card',     order,   f'{OUT}/03_textcard_order.jpg'))
    made.append(TP.render('stat_card',     numbers, f'{OUT}/04_statcard_rainfall.jpg'))
    made.append(TP.render('quote_card',    quote,   f'{OUT}/05_quotecard.jpg'))
    made.append(TP.render('story_card',    weather, f'{OUT}/06_story_9x16.jpg'))
    made.append(TP.render('youtube_thumb', crime,   f'{OUT}/07_yt_thumb.jpg',
                          hook='ಬ್ರಹ್ಮಾವರ ದುರಂತ: ಪುತ್ರ ಬಂಧನ'))
    made.append(TP.render('broadsheet',    edition, f'{OUT}/08_broadsheet.jpg'))
    made += TP.render('carousel', edition, OUT, prefix='09_carousel')
    for p in made:
        print('  ✓', p)
    print(f'\n{len(made)} files → {OUT}')


if __name__ == '__main__':
    main()
