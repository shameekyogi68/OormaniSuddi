"""
ಊರ್ಮನಿ ಸುದ್ದಿ — who should be working right now, and why. D89, D92.
====================================================================
Ten specialist agents live in `.claude/agents/` (their shared rules are in
`.claude/agents/_CONVENTIONS.md`, which is not an agent). An agent nobody
remembers to call is an agent that does not exist, so this module reads the
state of the newsroom — editions, kept sources, receipts, gate reports, the
complaint clocks — and says which agents are due, for what, in which wave.
Nothing here calls a model; it is arithmetic over files.

The production path, in waves (tasks in one wave run in parallel):

  0  intake-editor      an edition has a story with no `segment` (D92)
     corrections-officer  a complaint clock is running, or a known error is
                        uncorrected
  1  fact-checker, legal-standards      one per story (legal: risky ones)
  2  kannada-editor     one per story
     picture-editor     one per story that needs a picture checked or briefed
  3  (after render)     package-inspector, one per format in out/<stem>
                        (roundup, saara, mukhya_N) · social-writer caption
                        audit · gate-doctor when the gate HELD. The code
                        owners are NOT dispatched beside the doctor: it names
                        them in its receipt.

**Ops** — planning-editor (weekly review, or on request) and systems-steward
(weekly, or health red) — are listed separately and never mixed into the
production waves.

**Person** tasks are what no agent may do: verify a story (`verified_by`),
answer "real photo, or generate?" (`photo_plan`), send the photograph, sign
off.

**Receipts.** Every agent files its report with
`python3 scripts/dispatch.py receipt …`, stamped with a hash of what it
looked at. Each desk hashes only what its work depends on: the fact and legal
desks hash the fact-bearing fields, so assigning a segment or adding a photo
does not send a story back to them; a copy edit does. A receipt whose
verdict is BLOCK is surfaced to the person — no agent clears another's block.

Routing of gate codes to agents lives in `CODE_AGENT`, beside
`brand/codes.py :: OWNER` which says the same thing for people.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS_DIR = os.path.join(ROOT, '.claude', 'agents')
RECEIPTS = os.path.join(ROOT, 'inbox', 'receipts')
CONVENTIONS = '_CONVENTIONS.md'   # shared rules; not an agent

# Every agent, what kind it is, and the stage it serves. The test suite holds
# this table and `.claude/agents/*.md` (minus _CONVENTIONS.md) to each other.
ROSTER: dict[str, dict] = {
    'intake-editor':       {'kind': 'reactive', 'stage': 'intake'},
    'fact-checker':        {'kind': 'reactive', 'stage': 'desk'},
    'legal-standards':     {'kind': 'reactive', 'stage': 'desk'},
    'kannada-editor':      {'kind': 'reactive', 'stage': 'desk'},
    'picture-editor':      {'kind': 'reactive', 'stage': 'picture'},
    'instagram-strategist': {'kind': 'reactive', 'stage': 'reach'},
    'package-inspector':   {'kind': 'reactive', 'stage': 'package'},
    'social-writer':       {'kind': 'reactive', 'stage': 'package'},
    'gate-doctor':         {'kind': 'reactive', 'stage': 'gate'},
    'corrections-officer': {'kind': 'reactive', 'stage': 'after'},
    'planning-editor':     {'kind': 'ops',      'stage': 'planning'},
    'systems-steward':     {'kind': 'ops',      'stage': 'operations'},
}

# Desks that work story by story and may read several in one run (D97).
BATCHED = ('fact-checker', 'legal-standards', 'kannada-editor', 'picture-editor')

# A failing gate code, routed to the agent that can do the work.
CODE_AGENT = {
    'FACT': 'fact-checker', 'SRC': 'fact-checker', 'LAW': 'legal-standards',
    'IMG': 'picture-editor', 'TYPE': 'package-inspector',
    'SND': 'kannada-editor', 'VID': 'package-inspector', 'PKG': 'gate-doctor',
    'PUB': 'social-writer', 'OPS': 'systems-steward', 'DUP': 'intake-editor',
}

# D92: one story, one format.
SEGMENTS = ('speed', 'saara', 'mukhya')
PHOTO_PLANS = ('', 'real', 'ai')
# The file-name prefix each format renders under in out/<stem>/.
_FORMAT_FILE = re.compile(r'^(roundup|saara|mukhya(?:_\d+)?)(?=[_.\-]|$)')

# Stories a legal eye reads before anyone else polishes them.
RISK_WORDS = ('ಸಾವು', 'ಮೃತ', 'ಆತ್ಮಹತ್ಯೆ', 'ಕೊಲೆ', 'ಅತ್ಯಾಚಾರ', 'ಬಂಧನ', 'ಆರೋಪ',
              'ಶವ', 'ಬಾಲಕ', 'ಬಾಲಕಿ', 'ಅಪ್ರಾಪ್ತ', 'ನಿಧನ')

# Days whose published stories carried claims their sources did not contain,
# with no correction logged (D84, D88). The corrections desk raises them
# until a case about each day is in the ledger.
KNOWN_ERRATA = ('2026-09-23', '2026-09-24')

# ── What each desk's work depends on ────────────────────────────────────────
# The fact and legal desks read the fact-bearing lines and nothing else:
# segment, photo_plan, photo, hook, template and verification are not facts.
FACT_FIELDS = ('headline', 'deck', 'points', 'numbers', 'quote', 'sources',
               'source_urls', 'location', 'dateline', 'category',
               'involves_minor', 'sexual_offence', 'convicted',
               'published_at', 'reel_line')
# The Kannada desk reads every line a reader sees or hears, for its format.
COPY_FIELDS = FACT_FIELDS + ('hook', 'takeaway', 'reel_points', 'reel_support',
                             'narration_script', 'segment')
# The reach desk decides format, hook, slot and first hour from what kind of
# story it is and when — NOT from its wording, so a Kannada copy edit never
# sends it round again (D97). The hook it proposes lives in `hook`, which is
# deliberately outside this list for the same reason.
STRATEGY_FIELDS = ('segment', 'category', 'location', 'published_at',
                   'photo_plan')
# The picture desk reads the picture, the plan for it, and what it must show.
PICTURE_FIELDS = ('photo', 'photo_plan', 'segment', 'headline', 'location',
                  'category', 'involves_minor', 'sexual_offence')
# Verification changes when a person signs; the story itself has not.
_VOLATILE = {'verified_by', 'verified_at'}


@dataclass
class Task:
    agent: str
    kind: str          # reactive | ops
    wave: int          # 0 first; tasks in one wave run in parallel
    reason: str
    target: str = ''   # edition path, out dir, or ''
    story: int = 0
    urgent: bool = False
    part: str = ''     # a format in out/<stem>: roundup, saara, mukhya_N


@dataclass
class Plan:
    day: str
    tasks: list[Task] = field(default_factory=list)
    ops: list[Task] = field(default_factory=list)     # never production waves
    person: list[str] = field(default_factory=list)   # only a human can do these

    def add(self, *a, **kw):
        t = Task(*a, **kw)
        into = self.ops if ROSTER.get(t.agent, {}).get('kind') == 'ops' \
            else self.tasks
        key = (t.agent, t.target, t.story, t.part)
        if key not in {(x.agent, x.target, x.story, x.part) for x in into}:
            into.append(t)

    def waves(self) -> dict[int, list[Task]]:
        out: dict[int, list[Task]] = {}
        for t in sorted(self.tasks, key=lambda t: (t.wave, not t.urgent, t.agent,
                                                   t.story, t.part)):
            out.setdefault(t.wave, []).append(t)
        return out

    def launches(self) -> dict[int, list[dict]]:
        """The same plan as AGENT RUNS, which is what costs tokens (D97).

        A per-story desk reads several stories in one run, up to
        Limits.agent_batch_max; everything else is one run per task. The gate
        still asks the per-story question (desk_gaps) — only the launching is
        batched, never the checking."""
        from .tokens import Limits
        out: dict[int, list[dict]] = {}
        for wave, tasks in self.waves().items():
            groups: dict[tuple, list[Task]] = {}
            runs: list[dict] = []
            for t in tasks:
                if t.story and t.agent in BATCHED and not t.part:
                    groups.setdefault((t.agent, t.target), []).append(t)
                else:
                    runs.append({'agent': t.agent, 'target': t.target,
                                 'stories': [t.story] if t.story else [],
                                 'part': t.part, 'urgent': t.urgent,
                                 'reasons': [t.reason]})
            for (agent, target), ts in groups.items():
                for k in range(0, len(ts), Limits.agent_batch_max):
                    chunk = ts[k:k + Limits.agent_batch_max]
                    runs.append({'agent': agent, 'target': target,
                                 'stories': [t.story for t in chunk], 'part': '',
                                 'urgent': any(t.urgent for t in chunk),
                                 'reasons': list(dict.fromkeys(t.reason for t in chunk))})
            out[wave] = sorted(runs, key=lambda r: (not r['urgent'], r['agent'],
                                                    r['stories'][:1]))
        return out

    def to_dict(self) -> dict:
        return {'day': self.day, 'tasks': [asdict(t) for t in self.tasks],
                'ops': [asdict(t) for t in self.ops], 'person': self.person}


# ─────────────────────────────────────────────────────────────────────────────
#  RECEIPTS
# ─────────────────────────────────────────────────────────────────────────────

def _digest(body) -> str:
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]


def story_hash(story: dict) -> str:
    """Everything but who verified it."""
    return _digest({k: v for k, v in story.items() if k not in _VOLATILE})


def fact_hash(story: dict) -> str:
    """Only the fact-bearing fields: a segment or a photo is not a fact."""
    return _digest({k: story.get(k) for k in FACT_FIELDS if k in story})


def copy_hash(story: dict) -> str:
    return _digest({k: story.get(k) for k in COPY_FIELDS if k in story})


def strategy_hash(story: dict) -> str:
    return _digest({k: story.get(k) for k in STRATEGY_FIELDS if k in story})


def picture_hash(story: dict) -> str:
    return _digest({k: story.get(k) for k in PICTURE_FIELDS if k in story})


# Which hash stamps which desk's receipt.
HASH_OF = {'fact-checker': fact_hash, 'legal-standards': fact_hash,
           'kannada-editor': copy_hash, 'picture-editor': picture_hash,
           'instagram-strategist': strategy_hash}


def hash_for(agent: str, story: dict) -> str:
    return HASH_OF.get(agent, story_hash)(story)


def edition_hash(edition: dict, fn=story_hash) -> str:
    return hashlib.sha1(''.join(fn(s) for s in edition.get('stories', []))
                        .encode()).hexdigest()[:12]


def _stem(path: str) -> str:
    return os.path.splitext(os.path.basename(path.rstrip('/')))[0]


def receipt_path(agent: str, stem: str, story: int = 0, part: str = '') -> str:
    name = (f'{agent}-{story}.md' if story else
            f'{agent}@{part}.md' if part else f'{agent}.md')
    return os.path.join(RECEIPTS, stem, name)


_HEAD = re.compile(r'<!-- receipt (.*?) -->')


def read_receipt(agent: str, stem: str, story: int = 0, part: str = '') -> dict:
    try:
        with open(receipt_path(agent, stem, story, part), encoding='utf-8') as fh:
            m = _HEAD.search(fh.readline())
    except OSError:
        return {}
    if not m:
        return {}
    return dict(kv.split('=', 1) for kv in m.group(1).split() if '=' in kv)


def write_receipt(agent: str, edition_path: str, verdict: str, body: str,
                  story: int = 0, part: str = '') -> str:
    """File an agent's report, stamped with a hash of what it looked at."""
    if agent not in ROSTER:
        raise ValueError(f'unknown agent {agent!r}; roster: {sorted(ROSTER)}')
    verdict = verdict.upper()
    if verdict not in ('PASS', 'FIX', 'BLOCK', 'HELD', 'DONE'):
        raise ValueError('verdict is PASS, FIX, BLOCK, HELD or DONE')
    if part and not _FORMAT_FILE.match(part):
        raise ValueError(f'format is roundup, saara or mukhya_N, not {part!r}')
    stem, h = _stem(edition_path), ''
    if edition_path.endswith('.json') and os.path.exists(edition_path):
        with open(edition_path, encoding='utf-8') as fh:
            ed = json.load(fh)
        stories = ed.get('stories', [])
        if story:
            if not 1 <= story <= len(stories):
                raise ValueError(f'story {story} is not in {edition_path}')
            h = hash_for(agent, stories[story - 1])
        else:
            h = edition_hash(ed, HASH_OF.get(agent, story_hash))
    path = receipt_path(agent, stem, story, part)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    head = (f'<!-- receipt agent={agent} story={story} '
            f'{"format=" + part + " " if part else ""}hash={h or "-"} '
            f'verdict={verdict} at={datetime.now().isoformat(timespec="seconds")} -->')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(head + '\n\n' + body.strip() + '\n')
    return path


def _receipt_current(agent: str, stem: str, h: str, story: int = 0) -> dict:
    r = read_receipt(agent, stem, story)
    return r if r and r.get('hash') == h else {}


# ─────────────────────────────────────────────────────────────────────────────
#  THE PLAN
# ─────────────────────────────────────────────────────────────────────────────

# Folders under editions/ that never hold a day's news.
NOT_DAILY = ('greetings',)


def _editions_for(day: str) -> list[str]:
    """The day's editions: editions/<day>*.json, and editions/<sub>/<day>*.json
    for a subfolder that holds daily editions — never editions/greetings/."""
    base = os.path.join(ROOT, 'editions')
    found = glob.glob(os.path.join(base, f'{day}*.json'))
    for sub in sorted(glob.glob(os.path.join(base, '*', ''))):
        if os.path.basename(os.path.dirname(sub)) in NOT_DAILY:
            continue
        found += glob.glob(os.path.join(sub, f'{day}*.json'))
    return sorted(found)


def _risky(st: dict) -> bool:
    if st.get('category') in ('crime', 'obituary') or st.get('involves_minor') \
            or st.get('sexual_offence'):
        return True
    text = ' '.join(filter(None, [st.get('headline', ''), st.get('deck', ''),
                                  st.get('reel_line', ''), *st.get('points', [])]))
    return any(w in text for w in RISK_WORDS)


def _photo(sd: dict) -> dict:
    p = sd.get('photo')
    if isinstance(p, str):
        return {'path': p} if p else {}
    return p or {}


def _picture_tasks(plan: Plan, rel: str, stem: str, i: int, sd: dict) -> None:
    """D92 point 3: real photographs first, AI only when the editor said so."""
    seg = sd.get('segment', '')
    photo, pplan = _photo(sd), sd.get('photo_plan', '') or ''
    if seg == 'saara':
        if photo:
            plan.person.append(f'{rel} story {i} is ಸುದ್ದಿ ಸಾರ but carries a '
                               f'photo — saara never shows one: drop it, or '
                               f'make the story mukhya')
        return
    if seg not in ('mukhya', 'speed'):
        return
    need = 'ಮುಖ್ಯ ಸುದ್ದಿ cannot render without one (IMG-04)' if seg == 'mukhya' \
        else 'optional — ಸ್ಪೀಡ್ ನ್ಯೂಸ್ can run a type-only frame'
    h = picture_hash(sd)
    r = _receipt_current('picture-editor', stem, h, i)
    if r.get('verdict') == 'BLOCK':
        plan.person.append(f'{rel} story {i}: picture desk BLOCKED it — read '
                           f'{os.path.relpath(receipt_path("picture-editor", stem, i), ROOT)}')
        return
    if photo:
        if not r:
            what = ('the generated picture: blind description, no text, no '
                    'face standing in for a named person'
                    if photo.get('nature') == 'ai' else
                    'the editor\'s photograph: crops 4:5 / 9:16, faces of '
                    'minors or victims, blind description')
            plan.add('picture-editor', 'reactive', 2, f'check {what}', rel, story=i)
        return
    if pplan == 'ai':
        if not r:
            plan.add('picture-editor', 'reactive', 2,
                     'the editor said generate — write the single-frame brief, '
                     'then check the result blind', rel, story=i)
    elif pplan == 'real':
        plan.person.append(f'{rel} story {i}: waiting for the editor\'s '
                           f'photograph ({need})')
    else:
        plan.person.append(f'{rel} story {i}: ask the editor — real photo, or '
                           f'generate? Record the answer as photo_plan '
                           f'"real" / "ai" ({need})')


def _load_stories(path: str, stories: list[dict]):
    """Story objects for the mechanical fact pass, one per raw story, or None
    where a story does not validate. Returns (stories, first error)."""
    from .content import Edition, Story
    try:
        return list(Edition.load(path).stories), ''
    except Exception as e:
        err = str(e)[:120] or type(e).__name__
    out = []
    for sd in stories:
        # A story the intake desk has not given a segment yet is still worth
        # a fact pass; the segment is not a fact, so any value will do here.
        probe = sd if sd.get('segment') in SEGMENTS else {**sd, 'segment': 'saara'}
        try:
            out.append(Story.from_dict(probe))
        except Exception:
            out.append(None)
    return out, err


def _edition_tasks(plan: Plan, path: str) -> None:
    from . import factcheck, sourcing
    stem = _stem(path)
    rel = os.path.relpath(path, ROOT)
    with open(path, encoding='utf-8') as fh:
        raw = json.load(fh)
    stories = raw.get('stories', [])
    objs, err = _load_stories(path, stories)
    try:
        claims = factcheck.load_ledger(path)
    except Exception:
        claims = []

    no_segment = [i for i, sd in enumerate(stories, 1)
                  if sd.get('segment', '') not in SEGMENTS]
    if err and not no_segment:
        # A missing segment is the intake desk's work, not a fault to
        # diagnose; anything else that stops the edition loading is.
        plan.add('gate-doctor', 'reactive', 0,
                 f'{rel} does not validate: {err}', rel, urgent=True)
    if no_segment:
        plan.add('intake-editor', 'reactive', 0,
                 f'{len(no_segment)} of {len(stories)} stories have no segment '
                 f'({", ".join(map(str, no_segment[:8]))}) — split the paste, keep '
                 f'each source, propose mukhya / speed / saara', rel)

    if stories and not no_segment:
        # One reach plan for the whole edition, due once every story has a
        # format and again only if a format or category changes (D97).
        eh = edition_hash(raw, strategy_hash)
        if read_receipt('instagram-strategist', stem, 0).get('hash') != eh:
            plan.add('instagram-strategist', 'reactive', 1,
                     'reach plan: format fit, cover hooks, slot, first comment '
                     'and first hour', rel)

    for i, (st, sd) in enumerate(zip(objs, stories), 1):
        fh_ = fact_hash(sd)
        receipt = _receipt_current('fact-checker', stem, fh_, i)
        probs, fr = [], None
        if st is not None:
            try:
                fr = factcheck.check(st, claims, index=i)
                probs = sourcing.source_problems(st)
            except Exception:
                fr = None
        mech_bad = bool(probs) or (fr is not None and (
            fr.blocking or fr.state == 'uncheckable'))
        if mech_bad or not receipt:
            why = (probs[0][1][:90] if probs else
                   'no kept source text for it' if fr is not None and fr.state == 'uncheckable' else
                   'the kept source does not carry the story' if fr is not None and fr.state == 'mismatch' else
                   'a figure is not in the kept source' if fr is not None and fr.figures else
                   'not yet checked in this form')
            plan.add('fact-checker', 'reactive', 1, why, rel, story=i)
        elif receipt.get('verdict') == 'BLOCK':
            plan.person.append(f'{rel} story {i}: fact desk BLOCKED it — read '
                               f'{os.path.relpath(receipt_path("fact-checker", stem, i), ROOT)}')
        if _risky(sd):
            r = _receipt_current('legal-standards', stem, fh_, i)
            if not r:
                plan.add('legal-standards', 'reactive', 1,
                         'crime / death / minor / obituary — read as the '
                         'lawyer for the person named', rel, story=i)
            elif r.get('verdict') == 'BLOCK':
                plan.person.append(f'{rel} story {i}: legal-standards BLOCKED it')
        if sd.get('segment', '') in SEGMENTS:
            if not _receipt_current('kannada-editor', stem, copy_hash(sd), i):
                plan.add('kannada-editor', 'reactive', 2,
                         f'{sd["segment"]} copy not read in this form', rel, story=i)
            _picture_tasks(plan, rel, stem, i, sd)
        if not sd.get('verified_by'):
            plan.person.append(f'{rel} story {i}: open the source, then '
                               f'scripts/verify.py {rel} --story {i} --by "<name>"')


def formats_in(outdir: str) -> dict[str, float]:
    """Each rendered format in a render folder (roundup, saara, mukhya_N) and
    the time of its newest file, _review/ frames included."""
    out: dict[str, float] = {}
    for d in (outdir, os.path.join(outdir, '_review')):
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for n in names:
            m = _FORMAT_FILE.match(n)
            if not m:
                continue
            t = os.path.getmtime(os.path.join(d, n))
            out[m.group(1)] = max(out.get(m.group(1), 0.0), t)
    return out


def _since(agent: str, stem: str, when: float, part: str = '') -> dict:
    r = read_receipt(agent, stem, 0, part)
    try:
        # receipts are stamped to the second; a file written in that same
        # second is not newer than the look that followed it
        ok = datetime.fromisoformat(r['at']).timestamp() >= int(when)
    except (KeyError, ValueError):
        ok = False
    return r if ok else {}


def _package_tasks(plan: Plan, outdir: str) -> None:
    stem = _stem(outdir)
    rel = os.path.relpath(outdir, ROOT)
    rep_path = os.path.join(outdir, 'review_report.json')
    try:
        with open(rep_path, encoding='utf-8') as fh:
            rep = json.load(fh)
    except (OSError, ValueError):
        return
    rendered_at = os.path.getmtime(rep_path)
    fails = [f for f in rep.get('findings', []) if f.get('severity') == 'fail']
    if fails and not _since('gate-doctor', stem, rendered_at):
        codes = sorted({f['code'] for f in fails})
        owners = sorted({CODE_AGENT.get(c.split('-')[0], '?') for c in codes}
                        - {'gate-doctor'})
        # The owners are not launched beside the doctor: it finds the root
        # cause and names them in its receipt; they go in the next wave.
        plan.add('gate-doctor', 'reactive', 3,
                 f'gate HELD on {", ".join(codes)} — names the owners '
                 f'({", ".join(owners) or "none"}) in its receipt', rel, urgent=True)

    for fmt, t in sorted(formats_in(outdir).items()):
        r = _since('package-inspector', stem, t, fmt)
        if not r:
            plan.add('package-inspector', 'reactive', 3,
                     'rendered and not yet looked at, frame by frame', rel,
                     part=fmt)
        elif r.get('verdict') == 'BLOCK':
            plan.person.append(f'{rel} {fmt}: package-inspector BLOCKED a frame — '
                               f'read {os.path.relpath(receipt_path("package-inspector", stem, 0, fmt), ROOT)}')
    # Everything a person will paste somewhere: captions, the WhatsApp
    # community posts and the Facebook group posts (D94).
    captions = [f for pat in ('*_caption.txt', 'whatsapp_*.txt',
                              'facebook_group_*.txt')
                for f in glob.glob(os.path.join(outdir, pat))]
    if captions:
        newest = max(os.path.getmtime(c) for c in captions)
        if not _since('social-writer', stem, newest):
            plan.add('social-writer', 'reactive', 3,
                     f'copy audit — {len(captions)} paste file(s): captions, '
                     f'WhatsApp, Facebook', rel)
    from .review import is_signed
    if not is_signed(outdir) and not fails:
        listen = (', listen to the ಸ್ಪೀಡ್ ನ್ಯೂಸ್ once'
                  if os.path.exists(os.path.join(outdir, 'roundup.mp4')) else '')
        plan.person.append(f'{rel}: look at _review/{listen}, then '
                           f'scripts/sign_off.py {rel} --by "<name>"')


def _corrections_tasks(plan: Plan) -> None:
    from . import corrections
    try:
        late = corrections.overdue()
    except Exception:
        late = {}
    try:
        rows = corrections.current()
    except Exception:
        rows = {}
    if late.get('unacknowledged') or late.get('unresolved'):
        n = len(late.get('unacknowledged', [])) + len(late.get('unresolved', []))
        plan.add('corrections-officer', 'reactive', 0,
                 f'{n} complaint(s) past a statutory clock', urgent=True)
        return
    open_rows = [r for r in rows.values()
                 if r.get('state') not in ('closed', 'published', 'rejected')]
    if open_rows:
        plan.add('corrections-officer', 'reactive', 0,
                 f'{len(open_rows)} open complaint(s) — the clocks are running')
        return
    logged = {str(r.get('about', ''))[:10] for r in rows.values()}
    missing = [d for d in KNOWN_ERRATA if d not in logged]
    if missing:
        plan.add('corrections-officer', 'reactive', 0,
                 f'unsupported claims published {", ".join(missing)} (D84, D88) '
                 f'— no correction logged')


def _ops_tasks(plan: Plan, today: date) -> None:
    """Planning and the machine: weekly, or when something is red. Never in
    the production waves."""
    report = os.path.join(ROOT, 'archive', 'metrics_report.md')
    stale = (not os.path.exists(report) or
             datetime.now().timestamp() - os.path.getmtime(report) > 7 * 86400)
    week_file = os.path.join(ROOT, 'inbox', f'week_{today.isocalendar()[1]:02d}.md')
    if stale and not os.path.exists(week_file):
        plan.add('planning-editor', 'ops', 0,
                 'weekly review due: metrics, what worked, next week',
                 os.path.relpath(week_file, ROOT))

    steward_file = os.path.join(ROOT, 'logs', f'steward_{today.isoformat()}.md')
    if os.path.exists(steward_file):
        return
    recent = False
    for f in glob.glob(os.path.join(ROOT, 'logs', 'steward_*.md')):
        try:
            d = date.fromisoformat(os.path.basename(f)[8:18])
        except ValueError:
            continue
        recent = recent or 0 <= (today - d).days < 7
    reasons = [] if recent else ['weekly check due']
    try:
        import importlib
        h = importlib.import_module('scripts.health')
        for name in ('check_backups', 'check_music', 'check_git'):
            fn = getattr(h, name, None)
            for line in (fn() if fn else []):
                if line.lstrip().startswith('✗'):
                    reasons.append(line.strip().lstrip('✗ ').split('. ')[0][:70])
    except Exception as e:
        reasons.append(f'health check raised {type(e).__name__}')
    if reasons:
        plan.add('systems-steward', 'ops', 0,
                 '; '.join(dict.fromkeys(reasons))[:140],
                 os.path.relpath(steward_file, ROOT))


# ─────────────────────────────────────────────────────────────────────────────
#  THE DESKS ARE NOT OPTIONAL (D95)
#  The first ಸುದ್ದಿ ಸಾರ (2026-09-27) was approved with no desk having read
#  it — the waves were advice, and advice is skipped on a busy morning. Its
#  wording slips and wrong categories are exactly what the Kannada desk and
#  the intake rules exist to catch. These two functions let the gate and the
#  sign-off ask the same question the plan asks, so they cannot disagree.
# ─────────────────────────────────────────────────────────────────────────────

PRE_RENDER_DESKS = ('fact-checker', 'legal-standards', 'kannada-editor',
                    'picture-editor', 'instagram-strategist')
POST_RENDER_DESKS = ('package-inspector', 'social-writer')


def desk_gaps(edition_path: str) -> list[str]:
    """What still has to read this edition, in its CURRENT wording, before it
    may be approved — and any desk that read it and BLOCKED it."""
    p = Plan(day='')
    _edition_tasks(p, edition_path)
    out = [f'{t.agent}{f" story {t.story}" if t.story else ""}: {t.reason}'
           for t in p.tasks if t.agent in PRE_RENDER_DESKS]
    out += [x for x in p.person if 'BLOCKED' in x]
    return out


def inspection_gaps(outdir: str) -> list[str]:
    """What still has to look at the rendered package before a person signs
    it — and any inspector that BLOCKED a frame."""
    p = Plan(day='')
    _package_tasks(p, outdir)
    out = [f'{t.agent}{f" [{t.part}]" if t.part else ""}: {t.reason}'
           for t in p.tasks if t.agent in POST_RENDER_DESKS]
    out += [x for x in p.person if 'BLOCKED' in x]
    return out


def owner_of(outdir: str) -> str:
    """The edition file a render folder was made from (render.py stamps it,
    D90), or '' for a folder rendered before the stamp existed."""
    try:
        with open(os.path.join(outdir, '.edition'), encoding='utf-8') as fh:
            return fh.read().strip()
    except OSError:
        return ''


def plan(day: str | None = None, include_ops: bool = True) -> Plan:
    today = date.fromisoformat(day) if day else date.today()
    p = Plan(today.isoformat())
    eds = _editions_for(p.day)
    if not eds:
        p.person.append(f'no edition for {p.day} yet — paste the day\'s news and '
                        f'say what to make; the intake-editor turns it into '
                        f'editions/{p.day}.json')
    for path in eds:
        _edition_tasks(p, path)
        out = os.path.join(ROOT, 'out', _stem(path))
        if not os.path.isdir(out):
            continue
        owner = owner_of(out)
        rel = os.path.relpath(path, ROOT)
        if owner and owner != rel:
            # D90: the folder is another edition's package.
            p.person.append(f'{os.path.relpath(out, ROOT)} holds {owner}, not '
                            f'{rel}. Move that package, then render {rel}.')
            continue
        _package_tasks(p, out)
    if include_ops:
        _corrections_tasks(p)
        _ops_tasks(p, today)
        _insights_task(p, today)
    return p


INSIGHTS_STALE_DAYS = 8


def _insights_task(p: Plan, today: date) -> None:
    """The editor logs what Instagram Insights shows, weekly (D97).

    Only two posts were ever logged, so every rule in docs/INSTAGRAM.md is a
    hypothesis. Nothing else in the system can fix that; a person has to type
    the numbers in. Asked only once the channel has posted for a while, and
    only when the log has gone quiet."""
    import sqlite3
    db = os.path.join(ROOT, 'archive', 'metrics.db')
    last = None
    try:
        if not os.path.exists(db):      # connect() would create an empty file
            raise sqlite3.Error('no log yet')
        con = sqlite3.connect(db)
        row = con.execute('SELECT MAX(date) FROM posts').fetchone()
        con.close()
        last = date.fromisoformat(row[0]) if row and row[0] else None
    except (sqlite3.Error, ValueError):
        pass
    if last is None or (today - last).days > INSIGHTS_STALE_DAYS:
        since = f'last logged {last.isoformat()}' if last else 'nothing logged yet'
        p.person.append(f'log last week\'s Instagram numbers ({since}): '
                        f'python3 scripts/metrics.py add --date … --asset … '
                        f'--format saara|mukhya|roundup --reach … --saves … '
                        f'--shares … --nonfollowers … — two minutes, and the '
                        f'only way docs/INSTAGRAM.md stops being a guess')


def _run_line(r: dict) -> str:
    where = r['target']
    if r['stories']:
        nums = ','.join(map(str, r['stories']))
        where += f' stor{"ies" if len(r["stories"]) > 1 else "y"} {nums}'
    if r['part']:
        where += f' [{r["part"]}]'
    why = r['reasons'][0] if len(r['reasons']) == 1 else \
        f'{r["reasons"][0]} (+{len(r["reasons"]) - 1} more reasons — it will see them)'
    return f'    {"‼ " if r["urgent"] else ""}{r["agent"]:<20} {where} — {why}'


def _line(t: Task) -> str:
    tgt = t.target + (f' story {t.story}' if t.story else '') + \
        (f' [{t.part}]' if t.part else '')
    flag = '‼ ' if t.urgent else ''
    return f'    {flag}{t.agent:<20} {tgt} — {t.reason}'


def brief(p: Plan, limit: int = 30) -> str:
    """The plan as the team lead reads it: waves, parallel within a wave."""
    if not p.tasks and not p.person and not p.ops:
        return f'Team plan {p.day}: nothing due. Every receipt is current.'
    launches = p.launches()
    n_runs = sum(len(v) for v in launches.values())
    lines = [f'Team plan {p.day} — {len(p.tasks)} production task(s) in {n_runs} '
             f'agent run(s). Launch each wave as ONE message of Agent calls so it '
             f'runs in parallel; ONE agent per line below (a desk reads several '
             f'stories in one run; one inspector per format after render). Each '
             f'agent files a receipt per story with '
             f'`python3 scripts/dispatch.py receipt`.']
    n = 0
    for wave, runs in launches.items():
        lines.append(f'  wave {wave}:')
        for r in runs:
            n += 1
            if n > limit:
                break
            lines.append(_run_line(r))
    if n > limit:
        lines.append(f'    … and {n - limit} more (python3 scripts/dispatch.py)')
    if p.ops:
        lines.append('  ops (not on the production path — run when convenient):')
        lines += [_line(t) for t in p.ops]
    if p.person:
        lines.append('  needs a person (no agent may do these):')
        lines += [f'    · {x}' for x in dict.fromkeys(p.person)][:16]
    return '\n'.join(lines)
