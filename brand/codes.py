"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Error codes
===========================
Every check the Chief Editor's gate runs emits one of these. Three things fall
out of having them, none of which is possible with prose alone:

  * `review_report.json` can be read by something other than a human — a
    notifier, a dashboard, a script that reopens the right step.
  * A board discussion can name a fault instead of describing it.
  * `docs/TRACEABILITY.md` can map a decision number to the code that enforces
    it, and show which decisions are enforced by nothing at all.

The prefix says who owns the fix:

    LAW   legal / statutory        → the sub-editor rewrites copy
    SRC   sourcing & verification  → the desk reopens the source
    IMG   pictures & disclosure    → the picture desk
    TYPE  typography & glyphs      → copy, or the type engine
    SND   audio & narration        → the voice pass
    VID   video & timing           → the motion engine
    PKG   package completeness     → re-render
    PUB   publishing & platform    → the schedule
    OPS   channel-level compliance → the publisher
"""
from __future__ import annotations

CODES: dict[str, str] = {
    # ── LAW ───────────────────────────────────────────────────────────────
    'LAW-01': 'crime copy asserts guilt with no allegation marker (BNS §356)',
    'LAW-02': 'a minor could be identified (JJ Act 2015 §74)',
    'LAW-03': 'a sexual-offence victim could be identified (POCSO §23 / BNS §72)',
    'LAW-04': 'an obituary rests on a single source',
    'LAW-05': 'synthetic imagery is not disclosed in the caption (IT Rules 2021)',
    # ── SRC ───────────────────────────────────────────────────────────────
    'SRC-01': 'a sourced story carries no source_url',
    'SRC-02': 'no named person has verified this story (D59)',
    'SRC-03': 'an unknown category was used',
    # ── IMG ───────────────────────────────────────────────────────────────
    'IMG-01': 'an image would appear on screen with no disclosure line',
    'IMG-02': 'a generated image is not wearing nature="ai" (D57)',
    'IMG-03': 'a reel has fewer gallery frames than facts, so a picture repeats',
    'IMG-04': 'a carousel slide carries no photograph (house rule 2026-09-17-03)',
    # ── TYPE ──────────────────────────────────────────────────────────────
    'TYPE-01': 'a character no house font can set would render as an empty box',
    'TYPE-02': 'a colour pair falls below the contrast floor',
    'TYPE-03': 'the line that sells the post is illegible at feed size',
    # ── SND ───────────────────────────────────────────────────────────────
    'SND-01': 'a reel has no audio track and would post silent',
    'SND-02': 'narration synthesis failed and the reel fell back to silence',
    'SND-03': 'a narration beat contains a TTS hazard (D50)',
    'SND-04': 'a pause inside the speech is longer than a designed beat gap',
    'SND-05': 'a narration beat is over the character budget',
    'SND-06': 'the spoken track does not match the script it was given',
    'SND-07': 'a reel is mastered more than 1.5 LU off the house loudness',
    # ── VID ───────────────────────────────────────────────────────────────
    'VID-01': 'a reel is outside the house duration window (D56)',
    'VID-02': 'a reel would be refused or cropped by the platform',
    'VID-03': 'a reel is too short to be watched',
    'VID-04': 'a video peaks above the true-peak ceiling',
    # ── PKG ───────────────────────────────────────────────────────────────
    'PKG-01': 'the copy points at a file that was not rendered',
    'PKG-02': 'the folder contains nothing publishable',
    'PKG-03': 'a reel has no cover frame',
    'PKG-04': 'a file is heavy for its channel',
    'PKG-05': 'a music bed is not in the licence register',
    # ── PUB ───────────────────────────────────────────────────────────────
    'PUB-01': 'the handle is miscapitalised',
    'PUB-02': 'the schedule routes an AI reel to YouTube (Rule 7)',
    'PUB-03': 'two posts are close enough to compete with each other',
    'PUB-04': 'the edition is drifting toward being a crime channel',
    'PUB-05': 'the town name sits past the caption fold, where nobody sees it',
    'PUB-06': 'a story is marked as a reel that reads better as a card',
    'PUB-07': 'more reels than the day targets, splitting the same audience',
    'PUB-08': 'a story names no place, so nobody can tell it is about their town',
    # ── OPS ───────────────────────────────────────────────────────────────
    'OPS-01': 'no Grievance Officer is named (IT Rules 2021 Part III)',
    'OPS-02': 'no contact route is published anywhere',
    'OPS-03': 'no human has signed off on taste, culture and news judgement',
}


def describe(code: str) -> str:
    return CODES.get(code, 'unregistered code')


def valid(code: str) -> bool:
    return code in CODES


def prefix(code: str) -> str:
    return code.split('-', 1)[0]


# Which step of the newsroom a failure routes back to. The point of a code is
# that the loop-back does not depend on a human remembering who owns what.
OWNER = {
    'LAW': 'sub-editor — rewrite the copy',
    'SRC': 'desk — reopen the source and confirm',
    'IMG': 'picture desk — stock, then generate, then plate',
    'TYPE': 'copy, or brand/typo.py if the face is the problem',
    'SND': 'voice pass — re-run narration',
    'VID': 'motion engine — re-cut',
    'PKG': 're-render the package',
    'PUB': 'schedule and captions',
    'OPS': 'publisher — channel-level, not per edition',
}


def owner(code: str) -> str:
    return OWNER.get(prefix(code), 'unassigned')
