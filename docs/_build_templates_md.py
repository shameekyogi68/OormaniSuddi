#!/usr/bin/env python3
"""Generate docs/TEMPLATES.md FROM templates/__init__.py.

Hand-maintained docs drift the moment someone changes a limit and forgets the
table. This one cannot: run it after touching the registry.

    python3 docs/_build_templates_md.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from templates import TEMPLATES
from brand.tokens import FORMATS

HERE = os.path.dirname(os.path.abspath(__file__))

HEAD = """# Templates

Generated from `templates/__init__.py` — do not edit by hand; run
`python3 docs/_build_templates_md.py` instead.

Nine templates. Each is one file in `templates/`, self-contained: no template
imports another, so you can read one without reading the rest.

```python
import templates as TP
TP.render('report_card', story, 'out/card.jpg')     # by name
TP.choose(story)                                     # let it pick
TP.get('report_card').limits                         # the rules, as data
```

Or without Python at all — see [`AI_BRIEF.md`](AI_BRIEF.md):

```bash
python3 render.py edition.json --only report_card carousel
```

## At a glance

| Template | Size | Takes | Use it when |
|---|---|---|---|
"""


def main():
    rows = []
    for k, s in TEMPLATES.items():
        when = s.when.split('.')[0] + '.'
        rows.append(f'| [`{k}`](#{k.replace("_", "-")}) | {s.size[0]}×{s.size[1]} '
                    f'| {s.takes} | {when} |')

    body = [HEAD + '\n'.join(rows) + '\n']

    for k, s in TEMPLATES.items():
        f = FORMATS[s.format]
        body.append(f"""
---

## `{k}`

{s.summary}

**When to use.** {s.when}

| | |
|---|---|
| file | `templates/{s.module}.py` → `{s.entry}()` |
| takes | a `{s.takes.capitalize()}` |
| output | {s.size[0]}×{s.size[1]} at {f.ss}× supersample, {s.produces} |
| safe inset | {f.safe[0]}, {f.safe[1]}, {f.safe[2]}, {f.safe[3]} (L, T, R, B) |
| format note | {f.note} |

**Requires.** `{'`, `'.join(s.requires)}`

**Also accepts.** {('`' + '`, `'.join(s.accepts) + '`') if s.accepts else '—'}

**Limits.** {', '.join(f'`{a}` = {b}' for a, b in s.limits.items()) if s.limits else '—'}
""" + (f'\n**Note.** {s.notes}\n' if s.notes else ''))

    body.append("""
---

## Adding one

1. Write `templates/<name>.py`. Take every colour, size and margin from
   `brand.tokens`; build from `brand.components`, not raw `ImageDraw`.
2. Flow the content, do not position it — see [`../STANDARDS.md`](../STANDARDS.md) §6.
3. Respect the format's safe inset.
4. Finish with `grain(sf, Grade.grain, Grade.grain_shadow_bias)`.
5. Add a `Spec` to `templates/__init__.py`.
6. Regenerate: `python3 -m templates --dump && python3 docs/_build_templates_md.py`
7. Add a golden case in `tests/test_golden.py` so the design is pinned.
""")

    p = os.path.join(HERE, 'TEMPLATES.md')
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write(''.join(body))
    print('wrote docs/TEMPLATES.md')


if __name__ == '__main__':
    main()
