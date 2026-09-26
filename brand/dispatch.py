"""
ಊರ್ಮನಿ ಸುದ್ದಿ — who should be working right now, and why. D89.
===============================================================
Twelve specialist agents live in `.claude/agents/`. An agent nobody remembers
to call is an agent that does not exist, so this module reads the state of
the newsroom — editions, kept sources, gate reports, the calendar, the
complaint clocks, the backups — and says which agents are due, for what, in
which wave. Nothing here calls a model; it is arithmetic over files, so it
is fast enough to run at the start of every session and after every render.

Two kinds of trigger:

  * **Proactive** — something is coming or missing: no edition yet today, a
    festival in three days, no trend sheet, backups going stale, the weekly
    review due.
  * **Reactive** — something happened: the gate failed with a code, a source
    does not carry its story, a crime or death story entered the edition, a
    reader's complaint is running out of clock, a package was rendered and
    nobody has looked at it.

**Receipts.** Every agent files its report with
`python3 scripts/dispatch.py receipt …`, which stamps it with a hash of what
it looked at (the story, minus who verified it). Change the story and the
receipt no longer matches, so the agent is due again; leave it alone and the
work is never repeated. A receipt whose verdict is BLOCK is surfaced to the
person — no agent can clear another agent's block.

Routing of gate codes to agents lives in `CODE_AGENT`, one line per code
family, beside `brand/codes.py :: OWNER` which says the same thing for people.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS_DIR = os.path.join(ROOT, '.claude', 'agents')
RECEIPTS = os.path.join(ROOT, 'inbox', 'receipts')

# Every agent, what kind it is, and the stage it serves. The test suite holds
# this table and `.claude/agents/*.md` to each other.
ROSTER: dict[str, dict] = {
    'news-scout':          {'kind': 'proactive', 'stage': 'intake'},
    'trend-scout':         {'kind': 'proactive', 'stage': 'intake'},
    'planning-editor':     {'kind': 'proactive', 'stage': 'planning'},
    'systems-steward':     {'kind': 'proactive', 'stage': 'operations'},
    'fact-checker':        {'kind': 'reactive',  'stage': 'desk'},
    'legal-standards':     {'kind': 'reactive',  'stage': 'desk'},
    'kannada-editor':      {'kind': 'reactive',  'stage': 'desk'},
    'picture-editor':      {'kind': 'reactive',  'stage': 'picture'},
    'social-writer':       {'kind': 'reactive',  'stage': 'package'},
    'package-inspector':   {'kind': 'reactive',  'stage': 'package'},
    'gate-doctor':         {'kind': 'reactive',  'stage': 'gate'},
    'corrections-officer': {'kind': 'reactive',  'stage': 'after'},
}

# A failing gate code, routed to the agent that can do the work. People are
# routed by brand/codes.py :: OWNER; this is the same map for the team.
CODE_AGENT = {
    'FACT': 'fact-checker', 'SRC': 'fact-checker', 'LAW': 'legal-standards',
    'IMG': 'picture-editor', 'TYPE': 'package-inspector',
    'SND': 'kannada-editor', 'VID': 'package-inspector', 'PKG': 'gate-doctor',
    'PUB': 'social-writer', 'OPS': 'systems-steward',
}

# Stories a legal eye reads before anyone else polishes them.
RISK_WORDS = ('ಸಾವು', 'ಮೃತ', 'ಆತ್ಮಹತ್ಯೆ', 'ಕೊಲೆ', 'ಅತ್ಯಾಚಾರ', 'ಬಂಧನ', 'ಆರೋಪ',
              'ಶವ', 'ಬಾಲಕ', 'ಬಾಲಕಿ', 'ಅಪ್ರಾಪ್ತ', 'ನಿಧನ')

# Verification fields change when a person signs; the story itself has not.
_VOLATILE = {'verified_by', 'verified_at'}


@dataclass
class Task:
    agent: str
    kind: str          # proactive | reactive
    wave: int          # 0 first; tasks in one wave run in parallel
    reason: str
    target: str = ''   # edition path, "edition#3", out dir, or ''
    story: int = 0
    urgent: bool = False


@dataclass
class Plan:
    day: str
    tasks: list[Task] = field(default_factory=list)
    person: list[str] = field(default_factory=list)   # only a human can do these

    def add(self, *a, **kw):
        t = Task(*a, **kw)
        key = (t.agent, t.target, t.story)
        if key not in {(x.agent, x.target, x.story) for x in self.tasks}:
            self.tasks.append(t)

    def waves(self) -> dict[int, list[Task]]:
        out: dict[int, list[Task]] = {}
        for t in sorted(self.tasks, key=lambda t: (t.wave, not t.urgent, t.agent)):
            out.setdefault(t.wave, []).append(t)
        return out

    def to_dict(self) -> dict:
        return {'day': self.day, 'tasks': [asdict(t) for t in self.tasks],
                'person': self.person}


# ─────────────────────────────────────────────────────────────────────────────
#  RECEIPTS
# ─────────────────────────────────────────────────────────────────────────────

def story_hash(story: dict) -> str:
    body = {k: v for k, v in story.items() if k not in _VOLATILE}
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]


def edition_hash(edition: dict) -> str:
    return hashlib.sha1(''.join(story_hash(s) for s in edition.get('stories', []))
                        .encode()).hexdigest()[:12]


def _stem(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def receipt_path(agent: str, stem: str, story: int = 0) -> str:
    name = f'{agent}-{story}.md' if story else f'{agent}.md'
    return os.path.join(RECEIPTS, stem, name)


_HEAD = re.compile(r'<!-- receipt (.*?) -->')


def read_receipt(agent: str, stem: str, story: int = 0) -> dict:
    try:
        with open(receipt_path(agent, stem, story), encoding='utf-8') as fh:
            m = _HEAD.search(fh.readline())
    except OSError:
        return {}
    if not m:
        return {}
    return dict(kv.split('=', 1) for kv in m.group(1).split() if '=' in kv)


def write_receipt(agent: str, edition_path: str, verdict: str, body: str,
                  story: int = 0) -> str:
    """File an agent's report, stamped with a hash of what it looked at."""
    if agent not in ROSTER:
        raise ValueError(f'unknown agent {agent!r}; roster: {sorted(ROSTER)}')
    verdict = verdict.upper()
    if verdict not in ('PASS', 'FIX', 'BLOCK', 'HELD', 'DONE'):
        raise ValueError('verdict is PASS, FIX, BLOCK, HELD or DONE')
    stem, h = _stem(edition_path), ''
    if edition_path.endswith('.json') and os.path.exists(edition_path):
        with open(edition_path, encoding='utf-8') as fh:
            ed = json.load(fh)
        stories = ed.get('stories', [])
        if story:
            if not 1 <= story <= len(stories):
                raise ValueError(f'story {story} is not in {edition_path}')
            h = story_hash(stories[story - 1])
        else:
            h = edition_hash(ed)
    path = receipt_path(agent, stem, story)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    head = (f'<!-- receipt agent={agent} story={story} hash={h or "-"} '
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

def _editions_for(day: str) -> list[str]:
    return sorted(p for p in glob.glob(os.path.join(ROOT, 'editions', f'{day}*.json')))


def _risky(st: dict) -> bool:
    if st.get('category') in ('crime', 'obituary') or st.get('involves_minor') \
            or st.get('sexual_offence'):
        return True
    text = ' '.join(filter(None, [st.get('headline', ''), st.get('deck', ''),
                                  *st.get('points', [])]))
    return any(w in text for w in RISK_WORDS)


def _edition_tasks(plan: Plan, path: str) -> None:
    from .content import Edition
    from . import factcheck, sourcing
    stem = _stem(path)
    rel = os.path.relpath(path, ROOT)
    with open(path, encoding='utf-8') as fh:
        raw = json.load(fh)
    stories = raw.get('stories', [])
    try:
        ed = Edition.load(path)
    except Exception as e:
        plan.add('gate-doctor', 'reactive', 0,
                 f'{rel} does not validate: {str(e)[:120]}', rel, urgent=True)
        return
    claims = factcheck.load_ledger()
    rendered = os.path.isdir(os.path.join(ROOT, 'out', stem))

    all_pass = True
    for i, (st, sd) in enumerate(zip(ed.stories, stories), 1):
        h = story_hash(sd)
        fr = factcheck.check(st, claims, index=i)
        probs = sourcing.source_problems(st)
        receipt = _receipt_current('fact-checker', stem, h, i)
        if probs or fr.blocking or fr.state == 'uncheckable' or not receipt:
            all_pass = False
            why = (probs[0][1][:90] if probs else
                   'a figure is not in the source' if fr.figures else
                   'the source does not carry the story' if fr.state == 'mismatch' else
                   'no source text held' if fr.state == 'uncheckable' else
                   'not yet checked in this form')
            plan.add('fact-checker', 'reactive', 1, why, rel, story=i)
        elif receipt.get('verdict') == 'BLOCK':
            all_pass = False
            plan.person.append(f'{rel} story {i}: fact desk BLOCKED it — '
                               f'read {os.path.relpath(receipt_path("fact-checker", stem, i), ROOT)}')
        if _risky(sd):
            r = _receipt_current('legal-standards', stem, h, i)
            if not r:
                plan.add('legal-standards', 'reactive', 1,
                         'crime / death / minor / obituary — read as the '
                         'lawyer for the person named', rel, story=i)
            elif r.get('verdict') == 'BLOCK':
                plan.person.append(f'{rel} story {i}: legal-standards BLOCKED it')
        if not sd.get('photo'):
            plan.add('picture-editor', 'reactive', 2,
                     'no photograph; every carousel slide needs one (IMG-04)',
                     rel, story=i)
        if not sd.get('verified_by'):
            plan.person.append(f'{rel} story {i}: open the source, then '
                               f'scripts/verify.py {rel} --story {i} --by "<name>"')

    eh = edition_hash(raw)
    if not rendered:
        if not _receipt_current('kannada-editor', stem, eh):
            plan.add('kannada-editor', 'reactive', 2,
                     'copy has changed since its last Kannada read', rel)
        if all_pass and not _receipt_current('social-writer', stem, eh):
            plan.add('social-writer', 'reactive', 2,
                     'facts passed — hooks, reel lines, titles', rel)


def _package_tasks(plan: Plan, outdir: str) -> None:
    stem = os.path.basename(outdir)
    rel = os.path.relpath(outdir, ROOT)
    rep_path = os.path.join(outdir, 'review_report.json')
    try:
        with open(rep_path, encoding='utf-8') as fh:
            rep = json.load(fh)
    except (OSError, ValueError):
        return
    fails = [f for f in rep.get('findings', []) if f.get('severity') == 'fail']
    if fails:
        codes = sorted({f['code'] for f in fails})
        plan.add('gate-doctor', 'reactive', 3,
                 f'gate HELD on {", ".join(codes)}', rel, urgent=True)
        for c in codes:
            agent = CODE_AGENT.get(c.split('-')[0])
            if agent and agent != 'gate-doctor':
                plan.add(agent, 'reactive', 3, f'owns {c} on the held gate', rel)
    rendered_at = os.path.getmtime(rep_path)

    def since_render(agent: str) -> bool:
        r = read_receipt(agent, stem)
        return bool(r.get('at')) and \
            datetime.fromisoformat(r['at']).timestamp() >= rendered_at

    if not since_render('package-inspector'):
        plan.add('package-inspector', 'reactive', 3,
                 'rendered and not yet looked at, frame by frame', rel)
    elif read_receipt('package-inspector', stem).get('verdict') == 'BLOCK':
        plan.person.append(f'{rel}: package-inspector BLOCKED a frame — read '
                           f'{os.path.relpath(receipt_path("package-inspector", stem), ROOT)}')
    if not since_render('social-writer'):
        plan.add('social-writer', 'reactive', 3,
                 'post-render caption audit', rel)
    if not os.path.exists(os.path.join(outdir, 'SIGNOFF.json')) and not fails:
        plan.person.append(f'{rel}: look at _review/, listen to one reel, then '
                           f'scripts/sign_off.py {rel} --by "<name>"')


def _calendar_tasks(plan: Plan, today: date) -> None:
    try:
        import importlib
        wo = importlib.import_module('scripts.whats_on')
        dated, lunar, seasons = wo.upcoming(7)
    except Exception:
        return
    soon = [o for _, d, o in dated if d <= 3] + [o for _, d, o in lunar if d <= 7]
    starting = [s for _, d, s, st in seasons if st == 'starts' and d <= 3]
    plan_file = os.path.join(ROOT, 'inbox', f'plan_{today.isoformat()}.md')
    if (soon or starting) and not os.path.exists(plan_file):
        names = [o.get('name_en') or o.get('name') or o.get('id', '?')
                 for o in soon + starting]
        plan.add('planning-editor', 'proactive', 0,
                 'coming up: ' + ', '.join(str(n) for n in names[:4]),
                 os.path.relpath(plan_file, ROOT))
    report = os.path.join(ROOT, 'archive', 'metrics_report.md')
    stale = (not os.path.exists(report) or
             datetime.now().timestamp() - os.path.getmtime(report) > 7 * 86400)
    week_file = os.path.join(ROOT, 'inbox', f'week_{today.isocalendar()[1]:02d}.md')
    if stale and not os.path.exists(week_file):
        plan.add('planning-editor', 'proactive', 0,
                 'weekly review due: metrics, what worked, next week',
                 os.path.relpath(week_file, ROOT))


def _ops_tasks(plan: Plan, today: date) -> None:
    from . import corrections
    try:
        late = corrections.overdue()
    except Exception:
        late = {}
    if late.get('unacknowledged') or late.get('unresolved'):
        n = len(late.get('unacknowledged', [])) + len(late.get('unresolved', []))
        plan.add('corrections-officer', 'reactive', 0,
                 f'{n} complaint(s) past a statutory clock', urgent=True)
    else:
        try:
            open_rows = [r for r in corrections.current().values()
                         if r.get('state') not in ('closed', 'published', 'rejected')]
        except Exception:
            open_rows = []
        if open_rows:
            plan.add('corrections-officer', 'reactive', 0,
                     f'{len(open_rows)} open complaint(s) — the clocks are running')
    steward_file = os.path.join(ROOT, 'logs', f'steward_{today.isoformat()}.md')
    if os.path.exists(steward_file):
        return
    reasons = []
    try:
        import importlib
        h = importlib.import_module('scripts.health')
        for fn in (h.check_fetch, h.check_backups, h.check_music, h.check_git):
            for line in fn():
                if line.lstrip().startswith(('✗', '!')):
                    reasons.append(line.strip().lstrip('✗! ').split(' — ')[0])
    except Exception as e:
        reasons.append(f'health check raised {type(e).__name__}')
    if reasons:
        plan.add('systems-steward', 'proactive', 0,
                 '; '.join(dict.fromkeys(reasons))[:140],
                 os.path.relpath(steward_file, ROOT))


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
        p.add('news-scout', 'proactive', 0,
              f'no edition for {p.day} yet — find today\'s coastal news',
              f'editions/{p.day}.json')
    from . import trends
    if not os.path.exists(trends.path_for(p.day)) or not \
            _receipt_current('trend-scout', p.day, '-'):
        p.add('trend-scout', 'proactive', 0 if not eds else 1,
              'today\'s trend sheet has not been scouted', f'inbox/trends_{p.day}.json')
    for path in eds:
        _edition_tasks(p, path)
        out = os.path.join(ROOT, 'out', _stem(path))
        if not os.path.isdir(out):
            continue
        owner = owner_of(out)
        rel = os.path.relpath(path, ROOT)
        if owner and owner != rel:
            # D90: the folder is another edition's package. Inspecting it
            # "for" this edition is how an explainer got checked as the news.
            p.person.append(f'{os.path.relpath(out, ROOT)} holds {owner}, not '
                            f'{rel}. Move that package, then render {rel}.')
            continue
        _package_tasks(p, out)
    _calendar_tasks(p, today)
    if include_ops:
        _ops_tasks(p, today)
    return p


def brief(p: Plan, limit: int = 30) -> str:
    """The plan as the team lead reads it: waves, parallel within a wave."""
    if not p.tasks and not p.person:
        return f'Team plan {p.day}: nothing due. Every receipt is current.'
    lines = [f'Team plan {p.day} — {len(p.tasks)} agent task(s). Launch each '
             f'wave as ONE message of Agent calls so it runs in parallel; one '
             f'agent per story. Each agent files its report with '
             f'`python3 scripts/dispatch.py receipt`.']
    n = 0
    for wave, tasks in p.waves().items():
        lines.append(f'  wave {wave}:')
        for t in tasks:
            n += 1
            if n > limit:
                break
            tgt = f'{t.target} story {t.story}' if t.story else t.target
            flag = '‼ ' if t.urgent else ''
            lines.append(f'    {flag}{t.agent:<20} [{t.kind}] {tgt} — {t.reason}')
    if n > limit:
        lines.append(f'    … and {n - limit} more (python3 scripts/dispatch.py)')
    if p.person:
        lines.append('  needs a person (no agent may do these):')
        lines += [f'    · {x}' for x in dict.fromkeys(p.person)][:12]
    return '\n'.join(lines)
