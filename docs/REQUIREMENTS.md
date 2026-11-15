# ಊರ್ಮನಿ ಸುದ್ದಿ — what the system must do, and whether it does

**Measured 2026-11-15** on the newsroom Mac. Written from the code, the contract ([`AGENTS.md`](../AGENTS.md)) and the decisions
([`DECISIONS.md`](DECISIONS.md)); it restates no design value — numbers live in `tokens.Limits` (D56).

Every line says **how it is checked**, so the status is something you can re-run, not something to believe. Three statuses only:

* **Met** — a command or test proves it today.
* **Met, needs a person** — the machine's half is proved; the other half is a person's by design (D59, D62) and no code may do it.
* **Open** — not met. Each one names who can close it.

Re-measure: `python3 -m unittest discover tests` · `python3 scripts/health.py` · `python3 docs/_build_traceability.py`.

## Functional requirements — what it does

| # | The system must… | Checked by | Status |
|---|---|---|---|
| FR-1 | take pasted news and keep each story's own source text | `scripts/intake.py source`; `tests/test_intake.py` | Met |
| FR-2 | refuse a story with no source, and refuse approval with no named person | `Story.validate()` (D55, D59); `tests/test_contract.py` | Met, needs a person — the name comes from the editor |
| FR-3 | state allegations, never verdicts; headline and reel line checked on their own | `Story.validate()` (D29, D109); `tests/legal_corpus.json`, 48 measured phrasings | Met — the guard is a word list; a phrasing it misses is added to the corpus first (D61) |
| FR-4 | check every figure against the kept source, offline | `scripts/fact_check.py` (D84) | Met |
| FR-5 | run one story in exactly one format, and refuse a source already published | `segment`, `DUP-01` (D92); `scripts/intake.py seen` | Met |
| FR-6 | make the three news formats and festival greetings from JSON alone | `render.py --describe`; `tests/test_golden.py` pins the pixels | Met |
| FR-7 | make the daily ಸುದ್ದಿ ಸಾರ reel to the reel standard | [`REEL_STANDARD.md`](REEL_STANDARD.md); `scripts/reel_check.py --strict`; `tests/test_saara_reel*.py` | Met |
| FR-8 | hear the reel's voice back word by word and hold a reel whose town was not said | D146, D147; `SND-09`; `tests/test_ear.py` | Met — depends on a daily listening allowance that resets at 12:30 IST |
| FR-9 | never use a picture without credit and licence; an AI picture only with the editor's name | `Photo.validate()`; `IMG-04`, `IMG-05` (D92) | Met, needs a person |
| FR-10 | gate every package and record what a machine established | `brand/review.py` → `APPROVAL.md` (D52) | Met |
| FR-11 | leave taste, dignity and news judgement to a signed person | `scripts/sign_off.py` (D62) | Met, needs a person |
| FR-12 | write captions, WhatsApp and Facebook copy to platform rules | `brand/copy.py`; `PUB-*`; `tests/test_reach_copy.py` | Met |
| FR-13 | track corrections against the IT Rules clocks | `scripts/correction.py status` | **Open** — the dispatcher lists unsupported claims published 2026-09-23 and 2026-09-24 with no correction logged. Owner: a person, with the corrections desk |
| FR-14 | keep money away from news: labelled products only, every deal cleared by a person | `brand/business.py` (D118); `tests/test_business.py` | Met, needs a person |
| FR-15 | turn a standing instruction into a recorded rule, and refuse one that waives a check | `scripts/house_rule.py` (D73); `tests/test_house.py` | Met |
| FR-16 | tell an AI tool exactly what is wrong with the JSON it wrote | `brand/content.py` shape checks (D150); `tests/test_shape.py` | Met — was Open until today |

## Non-functional requirements — how well it does it

| # | Quality | Requirement | Measured today | Status |
|---|---|---|---|---|
| NFR-1 | Accuracy | every decision is held up by a test, the golden design, or a stated reason it cannot be | 150 decisions: 113 tested, 17 golden-guarded, 2 untestable by design, 18 retired, **0 unenforced** | Met |
| NFR-2 | Accuracy | the design does not move unless someone moves it | `tests/test_golden.py`: same bytes on two renders | Met |
| NFR-3 | Reliability | the whole suite passes | 845 tests, 0 failures, 119 s | Met |
| NFR-4 | Reliability | no daily command ends in a traceback on a bad edition | 240 broken-file runs across 6 commands: 0 tracebacks (was 44 of 76) | Met — D150 |
| NFR-5 | Reliability | a missing tool is named before it costs a render | `health.py` → `tools`, `reel`; `tests/test_health.py` | Met |
| NFR-6 | Speed | the checks an AI runs on every edition answer at once | `render.py --check` 0.3 s · `fact_check.py` 0.2 s · `reel_check.py --strict` 0.8 s · `dispatch.py` 0.2 s | Met |
| NFR-7 | Speed | the sit-down health check is quick enough to be a habit | 9 s (was 41 s) | Met — D150 |
| NFR-8 | Speed | the commit hook is quick enough not to be skipped | quick suites 8 s (was about 40 s) | Met — D150 |
| NFR-9 | Agility | a number changes in one place | `tokens.Limits` (D56); `tests/test_contract.py` | Met |
| NFR-10 | Agility | a new test file is checked from the day it is added, and a slow one is noticed | by exclusion from `tests/slow_suites.txt`; `health.py` names a suite over budget | Met — D150 |
| NFR-11 | Agility | generated files cannot drift from the code | the hook regenerates registry, schemas, `TEMPLATES.md`, `TRACEABILITY.md` | Met |
| NFR-12 | Maintainability | no code that is not used | 20 unused imports removed; every module compiles | Met — imports only; no wider dead-code audit was done |
| NFR-13 | Security | no key in the repository; private books and pasted sources stay off the public remote | pattern scan of tracked and untracked files: none; `.gitignore` covers `business/`, `inbox/`, `archive/` | Met |
| NFR-14 | Security | nothing is written outside the workspace | `path_inside` (D106, D127) | Met |
| NFR-15 | Recoverability | three copies of the work | local backup 0 days old; second copy on iCloud Drive | Met |
| NFR-16 | Recoverability | the offsite copy is current | **13 commits not pushed; 105 files uncommitted** | **Open** — owner's decision; `health.py` shows it red every day until then |
| NFR-17 | Learning | the guessed Instagram numbers are replaced by measured ones | `scripts/metrics.py report`: nothing logged; platform numbers 34 days old | **Open** — needs the owner's numbers; two minutes a week |
| NFR-18 | Portability | the contract passes on a machine that is not the Mac | `.github/workflows/contract.yml`, Python 3.12 and 3.14 | Not re-measured today — CI runs on push, and nothing has been pushed (NFR-16) |

## What "perfect" does not mean here

Three things are open and no code closes them: a correction a person must send (FR-13), a push the owner must say yes to (NFR-16), and numbers
only the owner can read off the apps (NFR-17). A file that called those done would be the kind of claim this project exists to refuse.

Not measured in this pass, so not claimed: a full render of today's reel (there is no edition for 2026-11-15 yet), and how the voice sounds —
that is judged by ear, by a person.
