# House rules

_Generated from `docs/HOUSE_RULES.json` by `brand/house.py`. Do not edit by hand — use `python3 scripts/house_rule.py`._

Things the owner asked for once, written down where the newsroom reads
them at the start of every run. The alternative is an instruction that
lives in a chat log until everybody forgets it.

**A house rule cannot switch a check off.** Numbers live in
`tokens.Limits`, legal rules in `brand/content.py`, places in
`copy.PLACE_TAGS`. This file is for wording, habits and preferences —
the things that are genuinely house style rather than contract.

## desk

- **2026-09-16-02** — Weather takeaway always names the helpline number, not just 'contact the DC'
  - _why:_ a takeaway people can act on is the strongest forward predictor (D72)
  - _asked by:_ Gautam Paduvari
- **2026-09-17-04** — Every story in a daily bulletin must have a comprehensive Kannada news description (deck). A carousel is not a headline ticker; the deck explains who, what, where, and why below the headline.
  - _why:_ Editor standing instruction (2026-09-17): carousel slides must never be headlines-only; deck is mandatory.
- **2026-09-17-08** — WhatsApp group and broadcast messages must follow the tailored format: 🌾 *ಊರ್ಮನಿ ಸುದ್ದಿ · {date}*, tagline, numbered items with place names (1️⃣ *ಸ್ಥಳ*: ಸುದ್ದಿ), and '📲 *ಪೂರ್ಣ ವರದಿ ಹಾಗೂ ವಿವರಣೆಗಾಗಿ ಇನ್‌ಸ್ಟಾಗ್ರಾಮ್ ಲಿಂಕ್ ನೋಡಿ:*'. NEVER write 'ಫೋಟೋಗಳು' or 'photos' when using AI-generated imagery.
  - _why:_ Editor standing instruction (2026-09-17): exact approved WhatsApp group/broadcast format.
- **2026-09-20-02** — State-level education, government policy, and administrative news (e.g. PGCET, CET, state budget, welfare schemes, weather alerts) directly impact Coastal Karnataka students, institutions, and citizens. Always frame such news with an explicit Coastal Karnataka connection in headlines, decks, and visual representation rather than dismissing it as non-local.
  - _why:_ Editor standing instruction (2026-09-20): Major state-level educational and civic decisions affect coastal citizens and must be reported with an active Karavali focus.
  - _asked by:_ Gautam
- **2026-09-25-01** — Every story credits the outlet its own link belongs to, and every news item the editor adds keeps its own source: a link → that outlet; a press release → who issued it; seen or told → ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ. Never fold added news under another paper's name, never cite a link copied from a chatbot answer, and only draft news published within Limits.news_max_age_hours that is about the coast.
  - _why:_ editor 2026-09-25: added news ended up credited to one paper; stale and unrelated news reached the draft (D88)
  - _asked by:_ Shameek Yogi
- **2026-09-27-01** — When choosing or ordering the day's stories, prefer places in this order: ಕುಂದಾಪುರ (Kundapura) and ಬೈಂದೂರು (Byndoor) highest, then ಉಡುಪಿ (Udupi) and ಮಣಿಪಾಲ (Manipal), then ಕಾರ್ಕಳ (Karkala), ಬ್ರಹ್ಮಾವರ (Brahmavara), ಹೆಬ್ರಿ (Hebri), ಕಾಪು (Kaup), ಮಂಗಳೂರು (Mangalore).
  - _why:_ editor's own priority ranking of the coverage area, 2026-09-17; carried over unchanged from 2026-09-17-01, which was worded for the deleted morning auto-draft (D92)
  - _asked by:_ carried over from 2026-09-17-01
- **2026-09-27-02** — Keep the source's own Kannada word: never swap it for an English loan (ದೀಪಸ್ತಂಭ, not ಲೈಟ್‌ಹೌಸ್) or for a word that shifts the meaning (a sudden change in the weather is ವಾತಾವರಣದ ಹಠಾತ್ ಬದಲಾವಣೆ; ಹವಾಮಾನ ಬದಲಾವಣೆ reads as climate change). File every story under the category of what happened — never civic by default: a fatal fall is accident, a fish shoal or a dolphin is environment, a fishermen's scheme is fisheries.
  - _why:_ the first ಸುದ್ದಿ ಸಾರ, 2026-09-27, carried both wording slips and filed three of six stories under ಆಡಳಿತ wrongly; the kicker says the category on every slide
  - _asked by:_ Chief Editor review (from the editor's instruction to stop repeats)
- **2026-09-27-03** — Strictly verify and research authentic coastal Kannada place names and spelling: always use ತಲ್ಲೂರು (not ತಾಳೂರು), ಹೆಮ್ಮಾಡಿ (not ಹೇರ್ಮಾಡಿ), ಯಡ್ತರೆ, ತ್ರಾಸಿ, ಅರಾಟೆ, ಕೋಟೇಶ್ವರ, ಗಂಗೊಳ್ಳಿ. Never introduce phonetic or colloquial misspellings.
  - _why:_ Editor instruction (2026-09-27): Tallur is ತಲ್ಲೂರು, not ತಾಳೂರು; coastal place names must be rigorously researched and spelled with zero errors.
  - _asked by:_ Gautam Paduvari
- **2026-09-30-01** — Fact desk must verify budget figures (e.g. crores) and distinguish in-principle approvals from finalized commercial timetables
  - _why:_ Editor instruction 2026-09-30: prevent unsubstantiated project costs and premature finality claims in transport and infrastructure reporting
  - _asked by:_ Gautam Paduvari

## picture

- **2026-09-16-01** — ಹಬ್ಬದ ಕಾರ್ಡ್‌ನಲ್ಲಿ ಸಂಘಟಕರ ಹೆಸರು ಕಡ್ಡಾಯ — ಪೋಸ್ಟರ್‌ನಿಂದ ಅಲ್ಲ, ಸಂಘಟಕರಿಂದಲೇ ಪಡೆಯಿರಿ
  - _why:_ organisers reshare what credits them; a name off a poster is how ಸೇನೇಶ್ವರ happened
  - _asked by:_ Gautam Paduvari
- **2026-09-17-05** — Photo disclosure must never duplicate 'ಎಐ ರಚಿತ ಚಿತ್ರ' or 'AI ಚಿತ್ರ'. Photo.disclosure automatically prepends the nature label. The caption must only describe the visual scene, and credit must just be 'ಊರ್ಮನಿ ಸುದ್ದಿ' without repeating 'AI ಚಿತ್ರ'.
  - _why:_ Editor standing instruction (2026-09-17): avoid repetitive stutter of AI image labels on disclosure lines.
- **2026-09-19-02** — Before generating any AI editorial image for cultural, language, historical, or government news: 1) Research the real news reporting, actual artifacts, or cultural context first (e.g. search real manuscripts, scripts, official settings). 2) Always strictly prohibit text in prompts: mandate 'Strictly NO text, NO signs, NO banners, NO posters, NO writing, NO typography, NO logos anywhere in the image' to prevent corrupted AI lettering. 3) Depict authentic coastal Karnataka material culture (props like palm-leaf manuscripts/lamps, coastal attire, real meeting settings) instead of generic fantasy tropes.
  - _why:_ Editor standing instruction (2026-09-19): Tulu language and cultural images require real-world research first and zero fake AI text to produce broadcast-grade, culturally accurate photography every time without manual back-and-forth
  - _asked by:_ Editor
- **2026-09-20-01** — Every image must contextually match the exact real-world action of the story, not just its broad category. For online tests, counselling, seat allotments, or digital portals, show students with laptops/computers checking results with application sheets — NEVER show certificates/award ceremonies on a stage. For protests, show memorandum/delegation; for tenders/bills, show engineering/official files. Research the exact action before matching or generating any image.
  - _why:_ Editor rebuke on 2026-09-20: PGCET mock seat allotment was paired with a generic certificate ceremony photo instead of students checking results on a laptop. Lazy category-level matching damages editorial credibility.
  - _asked by:_ Gautam

## package

- **2026-09-17-06** — Every post that gets rendered also gets its own caption file — {post}_caption.txt — containing the caption and nothing else: no headings, no first comment, no WhatsApp forward. A YouTube post gets TITLE / DESCRIPTION / TAGS instead, because a title cannot be pasted into a description box. The working sheet stays in _copy.txt and MASTER_COPY.md.
  - _why:_ posting is select-all-and-paste on a phone; anything else in the file is something that eventually gets pasted with it
  - _asked by:_ Gautam Paduvari
- **2026-09-24-01** — Every town and topic in a carousel or speed-news post must be discoverable: the five hashtags carry the two most-covered towns, one trend the edition is genuinely about, ಕರಾವಳಿಸುದ್ದಿ and the channel; every other town appears in the caption's 📍 line in Kannada and English (brand/copy.py does this).
  - _why:_ supersedes 2026-09-17-07: Instagram reads 5 hashtags since Dec 2025 (D86); caption keywords are searchable
  - _asked by:_ Shameek Yogi

## Retired

Kept, because knowing a rule was dropped and when is worth more than a tidy file.

- ~~2026-09-17-01~~ (2026-09-17 → 2026-09-27) — When picking which tips to auto-draft each morning, prefer taluks in this order: ಕುಂದಾಪುರ (Kundapura) and ಬೈಂದೂರು (Byndoor) highest, then ಉಡುಪಿ (Udupi) and ಮಣಿಪಾಲ (Manipal), then ಕಾರ್ಕಳ (Karkala), ಬ್ರಹ್ಮಾವರ (Brahmavara), ಹೆಬ್ರಿ (Hebri), ಕಾಪು (Kaup), ಮಂಗಳೂರು (Mangalore).
  - editor's own priority ranking of the coverage area, 2026-09-17  · retired: D92: the morning auto-draft is deleted; the editor pastes the day's news. Taluk priority carried over as a new rule.
- ~~2026-09-17-02~~ (2026-09-17 → 2026-09-18) — Daily default render is carousel only. story_card and broadsheet are dropped entirely — carousel already covers that ground, and every extra format is more time spent posting. A reel is never a default; render one only when scripts/pick_formats.py says the lead story earns it (brand.reach.should_be_reel, D72).
  - editor's own observed performance: carousel outperforms, extra formats waste posting time  · retired: superseded by the speed-news daily reel rule of 2026-09-18 (D81); its carousel-only and no story_card/broadsheet parts are restated there
- ~~2026-09-17-03~~ (2026-09-17 → 2026-09-27) — Every carousel slide must have a photo (100% visual photo coverage). No carousel story slide may be published without an image; always pick a matching evergreen photo from assets/stock/ or generate a fresh AI image in chat.
  - Editor standing instruction (2026-09-17): no carousel slide should ever be without an image.  · retired: D92: 100% carousel photos is replaced by the picture rule — ಸುದ್ದಿ ಸಾರ never carries pictures, ಮುಖ್ಯ ಸುದ್ದಿ always does, real first, AI only when the editor says generate
- ~~2026-09-17-07~~ (2026-09-17 → 2026-09-24) — For daily carousel and bulletin editions, hashtags must include all locations (taluks/places) and categories from all stories featured in the edition, not just the lead story.
  - Editor standing instruction (2026-09-17): carousel hashtags must represent all news places and categories covered in the edition.  · retired: Instagram reads only 5 hashtags per post since Dec 2025; the intent (every town discoverable) now lives in the caption's 📍 place line. Superseded by D86 and the rule added 2026-09-24.
- ~~2026-09-18-01~~ (2026-09-18 → 2026-09-27) — Before asking for approval or 'go' on the morning draft, always ask the editor if they have any additional news, press releases, or info to add to today's edition.
  - Editor preference: ensure any spot news, local tips or press releases from the editor are incorporated before rendering.  · retired: D92: the morning draft is deleted; asking whether the editor has more to add is now a step of the RUNBOOK chat workflow
- ~~2026-09-18-02~~ (2026-09-18 → 2026-09-27) — The daily render is the carousel plus ONE reel. With 3 or more stories that reel is ಸ್ಪೀಡ್ ನ್ಯೂಸ್ (render.py --only roundup): a place and one line per story, spoken by the anchor while it is on screen, under 45 seconds. On a thin day of 1-2 stories, the lead-story reel only if scripts/pick_formats.py says the lead earns it. Never both reels. story_card and broadsheet stay out of the default.
  - editor's instruction 2026-09-18: news reels should be quick news; supersedes 2026-09-17-02, which said a reel is never a default  · retired: D92: one story, one format — every story carries segment (speed / saara / mukhya); no daily carousel + reel default
- ~~2026-09-19-01~~ (2026-09-19 → 2026-09-27) — All AI editorial images must be generated as single continuous frames matching the 16:9 card aspect ratio (AspectRatio: '16:9'). Prompts must explicitly mandate a single continuous camera angle with generous headroom and forbid collages, multi-panel grids, or split screens. Never crop sub-panels or quadrants from multi-image grids to prevent seams and cut-off subjects.
  - Crop and seam defects occurred when 1:1 grids were generated and manually cropped for carousel_03 on 2026-09-19. Card photo containers are ~16:9, so single native 16:9 frames ensure flawless framing every time.  · retired: D92: the 16:9 card photo box belongs to the deleted carousel; the single-frame, no-text AI rule is in AGENTS.md
- ~~2026-09-24-02~~ (2026-09-24 → 2026-09-27) — Every edition starts with the fact desk: run trend-scout and one fact-checker agent per story in parallel (scripts/fact_check.py), and write or rewrite no sentence of a story until its fact check passes. Then picture-editor per story and social-writer in parallel.
  - editor instruction 2026-09-24: a fact checker before any sentence is written, and the work done in parallel (D84, D87)  · retired: D92: trend-scout is deleted. The fact desk still goes first (D84, D87) — the dispatcher's waves and the RUNBOOK say so
- ~~2026-09-24-03~~ (2026-09-24 → 2026-09-27) — Check today's trends every day (scripts/trending_tags.py + trend-scout) and use every trending tag a story is genuinely about. Never attach a trend the story is not about — it is misleading metadata on YouTube and cuts reach on Instagram.
  - editor instruction 2026-09-24: trending tags daily for reach; D86 on why only relevant ones reach  · retired: D92: trend scraping and scripts/trending_tags.py are deleted; hashtags follow D86 from the story's own words
- ~~2026-09-25-02~~ (2026-09-25 → 2026-09-27) — ಮಹಿಳೆಯರ ಮತ್ತು ಯುವತಿಯರ ಸೈಬರ್ ಸುರಕ್ಷತೆ, ಡಿಜಿಟಲ್ ಬ್ಲ್ಯಾಕ್‌ಮೇಲ್, ಐಡಿ ದುರ್ಬಳಕೆ ಹಾಗೂ ಕಾನೂನು ರಕ್ಷಣೆಯ ಸಾರ್ವಜನಿಕ ಜಾಗೃತಿ ಸರಣಿ/ವರದಿಗಳನ್ನು 'ಕಾನೂನು ಕವಚ' (Kanoonu Kavacha — ಹೆಣ್ಣುಮಕ್ಕಳ ಡಿಜಿಟಲ್ & ಸೈಬರ್ ರಕ್ಷಣೆ) ಸೆಗ್ಮೆಂಟ್ ಅಡಿಯಲ್ಲಿ ಪ್ರಕಟಿಸಬೇಕು.
  - Editor standing instruction (2026-09-25): Standardize women's cyber safety and legal awareness series under the 'ಕಾನೂನು ಕವಚ' (Kanoonu Kavacha) segment.  · retired: D92: ಕಾನೂನು ಕವಚ is deleted; the channel makes three news formats only
- ~~2026-09-25-03~~ (2026-09-25 → 2026-09-27) — ಪ್ರತಿ ಶನಿವಾರ ವಿಶೇಷ ಸೆಗ್ಮೆಂಟ್ ದಿನ ('ಕಾನೂನು ಕವಚ' — Kanoonu Kavacha; ಪ್ರಸ್ತುತ ಹೆಣ್ಣುಮಕ್ಕಳ ಸೈಬರ್ & ಡಿಜಿಟಲ್ ರಕ್ಷಣೆ, ಕಾನೂನು ಅರಿವು). ವಿಶೇಷ ಸರಣಿಯ ಕ್ಯಾರೋಸೆಲ್‌ಗಳಲ್ಲಿ ಕೇವಲ ಸಲಹೆಯಷ್ಟೇ ಅಲ್ಲದೆ, ನೈಜ ಕೇಸ್ ಸನ್ನಿವೇಶ, ಕಿರುಕುಳ ನೀಡುವವರಿಗೆ ಕಠಿಣ ಕ್ರಿಮಿನಲ್ ಪರಿಣಾಮಗಳ ಎಚ್ಚರಿಕೆ ಹಾಗೂ ಸಂತ್ರಸ್ತರಿಗೆ ನಿಖರ ಪರಿಹಾರ ಕ್ರಮಗಳನ್ನು ಒಳಗೊಂಡಿರಬೇಕು.
  - Editor standing instruction (2026-09-25): Saturdays are dedicated to the Special Segment (currently female safety under 'ಕಾನೂನು ಕವಚ'). Pitch and produce case-driven deterrent + empowerment carousels.  · retired: D92: ಕಾನೂನು ಕವಚ Saturdays are deleted; the channel makes three news formats only
- ~~2026-09-25-04~~ (2026-09-25 → 2026-09-27) — Universal Carousel Visibility & Special Segment Branding (D89): 1) Every field in Story JSON (headline, deck, points) MUST be rendered visually on carousel slides (zero phantom data). When points are present, deck must be a concise 1-2 line lead-in (max_lines=2) so key facts and consequences ('ವಾಸ್ತವ') render as gold-numbered fact points. PUB-10 strictly fails the build if content overflows the card. Never write copy in JSON that cannot visually fit on the card. 2) Special segments (e.g. Kanoonu Kavacha) must never inherit coastal bulletin boilerplate: masthead wears the segment strapline, cover counter reads '{n} ಅಂಶಗಳು', closing slide shows 'ಹೆಚ್ಚಿನ ಮಾಹಿತಿ & ಜಾಗೃತಿಗಾಗಿ' with segment badge, and hashtags/captions are topic-driven (no #ಕರಾವಳಿಸುದ್ದಿ or #ಕರಾವಳಿ).
  - Editor demand for universal lifetime solution (2026-09-25): prevent half-baked carousel slides with missing points/reality and prevent inappropriate coastal boilerplate on special awareness segments (D89).  · retired: D92: the old carousel and the ಕಾನೂನು ಕವಚ segment branding are deleted (see D93)
