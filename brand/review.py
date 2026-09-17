"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Chief Editor's desk
====================================
The last gate before anything is handed to a human to publish.

WHY THIS IS CODE AND NOT A CHECKLIST
------------------------------------
The newsroom skill already asks a Chief Editor to "watch the full reel start
to finish" and "read every caption word". Written as prose, that instruction
is unenforceable: a reviewer — human or model — can write ✅ against it having
looked at nothing, and the failure is invisible precisely because the whole
point of the role is that nobody downstream checks the work again.

That is the same failure this project refuses everywhere else. `Story.validate`
does not ask an editor to remember the law; `preflight` does not ask them to
count characters; `audit_sync` does not ask them to trust that the cuts landed.
So the Chief Editor does not get to *assert* that a package is sound either.

`review()` establishes the facts a machine can establish — the handle is right,
every file exists, every reel carries audio of the right length, every
synthetic image is disclosed, no glyph is missing, every crime line qualifies
itself — and `evidence()` extracts the frames and copy that a judgement about
craft has to be made *against*. A green signal requires both: the checks clean,
and the evidence actually produced.

The output is `APPROVAL.md`. Its absence is meaningful: if it is not in the
folder, the package has not been cleared, whatever anyone says about it.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field

from .content import Edition, Story
from .tokens import Brand, fmt, Limits
from . import typo


# What each platform will actually accept, and what it does to what it accepts.
REEL_MAX_SECONDS = Limits.reel_platform_cap
SHORT_MAX_SECONDS = 180.0      # YouTube Shorts
REEL_MIN_SECONDS = Limits.reel_min_seconds
REEL_FAIL_SECONDS = Limits.reel_fail_seconds
REEL_WARN_SECONDS = Limits.reel_warn_seconds
REEL_TARGET_MAX = Limits.reel_target_max
UPLOAD_CEILING_MB = 300.0

# A crime line must qualify itself wherever it can travel alone.
ALLEGATION = ('ಆರೋಪ', 'ಆರೋಪಿ', 'ಶಂಕಿತ', 'ಪ್ರಕರಣ ದಾಖಲು', 'ತನಿಖೆ',
              'ಆರೋಪಿಸಿ', 'ದೂರು')


@dataclass
class Finding:
    """One fault, with the code that names it and the step that owns it.

    A prose finding can only be read by a person, which means a notifier
    cannot react to it, a dashboard cannot count it, and a loop-back depends on
    somebody remembering who fixes what. The code fixes all three.
    """
    code: str
    message: str
    severity: str = 'fail'      # fail | warn
    where: str = ''             # file, or "story 3"

    def to_dict(self) -> dict:
        from . import codes as _codes
        return {'code': self.code, 'severity': self.severity,
                'means': _codes.describe(self.code),
                'owner': _codes.owner(self.code),
                'where': self.where, 'message': self.message}


@dataclass
class ReviewReport:
    checked: list[str] = field(default_factory=list)
    warn: list[str] = field(default_factory=list)
    fail: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    # `fail` and `warn` stay real lists of strings so every existing caller and
    # test keeps working. `add_fail` / `add_warn` write to both, which is what
    # makes review_report.json possible without a second pass over prose.
    def add_fail(self, code: str, message: str, where: str = '') -> None:
        self.fail.append(message)
        self.findings.append(Finding(code, message, 'fail', where))

    def add_warn(self, code: str, message: str, where: str = '') -> None:
        self.warn.append(message)
        self.findings.append(Finding(code, message, 'warn', where))

    @property
    def clean(self) -> bool:
        return not self.fail

    def to_dict(self) -> dict:
        from .content import now
        return {
            'kind': 'chief_editor_review',
            'at': now().isoformat(),
            'clean': self.clean,
            'checks': len(self.checked),
            'checked': list(self.checked),
            'findings': [f.to_dict() for f in self.findings],
            'evidence': list(self.evidence),
        }

    def show(self) -> 'ReviewReport':
        from . import codes as _codes
        print(f'\n  CHIEF EDITOR — {len(self.checked)} checks')
        coded = {f.message: f.code for f in self.findings}
        for m in self.fail:
            c = coded.get(m)
            print(f'    ✗ {("[" + c + "] ") if c else ""}{m}')
            if c:
                print(f'        → {_codes.owner(c)}')
        for m in self.warn:
            c = coded.get(m)
            print(f'    ! {("[" + c + "] ") if c else ""}{m}')
        if self.clean and not self.warn:
            print('    ✓ every mechanical check clean')
        elif self.clean:
            print('    ✓ no blocking faults')
        return self


def _probe(path: str, stream: str = 'format=duration') -> str:
    try:
        sel = ['-select_streams', 'a:0'] if stream.startswith('stream') and 'a' in stream else []
        return subprocess.run(
            ['ffprobe', '-v', 'error', *sel, '-show_entries', stream,
             '-of', 'csv=p=0', path],
            capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return ''


def _duration(path: str) -> float:
    try:
        return float(_probe(path).split(',')[0])
    except Exception:
        return 0.0


def _has_audio(path: str) -> bool:
    out = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries',
         'stream=codec_type', '-of', 'csv=p=0', path],
        capture_output=True, text=True).stdout
    return 'audio' in out


def _peak_dbfs(path: str) -> float | None:
    try:
        out = subprocess.run(
            ['ffmpeg', '-hide_banner', '-i', path, '-af', 'volumedetect',
             '-f', 'null', '-'],
            capture_output=True, text=True).stderr
        m = re.search(r'max_volume:\s*([-\d.]+)\s*dB', out)
        return float(m.group(1)) if m else None
    except Exception:
        return None


# Shapes that a TTS engine reads as a full stop when they are not one. Each of
# these shipped: "₹1.10 ಲಕ್ಷ" was read "one" … "ten lakh", and "ಕೆ. ಜೆ. ಜಾರ್ಜ್"
# was read with a long gap between the letters of a man's name. Both are
# invisible in the text and only audible in the render, which is exactly why
# they are checked here rather than left to a listener.
TTS_HAZARD = [
    (re.compile(r'\d\.\d'),
     'a decimal point inside a figure — the engine stops on it and reads the '
     'two halves as separate numbers'),
    (re.compile(r'(?<![\w])[A-Za-z\u0C80-\u0CFF]{1,2}\.\s*[A-Za-z\u0C80-\u0CFF]{1,2}\.'),
     'initials with dots — the engine treats each letter as a finished '
     'sentence and leaves a gap inside the name'),
    (re.compile(r'₹'),
     'a ₹ symbol — the engine either skips it or names it in English'),
    (re.compile(r'\d\s*%'),
     'a % sign — Kannada says ಶೇಕಡಾ before the figure'),
    (re.compile(r'\d{1,2}:\d{2}'),
     'a clock time in digits — read as "colon"'),
]

# A pause this long inside one spoken beat is not phrasing, it is a seam.
MAX_INTERNAL_GAP = 0.85


def check_narration(story, spoken_beats) -> list[str]:
    """Read the script the engine will actually be given, and object to it."""
    out = []
    for key, text in spoken_beats:
        if len(text) > Limits.narration_beat_chars:
            out.append(f'narration beat "{key}" is {len(text)} characters — '
                       f'over the {Limits.narration_beat_chars:.0f}-character / '
                       f'{Limits.card_beat_seconds:.0f}s card budget. '
                       f'Tighten the copy or provide narration_script.')
        for pat, why in TTS_HAZARD:
            m = pat.search(text)
            if m:
                out.append(f'narration beat "{key}" contains {m.group(0)!r}: '
                           f'{why}')
    return out


def audio_gaps(path: str, limit: float = MAX_INTERNAL_GAP) -> list[tuple]:
    """Silences inside the speech, which is where a mispronunciation shows.

    A gap between beats is designed (Motion.vo_gap). A gap in the MIDDLE of a
    beat is the engine having stopped at something it read as a full stop —
    the audible form of every hazard in TTS_HAZARD.
    """
    out = subprocess.run(
        ['ffmpeg', '-hide_banner', '-i', path, '-af',
         f'silencedetect=n=-45dB:d={limit:.2f}', '-f', 'null', '-'],
        capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', out)]
    ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', out)]
    return list(zip(starts, ends))


def review(outdir: str, edition: Edition | None = None) -> ReviewReport:
    """Establish every fact about a finished package that a machine can."""
    r = ReviewReport()

    if not os.path.isdir(outdir):
        r.add_fail('PKG-02', f'{outdir} does not exist — nothing was rendered')
        return r

    files = sorted(os.listdir(outdir))
    texts = [f for f in files if f.endswith(('.txt', '.md', '.json'))]
    reels = [f for f in files if re.fullmatch(r'reel(_\d+)?\.mp4', f)]
    # Festival wish posters (D54) are deliverables too; without this a
    # greetings folder was rejected as having nothing in it.
    slides = [f for f in files
              if (f.startswith('carousel_') and f.endswith('.jpg'))
              or re.fullmatch(r'wish_\w+\.jpg', f)]

    # ── the handle ────────────────────────────────────────────────────────
    # One wrong capital and every caption points at an account that does not
    # exist. It is the single most-repeated string in the package, so it is
    # checked in every file rather than trusted from the token.
    r.checked.append('handle casing in every copy file')
    for f in texts:
        with open(os.path.join(outdir, f), encoding='utf-8') as fh:
            body = fh.read()
        for m in set(re.findall(r'@[A-Za-z_][A-Za-z0-9_.]*', body)):
            if m.lower() == Brand.handle.lower() and m != Brand.handle:
                r.add_fail('PUB-01', f'{f}: handle is written {m!r}; it must be '
                           f'{Brand.handle!r} exactly', where=f)

    # ── nothing is promised that is not there ─────────────────────────────
    r.checked.append('every file the copy references exists')
    master = os.path.join(outdir, 'MASTER_COPY.md')
    sched = os.path.join(outdir, 'schedule.json')
    referenced: set[str] = set()
    for p in (master, sched):
        if not os.path.exists(p):
            continue
        with open(p, encoding='utf-8') as fh:
            body = fh.read()
        # A range is written "carousel_01_cover.jpg … carousel_08_sources.jpg".
        # Both ends are real filenames and both are checked; what must NOT be
        # checked is a fragment left by the ellipsis itself.
        referenced |= set(re.findall(
            r'(?<![\w.-])[A-Za-z][\w.-]*\.(?:mp4|jpg|png|mp3|txt|md)', body))
    for name in sorted(referenced):
        base = os.path.basename(name)
        if base == 'APPROVAL.md':
            continue
        if base not in files:
            r.add_fail('PKG-01', f'the copy points at {base}, which was not rendered', where=base)

    # ── the reels ─────────────────────────────────────────────────────────
    for f in reels:
        p = os.path.join(outdir, f)
        r.checked.append(f'{f}: duration, audio, size')
        d = _duration(p)
        mb = os.path.getsize(p) / 1e6
        if d <= 0:
            r.add_fail('VID-02', f'{f} has no readable duration — it is not a video', where=f)
            continue
        if not _has_audio(p):
            r.add_fail('SND-01', f'{f} has NO AUDIO TRACK. It would post silent.', where=f)
        if d > REEL_MAX_SECONDS:
            r.add_fail('VID-02', f'{f} runs {d:.1f}s; Instagram Reels caps at '
                       f'{REEL_MAX_SECONDS:.0f}s and would refuse or crop it.', where=f)
        elif d > REEL_FAIL_SECONDS:
            r.add_fail(
                'VID-01',
                f'{f} runs {d:.1f}s; house rule fails anything over '
                f'{REEL_FAIL_SECONDS:.0f}s (target {Limits.reel_target_min:.0f}–'
                f'{REEL_TARGET_MAX:.0f}s).', where=f)
        if d < REEL_MIN_SECONDS:
            r.add_fail('VID-03', f'{f} is only {d:.1f}s — too short to be watched.', where=f)
        if REEL_WARN_SECONDS < d <= REEL_FAIL_SECONDS:
            r.add_warn(
                'VID-01',
                f'{f} runs {d:.1f}s. Target {Limits.reel_target_min:.0f}–'
                f'{REEL_TARGET_MAX:.0f}s for completion rate.', where=f)
        if mb > UPLOAD_CEILING_MB:
            r.add_warn('PKG-04', f'{f} is {mb:.0f}MB; that is a slow upload on mobile data.', where=f)
        # A cover is what the shelf shows. Missing, the platform picks frame 0.
        cover = f.replace('.mp4', '_cover.jpg')
        if cover not in files:
            r.add_warn('PKG-03', f'{f} has no {cover} — the platform will choose its '
                       f'own thumbnail.', where=f)

        # A reel that was MEANT to carry narration and came out silent.
        # render.py leaves a marker; without this check the folder looked
        # complete and a silent reel was cleared to publish.
        if os.path.exists(os.path.join(outdir, f[:-4] + '.NARRATION_FAILED')):
            with open(os.path.join(outdir, f[:-4] + '.NARRATION_FAILED'),
                      encoding='utf-8') as fh:
                why = fh.read().strip()
            r.add_fail('SND-02', f'{f} HAS NO VOICEOVER — synthesis failed and it fell '
                       f'back to a silent render ({why}). Re-run it.', where=f)

    if not reels and not slides:
        r.add_fail('PKG-02', 'the folder contains no reels and no carousel slides')

    # ── the copy ──────────────────────────────────────────────────────────
    if edition is not None:
        r.checked.append('legal markers, disclosure, glyph safety')
        for i, st in enumerate(edition.stories, 1):
            # Crime copy that travels alone must qualify itself alone.
            if st.category == 'crime':
                for label, line in (('headline', st.headline),
                                    ('reel_line', st.reel_line or st.headline)):
                    if line and not any(k in line for k in ALLEGATION):
                        r.add_fail('LAW-01',
                            f'story {i} {label} asserts a crime without an '
                            f'allegation marker: {line[:52]}…', where=f'story {i}')
            # Synthetic imagery must be disclosed in the caption too, not only
            # on the frame.
            if st.has_synthetic_imagery:
                cap = os.path.join(outdir, f'reel_{i:02d}_copy.txt')
                if os.path.exists(cap):
                    with open(cap, encoding='utf-8') as fh:
                        body = fh.read()
                    if 'ಎಐ ರಚಿತ' not in body:
                        r.add_fail('LAW-05',
                            f'story {i} uses generated imagery but its caption '
                            f'does not carry the ಎಐ ರಚಿತ ಚಿತ್ರ disclosure',
                            where=f'story {i}')
            # Anything that will be SET must be settable.
            for label, line in (('headline', st.headline),
                                ('reel_line', st.reel_line)):
                if not line:
                    continue
                gone = typo.missing_glyphs(line, typo.font_for(line, 'kn', 40))
                if gone:
                    r.add_fail('TYPE-01', f'story {i} {label} contains characters no '
                               f'house font can set: {" ".join(gone)}',
                               where=f'story {i}')
            # Visual novelty: every fact in a reel must cut to a distinct photo (1:1 scene coverage)
            if getattr(st, 'is_reel', False):
                n_facts = len([p for p in st.points if p.strip()])
                n_gallery = len(st.gallery)
                if n_gallery < n_facts:
                    r.add_fail('IMG-03',
                        f'story {i} is a reel with {n_facts} facts but only {n_gallery} gallery photos. '
                        f'Add gallery photos so the hero photo does not freeze or repeat across facts.',
                        where=f'story {i}')

        if slides:
            unillustrated = [i for i, st in enumerate(edition.stories, 1) if not st.photo]
            if unillustrated:
                # The editor's standing instruction, and it blocks rather than
                # warns: a warning is a thing you scroll past at 08:00 with a
                # bulletin due, which is precisely when the slide ships without
                # a picture. Recoverable in seconds — assets/stock/ is right
                # there and CATALOG.md says what is in it. House rule
                # 2026-09-17-03.
                r.add_fail('IMG-04',
                    f'carousel slides for stories {unillustrated} carry no '
                    f'photograph. Every slide in the daily carousel must have '
                    f'one (house rule 2026-09-17-03): pick a matching frame '
                    f'from assets/stock/ (see assets/stock/CATALOG.md) or '
                    f'generate one, and set nature="ai" on anything generated.')

        # ── the second half of D55 ────────────────────────────────────────
        # "No source, no claim" was enforced at the contract. "No human
        # verification, no publication" was written in the decision and
        # enforced nowhere, which meant the whole legal apparatus could still
        # be polishing copy that nobody had checked against its own source.
        # This is the check that closes it. See D59.
        r.checked.append('every story verified by a named person')
        for i, st in enumerate(edition.stories, 1):
            if st.is_verified:
                continue
            r.add_fail(
                'SRC-02',
                f'story {i} has no verified_by. Someone has to open the '
                f'source and say, by name, that they checked it — the gate '
                f'cannot establish whether a fact is true, and nothing '
                f'downstream ever asks again. Add '
                f'"verified_by": "<name>" (and ideally "verified_at") to '
                f'the story in the edition JSON.',
                where=f'story {i}')

        # ── editorial drift ───────────────────────────────────────────
        # Not a legal check and not a quality check: a direction check. The
        # reel gate rewards drama, stakes and shareability, crime wins on all
        # three, and nothing anywhere notices the channel turning into a crime
        # channel one good news day at a time. D68.
        r.checked.append('crime share of the edition')
        crime = [i for i, st in enumerate(edition.stories, 1)
                 if st.category == 'crime']
        crime_reels = [i for i, st in enumerate(edition.stories, 1)
                       if st.category == 'crime' and getattr(st, 'is_reel', False)]
        if len(crime_reels) > Limits.crime_reels_per_day:
            r.add_warn(
                'PUB-04',
                f'{len(crime_reels)} crime reels in one edition (house cap is '
                f'{Limits.crime_reels_per_day}). Crime always wins the reel '
                f'gate on drama and shareability, so the gate cannot be the '
                f'thing that limits it. Promote a civic, weather or culture '
                f'story to the second reel slot instead.')
        if edition.stories and len(crime) / len(edition.stories) > Limits.crime_share_warn:
            r.add_warn(
                'PUB-04',
                f'{len(crime)} of {len(edition.stories)} stories are crime '
                f'({len(crime) / len(edition.stories):.0%}). One day like this '
                f'is a day. A run of them is what the channel becomes, and it '
                f'is where every legal exposure in this system lives.')

        # ── reach ─────────────────────────────────────────────────────
        # Not craft and not law: whether the people this was written for can
        # tell it is for them. A coastal story whose town name sits past the
        # caption fold is invisible to the taluk it is about, and a notice
        # rendered as a video reaches fewer people than the card would have.
        # D72.
        r.checked.append('place before the fold, and format fit')
        try:
            from . import reach
            from .copy import for_story
            for i, st in enumerate(edition.stories, 1):
                rel = reach.relevance(st)
                if not rel.place:
                    r.add_warn(
                        'PUB-08',
                        f'story {i} names no place. Nobody scrolling can tell '
                        f'whether it is about their town, and nobody forwards '
                        f'what is not theirs. Set `location`.',
                        where=f'story {i}')
                else:
                    ok, why = reach.place_before_fold(st, for_story(st).instagram)
                    if not ok:
                        r.add_warn(
                            'PUB-05',
                            f'story {i}: {why}', where=f'story {i}')
                if getattr(st, 'is_reel', False):
                    earns, why = reach.should_be_reel(st)
                    if not earns:
                        r.add_warn(
                            'PUB-06',
                            f'story {i} is marked is_reel but {why}. A card '
                            f'that gets screenshotted beats a video nobody '
                            f'finishes.', where=f'story {i}')
            marked = sum(1 for st in edition.stories
                         if getattr(st, 'is_reel', False))
            if marked > Limits.reels_per_day_target:
                r.add_warn(
                    'PUB-07',
                    f'{marked} reels marked, the day targets '
                    f'{Limits.reels_per_day_target}. On an account this size '
                    f'each post goes to a small test slice — splitting the '
                    f'same audience {marked} ways makes all of them look '
                    f'average. Run the best two.')
        except Exception as e:
            r.add_warn('PUB-05', f'reach could not be checked ({e})')

        r.checked.append('grievance officer named')
        if not Brand.grievance_named():
            r.add_fail('OPS-01',
                'Grievance Officer is unnamed. Fill Brand.grievance_officer and '
                'Brand.grievance_phone or Brand.grievance_email before '
                'APPROVAL.md can be written.')

        r.checked.append('schedule does not send AI reels to YouTube')
        if os.path.exists(sched):
            try:
                with open(sched, encoding='utf-8') as fh:
                    body = fh.read()
                if 'YouTube Shorts' in body and 'Instagram Reels + YouTube Shorts' in body:
                    r.add_fail('PUB-02',
                        'schedule still routes AI reels to YouTube Shorts. '
                        'Rule 7: AI-card reels are Instagram-only.',
                        where='schedule.json')
            except OSError:
                pass

    # The script is checked, not the audio alone, because a hazard is visible
    # in the text and only audible after a four-minute render.
    if edition is not None:
        r.checked.append('narration script for TTS hazards')
        try:
            from .voice import narration_beats
            for i, st in enumerate(edition.stories, 1):
                for msg in check_narration(st, narration_beats(st)):
                    r.add_fail('SND-03', f'story {i}: {msg}', where=f'story {i}')
        except Exception as e:
            r.add_warn('SND-03', f'narration could not be checked ({e})')

    # ── gaps inside the spoken beats ──────────────────────────────────────
    for f in sorted(files):
        if not f.endswith('_voiceover.mp3'):
            continue
        r.checked.append(f'{f}: pauses inside the speech')
        p = os.path.join(outdir, f)
        long_gaps = [(a, b) for a, b in audio_gaps(p)
                     if b - a > MAX_INTERNAL_GAP and a > 1.0]
        # Beat boundaries are designed silences; anything much longer than the
        # designed gap, or a run of them, means the engine stopped mid-sentence.
        from .tokens import Motion
        ceiling = Motion.vo_gap + Motion.vo_hold_max + 0.6
        overlong = [(a, b) for a, b in long_gaps if b - a > ceiling]
        if overlong:
            where = ', '.join(f'{a:.1f}–{b:.1f}s' for a, b in overlong[:4])
            r.add_warn('SND-04',
                f'{f} has {len(overlong)} pause(s) longer than {ceiling:.1f}s '
                f'({where}). A designed beat gap is {Motion.vo_gap:.2f}s — '
                f'anything much past that is the engine having stopped at '
                f'something it read as a full stop.', where=f)

    # ── the seats a machine cannot sit in ─────────────────────────────────
    # Not a blocking fault: the sign-off happens AFTER the evidence folder is
    # looked at, which is after this runs. But the package is not publishable
    # until it is there, and APPROVAL.md says so in as many words.
    r.checked.append('human judgement seats')
    if not is_signed(outdir):
        missing = [s for s in JUDGEMENT_SEATS
                   if not str(signoff_state(outdir).get(s, '')).strip()]
        r.add_warn(
            'OPS-03',
            f'unsigned: {", ".join(missing)}. Mechanical checks cannot '
            f'establish taste, cultural dignity or news judgement. Look at '
            f'_review/ and run scripts/sign_off.py before uploading.')

    # ── the schedule ──────────────────────────────────────────────────────
    if os.path.exists(sched):
        r.checked.append('schedule spacing')
        try:
            with open(sched, encoding='utf-8') as fh:
                plan = json.load(fh)
            slots = plan if isinstance(plan, list) else plan.get('slots', [])
            mins = [s.get('at') for s in slots if isinstance(s, dict) and 'at' in s]
            if any(isinstance(m, (int, float)) for m in mins):
                nums = sorted(m for m in mins if isinstance(m, (int, float)))
                for a, b in zip(nums, nums[1:]):
                    if b - a < 90:
                        r.add_warn('PUB-03',
                            f'two posts are {b - a:.0f} minutes apart; posting '
                            f'that close makes them compete with each other.',
                            where='schedule.json')
                        break
        except Exception as e:
            r.add_warn('PUB-03', f'schedule.json could not be parsed ({e})', where='schedule.json')

    return r


def evidence(outdir: str, into: str | None = None) -> list[str]:
    """Extract what a judgement about craft has to be made against.

    Every carousel slide, every reel cover, and a frame from the middle of
    every card of every reel. The Chief Editor's visual verdict is only worth
    anything if these were actually looked at, so they are produced as files
    and the review is required to reference them.

    `_review/` holds all of it, including the stills — which used to stay in
    place, so on a carousel-only day the folder somebody was told to open was
    empty. It also holds `feed_sizes.jpg`: every deliverable shrunk to the
    width it is genuinely first seen at (150px in a profile grid, 200px in the
    Reels grid, 210px in a YouTube search row). Everything here is designed at
    1080 and judged at 100% on a desktop, which is the one viewing condition no
    reader of this channel has ever been in. See D60.
    """
    into = into or os.path.join(outdir, '_review')
    os.makedirs(into, exist_ok=True)
    out: list[str] = []

    for f in sorted(os.listdir(outdir)):
        src = os.path.join(outdir, f)
        if f.startswith('carousel_') and f.endswith('.jpg'):
            out.append(src)
        elif f.endswith('_cover.jpg'):
            out.append(src)
        elif re.fullmatch(r'reel(_\d+)?\.mp4', f):
            d = _duration(src)
            if d <= 0:
                continue
            # Eight evenly spaced frames: enough to see every card of a
            # narrated reel, and every transition between them.
            n = 8
            for k in range(n):
                t = d * (k + 0.5) / n
                dst = os.path.join(into, f'{f[:-4]}_t{int(t):03d}s.jpg')
                subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss',
                                f'{t:.2f}', '-i', src, '-frames:v', '1',
                                '-q:v', '3', dst], check=False)
                if os.path.exists(dst):
                    out.append(dst)

    # Bring the stills INTO the folder people are told to open. Before this,
    # `_review/` on a carousel-only morning was an empty directory and the
    # instruction "open every evidence frame" pointed at nothing.
    import shutil
    for src in list(out):
        if not src.lower().endswith(('.jpg', '.png')):
            continue
        if os.path.dirname(os.path.abspath(src)) == os.path.abspath(into):
            continue
        dst = os.path.join(into, os.path.basename(src))
        try:
            shutil.copy2(src, dst)
        except OSError:
            pass

    sheet = feed_size_sheet(outdir, into)
    if sheet:
        out.append(sheet)
    return out


def feed_size_sheet(outdir: str, into: str) -> str:
    """Every deliverable at the width it is actually first seen at.

    A carousel cover is about 150px in a profile grid; a reel's first frame
    about 200px in the feed; a thumbnail about 210px in a search row. Judging
    them at 1080 on a desktop is how a headline that nobody can read at feed
    size gets approved by somebody who read it perfectly well.

    One JPEG, written into the evidence folder. If the hook is not legible
    here, it is not legible. See brand/legibility.py and D60.
    """
    try:
        from PIL import Image, ImageDraw
        from . import legibility as L
    except Exception:
        return ''

    # (file pattern → the format key whose first-sight width applies)
    def key_for(name: str) -> str | None:
        n = name.lower()
        if n.startswith('carousel_'):
            return 'square'
        if n.endswith('_cover.jpg') or n.startswith('story_'):
            return 'reel' if 'reel' in n else 'story'
        if n.startswith('yt_thumbnail'):
            return 'thumb'
        if n.startswith('broadsheet'):
            return 'broadsheet'
        if n.startswith('post_'):
            return 'post'
        return None

    tiles: list[tuple[str, Image.Image]] = []
    for f in sorted(os.listdir(outdir)):
        if not f.lower().endswith('.jpg'):
            continue
        k = key_for(f)
        if not k:
            continue
        w = L.FEED_WIDTH.get(k, 300)
        try:
            im = Image.open(os.path.join(outdir, f)).convert('RGB')
        except Exception:
            continue
        im.thumbnail((w, w * 3), Image.Resampling.LANCZOS)
        tiles.append((f, im))
    if not tiles:
        return ''

    # Packed left to right, wrapping — NOT a uniform grid. These are
    # deliberately different widths (that is the whole point), and a grid sized
    # to the widest leaves a 300px hole beside every 150px thumbnail.
    pad, label_h, max_w = 14, 15, 1400
    rows_of: list[list] = [[]]
    width_of = [0]
    for name, im in tiles:
        need = im.width + pad
        if width_of[-1] + need > max_w and rows_of[-1]:
            rows_of.append([])
            width_of.append(0)
        rows_of[-1].append((name, im))
        width_of[-1] += need
    sheet_w = max(width_of) + pad
    row_h = [max(im.height for _n, im in r) + pad + label_h for r in rows_of]
    sheet = Image.new('RGB', (sheet_w, sum(row_h) + pad), (16, 18, 24))
    d = ImageDraw.Draw(sheet)
    y = pad
    for r, row in enumerate(rows_of):
        x = pad
        for name, im in row:
            sheet.paste(im, (x, y))
            d.text((x, y + im.height + 3), f'{name}  {im.width}px',
                   fill=(150, 160, 178))
            x += im.width + pad
        y += row_h[r]
    path = os.path.join(into, 'feed_sizes.jpg')
    try:
        sheet.save(path, 'JPEG', quality=88, optimize=True)
    except OSError:
        return ''
    return path


# The three things no check in this file can establish, and no model should be
# allowed to assert. Section 21 of the system book already said these stay
# human; until now the workflow did not force a human into the seat.
JUDGEMENT_SEATS = {
    'taste': 'Does this look like the channel at its best, at feed size?',
    'culture': 'Is every ritual, deity, name and community treated with dignity?',
    'news': 'Is this the right lead, and is every claim one we can stand behind?',
}

SIGN_FILE = 'SIGNOFF.json'


def signoff_state(outdir: str) -> dict:
    """Who has signed which judgement seat on this package."""
    p = os.path.join(outdir, SIGN_FILE)
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding='utf-8') as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def is_signed(outdir: str) -> bool:
    """True only when every judgement seat carries a real name."""
    state = signoff_state(outdir)
    return all(str(state.get(k, '')).strip() for k in JUDGEMENT_SEATS)


def sign(outdir: str, by: str, seats: tuple[str, ...] = (), notes: str = '') -> str:
    """Record a named person's judgement, then rewrite APPROVAL.md.

    A score out of ten from an assistant is not evidence. A name is — because
    a name can be asked about it afterwards, and a score cannot.
    """
    by = (by or '').strip()
    if not by:
        raise ValueError('sign() needs a real name; that is the whole point')
    unknown = [s for s in seats if s not in JUDGEMENT_SEATS]
    if unknown:
        raise ValueError(f'unknown judgement seat(s) {unknown}; '
                         f'choose from {sorted(JUDGEMENT_SEATS)}')
    from .content import now
    state = signoff_state(outdir)
    for seat in (seats or tuple(JUDGEMENT_SEATS)):
        state[seat] = by
    state['at'] = now().isoformat()
    if notes:
        state['notes'] = notes
    with open(os.path.join(outdir, SIGN_FILE), 'w', encoding='utf-8') as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False)
        fh.write('\n')
    # Re-stamp the approval so the folder never disagrees with itself.
    prev = os.path.join(outdir, 'APPROVAL.md')
    if os.path.exists(prev):
        _restamp(outdir)
    return os.path.join(outdir, SIGN_FILE)


def _restamp(outdir: str) -> None:
    """Refresh only the sign-off block of an existing APPROVAL.md."""
    path = os.path.join(outdir, 'APPROVAL.md')
    with open(path, encoding='utf-8') as fh:
        body = fh.read()
    head, sep, _tail = body.partition('## Human judgement')
    if not sep:
        return
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(head + '\n'.join(_judgement_block(outdir)).lstrip('\n'))


def _judgement_block(outdir: str) -> list[str]:
    state = signoff_state(outdir)
    lines = ['## Human judgement', '',
             'These three cannot be established by any check in `brand/review.py`,',
             'and an assistant scoring itself out of ten is not evidence for them.',
             '']
    for seat, question in JUDGEMENT_SEATS.items():
        who = str(state.get(seat, '')).strip()
        mark = 'x' if who else ' '
        lines.append(f'- [{mark}] **{seat}** — {question}'
                     + (f'  →  signed by **{who}**' if who else ''))
    lines += ['']
    if is_signed(outdir):
        when = state.get('at', '')
        lines += [f'🟢 **Signed{" · " + when if when else ""}. Cleared to publish.**', '']
        if state.get('notes'):
            lines += ['> ' + str(state['notes']), '']
    else:
        lines += [
            '🟡 **Mechanically clean, NOT yet cleared to publish.**',
            '',
            'Look at `_review/` at feed size, listen to one reel on headphones,',
            'then sign:',
            '',
            '```bash',
            f'python3 scripts/sign_off.py {outdir} --by "<your name>"',
            '```',
            '',
        ]
    lines += [
        '---', '',
        'ಈ ಕಡತವು ಯಾಂತ್ರಿಕ ಪರಿಶೀಲನೆಗಳು ಉತ್ತೀರ್ಣವಾಗಿವೆ ಎಂದು ಮಾತ್ರ ಹೇಳುತ್ತದೆ. '
        'ಅಭಿರುಚಿ, ಸಂಸ್ಕೃತಿ ಮತ್ತು ಸುದ್ದಿ ವಿವೇಚನೆ — ಇವು ಮನುಷ್ಯನ ಜವಾಬ್ದಾರಿ.', '',
        '_This file records what a machine could establish. Taste, cultural '
        'judgement and news judgement are not among them._', '',
    ]
    return lines


def approve(outdir: str, report: ReviewReport, notes: str = '') -> str | None:
    """Write APPROVAL.md — but only if the mechanical checks are clean.

    The file is the green signal. Its ABSENCE is the meaningful state: an
    output folder without one has not been cleared, whatever was said about it
    in conversation.

    What it is NOT is a substitute for a person. The old closing line said
    "you can post without watching", which is precisely the overclaim the rest
    of this module exists to prevent — no check here can tell whether the lead
    is right, whether a deity is treated with dignity, or whether the package
    looks like the channel at its best. Those three seats are written into the
    file unfilled, and `sign()` is the only thing that fills them.

    `review_report.json` is written either way: a failed review is the thing a
    notifier most needs to be able to read.
    """
    path = os.path.join(outdir, 'APPROVAL.md')
    # The machine-readable twin, written pass or fail.
    try:
        with open(os.path.join(outdir, 'review_report.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump(report.to_dict(), fh, indent=2, ensure_ascii=False)
            fh.write('\n')
    except OSError:
        pass
    if not report.clean:
        # Never leave a stale approval standing over a package that now fails.
        if os.path.exists(path):
            os.remove(path)
        return None
    from .content import now
    lines = [
        '# ಮುಖ್ಯ ಸಂಪಾದಕರ ಪರಿಶೀಲನೆ — CHIEF EDITOR REVIEW',
        '',
        f'**Mechanically cleared:** {now():%Y-%m-%d %H:%M %Z}',
        f'**Folder:** `{outdir}`',
        '',
        f'{len(report.checked)} mechanical checks passed with no failures. '
        'Full detail in `review_report.json`.',
        '',
        '## Checked',
        *[f'- {c}' for c in report.checked],
    ]
    if report.warn:
        lines += ['', '## Noted but not blocking']
        coded = {f.message: f.code for f in report.findings}
        for w in report.warn:
            c = coded.get(w)
            lines.append(f'- {("`" + c + "` ") if c else ""}{w}')
    if notes:
        lines += ['', "## Chief Editor's notes", '', notes]
    lines += ['', *_judgement_block(outdir)]
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return path


def approve_footage(outdir: str, notes: str = '') -> str | None:
    """Write APPROVAL_FOOTAGE.md for Line B/C packages.

    Best-performing content currently has the weakest gate. Real footage still
    needs: audio present, legal peak, named music bed, no child as thumbnail,
    and a Kannada engagement question in the description.
    """
    r = ReviewReport()
    r.checked.append('footage folder exists')
    if not os.path.isdir(outdir):
        r.add_fail('PKG-02', f'{outdir} is not a folder')
        return None

    files = [f for f in os.listdir(outdir)
             if os.path.isfile(os.path.join(outdir, f))]
    videos = [f for f in files if f.lower().endswith(('.mp4', '.mov', '.m4v'))]
    if not videos:
        r.add_fail('PKG-02', 'no video in the footage package')

    brief = os.path.join(outdir, 'BRIEF.md')
    if os.path.exists(brief):
        r.checked.append('BRIEF.md present')
        with open(brief, encoding='utf-8') as fh:
            body = fh.read()
        if 'ನಿಮ್ಮ ಅಭಿಪ್ರಾಯ' not in body and 'ಕಮೆಂಟ್' not in body:
            r.add_warn('PUB-02',
                'description has no Kannada engagement question '
                '("ನಿಮ್ಮ ಅಭಿಪ್ರಾಯ ಏನು? ಕಮೆಂಟ್ ಮಾಡಿ.")', where='BRIEF.md')
    else:
        r.add_warn('PKG-01', 'no BRIEF.md — names, dates and the engagement question live there')

    try:
        from .music import check_package
        for msg in check_package(outdir):
            r.add_fail('PKG-05', msg)
        r.checked.append('music licence register')
    except Exception as e:
        r.add_warn('PKG-05', f'music licence could not be checked ({e})')

    for f in videos:
        p = os.path.join(outdir, f)
        d = _duration(p)
        if d <= 0:
            r.add_fail('VID-02', f'{f} has no duration', where=f)
            continue
        r.checked.append(f'{f}: {d:.1f}s')
        if not _has_audio(p):
            r.add_fail('SND-01', f'{f} is silent — real footage must carry real sound', where=f)
        peak = _peak_dbfs(p)
        if peak is not None and peak > -0.5:
            r.add_fail('VID-04', f'{f} peaks at {peak:.1f} dBFS — will clip on YouTube', where=f)

    path = os.path.join(outdir, 'APPROVAL_FOOTAGE.md')
    if not r.clean:
        if os.path.exists(path):
            os.remove(path)
        r.show('footage review')
        return None
    from .content import now
    lines = [
        '# 🟢 FOOTAGE APPROVAL — Line B/C',
        '',
        f'**Cleared:** {now():%Y-%m-%d %H:%M %Z}',
        f'**Folder:** `{outdir}`',
        '',
        'Real camera package. YouTube-eligible under Rule 7.',
        '',
        '## Checked',
        *[f'- {c}' for c in r.checked],
    ]
    if r.warn:
        lines += ['', '## Noted but not blocking', *[f'- {w}' for w in r.warn]]
    if notes:
        lines += ['', '## Editor', '', notes]
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))
    r.show('footage review')
    return path
