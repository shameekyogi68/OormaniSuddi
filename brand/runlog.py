"""
ಊರ್ಮನಿ ಸುದ್ದಿ — The run log, and the lock
=========================================
Two small things that the 8 GB M1 makes necessary rather than nice.

**The log.** When a render fails at 07:40 the useful question is which step,
how long it had been going, and what it was carrying. Scrollback answers none
of those an hour later, and re-running to find out costs the morning. Each step
writes one JSON line to `out/{date}/build.log`, and `run_report()` turns the
day into something readable at a glance.

**The lock.** Two `render.py` runs, or a render and a footage build, on eight
gigabytes of unified memory is how macOS starts swapping and a three-minute
master becomes indefinite. The lock is advisory and stale-tolerant: it refuses
a second heavy job while one is genuinely running, and never leaves a dead
process blocking tomorrow.
"""
from __future__ import annotations

import errno
import json
import os
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK = os.path.join(ROOT, '.render.lock')
STALE_AFTER = 4 * 3600      # a render that has run four hours is not running


# ─────────────────────────────────────────────────────────────────────────────
#  THE LOG
# ─────────────────────────────────────────────────────────────────────────────

class RunLog:
    """One JSON line per step. Never raises — a log that can fail a render is
    worse than no log."""

    def __init__(self, outdir: str, name: str = 'build.log'):
        self.path = os.path.join(outdir, name)
        self.t0 = time.time()
        self.rows: list[dict] = []
        try:
            os.makedirs(outdir, exist_ok=True)
            # Fresh file per run: an appended log across three re-renders is a
            # log nobody reads.
            open(self.path, 'w', encoding='utf-8').close()
        except OSError:
            self.path = ''

    def event(self, step: str, status: str = 'ok', **fields) -> None:
        row = {'t': round(time.time() - self.t0, 2), 'step': step,
               'status': status, **fields}
        self.rows.append(row)
        if not self.path:
            return
        try:
            with open(self.path, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + '\n')
        except OSError:
            pass

    def start(self, step: str, **fields) -> None:
        self.event(step, 'start', **fields)

    def done(self, step: str, **fields) -> None:
        self.event(step, 'ok', **fields)

    def warn(self, step: str, why: str, **fields) -> None:
        self.event(step, 'warn', why=why, **fields)

    def fail(self, step: str, why: str, **fields) -> None:
        self.event(step, 'fail', why=why, **fields)

    @property
    def elapsed(self) -> float:
        return time.time() - self.t0

    def report(self, outdir: str, extra: list[str] | None = None) -> str:
        """A page a tired person can read down at 07:40."""
        lines = [
            '# Build report',
            '',
            f'Ran {self.elapsed:.0f}s · {len(self.rows)} events · '
            f'`{os.path.basename(self.path) or "no log"}`',
            '',
        ]
        fails = [r for r in self.rows if r['status'] == 'fail']
        warns = [r for r in self.rows if r['status'] == 'warn']
        if fails:
            lines += ['## Failed', '']
            lines += [f'- **{r["step"]}** — {r.get("why", "")}' for r in fails]
            lines += ['']
        if warns:
            lines += ['## Warned', '']
            lines += [f'- {r["step"]} — {r.get("why", "")}' for r in warns]
            lines += ['']
        # The slowest steps, because on this machine that is the actionable fact.
        timed = [r for r in self.rows if 'seconds' in r]
        if timed:
            lines += ['## Where the time went', '']
            for r in sorted(timed, key=lambda x: -x['seconds'])[:8]:
                lines.append(f'- {r["step"]}: {r["seconds"]:.0f}s')
            lines += ['']
        if extra:
            lines += extra + ['']
        lines += ['## Timeline', '', '```']
        for r in self.rows:
            mark = {'ok': '·', 'start': '▸', 'warn': '!', 'fail': '✗'}.get(
                r['status'], '·')
            detail = ' '.join(f'{k}={v}' for k, v in r.items()
                              if k not in ('t', 'step', 'status'))
            lines.append(f'{r["t"]:7.1f}s {mark} {r["step"]:<28} {detail}')
        lines += ['```', '']
        path = os.path.join(outdir, 'run_report.md')
        try:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write('\n'.join(lines))
        except OSError:
            return ''
        return path


# ─────────────────────────────────────────────────────────────────────────────
#  THE LOCK
# ─────────────────────────────────────────────────────────────────────────────

def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError as e:
        return e.errno == errno.EPERM
    return True


def lock_holder() -> dict | None:
    """Who holds the render lock, or None if it is free or stale."""
    if not os.path.exists(LOCK):
        return None
    try:
        with open(LOCK, encoding='utf-8') as fh:
            row = json.load(fh)
    except Exception:
        return None
    pid = int(row.get('pid', 0))
    age = time.time() - float(row.get('at', 0))
    if not pid or not _alive(pid) or age > STALE_AFTER:
        return None
    return row


def acquire(what: str) -> bool:
    """Take the heavy-job lock. False when someone else genuinely holds it."""
    holder = lock_holder()
    if holder:
        return False
    try:
        with open(LOCK, 'w', encoding='utf-8') as fh:
            json.dump({'pid': os.getpid(), 'at': time.time(), 'what': what}, fh)
    except OSError:
        return True      # a lock we cannot write must not stop a render
    return True


def release() -> None:
    holder = lock_holder()
    if holder and int(holder.get('pid', 0)) != os.getpid():
        return           # never clear someone else's lock
    try:
        os.remove(LOCK)
    except OSError:
        pass
