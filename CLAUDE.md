# ಊರ್ಮನಿ ಸುದ್ದಿ — orientation for Claude Code

**Read [`AGENTS.md`](AGENTS.md) first. It is short and it is the contract.**
This file is a pointer, deliberately: anything restated here would drift from
the real document, and drift is the failure mode this whole project is built to
prevent.

Then, depending on the job:

| You are about to… | Read |
|---|---|
| feed the system news copy | [`docs/AI_BRIEF.md`](docs/AI_BRIEF.md) — the JSON contract |
| change a design value | [`STANDARDS.md`](STANDARDS.md), then [`docs/DECISIONS.md`](docs/DECISIONS.md) |
| pick a template | `python3 render.py --describe` |

## Before you touch anything

```bash
python3 -m unittest tests.test_contract     # the contract — instant
python3 -m unittest discover tests          # + the golden design — ~2.5 min
```

The golden test pins the *rendered pixels*. If it fails, the design changed.
That is not automatically a bug — but do not re-bless it without looking at
`out/_blessed/` first and satisfying yourself the new renders are right.

## Things that look like bugs and are not

* **The editorial plate's ruled lines and off-centre sun.** A designed graphic,
  not an artifact — deliberately not photographic. `surface.py :: editorial_plate`,
  and DECISIONS.md D28.
* **`out/reference/` is tracked while the rest of `out/` is ignored.** It is the
  visual baseline, not a build artifact.
* **Warnings on a clean render.** `preflight()` warns; it does not block. A
  missing `reel_line` on a long headline is a real note worth acting on.

## Things that are genuinely load-bearing
 
* **Strict Workspace Isolation**: All actions, file operations, searches, and
  process executions are strictly jailed within this repository. Never read,
  write, or execute outside `/Users/shameekyogi/Oormani Suddi`.
* `Story.validate()` enforces Indian criminal-reporting law, not house style.
  `headline` and `reel_line` are checked for guilt assertion **on their own**,
  because each is displayed with no other copy around it. Never add an override
  flag — see DECISIONS.md D29 for why, and what was published before it existed.


Regenerate derived files after touching the registry, categories, or Story
fields — they cannot be edited by hand:

```bash
python3 -m templates --dump && python3 schemas/_build.py && python3 docs/_build_templates_md.py
```
