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
- **2026-09-17-01** — When picking which tips to auto-draft each morning, prefer taluks in this order: ಕುಂದಾಪುರ (Kundapura) and ಬೈಂದೂರು (Byndoor) highest, then ಉಡುಪಿ (Udupi) and ಮಣಿಪಾಲ (Manipal), then ಕಾರ್ಕಳ (Karkala), ಬ್ರಹ್ಮಾವರ (Brahmavara), ಹೆಬ್ರಿ (Hebri), ಕಾಪು (Kaup), ಮಂಗಳೂರು (Mangalore).
  - _why:_ editor's own priority ranking of the coverage area, 2026-09-17
  - _asked by:_ Gautam Paduvari
- **2026-09-17-04** — Every story in a daily bulletin must have a comprehensive Kannada news description (deck). A carousel is not a headline ticker; the deck explains who, what, where, and why below the headline.
  - _why:_ Editor standing instruction (2026-09-17): carousel slides must never be headlines-only; deck is mandatory.
- **2026-09-17-07** — For daily carousel and bulletin editions, hashtags must include all locations (taluks/places) and categories from all stories featured in the edition, not just the lead story.
  - _why:_ Editor standing instruction (2026-09-17): carousel hashtags must represent all news places and categories covered in the edition.
- **2026-09-17-08** — WhatsApp group and broadcast messages must follow the tailored format: 🌾 *ಊರ್ಮನಿ ಸುದ್ದಿ · {date}*, tagline, numbered items with place names (1️⃣ *ಸ್ಥಳ*: ಸುದ್ದಿ), and '📲 *ಪೂರ್ಣ ವರದಿ ಹಾಗೂ ವಿವರಣೆಗಾಗಿ ಇನ್‌ಸ್ಟಾಗ್ರಾಮ್ ಲಿಂಕ್ ನೋಡಿ:*'. NEVER write 'ಫೋಟೋಗಳು' or 'photos' when using AI-generated imagery.
  - _why:_ Editor standing instruction (2026-09-17): exact approved WhatsApp group/broadcast format.
- **2026-09-18-01** — Before asking for approval or 'go' on the morning draft, always ask the editor if they have any additional news, press releases, or info to add to today's edition.
  - _why:_ Editor preference: ensure any spot news, local tips or press releases from the editor are incorporated before rendering.

## picture

- **2026-09-16-01** — ಹಬ್ಬದ ಕಾರ್ಡ್‌ನಲ್ಲಿ ಸಂಘಟಕರ ಹೆಸರು ಕಡ್ಡಾಯ — ಪೋಸ್ಟರ್‌ನಿಂದ ಅಲ್ಲ, ಸಂಘಟಕರಿಂದಲೇ ಪಡೆಯಿರಿ
  - _why:_ organisers reshare what credits them; a name off a poster is how ಸೇನೇಶ್ವರ happened
  - _asked by:_ Gautam Paduvari
- **2026-09-17-03** — Every carousel slide must have a photo (100% visual photo coverage). No carousel story slide may be published without an image; always pick a matching evergreen photo from assets/stock/ or generate a fresh AI image in chat.
  - _why:_ Editor standing instruction (2026-09-17): no carousel slide should ever be without an image.
- **2026-09-17-05** — Photo disclosure must never duplicate 'ಎಐ ರಚಿತ ಚಿತ್ರ' or 'AI ಚಿತ್ರ'. Photo.disclosure automatically prepends the nature label. The caption must only describe the visual scene, and credit must just be 'ಊರ್ಮನಿ ಸುದ್ದಿ' without repeating 'AI ಚಿತ್ರ'.
  - _why:_ Editor standing instruction (2026-09-17): avoid repetitive stutter of AI image labels on disclosure lines.

## package

- **2026-09-17-06** — Every post that gets rendered also gets its own caption file — {post}_caption.txt — containing the caption and nothing else: no headings, no first comment, no WhatsApp forward. A YouTube post gets TITLE / DESCRIPTION / TAGS instead, because a title cannot be pasted into a description box. The working sheet stays in _copy.txt and MASTER_COPY.md.
  - _why:_ posting is select-all-and-paste on a phone; anything else in the file is something that eventually gets pasted with it
  - _asked by:_ Gautam Paduvari
- **2026-09-18-02** — The daily render is the carousel plus ONE reel. With 3 or more stories that reel is ಸ್ಪೀಡ್ ನ್ಯೂಸ್ (render.py --only roundup): a place and one line per story, spoken by the anchor while it is on screen, under 45 seconds. On a thin day of 1-2 stories, the lead-story reel only if scripts/pick_formats.py says the lead earns it. Never both reels. story_card and broadsheet stay out of the default.
  - _why:_ editor's instruction 2026-09-18: news reels should be quick news; supersedes 2026-09-17-02, which said a reel is never a default
  - _asked by:_ Gautam Paduvari

## Retired

Kept, because knowing a rule was dropped and when is worth more than a tidy file.

- ~~2026-09-17-02~~ (2026-09-17 → 2026-09-18) — Daily default render is carousel only. story_card and broadsheet are dropped entirely — carousel already covers that ground, and every extra format is more time spent posting. A reel is never a default; render one only when scripts/pick_formats.py says the lead story earns it (brand.reach.should_be_reel, D72).
  - editor's own observed performance: carousel outperforms, extra formats waste posting time  · retired: superseded by the speed-news daily reel rule of 2026-09-18 (D81); its carousel-only and no story_card/broadsheet parts are restated there
