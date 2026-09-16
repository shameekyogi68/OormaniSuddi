# ಊರ್ಮನಿ ಸುದ್ದಿ — orientation for Claude Code

**Read [`AGENTS.md`](AGENTS.md) first. It is short and it is the contract.**
This file is a pointer, deliberately: anything restated here would drift from
the real document, and drift is the failure mode this whole project is built to
prevent.

Then, depending on the job:

| You are about to… | Read |
|---|---|
| feed the system news copy | [`docs/AI_BRIEF.md`](docs/AI_BRIEF.md) then [`.agents/skills/second-brain/SKILL.md`](.agents/skills/second-brain/SKILL.md) — four stops, not thirteen |
| change a design value | [`STANDARDS.md`](STANDARDS.md), then [`docs/DECISIONS.md`](docs/DECISIONS.md) |
| pick a template | `python3 render.py --describe` |
| run a day end to end | [`docs/RUNBOOK.md`](docs/RUNBOOK.md) |
| edit raw clips into a long-format YouTube video | [`.claude/skills/youtube-longform-edit/SKILL.md`](.claude/skills/youtube-longform-edit/SKILL.md) |
| edit raw clips into an Instagram Reel / YouTube Short | [`.claude/skills/reels-shorts-edit/SKILL.md`](.claude/skills/reels-shorts-edit/SKILL.md) |

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
  DECISIONS.md D66 (why it is a scene) and D28 (why its variation is seeded
  from a stable digest and never from `hash()`).
* **`out/reference/` is tracked while the rest of `out/` is ignored.** It is the
  visual baseline, not a build artifact.
* **Warnings on a clean render.** `preflight()` warns; it does not block. A
  missing `reel_line` on a long headline is a real note worth acting on.
* **A green `APPROVAL.md` that still says "not yet cleared to publish".** That
  is correct. The file records what a *machine* established. Taste, cultural
  dignity and news judgement are signed by a person —
  `python3 scripts/sign_off.py out/<date> --by "<name>"`. See D62.
* **The broadsheet saving at a lower JPEG quality than everything else.** It is
  fitted to `Limits.forward_target_kb`, because its job is to be forwarded on
  mobile data, not to be pixel-peeped. See D60.

## Things that are genuinely load-bearing

* **Strict Workspace Isolation**: All actions, file operations, searches, and
  process executions are strictly jailed within this repository. Never read,
  write, or execute outside `/Users/shameekyogi/My Apps/Oormani Suddi`.
* `Story.validate()` enforces Indian criminal-reporting law, not house style.
  `headline` and `reel_line` are checked for guilt assertion **on their own**,
  because each is displayed with no other copy around it. Never add an override
  flag — see DECISIONS.md D29 for why, and what was published before it existed.
  The guard is a word list, and `tests/legal_corpus.json` is the measurement of
  what it catches — when you find a phrasing it misses, add the row **first**,
  watch it fail, then widen the list. See D61.
* **No source, no claim. No human verification, no publication.** A story needs
  a `source_url` to render (D55) and a `verified_by` to be approved (D59). The
  second one is not inferrable from `status`: "confirmed" is what the card says
  about the news, and a model can write that.
* **Numbers live in `tokens.Limits`, once.** Durations, character budgets,
  loudness, slots, contrast floors. Skills and docs quote those names; they do
  not restate the values. See D56.

## When the user asks for a change

Route it before you do it — `python3 scripts/house_rule.py where "…"`. A number
goes to `tokens.Limits`, a legal rule to `brand/content.py`, a place to
`copy.PLACE_TAGS`, everything else to a house rule. Then record it, and tell
them where it went and what its id is. An instruction that only applied to
today was a waste of both your time. D73.

Never write a house rule that waives a check. `add()` refuses it, and it is
right to.

## Numbers you can measure

```bash
python3 docs/_build_traceability.py     # which decisions are enforced by a test
python3 scripts/metrics.py report       # which of the guessed numbers hold up
python3 scripts/correction.py status    # the IT Rules clocks
python3 scripts/house_rule.py list      # standing instructions in force
```

Regenerate derived files after touching the registry, categories, or Story
fields — they cannot be edited by hand:

```bash
python3 -m templates --dump && python3 schemas/_build.py && python3 docs/_build_templates_md.py && python3 docs/_build_traceability.py
```
