#!/usr/bin/env python3
"""Generate schemas/*.json FROM the code, so they cannot drift out of sync.

Run after changing CATEGORIES, IMAGE_NATURE, STATUS or the Story fields:

    python3 schemas/_build.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from brand.content import (CATEGORIES_KEYS, IMAGE_NATURE, STATUS,
                           BREAKING_WINDOW_H, LICENCES)
from templates import TEMPLATES

HERE = os.path.dirname(os.path.abspath(__file__))

PHOTO = {
    'type': 'object',
    'description': 'A photograph and its provenance. Both are required — the '
                   'system will not render an uncredited picture.',
    'required': ['path', 'nature', 'credit', 'licence'],
    'additionalProperties': False,
    'properties': {
        'path': {'type': 'string',
                 'description': 'Path to the image file, relative to the project root.'},
        'nature': {'enum': sorted(IMAGE_NATURE),
                   'description': 'What this picture actually is. Use "actual" ONLY '
                                  'if it shows the scene being reported. Anything '
                                  'else is labelled on the card and cannot be hidden.'},
        'credit': {'type': 'string', 'minLength': 1,
                   'description': 'Photographer, agency, or "ಊರ್ಮನಿ ಸುದ್ದಿ ವರದಿಗಾರರಿಂದ" '
                                  'for own reporting.'},
        'licence': {'enum': sorted(LICENCES),
                    'description': 'Your right to publish it. "own" means the '
                                   'channel shot it. Crediting a picture is not '
                                   'the same as having the right to publish it.'},
        'source_url': {'type': 'string',
                       'description': 'Where it came from. Required unless '
                                      'licence is "own".'},
        'caption': {'type': 'string',
                    'description': 'What the picture shows. REQUIRED when nature is '
                                   '"actual".'},
        'focal': {'type': 'array', 'items': {'type': 'number', 'minimum': 0, 'maximum': 1},
                  'minItems': 2, 'maxItems': 2,
                  'description': 'Crop focal point [x, y] in 0..1. Default [0.5, 0.42] '
                                 '— above centre, because a centre crop decapitates people.'},
        'taken_at': {'type': 'string', 'format': 'date-time'},
    },
}

STORY = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    '$id': 'https://oormanisuddi.local/schemas/story.schema.json',
    'title': 'Story',
    'description': 'One news story. Every field that exists to keep the card '
                   'honest is required, not optional.',
    'type': 'object',
    'required': ['headline', 'sources'],
    'additionalProperties': False,
    'properties': {
        'headline': {'type': 'string', 'minLength': 1, 'maxLength': 140,
                     'description': 'The headline in Kannada. Budget is about 78 '
                                    'characters for a 4:5 card; longer sets smaller.'},
        'category': {'enum': CATEGORIES_KEYS, 'default': 'explainer',
                     'description': 'Drives the category rail colour and the Kannada '
                                    'kicker. "breaking" is auto-demoted if the story '
                                    f'is older than {BREAKING_WINDOW_H} hours.'},
        'deck': {'type': 'string', 'maxLength': 220,
                 'description': 'Standfirst — one or two sentences under the headline. '
                                'Past ~180 characters it stops being a standfirst.'},
        'points': {'type': 'array', 'items': {'type': 'string', 'maxLength': 180},
                   'maxItems': 5,
                   'description': 'Supporting facts. A 4:5 card carries three '
                                  'comfortably; extras are dropped from the bottom.'},
        'photo': PHOTO,
        'location': {'type': 'string',
                     'description': 'Place name in Kannada. Coastal readers scan for '
                                    'this first.'},
        'dateline': {'type': 'string', 'description': 'Bureau, e.g. "ಬ್ರಹ್ಮಾವರ ವರದಿ".'},
        'reporter': {'type': 'string'},
        'sources': {'type': 'array', 'items': {'type': 'string', 'minLength': 1},
                    'minItems': 1,
                    'description': 'Who told you. Own reporting counts, but you have '
                                   'to say so: ["ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ"].'},
        'status': {'enum': sorted(STATUS), 'default': 'developing',
                   'description': 'Verification state. Printed on the card as it '
                                  'stands — a card that admits it is still being '
                                  'checked is worth more than one that pretends.'},
        'published_at': {'type': 'string', 'format': 'date-time',
                         'description': 'ISO-8601 with offset, e.g. '
                                        '"2026-08-25T09:40:00+05:30". Drives the '
                                        'dateline AND the breaking calculation.'},
        'live_url': {'type': 'string',
                     'description': 'A real stream URL. Only this earns a ನೇರ ಪ್ರಸಾರ badge.'},
        'takeaway': {'type': 'string', 'maxLength': 200,
                     'description': 'What the reader should DO — a helpline, a deadline. '
                                    'On weather/health/civic alerts this outranks the facts.'},
        'numbers': {'type': 'array', 'maxItems': 4,
                    'items': {'type': 'array', 'items': {'type': 'string'},
                              'minItems': 2, 'maxItems': 2},
                    'description': 'Pairs of [value, Kannada label] for stat_card.'},
        'quote': {'type': 'array', 'items': {'type': 'string'},
                  'minItems': 2, 'maxItems': 2,
                  'description': '[text, attribution] for quote_card.'},
        'involves_minor': {'type': 'boolean', 'default': False,
                           'description': 'Set when a child is involved as accused '
                                          'or victim. Blocks identifying detail — '
                                          'JJ Act 2015 §74.'},
        'sexual_offence': {'type': 'boolean', 'default': False,
                           'description': 'Set for any sexual offence. Blocks '
                                          'identifying detail — POCSO §23, BNS §72.'},
        'convicted': {'type': 'boolean', 'default': False,
                      'description': 'Set ONLY when a court has convicted. Until '
                                     'then the copy must read as an allegation.'},
        'correction': {'type': 'string',
                       'description': 'If this card corrects an earlier one, say what changed.'},
        'template': {'enum': sorted(TEMPLATES), 
                     'description': 'Force a template. Omit to let choose() pick.'},
        'reel_line': {'type': 'string', 'maxLength': 60,
                      'description': 'A SHORT headline for the reel — about 45 '
                                     'characters. A print headline of 75 needs '
                                     '~11 seconds on screen to be readable, which '
                                     'is most of a scene. Without this the reel '
                                     'still works, it just runs long.'},
        'hook': {'type': 'string', 'maxLength': 40,
                 'description': 'Short line for the YouTube thumbnail. About seven '
                                'words maximum — it is read at 210 px wide. Put it on '
                                'the FIRST story; that is the one thumbnailed.'},
        'is_reel': {'type': 'boolean', 'default': True,
                    'description': 'Whether this story qualifies as a 10/10 story for '
                                   'an individual vertical reel. High-impact, visual, '
                                   'or breaking stories should set true; routine or '
                                   'bureaucratic updates set false.'},
    },
}

EDITION = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    '$id': 'https://oormanisuddi.local/schemas/edition.schema.json',
    'title': 'Edition',
    'description': "One day's bulletin. Everything — posts, carousel, story, "
                   'thumbnail, broadsheet and reel — is rendered from this single '
                   'object, so the outputs cannot drift apart.',
    'type': 'object',
    'required': ['stories'],
    'additionalProperties': False,
    'properties': {
        'stories': {'type': 'array', 'minItems': 1, 'maxItems': 6,
                    'items': {'$ref': 'story.schema.json'},
                    'description': 'Lead story first. Three to four read best in a reel.'},
        'date': {'type': 'string', 'format': 'date-time'},
        'edition_no': {'type': 'integer', 'minimum': 1},
        'strapline': {'type': 'string', 'default': 'ಕರಾವಳಿ ಬುಲೆಟಿನ್'},
    },
}


def main():
    for name, doc in (('story', STORY), ('edition', EDITION)):
        p = os.path.join(HERE, f'{name}.schema.json')
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
            f.write('\n')
        print('wrote', os.path.relpath(p, os.path.dirname(HERE)))


if __name__ == '__main__':
    main()
