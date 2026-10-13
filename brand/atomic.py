"""
ಊರ್ಮನಿ ಸುದ್ದಿ — atomic JSON writes
===================================
Every JSON file this system writes — an edition's verification, the sign-off
state, the calendar's review ledger — may be re-read by a person or a script
seconds later. A crash or a kill between `open(..., 'w')` and the last byte
would otherwise leave a truncated file in place of a good one, and a
truncated edition JSON fails as content, not as what it was: a machine that
lost power.

The contract of `write_json`:

  * the target path is either the fully-written new content or the untouched
    old content — never anything in between;
  * a failed write removes its `path + '.part'` temp before re-raising, so a
    dead temp is never mistaken for the real file by anything that globs the
    directory;
  * callers own the formatting (indent, ensure_ascii, trailing newline), so
    each site's bytes stay byte-for-byte what they were before adopting this.
"""
from __future__ import annotations

import json
import os


def write_json(path: str, data, *, indent: int = 2,
               ensure_ascii: bool = False) -> None:
    """Atomically replace `path` with `data` serialised as JSON.

    Writes to `path + '.part'`, flushes and fsyncs, then `os.replace`s over
    the target. If anything raises, the temp is removed and the original
    file is left exactly as it was; the exception propagates (fail loud —
    there is no "mostly written" state worth keeping quiet about).
    """
    tmp = f'{path}.part'
    try:
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, indent=indent, ensure_ascii=ensure_ascii)
            fh.write('\n')
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass                        # already gone, or never created
        raise
