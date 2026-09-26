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

**If the person in this chat says exactly "Start", says "Stop", or approves a
draft you showed them → follow [`docs/RUNBOOK.md`](docs/RUNBOOK.md)'s "Chat
workflow" section precisely, every time, regardless of which AI tool you are.**
It is the editor's own standing instruction for how a conversation, not a
terminal, drives the daily pipeline.

---

## Doing the work

```bash
python3 render.py --describe                    # every template + its rules
python3 render.py --schema story                # the input contract
python3 render.py --check my.json               # validate, render nothing
python3 render.py editions/greetings/X.json     # a festival wish: 9:16, 4:5, 1:1
python3 render.py editions/X.json --only $(python3 scripts/pick_formats.py editions/X.json)
                                                 # the daily default: carousel + ONE reel —
                                                 # ಸ್ಪೀಡ್ ನ್ಯೂಸ್ with 3+ stories, else the lead
                                                 # reel if it earns one (D81, 2026-09-18-02)
python3 render.py editions/X.json --only roundup  # ಸ್ಪೀಡ್ ನ್ಯೂಸ್ on its own
python3 render.py editions/2026-08-25.json --only story_card broadsheet   # on request only
python3 render.py editions/2026-08-25.json      # full package (AI bulletin is HOLD, not YouTube)
python3 -m unittest tests.test_contract         # the contract (instant)
python3 -m unittest discover tests              # + the golden design (~2 min)

python3 scripts/health.py                       # is anything quietly broken
python3 scripts/house_rule.py list              # standing instructions in force
python3 scripts/house_rule.py where "…"         # where does this change belong
python3 scripts/fetch_daily_news.py             # the morning tip sheet
python3 scripts/draft_edition.py                # tip sheet -> editions/{date}.json, unverified (D76)
python3 scripts/dispatch.py                     # which of the 12 agents are due, and why (D89)
python3 scripts/fact_check.py editions/DATE.json # every figure vs its source (D84)
python3 scripts/trending_tags.py                # today's trends (D86); --show to read
python3 -m brand.stock editions/DATE.json       # which stock frame each story earns, and why (D85)
python3 scripts/verify.py editions/DATE.json --story N --by NAME   # the one thing a person must do
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
# The 06:05 job outside this repo (D71) is not ours and stays as it is. Our
# own job fires at 06:10 and 07:00 — offset so it never races that one — and
# fetches, then drafts the edition (D76):
bash scripts/install_launchd.sh
bash scripts/backup.sh --install       # nightly, 22:30
```

Content is JSON in `editions/`. Copy a recent edition. You never write
rendering code — eleven finished templates already exist (`python3 render.py --describe`).

---

## Ten rules that override anything you might infer

1. **`Story.validate()` is not negotiable.** Every photograph carries a credit
   and declares whether it shows the actual scene. Every story names a source.
   ಬ್ರೇಕಿಂಗ್ is computed from the publish timestamp, never asserted. Do not add
   an override flag — it will be used on a deadline, and then the whole system
   is decoration.
2. **Strict Image Policy: 100% Carousel Photo Coverage (No Slide Without an Image; Zero Low-Quality Scrapes).**
   Every single carousel story slide MUST carry a high-quality photograph (100% photo coverage). No carousel slide may appear without an image or fall back to an editorial plate.
   Always check `assets/stock/` first for an evergreen match; if none exists, immediately generate a fresh high-quality AI image in chat using `generate_image`.
   **Native 16:9 Single-Shot Framing (Zero Grids / Zero Seams)**: All AI editorial images MUST be generated as single continuous frames with 16:9 aspect ratio (`AspectRatio: '16:9'`) matching the layout's 16:9 image container (`cw: 936, ph: 520`). Prompts must strictly enforce single camera angles with generous headroom and forbid multi-panel grids, collages, or split screens. Never crop sub-panels or quadrants from multi-image grids.
   NEVER fetch, scrape, or attach low-quality, compressed, or generic real web images.
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
10. **Zero Phantom JSON & Segment Brand Isolation (D89, House rule 2026-09-25-04).**
    What is authored in JSON MUST be rendered visibly on the card. If `points` are
    written in JSON, `templates/carousel.py` renders them via `factlist` with gold
    numerals (`01`, `02`, `03`). The gate `PUB-10` strictly fails the build if
    `headline + deck + points` overflows the card boundary, and `PUB-11` limits
    points to 3. Never author copy in JSON that cannot visually fit on the card
    slide. When points exist, `deck` serves strictly as a 1–2 line lead-in
    (`max_lines=2`). Furthermore, special awareness/explainer editions (e.g.,
    `ಕಾನೂನು ಕವಚ`) must NEVER receive coastal boilerplate (`ಕರಾವಳಿ ಬುಲೆಟಿನ್`,
    `#ಕರಾವಳಿಸುದ್ದಿ`, or coastal forwards).

---

## Standard Publishing Workflow: Carousel + Individual Reels (10x Reach)

Whenever raw news copy is provided for a bulletin:
0. **Ask the dispatcher, then run the team in waves (D89)**: `python3 scripts/dispatch.py` lists which of the twelve agents in `.claude/agents/` are due and why — proactive (intake, trends, planning, systems) and reactive (fact, legal, Kannada, picture, social, package, gate, corrections). Launch each wave as one message of parallel Agent calls, one agent per story; agents file receipts; no agent verifies, signs or posts.
   **Intake: fresh, coastal, real, credited (D88)**: the `news-scout` agent (and `scripts/fetch_daily_news.py`) keeps only stories published within `Limits.news_max_age_hours`, about the coast, from a real article page. **Every story credits the outlet its own link belongs to; news the editor adds keeps its own source** (press release → who issued it; no link → `ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ`). Never cite a link copied from a chatbot answer (`utm_source=gemini`) — find the publisher's URL. Gate: `FACT-05` not an article, `FACT-06` wrong outlet.
   **Fact desk first, as a parallel team (D84, D87, house rule 2026-09-24-02)**: before any sentence is written or rewritten, run `python3 scripts/fact_check.py editions/{DATE}.json` and — in Claude Code — the `trend-scout` agent plus one `fact-checker` agent per story, all in one message so they run in parallel (`.claude/agents/`). Then one `picture-editor` per story and the `social-writer`, in parallel. A figure not in the cited source (`FACT-01`) or a source page that does not carry the story (`FACT-02`) blocks at the gate.
1. **Flawless Kannada Copy & Mandatory News Description (`deck`)**: Natural, concise, grammatically verified Kannada. Numbers must always use Latin numerals (`25`, `29.6`), never Kannada numerals (`೨೫`). Headlines stay under 78 characters; punchy `reel_line` under 46 characters. Crime copy must strictly use allegation markers (ಆರೋಪ / ಆರೋಪಿ / ಶಂಕಿತ). **Every story MUST carry a rich, informative `deck` (standfirst/description)**: A carousel is a news medium, not a headline ticker; the `deck` explains what happened, where, and who was involved directly below the headline on every card.
2. **Visual Standards: 100% Photo Coverage on All Carousel Slides (Stock or Chat AI Generation; Zero Scrapes)**:
   - **Mandatory 100% Photo Coverage on Carousel**: Every story slide in the daily carousel MUST carry photography. No slide may be left unillustrated or fall back to an editorial graphic plate.
   - **Inspect Evergreen Stock Library FIRST (`assets/stock/`)**: On `start`, always check `assets/stock/` (and `assets/stock/CATALOG.md`) BEFORE generating new AI images. If a truly generic newsroom visual already exists (e.g. police dog squad, CCTV monitoring, traffic patrol, NH66 highway traffic, fishing harbour, taluk revenue office, rural market), REUSE it directly with `nature: 'ai'` (these frames were generated), `licence: 'own'`, and a truthful caption.
   - **Generate Fresh Editorial Imagery Whenever Stock Does Not Match**: Use `generate_image` in chat immediately when the story requires a visual scene not covered in stock.
   - **Native 16:9 Single-Shot Framing (Zero Grids / Zero Seams)**: All AI editorial images for news cards MUST be generated with `AspectRatio: '16:9'` to match the carousel card photo box (`cw: 936, ph: 520`). Prompts must strictly mandate a single continuous camera angle with generous headroom and explicitly forbid collages, multi-panel grids, or split screens. NEVER crop sub-panels or quadrants from multi-image grids — doing so introduces seam lines, cut-off subjects, and ruined composition. If a generation produces multiple panels, discard and regenerate with stronger single-shot framing.
   - **STRICT PROHIBITION**: NEVER fetch, scrape, or attach low-quality, pixelated, or random real web photos.
   - **Gemini API Key Strict Reservation**: The Gemini API key is strictly reserved for voice synthesis (TTS). NEVER use it for image generation.
   - **Clean Photo Disclosure (No Duplicate AI Labels)**: `Photo.disclosure` automatically prepends the nature tag (`ಎಐ ರಚಿತ ಚಿತ್ರ • `). Therefore, `caption` must ONLY describe the visual scene, never repeating `(ಎಐ ರಚಿತ ಚಿತ್ರ)` or `AI ಚಿತ್ರ`. The `credit` field must simply be `ಊರ್ಮನಿ ಸುದ್ದಿ` (never `AI ಚಿತ್ರ — ಊರ್ಮನಿ ಸುದ್ದಿ`). The printed disclosure line will say 'ಎಐ ರಚಿತ ಚಿತ್ರ' exactly once at the beginning.
   - **Research Before Prompting & Zero Fake AI Text (House rule 2026-09-19-02)**:
     - **Research Real Context First**: For cultural, language, historical, or government news (e.g. Tulu language status, literature meets, cabinet decisions, heritage rituals), do internet/tip research first to determine the exact authentic artifacts (e.g. palm-leaf manuscripts/talegari, brass styluses, bronze lamps, authentic meeting halls) and real context.
     - **Strictly Ban Text/Typography in Prompts**: Always enforce in every prompt: `Strictly NO text, NO signs, NO banners, NO posters, NO writing, NO typography, NO logos anywhere in the image`. AI image models inevitably generate corrupted, garbled pseudo-text on banners and signs. Forbidding all text guarantees clean, photographic broadcast realism on the first attempt without tedious corrections.
     - **Ground in Coastal Karnataka Material Culture**: Insist on authentic local attire (khadi, zari shawls, traditional sarees), local architecture (teakwood, coastal heritage houses), and real human emotions (sharing sweets, genuine joy, serious governance) over generic fantasy tropes.
   - **In-Chat Display**: All generated AI images and rendered carousel slides MUST be displayed directly in the chat response.
   - **Strict Contextual Visual Action Match (Zero Lazy Category Matching, House rule 2026-09-20-01)**:
     - Every image chosen from stock or generated MUST match the *exact real-world action* of the story, not just its broad category label.
     - For online exams, entrance tests, counselling, or mock seat allotments (e.g. PGCET, CET), ALWAYS show students with laptops/computers actively checking results on digital portals with application forms — NEVER attach generic stage award ceremonies or certificate distribution photos.
     - For memorandum deadlines/tenders, show official engineering/government files; for protests, show delegations. Lazy category-level matching damages editorial credibility.
   - **Coastal Framing for State-Level News (House rule 2026-09-20-02)**:
     - Major Karnataka state-level education, government policy, and welfare decisions (e.g. PGCET, CET, state budget, government orders, weather forecasts) directly impact students, institutions, and citizens of Coastal Karnataka.
     - Never dismiss relevant state news as non-local; always explicitly frame it with a Coastal Karnataka connection in headlines, decks, and visual representation (`ಕರಾವಳಿ ಭಾಗದ ವಿದ್ಯಾರ್ಥಿಗಳು / ಸಾರ್ವಜನಿಕರಿಗೆ...`).
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
   - **Dedicated 1-Click Copy Files (`{stem}_caption.txt` & `{stem}_whatsapp.txt`, House rules 2026-09-17-06 & 08)**:
     - `carousel_caption.txt`: Clean, complete Instagram caption (Lead hook, swipe prompt, headlines list, CTA question, sources, grievance contact, and multi-story hashtags) with ZERO extraneous banner headers or labels. Open on phone, Select All, Paste.
     - `carousel_whatsapp.txt`: Tailored WhatsApp group & broadcast digest (`🌾 *ಊರ್ಮನಿ ಸುದ್ದಿ · {date}*`, tagline, numbered emoji items `1️⃣ *ಸ್ಥಳ*: ಸುದ್ದಿ`, direct Instagram CTA `📲 *ಪೂರ್ಣ ವರದಿ ಹಾಗೂ ವಿವರಣೆಗಾಗಿ ಇನ್‌ಸ್ಟಾಗ್ರಾಮ್ ಲಿಂಕ್ ನೋಡಿ:*`, source credits, handle). NEVER mention "ಫೋಟೋಗಳು" when using AI imagery.
   - **Five Hashtags, Every Town Findable (D86, house rule 2026-09-24-01)**: Instagram reads 5 hashtags per post since Dec 2025. `brand/copy.py` picks them (town, TownNews, one trend the story is genuinely about, subject, ಕರಾವಳಿಸುದ್ದಿ/channel) and writes every other town into the caption's 📍 line in Kannada and English. The gate fails a caption over five (`PUB-09`). Trends come from `inbox/trends_{DATE}.json`; a trend the story is not about is never used — YouTube removes videos for misleading metadata, and on Instagram it sends the post to people who swipe past.
   - Ready-to-copy Instagram captions with First Comments (pinned questions).
   - Ready-to-copy YouTube Shorts Titles (<60 chars, mobile search optimized), Descriptions (with snippet and timestamps), and Tags for every single reel.
7. **Session Wrap & Stock Archival (`stop` / `close` workflow)**:
   - When the user types `stop`, `close`, `done`, or `cleanup`:
     - **Audit Newly Generated Images**: Inspect `assets/daily/{DATE}/` for any newly generated photos. Identify ONLY those that are truly generic and evergreen for future news stories across the region.
     - **Save to Stock**: Copy the generic images to `assets/stock/` with clean descriptive filenames and update `assets/stock/CATALOG.md`.
     - **Archive the published record first**: `python3 scripts/archive_edition.py {DATE}` copies edition JSON, APPROVAL.md, copy, schedule and review frames to `archive/{DATE}/`.
     - **Then** delete leftover `out/{DATE}/` and remaining `assets/daily/{DATE}/`. Never delete the edition JSON.
8. **Special Segment: 'ಕಾನೂನು ಕವಚ' (Kanoonu Kavacha, House rules 2026-09-25-02 & 2026-09-25-03)**:
   - **Publishing Schedule**: **Every Saturday** is dedicated to the Special Segment (`ಕಾನೂನು ಕವಚ` — currently focused on female safety, cyber rights, and relationship coercion).
   - **Segment Badge / Title**: `ಕಾನೂನು ಕವಚ` (Kanoonu Kavacha)
   - **Sub-tagline**: `ಹೆಣ್ಣುಮಕ್ಕಳ ಡಿಜಿಟಲ್ & ಸೈಬರ್ ರಕ್ಷಣೆ` • `ಭಯ ಬೇಡ • ಕಾನೂನು ನಿನ್ನ ಪರ`
   - **Core Structure (Case-Driven Deterrent + Empowerment)**:
     1. **Distinct Real Case Scenarios**: Each carousel covers ONE specific manipulative case/tactic (e.g., password coercion, leak extortion, fake ID defamation, suicide threats, minor/POCSO, 24/7 surveillance).
     2. **Strict Legal Deterrent to Perpetrators**: Always highlight the brutal legal consequences awaiting the abuser (non-bailable FIR, forensic device seizure, 3 to 7 years imprisonment, permanent criminal background record ruining jobs/visas/passports).
     3. **Empowerment & Relief for Girls**: Objective, compassionate, zero victim-blaming, practical evidence preservation, and direct helpline actions (**112**, **1930**, **1091**, [cybercrime.gov.in](https://cybercrime.gov.in), and [StopNCII.org](https://stopncii.org)).
     4. **Statutory Sources**: Accurately cite official legal statutes (BNS 2023, IT Act 2000, POCSO, National Cyber Crime Helpline).
   - **Future Ideation Mandate**: Whenever the editor asks for special segment topics or future ideas, automatically pitch and develop bold, practical, high-impact case scenarios adhering to this standard.
9. **Universal Carousel Visibility & Segment Branding Integrity (D89, House rule 2026-09-25-04)**:
   - **Zero Phantom Fields (100% Carousel Visibility)**: Every single story field authored in JSON (`headline`, `deck`, `points`) MUST render visibly on the card. `templates/carousel.py` renders `points` with gold numerals (`01`, `02`, `03`) via `factlist`. If points exist, `deck` serves strictly as a 1–2 line lead-in (`max_lines=2`). Card photo box dynamically adjusts to `H * 0.32` to guarantee ample room.
   - **Slide Capacity Hard Fail (`PUB-10` & `PUB-11`)**: The publishing gate strictly calculates the pixel height of `headline + deck + points`. If copy overflows the card boundary (`src_top - 20`), the build fails immediately. Never write copy in JSON that cannot visually fit on the card slide. `len(points)` is capped at 3 (`PUB-11`).
   - **Strict Branding Isolation for Special Segments**: Special awareness/explainer editions (e.g., `ಕಾನೂನು ಕವಚ`) must NEVER receive coastal boilerplate. Masthead, cover pill, footer badge, and hashtags are dynamically isolated (suppressing `#ಕರಾವಳಿಸುದ್ದಿ`, using topic-specific hashtags like `#ಕಾನೂನುಕವಚ`, `#CyberSafety`, `#WomenSafety`, and suppressing `forward_ಕರಾವಳಿ.txt`).

---

## Asking for a change

Four places, and only four. `python3 scripts/house_rule.py where "…"` tells you
which:

| What | Where | Why there |
|---|---|---|
| a **number** | `tokens.Limits` + decision + test | D56 — one home, or it drifts |
| a **legal** rule | `brand/content.py` + test + decision | D29 — never in a file that can be edited on a deadline |
| a **place** | `copy.PLACE_TAGS` | one registry, read by hashtags, forwards and reach |
| everything else | `scripts/house_rule.py add` | wording, habits, preferences |

A house rule applies from the moment it is added, every run, until retired. It
**cannot** switch a check off — `add()` refuses that, and says what to do
instead. `AGENTS.md` beats a house rule; a house rule beats the skill's
defaults. D73.

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
