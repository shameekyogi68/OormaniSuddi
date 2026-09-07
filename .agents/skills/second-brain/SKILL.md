---
name: second-brain
description: >
  Automated newsroom workflow for ಊರ್ಮನಿ ಸುದ್ದಿ. Activates on "start with content",
  runs 12 expert roles (Kannada Language, Sub-Editor, Photojournalism, Visual Culture & Legal
  Image Cross-Checker, Design QA, Content Manager, Broadcast Voiceover & News Anchor QA,
  Instagram & YouTube Audience Retention & Algorithm Expert, Social Media, Scheduling,
  Legal & YouTube Monetization Guardrail Expert, Final QA) in a review loop until 10/10,
  and produces a complete daily content package. Cleans up on "close".
---

# 🧠 Second Brain — ಊರ್ಮನಿ ಸುದ್ದಿ Automated Newsroom

> **Trigger**: User pastes raw news copy and types `start with content`
> (or: `start`, `begin`, `content ready`, `let's go`, `produce`)
>
> **Exit**: User types `close` (or: `done`, `cleanup`, `clear`)

---

## 0 · Before anything: load the rules

Read these files FIRST, every time — they are the law:

1. [`docs/AI_BRIEF.md`](file:///Users/shameekyogi/Oormani%20Suddi/docs/AI_BRIEF.md) — the JSON contract, template choice, hard limits, rejections
2. [`AGENTS.md`](file:///Users/shameekyogi/Oormani%20Suddi/AGENTS.md) — the five overriding rules, the standard workflow
3. [`STANDARDS.md`](file:///Users/shameekyogi/Oormani%20Suddi/STANDARDS.md) — brand design system (do not modify)

---

## 1 · The pipeline

When the user says **"start with content"**, execute these 12 expert steps in order.
The loop controllers (Step 4, Step 8, Step 11, and Step 12) loop back to earlier steps until every dimension is an undisputed 10/10.

### Constants for this run

```
DATE         = today's date, YYYY-MM-DD
DAILY_DIR    = out/{DATE}
DAILY_ASSETS = assets/daily/{DATE}
EDITION_FILE = editions/{DATE}.json
EDITION_NO   = (last edition_no in editions/) + 1
```

### Deliverable Scope & Targeted Output (Deliver ONLY what the user asks for)

- **Default / Daily Focus**: Everyday publishing primarily focuses on **Carousel + Reels**.
- **Deliverable Filtering**:
  - If the user specifies formats (e.g. *"only carousel and reel"*, *"just reels"*, *"only carousel"*):
    - **Carousel + Reels**: `python3 render.py editions/{DATE}.json --only carousel reel --out out/{DATE}`
    - **Reels only**: `python3 render.py editions/{DATE}.json --only reel --out out/{DATE}`
    - **Carousel only**: `python3 render.py editions/{DATE}.json --only carousel --out out/{DATE}`
  - If user explicitly requests the entire package (*"all"* / *"full package"*): run without `--only` (adds bulletin, broadsheet, story card, posts).
- **Zero Clutter Output**: Do NOT render, build, or present copy for formats not requested. In `MASTER_COPY.md` and the final response, present **ONLY** the copy, captions, and schedules for the specific deliverables requested.

---

### STEP 1 — ಕನ್ನಡ ಭಾಷಾ ತಜ್ಞ (Kannada Language Expert)

**Role**: Transform raw copy into publication-ready Kannada.

**Rules — non-negotiable:**
- Headlines: ≤78 characters, natural spoken Kannada, no padded officialese
- `reel_line`: ≤46 characters, punchy, self-contained
- `hook`: ≤7 words (for lead story ONLY, story index 0)
- `deck`: ≤190 characters
- `points`: max 3 items, each ≤150 characters
- Numerals: ALWAYS Latin (`25`, `1077`, `40-50`), NEVER Kannada (`೨೫`)
- Crime copy: allegation markers (ಆರೋಪ / ಆರೋಪಿ / ಶಂಕಿತ / ಪ್ರಕರಣ ದಾಖಲು) in BOTH `headline` AND `reel_line` independently
- No guilt assertions: "ಕೊಂದ ಪುತ್ರ" → "ಕೊಲೆ ಆರೋಪ, ಪುತ್ರ ಬಂಧನ"
- Write Kannada that a person actually says out loud

**Morphology check:**
- Case markers are BOUND morphemes: ಉಡುಪಿಯಲ್ಲಿ (correct), NOT ಉಡುಪಿ ನಲ್ಲಿ (wrong)
- Sandhi rules must be correct

**Output per story:**
```json
{
  "headline": "...",
  "reel_line": "...",
  "is_reel": true,     // true ONLY for 10/10 visual, breaking, or high-stakes stories; false for routine copy
  "hook": "...",       // lead story only
  "category": "...",   // one of: breaking, crime, weather, civic, health, education, culture, sport, farm, obituary, explainer
  "deck": "...",
  "points": ["...", "...", "..."],
  "takeaway": "...",
  "location": "...",
  "dateline": "...",
  "sources": ["..."],
  "status": "confirmed|developing|unconfirmed|official",
  "published_at": "ISO 8601 with +05:30"
}
```

---

### STEP 2 — ಸಂಪಾದಕ (Sub-Editor & 10/10 Reel Gatekeeper)

**Role**: Editorial integrity gate & short-form video gatekeeper.

**Checklist — every story must pass ALL:**
- [ ] `sources` is not empty and not invented — if unknown, ASK the user
- [ ] `status` accurately reflects confirmation level
- [ ] Crime stories: `headline` carries its own allegation marker (checked standalone)
- [ ] Crime stories: `reel_line` carries its own allegation marker (checked standalone)
- [ ] `involves_minor: true` set where applicable
- [ ] `sexual_offence: true` set where applicable
- [ ] `convicted: true` ONLY if a court actually convicted (never assume)
- [ ] `published_at` is realistic for the story (affects breaking decay — 12h window)
- [ ] No facts, sources, quotes, or credits are invented to fill required fields
- [ ] Obituary stories: tone is respectful, no sensationalism
- [ ] **10/10 Reel Editorial Filter (News Expert Judgement)**:
  - **The Carousel and Post cards carry the full edition** — every story is covered there.
  - **Reels are algorithmic assets requiring maximum completion rate**.
  - Evaluate each story: Is it a true **10/10 Reel**?
    - High visual drama (coastal storm, rescue, sea erosion, crime scene, big event)
    - High public stakes (weather red/orange alerts, major safety warnings)
    - High shareability / "Did you hear?" factor (provokes immediate WhatsApp forwards)
  - If YES (10/10) → `is_reel: true` (creates `reel_*.mp4`)
  - If NO (routine civic notice, date extension, administrative order, dry tender) → `is_reel: false`. **Ignore for reels**; forcing routine news into video tanks watch time and penalizes account distribution.

**If any item fails**: fix it in the story data and re-run Step 1 checks on the modified copy.

---

### STEP 3 — ಛಾಯಾಗ್ರಾಹಕ (Photojournalism Expert)

**Role**: Generate credible editorial images and multi-scene gallery photos.

**Decision tree per story:**

```
Can realistic, credible photojournalistic images be generated for this specific story?
├── YES → generate_image with photojournalistic prompt for hero photo AND gallery scene photos
│         Set: nature='ai'
│              credit='AI ಚಿತ್ರ — ಊರ್ಮನಿ ಸುದ್ದಿ'
│              licence='own'
│              caption='<honest description of what the image depicts>'
│              focal=[x, y] (0.0-1.0, where the subject is)
│         Save to: assets/daily/{DATE}/story_{N}.jpg and story_{N}_gallery_{K}.jpg
│
└── NO  → omit `photo` entirely
          The story gets text_card (branded plate) — this is CORRECT
          NEVER attach a loosely related or decorative image
```

**Image generation rules:**
- The image must be believable as a real photograph of the scene
- It must match the SPECIFIC location and context of the story
- A Brahmāvara story must NOT show a Honnavar bridge — this is THE failure the system prevents
- Weather images: show the actual geography (coastal Karnataka, specific town if named)
- Crime images: show location/area context, NEVER show identifiable faces or victims
- Civic/health images: show relevant institutions, buildings, contexts
- Generate at high quality, suitable for 1080×1080 and 1080×1920 crops

**Multi-Scene Gallery for 10/10 Reels:**
- Generate 3 additional scene photographs per reel story (`gallery` list in JSON) corresponding to each story chapter:
  - Chapter 1: Main hook scene
  - Chapter 2: Ground reality / specific incident scene
  - Chapter 3: Official investigation / emergency response / cultural ritual detail
  - Chapter 4: Public context / outcome / highway clearance
- This gives reels continuous visual novelty every 12–15s, eliminating viewer boredom.

---

### STEP 4 — ದೃಶ್ಯ ಸಂಸ್ಕೃತಿ ಹಾಗೂ ಕಾನೂನು ಪರಿಶೀಲಕ (Visual Culture, Ethics & Legal Image Cross-Checker Expert)

**Role**: Mandatory cross-checking gate for every generated photograph. Inspects imagery for absolute topic fidelity, deep cultural respect, and Indian media law compliance.

**Auditing Contract — Every Image Must Score a True 10/10:**
1. **Topic Fidelity & Zero Generic Drift**:
   - Is the image 100% on-topic for the specific story?
   - Does it accurately portray Coastal Karnataka geography, architecture, signage, and environmental context?
   - Reject any generic American/European stock aesthetic or mismatched Indian regional cues.
2. **Cultural Sanctity & Religious Dignity (ಕರಾವಳಿ ಸಂಸ್ಕೃತಿಯ ಪಾವಿತ್ರ್ಯತೆ)**:
   - Zero tolerance for distortions, grotesque AI rendering, or mockery of sacred regional traditions (e.g. Sri Krishna Matha rituals, Rathothsava, Mosaru Kudike, Hulivesha, Yakshagana, Daivaradhane/Bhoota Kola).
   - Religious elements, priests, traditional dhotis, ceremonial umbrellas, and temple car street customs must be represented with authentic reverent dignity.
3. **Legal Compliance & Ethical Journalism**:
   - **POCSO & Juvenile Justice Act**: Absolutely NO identifiable faces or depictions of minors in crime, accident, or sensitive situations.
   - **Victim & Accused Identity**: Strictly no identifiable faces of accident victims or unconvicted crime suspects (Section 228A IPC/BNS).
   - **Decency & Dignity**: Zero graphic gore, bloodbaths, mutilated corpses, or sensationalist trauma.
4. **Honesty & Licensing Integrity**:
   - Must carry truthful metadata: `nature: 'ai'`, `credit: 'AI ಚಿತ್ರ — ಊರ್ಮನಿ ಸುದ್ದಿ'`, `licence: 'own'`, and a precise, descriptive `caption`.

**10/10 Review Loop**:
- If an image fails ANY criterion (e.g. awkward AI artifacts, cultural inaccuracy, legal concern, or thematic drift) → **Score < 10/10**.
- Reject the image, provide exact actionable feedback, and loop back to **Step 3 (Photojournalism Expert)** to regenerate.
- **Only when this expert explicitly certifies 10/10 PERFECT is the image cleared for layout.**

---

### STEP 5 — ವಿನ್ಯಾಸಕ (Design QA Expert)

**Role**: Validate the design system produces clean output.

**Actions:**

```bash
# 1. Create assets directory
mkdir -p assets/daily/{DATE}

# 2. Save edition JSON
# (already built from Steps 1-4)

# 3. Preflight check
python3 render.py --check editions/{DATE}.json
```

**If preflight fails (`✗`):**
- Read the error messages
- Route back to the appropriate expert:
  - Missing credit/caption/licence → Step 3 & 4
  - Headline too long → Step 1
  - Missing sources → Step 2
  - Unknown field → fix the JSON structure

**If preflight warns (`!`):**
- Evaluate whether the warning needs fixing
- Deck >190 chars → send back to Step 1 for tighter writing
- Otherwise note and continue

**If preflight clean:**
- Proceed to Step 6

---

### STEP 6 — ವಿಷಯ ವ್ಯವಸ್ಥಾಪಕ (Content Manager)

**Role**: Run targeted render for the requested formats and verify deliverables.

**Actions:**

```bash
# Targeted render (e.g. only carousel and reel, or as requested):
python3 render.py editions/{DATE}.json --only carousel reel --out out/{DATE}

# Or full render if explicitly asked:
python3 render.py editions/{DATE}.json --out out/{DATE}
```

**Verify requested files exist (based on --only scope):**

```
out/{DATE}/
├── carousel_01_cover.jpg .. carousel_06_sources.jpg     # if carousel requested
├── carousel_copy.txt + .json
├── reel_01.mp4 + reel_01_cover.jpg + reel_01_copy.txt   # if reels requested (10/10 stories)
├── reel_02.mp4 + reel_02_cover.jpg + reel_02_copy.txt
├── schedule.txt + schedule.json                         # generated timetable for rendered assets
└── MASTER_COPY.md                                       # targeted copy for requested assets only
```

**Output audit** (printed by render.py):
- Must show "✓ every file clean"
- If any audit finding → investigate and fix (bad focal point, oversized, etc.)

---

### STEP 7 — ವಾರ್ತಾವಾಚನ ಹಾಗೂ ಧ್ವನಿ ಪರಿಣಿತೆ (Broadcast Voiceover & News Anchor QA Expert)

**Role**: Listen to and audit every audio version of the news narration until a true 10/10 Kannada television news anchor quality is achieved.

**Engine standard**:
- **Primary Engine**: Google Native Indic Kannada TTS (`tl=kn`) powered by sentence-level prosodic chunking and broadcast pace tuning (`atempo=1.15` via ffmpeg) for punchy television delivery.
- **Neural Alternate**: `kn-IN-SapnaNeural` (`rate='+5%'`) with regional newsroom cadence.
- **Strict Prohibition**: Foreign or un-phoneticized Dravidian models (e.g. raw Gemini multingual voices without Kannada phonetic dictionary) that distort Kannada *ಒತ್ತಕ್ಷರಗಳು* or pronounce Kannada phonemes like foreign/Urdu sounds are STRICTLY PROHIBITED.

**News Reader Scriptwriting Contract (`narration_script`):**
Raw bullet points, colons (`:`), semicolons (`;`), and print-copy dashes (`-`) sound unnatural and glitchy when spoken. The Voiceover Expert transforms each 10/10 story into an authentic TV broadcast news copy:
1. **Anchor Hook & Greeting**: Opens like a prime-time television broadcast (*"ನಮಸ್ಕಾರ, ಊರ್ಮನಿ ಸುದ್ದಿಯ ಪ್ರಮುಖ ವರದಿ..."*).
2. **Conversational Flow**: Weaves isolated facts into complete spoken sentences with broadcast connectors (*"ಇನ್ನು...", "ಇದೇ ವೇಳೆ...", "ಈ ನಡುವೆ..."*).
3. **Regional Phonetics**: Accurately handles Coastal Karnataka place-names (Gangolli, Mullikatte, Kundapura, Udupi, Brahmavara, Siddapura).
4. **Broadcast Sign-off**: Signature newsroom closing (*"ಕ್ಷಣ ಕ್ಷಣದ ನಿಖರ ಕರಾವಳಿ ಸುದ್ದಿಗಳಿಗಾಗಿ ಊರ್ಮನಿ ಸುದ್ದಿ ಫಾಲೋ ಮಾಡಿ."*).

**Audio Mix & Mastering Standards:**
- **Voice Level**: Mastered loud, clear, and centered (-14 LUFS target).
- **News BGM Ducking**: Background newsroom bed automatically ducked to 22% (`volume=0.22`) during spoken narration, swelling to full volume only during intro/outro brand stings.
- **Auditory Verification**: The expert verifies intelligibility, cadence, and anchor realism. If the narration sounds robotic, hesitant, or lacks journalistic authority, the expert rejects the take and rewrites the script for a fresh synthesis until it hits 10/10.

---

### STEP 8 — ಪ್ರೇಕ್ಷಕರ ಪ್ರತಿಕ್ರಿಯೆ ಹಾಗೂ ಅಲ್ಗಾರಿದಮ್ ತಜ್ಞ (Instagram & YouTube Shorts Audience Retention & Algorithm Expert)

**Role**: Evaluate the entire reel and content package through the eyes of an Instagram and YouTube Shorts consumer. Loops continuously until the content scores an undisputed 10/10.

**Auditing Contract — Every Deliverable Must Score 10/10:**
1. **First 3 Seconds Hook Power**:
   - Does Frame 0 instantly stop the thumb scroll in high-speed feed scrolling?
   - Is the headline text bold, high-contrast, and effortlessly readable on a 6-inch phone?
   - Does the anchor's opening voiceover line spark instant curiosity without dragging?
2. **Dynamic Visual Rhythm & Anti-Monotony**:
   - **Zero Visual Freezes**: The video must NEVER show a single fixed image for 60+ seconds.
   - **Multi-Scene Chapters**: Every 12–15 seconds, the visual must cut to a new distinct scene photo with smooth Ken Burns motion and subtle audio whooshes.
   - **Clean Top Header**: No cluttered or distracting numbered badges at the top; only the clean, elegant masthead and dateline.
3. **Audio-Visual Pacing & Clarity**:
   - Do on-screen lower-third fact cards match the spoken narration points in real-time?
   - Is the background music ducked cleanly so speech is 100% crisp and intelligible on phone speakers?
   - Does the outro animate smoothly with living continuous scale, avoiding any "stuck" or frozen frame?
4. **High-Engagement Triggers & Algorithm Reach**:
   - Does the news package inspire immediate regional sharing (WhatsApp forwards / Instagram DM shares)?
   - Does the First Comment pose a genuine regional debate question to drive comment replies (vital algorithmic signal)?

**10/10 Review Loop**:
- If any aspect feels boring, text is cluttered, pacing drags, or hook is weak → **Score < 10/10**.
- Reject the video, outline exact structural adjustments, and loop back to the responsible step (Step 1 Copy, Step 3 Photos, or Step 7 Voiceover).
- **Only when the Audience Expert certifies a solid 10/10 is the content permitted to advance.**

---

### STEP 9 — ಸಮಾಜಿಕ ಜಾಲತಾಣ ತಜ್ಞ (Social Media Expert)

**Role**: Compile, review, and optimise all platform copy.

**Build `MASTER_COPY.md`** in `out/{DATE}/` using the template at:
`templates/MASTER_COPY_TEMPLATE.md` (in this skill folder)

**For each reel and the carousel, include:**

| Platform | Content |
|----------|---------|
| Instagram Caption | From `*_copy.txt` — review for algorithm optimisation |
| Instagram First Comment | Paste IMMEDIATELY after posting — this is the engagement signal |
| YouTube Shorts Title | <60 chars for mobile display, search-optimised |
| YouTube Description | Lead with the news, not the brand. Include snippet and sources |
| YouTube Tags | From `*_copy.json` — verify specificity ordering |
| WhatsApp Forward | Clean text, no emoji boxes, no hashtags |
| X Post | Under 280 chars with @OormaniSuddi |

**Algorithm optimisation review:**
- First line of every caption must earn the tap (Instagram fold = ~125 chars)
- Hashtags: 8 max, specificity-ordered (place → category → brand → wide)
- CTA matches the story category (crime → share, weather → comment, etc.)
- First comment is a QUESTION that drives replies, not a restatement

---

### STEP 10 — ವೇಳಾಪಟ್ಟಿ ತಜ್ಞ (Scheduling & Analytics Expert)

**Role**: Validate and present the publishing schedule.

**Read** `out/{DATE}/schedule.txt` and `out/{DATE}/schedule.json` (auto-generated by render.py).

**Validate:**
- Bulletin goes up FIRST (08:30) — it needs the whole day for watch time
- Carousel at 09:00 — the morning scroll window
- Story card at 09:15 — drives to the carousel that already exists
- Reels spaced ≥2.5 hours apart (11:30, 15:30, 19:00, 21:30)
- Broadsheet at 20:00 — end-of-day forward

**Include the complete schedule in MASTER_COPY.md** with:
- Exact posting times (IST)
- Which file to upload
- Which platform
- The copy file to use
- Any cover frames to set

---

### STEP 11 — ಕಾನೂನು ಹಾಗೂ ಯೂಟ್ಯೂಬ್ ಮಾನಿಟೈಸೇಷನ್ ರಕ್ಷಕ (Legal, Copyright & YouTube Monetization Guardrail Expert)

**Role**: Absolute pre-publishing audit of YouTube advertiser-friendly guidelines, Content ID copyright protection, Indian digital media laws, and Meta monetization policies. Guarantees 0 demonetization strikes, 0 copyright claims, and 0 legal liabilities.

**Contract & Audit Checklist — Must Score 10/10 to Approve:**
1. **YouTube Advertiser-Friendly Guidelines (AdSense "Green Dollar" Guarantee)**:
   - **Violence & Sensitive Events**: News reporting on accidents, crime, or civic disasters must use matter-of-fact, objective language. Absolutely ZERO depictions of blood, open wounds, bodily fluids, gore, or trapped victims in visuals or thumbnails. No sensationalized "shock" clickbait.
   - **Safe Language & Profanity**: Zero vulgarities or offensive colloquialisms. Strictly dignified news language.
   - **Originality & Reused Content Policy**: Reused static image slideshows without commentary get demonetized by YouTube. Our package features full original human-sounding TV news anchor voiceovers + multi-image narrative progression, establishing 100% eligibility for YouTube Partner Program (YPP) revenue sharing.
2. **Copyright & Content ID Shield**:
   - **Zero Copyright Claims**: All background music is in-house royalty-free audio (`assets/news_bgm.mp3`), sound effects are open/proprietary broadcast beds (`sfx/`), and visual assets carry verified `own` licenses. Zero risk of Content ID audio mutes or revenue redirection.
3. **Indian Media Law & Digital Publisher Safeguards**:
   - **IT Rules 2021 Part III**: Publisher transparency and Grievance Officer details are actively maintained.
   - **POCSO Act & Juvenile Justice Act**: Absolute ban on naming or identifying minors in any distress or crime report.
   - **Section 228A IPC / Section 72 BNS**: Absolute protection of victims of sexual or gender offences.
   - **Presumption of Innocence & Contempt of Court**: Crime copy strictly uses allegation markers (*ಆರೋಪ, ಆರೋಪಿ, ಶಂಕಿತ, ಪ್ರಕರಣ ದಾಖಲು*). No headline implies guilt prior to judicial verdict.
   - **Public Order & Harmony (Section 153A, 499/500 IPC/BNS)**: Factual reporting verified by police or official sources. Zero hate speech, communal bias, or defamatory unverified rumors.

**10/10 Review Loop**:
- If any title, script sentence, image, or audio asset poses even a slight risk of demonetization (Yellow Dollar), copyright claim, or legal vulnerability → **Score < 10/10**.
- Reject the build, provide specific compliance edits, and loop back to the responsible step (Step 1 Copy, Step 3 Photos, or Step 7 Voiceover).
- **Only when the Monetization & Legal Expert certifies an unequivocal 10/10 GREEN DOLLAR rating is the edition cleared for final QA.**

---

### STEP 12 — ಗುಣಮಟ್ಟ ನಿಯಂತ್ರಕ (Final QA / Master Loop Controller)

**Role**: The gatekeeper. Reviews EVERYTHING across all 11 preceding roles. Loops until 10/10 perfection is verified.

**10/10 Checklist:**

```
LANGUAGE
  □ All Kannada is natural, grammatically perfect
  □ All headlines ≤78 chars, reel_lines ≤46 chars, hooks ≤7 words
  □ Latin numerals only, no Kannada numerals
  □ Proper sandhi and vibhakti (bound morphemes)

EDITORIAL
  □ Every story has real sources (not invented)
  □ 10/10 Reel Gatekeeper: only true 10/10 stories set is_reel=true
  □ Crime stories: allegation markers in headline AND reel_line independently
  □ No guilt assertions anywhere

VISUAL CULTURE & LEGAL IMAGE CROSS-CHECK (10/10 CERTIFIED)
  □ Every image is 100% relevant and geographically true to coastal Karnataka
  □ Zero cultural or religious insensitivity; sacred traditions treated with utmost reverence
  □ Zero minor or accident/crime victim faces; full legal compliance
  □ Honest metadata (nature: 'ai', credit, licence: 'own', accurate caption)

DESIGN & RENDERING
  □ render.py --check passed clean
  □ Output audit clean (✓ every file clean)
  □ Clean top masthead (no cluttered numbered capsules)
  □ Multi-image chapter cuts in reels (no single-image visual freezes)

AUDIO & BROADCAST ANCHOR (10/10 CERTIFIED)
  □ Authentic Kannada TV news anchor delivery (Google Native Indic TTS at 1.15x pace or SapnaNeural)
  □ Zero foreign phonetic distortions or broken ಒತ್ತಕ್ಷರಗಳು
  □ Conversational TV flow with anchor greeting and signature sign-off
  □ Background news music cleanly ducked to 22% during voiceover; crisp -14 LUFS mastering

AUDIENCE RETENTION & ALGORITHM (10/10 CERTIFIED)
  □ 3-second hook grabs phone scroller immediately
  □ Visual stimuli cut every 12–15s with smooth Ken Burns motion and micro-whooshes
  □ Living animated outro with zero frozen/stuck frame
  □ High-retention narrative structure engineered for 100%+ completion

LEGAL & YOUTUBE MONETIZATION GUARDRAILS (10/10 CERTIFIED)
  □ AdSense Green Dollar compliant (zero gore, zero sensationalism, ad-friendly tone)
  □ Zero Content ID copyright risks (all audio/visuals own/royalty-free)
  □ Full Indian media law compliance (POCSO, Sec 228A IPC/BNS, IT Rules 2021)
  □ Allegation discipline verified (presumption of innocence preserved)

COPY & SCHEDULE
  □ Instagram captions optimised (hook before fold, category CTA)
  □ First comments are engagement questions that drive replies
  □ YouTube titles <60 chars and search-optimised
  □ Schedule timings validated with coastal Karnataka engagement peak windows

MASTER_COPY.md
  □ All sections populated and ready for copy-paste
  □ Schedule section complete
```

**Loop logic:**
```
IF any item fails:
    Identify which expert owns the fix
    Route back to that step
    Re-run from that step forward
    Return to Step 12

IF all items pass:
    Declare: "✅ 10/10 — ಎಲ್ಲಾ ಸಿದ್ಧ. out/{DATE}/ ರಲ್ಲಿ ನೀವು ಕೇಳಿದ ಕಂಟೆಂಟ್ ಮಾತ್ರ ಸಿದ್ಧವಾಗಿದೆ."
    Present MASTER_COPY.md summary to user with ONLY the requested formats (e.g. Carousel and Reels)
    STOP — wait for "close" or new instructions
```

---

## 2 · The `close` command

When the user types **`close`** (or `done`, `cleanup`, `clear`):

```python
# Delete the heavy media — keep the editorial record
import shutil, os

date = "YYYY-MM-DD"  # today's date

# 1. Delete output folder (all rendered media)
shutil.rmtree(f"out/{date}", ignore_errors=True)

# 2. Delete daily AI-generated images
shutil.rmtree(f"assets/daily/{date}", ignore_errors=True)

# 3. Keep editions/{date}.json — it's the editorial record
# (lightweight JSON, no storage concern)

print(f"✓ Cleaned up: out/{date}/ and assets/daily/{date}/")
print(f"✓ Kept: editions/{date}.json (editorial record)")
```

**Confirm to user:**
> ✅ ಇಂದಿನ ಕಂಟೆಂಟ್ ಡಿಲೀಟ್ ಮಾಡಲಾಗಿದೆ. ಎಡಿಷನ್ JSON ಉಳಿಸಿಕೊಳ್ಳಲಾಗಿದೆ.

---

## 3 · Edition number auto-increment

```python
import glob, json

existing = sorted(glob.glob("editions/*.json"))
if existing:
    with open(existing[-1]) as f:
        last = json.load(f)
    edition_no = last.get("edition_no", 0) + 1
else:
    edition_no = 1
```

---

## 4 · Daily folder structure

Everything for one day lives in predictable paths:

```
editions/{DATE}.json              ← editorial record (KEPT on close)
assets/daily/{DATE}/              ← AI-generated images (DELETED on close)
  ├── story_01.jpg
  ├── story_02.jpg
  └── ...
out/{DATE}/                       ← all rendered deliverables (DELETED on close)
  ├── post_*.jpg + *_copy.*
  ├── carousel_*.jpg + carousel_copy.*
  ├── story_9x16.jpg
  ├── yt_thumbnail.jpg
  ├── broadsheet.jpg
  ├── reel_*.mp4 + *_cover.jpg + *_copy.*
  ├── bulletin.mp4 + bulletin_copy.*
  ├── schedule.txt + schedule.json
  └── MASTER_COPY.md
```

---

## 5 · What this skill does NOT do

- ❌ Does not modify `brand/`, `templates/`, or `render.py`
- ❌ Does not write rendering code (Pillow, canvas, HTML-to-image)
- ❌ Does not hard-code colours, font sizes, or margins
- ❌ Does not invent facts, sources, quotes, or credits
- ❌ Does not suppress provenance labels
- ❌ Does not override `Story.validate()`
- ❌ Does not assert `category: "breaking"` — it's computed from timestamp
