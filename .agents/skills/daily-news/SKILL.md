---
name: daily-news
description: >
  Daily newsroom automation for ಊರ್ಮನಿ ಸುದ್ದಿ. Activates whenever the editor pastes news,
  says "start today", "stop yesterday and start today", or brings daily news items to produce.
  Handles archiving yesterday, source saving, fact checking, desk receipts, verification,
  rendering, and caption handover.
---

# Daily News Production — ಊರ್ಮನಿ ಸುದ್ದಿ

> **Trigger**: The editor pastes news stories (e.g. from Udayavani, Prajavani, Vijay Karnataka, etc.),
> or says "start today", "stop yesterday and start today".
> **Formats**: `saara` (ಸುದ್ದಿ ಸಾರ text carousel, 2–6 stories, no photos),
> `mukhya` (ಮುಖ್ಯ ಸುದ್ದಿ 4:5 photo carousel, 1 top story, always photo),
> `speed` (ಸ್ಪೀಡ್ ನ್ಯೂಸ್ 9:16 reel, 3+ stories).

---

## The 4-Step Daily Pipeline

### Step 1: Intake & Archive

When the editor says "Stop yesterday and start today" and pastes news copy:

1. **Archive yesterday** (never delete edition JSON):
   ```bash
   python3 scripts/daily_flow.py archive-yesterday
   ```

2. **Save pasted sources and auto-extract factcheck claims**:
   Pipe the pasted text into `daily_flow.py intake`:
   ```bash
   python3 scripts/daily_flow.py intake << 'EOF'
   <paste content>
   EOF
   ```
   This automatically:
   - Detects the news outlet from the URL (e.g. Udayavani, Vijay Karnataka).
   - Saves source text in `inbox/sources/<digest>.txt`.
   - Extracts number words ("ಆರುನೂರು" -> 600, "ಹದಿನಾರು" -> 16, "ನಾಲ್ಕು" -> 4) with their source sentences into `inbox/factcheck/<DATE>.json` so fact checks pass seamlessly.

---

### Step 2: Draft the Edition & Preflight

Write `editions/<DATE>.json` (schema_version 4) respecting the character budgets:
- **Headlines**: maximum 78 characters (`tokens.Limits.headline_chars_carousel`). Crime headlines MUST carry `ಆರೋಪಿ` / `ಆರೋಪ` / `ಶಂಕಿತ` / `ಪ್ರಕರಣ ದಾಖಲು`.
- **Decks**: maximum 190 characters (`tokens.Limits.deck_chars_carousel`).
- **Points**: 3 points, each maximum 150 characters (`tokens.Limits.point_chars_carousel`).
- **Takeaway**: Actionable advisory or authority contact.
- **Numbers**: Latin numerals (`600`, `16`, `4`), never Kannada digits.

Check and preflight:
```bash
python3 scripts/intake.py seen editions/<DATE>.json
python3 scripts/fact_check.py editions/<DATE>.json
python3 render.py --check editions/<DATE>.json
```

---

### Step 3: Desks & Show Editor

1. **Run the desks** — they are not optional (OPS-04, D95). List what is due,
   batched into as few agent runs as possible:
   ```bash
   python3 scripts/daily_flow.py receipts      # shows the waves; files nothing
   ```
   Launch each wave as ONE message of parallel Agent calls, one per line shown
   (fact desk + legal + reach desk first, then Kannada + picture). Each agent
   files its own receipts; no script does.

2. **Show the editor the 1-page summary**:
   Present each story with:
   - What happened
   - Location & Category
   - Source link
   - Flags (crime / minor / etc.)
   - Proposed segment (default `saara`)

3. **Ask the editor**:
   - Are the segments right?
   - If any `mukhya` story: "Real photo or generate?"
   - Editor's name for verification (`verified_by`).

---

### Step 4: Approve, Render & Sign-off

When the editor gives their name (e.g. "approved by Gautam Paduvari"):

1. **Verify**:
   ```bash
   python3 scripts/daily_flow.py verify --by "<editor name>"
   ```

2. **Render**, then launch wave 3 (the inspectors and the copy desk):
   ```bash
   python3 scripts/daily_flow.py render --by "<editor name>"
   ```

3. **Handover**:
   - Point to `out/<DATE>/saara_caption.txt` for Instagram caption (ready to copy-paste).
   - Point to `out/<DATE>/whatsapp_kundapura_byndoor.txt` for WhatsApp broadcasts.
   - Instruct the editor to view `out/<DATE>/_review/feed_sizes.jpg` and sign:
     ```bash
     python3 scripts/sign_off.py out/<DATE> --by "<editor name>"
     ```
