# 🌾 ಊರ್ಮನಿ ಸುದ್ದಿ (Oormani Suddi)

> **Brand**: ಊರ್ಮನಿ ಸುದ್ದಿ · **Tagline**: ನಮ್ಮ ಊರು • ನಮ್ಮ ಧ್ವನಿ
> **Handle**: `@oormanisuddi`
> **Coverage**: ಕರಾವಳಿ — coastal Karnataka. One word, set in `tokens.Brand.coverage`.

---

## Start here

**If you are an AI tool being handed news copy → read
[`docs/AI_BRIEF.md`](docs/AI_BRIEF.md) and nothing else first.** It is written
for you: the JSON contract, how to choose a template, the hard limits, and what
will be rejected.

**If you are an AI tool asked to edit raw video clips into a long-format
YouTube video → read
[`.agents/skills/youtube-longform-edit/SKILL.md`](.agents/skills/youtube-longform-edit/SKILL.md)
first.** It is the house method (expert panel, creative and technical standards,
lessons from the first job) and ships the tools that do the work. For a vertical
**Instagram Reel / YouTube Short from real clips**, read
[`.agents/skills/reels-shorts-edit/SKILL.md`](.agents/skills/reels-shorts-edit/SKILL.md).

**If you are a human working on the design → read
[`STANDARDS.md`](STANDARDS.md)**, then [`docs/DECISIONS.md`](docs/DECISIONS.md)
before changing any value.

---

## Doing the work

```bash
python3 render.py editions/2026-08-25.json --only carousel story_card broadsheet reel
python3 render.py editions/2026-08-25.json      # full package (AI bulletin is HOLD, not YouTube)
python3 render.py --describe                    # every template + its rules
python3 render.py --schema story                # the input contract
python3 render.py --check my.json               # validate, render nothing
python3 render.py editions/greetings/X.json     # a festival wish: 9:16, 4:5, 1:1
python3 render.py editions/X.json --minimal      # the four things that ship daily
python3 -m unittest tests.test_contract         # the contract (instant)
python3 -m unittest discover tests              # + the golden design (~2 min)

python3 scripts/fetch_daily_news.py             # the morning tip sheet
python3 scripts/sign_off.py out/DATE --by NAME  # sign taste / culture / news
python3 scripts/whats_on.py                     # what is coming, what is overdue
python3 scripts/correction.py status            # the IT Rules clocks
python3 scripts/metrics.py report               # whether the guessed numbers hold
python3 scripts/verify_narration.py out/DATE    # did the voice say the words
python3 scripts/archive_edition.py DATE         # the published record
bash scripts/backup.sh --status                 # three copies, or fewer
```

On a fresh checkout, once:

```bash
python3 -m pip install --break-system-packages -r requirements.txt
bash scripts/install_hooks.sh          # contract runs before every commit
bash scripts/install_launchd.sh        # 06:05 tip sheet, with failure alerts
bash scripts/backup.sh --install       # nightly, 22:30
```

Content is JSON in `editions/`. Copy a recent edition. You never write
rendering code — eleven finished templates already exist (`python3 render.py --describe`).

---

## Nine rules that override anything you might infer

1. **`Story.validate()` is not negotiable.** Every photograph carries a credit
   and declares whether it shows the actual scene. Every story names a source.
   ಬ್ರೇಕಿಂಗ್ is computed from the publish timestamp, never asserted. Do not add
   an override flag — it will be used on a deadline, and then the whole system
   is decoration.
2. **Strict Image Policy: High-Quality AI Imagery Only or Clean Editorial Plate (No Low-Quality Web Scrapes).**
   Only high-quality AI-generated images created directly via the chat/agent environment may be used.
   If AI image generation is unavailable (e.g. quota limits), leave the story WITHOUT a photo — the template
   will automatically render the clean brand editorial graphic plate. NEVER fetch, scrape, or attach low-quality,
   compressed, or generic real web images.
   **Gemini API Key Reservation**: The Gemini API key is STRICTLY reserved for voiceover synthesis (TTS).
   It must NEVER be used for image generation under any circumstance.
   Furthermore, all AI-generated images and rendered carousel slides MUST be displayed directly in the chat
   response so the editor can visually inspect them.
3. **Restraint.** One accent (gold), hairlines not borders, square corners, no
   frame around the canvas, no outlined boxes.
   That is the rule for NEWS. A festival **greeting** is a separate genre —
   centred, ornamented, signed — made only by `templates/greeting.py`
   (DECISIONS D54). Gold is still the only accent there.
4. **Crime copy states allegations, never verdicts** — and every photograph
   carries a licence, not just a credit. Both are enforced by
   `Story.validate()`; see [`docs/DECISIONS.md`](docs/DECISIONS.md) D29–D30.
   The `headline` and `reel_line` are checked **on their own**: they travel
   without the rest of the story, so each must carry its own ಆರೋಪ / ಆರೋಪಿ /
   ಶಂಕಿತ. A qualifier in the deck does not cover a headline.
5. **No source, no claim. No human verification, no publication.** A story
   that is not own reporting needs a `source_url` the editor can reopen — that
   is enforced at render. It ALSO needs `verified_by`: the name of the person
   who opened that source and checked the facts. The Chief Editor gate will not
   write `APPROVAL.md` without one. This is not the same as `status`:
   "confirmed" is what the card says about the news and a model can write it;
   `verified_by` is what a person says about their own work. D55, D59.
6. **`APPROVAL.md` is a mechanical clearance, not a verdict.** It says the
   checks passed. It does not say the lead is right, that a deity is treated
   with dignity, or that the package looks like the channel at its best —
   nothing in `brand/review.py` can establish any of those. Look at `_review/`
   at feed size, listen to one reel on headphones, then sign:
   `python3 scripts/sign_off.py out/DATE --by "<name>"`. Do not upload an
   unsigned package, and never write a sign-off in someone else's name. D62.
7. **Keep `tokens.Brand.grievance_officer` and a watched contact filled in.**
   IT Rules 2021 Part III requires a named Grievance Officer. Officer is
   Gautam Paduvari, WhatsApp +91 96117 56514, email oormanisuddi@gmail.com.
   `compliance()` and `review()` fail while the officer or contact is blank.
   See `docs/CORRECTIONS.md`.
8. **Strict Workspace Isolation & AI Boundary Containment.** This repository is an
   isolated environment. No AI model, agent, subagent, script, or automated tool
   shall ever read, write, execute commands in, inspect, or operate outside this
   project folder (`/Users/shameekyogi/My Apps/Oormani Suddi`). All task execution, file
   access, and shell contexts are strictly confined within this directory. Cross-project
   access or path traversal outside this perimeter is prohibited and must fail-closed.
9. **Platform Strategy: YouTube ≠ Instagram (Data-Driven, Sept 2026).**
   Channel analytics from weeks 1–3 proved that YouTube's algorithm aggressively
   suppresses AI-generated TTS + slideshow reels (avg 37 views, latest at 1–4)
   while real footage averaged 397 views — a **10× gap**. The rules:
   - **YouTube**: AI-rendered card reels must NOT be uploaded to YouTube as the
     primary content. YouTube uploads MUST contain real camera footage (phone is
     fine), real human voiceover, or face-to-camera anchor reads. The AI rendering
     pipeline may be used for YouTube thumbnails, lower-thirds, and supplementary
     graphics overlaid on real footage — but never as the entire video.
   - **Instagram**: AI-rendered carousels and reels continue as the primary format.
     Instagram's algorithm does not penalise AI imagery the way YouTube does, and
     the carousel format is optimised for the platform.
   - **Reels built by `render.py`** are scheduled for **Instagram Reels only** by
     default. They are cross-posted to YouTube Shorts **only** when the editor
     explicitly requests it (e.g. for a major story with no available footage).
   - Every YouTube upload description must end with an engagement question in
     Kannada ("ನಿಮ್ಮ ಅಭಿಪ್ರಾಯ ಏನು? ಕಮೆಂಟ್ ಮಾಡಿ.") to drive the comment signal
     the algorithm needs.


---

## Standard Publishing Workflow: Carousel + Individual Reels (10x Reach)

Whenever raw news copy is provided for a bulletin:
1. **Flawless Kannada Copy**: Natural, concise, grammatically verified Kannada. Numbers must always use Latin numerals (`25`, `29.6`), never Kannada numerals (`೨೫`). Headlines stay under 78 characters; punchy `reel_line` under 46 characters. Crime copy must strictly use allegation markers (ಆರೋಪ / ಆರೋಪಿ / ಶಂಕಿತ).
2. **Visual Standards: High-Quality AI Imagery Only or Clean Editorial Plate (Zero Low-Quality Scrapes)**:
   - **Inspect Evergreen Stock Library FIRST (`assets/stock/`)**: On `start`, always check `assets/stock/` (and `assets/stock/CATALOG.md`) BEFORE generating new AI images. If a truly generic newsroom visual already exists (e.g. police dog squad, CCTV monitoring, traffic patrol, NH66 highway traffic, fishing harbour, taluk revenue office, rural market), REUSE it directly with `nature: 'ai'` (these frames were generated), `licence: 'own'`, and a truthful caption. Generate fresh AI images ONLY if no suitable stock image exists.
   - **Generate Fresh Editorial Imagery Only When Needed**: Use `generate_image` strictly when the story requires a unique visual scene not covered in stock.
   - **STRICT PROHIBITION**: NEVER fetch, scrape, or attach low-quality, pixelated, or random real web photos.
   - If AI image generation is unavailable (e.g. quota limits), leave the story WITHOUT a photo — the template will automatically render the clean brand editorial plate (`editorial_plate`).
   - **Gemini API Key Strict Reservation**: The Gemini API key is strictly reserved for voice synthesis (TTS). NEVER use it for image generation.
   - Every generated image, including reused stock, carries `nature: 'ai'`, `credit: 'AI ಚಿತ್ರ — ಊರ್ಮನಿ ಸುದ್ದಿ'`, `licence: 'own'`, and an honest `caption`. `representative` is only for a real photograph of a similar scene.
   - **In-Chat Display**: All generated AI images and rendered carousel slides MUST be displayed directly in the chat response.
   - **Mandatory 10/10 Cultural & Legal Cross-Check**: The Visual Culture & Legal Expert inspects every image. Zero tolerance for distortions or mockery of sacred coastal traditions (Yakshagana, Hulivesha, Daivaradhane, temple rituals). Zero minor faces, victim trauma, or gore. Must score a verified 10/10 before layout; otherwise regenerate on loop.
3. **Edition JSON**: Save to `editions/YYYY-MM-DD.json`.
4. **Targeted Deliverables on Demand (Zero Clutter)**:
   - Deliver **ONLY** what the user actually requests (e.g. `--only carousel reel`). Do not waste render time or clutter output with formats not requested (bulletin, broadsheet, individual post cards, etc.).
   - **Carousel** (`carousel_01_cover.jpg` .. `08`) for swipeable daily coverage. 100% of slides carry photography.
   - **Individual Reels ONLY for 10/10 Reel-Worthy Stories** (`reel_01.mp4`, `reel_02.mp4`, etc.) with their respective cover frames (`reel_*_cover.jpg`).
     - **Short-Form Audience Retention & 10/10 Algorithm Gate**:
       - Only stories scoring 10/10 in visual drama, public urgency, high stakes, or viral regional talkability become reels (`is_reel: true`).
       - Multi-image chapter breakdown (cutting to fresh scene photos every 12–15s) guarantees dynamic visual rhythm without static freezes.
       - **Speech-Locked Beat Synchronization (D45)**: Narration is synthesized per card beat (`card_keys()`), and cuts are timed strictly to speech boundaries (`vo_gap`, `vo_lead`), completely preventing drift between voiceover and on-screen cards.
       - **Strict Card-to-Narration 1:1 Audit**: Anchor greeting and lead sentence stay bound together on `lead`, each fact beat strictly corresponds to its on-screen card, initials with periods do NOT split into spurious beats, and advisory carries an advisory marker (`ಗಮನಿಸಿ:`). No card may display text while the voiceover reads a different card's copy.
       - **Clean Wipes & Restrained Audio Bed (D48)**: Smooth scene wipes with gold rim; background score ducks once cleanly under speech (`bgm_duck`) without pumping.
       - **Glyph Safety (D46)**: Typographic fallback (`typo.safe()`) and drawn badge marks ensure no missing characters or empty tofu boxes render in badges or copy.
       - The Audience Retention Expert audits the final video (3-second hook, speech-locked sync, audio ducking, text legibility, living outro). If rating < 10/10, loop back to polish until 10/10 perfection is reached.
5. **Legal, Copyright & YouTube Monetization Guardrails (10/10 Ad-Safe)**:
   - **AdSense Green Dollar Clearance**: Zero depictions of blood, open wounds, gore, or trapped victims in imagery or thumbnails. Sober, objective reporting without sensationalized clickbait.
   - **Content ID & Copyright Shield**: In-house royalty-free music (`assets/news_bgm.mp3`), open/proprietary broadcast SFX (`sfx/`), and verified `own` licenses. Zero risk of copyright claims or audio mutes.
   - **Indian Media Law Compliance**: IT Rules 2021 publisher transparency, POCSO minor privacy protection, Section 228A IPC/BNS victim privacy, and strict allegation markers (*ಆರೋಪ / ಆರೋಪಿ / ಶಂಕಿತ*).
   - The Legal & Monetization Expert audits the full package; zero tolerance for ad-limitation or legal risks.
6. **Complete Copy & Schedule Plan**:
   - The time-scheduled publishing timetable is **generated** — `render.py` writes `schedule.txt` and `schedule.json` from what it actually rendered.
   - Ready-to-copy Instagram captions with First Comments (pinned questions).
   - Ready-to-copy YouTube Shorts Titles (<60 chars, mobile search optimized), Descriptions (with snippet and timestamps), and Tags for every single reel.
7. **Session Wrap & Stock Archival (`stop` / `close` workflow)**:
   - When the user types `stop`, `close`, `done`, or `cleanup`:
     - **Audit Newly Generated Images**: Inspect `assets/daily/{DATE}/` for any newly generated photos. Identify ONLY those that are truly generic and evergreen for future news stories across the region.
     - **Save to Stock**: Copy the generic images to `assets/stock/` with clean descriptive filenames and update `assets/stock/CATALOG.md`.
     - **Archive the published record first**: `python3 scripts/archive_edition.py {DATE}` copies edition JSON, APPROVAL.md, copy, schedule and review frames to `archive/{DATE}/`.
     - **Then** delete leftover `out/{DATE}/` and remaining `assets/daily/{DATE}/`. Never delete the edition JSON.

---

## When it goes wrong

[`docs/RUNBOOK.md`](docs/RUNBOOK.md) — every error code mapped to its fix, both
statutory clocks, the short-day floor, and what to do when the golden test
fails. That is the document to reach for at 07:40; this one is the contract.

---

## Layout of the project

```
render.py           JSON in, finished design out — the entry point
editions/*.json     the content; one file per day's bulletin

templates/          eleven templates, one file each, none importing another
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
