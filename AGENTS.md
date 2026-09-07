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

## Six rules that override anything you might infer

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
   The `headline` and `reel_line` are checked **on their own**: they travel
   without the rest of the story, so each must carry its own ಆರೋಪ / ಆರೋಪಿ /
   ಶಂಕಿತ. A qualifier in the deck does not cover a headline.
5. **Keep `tokens.Brand.grievance_officer` and `grievance_email` filled in.**
   IT Rules 2021 Part III requires a news publisher to name a Grievance Officer
   and publish contact details. Both are set; `compliance()` warns on every run
   if either is ever cleared, and no card or caption carries the line without
   them.
6. **Strict Workspace Isolation & AI Boundary Containment.** This repository is an
   isolated environment. No AI model, agent, subagent, script, or automated tool
   shall ever read, write, execute commands in, inspect, or operate outside this
   project folder (`/Users/shameekyogi/Oormani Suddi`). All task execution, file
   access, and shell contexts are strictly confined within this directory. Cross-project
   access or path traversal outside this perimeter is prohibited and must fail-closed.


---

## Standard Publishing Workflow: Carousel + Individual Reels (10x Reach)

Whenever raw news copy is provided for a bulletin:
1. **Flawless Kannada Copy**: Natural, concise, grammatically verified Kannada. Numbers must always use Latin numerals (`25`, `29.6`), never Kannada numerals (`೨೫`). Headlines stay under 78 characters; punchy `reel_line` under 46 characters. Crime copy must strictly use allegation markers (ಆರೋಪ / ಆರೋಪಿ / ಶಂಕಿತ).
2. **Editorial Images & 10/10 Cultural/Legal Cross-Check**:
   - Generate high-quality photojournalistic hero and multi-scene gallery images using `generate_image`.
   - Every image carries `nature: 'ai'`, `credit: 'AI ಚಿತ್ರ — ಊರ್ಮನಿ ಸುದ್ದಿ'`, `licence: 'own'`, and an honest `caption`.
   - **Mandatory 10/10 Cultural & Legal Cross-Check**: The Visual Culture & Legal Expert inspects every image. Zero tolerance for distortions or mockery of sacred coastal traditions (Yakshagana, Hulivesha, Daivaradhane, temple rituals). Zero minor faces, victim trauma, or gore. Must score a verified 10/10 before layout; otherwise regenerate on loop.
3. **Edition JSON**: Save to `editions/YYYY-MM-DD.json`.
4. **Targeted Deliverables on Demand (Zero Clutter)**:
   - Deliver **ONLY** what the user actually requests (e.g. `--only carousel reel`). Do not waste render time or clutter output with formats not requested (bulletin, broadsheet, individual post cards, etc.).
   - **Carousel** (`carousel_01_cover.jpg` .. `06`) for swipeable daily coverage.
   - **Individual Reels ONLY for 10/10 Reel-Worthy Stories** (`reel_01.mp4`, `reel_02.mp4`, etc.) with their respective cover frames (`reel_*_cover.jpg`).
     - **Short-Form Audience Retention & 10/10 Algorithm Gate**:
       - Only stories scoring 10/10 in visual drama, public urgency, high stakes, or viral regional talkability become reels (`is_reel: true`).
       - Multi-image chapter breakdown (cutting to fresh scene photos every 12–15s) guarantees dynamic visual rhythm without static freezes.
       - The Audience Retention Expert audits the final video (3-second hook, audio ducking, text legibility, living outro). If rating < 10/10, loop back to polish until 10/10 perfection is reached.
5. **Legal, Copyright & YouTube Monetization Guardrails (10/10 Ad-Safe)**:
   - **AdSense Green Dollar Clearance**: Zero depictions of blood, open wounds, gore, or trapped victims in imagery or thumbnails. Sober, objective reporting without sensationalized clickbait.
   - **Content ID & Copyright Shield**: In-house royalty-free music (`assets/news_bgm.mp3`), open/proprietary broadcast SFX (`sfx/`), and verified `own` licenses. Zero risk of copyright claims or audio mutes.
   - **Indian Media Law Compliance**: IT Rules 2021 publisher transparency, POCSO minor privacy protection, Section 228A IPC/BNS victim privacy, and strict allegation markers (*ಆರೋಪ / ಆರೋಪಿ / ಶಂಕಿತ*).
   - The Legal & Monetization Expert audits the full package; zero tolerance for ad-limitation or legal risks.
6. **Complete Copy & Schedule Plan**:
   - The time-scheduled publishing timetable is **generated** — `render.py` writes `schedule.txt` and `schedule.json` from what it actually rendered.
   - Ready-to-copy Instagram captions with First Comments (pinned questions).
   - Ready-to-copy YouTube Shorts Titles (<60 chars, mobile search optimized), Descriptions (with snippet and timestamps), and Tags for every single reel.

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
