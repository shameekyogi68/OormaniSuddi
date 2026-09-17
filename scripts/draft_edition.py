#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — the morning collapsed to a few taps
====================================================
Runs automatically after the fetch. Turns today's tip sheet into a real,
renderable `editions/{date}.json` — every field copied verbatim from what the
tip sheet already has, nothing invented.

WHAT THIS DOES NOT DO, AND WHY
-------------------------------
It does not set `verified_by`. It cannot. That is the one field only a person
can fill in — it is a statement that a human opened the source and checked it,
and a script cannot make that statement on anyone's behalf (D59). The gate
will not write APPROVAL.md without it (`SRC-02`), so a draft this script makes
can never accidentally become a publishable package on its own. That refusal
is the whole safety of running this unattended.

It never writes a sentence. Every `headline`, `deck`, `point` and `takeaway`
is text the tip sheet already carries — the tip's own scraped headline, or the
lead/facts the intake's groundedness pass (D63) already checked against the
source. This script only re-shapes that into the Story schema. It is a
copy-paste with better handwriting, not a writer.

It skips, rather than guesses, anything that would need a judgement call: an
English-only tip (this is a Kannada brand), a story whose own legal validation
fails (a crime headline the copy itself asserts guilt in — Story.validate()
catches it, and the honest response is to leave it for a human to rewrite, not
to silently drop the safety check), an obituary (needs two sources, a single
tip only ever has one).

Defaults toward caution, not toward looking finished: `is_reel` is always
False (a person picks which stories perform, not a heuristic), and a tip
flagged `risk: minor` sets `involves_minor: True` rather than leaving it off —
a false positive costs a vaguer card, a false negative costs an offence.

    python3 scripts/draft_edition.py                 # today's tip sheet
    python3 scripts/draft_edition.py --max 4
    python3 scripts/draft_edition.py --date 2026-09-17
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand.content import Story, Edition, ContentError, OWN_REPORTING, now  # noqa: E402
from brand.qa import preflight  # noqa: E402
from brand.reach import BREADTH, ACTIONABLE  # noqa: E402
from scripts.fetch_daily_news import (_kannada_share, UNCHECKABLE,  # noqa: E402
                                      _shared_urls, link_opens)

INBOX_JSON = os.path.join(ROOT, 'inbox', 'today.json')

# Keyword → category. A floor, like the legal word lists — good enough to sort
# tips into the right bucket most mornings; a human re-categorises the rest in
# the two minutes they already spend confirming the story anyway.
# Checked in order — the first match wins, so put the more specific signal
# (an actual hospital, an actual road) ahead of the vaguer one.
CATEGORY_HINTS = [
    ('weather',   ('ಮಳೆ', 'ಗಾಳಿ', 'ಚಂಡಮಾರುತ', 'ಹವಾಮಾನ', 'ಪ್ರವಾಹ', 'ಎಚ್ಚರಿಕೆ')),
    ('health',    ('ಆಸ್ಪತ್ರೆ', 'ಆರೋಗ್ಯ', 'ಚಿಕಿತ್ಸೆ', 'ಸಾಂಕ್ರಾಮಿಕ', 'ಜ್ವರ',
                   'ಅಪಘಾತ', 'ಮಿದುಳು', 'ಅಂಗಾಂಗ', 'ಗಾಯ')),
    ('education', ('ಶಾಲೆ', 'ಕಾಲೇಜು', 'ಪರೀಕ್ಷೆ', 'ಫಲಿತಾಂಶ', 'ವಿದ್ಯಾರ್ಥಿ')),
    ('culture',   ('ಜಾತ್ರೆ', 'ಉತ್ಸವ', 'ಯಕ್ಷಗಾನ', 'ದೇವಸ್ಥಾನ', 'ಹಬ್ಬ', 'ಕಂಬಳ')),
    ('sport',     ('ಕ್ರೀಡೆ', 'ಪಂದ್ಯ', 'ಟೂರ್ನಿ')),
    ('farm',      ('ರೈತ', 'ಕೃಷಿ', 'ಬೆಳೆ', 'ಬೆಂಬಲ ಬೆಲೆ')),
    ('civic',     ('ರಸ್ತೆ', 'ಚರಂಡಿ', 'ನೀರು', 'ವಿದ್ಯುತ್', 'ಪಂಚಾಯಿತಿ', 'ಕಚೇರಿ',
                   'ಹೆದ್ದಾರಿ', 'ಸೇತುವೆ', 'ಜಿಲ್ಲಾಧಿಕಾರಿ', 'ಸಚಿವ', 'ಶಾಸಕ',
                   'ಸಂಸದ', 'ಸಭೆ', 'ಭೇಟಿ')),
]

# Extra sexual-offence signal beyond the fetch's coarse risk classifier. A
# floor, exactly like content.GUILT_ASSERTING — over-eager on purpose.
SEXUAL_OFFENCE_MARK = ('ಅತ್ಯಾಚಾರ', 'ಲೈಂಗಿಕ ದೌರ್ಜನ್ಯ', 'ಲೈಂಗಿಕ ಕಿರುಕುಳ')

# Which taluk to reach for FIRST when several clean tips are competing for the
# same handful of morning slots. The editor's own ranking of the coverage
# area, not a guess — house rule 2026-09-17-01. This does not add, remove, or
# rename a place (copy.PLACE_TAGS is untouched); it only breaks ties among tips
# that already have one.
TALUK_PRIORITY = {
    'ಕುಂದಾಪುರ': 1.0, 'ಬೈಂದೂರು': 1.0,
    'ಉಡುಪಿ': 0.7, 'ಮಣಿಪಾಲ': 0.7,
    'ಕಾರ್ಕಳ': 0.4, 'ಬ್ರಹ್ಮಾವರ': 0.4, 'ಹೆಬ್ರಿ': 0.4,
    'ಕಾಪು': 0.4, 'ಮಂಗಳೂರು': 0.4,
}


def _category_for(text: str, risk: str) -> str:
    if risk in ('crime', 'minor'):
        return 'crime'
    for cat, words in CATEGORY_HINTS:
        if any(w in text for w in words):
            return cat
    return 'explainer'


def _score(tip: dict) -> float:
    """Same shape as reach.relevance(), adapted to a raw tip dict — reuses
    the SAME breadth and actionable tables reach.py already owns, rather than
    forking a second copy that drifts (D72's own rule, applied here)."""
    text = ' '.join(filter(None, [tip.get('lead_kn') or tip.get('headline', ''),
                                  tip.get('snippet', '')]))
    cat = _category_for(text, tip.get('risk', 'normal'))
    score = BREADTH.get(cat, 0.5) * 0.4
    if tip.get('taluk'):
        # A story from a lower-priority taluk still outranks one with no
        # taluk at all — the floor of 0.4 keeps that true even at the bottom
        # of TALUK_PRIORITY (house rule 2026-09-17-01).
        score += 0.3 * TALUK_PRIORITY.get(tip['taluk'], 0.4)
    if any(w in text for w in ACTIONABLE):
        score += 0.2
    if tip.get('risk') != 'normal':
        score += 0.1
    # Clean leads (nothing flagged, or correctly marked uncheckable) sort
    # ahead of flagged ones — a draft should prefer what needs the LEAST
    # second-guessing, not what happens to score highest.
    flags = tip.get('unsupported') or []
    if flags and flags != [UNCHECKABLE]:
        score -= 0.5
    return score


def _story_dict(tip: dict) -> dict | None:
    """One tip, reshaped into the Story schema. None if it should be skipped."""
    lead = (tip.get('lead_kn') or '').strip() or tip.get('headline', '').strip()
    if _kannada_share(lead) < 0.5:
        return None    # English-only tip; this is a Kannada brand
    url = (tip.get('source_url') or '').strip()
    if not url.startswith('http'):
        return None    # nothing an editor can reopen — the whole point of D55
    if not link_opens(url):
        # An aggregator hop resolves only under JavaScript, so the person who
        # clicks it to confirm this story lands on a home page instead. A
        # story whose source cannot be reopened is exactly what D55 refuses,
        # and verifying it would mean a name attached to an unchecked claim.
        return None
    facts = [f.strip() for f in (tip.get('snippet') or '').split('|')
            if f.strip() and len(f.strip()) < 300][:3]
    text = ' '.join([lead, *facts])
    cat = _category_for(text, tip.get('risk', 'normal'))
    d = {
        'headline': lead,
        'category': cat,
        'deck': ' '.join(facts) if facts else '',
        'points': facts,
        'location': tip.get('taluk', '') or '',
        'sources': [tip.get('source_name', 'ಮೂಲ')],
        'source_urls': [url],
        'status': 'developing',
        'is_reel': False,   # a person picks which stories perform, not a script
    }
    if tip.get('risk') == 'minor':
        d['involves_minor'] = True
    if any(w in text for w in SEXUAL_OFFENCE_MARK):
        d['sexual_offence'] = True
    return d


def build(date_s: str, max_stories: int) -> tuple[list[dict], list[str]]:
    """(stories that validated, notes about what was skipped and why)."""
    if not os.path.exists(INBOX_JSON):
        raise FileNotFoundError(
            f'{INBOX_JSON} does not exist — run scripts/fetch_daily_news.py first')
    with open(INBOX_JSON, encoding='utf-8') as fh:
        payload = json.load(fh)
    raw_tips = payload.get('tips', [])

    # Same check D75 already proved out: a source_url more than one tip
    # resolves to is a listing page, not that tip's article — reused directly
    # rather than forked, via the real Tip objects so the logic cannot drift.
    from scripts.fetch_daily_news import Tip as _Tip
    generic = _shared_urls([_Tip(**t) for t in raw_tips])
    if generic:
        print(f'  {len(generic)} listing-page URL(s) excluded from drafting — '
             f'not specific enough for a person to reopen and confirm '
             f'against (D75).')

    tips = sorted(raw_tips, key=_score, reverse=True)

    stories: list[dict] = []
    notes: list[str] = []
    seen_places: set[str] = set()
    for tip in tips:
        if len(stories) >= max_stories:
            break
        if (tip.get('source_url') or '') in generic:
            continue
        d = _story_dict(tip)
        if d is None:
            continue
        # One story per taluk in the draft, so the morning brief is not four
        # Byndoor stories — the human can always add more by hand.
        if d['location'] and d['location'] in seen_places:
            continue
        try:
            story = Story.from_dict(d).validate()
        except ContentError as e:
            notes.append(f'skipped "{d["headline"][:50]}" — needs a human '
                        f'rewrite, not an auto-draft: {e}')
            continue
        # Legally valid is not the same as renderable. A lead sentence copied
        # verbatim can run to 130+ characters, which is a fine SENTENCE and a
        # broken HEADLINE — render.py's preflight hard-fails it. Shortening it
        # well is writing, which this script does not do; skipping it and
        # saying why is the honest alternative to shipping a draft that fails
        # at 8am instead of at 2am.
        rep = preflight(story, 'post')
        if rep.fail:
            notes.append(f'skipped "{d["headline"][:50]}" — would fail the '
                        f'render as-is ({rep.fail[0]}). The tip is real; the '
                        f'headline needs a person to shorten it.')
            continue
        stories.append(d)
        if d['location']:
            seen_places.add(d['location'])

    if not stories:
        notes.append('nothing in the tip sheet safely auto-drafted. Every '
                     'tip was either English-only, unsourced, or failed a '
                     'legal check on its own headline. Build today by hand '
                     'from inbox/today.md.')
    return stories, notes


def write_checklist(stories: list[dict], notes: list[str], path: str) -> str:
    lines = [
        '# Morning checklist', '',
        'Every story below is copied verbatim from the tip sheet — nothing was',
        'written. Open each source, confirm it is true, then run the verify',
        'command with your own name. Nothing here can be approved or posted',
        'until you do; the gate refuses without it (D59).', '',
    ]
    for i, s in enumerate(stories, 1):
        lines += [
            f'## {i}. {s["headline"]}',
            f'- Category: {s["category"]}' + (' ⚠️ crime — check for guilt '
              'language yourself, the machine only checks the headline'
              if s['category'] == 'crime' else ''),
            f'- Source: {s["sources"][0]} — {s["source_urls"][0]}',
        ]
        if s.get('involves_minor'):
            lines.append('- ⚠️ flagged: may involve a minor — verify names/ages are absent')
        if s.get('sexual_offence'):
            lines.append('- ⚠️ flagged: may involve a sexual offence — verify location is not granular')
        for p in s.get('points', []):
            lines.append(f'  • {p}')
        lines += [
            '',
            f'  ✅ Once confirmed:',
            f'  `python3 scripts/verify.py {{EDITION}} --story {i} --by "Your Name"`',
            '',
        ]
    if notes:
        lines += ['## Not auto-drafted', ''] + [f'- {n}' for n in notes] + ['']
    lines += [
        '## Once every story above is verified',
        '',
        '```bash',
        'python3 render.py {EDITION} --minimal --out out/{DATE}',
        'python3 scripts/sign_off.py out/{DATE} --by "Your Name"',
        '```',
        '',
        'Then post from `MASTER_COPY.md` and the per-town forwards in `out/{DATE}/`.',
        '',
    ]
    body = '\n'.join(lines)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(body)
    return body


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--date', default=datetime.now().strftime('%Y-%m-%d'))
    ap.add_argument('--max', type=int, default=4,
                    help='at most this many stories (D69: three or four is a day)')
    ap.add_argument('--force', action='store_true',
                    help='overwrite an existing editions/{date}.json')
    args = ap.parse_args()

    out_path = os.path.join(ROOT, 'editions', f'{args.date}.json')
    if os.path.exists(out_path) and not args.force:
        print(f'! {out_path} already exists — not overwriting. '
              f'Pass --force to replace it, or edit it by hand.')
        return 1

    try:
        stories, notes = build(args.date, args.max)
    except FileNotFoundError as e:
        print(f'✗ {e}', file=sys.stderr)
        return 1

    if not stories:
        print('✗ nothing safely auto-drafted:')
        for n in notes:
            print(f'  - {n}')
        return 1

    edition = {
        'date': f'{args.date}T08:00:00+05:30',
        'edition_no': 1,
        'stories': stories,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as fh:
        json.dump(edition, fh, indent=2, ensure_ascii=False)
        fh.write('\n')

    # Confirm it actually loads and validates as a whole edition, not just
    # story by story — a belt-and-braces check before anyone reads the file.
    try:
        Edition.load(out_path)
    except ContentError as e:
        print(f'✗ the drafted edition does not validate as a whole: {e}',
              file=sys.stderr)
        return 1

    checklist = os.path.join(ROOT, 'inbox', f'checklist_{args.date}.md')
    write_checklist(stories, notes,
                    checklist.replace('{EDITION}', 'x').replace('{DATE}', 'x'))
    # Fill the real paths in now that the file exists.
    with open(checklist, encoding='utf-8') as fh:
        body = fh.read()
    body = body.replace('{EDITION}', f'editions/{args.date}.json').replace(
        '{DATE}', args.date)
    with open(checklist, 'w', encoding='utf-8') as fh:
        fh.write(body)

    print(f'✓ {len(stories)} stories drafted → {os.path.relpath(out_path, ROOT)}')
    print(f'✓ checklist → {os.path.relpath(checklist, ROOT)}')
    print(f'  Every field is copied from the tip sheet. verified_by is empty '
          f'on all {len(stories)} — nothing here can be approved until a '
          f'person fills it in.')
    if notes:
        print(f'  {len(notes)} tip(s) not drafted — see the checklist.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
