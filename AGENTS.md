# 🌾 ಊರ್ಮನಿ ಸುದ್ದಿ (Oormani Suddi)

> **Brand**: ಊರ್ಮನಿ ಸುದ್ದಿ · **Tagline**: ನಮ್ಮ ಊರು • ನಮ್ಮ ಧ್ವನಿ
> **Handle**: `@OormaniSuddi`
> **Coverage**: ಕರಾವಳಿ — coastal Karnataka. One word, set in `tokens.Brand.coverage`.

---

## Start here

**If you are an AI tool being handed news copy → read
[`docs/AI_BRIEF.md`](docs/AI_BRIEF.md) and nothing else first.** It is written
for you: the JSON contract, how to choose a template, the hard limits, and what
will be rejected.

**If you are a human working on the design → read
[`STANDARDS.md`](STANDARDS.md)**, then [`docs/DECISIONS.md`](docs/DECISIONS.md)
before changing any value.

---

## Doing the work

```bash
python3 render.py editions/2026-08-25.json      # a full package from JSON
python3 render.py --describe                    # every template + its rules
python3 render.py --schema story                # the input contract
python3 render.py --check my.json               # validate, render nothing
python3 -m unittest tests.test_contract         # the contract (instant)
python3 -m unittest discover tests              # + the golden design (~2 min)
```

Content is JSON in `editions/`. Copy `editions/2026-08-25.json`. You never write
rendering code — nine finished templates already exist.

---

## Three rules that override anything you might infer

1. **`Story.validate()` is not negotiable.** Every photograph carries a credit
   and declares whether it shows the actual scene. Every story names a source.
   ಬ್ರೇಕಿಂಗ್ is computed from the publish timestamp, never asserted. Do not add
   an override flag — it will be used on a deadline, and then the whole system
   is decoration.
2. **If there is no honest picture, omit `photo`** and let the story take
   `text_card`. Never a stock photo that only decorates. Illustrating a
   Brahmāvara story with a highway bridge signposted HONNAVAR is the exact
   failure this system exists to prevent.
3. **Restraint.** One accent (gold), hairlines not borders, square corners, no
   frame around the canvas, no outlined boxes.
4. **Crime copy states allegations, never verdicts** — and every photograph
   carries a licence, not just a credit. Both are enforced by
   `Story.validate()`; see [`docs/DECISIONS.md`](docs/DECISIONS.md) D29–D30.
5. **Fill in `tokens.Brand.grievance_officer` and `grievance_email`.** IT Rules
   2021 Part III requires a news publisher to name a Grievance Officer and
   publish contact details. Until they are set, no card or caption carries them
   and preflight warns on every run.

---

## Layout of the project

```
render.py           JSON in, finished design out — the entry point
editions/*.json     the content; one file per day's bulletin

templates/          nine templates, one file each, none importing another
  __init__.py         the registry: what each takes, its limits, when to use it
  registry.json       the same table, machine-readable
brand/              the engine — read STANDARDS.md before changing any of it
  tokens.py           colour, type scale, grid, formats, motion constants
  typo.py             Kannada-safe text engine (baselines, wrapping, fitting)
  surface.py          canvas, house photo grade, scrims, grain, hairlines
  components.py       masthead, eyebrow, fact list, provenance, footer
  content.py          Story / Photo / Edition, the contract, the clock,
                      and the India criminal-reporting guards
  copy.py             captions, hashtags, YouTube metadata, alt text
  motion.py           the reel engine
  qa.py               preflight and output audit
schemas/            JSON Schema for the input, generated from the code
docs/
  AI_BRIEF.md         ← for a tool generating content
  TEMPLATES.md        per-template reference, generated from the registry
  DECISIONS.md        why each rule exists, and what breaks without it
tests/              the contract, and golden hashes pinning the design
examples/           the Python API, if you prefer it to JSON
assets/  fonts/  sfx/    logo master + derivatives, the four faces, broadcast hits
out/                rendered deliverables
```

`assets/logo.png` is the **master** logo — the RGB original that
`logo_clean_circle.png` and `logo_clean_card.png` were cut from. Do not delete it.

## Regenerating the generated files

```bash
python3 -m templates --dump              # templates/registry.json
python3 schemas/_build.py                # schemas/*.json
python3 docs/_build_templates_md.py      # docs/TEMPLATES.md
```

These are derived from code so they cannot drift. Run them after touching the
registry, the category list, or the Story fields.
