To level up the ಊರ್ಮನಿ ಸುದ್ದಿ newsroom without incurring significant software licensing fees or overwhelming your single 8 GB M1 Mac, you can leverage lightweight open-source tooling, Apple Silicon hardware acceleration, and targeted automation patterns.

---

### 1. Artificial Intelligence and Ingestion Upgrades

#### Eliminate Hallucination via Two-Stage Scraping

The current vulnerability in `scripts/fetch_daily_news.py` stems from sending bare headlines to Gemini and asking it to extrapolate detailed journalistic paragraphs.

* **Free Solution:** Upgrade the scraper with an open-source body extractor such as `trafilatura` or `newspaper3k` (both free, lightweight Python packages). When a headline is scraped from Udayavani or OneIndia, follow the link and extract the main article text before invoking the LLM.


* **Extraction-Only Prompting:** Pass the raw article body into Gemini with a strict system constraint: *"Extract and summarize only the facts present in the source text into pure formal Kannada. Do not extrapolate, infer, or invent unnamed officials, hospital details, or vehicle models. If details are missing, omit them."*
* **Structured Output Mode:** Use Gemini’s native `response_schema` (JSON mode) to return an array of validated story objects matching your `content.py` schema directly, completely bypassing intermediate text parsing.



#### Local Speech-to-Text Auditing via `mlx-whisper`

Currently, pronunciation and narration-sync validation rely on human review or regex hazard checks.

* **Free Automation:** Run OpenAI’s Whisper locally using `mlx-whisper` (optimized specifically for Apple Silicon M1/M2/M3 using Apple's MLX framework).
* **Automated Audio Verification Gate:** Pass the rendered Google TTS WAV file into `mlx-whisper` (using the `tiny` or `base` multilingual model) to produce an automated Kannada transcript. Compute the Levenshtein distance between the generated audio transcript and the original text. If pronunciation drifts or words are skipped, the build gate fails before rendering video frames.



#### Local Visual Culture & AI Image Inspection

* **Multimodal Triage:** Use an open-source visual LLM running locally via Ollama (such as `moondream2` or `minicpm-v`, which require less than 2.5 GB of RAM).
* **Automated Cultural & Legal Compliance:** Automatically prompt the local vision model to inspect candidate photos or AI-generated stock before rendering: *"Does this image contain visible injuries, blood, children's faces, or distorted religious iconography?"* If the vision model detects violations, it triggers Step 4 rejection automatically.



---

### 2. Development & Hardware Performance (M1 8 GB Optimization)

Running Real-ESRGAN, MoviePy, and FFmpeg simultaneously on an 8 GB unified memory workstation leads to swap death and process terminations. The following architectural adjustments resolve these resource bottlenecks.

#### Enable Apple Silicon Hardware Video Acceleration (`VideoToolbox`)

* MoviePy and default FFmpeg builds frequently rely on CPU-bound software encoders (`libx264`) that consume large amounts of RAM and throttle the CPU cores.
* Configure FFmpeg to use Apple's dedicated hardware media encoding engine:
```bash
-c:v h264_videotoolbox -b:v 12M -profile:v high -pix_fmt yuv420p

```


`VideoToolbox` bypasses unified RAM and CPU crunching, reducing video export times by 60% to 80% while keeping machine temperatures cool.

#### Real-ESRGAN Tiling to Prevent Out-Of-Memory Crashes

* When processing Line B event footage, standard 4× upscaling of an entire frame buffer exhausts memory on 8 GB systems.


* Pass the `--tile 256` or `--tile 128` parameter to Real-ESRGAN. Tiling breaks video frames into smaller geometric patches, processes them in VRAM under 1.5 GB, and stitches them back together seamlessly, preventing `SIGKILL` terminations and SSD swap thrashing.



#### ChatOps: Free Telegram/WhatsApp Remote Control

Instead of tethering an editor to the Mac terminal to run commands like `start with content` or `render.py`:

* Build a lightweight bot using `python-telegram-bot` (100% free and open-source).
* When `fetch_daily_news.py` runs at 06:05 AM IST, the bot posts a digest of the day's stories to a private Telegram channel.


* Editors can click inline interactive buttons (**"Approve"**, **"Edit Story 2"**, **"Trigger Line A"**) from their phone. The Mac executes the headless render, posts the preview frames back to Telegram for sign-off, and attaches the master copy.



#### Modern Dependency and Process Management

* Replace untracked manual scripts with `uv` (an ultra-fast, Rust-based Python package manager). `uv pip compile` creates an immutable, locked `requirements.txt` in milliseconds, resolving Issue #18.


* Run morning scraping and background jobs using native macOS `launchd` daemons (`~/Library/LaunchAgents/`) instead of manual terminal executions.



---

### 3. Design & Motion Polish

#### Kinetic Syllable-Level Typography (Word Revealing)

* Instagram Reels and YouTube Shorts retention depends heavily on visual movement within the safe zones.


* Instead of displaying static cards for 8 to 10 seconds, use the word-level timestamps generated by Google TTS or `mlx-whisper` to implement a dynamic text wipe or word-by-word color highlight (e.g., transitioning inactive words in warm paper white `#F7F5F1` to gold `#F5B301` as they are spoken). This keeps viewer attention locked without needing flashy cuts.



#### 2.5D Parallax Motion (Pseudo-3D Ken Burns)

* Flat 2D digital zoom on stock photos can feel repetitive.


* Integrate `Depth-Anything-V2-Small` (an open-source monocular depth estimation model that runs in ~200 ms on the M1 Neural Engine). By generating a greyscale depth map for approved stock photos, Pillow and MoviePy can apply a subtle 2.5D camera pan, separating the foreground subject from the coastal background for a cinematic broadcast feel.

#### Automated Thumbnail Face Extraction and Dynamic Contrast

* For YouTube thumbnails (1280×720), programmatic composition often struggles with cluttered source backgrounds.


* Implement `rembg` (an open-source background-removal library based on U^2-Net). Automatically extract prominent figures or faces, place a subtle gold stroke or shadow around them, and composite them over high-contrast dark backgrounds (`#03050A`) to boost click-through rates across mobile screens.



---

### 4. Refining the "Experts" & Newsroom Workflow

The current 13-step automated newsroom simulates human desks via LLM prompting. You can simplify this by splitting programmatic rules from editorial decisions:

| Current Simulated Role | Optimized Implementation | Operational Benefit |
| --- | --- | --- |
| **Step 1: Kannada Language Desk**<br> | Split: Deterministic regex for Latin numerals, punctuation, and length budgets; LLM reserved exclusively for syntax polish.

 | Zero-cost instant execution; removes LLM drift on character counts.

 |
| **Step 2: Sub-Editor & Crime Gate**<br> | Automated regex dictionary checking for BNS §356 allegation markers and POCSO/JJ Act identifying tokens.

 | Eliminates legal liability without spending API tokens.

 |
| **Step 5 & 12: Design QA & Loop Control**<br> | Integrated Python preflight validation functions inside `render.py`.

 | Hard programmatic blocks instead of conversational LLM looping.

 |
| **Step 7: Voiceover QA**<br> | Local `mlx-whisper` diff engine comparing audio output to story text. | Completely automated acoustic verification; detects silent/dropped frames instantly.

 |
| **Step 13: Chief Editor Gate**<br> | Generates a single visual proof sheet (contact strip) sent to the editor's smartphone via Telegram with a one-click signing link to write `APPROVAL.md`.

 | Retains essential human oversight while cutting desk review time from 20 minutes to 30 seconds.

 |

---

### Immediate Next Steps to Lock Version 1.0

1. **Hardware Configuration:** Update the FFmpeg wrapper in `brand/motion.py` to target `-c:v h264_videotoolbox` and verify Real-ESRGAN uses `--tile 256`.


2. **Ingestion Hardening:** Add full-article body scraping via `trafilatura` to `scripts/fetch_daily_news.py` to stop AI extrapolation.


3. **Repository Lock:** Freeze dependencies using `uv pip freeze > requirements.txt`, commit unversioned template assets, and apply the Git tag `v1.0-board-approved`.


Yes. After looking at the system structure and the Deep Research findings, I would make one major shift.

Your system is already much more structured than a normal AI content workflow. The next level is not adding more AI agents. It is making AI work as a controlled newsroom pipeline with automation around it.

Your own document already identifies the biggest weakness: the system checks whether a source is named, but it does not independently establish whether the underlying fact is true. 

Here is how I would level it up while keeping the cost close to zero.

1. Build a "Truth Layer" before the AI newsroom

Current flow:

News → Gemini → Kannada copy → AI experts → render

I recommend:

News sources
↓
Source collector
↓
Fact extraction
↓
Cross-source verification
↓
Confidence score
↓
Editor approval
↓
AI newsroom
↓
Rendering
↓
QA
↓
Publishing

Every story should receive:

source_url
source_name
published_time
retrieved_time
claim_list
supporting_source
verification_status
confidence
editor_status

Use three states:

VERIFIED
PARTIALLY VERIFIED
UNVERIFIED

Only VERIFIED stories enter automatic production.

This directly addresses the document's Issue #2, where headlines are sent to Gemini while the system asks Gemini for details that do not exist in those headlines. 

2. Use AI as multiple roles, not one giant prompt

You already have a 13-step AI newsroom. 

I would restructure it into five AI stages.

AI 1: Researcher

Finds:

• What happened
• Who said it
• Where
• When
• Primary source
• Supporting sources

AI 2: Fact checker

Checks every factual sentence against the retrieved source.

Example:

Claim:
"Udupi district administration announced..."

AI response:

SUPPORTED
Source: official government release
Evidence: paragraph 3

AI 3: Kannada editor

Converts verified facts into natural Kannada.

AI 4: Legal/editorial checker

Checks:

• allegation
• accusation
• minors
• sexual offences
• death
• crime
• political claims
• religious sensitivity
• misleading headlines

AI 5: Creative director

Handles:

• hook
• visual
• pacing
• typography
• voice
• caption
• CTA

This separation makes debugging much easier.

3. Give every story a "Fact Passport"

This would be one of my strongest recommendations.

Create:

story_id
headline
claim_1
claim_2
claim_3
source_1
source_2
source_3
primary_source
verification
legal_status
image_status
editor_status
published_status

Then your AI never receives "a news paragraph".

It receives a structured evidence package.

This reduces hallucination risk.

4. Add an automatic contradiction detector

This is cheap to implement.

For every important story:

Source A says:
"3 people injured"

Source B says:
"4 people injured"

The system should stop.

Status:

CONFLICT DETECTED

Do not generate the final reel.

This is much more valuable than adding another "expert AI".

5. Add source hierarchy

Give sources different weights.

For example:

Tier 1
Official government
Police
Courts
Election Commission
IMD
Government departments
Official company statements

Tier 2
Established newspapers
Established news agencies

Tier 3
Local portals

Tier 4
Social media

Tier 5
Unverified posts

AI should never treat all sources equally.

Your document currently focuses heavily on source presence. The next level is source authority and evidence strength.

6. Add a "research budget"

Do not send every story through expensive AI processing.

Example:

Routine local story:
2 sources

Important story:
4 sources

Breaking story:
6+ sources

Sensitive story:
primary source + independent confirmation

This saves API usage.

7. Make automation event-driven

Your current morning fetch is written for 06:05, but the scheduler is not configured. 

I would automate this:

06:00
Fetch sources

06:05
Deduplicate

06:10
Extract facts

06:15
Verify

06:20
Create editor inbox

Editor opens:

TODAY'S NEWS

🟢 6 verified
🟡 3 need review
🔴 2 rejected

You only work on the yellow items.

8. Add failure automation

You already have `.fetch_failed`. 

Take it one step further.

If:

fetch fails
↓
retry
↓
fails again
↓
create alert
↓
switch to manual mode

Your system should never silently produce empty or questionable news.

9. Automate daily archival

At the end of the day:

edition
↓
sources
↓
images
↓
audio
↓
final renders
↓
approval
↓
publication record

Store a small JSON record.

Example:

2026-09-16/
edition.json
sources.json
approval.json
analytics.json

Keep large video files outside Git.

Your document already identifies the media-folder problem. 

10. Add a "Why this story?" score

Instead of simply choosing stories manually, calculate:

Relevance
30%

Local impact
25%

Public importance
20%

Freshness
15%

Shareability
10%

Then AI recommends the top stories.

The editor still decides.

11. Use analytics to replace assumptions

Your current posting times are essentially starting assumptions. The document itself says there is no automatic analytics system yet. 

After 30 days, record:

post_time
topic
duration
views
3-second retention
average watch time
completion rate
shares
saves
comments
followers gained

Then AI produces:

"17:30 performs 31% better than 14:30 for local civic stories."

Now your system learns from your audience.

12. Add an AI "daily newsroom report"

Every night:

TODAY

Stories published: 7
Reels: 4
Carousels: 2
Footage edits: 1

Best story:
NH66 traffic update

Best format:
34-second reel

Best time:
17:30

Problems:
2 source conflicts
1 pronunciation correction

Recommendation:
Continue 17:30 slot for civic stories.

This turns your content system into a learning system.

13. Add a pronunciation memory

For Kannada news, this would be extremely useful.

Create:

pronunciation.json

Example:

Byndoor → ಬೈಂದೂರು
Kundapura → ಕುಂದಾಪುರ
Udupi → ಉಡುಪಿ
Brahmavar → ಬ್ರಹ್ಮಾವರ

Also store names that repeatedly cause TTS mistakes.

Then every new script passes through:

Kannada text
↓
pronunciation dictionary
↓
TTS normalization
↓
voice generation

Your document already has a dedicated voice QA stage. 

14. Fix the rule contradictions before adding anything

This is more important than adding AI.

The document identifies several conflicts:

YouTube policy conflict. 

Gemini key conflict. 

Image policy conflict. 

Reel length conflict. 

Opening greeting conflict. 

Posting-time conflict. 

Footage approval bypass. 

Music licensing gap. 

These should become automated tests.

15. Create a single "Source of Truth"

This is probably the most important technical improvement.

Right now rules exist across:

AGENTS.md
CLAUDE.md
SKILL.md
tokens
render.py
templates
schemas
docs

The document itself identifies contradictions between these layers.

Instead:

config/
newsroom.yaml
legal.yaml
media.yaml
motion.yaml
publishing.yaml

Then generate:

AGENTS.md
SKILL.md
documentation
validation rules

from those configuration files.

One rule.

Many outputs.

This prevents the same rule becoming different rules in different files.

16. Add "AI approval levels"

Use:

LEVEL 0
AI suggestion only

LEVEL 1
AI drafts, human approves

LEVEL 2
AI researches + drafts, human approves

LEVEL 3
AI researches + drafts + renders, human approves

LEVEL 4
Fully automated publishing

I would keep your newsroom at Level 2 or Level 3 for now.

Do not automate final publication of sensitive news.

17. Add an AI cost controller

Every AI call should record:

model
task
tokens
time
cost
result
failure

Then create:

ai_usage.json

You will quickly discover which operations waste API usage.

For example, you might find that generating five AI image variations produces little benefit.

Remove it.

18. Use smaller models for simple jobs

Do not use your strongest model for everything.

Small model:

• spelling
• formatting
• category detection
• JSON validation
• hashtag generation
• character counting

Better model:

• fact synthesis
• legal reasoning
• sensitive news
• editorial judgement

This reduces cost.

19. Add an automatic "human required" switch

This is important.

If:

confidence < threshold

OR

sources conflict

OR

crime allegation

OR

minor involved

OR

death

OR

political controversy

OR

religious sensitivity

Then:

HUMAN REVIEW REQUIRED

No automatic rendering.

20. Build one command for the entire newsroom

Eventually you want:

python newsroom.py today

And it performs:

fetch
→ clean
→ deduplicate
→ verify
→ rank
→ generate Kannada
→ legal check
→ image selection
→ voice
→ render
→ QA
→ approval package

Then you only open the editor dashboard.

Your existing `render.py` already acts as an entry point, while the project has dedicated modules for content, tokens, motion, voice, copy, QA and review. 

The architecture is already pointing in the right direction.

My recommended free-first architecture

You do not need an expensive AI stack.

Use:

Python
+
SQLite
+
JSON
+
Git
+
Cron / launchd
+
your existing scripts
+
free/local processing
+
one paid/free AI API where required

SQLite would be especially useful.

Instead of scattered JSON files:

news.db

Tables:

stories
sources
claims
verifications
assets
renders
approvals
publications
analytics
ai_runs

This gives you a real newsroom database without needing PostgreSQL.

The biggest upgrade

I would change your philosophy from:

"AI creates content."

to:

"AI processes evidence through a controlled pipeline."

That distinction matters.

Your existing system already has strong governance, QA, templates, provenance, approval, legal checks and a 13-step AI newsroom. 

The biggest missing layer is evidence management.

My priority order would be:

P0, fix immediately

1. Source verification
2. Claim-level evidence
3. Contradiction detection
4. Rule conflicts
5. Grievance officer
6. Image provenance
7. Music licensing
8. Version 1.0 lock

P1, next

9. SQLite newsroom database
10. Automated morning fetch
11. Failure alerts
12. AI cost tracking
13. Pronunciation dictionary
14. Human-review routing

P2, after 30 days

15. Analytics ingestion
16. AI performance analysis
17. Posting-time optimization
18. Story ranking
19. Automated daily report
20. Content-performance feedback loop

If you implement only the P0 and P1 items, I would expect the system to become substantially more reliable without requiring a large increase in spending.

The good part is your existing design already has the foundations for this. The document explicitly requires board decisions, tests, version tagging, and a dependency lock before v1.0. 

I would not rebuild the project.

I would upgrade it around a new central component:

Evidence → Verification → Editorial Decision → AI Production → QA → Human Approval → Analytics → Learning

That gives you a much cleaner path toward a self-improving newsroom while keeping the human accountable for truth, judgement and publication.
Yes. If we look at your SYSTEM_BOOK as a real product, not just a news-content script, I would improve it in three areas:
Design
Development/architecture
Expert/AI newsroom system
Your current document already has a strong editorial foundation. It has a truth contract, provenance, legal checks, format rules, QA and a 12-expert panel.
1. DESIGN: move from "templates" to a real design system
Currently you have 11 templates and many detailed visual rules.
I would introduce a proper design-system layer:
design/
├── tokens.yaml
├── typography.yaml
├── colors.yaml
├── spacing.yaml
├── grids.yaml
├── safe_zones.yaml
├── motion.yaml
├── components/
│   ├── masthead
│   ├── headline
│   ├── source_badge
│   ├── location_badge
│   ├── photo_credit
│   ├── breaking_badge
│   ├── quote_card
│   └── statistic_card
└── templates/
    ├── instagram_4x5
    ├── instagram_reel
    ├── youtube_16x9
    └── live_overlay
The important change
Don't let every template independently decide:
font size
margins
colours
animation
logo position
source placement
safe zones
Instead:
Design Tokens
      ↓
Components
      ↓
Templates
      ↓
Platform Renderer
That gives you consistency.
Add responsive design
One story should be able to generate:
1 story
 ├── Instagram 4:5
 ├── Instagram Reel 9:16
 ├── YouTube 16:9
 ├── YouTube Short 9:16
 ├── WhatsApp image
 └── Web article
The content remains the same. Only presentation changes.
Your system already tries to make one edition object drive multiple formats, which is a very good architectural decision.
2. DEVELOPMENT: build it like a newsroom platform
This is where I would make the biggest improvement.
Right now the system is heavily file/script driven.
Move toward:
                 ┌──────────────┐
                 │ News Sources │
                 └──────┬───────┘
                        ↓
                ┌───────────────┐
                │ Source Ingest │
                └───────┬───────┘
                        ↓
                ┌───────────────┐
                │ AI Researcher │
                └───────┬───────┘
                        ↓
                ┌───────────────┐
                │ Fact Database │
                └───────┬───────┘
                        ↓
                ┌───────────────┐
                │ Verification  │
                └───────┬───────┘
                        ↓
                 Human Approval
                        ↓
                ┌───────────────┐
                │ AI Newsroom   │
                └───────┬───────┘
                        ↓
              ┌──────────────────┐
              │ Content Generator│
              └────────┬─────────┘
                       ↓
               Design Renderer
                       ↓
                 QA / Gate
                       ↓
                   Publish
                       ↓
                  Analytics
                       ↓
                AI Improvement
This is much more powerful than simply:
Fetch → Gemini → Render
The biggest development addition: Fact Database
I strongly recommend adding SQLite first.
You don't need PostgreSQL immediately.
Something like:
newsroom.db

stories
sources
claims
verifications
assets
ai_runs
approvals
renders
publications
analytics
corrections
For example:
STORY
│
├── Story ID
├── Headline
├── Category
├── Location
├── Status
│
├── CLAIM 001
│    ├── statement
│    ├── source
│    ├── verified
│    └── confidence
│
├── CLAIM 002
│    ├── statement
│    ├── source
│    ├── verified
│    └── confidence
│
└── APPROVAL
     ├── editor
     ├── timestamp
     └── decision
This would make the system much more auditable.
3. AI: don't use one "AI journalist"
This is the biggest conceptual upgrade I recommend.
Instead of:
Gemini
   ↓
Write news
use:
AI Researcher
      ↓
AI Fact Checker
      ↓
AI Contradiction Detector
      ↓
AI Kannada Editor
      ↓
AI Legal Checker
      ↓
AI Visual Director
      ↓
AI Social Editor
      ↓
AI QA Assistant
Each AI has a limited responsibility.
That makes hallucination easier to detect.
4. Create an "AI newsroom team"
Your current system already has a 12-expert panel. It includes Story Producer, Editor, Colourist, Restoration Engineer, Sound Engineer, Music Supervisor, Motion & Brand Designer, Kannada Language & Culture, YouTube Growth, Legal & Monetisation, Technical QC and Chief Editor.
I would split these into three groups.
A. Editorial experts
1. Research Editor
2. Fact Checker
3. Kannada Editor
4. Local Culture Editor
5. Legal Editor
6. Chief Editor
B. Creative experts
7. Story Producer
8. Visual Director
9. Motion Designer
10. Colourist
11. Sound Engineer
12. Music Supervisor
C. Distribution experts
13. Social Media Editor
14. YouTube Editor
15. Audience Analyst
16. Thumbnail Specialist
17. SEO/Metadata Editor
That gives you a more complete newsroom.
5. Add one expert you are currently missing
Local Verification Editor
For a local Kannada newsroom, this is extremely valuable.
Their job:
Place name
      ↓
Taluk
      ↓
District
      ↓
Village
      ↓
Temple
      ↓
Person
      ↓
Organisation
      ↓
Event
They check local spellings and context.
For example:
Byndoor
Baindoor
ಬೈಂದೂರು
ಬೈಂದೂರು ತಾಲೂಕು
ಉಡುಪಿ ಜಿಲ್ಲೆ
The system should know that these refer to the appropriate local entities rather than treating them as unrelated strings.
This becomes particularly important when AI generates Kannada.
6. Add an AI "News Research Agent"
This is where your Deep Research idea can become genuinely useful.
Instead of asking AI:
Write today's news.
ask it:
Find → collect → compare → verify → structure
For every story:
Question
↓
Primary source
↓
Secondary source
↓
Local source
↓
Extract facts
↓
Compare facts
↓
Detect conflict
↓
Generate evidence report
Then:
Evidence Report
      ↓
Kannada Editor
      ↓
Final Story
The AI should not be allowed to invent missing information.
7. Add a "confidence state"
I would add:
VERIFIED
PARTIALLY_VERIFIED
DEVELOPING
UNVERIFIED
CONFLICTING
REJECTED
Especially:
CONFLICTING
This should automatically stop production.
Example:
Police source:
3 people arrested

Newspaper:
2 people arrested

Social media:
5 people arrested
AI should NOT choose 3 because it "looks most reliable."
Instead:
⚠ SOURCE CONFLICT

Human verification required.
That is a major newsroom-quality improvement.
8. Add an AI cost manager
You don't need your strongest model for everything.
Use:
Simple task
↓
Small/cheap model

Complex research
↓
Strong model

Sensitive/legal story
↓
Strong model + human
For example:
Task	AI level
Spelling	Small
Category	Small
Formatting JSON	Small
Deduplication	Small
Kannada cleanup	Medium
Story summarization	Medium
Research	Strong
Fact verification	Strong
Contradiction detection	Strong
Legal review	Strong + human
Sensitive story	Strong + human
This can substantially reduce API cost.
9. Add "AI run logs"
Every AI operation should leave a record:
AI_RUN

run_id
story_id
agent
model
prompt_version
input_sources
output
tokens
cost
duration
status
human_review
Then six months later you can answer:
Which model produced this?
Which sources were used?
Which prompt version?
Who approved it?
What changed?
That is the difference between an AI experiment and an AI production system.
10. Design an actual newsroom dashboard
This would be one of my highest-priority UI additions.
Something like:
┌───────────────────────────────────────────────┐
│ OORMANI SUDDI NEWSROOM                        │
├───────────────────────────────────────────────┤
│ TODAY: 16 SEP 2026                            │
│                                               │
│ Stories       28                              │
│ Verified      19                              │
│ Review         6                              │
│ Conflicts      2                              │
│ Rejected       1                              │
├───────────────────────────────────────────────┤
│ STORY QUEUE                                   │
│                                               │
│ 🟢 Ganapathi Festival      VERIFIED           │
│ 🟢 Rainfall Alert          VERIFIED           │
│ 🟡 Road Accident           REVIEW             │
│ 🔴 Political Claim         CONFLICT           │
│ 🟡 Temple Event            LEGAL REVIEW       │
├───────────────────────────────────────────────┤
│ [RESEARCH] [APPROVE] [RENDER] [QA] [PUBLISH] │
└───────────────────────────────────────────────┘
This would make the project feel like a real newsroom product.
11. Add "one-click story production"
Your current system already has many commands and separate processes.
Eventually create:
python newsroom.py story 117
And:
Research
   ✓
Sources
   ✓
Facts
   ✓
Verification
   ✓
Kannada
   ✓
Legal
   ✓
Images
   ✓
Voice
   ✓
Design
   ✓
Render
   ✓
QC
   ✓

WAITING FOR HUMAN APPROVAL
Then:
[ APPROVE ]

       ↓

Publishing Package
12. Fix the "expert scoring" concept
Your current system says the Chief Editor scores every dimension out of 10 and anything below 9 is fixed.
I would change the internal logic from:
Score = 8
to:
PASS
WARN
FAIL
HUMAN REVIEW
Why?
Because a numerical score can create false precision.
For example:
Legal safety = 8.7/10
doesn't actually mean much.
Instead:
LEGAL
✓ No prohibited identification
✓ Allegation language present
✓ Source present
✓ Image compliant

STATUS: PASS
Much more actionable.
13. Add an "expert disagreement engine"
This is advanced but very useful.
Imagine:
Kannada Editor:
PASS

Legal Editor:
REVIEW

YouTube Editor:
PASS

Visual Editor:
PASS

Fact Checker:
CONFLICT
The system should automatically produce:
FINAL STATUS: HUMAN REVIEW

Reason:
Fact Checker detected source conflict.
Legal Editor requested review.
That is better than allowing the average of all experts to become the answer.
14. Design + AI + Development should meet here
The ideal architecture becomes:
                  OORMANI SUDDI
                       │
          ┌────────────┴────────────┐
          │                         │
      KNOWLEDGE                  DESIGN
          │                         │
 Sources / Facts             Design System
 Local entities              Components
 Legal rules                 Templates
 Culture rules               Motion
          │                         │
          └────────────┬────────────┘
                       │
                   AI AGENTS
                       │
       ┌───────────────┼───────────────┐
       │               │               │
    Research       Editorial        Creative
       │               │               │
       └───────────────┼───────────────┘
                       │
                 HUMAN EDITOR
                       │
                  QUALITY GATE
                       │
                 MULTI PLATFORM
                       │
             Analytics / Feedback
                       │
                       └──────→ AI improves
My recommended roadmap
Phase 1: Foundation
Do these first:
1. SQLite newsroom database
2. Story/Source/Claim model
3. Fact Passport
4. Verification states
5. Contradiction detector
6. Single configuration file
7. Automated tests for all current rule conflicts
Phase 2: AI newsroom
8. Research Agent
9. Fact Checker
10. Kannada Editor
11. Legal Agent
12. Local Verification Agent
13. Creative Agent
14. AI run/cost logging
Phase 3: Design system
15. Design tokens
16. Reusable components
17. Responsive templates
18. Central typography system
19. Central animation system
20. Automated visual regression testing
Phase 4: Newsroom dashboard
21. Story queue
22. Source viewer
23. Fact verification panel
24. AI activity log
25. Human approval
26. Render preview
27. QC dashboard
Phase 5: Automation
28. Scheduled source collection
29. Automatic deduplication
30. Research pipeline
31. Editor notification
32. Automatic rendering
33. Publishing package
34. Analytics collection
35. Daily newsroom report
The most important change
I would change the project's philosophy from:
AI News Generator
to:
AI-Assisted Evidence-Based Local Newsroom
Your existing SYSTEM_BOOK is already moving in this direction through its truth contract, provenance requirements, legal gates, human responsibility and multi-expert review.
The next level is to make those principles actual software architecture rather than only documentation.
The end goal should be:
AI researches.
AI organizes.
AI checks.
AI designs.
AI renders.
AI reports problems.

HUMAN decides what gets published.
That would give you a much stronger foundation for turning Oormani Suddi into a serious local-news automation platform rather than just a collection of AI scripts.

Level up by automating **intake, checks, and packaging**. Do not automate **facts, guilt language, or publishing**. The system already has the hard part: a gate that can refuse a bad story. Use AI around that gate, not instead of it.

## How AI should be used here

Treat every model as a junior desk, not a reporter.

| AI may do | AI must not do |
|---|---|
| Collect headlines and full-text tips | Invent official quotes, numbers, causes |
| Deduplicate, cluster, rank by taluk | Mark breaking or live |
| Draft Kannada, then wait for a human | Write crime copy without allegation markers |
| Normalise speech, check length, check glyphs | Post, schedule-upload, or reply to DMs as the channel |
| Grade, caption, chapter footage | Cover a deity or put a child on a thumbnail |
| Build `MASTER_COPY.md` and `schedule.txt` | Decide a story is true |

If the output cannot point at a source URL or `ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ`, it stays in `inbox/`, not in `editions/`.

## 1. Fix the morning fetch first

This is the highest-leverage change and it is mostly free.

**Today:** headlines → Gemini writes 3–5 sentences → editor inherits invented detail.

**Change it to a tip sheet:**

1. Keep the four scrapers.
2. When a headline matches, fetch the article body (or the RSS description). Store `source_name`, `source_url`, `fetched_at`.
3. Ask the model only to: cluster duplicates, order Byndoor/Kundapura first, write a **one-line lead + 3 fact bullets that appear in the source text**.
4. If a fact is not in the source text, drop it. No “background causes.”
5. Write `inbox/today.md` as:

```
## Story
Lead:
Facts:
- 
Source: Name — URL
Taluk:
Needs editor: yes/no (crime / minor / official claim)
```

6. Production starts only after the editor types confirm. Unconfirmed items never become JSON.

That one change kills issue #2 without buying anything.

**Free extra sources to add later:** Udupi district administration releases, police handles, IMD coastal bulletin, university exam notices. Official pages beat a third syndication of Udayavani.

**Do not schedule the fetch until this tip-sheet mode exists.** A 06:05 cron that invents procedure text is worse than a manual run.

## 2. Collapse 13 experts into 4 human stops

The 13-step newsroom is expensive in attention. Keep the code gates. Cut the roleplay.

| Stop | Person does | Machine does |
|---|---|---|
| **A. Desk** | Accept / reject each tip, set legal flags, pick reel stories | Language clean-up, numeral check, allegation-verb scan |
| **B. Picture** | Approve every new image in chat | Stock search first, generate only on miss, force `nature: ai` |
| **C. Package** | Listen to one reel, glance evidence frames | `render.py --check`, sync audit, copy + schedule |
| **D. Gate** | Say publish | `review.py` writes `APPROVAL.md` or nothing ships |

Loop only when a gate fails. Do not re-score twelve 10/10s on a four-story morning.

Implementation: one trigger phrase still works. Internally it runs A→B→C→D and prints a single page: what failed, what the editor must type. That is a skill rewrite, not a new engine.

## 3. Cheap automation that stays on the Mac

You do not need n8n Cloud or a social autoposter. Those templates exist so people auto-publish. You should not.

**Use launchd / cron only for:**

- 06:05 fetch → tip sheet + a local notification if `.fetch_failed`
- 07:00 weather/IMD pull into the same inbox
- Nightly: if the editor typed `stop`, archive stock, delete `out/{date}` and `assets/daily/{date}`

**Use a Telegram or WhatsApp message to the editor, not to the audience:**

```
4 tips ready. 1 crime (flags needed). 1 weather.
Open inbox/today.md
```

Approve in chat. Render on the Mac. Upload by hand.

Self-hosted n8n on the same Mac is optional and only worth it if you already want a visual cron. It adds a service to keep alive on 8 GB RAM. Prefer `launchd` + the scripts you already have.

**Do not connect Instagram/YouTube APIs.** The book’s “person uploads” rule is the product. Breaking it to “level up” is how you ship a wrong crime headline at 08:31.

## 4. AI spend map (free first)

Split keys. That is issue #3, and it also saves money.

| Job | Use | Cost posture |
|---|---|---|
| Fetch / cluster / draft from source text | Cheap text model, separate key, daily cap | A few thousand tokens a morning |
| Kannada polish + legal verb check | Same text key | Tiny |
| Voice | Keep current Google Kannada TTS. Edge/Sapna stays a fallback the native ear already rejected | Google Cloud TTS still has a large monthly Standard free band if billing is on; stay on the voice you already approved |
| Still images | Stock first. New image only when stock misses. Never Gemini image from the voice key | Almost zero if stock is used |
| Footage upscale | Real-ESRGAN only on masters, not on every preview | Time, not money |
| Footage speech-to-text for chapters | Local Whisper / faster-whisper on the Mac | Free, offline |

A daily package is a few hundred spoken characters per reel. Voice is not the expensive part. Invented long copy is the expensive part, in trust.

Keep `news_bgm.mp3` and the ten unverified beds out of new renders until you have a licence row. Pixabay instrumental with a saved licence page is freer than a mystery file in `assets/`.

## 5. Make the library do more work

The stock folder is the cheapest “AI” you have.

- After `stop`, only copy images that could illustrate *next week* (harbour, NH66, taluk office, dam, market). Delete one-off festival frames from daily.
- Catalogue with searchable Kannada keywords: `ನಾಯಿ`, `ಪೊಲೀಸ್`, `ಹೆದ್ದಾರಿ`, `ಯಕ್ಷಗಾನ`. Step 3 should return three candidates before anyone generates.
- One rule: if it was generated, `nature` is `ai` even when reused. The plate is allowed. “Zero plate” is how you generate junk at 07:40.

That single policy removes most daily image cost and most disclosure risk.

## 6. Level up distribution, not production volume

Coastal growth is WhatsApp and the broadsheet, not a fifth reel.

**Free / easy:**

- One broadcast list per taluk (Byndoor, Kundapura, Udupi, Karkala…) rather than one giant group. Forward the broadsheet at 20:00 with the WhatsApp text the system already writes. Put that text in `MASTER_COPY.md` every day (issue #17).
- Story card at 09:15 should name the carousel, not repeat the headline.
- First comment pasted immediately — that is already specified. Make it a physical checklist on the phone, not another AI step.
- Drop X unless someone actually posts there. Do not generate a third caption dialect for a dead platform.

**Do not add AI reply bots on Instagram DMs.** Corrections are a legal clock (24 h / 15 days). A model answering a victim-identification complaint is a liability.

## 7. Footage: automate the dull parts only

Lines B and C already work. Add three free helpers:

1. **Intake:** drop folder → contact sheet + duration list + “original or WhatsApp-sized?” warning. You have this. Run it the moment files land, before the brief.
2. **Speech log:** local Whisper on the clips. Use it to *propose* chapter labels. Client still confirms every on-screen name.
3. **QC bot:** fail the file automatically if true peak > −1.0 after encode, duration outside the window, or masthead missing on a sampled frame. That is a script, not an expert panel.

Keep Real-ESRGAN for the master only. Previews stay plain grade. That halves waiting time on the M1.

Record one instrumental licence sheet as a CSV: title, URL, licence, date, who said yes. Refuse `build.py` if the field is empty. Free, and it closes issue #16 for footage.

## 8. A closed loop that costs nothing

After 30 days, stop guessing times.

Once a week the editor pastes three numbers into a sheet: IG reel views, WhatsApp forwards of the broadsheet, YT watch time on *footage only*. The scheduler expert should retune times from that sheet, not from Step 10 vs code arguments.

Expected first correction: drop the AI bulletin from the 08:30 default. Put any real-footage video there instead. That is the analytics you already have (37 vs 397).

## 9. What to build this month, in order

**Week 1 — lock and simplify**

- Board answers on YouTube, fetch-as-tips, image nature, grievance contact.
- `requirements.txt` + tag. Without this, every new automation is sand.
- Fetch writes source URL + one-line lead only.
- Categories: reject unknown names (no silent “governance”).

**Week 2 — editor UX**

- `inbox/today.md` + Telegram/WhatsApp ping to the editor.
- Four-stop newsroom skill instead of 13.
- `MASTER_COPY.md` always includes WhatsApp forward text.

**Week 3 — library and voice**

- Stock search by keyword before generate.
- Licence register; quarantine unverified BGM.
- Silent-reel and narration-hazard checks stay blocking.

**Week 4 — footage and schedule**

- Whisper chapters + peak-level QC script.
- launchd for fetch + failure ping only.
- One week of handwritten analytics. Then change times.

Nothing in that month requires a new SaaS, a new Mac, or auto-posting.

## 10. What not to “level up”

- Auto-upload to Instagram or YouTube.
- Letting the fetch write decks and takeaways.
- More AI images when the plate or stock would do.
- A twelfth expert.
- Merging this desk with an English statewide briefing. Different brand, different source rule, different audience. Share the Mac, not the contract.

The system levels up when the editor’s morning is: read four sourced tips, flag the crime story, approve two pictures, listen to one reel, upload from `MASTER_COPY.md`. Everything else should be a script. If a new AI step does not shorten that path or catch a legal miss, it is not an upgrade.
Three layers. Keep the gates. Cut ceremony. Put every rule in one place so design, code, and “experts” stop arguing.

## Design

The design system is already better than the newsroom process. Tokens, one gold accent, category colour only on the rail, Kannada baselines, safe zones, grain, editorial plate — that is a real brand. Do not redesign it. Finish it.

**What is working**
- One palette sampled from the logo. No template owns its own hex.
- News grammar vs greeting grammar (D54) is the correct split. A Ganesha card that looks like a crime report is how the brand dies.
- Footage masthead matching the reel masthead makes two production lines look like one paper.
- Disclosure on the frame, not only in the caption.

**What is holding it back**
- Eleven templates for a desk that ships four things most mornings: report card, carousel, story, reel. Quote, stat, text, broadsheet, bulletin, thumb, greeting, live overlay are real — but they should be *available*, not part of the daily default path.
- Motion numbers live in three documents (Step 8, registry, gate). Viewers feel that as uneven pace, not as a policy debate.
- Stock reused as `ಸಾಂದರ್ಭಿಕ` while the credit says AI is a design lie. The label is part of the layout. If the picture is generated, the stamp is `ಎಐ ರಚಿತ ಚಿತ್ರ`.
- The AI bulletin is a 16:9 cousin of the reel. Same voice, same pictures, worse YouTube fit. Design effort there is unused brand weight.

**Do this, cheaply**

1. **Daily design path = 4 outputs.** Report card + carousel + story + reel. Everything else is `--only` on request. Broadsheet stays for 20:00 WhatsApp. Bulletin off by default.
2. **One motion spec in `tokens.Motion`.** Reel 28–45 s, fail > 60 s, card 5–12 s, hook ≤ 1.5 s, opening on the headline. Delete the competing sentences in the newsroom skill.
3. **Evidence instead of a “Design QA expert.”** `review.py` already dumps carousel slides, covers, and eight reel frames. The human looks at that sheet for 90 seconds: type joining, safe zone, disclosure visible, no deity covered. That *is* design QA.
4. **Stock cards as a designed kit, not a junk drawer.** Same crop, same grade, same caption pattern. Keyworded in Kannada so Step 3 is search, not generation.
5. **Greeting stays a separate genre.** Do not let news tokens (dateline, category rail, “special”) leak onto wishes. You already learned this the hard way.
6. **Stop drawing what the platform will hide.** Reel safe inset 72/230/220/480 is correct. Footage credits under the caption bar was a design bug, not an editor bug. Add a preview PNG with IG chrome drawn on it. One file, used in both AI reels and footage reels.

Do not add new templates until v1.0 is tagged. New formats are how this system stays unlocked.

## Development

The valuable code is the contract, not the 13-step script. Develop as if `Story.validate()`, preflight, and `APPROVAL.md` are the product.

**What is working**
- JSON in, unknown fields rejected, no override switch.
- Legal checks on headline and reel line in isolation.
- Golden test + frozen clock. That is how a brand survives refactors.
- Render only what was asked (`--only`).
- Tests already exist (112). Use them as the expert panel that cannot be sweet-talked.

**What is holding it back**
- Policy, skill text, and constants disagree. That is a development failure, not a board-philosophy failure.
- No `requirements.txt`, dirty tree since `35b609c`, wrong project path in AGENTS. The machine cannot be rebuilt.
- Fetch writes finished copy from headlines. That is a feature that violates the contract the rest of the repo enforces.
- Footage lines never pass through `review.py`. Two quality systems means one will be skipped on deadline.
- 8 GB M1: detached renders and “close Chrome” are tribal knowledge, not engineering.

**Do this, cheaply**

1. **Single source of limits.** Character caps, durations, loudness, categories, handle casing live in `tokens.py` (or one `limits.json` the tokens module reads). Skills quote those names. Tests import them. If Step 8 wants 42 s and the gate wants 90 s, the test fails before anyone “decides.”
2. **Tag v1.0 after the board sheet, not before.** Pin dependencies. Fix the folder path. Add a `CHANGELOG` line that points at D55+. After that, a limit change is: decision note + constant + test + tag. Day-to-day news stays ungated by the board.
3. **Fetch becomes a typed inbox, not an edition.** Output `inbox/today.json` with `lead`, `bullets[]`, `source_url`, `source_name`, `taluk`, `risk: crime|minor|normal`. No deck, no takeaway, no invented why. `start with content` refuses to run if a story has no `source_url` and is not marked own reporting.
4. **One approval entry point.** Footage `qc_report.md` can stay. Still require `review.py` (or a thin sibling) to write `APPROVAL.md` for line B/C: QC pass, licence field filled, names confirmed, engagement question present. Otherwise the Chief Editor gate is theatre for line A only.
5. **Local CI, no cloud needed.**
   - On change to `brand/` or `templates/`: contract tests.
   - On change to golden fingerprints: refuse (you already do this).
   - Nightly or on `stop`: delete daily dirs, assert `editions/{date}.json` still exists.
6. **Mac reality in the tools.** Preview is 1080p, one job at a time, crash-restart already exists. Add a lock file so a second `build.py` cannot start. Estimate remaining time from last run’s seconds-per-frame, not optimism.
7. **Do not rewrite the renderer.** `render.py` + templates + tokens is the stable core. New work goes to: fetch contract, inbox schema, review coverage for footage, licence register, stock catalogue search. Those are small files.

Development level-up is fewer moving policy documents, not a new framework.

## Experts

Most “experts” are checklists. Some checklists belong in code. A few need a native eye. Pay attention only to the second group.

**Keep as a human (or native-ear) pass**

| Role | Why a person | What they actually look at |
|---|---|---|
| Desk editor | Truth and news judgement | Sources, status, whether it is a reel, obituary tone |
| Legal flags | Word lists miss clever guilt | `involves_minor`, `sexual_offence`, `convicted`, location grain |
| Native voice | TTS can be legal and still wrong | One reel, headphones, opening line, rupee/percent speech |
| Culture on footage | Dignity is not a regex | Deity held, no child hero frame, names as the client wrote them |
| Publisher | IT Rules clock, real upload | `APPROVAL.md` present, first comment pasted, times from the sheet |

That is five responsibilities. They can be one or two people. They cannot be twelve model calls.

**Turn into code (stop calling them experts)**

- Headline / reel-line length  
- Latin numerals only  
- Allegation verbs on crime headlines  
- Gallery count ≥ facts  
- Handle spelling  
- File exists if schedule names it  
- Reel duration and silent-file marker  
- Missing glyphs  
- Loudness / true peak on finished media  
- Unknown category  
- AI nature + caption disclosure  
- Music licence field empty  

If a check has a number or a word list, it is not an expert. It is `qa.py` / `review.py`. You already built this. Use it as the default “panel.”

**Merge the rest**

| Current theatre | Becomes |
|---|---|
| Kannada Language Expert + Sub-Editor | One desk pass. Model proposes; human accepts. |
| Photojournalism + Culture/Legal image | One image pass in chat. Stock → generate → plate. Culture veto is a yes/no on the frame. |
| Design QA + Retention + Voice QA + Final QA | One package pass on the evidence folder + audio. |
| Social + Scheduling | One `MASTER_COPY.md`. Times come from last month’s sheet, not from two skills. |
| Legal/Monetisation Guard | Code + the flag pass above. No separate score out of 10. |
| Chief Editor | Runs `review.py`. Does not “score dimensions.” Green file or not. |
| Footage 12-expert panel | 4: picture/sound QC script, culture/names human, music licence field, YouTube package checklist (title, chapters, last line). |

A “10/10” from an assistant is not evidence. A failed test, a peak meter, a missing `source_url`, a frame with the disclosure cropped — that is evidence.

**How the remaining experts should work**

- Each human stop has a **one-page checklist** and a **block list**. Example: culture can veto, cannot redesign the masthead.
- The assistant’s job at each stop is to **show the checklist with the actual values filled in** (headline 81 chars, gallery 2, facts 3, peak −0.2 dB). Then wait.
- No expert is allowed to edit `tokens.py`, templates, or `render.py` during a production day. That is already the rule. Enforce it in the skill: production mode cannot touch those paths.
- Footage names: if it is not in the client brief, it does not render. That single expert rule prevents the Someshwara / ಸೇನೇಶ್ವರ class of error.

## How the three fit together

```
tokens + contract     = design and law, frozen
inbox JSON            = development boundary (tips in, edition out)
4 human stops         = experts
render + review.py    = machine
person uploads        = publishing
```

If design wants a new length, it changes a token and a test.  
If development wants a new source, it adds a scraper that still emits the same inbox schema.  
If an expert wants a new taste rule, it goes on a checklist first; it becomes code only when it has a number.

That is the easy level-up: one spec, one inbox, four stops, one approval file. Everything else in the book is either a good constraint already written, or a second copy of that constraint that will drift again.
Before I answer, let me check a couple of things that change often — the posting APIs and current Kannada voice options — so I'm not sending you down a dead end.Here's what I'd actually do, ordered by leverage rather than by category. Almost all of it is free.

## 1. Turn the fetch from a generator into a retriever

This is the fix for the hole I flagged, and it's a day's work.

RSS already gives you article links. Add **trafilatura** (free Python library) to pull the full article body from each link, then send *that* to Gemini with a hard instruction to use only the supplied text. Ask for structured JSON output directly against your Story schema, including a `source_url` and a `source_sentence` per fact. Gemini supports response schemas, so you get validated JSON instead of prose you re-type.

Then add a second cheap pass: give the model the draft and the source text and ask it to list every sentence not supported by the source. Anything it lists gets deleted or flagged for the editor. Two API calls instead of one, and the fabrication problem mostly goes away. Keep the raw source text in `inbox/processed_*.txt` so an editor can audit a story three weeks later.

While you're there: the scraping-and-rewriting question. Once you have per-story source links, you can attribute properly (`ಮೂಲ: ಉದಯವಾಣಿ` with a link in the caption), which is both more defensible and more trustworthy to readers.

## 2. Build the feedback loop you don't have

Right now every number in the book is a guess: posting times, reel length, hook timing, hashtag mix, 8 slides vs 6. Section 23 says "review after 30 days of analytics" but nothing is collecting analytics.

Write one small script, `scripts/pull_metrics.py`, that hits the Instagram Graph API insights endpoint and the YouTube Analytics API and writes reach, saves, shares, watch-through and follows into a SQLite file keyed by the edition JSON and story ID. Run it daily via launchd. Then a weekly auto-generated markdown report: which categories get shared, which posting slot wins, where carousel viewers drop off, what reel length actually retains.

One caveat worth knowing before you build it: Instagram insights are not available for accounts with fewer than 1,000 followers. If you're under that, log what you can from YouTube and Telegram and revisit.

This is the single highest-value addition after fixing intake, because it converts twenty design opinions into measurements.

## 3. Automate the publishing, keep the human gate

"A person uploads each item" is your biggest recurring time cost: eleven files a day, covers set by hand, first comments pasted on time.

The Instagram Content Publishing API does this. You can publish single images, videos, reels, and carousel posts on Instagram Professional accounts, and as of 2023 Stories are publishable too. Accounts are limited to 100 API-published posts per rolling 24 hours, which you'll never approach. Two practical requirements: the media must be hosted on a publicly accessible server at the time of the attempt, so you'll need somewhere free to park files briefly (Cloudflare R2, GitHub raw, a cheap VPS), and reels have to be 9:16, 5–90 seconds, H.264 or HEVC, with `thumb_offset` in milliseconds to pick the cover frame. Your reel cover logic maps onto that directly.

YouTube Data API v3 does the same for the long videos including thumbnail, description and chapters, within a free daily quota that comfortably covers a handful of uploads.

**Telegram is the easy one and I'd start there.** The Bot API is free, instant, has no review process, and posts are deletable. Auto-post the broadsheet and the forward text to your Telegram channel the moment `APPROVAL.md` exists. Same bot handles your `.fetch_failed` alerts at 6am so you find out about a failed scrape before you sit down.

The design principle stays intact: nothing publishes without `APPROVAL.md`. You're not removing the human gate, you're collapsing eleven manual uploads into one approval.

## 4. Voice: the biggest quality jump available

Synthetic TTS is the weakest thing a local channel can have, because trust is the product and a robot voice signals "this is not from here."

Two options, both free. The interesting one is **IndicF5** from AI4Bharat: a near-human quality, open-source TTS model trained on 1,417 hours of Indian language speech, covering Kannada among eleven Indian languages, with local voice cloning. You record thirty seconds of your own voice, clone it, and your reels are narrated in a real coastal Kannada voice that belongs to a named person. Runs locally, no API cost, no throttling.

That also unlocks something strategic. AGENTS rule 7 blocks AI slideshows from YouTube because they average 37 views against 397 for real footage. But rule 7 permits a real human voice. A cloned owner voice over stock visuals is a genuinely different product from Google TTS, and it's worth testing on YouTube before assuming it fails.

The cheaper version of the same idea: record the lead story yourself on your phone each morning. Sixty seconds. Use TTS for the rest.

## 5. Make the footage pipeline stop eating your days

Line B currently costs 5–10 minutes of intake, 10–15 minutes of edit list, and hours of rendering, for a film the client rated 50%.

- **faster-whisper** locally on the audio gives you a timestamped Kannada transcript of the whole shoot. That turns "watch fifteen minutes of footage" into "read two pages." You get subtitles, chapter boundaries from actual speech, quotable lines, and the hook candidate, all for free on the M1.
- **PySceneDetect** plus a simple sharpness and motion score per shot auto-drafts `project.json`. You edit a generated list instead of writing one.
- **Gemini vision on your contact sheets** to label ritual stages, flag frames containing children's faces before a human looks, and nominate hero shots. This directly serves your culture check and your "no child's face as thumbnail" rule.
- **Stop running Real-ESRGAN on the whole timeline.** Run it on the eight or ten hero shots that will be held on screen; use ffmpeg lanczos with a light unsharp pass for everything moving fast. Your two-hour master becomes twenty minutes and no viewer notices. Add a render cache keyed on a content hash so a copy fix doesn't re-render the film.

## 6. The strategic one: stop rewriting Udayavani

Everything above makes you a faster version of what you already are, which is a synthesis layer on four other publishers. The thing that makes you a real local channel is original reporting, and you have the cheapest possible route to it.

Build a **Telegram tip bot**. Locals send a photo, a clip, or a line of text; the bot logs it with sender, timestamp and location into `inbox/tips/`, and pings you. Put the bot link in your Instagram bio and on the closing slide of every carousel. In Byndoor and Kundapura you will get flooding photos, road closures, temple event notices and accident reports before any district paper has them. That's news nobody else has, with real provenance, and it feeds the `ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ` source line your contract already supports.

Pair it with a comment and DM triage classifier that sorts incoming messages into tip / correction / question / abuse. Corrections found by readers are how you build the trust your legal architecture is designed to protect.

## A four-week order

Week 1: Telegram bot for alerts and channel posting, launchd for the 6am fetch, `requirements.txt` and a v1.0 tag. All small, all removes risk.

Week 2: rebuild the fetch as retrieval with per-fact sources and the groundedness pass. Turn the old path off.

Week 3: metrics logging plus the weekly report. Let it run while you do other things.

Week 4: IndicF5 voice clone, and the Whisper plus PySceneDetect intake for footage.

Instagram and YouTube auto-publishing after that, once you trust the approval gate with a month of clean days behind it.

## What I would not automate

Crime posts stay manual, always. Legal flags stay human-set. The native-ear voice check stays yours. And nothing bypasses `APPROVAL.md`, including the Telegram bot.
Taking those three separately, because the fixes are different in kind.

# Design

**The gold has a contrast problem you should encode as a rule.** Gold 500 (`#F5B301`) against ink 950 sits around 10.7:1, which is excellent. Against paper (`#F7F5F1`) it's roughly 1.7:1, which is illegible. Right now nothing in the token system stops gold type landing on a light ground, and it will eventually happen on a greeting theme or a light card. Add a second token, a bronze around `#8A6200`, for light grounds, and write the rule into `tokens.py`: gold only on ink or under a scrim above 60%. Then make it a test.

**More broadly, legibility isn't enforced anywhere and it should be.** You have 112 tests and a philosophy of putting rules in code rather than memory, but nothing checks whether text can be read. Two machine checks would fit straight into `qa.inspect()`:

1. A contrast test that walks every text-on-ground pair in the token system and fails below 4.5:1, or 3:1 for display sizes.
2. A **feed-size test**: downscale every rendered deliverable to the size it's actually seen at (carousel cover 150px, reel first frame ~200px, thumbnail 210px) and write a contact sheet. You already do this thinking for the YouTube thumbnail and nowhere else. Everything is designed at 1080 and consumed at 400.

That second one will also tell you that **19px minimum type is too small**. At 1080 wide viewed at 400px, 19px renders at around 7px, and Kannada conjuncts need more vertical room than Latin does at the same nominal size. I'd raise the floor to 26–28px on a 1080 canvas and let the test prove it.

**The category rail is invisible at the size people see it.** D9 is a nice restraint decision, but a thin rail at thumbnail scale carries no signal at all. Either let the kicker text take the category colour too, or accept that categories are internal taxonomy rather than a reader-facing cue, and stop paying design cost for them.

**Three Kannada families is one too many.** Anek Kannada is variable across weight and width. You could carry both headline and body from Anek alone, with real optical control, and keep Noto Serif strictly for greetings. Fewer families reads as more deliberate, and it removes a class of fallback bugs.

**One editorial plate becomes a liability at volume.** If a meaningful share of stories have no photo, every such card is identical. Make it a family: procedural variation seeded from a hash of the headline, so it's varied to a reader and still fully deterministic for the golden test.

**Two things specific to your actual audience that the system doesn't account for.** The broadsheet is near-black at 1080×1620, forwarded on WhatsApp and opened on a bright phone outdoors at midday in coastal Karnataka. A light variant, paper ground and ink type, would read far better in that exact situation. And JPEG 95 at 4:4:4 is a lot of bytes to push through rural data for a forward; for forwards specifically, q85 at 4:2:0 targeting under 300KB is invisible at phone scale and materially more forwardable. Your current warn threshold of 5MB is about ten times too generous for the format that's supposed to be your main growth route.

**Motion is the weakest layer.** Eased Ken Burns plus a gold edge wipe is competent and anonymous. The logo has speed strokes; derive your transition geometry from those rather than from a generic wipe. A recognisable motion signature in the first half-second is worth more than any other motion refinement you could make.

# Development

**The single change that matters most: make the code generate the rules, not mirror them.** Issues #6, #7, #9, #12, #13 and #15 are all the same bug. Numbers live in `AGENTS.md`, in the newsroom skill markdown, and in `tokens.py`, and they drift. You already generate `TEMPLATES.md` and the schemas from code and refuse manual edits via hooks. Extend that to every limit, time, length and threshold: code is the source of truth, the rule documents are build artifacts. Then contradiction becomes structurally impossible instead of something you audit for and list in Section 22.

**Pin the fonts and Pillow exactly, or the golden test is decorative.** Font files in `fonts/` is right. But a Pillow or raqm version bump will shift rasterisation and your golden fingerprints will fail for reasons that have nothing to do with design. Lock the whole environment (`uv.lock` or pip-tools), and record the Pillow, raqm and font hashes inside the blessed output metadata so a failure tells you *why*.

**Build an adversarial corpus for the legal guards.** The word-list approach has an unknown false-negative rate, and Section 21 admits it without measuring it. Write 200 real Kannada crime sentences, label them pass/fail by hand, and run them as a test. Now you have a number. Then add a second layer: keep the word list as the deterministic blocker, and add an LLM pass that flags "asserts guilt without allegation marker" as a *warning*. Blocking stays deterministic, coverage improves, and you can measure how often layer 2 catches what layer 1 misses.

**Split the tests and add logging.** `test_contract.py` spans sixteen distinct concerns. Split by concern so a failure names itself. And nothing currently logs: record per render which checks fired, what got dropped for space, which warnings appeared. After a month you'll know which of your fifty-four decisions actually bind and which are theoretical.

**Build a single-page edition review.** Today the Chief Editor step means opening `_review/` frames, `MASTER_COPY.md`, `schedule.txt` and a dozen files. One generated HTML page per edition, with every asset shown at *feed size*, every caption, the schedule, and all warnings inline, turns that step into sixty seconds. It's a small build with a disproportionate effect on whether the review actually happens properly on a tired Tuesday.

**Minor but worth doing:** a proper CLI entry point with subcommands instead of flag-laden `render.py` calls, and `mypy --strict` over `brand/`, which will catch a surprising amount around the contract.

# Experts

**Drop the scores.** One model wearing twelve hats, scoring itself out of ten, with a rule that anything under nine gets fixed, produces nines. Replace with binary pass/fail and a required artifact per item: a timestamp, a measured LUFS figure, a frame path. No citable evidence, automatic fail. This costs you nothing and removes the main way the panel can quietly become ceremonial.

**Twenty-five personas is too many.** Twelve experts for footage plus thirteen newsroom steps is a lot of the same judgement in different costumes. Six real roles would do more work: Reporter (facts, sources), Lawyer (legal and monetisation), Designer (look and brand), Sound, Growth, Chief Editor. Deeper checklists, fewer of them, much lower cost per edition.

**Add the role that's missing: one whose job is to fail the package.** Every expert you have is helping the piece ship, which means the panel is additive rather than adversarial, and an adversarial panel is the only kind worth running. Give one agent the opposite incentive in its prompt: argue this story shouldn't run, this headline is defamatory, this image is wrong, this claim isn't sourced. Let the Chief Editor adjudicate. This is where multi-agent review actually earns its cost.

**Stop letting a text model claim it perceived something.** "No dragging shot", "chants intelligible", "natural skin", "no clipping or banding" are perceptual judgements. Either measure them (loudness in the speech band, colour histograms, shot-length distribution) or show them to a person. Anything that's neither should be marked unverified rather than passed.

**Step 2 is your most important role and your vaguest.** "Drama, public stakes, shareability" as the reel gate will drift toward crime, because crime always wins on those three. Give it an explicit weighted rubric and a hard cap: no more than N crime reels a week. Otherwise the analytics loop I suggested earlier will actively push you into being a crime channel, which is exactly where the legal exposure lives and where local outlets reliably end up.

**The culture expert should flag, never approve.** Cultural judgement around Daivaradhane, Yakshagana and temple ritual is precisely the category where a model is confidently and subtly wrong. Let it surface candidates for your eye. Don't let it clear anything on its own.

**Persist the verdicts.** Every expert's decision and evidence should be written back into the edition JSON. Right now the judgements evaporate the moment the day closes, which means six months from now you cannot answer why a story ran.

**And move the human.** You're currently at both ends: pasting news at the start, approving everything at the end. The scarcest human judgement is in the middle — ninety seconds choosing which four stories run and confirming the reel picks. Put yourself there and let the machine own the rest.

If the single-page edition review or the contrast-and-feed-size test suite sounds useful, either is a short build and I can write it.

Here are concrete, practical upgrades that will level up Oormani Suddi without making the system heavier or more expensive. I’ll group them by goal and keep each item small enough to implement in a few hours.

***

## 1. Make the AI smarter, not louder

### 1.1 Add a “source-aware” drafting step

Right now the fetch script sends only headlines to Gemini and asks for rich paragraphs. That invites hallucination.

Upgrade:

1. For each headline, fetch the full article text or official notice when available.
2. Pass to Gemini:
   - Headline
   - Source URL
   - Source type (news portal / government / police / other)
   - Full article text (or “no full text available”)
3. Ask Gemini to produce:
   - A 1–2 sentence verified summary.
   - A list of claims with explicit “source: URL” tags.
   - A flag: `fully_supported`, `partially_supported`, `insufficient_source`.

Then your editor only works on `fully_supported` or `partially_supported` items. Anything `insufficient_source` becomes a tip, not a story.

This keeps AI as a research assistant, not a fact inventor.

***

### 1.2 Add a “confidence score” per story

Extend the JSON story object with:

```json
"ai_confidence": {
  "score": 0.85,
  "reason": "Two independent sources; official statement quoted; no contradictory reports",
  "missing": ["no on-ground confirmation", "no direct quote from civic body"]
}
```

You can compute this in a small Python function that:

- Counts distinct sources.
- Checks for official sources.
- Checks for direct quotes.
- Checks for contradictions across sources.

Then:

- High confidence → normal production.
- Medium → “developing” status, cautious language.
- Low → internal only or reporter verification required.

This gives you a simple, explainable AI safety layer.

***

### 1.3 Use AI for “story expansion,” not “story creation”

Instead of asking AI to write the entire story from scratch, use it in narrower roles:

- **Summariser:** “Summarise this article into 3 bullet points in formal Kannada.”
- **Explainer:** “Explain this government order in simple Kannada for a general reader.”
- **Context builder:** “Given these 3 articles, list what is new today vs yesterday.”
- **Question generator:** “Generate 3 questions a local resident might ask about this notice.”

This keeps the human in control of the narrative while AI handles heavy lifting on language and structure.

***

## 2. Automate the boring parts, not the judgement

### 2.1 Auto-generate a “verification checklist” per story

For each story, generate a short checklist for the editor:

```text
[ ] Source URL opened and matches headline claim
[ ] Place name verified in source
[ ] Numbers (₹, %, dates) match source
[ ] Any claim of death/injury/arrest has official source
[ ] Any child involvement? If yes, mark minor flags
[ ] Any sexual offence? If yes, mark sexual_offence flags
[ ] Any allegation without conviction? Ensure headline/reel line have allegation markers
```

AI can generate this checklist based on the story category and content. The editor just ticks boxes. This turns vague “be careful” into a concrete 30-second task.

***

### 2.2 Auto-draft corrections and follow-ups

When a correction is needed:

- Editor types: `correct story 3: wrong place name, should be Brahmavara`.
- AI:
  - Generates corrected headline, deck, and points.
  - Generates a correction note.
  - Generates an Instagram caption and WhatsApp forward explaining the change.
  - Updates the edition JSON with a `correction` field.

Similarly, for follow-up stories (“yesterday’s road closure extended”), AI can:

- Pull the previous story from the edition archive.
- Draft a “previously” block.
- Draft the new update with clear linkage.

This makes corrections and continuity easy instead of painful.

***

### 2.3 Auto-generate a daily “editor’s brief”

Every morning, after fetch, run a script that produces:

- Top 5 stories by potential local impact.
- Suggested categories.
- Suggested formats (reel or not).
- Suggested hooks in Kannada.
- A short risk note (crime, minors, sensitive topics).

The editor starts from this brief instead of raw headlines. This is a huge productivity boost and ensures consistency.

***

## 3. Use AI to strengthen trust, not just content

### 3.1 “Show your work” panels for important stories

For high-impact stories (civic, health, crime, large projects), generate a simple graphic or caption block:

- “Sources used” list.
- “What we confirmed” vs “What is still unclear”.
- “When we last updated”.

AI can draft this text from the story’s metadata. You can render it as a small “transparency card” in the carousel or as part of the caption.

This is rare in local Indian news and can become a brand differentiator.

***

### 3.2 Auto-generate a weekly “corrections & clarifications” post

Once a week:

- Scan all editions for `correction` fields.
- AI drafts a short post:
  - What was corrected.
  - Why.
  - What you changed.
- Post it as a Story or a small carousel slide.

This shows readers that you take accuracy seriously and are willing to publicly correct yourself.

***

### 3.3 Use AI to summarise reader tips and DMs

Collect reader tips (via WhatsApp, Instagram DMs, Google Form) into a single text file.

Run an AI summariser that:

- Groups tips by location and topic.
- Highlights repeated issues (e.g. “water supply in X area” mentioned 5 times).
- Suggests 2–3 story ideas.

This turns scattered messages into an editorial pipeline without manual sorting.

***

## 4. Make video production easier and better

### 4.1 Auto-generate a “shot list” from raw footage

For event footage (temple, rally, meeting):

- Editor uploads clips.
- AI watches file names, durations, and any available metadata.
- Generates a suggested shot list:
  - “Cold open: clip 3, 0:12–0:18 (firecrackers).”
  - “Act 1: arrival – clips 1, 2, 5.”
  - “Hero moment: clip 7, 0:45–1:05.”
  - “Outro: crowd reaction – clip 9.”

This doesn’t replace human judgement but gives a strong first cut plan in seconds.

***

### 4.2 Auto-generate chapter markers and timestamps

For long YouTube videos:

- AI analyses the edit list or transcript.
- Suggests chapters with timestamps and Kannada titles.
- Editor tweaks and approves.

This saves time and ensures every video has proper chapters, which helps retention and search.

***

### 4.3 Auto-generate multiple cuts from one master

From one long footage edit:

- Use AI + simple rules to auto-generate:
  - A 45–60s vertical Short/Reel.
  - A 15–20s teaser for Instagram Stories/WhatsApp.
  - A 6–10s hook clip for promotional use.

You already have the long-form pipeline; adding a small “cutdown generator” that reuses the same assets and music licence will multiply your output without extra shooting.

***

## 5. Make analytics work for you (lightly)

You don’t need a heavy dashboard. Just a few simple automations.

### 5.1 Weekly performance digest

Once a week:

- Export basic metrics (views, likes, shares, comments, watch time) from Instagram and YouTube (manual copy/paste is fine at first).
- AI generates:
  - Top 3 posts by reach.
  - Top 3 by engagement rate.
  - Best-performing format (reel, carousel, short, long).
  - Best-performing topics and locations.
  - 3 concrete experiments for next week (e.g. “try 35–40s reels on civic stories”, “test morning vs evening posting for weather”).

This keeps your strategy data-informed without building a complex system.

***

### 5.2 Auto-suggest “evergreen” content

From your archive:

- AI scans past stories and identifies:
  - Frequently searched topics (e.g. “bus timings”, “exam dates”, “hospital services”).
  - High-share civic information.
- Suggests evergreen posts or explainers that can be updated and re-posted.

This helps you build a library of useful local reference content.

***

## 6. Make the system easier to run daily

### 6.1 Add a “minimal mode” command

Create a simple command like:

```bash
python render.py --mode minimal editions/today.json
```

Which produces only:

- 1 carousel.
- 1 Story card.
- 1 WhatsApp broadsheet.
- 0–2 reels (only for the strongest stories).

This prevents burnout and keeps quality high on busy days.

***

### 6.2 Add a “quick post” mode for breaking news

For urgent, verified updates:

- Editor provides:
  - Headline.
  - 1–2 facts.
  - Source URL.
- AI generates:
  - A simple text card.
  - A Story card.
  - A short caption.
- Rendered in under a minute.

This gives you speed without sacrificing sourcing or legal checks.

***

### 6.3 Auto-archive and backup

Add a simple script that:

- Zips each month’s editions, rendered outputs, and source records.
- Saves to a backup location (external drive or cloud).
- Logs what was backed up.

This protects your work and makes future corrections or investigations easier.

***

## 7. Use AI to grow the brand, not just the feed

### 7.1 Auto-generate “local guide” explainers

From your accumulated stories:

- AI drafts simple explainers like:
  - “How to apply for X certificate in Udupi district.”
  - “What to do if your area has no water for 2 days.”
  - “Steps to file a complaint about stray dogs / road damage.”

These can be:

- Carousels.
- Short videos.
- WhatsApp-forwardable PDFs.

This positions Oormani Suddi as a practical helper, not just a news ticker.

***

### 7.2 Auto-generate monthly “what changed in your taluk” posts

At the end of each month:

- AI scans all stories by taluk.
- Generates a short summary:
  - Key civic changes.
  - Major events.
  - Crime highlights (carefully worded).
  - Upcoming deadlines or notices.

Post this as a carousel or long caption. It becomes a local “monthly digest” people look forward to.

***

### 7.3 Use AI to draft collaboration pitches

When approaching:

- Local businesses.
- Event organisers.
- Schools/colleges.
- NGOs.

AI can draft:

- Short pitch messages in Kannada and English.
- Sample post concepts.
- Simple media kits (what you offer, typical reach, sample posts).

This helps you monetise or partner without spending hours on outreach.

***

## 8. Keep it free or very low-cost

All of the above can be done with:

- Your existing Gemini API key (or a second free/low-cost key if needed).
- Simple Python scripts.
- No new paid tools.

If you want, I can next:

- Draft specific prompt templates for each AI task (drafting, verification, explainers, corrections, analytics).
- Or outline a small “v2 system” with a simpler daily workflow and a clear upgrade path.
Here’s a focused upgrade plan in three layers: **design**, **development**, and **experts**—aimed at making Oormani Suddi stronger, faster, and more trustworthy without bloating the system.

***

## 1. Design: make it clearer, faster, and more “Oormani”

### 1.1 Tighten the visual hierarchy

Right now the system is very consistent, which is good. Next step: make it instantly scannable.

**Suggestions:**

- **Stronger headline contrast**  
  - Increase the size/weight gap between headline and deck on report cards and reels.  
  - On mobile, readers decide in <1 second; the headline should dominate.

- **Clearer category signals**  
  - Keep the thin rail, but consider:
    - A small icon per category (cloud for weather, gavel for civic/legal, etc.).
    - Consistent position so regular viewers learn the code quickly.
  - Don’t overdo it—just 1–2 simple glyphs per category.

- **Dedicated “breaking” layout**  
  - For true breaking news, use a distinct layout:
    - Bolder red rail.
    - Larger headline, shorter deck.
    - Minimal facts (2 instead of 3).
  - Reserve this for genuinely urgent items so it doesn’t become noise.

***

### 1.2 Make AI imagery look less “generic”

AI images are already disclosed, which is good. To raise perceived quality:

- **Create a “Oormani style” prompt template**  
  - Fixed elements: coastal light quality, typical building styles, vegetation, sea/sky tones.
  - Avoid overly cinematic or global-stock-looking scenes.
  - Save a few “base prompts” for common situations (harbour, market, office, road, temple).

- **Build a small “style reference” set**  
  - 5–10 AI images that you consider “on brand”.
  - Use them as visual references when generating new images (via image+text prompts if your model supports it).
  - This slowly creates a recognisable Oormani look.

- **Avoid human faces where possible**  
  - AI faces often look off and reduce trust.
  - Prefer scenes where people are small, silhouetted, or absent.
  - For human-centric stories, lean more on text cards or representative objects.

***

### 1.3 Add a “trust strip” to important posts

For high-impact stories (civic, health, crime, large projects):

- Add a small line on the card or in the caption:
  - “Sources: 2 news portals + district notice”
  - or “Field-verified by Oormani Suddi”
- Keep it short, in Kannada, and consistent in placement.

This becomes part of your brand language: “This isn’t random; we checked.”

***

### 1.4 Simplify some templates for speed

You have 11 templates, which is great for flexibility. For daily use, define:

- **Core 4 templates**:
  - Report card (main feed post).
  - Story card (9:16).
  - Reel (9:16 narrated).
  - Broadsheet (WhatsApp/Telegram).

- **Occasional templates**:
  - Quote card, stat card, greeting, bulletin, carousel, thumbnail, live overlay.

Visually, ensure the core 4 are:

- Fast to render.
- Easy to read at thumbnail size.
- Consistent enough that people recognise Oormani even without seeing the logo.

***

### 1.5 Design for “corrections” as a feature, not a failure

Create a small correction template:

- Same brand frame.
- A clear “ತಿದ್ದುಪಡಿ / Clarification” label.
- Short text: what was wrong, what is correct.
- Same colours and fonts so it feels like part of the system, not an afterthought.

This makes accuracy visible and strengthens trust.

***

## 2. Development: make the system easier to extend and safer to change

### 2.1 Modularise the newsroom logic

Right now a lot of intelligence lives in one “second-brain” skill and a few big scripts.

Split into clearer modules:

- `news_intake/`  
  - Fetching, deduplication, source parsing.
- `story_builder/`  
  - Turning raw text into structured story JSON.
- `legal_guard/`  
  - Criminal law, minor/POCSO rules, defamation checks.
- `design_engine/`  
  - Tokens, components, templates.
- `motion_engine/`  
  - Reels, bulletins, audio sync.
- `copy_engine/`  
  - Captions, hashtags, YouTube metadata.
- `review_gate/`  
  - Preflight, approval, evidence collection.

Benefits:

- Easier to test each piece.
- Easier to swap components (e.g. try a different TTS or summariser).
- New contributors (or future you) can understand it faster.

***

### 2.2 Add a proper config layer

Instead of hard-coding many rules in code or scattered docs:

- Create a `config/` folder with:
  - `categories.yaml` – category names, colours, icons.
  - `schedule.yaml` – default posting times per platform.
  - `limits.yaml` – headline lengths, reel durations, file size caps.
  - `brand.yaml` – name, tagline, handle, contact, grievance officer.
- Load these at runtime.

Then:

- Changing a colour, time, or limit doesn’t require touching core logic.
- You can have `config.dev.yaml`, `config.prod.yaml` if needed.

***

### 2.3 Add structured logging and error reports

Right now failures are probably printed to console or basic logs.

Add:

- A `logs/` folder with:
  - `fetch_YYYY-MM-DD.log`
  - `render_YYYY-MM-DD.log`
  - `review_YYYY-MM-DD.log`
- Structured logs (JSON or clearly parseable text) with:
  - Timestamp.
  - Stage.
  - Story IDs.
  - Errors and warnings.

Then you can:

- Quickly see what broke and when.
- Build simple scripts to summarise daily errors.
- Debug issues without re-running the whole pipeline.

***

### 2.4 Add a “dry-run + preview” mode for editors

Add commands like:

```bash
python render.py editions/today.json --preview
```

Which:

- Runs the full pipeline up to rendering.
- Generates:
  - A text report of stories, categories, lengths.
  - Low-res or watermarked previews of key assets.
  - A “risk report” (legal warnings, AI usage, missing sources).

Editor can:

- Approve or request changes before full render.
- Avoid wasting time on full-quality renders for stories that will be changed.

***

### 2.5 Add simple tests for new features

You already have 112 tests, which is excellent. For any new feature:

- Add at least one test that:
  - Fails if the feature is removed or broken.
  - Uses a small fixed input and checks the output.

Examples:

- Test that a story with no sources fails validation.
- Test that a crime headline without allegation markers fails.
- Test that a reel longer than the max limit fails.
- Test that a correction field appears in the generated caption.

This keeps the system stable as you add improvements.

***

### 2.6 Add a lightweight data layer for stories

Instead of only JSON files in `editions/`, consider:

- A simple SQLite database:
  - `stories` table: id, date, headline, category, location, sources, status.
  - `corrections` table: story_id, what_changed, when, why.
  - `sources` table: story_id, URL, type, fetched_at.

Benefits:

- Easy queries like “show all crime stories in Byndoor last month”.
- Better analytics and internal search.
- Easier to generate monthly digests and evergreen content.

You can still keep JSON for rendering; the DB is just for indexing and analysis.

***

### 2.7 Add a plugin-style hook for new formats

Define a simple interface for new templates/formats:

- A Python base class like `BaseTemplate` with methods:
  - `validate(edition)`
  - `render(edition, output_dir)`
  - `copy_templates()` (captions, metadata)
- New formats are just new classes that implement this.

Then:

- Adding a new format (e.g. Twitter/X card, Telegram sticker, PDF brief) doesn’t require rewriting the core renderer.
- You can enable/disable formats via config.

***

## 3. Experts: clarify roles and add a few high-leverage ones

You already have a rich “13 experts” model. The goal now is to make these roles more practical and less theatrical.

### 3.1 Consolidate into 6–7 core human-facing roles

Map the 13 AI experts into fewer, clearer responsibilities:

1. **News Editor (ಮುಖ್ಯ ಸಂಪಾದಕ)**  
   - Owns story selection, sources, and final go/no-go.
   - Uses the verification checklist and confidence scores.

2. **Legal & Ethics Guard**  
   - Focuses on crime, minors, sexual offences, defamation, privacy.
   - Reviews flagged stories and correction cases.

3. **Design Lead**  
   - Owns brand consistency, template changes, and visual quality.
   - Reviews new templates or major visual experiments.

4. **Video Lead**  
   - Owns footage edits, music licences, QC reports.
   - Decides which events get long-form vs short-form treatment.

5. **Community & Corrections Manager**  
   - Handles DMs, WhatsApp messages, corrections, and reader tips.
   - Maintains the corrections log and weekly clarifications post.

6. **Growth & Analytics Lead**  
   - Reviews weekly performance digest.
   - Proposes experiments (posting times, formats, topics).

7. **AI Workflow Designer**  
   - Maintains prompts, AI skills, and automation scripts.
   - Ensures AI outputs are safe, consistent, and documented.

One person can play multiple roles, but each role should be explicit.

***

### 3.2 Define clear “expert checklists”

For each role, create a 5–10 point checklist, e.g.:

**News Editor checklist:**

- [ ] Each story has at least one source URL.
- [ ] Numbers and place names match sources.
- [ ] Crime stories have allegation markers in headline and reel line.
- [ ] Minor/sexual-offence flags set where relevant.
- [ ] Status (confirmed/developing/unconfirmed/official) is correct.

**Legal & Ethics checklist:**

- [ ] No guilt stated before conviction.
- [ ] No identifying details for minors or sexual-offence victims.
- [ ] No sensational or gore-heavy wording.
- [ ] Corrections are clear and visible.

These checklists can be:

- Printed or stored as Markdown.
- Partially automated (AI pre-fills, human ticks).

***

### 3.3 Add two new expert perspectives

#### 3.3.1 Local Community Advisor

Role:

- Ensures stories reflect what locals actually care about.
- Flags tone issues (condescending, too formal, disconnected from ground reality).
- Suggests hyperlocal angles (specific wards, markets, schools, bus routes).

How to implement:

- Can be you, a friend, or a small group of regular readers.
- Once a week, they review:
  - Top stories.
  - Reader messages.
  - Suggest 2–3 topics you missed.

This keeps the channel rooted in the community, not just in scraped headlines.

***

#### 3.3.2 Trust & Transparency Lead

Role:

- Owns everything related to credibility:
  - Source disclosure.
  - Corrections policy.
  - “How we work” explanations.
  - Response to complaints.

Tasks:

- Maintain a simple “About Oormani Suddi” page/post:
  - How stories are sourced.
  - How corrections work.
  - How to send tips or complaints.
- Review any serious complaint or controversy.
- Approve any change to how sources or corrections are shown.

This role turns trust from a vague value into an owned responsibility.

***

### 3.4 Make AI a “junior reporter + designer”, not an editor

Reframe the AI’s role explicitly:

- **AI as:**
  - Research assistant (summarising articles, extracting facts).
  - Draft writer (first version of headlines, decks, captions).
  - Design assistant (suggesting layouts, generating images).
  - QA assistant (running checklists, flagging risks).

- **Human as:**
  - Final decision-maker on what is true and what is publishable.
  - Owner of tone, ethics, and community relationship.

Document this in your internal guide so future contributors don’t accidentally treat AI output as final truth.

***

### 3.5 Add a simple “expert review” step for major changes

For any significant change (new template, new platform, major workflow shift):

- Require a mini-review:
  - 1-page note: what, why, expected impact, risks.
  - Checked by:
    - News Editor.
    - Design Lead.
    - Trust Lead.
  - Recorded in `docs/DECISIONS.md` with a decision ID.

This keeps the system coherent as it grows.

***

## 4. A practical “level-up” roadmap

### Phase 1 (next 2–4 weeks)

- Implement:
  - Source-aware drafting.
  - Confidence scores.
  - Verification checklists.
  - Correction template and log.
  - Config layer for categories, limits, brand.
- Clarify:
  - 6–7 core roles.
  - Basic checklists for each.

### Phase 2 (1–3 months)

- Add:
  - Modular code structure.
  - Structured logging.
  - Preview/dry-run mode.
  - Simple SQLite story index.
- Start:
  - Weekly performance digest.
  - Monthly “what changed in your taluk” post.
  - Local community advisor input.

### Phase 3 (3–6 months)

- Expand:
  - Evergreen explainers.
  - Local guide content.
  - More sophisticated video cutdowns.
- Refine:
  - AI image style.
  - Trust strip and transparency features.
  - Expert review process for changes.

***

If you tell me your current tech stack (exact Python version, OS, how you run scripts), I can sketch concrete file structures and example code snippets for the config layer, modularisation, and verification checklists next.

# Level-Up Guide for Oormani Suddi

Free, easy, high-impact moves — organized by effort and priority. I've read the whole book; these are things that build on what's already good, not replacements for it.

---

## The single biggest free win: Bhashini + AI4Bharat

Before anything else, know these exist. They change the economics of the entire system.

| Tool | What it gives you | Why it matters here |
|---|---|---|
| **Bhashini** (bhashini.gov.in) | Free government API for Indian-language TTS, ASR, translation | Replaces Google TTS cost, gives you Kannada ASR for footage, translates English sources |
| **AI4Bharat IndicTTS** | Open-source Kannada TTS | Local, free, no API key, no rate limit |
| **AI4Bharat IndicWhisper** | Open-source Kannada ASR | Transcribes real footage — chants, speeches, crowd |
| **IndicTrans2** | Free translation | English sources → Kannada drafts |
| **Sarvam AI** | Indian LLM with strong Kannada | Alternative to Gemini for text tasks |

**Why this is the biggest win:** The doc's issue #3 (Gemini key dual-use) and the entire voice section (Section 15) assume Google TTS is the only option. It isn't. Bhashini is free, designed for exactly this use case, and government-backed — which matters for a news publisher's credibility. Adopting it:
- Removes the API cost concern
- Gives you ASR you don't currently have (footage transcription)
- Gives you translation you don't currently have
- Removes the single-key dependency

**Effort:** A few hours to add as an alternative engine in `brand/voice.py`. Keep Google as fallback.

---

## Tier 1 — Do this week (free, easy, high impact)

| # | Move | Why | Effort |
|---|---|---|---|
| 1 | **Commit everything to git + add `requirements.txt`** | Issue #18. Existential. One machine failure = total loss. | 30 min |
| 2 | **Name a Grievance Officer** | Issue #4. Legal requirement under IT Rules 2021. | 10 min |
| 3 | **Set up 3-2-1 backup** (git + external drive + Backblaze B2) | Same as #1. Backblaze is ~$6/month. | 1 hour |
| 4 | **Add Whisper for footage transcription** | Free, local, open-source. Gives you searchable transcripts, auto-captions, auto-chapters, auto-descriptions for Lines B & C. | 3–4 hours |
| 5 | **Add Bhashini TTS as an option** | Free Kannada voice, no API key. | 3–4 hours |
| 6 | **Fix the fabrication risk in the fetch** (issue #2) | Fetch full article bodies with `trafilatura` (free) and constrain Gemini to paraphrase only that. Or reduce to one-line leads with source links. | 1 day |
| 7 | **Set up launchd for 06:05 fetch** (issue #19) | Already written, just not scheduled. Add a failure alert. | 30 min |
| 8 | **Add a Telegram bot for notifications** | Team already uses Telegram. Bot sends morning brief, "start"/"stop" commands, approval status, schedule reminders. | 4–6 hours |
| 9 | **RSS feed of your own output** | Free discovery. Other aggregators pick it up. | 2 hours |
| 10 | **WhatsApp Channel + Instagram Broadcast Channel + YouTube Community posts** | Free one-way broadcast channels you're not using. Breaking news alerts. | 30 min |

---

## Tier 2 — This month (free, medium effort, high impact)

| # | Move | Why | Effort |
|---|---|---|---|
| 11 | **Ollama + local LLM** (Llama 3.2 3B or Gemma 2 2B on 8GB M1) | Free, private, offline. Solves issue #3. Handles copy drafts, hashtags, alt text, classification. | 1 day |
| 12 | **Analytics ingestion** — pull IG/YouTube analytics via APIs into local SQLite | Needed for the 30-day review. Currently missing. | 1–2 days |
| 13 | **Simple local web dashboard** (Flask + HTML) | Shows today's package, preview images, approval buttons, schedule. One-click approve. Much faster than terminal. | 2–3 days |
| 14 | **Reader tip intake via WhatsApp/Telegram** | A number readers can send tips to. Auto-parse into inbox. Local news thrives on reader tips. | 2 days |
| 15 | **Weather + tide + transport data feeds** | IMD, INCOIS, KSRTC — all free. High utility for coastal readers. Automated alerts. | 2 days |
| 16 | **Correction tracking system** | When a correction is issued, update caption, post correction card, log it. | 1 day |
| 17 | **Auto-generate `WhatsApp` text** (issue #17) | Already generated but not written. Fix that. | 2 hours |
| 18 | **Local image generation** (Stable Diffusion 1.5 or Flux Schnell) | Free, private, unlimited. Solves the "Gemini key for images" rule violation. | 1–2 days |
| 19 | **Auto-chapter generation** from Whisper transcript | For long videos. | 4 hours |
| 20 | **C2PA / Content Credentials** for AI content labeling | Standard for AI provenance. Future-proofs against platform rules. | 1 day |

---

## Tier 3 — This quarter (bigger projects, still free)

| # | Move | Why |
|---|---|---|
| 21 | **Agentic workflow** — turn the 13-step checklist into an agent that calls tools, loops, escalates to human only when needed | Currently the AI plays each expert. An agent could actually *do* the steps. |
| 22 | **RAG over past editions** — embed all past editions, retrieve related coverage when new stories come in | Gives context, prevents contradictions, enables "as we reported earlier" links. |
| 23 | **Multimodal QA** — vision model reviews rendered cards: "Does this look professional? Is text legible? Brand consistent?" | Automated design review. Catches issues before the human sees them. |
| 24 | **Open-source the framework** (not the content) | Builds reputation, attracts contributors, strengthens grant applications. |
| 25 | **Simple website** (GitHub Pages / Cloudflare Pages — free) | Needed for SEO, AdSense, credibility. RSS feed lives here. |
| 26 | **Email newsletter** (Substack / Buttondown — free tier) | Local news thrives on email. Own your audience. |
| 27 | **Productize the system** — other local newsrooms in India could use this | SaaS, open-source + support, or training. Could be a revenue line. |
| 28 | **Grants** — Google News Initiative, Meta Journalism Project, local foundations | This system is a strong grant candidate. The doc *is* the application. |

---

## AI usage — specific upgrades

**1. Replace headline-only synthesis with full-text synthesis.**
Currently the fetch sends only headlines to Gemini but asks for 3–5 detailed paragraphs. Use `trafilatura` (free, Python) to fetch full article bodies, then constrain Gemini: "Paraphrase only what is in the provided text. If a detail is not in the text, do not include it." Attach source URL per story.

**2. Add Whisper for footage.**
```bash
pip install faster-whisper
# or whisper.cpp for efficiency
```
Transcribe real audio → searchable transcript → auto-captions, auto-chapters, auto-descriptions, auto-lower-thirds suggestions. Huge for Lines B & C.

**3. Local LLM for routine tasks.**
Ollama + Llama 3.2 3B or Gemma 2 2B. Use for: hashtag generation, alt text, classification, simple copy drafts. Keep Gemini for complex synthesis. This solves issue #3 (key dual-use) and removes the cost concern.

**4. Embedding-based deduplication.**
Replace MD5-on-first-60-chars with `sentence-transformers` (free, local). Catches semantically similar stories from different sources — much better than string matching.

**5. Source credibility scoring.**
Track which sources have been reliable. Weight them. Simple SQLite table. Improves the editorial signal.

**6. Claim extraction, not paragraph generation.**
Instead of asking Gemini for paragraphs, ask for structured claims: `{who, what, where, when, source_url}`. This constrains fabrication and gives the editor a brief, not a draft.

**7. Auto-thumbnail selection.**
Use face detection + motion analysis + composition rules to pick the best frame. Currently manual.

**8. Sentiment monitoring on comments/DMs.**
Flag urgent issues, track reader mood. Free via platform APIs.

**9. Trend detection.**
Monitor local social media for trending topics. Free via public APIs.

**10. Voice quality scoring.**
Automatically score TTS output for naturalness, pronunciation errors, pacing. Flag below threshold.

---

## Automation — specific upgrades

**1. Scheduled posting via official APIs (with human click).**
Instagram Graph API and YouTube Data API allow scheduled posts. The doc's principle "it never posts by itself" is correct — but you can automate *preparation* and have a human click "approve and schedule." This eliminates the manual upload bottleneck without removing accountability.

**2. Telegram bot for the workflow.**
```
/start  → morning brief
/status → today's package status
/approve → approve and schedule
/schedule → today's schedule
/alerts → recent failures
```
Much faster than opening a terminal. The team already uses Telegram.

**3. Git hooks.**
- Pre-commit: run tests
- Pre-push: backup
- Post-merge: regenerate docs

**4. GitHub Actions (free tier).**
Run tests, builds, backups. 2,000 minutes/month free for private repos.

**5. Watchdog script.**
Checks if the 06:05 fetch succeeded. If not, sends Telegram alert. Runs every 30 minutes.

**6. Queue system for footage edits.**
Simple SQLite-based queue so jobs don't conflict on the 8GB M1.

**7. Resource monitoring.**
Track CPU, RAM, disk. Alert before failures. The M1 can kill jobs when memory runs out.

**8. Auto-cleanup at end of day.**
Already done with "stop" — could be automatic.

**9. Auto-archive old editions to cold storage.**
External drive + Backblaze. Keeps the working directory small.

**10. Weekly/monthly analytics reports.**
Auto-generated from ingested analytics. Needed for the 30-day review.

---

## Content & growth — free channels you're missing

| Channel | Why | Effort |
|---|---|---|
| **RSS feed** | Discovery, aggregation | 2 hours |
| **Email newsletter** (Substack/Buttondown) | Own your audience | 1 day |
| **Simple website** (GitHub Pages/Cloudflare Pages) | SEO, AdSense, credibility | 1–2 days |
| **WhatsApp Channel** | Free broadcast, breaking alerts | 30 min |
| **Instagram Broadcast Channel** | Free one-way | 30 min |
| **YouTube Community posts** | Free engagement between videos | 30 min |
| **Google Business Profile** | Local search presence | 30 min |
| **Podcast** (repurpose bulletin audio) | New distribution | 1 day |
| **Reader polls** | Free engagement | 2 hours |
| **Weekly explainer** | Authority, search traffic | Ongoing |
| **Data journalism** (rainfall, crop prices, crime stats) | Stat cards already exist | Ongoing |
| **"Ask Oormani"** — reader questions answered | Free content, high engagement | Ongoing |
| **Local history** — "This day in coastal Karnataka" | Evergreen, shareable | Ongoing |
| **Fact-check template** | For viral local claims | 1 day |
| **Reader photos pipeline** | Readers send photos, you verify | 2 days |

---

## Architecture — small changes, big wins

**1. Single source of truth for all numeric limits.**
Put every limit in `tokens.py` or `config.py`. Have all rules, docs, and tests reference it. Eliminates issues #6, #7, #9, #12, #13 — the "rule files disagree" class of problems.

**2. Schema-first everything.**
JSON Schema for Story, Edition, Greeting. Generate validation from it. Generate docs from it. Already partially done — make it central.

**3. Idempotent renders.**
If the input JSON hasn't changed, skip the render. Saves time on re-runs.

**4. Content-addressed storage.**
Hash all assets (images, music, footage) to verify integrity and deduplicate.

**5. Circuit breakers.**
If Google TTS fails 3 times, switch to Bhashini automatically. If Gemini fails 3 times, switch to Ollama.

**6. Retry with exponential backoff everywhere.**
Currently only in the fetch. Apply to all network calls.

**7. Structured logging.**
When something fails at 06:05, you want to know why without reading logs manually.

**8. Observability.**
Metrics, traces, dashboards. Even simple ones.

**9. Runbook.**
When X fails, do Y. The system is complex enough to need one.

**10. Post-mortems.**
After every failure, write what happened and what changed. The doc already does this for the 14 September reel — make it a formal practice.

---

## My 30-day plan

If I were running this, here's the order I'd do things:

**Week 1 — Existential**
- Commit everything to git, add `requirements.txt` (Day 1)
- Name Grievance Officer, update `tokens.Brand` (Day 1)
- Set up 3-2-1 backup (Day 2)
- Fix fabrication risk in fetch (Days 3–4)
- Set up launchd for 06:05 fetch with failure alert (Day 5)

**Week 2 — Free AI upgrades**
- Add Bhashini TTS as an option (Days 1–2)
- Add Whisper for footage transcription (Days 3–4)
- Add Ollama for local LLM tasks (Day 5)

**Week 3 — Automation**
- Telegram bot for notifications and commands (Days 1–3)
- Analytics ingestion (Days 4–5)

**Week 4 — Visibility**
- Local web dashboard (Days 1–3)
- RSS feed + WhatsApp Channel + email newsletter (Days 4–5)

After 30 days, you'd have:
- A backed-up, version-controlled system
- Free Kannada TTS/ASR
- Local LLM for routine tasks
- Footage transcription
- A notification/command layer
- Analytics for the 30-day review
- A dashboard for the daily workflow
- New distribution channels

All free. All building on what's already there.

---

## Two final thoughts

**1. The system's biggest strength is its ethics. Don't compromise that for automation.**
The "it never posts anything by itself" principle, the no-override truth contract, the provenance system — these are why the system is trustworthy. Every automation should preserve them. The human click on "approve and schedule" is not a bug; it's the feature.

**2. The system's biggest weakness is that it's one Mac.**
Issue #18 is existential. If that machine dies before the work is committed and backed up, the channel's operational capability dies with it. This is the first thing to fix, not the last.

The doc is a strong foundation. These suggestions are about building on it — not replacing it. The ethics are right. The architecture is sound. The gaps are mostly in tooling and operational resilience, and most of them can be closed for free.
# Level-Up: Design, Development & Experts

Focused, free, buildable suggestions in the three areas you named. I'll assume the system book as the baseline and only propose things that extend it.

---

# 1. DESIGN

## 1.1 The design system gaps

The design system (Section 12) is strong on tokens and rules but thin in three places: **motion tokens, component contracts, and a visible style guide**. Here's how to close them for free.

### Add a motion token layer

Right now motion timing is scattered across D16, D45, D48, and `tokens.Motion`. Consolidate it into a single spec:

```python
MOTION = {
    "ease_out":      (0.16, 1, 0.3, 1),      # snappy entries
    "ease_in_out":   (0.65, 0, 0.35, 1),     # scene transitions
    "ease_soft":     (0.4, 0, 0.2, 1),       # gentle pushes
    "dur_micro":     0.18,   # button/badge appear
    "dur_short":     0.32,   # text rise
    "dur_medium":    0.55,   # card enter
    "dur_scene":     0.80,   # wipe / dissolve
    "stagger_text":  0.06,   # per-line
    "kenburns_min":  1.00,   # zoom start
    "kenburns_max":  1.055,  # zoom end
    "grain_opacity": 0.045,
}
```

Why it matters: every designer, editor, and AI assistant references the same numbers. No more "warn at 48s" vs "fail at 60s" drift — the gate reads from here.

### Component contracts

Each component in `brand/components.py` should declare its **inputs, outputs, and invariants** in one place:

```python
COMPONENTS = {
  "masthead": {
    "requires": ["brand_name", "logo"],
    "produces": ["masthead_layer"],
    "invariants": ["never covers safe zone", "always top-left"],
    "tokens_used": ["gold_500", "ink_950"],
  },
  "headline": {
    "requires": ["text", "category"],
    "invariants": ["fits 78 chars at base size", "never over photo focal point"],
    "fallback": "shrink_to_fit",
  },
  # ...
}
```

Generate `docs/COMPONENTS.md` from this. Now the design system is *machine-readable* and *documented* from one source.

### Add a live style guide page

A single `docs/styleguide.html` that renders:

- Every token (colour swatch, type specimen, spacing scale)
- Every component in every state
- Every safe-zone overlay
- Every category rail
- Every photo nature label (`ಸಂಗ್ರಹ`, `ಸಾಂದರ್ಭಿಕ`, `ಎಐ ರಚಿತ`, etc.)
- Every greeting theme

Free, static, regenerable by a script. Anyone (board, new editor, freelance designer) opens one file and sees the whole visual language. No more "what does the report card look like?" questions.

---

## 1.2 Design moves that would raise the level

These are the ones I'd prioritize. All free.

### A. Add a "quiet edition" variant

The system is loud (gold, film grain, Ken Burns, wipes). One edition per week — say Sunday — should be **quiet**: no grain, no gold rails except the masthead, slower motion, more white space, longer reading cards. Creates rhythm. Signals editorial maturity. Very cheap to build: pass a `mood` flag to templates that toggles 4–5 tokens.

### B. Add a "data edition" layout

You already have `stat_card`. Scale it: one edition per month where the lead story is a data story (rainfall, crop prices, crime stats, traffic). Uses the same templates but with a **chart component** — simple Kannada-labelled bar/line charts drawn with Pillow. Free, unique, high-shareability. Local news with data is rare and trusted.

### C. Add a "reader voice" layout

You have `quote_card`. Add a **`reader_quote_card`** for reader-submitted reactions, corrections, or tips. Different visual treatment (no gold, softer type, "ಓದುಗರ ಧ್ವನಿ" kicker). Turns readers into participants. Costs one template file.

### D. Weather as a first-class citizen

Coastal Karnataka weather is *the* recurring story. Build a **daily weather card** — tide, wind, rain forecast, sea state — driven by IMD/INCOIS feeds. One template, one data adapter, one scheduled post. High utility. Free data. Differentiates the channel from every other local outlet.

### E. The editorial plate should have variants

Currently one drawn coastal scene (D28, D31). Make 6–8: morning sea, monsoon sky, backwater, paddy field, temple gopuram silhouette, fishing boats, night harbour, lighthouse. Same drawing code, different parameters. Now the plate doesn't repeat, and it matches the story's mood. Solves a chunk of issue #5 too.

### F. Greeting themes → seasonal palettes

The greeting themes (sacred, lights, harvest, rajyotsava, national, serene) change ground and light. Add **seasonal palettes** that shift the ground colour across the year (monsoon slate, summer ochre, harvest amber, winter teal). The greeting genre then feels alive instead of formulaic.

### G. Kannada type specimen

You use Noto Sans Kannada Bold, Anek Kannada, Noto Serif Kannada, SF for Latin. Add:

- **A Kannada type specimen** in `docs/type-specimen.html` — every conjunct, vowel sign, numeral, and punctuation rendered in every house face at every size.
- **A "shaping regression" test** — a fixed string with hard conjuncts (`ಕ್ಷ`, `ಜ್ಞ`, `ತ್ತ`, `ದ್ದ`, `ಳ್ಳ`, `ಱ` if used) that must render identically every build. Extend the golden test.

### H. Photo treatment variants

Currently: gentle house grade, filmic roll-off (D30). Add three named grades:

- **`news`** — neutral, current default
- **`feature`** — warmer, slightly lifted shadows
- **`solemn`** — desaturated, cooler (obituaries, disasters)

Named grades mean editors pick a *mood*, not a slider. Cheap: three lookup tables, one parameter.

### I. Slide-level variants for carousel

Currently one slide per story. Add:

- **`context` slide** — background/why it matters (from `deck` + first fact)
- **`numbers` slide** — when the story has stats
- **`quote` slide** — when the story has a quote
- **`timeline` slide** — when multiple events are referenced

The carousel then reads like a small magazine, not a list of headlines. Same data, richer composition.

### J. Add an "explainer edition" once a week

One edition per week is a **single-story explainer** — `ವಿಶ್ಲೇಷಣೆ` category, 6–8 minute read, one card per beat, no reel. Builds authority. Ranks well on YouTube. Uses existing templates with a slower motion profile.

---

## 1.3 Design anti-patterns to fix now

Small things the book already hints at:

1. **The masthead must not appear on the outro** (Section 9 says it's off during outro — good). Confirm it's off on the greeting poster too.
2. **The `ಕೃಪೆ:` credit line is on every card.** Good. But it's often 11–13px. Raise minimum to 14px and give it its own baseline slot (D24 already covers translucent layers).
3. **AI disclosure line** — currently `ಎಐ ರಚಿತ ಚಿತ್ರ` on the card and in the caption. Add a **small drawn badge** (a stylized "AI" in a hairline circle) so it's visible in a thumbnail, not just readable at full size.
4. **Film grain at 4.5% is right.** At 1080×1920 it's fine; at 4K it will look noisy. Make grain scale inversely with resolution.
5. **The editorial plate is currently one composition.** See 1.2E — make it a family.

---

# 2. DEVELOPMENT

## 2.1 Architecture — the free, high-leverage changes

### A. Single config module

Right now numeric limits are scattered. Create `config.py`:

```python
LIMITS = {
  "headline_max": 78,
  "deck_max": 190,
  "reel_line_max": 46,
  "reel_points_max": 60,
  "hook_chars_max": 34,
  "hook_words_max": 7,
  "reel_len_target": (28, 42),
  "reel_len_warn": 48,
  "reel_len_fail": 60,
  "card_max": 12,
  "beat_max": 150,
  "bulletin_min": 60,
  "bulletin_max": 120,
  "reel_count_max": 5,
  # ...
}
```

Import it in `tokens.py`, `qa.py`, `review.py`, `copy.py`, and the rule files reference it. Eliminates the entire "issues #6, #7, #9, #12, #13" class of bugs.

### B. Schema-first validation

You have `schemas/`. Make them the *only* source of truth:

- Generate `Story.validate()` from the schema
- Generate `docs/AI_BRIEF.md` from the schema
- Generate `render.py --schema` output from the schema
- Fail the build if any of these drift

Use `pydantic` or `jsonschema` — both free.

### C. Idempotent renders

```python
# Hash the input JSON + tokens + template version
render_key = sha256(json.dumps(edition) + tokens_hash + template_version)
if cache.exists(render_key):
    return cache.get(render_key)
```

Saves minutes on every re-run. Important on 8GB M1.

### D. Content-addressed assets

Hash every image, music file, and footage clip on ingest. Store by hash. Now:

- Deduplication is automatic
- Integrity is verifiable
- The stock library can't drift
- No more "which version of `news_bgm.mp3` is this?"

### E. Circuit breakers

Wrap every external call (Gemini, Google TTS, RSS feeds, IMD) in a circuit breaker:

```python
@circuit_breaker(fail_threshold=3, reset_after=300)
def call_gemini(...): ...
```

When it trips, fall back: Gemini → Ollama. Google TTS → Bhashini. Udayavani RSS → cache.

### F. Structured logging

```python
logger.info("fetch.start", source="udayavani", run_id=...)
logger.warn("fetch.empty", source="oneindia", reason="0 items")
```

Write to JSON lines. Now failures at 06:05 are diagnosable without re-running.

### G. A real test pyramid

Currently: 112 tests. Good. Add:

- **Property tests** (Hypothesis, free) — "any valid Story produces a valid render", "no random string breaks the headline fitter"
- **Snapshot tests** for every template — one golden per template, not just one edition
- **Fuzz tests** for the truth contract — random JSON must never crash, always reject cleanly
- **Performance tests** — "a 4-story edition renders in < X seconds on the M1"

### H. Deprecation discipline

When a rule changes, add a `deprecated_at` field. The gate warns for one edition, fails the next. Never silent change.

---

## 2.2 AI usage — the free, level-up moves

### A. Local LLM for routine tasks (Ollama)

```bash
brew install ollama
ollama pull llama3.2:3b   # or gemma2:2b
```

Use for:
- Hashtag generation
- Alt text
- Category classification
- Headline variants
- First-comment drafts
- WhatsApp text
- Simple translation

Keep Gemini (or better, Sarvam) for the hard stuff: full news synthesis from article bodies.

This alone solves issue #3.

### B. Bhashini for TTS and ASR

- **TTS**: free Kannada voice, no key, government-backed
- **ASR**: transcribe footage — chants, speeches, crowd
- **Translation**: English sources → Kannada drafts

Add as an engine in `brand/voice.py`. Fall back chain: Bhashini → Google → Gemini.

### C. Whisper for footage

```bash
pip install faster-whisper
```

Per footage clip, produce:
- Searchable transcript
- Auto-captions (time-aligned)
- Auto-chapter suggestions (scene changes + keyword shifts)
- Lower-third name suggestions (proper-noun extraction)
- Auto-description draft

This is the single biggest upgrade to Lines B and C.

### D. Embeddings for deduplication

Replace MD5-on-first-60-chars with `sentence-transformers` (`paraphrase-multilingual-MiniLM`). Catches semantically similar stories across sources and languages. Free, local, ~80MB.

### E. Claim extraction instead of paragraph generation

Change the fetch prompt from "write 3–5 paragraphs" to:

```json
[
  {"claim": "...", "source_url": "...", "source_name": "...", "confidence": "high|medium|low"}
]
```

Then let the sub-editor (human or AI) assemble. This is the *only* structurally sound fix for issue #2. It also makes the legal checks sharper because each claim is source-tagged.

### F. Vision model for QA

Add a vision review step: for each rendered card, ask a local vision model (Llava, Qwen-VL, or Gemini's free tier):

- Is the text legible?
- Is the brand mark present?
- Is any element in the safe zone?
- Is the photo appropriate for the category?
- Is the AI disclosure visible?

This catches what the pixel checks miss. Can be a warning layer, not a block.

### G. Voice quality scoring

Score each TTS output for:
- Pronunciation (compare against expected phonemes)
- Pacing (words per second)
- Naturalness (a small classifier)

Flag below threshold for the native ear. Saves editor time.

### H. Auto-thumbnail selection

For footage: use face detection + composition rules + motion analysis to pick the best 3 frames. Present them to the editor. Free via OpenCV.

### I. Reader tip triage

When tips arrive (WhatsApp/Telegram), a local LLM classifies: newsworthy / not / needs verification / spam. Editor sees the shortlist.

### J. Style-consistent generation

When the LLM generates a caption or a description, feed it 3 past examples of the same category as few-shot. The output then sounds like *your* newsroom, not generic LLM prose.

---

## 2.3 Automation — free, high-leverage

### A. Telegram bot as the control surface

The team already uses Telegram. Build a bot with:

```
/start          → morning brief
/today          → package status
/approve        → approve + schedule
/preview NN     → send card/reel frame
/schedule       → today's plan
/alerts         → recent failures
/stock          → add image to stock
/stop           → end of day
```

Uses the free Bot API. Replaces terminal for 90% of daily actions.

### B. launchd jobs

- 06:05 — fetch
- 06:15 — watchdog (check fetch succeeded, else alert)
- 08:00 — send morning brief to Telegram
- 22:00 — end-of-day cleanup
- Weekly — analytics pull

All free with macOS `launchd`.

### C. GitHub Actions for CI

Free tier gives 2,000 minutes/month for private repos. Run:

- Tests on every push
- Golden test on every PR
- Nightly backup to encrypted storage
- Weekly dependency audit

### D. Scheduled posting (with human click)

Instagram Graph API and YouTube Data API support scheduled posts. The principle stays: **a human clicks "approve and schedule."** The upload itself is automated. Removes the manual bottleneck without removing accountability.

### E. Watchdog + alerts

```python
# Every 30 min: did the 06:05 job succeed?
if not fetch_succeeded_today():
    telegram.send("@editor — fetch failed, see inbox/.fetch_failed")
```

### F. Queue for footage edits

SQLite-backed queue so two heavy jobs never run at once on the 8GB M1. `project.json` gets a `queue_position` field.

### G. Auto-archive

At *stop*: gzip old editions to `archive/YYYY/MM/`, sync to external drive + Backblaze. Working directory stays small.

### H. Auto-generated analytics reports

Pull IG/YouTube analytics daily into SQLite. Weekly report:

- Top 5 posts by reach
- Best posting times
- Best reel lengths
- Best hashtags
- Best categories

This is what the 30-day review needs and currently doesn't have.

### I. RSS feed of your own output

`feed.xml` regenerated on every edition. Discovery, aggregation, podcast ingestion.

### J. Backup discipline

- Git remote (GitHub private, free)
- External drive (Time Machine)
- Backblaze B2 (~$6/mo, but free for <10GB)
- Weekly encrypted archive

Three copies, two media, one offsite. This is the #1 fix for issue #18.

---

## 2.4 The single architecture change I'd argue for

**Turn the 13-step newsroom into an agent with tools.**

Currently: an AI assistant *plays* 13 experts, each reading a checklist. It doesn't actually *do* anything — it narrates.

What it could be: an agent that:

1. Calls `fetch_news()`
2. Calls `check_kannada(text)` — a real Kannada grammar tool
3. Calls `check_legal(story)` — the real guards
4. Calls `pick_images(story)` — real stock search
5. Calls `render(story)` — real rendering
6. Calls `audit_sync(reel)` — real check
7. Calls `qa_preflight(edition)` — real gate
8. Escalates to human only when a check fails or a judgement is needed

This is the difference between *role-play* and *automation*. The book already has all the tools — they just aren't chained. Chaining them (with a simple state machine, free) is the single biggest level-up available.

Keep the AI in the loop for the judgement steps (taste, culture, news). Take it out of the mechanical steps.

---

# 3. EXPERTS

The 12-expert panel and 13-step newsroom are the most ambitious part of the system — and the most fragile, because an AI *playing* an expert is not an expert.

Here's how to level this up without hiring anyone.

## 3.1 The core fix: separate "mechanical" from "judgement"

Split every expert step into two kinds of checks:

| Kind | Who checks | How | Blocks? |
|---|---|---|---|
| **Mechanical** | Code | Deterministic test | Yes |
| **Judgement** | Human | Explicit sign-off | Yes |

Currently the book mixes them. Example: "Story Producer: the story can be stated in one line" — that's a judgement. "Duration 30–45s" — that's mechanical.

**Every judgement call should require a named human sign-off in `APPROVAL.md`.** Not a score from an AI. A line:

```
taste_approved_by: Shameek
culture_approved_by: Shameek
news_judgement_approved_by: Shameek
```

Then the AI can still *prepare* the judgement (evidence, options, recommendation), but the human owns it. This is what Section 21 says should happen. Make the code enforce it.

## 3.2 Upgrade each expert with a real tool

Free tools that make each role more than a checklist:

| Expert | Free tool that actually does the work |
|---|---|
| **Kannada Language** | `indic-nlp-library`, `kannada-nlp`, LanguageTool (Kannada exists), Bhashini grammar API |
| **Sub-Editor** | Embedding-based dedup + claim extraction (see 2.2E) |
| **Photojournalism** | Local CLIP model to score image-story relevance |
| **Culture & Ethics** | Vision model + a curated reference set of approved/blocked images |
| **Design QA** | Golden test + vision QA (see 2.2F) |
| **Broadcast Voice** | Bhashini TTS + voice quality scoring (see 2.2G) |
| **Retention** | Whisper transcript + scene-change detection + auto-hook detection |
| **Social Media** | Local LLM + few-shot examples from past captions |
| **Scheduling** | Analytics ingestion (see 2.3H) — real data, not guesses |
| **Legal** | Existing guards + a case-law lookup (Indian Kanoon has a free API) |
| **Final QA** | Existing gate + vision QA |
| **Chief Editor** | Existing code gate |

Now each "expert" is backed by a tool. The checklist becomes the *interface*, the tool does the *work*.

## 3.3 Add three missing experts

The current panel misses three roles that a real newsroom has:

### A. Corrections & Accountability Editor

Owns:
- Corrections tracking (log, update, notify)
- Reader complaint responses (IT Rules timeline: acknowledge 24h, resolve 15 days)
- Retraction workflow
- Public corrections log on the website

Free to add as a rule file + a small SQLite table.

### B. Data & Verification Editor

Owns:
- Statistical claims (rainfall, prices, crimes) — sourced, not asserted
- Fact-check workflow for viral claims
- Data journalism (see 1.2B)

Free: a rule file + a `data_claim` schema field.

### C. Community & Engagement Editor

Owns:
- Reader tips triage (see 2.2I)
- Comment moderation
- Reader voice features (see 1.2C)
- WhatsApp/Telegram channel

Free: a rule file + Telegram bot integration.

These three are what separate a *publisher* from a *broadcaster*. The system is currently a broadcaster.

## 3.4 Make the expert panel *evidence-based*

Currently, the panel scores 10/10 with "evidence (numbers, timestamps, the sheet)". Good — but the evidence isn't structured.

Change to a **rubric with fixed evidence types**:

```json
{
  "expert": "Sound Engineer",
  "claim": "Loudness is −14 LUFS ±1",
  "evidence": {
    "type": "measurement",
    "tool": "ffmpeg ebur128",
    "value": -14.2,
    "threshold": [-15, -13],
    "pass": true,
    "artifact": "_review/loudness.json"
  }
}
```

Every expert's verdict must reference a tool, a measurement, and an artifact. This makes the panel auditable and teaches the AI to gather evidence rather than assert.

## 3.5 The "12-expert panel" reframed

I'd reframe it honestly as:

> **A 12-dimension QA rubric with tool-backed evidence and human sign-off on judgement calls.**

Because:
- It *is* 12 dimensions (real)
- It *is* tool-backed (once you add the tools above)
- It *requires* human sign-off on taste, culture, and news judgement (once the code enforces it)

The current framing ("panel of experts") oversells what an AI playing roles can do. The reframed version is *stronger* because it's honest and because it actually delivers.

## 3.6 A training loop for the experts

Every time a human overrides an AI judgement (e.g. "this caption is wrong"), log it:

```
override_log.jsonl:
{"expert": "Social Media", "story": "...", "ai_said": "...", "human_said": "...", "reason": "..."}
```

Monthly, review. Patterns become:
- New rules in the checklist
- New few-shot examples
- New tests

The experts improve over time. Free. This is how the system gets *smarter*, not just *more documented*.

## 3.7 The culture expert needs a reference library

The culture expert "can veto" — but on what basis? Build a **reference library**:

- Approved images (with metadata: what's respectful, why)
- Blocked images (with metadata: what was wrong)
- Names, spellings, honorifics
- Ritual sequences and what's sacred at each stage
- Regional variations (Badagutittu vs Thenkutittu Yakshagana, etc.)

Then the culture check is *retrieval against the library*, not a vibe. Free. A folder of images + a JSON of rules.

---

# The single most important suggestion

If I could only make one change across all three areas:

> **Split every check into mechanical (code, blocks) and judgement (human, blocks), and require a named human sign-off on every judgement call in `APPROVAL.md`.**

Everything else follows from this:
- Design: taste decisions become human-owned
- Development: the code enforces who signed what
- Experts: the AI prepares, the human decides, the file records it

The book's Section 21 already says "taste, cultural judgement and news judgement remain human responsibilities." But the *workflow* doesn't force a human into those seats. Fix that and the system is no longer an AI *playing* a newsroom. It's a newsroom *using* AI.

That's the level-up. Everything above is in service of it.

---

## A short reading list (all free)

- **Bhashini** — bhashini.gov.in
- **AI4Bharat** — ai4bharat.org
- **IndicNLP** — github.com/AI4Bharat/IndicNLP
- **faster-whisper** — github.com/SYSTRAN/faster-whisper
- **Ollama** — ollama.com
- **trafilatura** (article extraction) — github.com/adbar/trafilatura
- **CLIP / OpenCLIP** — for image-text matching
- **Indian Kanoon API** — indiankanoon.org (free tier)
- **PIB / IMD / INCOIS feeds** — free data for weather, tide, transport

None require payment. None require hiring. All extend what you already have.

Based on the comprehensive `SYSTEM_BOOK.md`, the **ಊರ್ಮನಿ ಸುದ್ದಿ (Oormani Suddi)** system already has an exceptionally strong foundation. The "Truth Contract," 13-step AI newsroom, and strict legal guards (POCSO, BNS, IT Rules) put it ahead of 99% of solo AI news operations. 

However, to make this system **"level up freely and easily"** (i.e., scale with minimal friction, reduce manual bottlenecks, and eliminate the 20 open decisions), you need to shift from *semi-automated* to *fully orchestrated* workflows. 

Here is a strategic, phased roadmap for improvements, focusing on AI enhancements and automation.

---

### Phase 1: Fix the Foundation (Resolve Section 22 Open Decisions)
*Before scaling, plug the leaks. These are low-effort, high-impact fixes.*

1. **Solve the "Hallucination" Fetch (Issue #2)**: 
   - **Current**: Sends only headlines to Gemini and asks for detailed paragraphs, risking invented facts.
   - **Upgrade**: Implement a lightweight **RAG (Retrieval-Augmented Generation)** step. Use a library like `readability-lxml` or `newspaper3k` to scrape the *first 3 paragraphs* of the source URL along with the headline. Feed *that* to Gemini with the prompt: *"Summarize only using the provided text. Do not add external details."*
2. **Separate API Keys (Issue #3)**: 
   - Create a dedicated, low-cost API key (e.g., a separate Google Cloud project or a cheaper model like `gemini-1.5-flash`) strictly for text synthesis, keeping the primary key reserved for high-quality TTS.
3. **Automate the Morning Fetch (Issue #19)**: 
   - Deploy a `launchd` plist (macOS) or cron job for 06:05 AM. 
   - **Automation**: Add a webhook to the script so that if `.fetch_failed` is triggered, it instantly sends a WhatsApp/Telegram alert to the editor: *"⚠️ Morning fetch failed. Check inbox/."*
4. **Lock Version 1.0 (Issue #18)**: 
   - Run `pip freeze > requirements.txt`. 
   - Set up a free **GitHub Actions** workflow that automatically runs `python3 -m unittest discover tests` on every push. This guarantees that no future change breaks the "Truth Contract."

---

### Phase 2: AI Content & Quality Upgrades
*Make the output indistinguishable from a premium, human-run local newsroom.*

1. **Upgrade the Voice (Section 15)**:
   - **Current**: Google TTS or Edge (Microsoft Sapna), which can sound synthetic.
   - **Upgrade**: Integrate a local, open-source TTS engine like **Piper** or **Coqui TTS**, fine-tuned on a few hours of a real, trusted Kannada news anchor’s voice. This runs locally on the M1 Mac, costs $0 per render, and sounds vastly more authentic and emotionally resonant than standard cloud TTS.
2. **Hyper-Local AI Imagery (Section 16)**:
   - **Current**: Generic AI images or stock.
   - **Upgrade**: Use a localized Stable Diffusion model (or a specific Midjourney/Flux prompt template) trained on coastal Karnataka aesthetics (e.g., specific Yakshagana costumes, Byndoor temple architecture, red-tiled roofs). This makes "representative" (`ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ`) images feel genuinely local, increasing audience trust.
3. **Automated Fact-Checking Agent (New Step)**:
   - Add a "Step 2.5" in the 13-step newsroom: An AI agent that takes the generated JSON and performs a quick web search (via a tool like `DuckDuckGo Search API`) to verify that the core claim (e.g., "rainfall in Kundapura") has at least one corroborating source before allowing the render to proceed.

---

### Phase 3: Workflow & Publishing Automation (The "Freely and Easily" Leap)
*Remove the human from the repetitive tasks, keeping them only for high-value editorial judgment.*

1. **Unified Approval Gate (Issue #11)**:
   - Currently, footage edits (Lines B & C) bypass the `review.py` Chief Editor gate. 
   - **Upgrade**: Modify `review.py` to accept a `project.json` from the footage editing tools. It should automatically verify: music license field is populated, no POCSO keywords in the transcript, and the engagement question is present. If it passes, it generates the `APPROVAL.md`.
2. **API-Driven Auto-Scheduling**:
   - **Current**: "A person uploads each file at its scheduled time." This is the biggest bottleneck for a solo operator.
   - **Upgrade**: Write a simple `publish.py` script that uses the **YouTube Data API v3** and **Meta Graph API** to read `schedule.json` and automatically upload and schedule posts at the exact prescribed times. (Note: Instagram requires a Meta Business account for API scheduling, which is highly recommended for this workflow).
3. **Automated Music Licensing Registry (Issue #16)**:
   - Create a `music_licenses.json` file. When the AI suggests a track from `assets/bgm_options/`, the system cross-references this JSON. If a track lacks a verified license, the render fails with: *"Error: Track 'news_bgm.mp3' lacks license metadata. Replace or update registry."*

---

### Phase 4: Analytics & Growth Automation
*Let the system learn what works and optimize itself.*

1. **Closed-Loop Scheduling Optimization**:
   - Write a monthly script that pulls basic analytics (views, retention) from YouTube/Instagram APIs.
   - The AI analyzes this data and automatically updates the default times in `schedule.json`. For example: *"Data shows 14:30 reels underperform by 40%. Shifting default slot to 15:30."*
2. **Smart Community Management**:
   - Use a tool like **ManyChat** or a custom WhatsApp Business API bot linked to `@oormanisuddi`. 
   - **Automation**: Auto-reply to common comments/DMs (e.g., *"ಧನ್ಯವಾದಗಳು! ಹೆಚ್ಚಿನ ಸುದ್ದಿಗಳಿಗಾಗಿ ನಮ್ಮನ್ನು ಫಾಲೋ ಮಾಡಿ."*). If a message contains keywords like "ದೂರು" (complaint), "ತಪ್ಪು" (wrong), or "ಸುಳ್ಳು" (false), it instantly forwards the message to the human Grievance Officer’s email, ensuring the 24-hour IT Rules acknowledgment deadline is never missed.

---

### Phase 5: Legal & Compliance Hardening (Future-Proofing)
*Protect the solo operator from the immense burden of the IT Rules.*

1. **Automated Compliance Archiving**:
   - The IT Rules require maintaining records of complaints and actions. Create a `compliance_log.md` that automatically appends an entry every time a correction is published or a user complaint is received, timestamped and linked to the original `edition_XXX.json`. This makes annual audits or government inquiries a 5-minute task instead of a 5-day panic.
2. **Invisible Synthetic Metadata**:
   - Beyond the visible `ಎಐ ರಚಿತ ಚಿತ್ರ` label, use a Python library like `piexif` or `ffmpeg` to inject **C2PA (Coalition for Content Provenance and Authenticity)** or basic EXIF metadata into every generated image and video, explicitly stating `"Generated by AI, Oormani Suddi Newsroom"`. This proactively satisfies emerging global and Indian platform policies on synthetic media.

---

### 🚀 Your Immediate Next 3 Steps (To get to v1.0 this week)

1. **Hold the Board Meeting**: Resolve the 20 decisions in Section 22. (Strongly recommend accepting the document's recommendations, especially making AI reels Instagram-only and fixing the morning fetch hallucination risk).
2. **Run the Lock Procedure**: 
   - Update `brand/tokens.py` and `AGENTS.md` with the board's decisions.
   - Run `python3 -m unittest discover tests`.
   - Commit with the message `"chore: v1.0 board-approved lock"` and generate `requirements.txt`.
3. **Build the `publish.py` Scheduler**: This single automation will save the operator ~5–10 hours per week, instantly making the system feel "free and easy" to run.

By implementing these upgrades, **ಊರ್ಮನಿ ಸುದ್ದಿ** will transition from a "fragile, highly-managed experiment" to a **resilient, self-driving local news institution** that can reliably serve coastal Karnataka with minimal daily human intervention.

To make **ಊರ್ಮನಿ ಸುದ್ದಿ (Oormani Suddi)** "level up freely and easily," we must evolve the system from a **fragile, linear, single-machine script** into a **resilient, modular, and self-optimizing media engine**. 

Based on the deep constraints and architecture detailed in the `SYSTEM_BOOK.md`, here is the blueprint for upgrading the three core pillars: **Design, Development, and Experts**.

---

### 1. DESIGN: From "Static Pixel-Pushing" to "Dynamic Generative Layouts"
*Current State (Sections 5, 12):* Design is handled by Python (`Pillow`, `raqm`) drawing pixels on a canvas based on strict `tokens.py`. While beautiful, it is rigid. Kannada typography is notoriously difficult to render perfectly with basic image libraries (leading to Issue #46: missing glyphs/baseline issues).

#### 🚀 The Level-Up Strategy:
**A. Shift from Python Canvas to Headless Browser Rendering (HTML/CSS)**
*   **The Fix:** Stop drawing text and layouts with Python `Pillow`. Instead, have the Python backend generate a structured JSON/HTML file, and use a headless browser (like **Playwright** or **Puppeteer**) to render the final image/video frames.
*   **Why it levels up:** 
    *   **Perfect Kannada Typography:** Browsers natively handle complex Kannada conjuncts, baseline alignments (D2), and font fallbacks (D4) flawlessly. No more missing glyphs.
    *   **CSS Animations for Reels:** Instead of calculating Ken Burns zooms and text easing in Python (`brand/motion.py`), you can use CSS `@keyframes`. This makes creating complex, broadcast-quality motion graphics trivial and infinitely customizable.
    *   **Responsive Templates:** You can use CSS Grid to make templates that automatically adapt if a headline is 40 characters vs 78 characters, eliminating the need for hardcoded "drop content in editorial order" logic.

**B. Parametric "Design Atoms" instead of 11 Rigid Templates**
*   **The Fix:** Break the 11 templates down into "Atoms" (Masthead, Category Rail, Fact Card, Quote Block, Disclosure Strip). 
*   **Why it levels up:** The AI Design QA (Step 5) can dynamically assemble these atoms based on the *weight* of the news. A massive breaking news story gets a full-bleed red-rail atom; a minor civic update gets a compact text-card atom. The design system becomes fluid, not a fixed menu.

**C. Visual A/B Testing Engine**
*   **The Fix:** Generate two variations of a thumbnail or carousel cover (e.g., one with the deity's face, one with a wide landscape shot). Let the system track which one gets a higher Click-Through Rate (CTR) on YouTube/IG, and automatically update the `tokens.py` weighting for future renders.

---

### 2. DEVELOPMENT: From "Single-Machine Bottleneck" to "Resilient Cloud-Native Pipeline"
*Current State (Sections 2, 8, 21):* The entire 13-step newsroom, scraping, and heavy video rendering (Real-ESRGAN upscaling, 1440p encoding) runs on a single M1 Mac with 8GB RAM. This causes memory crashes, 2-hour render times, and blocks the editor (Issue #18, #19).

#### 🚀 The Level-Up Strategy:
**A. Decouple the Pipeline (State-Machine Architecture)**
*   **The Fix:** Break `render.py` into independent micro-services or distinct queue-based workers (e.g., using **Redis/Celery** or even simple local SQLite task queues).
    *   *Worker 1:* Fetch & Deduplicate
    *   *Worker 2:* Gemini Synthesis & Truth Contract JSON generation
    *   *Worker 3:* Asset Generation (HTML->Image, TTS Audio)
    *   *Worker 4:* Video Compilation & Upscaling
*   **Why it levels up:** If the video render crashes (OOM on the Mac), you don't lose the news fetch or the TTS audio. You just retry the video worker. The editor can also manually trigger a re-render of a single Reel without re-running the whole day's pipeline.

**B. Cloud GPU Offloading for Heavy Lifting**
*   **The Fix:** The M1 Mac should only act as the "Orchestrator." Offload the Real-ESRGAN upscaling and 1440p H.264 encoding to a cheap, on-demand cloud GPU (like RunPod, Modal, or AWS Lambda with GPU). 
*   **Why it levels up:** A 3-minute 1440p video that takes 2 hours on the Mac will render in **45 seconds** on a cloud GPU. This removes the physical hardware ceiling and allows the channel to scale to multiple daily editions effortlessly.

**C. Automated CI/CD & The "Golden Lock" (Solving Issue #18)**
*   **The Fix:** Move the codebase to GitHub. Set up **GitHub Actions** so that every time a change is pushed:
    1. It runs the 112 unit tests (`test_contract.py`, etc.).
    2. It runs the **Golden Test** (comparing pixel fingerprints).
    3. It automatically generates `requirements.txt` and builds a Docker container.
*   **Why it levels up:** The system becomes "deployment-proof." You can spin up an exact clone of the Oormani Suddi newsroom on any machine in the world in 5 minutes. The "Truth Contract" is mathematically guaranteed to never be broken by a bad code commit.

**D. Local RAG (Retrieval-Augmented Generation) for Zero Hallucinations**
*   **The Fix:** Solve Issue #2 (Invented Detail). Instead of sending headlines to Gemini and asking for paragraphs, use a local vector database (like **ChromaDB**). Scrape the *actual* HTML text of the Udayavani/OneIndia articles, chunk it, and store it. Gemini is then prompted *only* to translate and summarize the retrieved chunks. 
*   **Why it levels up:** 100% elimination of AI hallucinations. The system can legally and ethically cite the exact source paragraph.

---

### 3. EXPERTS: From "Linear 13-Step Checklist" to "Autonomous Multi-Agent Debate"
*Current State (Section 17):* The "Second Brain" uses a linear 13-step prompt chain where one AI persona hands off to the next. This is prone to context-window degradation and lacks true editorial nuance.

#### 🚀 The Level-Up Strategy:
**A. Multi-Agent Debate & Consensus (The "Virtual Editorial Board")**
*   **The Fix:** Instead of a linear handoff, instantiate the Sub-Editor, Legal Expert, and Kannada Expert simultaneously in a shared JSON workspace. 
    *   *Scenario:* A crime story comes in. The Sub-Editor wants to use the word "ಕೊಂದ" (killed) for high drama. The Legal Expert blocks it (BNS §356 violation). 
    *   *The Upgrade:* They "debate" in the background. The Legal Expert suggests "ಹತ್ಯೆ ಆರೋಪ" (murder allegation). The Sub-Editor accepts. The final JSON is output only when all agents reach a consensus score of >9/10.
*   **Why it levels up:** This mimics a real physical newsroom. It catches edge cases that a linear checklist misses and produces much higher-quality, legally bulletproof copy.

**B. The "Shadow Editor" (Machine Learning from Human Corrections)**
*   **The Fix:** When the human Chief Editor (Step 13) overrides an AI decision (e.g., changes a headline, rejects an AI image, alters a schedule time), the system logs the *Delta* (the difference between AI output and Human final).
*   **Why it levels up:** Once a month, an "Analytics Agent" reviews these Deltas and automatically rewrites the system prompts or adjusts the `tokens.py` weights. The AI experts literally *learn* the owner's taste and editorial instincts over time, requiring less and less human intervention.

**C. Parallel Execution DAG (Directed Acyclic Graph)**
*   **The Fix:** Steps 3 (Photojournalism), 4 (Culture/Legal Image), and 7 (Voiceover) do not depend on each other. They should run in parallel.
*   **Why it levels up:** Reduces the total "Time to APPROVAL.md" from ~15 minutes of sequential LLM API calls down to ~3 minutes. The editor gets the daily package almost instantly after the morning fetch.

**D. The "Analytics & Growth" Autonomous Agent (Solving Issue #21)**
*   **The Fix:** Currently, analytics are a "known limit." Introduce an Agent that connects to the YouTube Data API and Instagram Graph API. 
    *   It analyzes retention graphs (e.g., "Viewers drop off at 0:14 on Reels").
    *   It automatically updates the `schedule.json` and `tokens.py` (e.g., "Shorten hooks to 1.0s", "Shift 14:30 slot to 15:30").
*   **Why it levels up:** The system stops being a static machine and becomes a **self-optimizing organism** that grows its own audience based on empirical data, not just the board's initial assumptions.

---

### Summary of the "Level-Up" Architecture

| Pillar | Current State (v0.9 Draft) | Level-Up State (v1.0+ Autonomous) |
| :--- | :--- | :--- |
| **Design** | Python `Pillow` pixel drawing; 11 rigid templates; manual Kannada baseline math. | **HTML/CSS via Headless Browser**; Parametric Atoms; Native Kannada typography; CSS motion graphics. |
| **Development** | Single M1 Mac 8GB; Monolithic `render.py`; 2-hour renders; manual testing. | **Decoupled Task Queue**; Cloud GPU offloading; CI/CD Golden Locks; Local RAG for zero hallucinations. |
| **Experts** | Linear 13-step prompt chain; AI acts as a passive checklist follower. | **Multi-Agent Debate**; Parallel DAG execution; Shadow-learning from human edits; Auto-optimizing via API analytics. |

By implementing these changes, **ಊರ್ಮನಿ ಸುದ್ದಿ** transitions from a brilliant but fragile "science experiment" into an **enterprise-grade, autonomous local news institution** that can run freely, scale infinitely, and remain 100% compliant with the Truth Contract and IT Rules.


Good timing to ask — most of the "level up" moves here cost nothing but a day of setup. I've grouped them by what they fix, ordered roughly by impact-per-effort. All free, all run on the existing M1.

## 1. Automations that close your known gaps

| Problem (from the book) | Free fix | Effort |
|---|---|---|
| #19 — fetch not scheduled | `launchd` plist at 06:05 (launchd is built into macOS, more reliable than cron for a laptop that sleeps) | 1 hour |
| No failure alert when fetch breaks | Watch `inbox/.fetch_failed` with a launchd `WatchPaths` job → **ntfy.sh** push notification to your phone (free, no account, one curl). Same watcher for `APPROVAL.md` appearing → "package approved" ping | 2 hours |
| #18 — no version lock, no backups | `pip freeze > requirements.txt`; `git init` + free **private GitHub repo**; add a small `backup.sh` (commit + push) run hourly by launchd. Exclude media folders via `.gitignore` — code and rules are small | Half a day |
| Editor pastes first comment manually | The schedule script already knows the time — add a step that copies that hour's first comment to clipboard (`pbcopy`) and fires a notification: "Posting reel 03 now — first comment is on your clipboard" | 1 hour |
| 8MB file-size warnings handled by hand | `sips` is built into macOS — an auto-shrink pass (JPEG re-encode at quality 90, strip metadata) after render, only on files over limit | 1 hour |

That last row turns three warnings into zero human attention.

## 2. AI usage that makes the existing checks *stronger*, not busier

**Claim-vs-source audit on the morning fetch (directly addresses your worst issue, #2).** After Gemini synthesises the stories, run a second cheap pass: for each proper noun, number, and place in the output, check it appears in (or is trivially derivable from) the source headlines. Anything unanchored gets flagged `⚠️ verify` in `today.txt`. This doesn't replace the editor — it means the editor's eye goes to exactly the three sentences that matter. This is the single highest-value AI change you can make.

**Local Whisper as a free proof-reader for the TTS voice.** Your hazard checks catch problems in *text*. Run **whisper.cpp** (runs natively on the M1, no API cost, no key) on each rendered `reel_NN.mp4` audio and diff the transcription against the intended narration. You'd catch mispronunciations and dropped words that no text check can see — the "voice is synthetic, native ear decides" step becomes evidence-based instead of vibe-based.

**Free instrumental proof for music (fixes the "proof is by listening" limit).** Run the same Whisper over any candidate music track. If it produces intelligible lyric text → flag for human listen; if it produces gibberish/nothing → almost certainly instrumental. Not perfect, but it converts "the client must listen to every track" into "client only listens to flagged ones."

**Auto chapters for footage edits.** Whisper-transcribe the cleaned client audio, extract natural segment boundaries and repeated phrases (bell patterns, chant starts) as *suggested* chapter timestamps. Editor confirms instead of scrubbing for chapter points. Saves 30+ minutes per long edit.

**Weekly analytics digest, feeding your 30-day review automatically.** YouTube Data API is free. Pull views/watch-time per format (bulletin vs. footage vs. Shorts) into a Markdown digest every Sunday. The 30-day review in Section 23 currently requires someone to manually collect data — this makes the review a reading exercise instead of a data-entry exercise. Keep Instagram manual (no free API worth the pain); YouTube is where your rule-7 strategy lives anyway, and it's measurable.

## 3. Small "free level-ups" worth doing while you're in there

- **Two hooks per lead story.** Your copy engine can generate a second thumbnail line for free; post the alternates as a second cover the next day on Stories. You get A/B learning without any new infrastructure.
- **AI pre-screen for image culture checks** (not auto-approval). Feed each candidate stock/AI image through Gemini's vision with the culture checklist as the prompt; it *flags*, the human *decides*. Cuts the "regenerate until it passes" loop roughly in half.
- **Folder action on `out/{date}/_review/`**: a launchd job that opens the evidence frames in Preview automatically when the render finishes. The Chief Editor's "look with a consumer's eye" step should take 90 seconds, not require remembering a path.

## 4. What *not* to automate, even though you could

Your "a person uploads every post" and "no auto-posting" choices are correct — keep them, they're trust features, not inefficiencies. Same for the culture/veto checks and grievance replies. Automate the evidence-gathering *around* the human decisions, never the decisions.

## Suggested order

1. **This week (hours each):** backup + `requirements.txt`, ntfy alerts, clipboard first-comments.
2. **Next week (a day each):** claim-vs-source audit, Whisper voice verification, music register cleanup (#16).
3. **This month:** analytics digest, chapter suggestion, image pre-screen.

If you want, I can draft any of these as ready-to-drop-in scripts — the launchd plists + ntfy watcher and the Whisper verification harness are the two I'd start with. Which would be most useful?

Good framing — those are the three layers the whole machine is built from. Here's where I'd push each one, still free, still one-Mac-friendly.

## Design

**Your design system is already the strongest part — so the goal is consistency at scale, not more design.**

- **Unify motion across engines.** The AI reels/bulletin live in `brand/motion.py`; the footage tools have their own build scripts. Put timing, easing curves, wipe durations and Ken Burns parameters into `tokens.Motion` and make *both* engines read from it. Right now the footage edits and AI reels can drift apart visually — same brand, two dialects.
- **Extend the golden test to motion.** Today it fingerprints stills. Add frozen-frame fingerprint checks at fixed timestamps in reels/bulletin *plus* an audio check (a free chromaprint-style fingerprint of the narration track catches silent reels and swapped audio before the gate does).
- **Add an automated contrast/lint pass to `inspect()`.** Safe zones and file sizes are checked; add minimum text/background contrast ratios and minimum effective font size per format. This is pure arithmetic — cheap to enforce, and it catches degradation as more templates get added.
- **Auto-generate a template gallery.** A `--gallery` mode that renders all 11 templates with sample content into one contact sheet. After every design change it regenerates; the board and clients see the full system on one page, and drift becomes visible.
- **Two covers per reel.** `reel_NN_cover.jpg` plus a variant frame; Stories can A/B them next-day at zero extra production cost. Cover choice is currently a one-shot guess.
- **Resolve the category gap in design terms.** Either add "governance" as a 12th category with its own rail colour (it clearly exists editorially) or reject it — but decide, because silently recolouring a story is a design lie.

## Development

**The codebase's biggest risk isn't quality — it's that it's untracked, untested-in-CI, and re-renders everything from scratch.**

- **Lock and CI first.** Pin `requirements.txt`, tag `v1.0`, then put the 112 tests on **GitHub Actions** (free for private repos). Your editor hooks run tests locally; CI means a test failure can never be committed from any machine, and the board's lock procedure in Section 23 gets a mechanical enforcer.
- **Single source of truth for the contradictions.** Issues #6, #7, #9, #12 are all "different files say different numbers." Move reel length, beat length, card hold, posting times, and loudness into `tokens.py` constants and have the gate, the newsroom skill text, and the schedule generator *all read from there* — ideally generating the documentation lines from the same constants so they can't drift again.
- **Cache TTS by content hash.** Per-sentence synthesis exists; add `assets/tts_cache/{hash}.mp3`. Re-renders, corrections and next-day tweaks skip already-synthesised sentences. Saves time and API quota on every revision.
- **Incremental renders.** Hash each story; `--only changed` re-renders just the affected cards/reels/carousel pages. With 5+ reels per edition, fixing one story shouldn't cost a full re-render on an 8GB machine.
- **Structured, machine-readable gate results.** `review.py` should write `review_report.json` (per-check pass/fail with evidence paths), and `APPROVAL.md` is generated *from* it. Then automation (the ntfy alerts from before) can react to specific failures without parsing prose.
- **Property-based tests for typography.** Add a small hypothesis-style test suite: random long Kannada words, numeral mixing, edge-length headlines, and assert no overflow, no missing glyphs, wrapping intact. Your typo engine is hand-rolled; fuzz it.
- **One log per edition.** `out/{date}/build.log` with structured entries per step. When something fails at 08:00, you're reading a timeline, not scrolling a terminal.

## Experts

**The panels are your quality ceiling — and currently your biggest source of hidden cost. Make them evidence-machines, then make them learn.**

- **Every expert returns a schema, not prose.** Define a small JSON per expert: checklist items, pass/fail, and *evidence* (timestamp, frame path, number). The Chief Editor gate consumes these programmatically — and failures route automatically: sync evidence → step 7, image evidence → step 3, legal → step 2. Today the loop-back is a human remembering who to send it to.
- **Tier the panel by format.** A 12-expert panel for a 45-second footage reel is ceremony. Short-form: 5 experts (Hook & Retention, Brand, Sound, Culture, Chief Editor). Long-form keeps 12. The checklists are written; just subset them per skill.
- **A shared, append-only `docs/LESSONS.md`.** The footage playbook has one; the daily newsroom doesn't. Every time any expert catches a real fault, one line gets appended: date, fault, which check caught it, which step it routed to. Within a month the checklists self-tighten — experts stop passing what later fails.
- **Measure expert precision.** If step 8's retention expert routinely passes reels that later underperform, or the legal expert passes copy the gate then fails, that's a calibration problem, not a story problem. A one-line-per-edition scorecard (`experts.json`) lets you see which expert's bar is set wrong — then you fix the checklist, not the expert count.
- **Add a red-team expert for crime stories.** One prompt whose only job: argue this copy is defamatory or identifies someone it shouldn't. If the red team *can* build the case, the rewrite happens before the contract ever sees it. Your legal checks are word-list based (the book admits they're incomplete) — an adversarial reader is the free patch for that gap.
- **Keep the human seats exactly where they are.** Native-ear voice, culture veto, grievance officer, the person who physically uploads — untouched. The automation goal is that every human step arrives with its evidence already assembled, so a "10/10" judgement takes minutes and is backed by artefacts, not confidence.

**Sequencing if you do all of this:** development lock + CI first (it protects everything else), then expert schemas with auto-routing (biggest daily time save), then motion unification + extended golden test (protects the brand as volume grows). The design gallery and two-cover trick are afternoon projects whenever there's a gap.

Want me to draft the expert JSON schema and the auto-routing table (which failure signature → which step) as a concrete starting point?


Good question — and the encouraging part is that most of the next level for this system is free, because its bottlenecks are trust and attention, not hardware. Here's what I'd do, ordered by leverage, with the constraint that the human gate and the APPROVAL.md principle stay untouched.

## Tier 1 — Free fixes that close the trust gap (do these first)

These directly attack Issue #2 without spending anything.

**1. Fetch full article bodies, not headlines.** The RSS feeds and article pages already contain the facts Gemini needs. Add `trafilatura` (free, pip install, excellent main-content extraction, handles Kannada/UTF-8 perfectly) to pull each article's body before synthesis. `newspaper4k` is a fallback. Check first whether Udayavani's RSS includes full text in `content:encoded` — you may already have the material. This single change converts the pipeline from "invent 5 sentences from a headline" to "condense 5 paragraphs into 3."

**2. Make every sentence prove its source.** Change the Gemini prompt to return JSON where each sentence carries a `source_ref` pointing at the fetched text, and run a **second free Gemini call as auditor**: "Given this source text and this Kannada story, list any sentence not supported by the source." Any unsupported sentence → story downgraded to `unconfirmed` status automatically, or the gate blocks it. This is a mechanical fix for hallucination that costs zero rupees and fits your existing "no override switch" philosophy.

**3. Add a `verified_by` / `verified_at` field to the truth contract.** The editor confirms each story against the source before it enters production; the Chief Editor gate refuses to write `APPROVAL.md` without it. Now human verification is an auditable record, not a memory. Free, one afternoon of work, and it's the single strongest governance upgrade available.

**4. Snapshot every source at publish time.** One `curl` to `web.archive.org/save/<url>`, store the snapshot link in the edition JSON. When someone disputes a story in three months, you have tamper-proof evidence. Free.

**5. Label the synthetic voice.** You label AI images on every frame; do the same for TTS narration in captions (`ಧ್ವನಿ: ಎಐ` or similar) and flip YouTube's synthetic-media disclosure toggle on every bulletin upload. This is now a platform requirement, and it's also brand-consistent — you're the transparent one.

## Tier 2 — Free AI that adds real capability

**6. A free fallback voice: `edge-tts`.** Your `NARRATION_FAILED` guard blocks the whole package when synthesis fails — on a one-person operation that's a day lost. `edge-tts` (pip) gives neural Kannada voices (`kn-IN-SapnaNeural`, `kn-IN-GaganNeural`) for free. Even if you keep your current TTS as primary, wire this in as the automatic fallback so a synthesis outage never blocks publishing. (Caveat: it's an unofficial API; fine as a fallback, and AI4Bharat's Indic-TTS v2 has an offline Kannada voice if you want something fully self-hosted.)

**7. Whisper for Line C — this is your biggest retention win.** Your AI reels already have on-screen text synced to speech. Your *footage* reels don't — and most reels are watched muted. `whisper.cpp` (or `mlx-whisper`) runs fast on your M1 and transcribes Kannada well with large-v3. Auto-generate burned-in Kannada subtitles for footage reels from the real audio. Also: transcription catches name errors — the "Someshwara vs ಸೇನೇಶ್ವರ" failure you documented would have been flagged by comparing transcript against the client's confirmed text.

**8. Close the loop on TTS quality.** Run every synthesized narration back through Whisper, compare the transcript to the script, fail on low similarity. This is an automated "did the voice actually say the words" test — add it to your 112. Free, catches mispronunciations and garbled synthesis before the audience does.

**9. Vision pre-check on images.** You already have a culture-and-legal image check; automate the first pass with Gemini's free tier: "Does this image contain garbled pseudo-text? Deformed faces/hands? Anything disrespectful in a religious context?" AI images are exactly where these failures live, and flagging before human review saves the most scarce resource you have — editor attention.

**10. Auto-provenance for the stock library.** Your truth contract needs credit, licence, and source_url for every photo — so make the library fill them itself:
- **Wikimedia Commons API** and **Openverse API** return licence + author metadata with every image — auto-populate the provenance fields.
- **Pexels API** (free key) for higher-quality modern stock.
- Index the library with **CLIP** (`open-clip`, runs fine on an M1) so the newsroom can search it by meaning ("bridge flood water") instead of filename. This removes the main friction that pushes editors toward generating a new AI image — which your own policy says should be the last resort.

**11. A small local model for the boring tasks.** Your 8GB Mac runs Gemma 3 4B or Qwen 2.5 3B via Ollama comfortably. Don't use it to write news — use it for category classification, hashtag suggestions, and Kannada grammar pre-checks, offline and free, so your Gemini quota and your latency budget go to synthesis and auditing.

## Tier 3 — Automation glue (all free)

**12. Actually deploy the 06:05 job.** This is Issue #19; it's a launchd plist away:

```xml
<key>StartCalendarInterval</key>
<dict><key>Hour</key><integer>6</integer><key>Minute</key><integer>5</integer></dict>
```

launchd fires missed jobs when the Mac wakes; set `pmset repeat wake MTWRFSU 06:00:00` if it sleeps.

**13. Ping a dead-man's switch.** End the fetch script with `curl https://hc-ping.com/<uuid>` (healthchecks.io, free). If the Mac was off, the WiFi failed, or Udayavani blocked you, you get an alert email — instead of discovering a missing edition at noon.

**14. A Telegram bot as the newsroom's phone.** BotFather + 20 lines of Python. Push to the editor's phone: the 06:20 morning brief (today.txt + fetch status), render completion, gate pass/fail, and the finished `MASTER_COPY.md` as a document. The editor reads the day's paper over coffee instead of at the desk. Keep `APPROVAL.md` generation on the Mac — the bot informs, it never approves.

**15. Git + free private GitHub repo.** Your Section 23 change control becomes real: tag v1.0 at lock, decisions change via PR, every rule has a diffable history. For a system whose brand is trustworthiness, a timestamped decision ledger is cheap armor.

**16. Small render optimizations.** Cache TTS audio per sentence (same trick as drawing type once per scene), and auto-generate YouTube chapters from the `project.json` sections you already have.

**17. One backup.** `restic` to Backblaze B2's free 10GB or rclone to a free Drive account. One Mac, nightly-deleted renders, so the backup is tiny. This is the insurance the "Known limits" section doesn't mention.

## Tier 4 — The growth loop (free, and the real "level up")

**18. Replace guessed numbers with measured ones.** Your targets — 28–42s reels, 1.5s hook, 30–45s footage cuts — are currently folklore. Pull **YouTube Analytics API** (free) weekly and IG insights via the Graph API into an auto-generated `retention_report.md`: retention by length, by category, by taluk. Then let the newsroom targets drift toward what coastal Kannada viewers actually watch. This is the difference between a template system and a learning system, and it costs nothing.

**19. YouTube's native thumbnail A/B (Test & Compare)** on every bulletin. Free experiments on your highest-stakes visual.

**20. Publish a "How we use AI" page.** You already label everything — turn that discipline into a public differentiator. A tiny local channel that says "AI drafts, humans verify, here's every label we use" earns trust that big channels can't buy.

## What *not* to do

- **Don't auto-publish.** Meta Business Suite and YouTube scheduling exist and are free, but your manual human upload is the load-bearing wall of the whole trust story. If you ever automate it, trigger it *from* the APPROVAL file, never around it.
- **Don't try a big local LLM for writing.** 8GB can't run a model that writes good formal Kannada journalism. Free tiers of Gemini do this better.
- **Don't add AI video generation for news imagery.** Your motion engine is predictable, on-brand, and cheap; generated video would add risk to the exact line (A) that carries your credibility.
- **Don't automate crime/obituary stories end-to-end**, even after the Tier 1 fixes. Let those always pass through a human fact-confirmation as policy.

## Sequencing

| When | Do |
|---|---|
| This week | #1 trafilatura full-text, #2 source-grounded generation + audit pass, #12 launchd |
| This month | #3 verified_by gate, #5 voice label, #13 healthchecks, #14 Telegram bot, #7 Whisper subtitles for footage reels |
| This quarter | #10 auto-provenance stock library, #16 caches, #18 analytics feedback loop, #15 git ledger, #17 backup, #20 AI transparency page |

The pattern across all of this: your system's rarest resources are editor attention and reader trust, and almost every suggestion either **saves the first** (auto-subtitles, provenance autofill, vision pre-checks, Telegram briefs) or **compounds the second** (grounded generation, verification records, archived evidence, measured targets). Notably, none of it requires spending money — which matters for a channel whose business model is still "1,000 subscribers and 4,000 hours away."

The deepest upgrade available is conceptual, though: right now verification happens at the *gate* (end of the pipeline). Move it to the *intake* — every fact provable at the moment it enters — and the gate becomes a formality instead of a firewall. That's what Tier 1 does, and it's free.



Good framing — those are the three places where this system can compound. The common thread in everything below: the system already treats rules as code, so the next level is **design that defends itself, development that leaves evidence, and experts that get measurably better**. All free, all buildable on the current Mac.

---

## DESIGN — from "rules in code" to pixels that prove themselves

**1. Replace character limits with measured ink width.** This is the single best design upgrade available. "78 characters fits a 4:5 card" is a proxy — Kannada conjuncts (ಕ್ಷ, ತ್ರ, ರ್ವ) vary enormously in rendered width, so 78 chars can be comfortable or catastrophic. You already draw text with Pillow + raqm, which means you can *measure* the advance width of every line before committing it. Change the contract: limits become measured-width budgets; the auto-fit logic shrinks within the type ramp, then wraps, then truncates *deliberately* — never overflows by accident. Same for the 46-char reel line and 34-char hook.

**2. Automated contrast pass behind every text block.** You have scrims (D6) and translucent-text layers (D24). Now enforce them: for each text box, sample the luminance of the composite behind it and require a contrast ratio (≈4.5:1 for body, 3:1 for large type). If it fails, strengthen the scrim automatically or fail the render. Photos are your main variable — this makes them safe by construction, not by taste.

**3. Golden-master visual regression tests.** Your 112 tests cover law, copy, and design *values* — but nothing checks that a token change didn't silently reshape every card. Render one canonical sample per template, store as reference PNGs, and pixel-diff on every change (Pillow's `ImageChops` is enough). Unexpected diff → test fails → human looks. Combined with #1 and #2, "design tests" stop being assertions about numbers and start being assertions about the actual pixels viewers see.

**4. Auto-generated specimen sheet.** One command renders every template with sample content, the full type ramp, rail colours, and safe-zone overlays into a single review sheet. It becomes the board's visual contract at lock (v1.0), the regression baseline for #3, and the fastest way to spot when two templates have drifted apart.

**5. Thumbnail legibility gate.** You already design yt_thumbnail to read at 210 px — so test it: downscale the render to 210 px and ask Gemini's free tier "transcribe the text you can read." If it can't read the hook, no viewer will. Mechanical check for your highest-stakes visual.

**6. Pin the fonts.** Vendor the Noto/Anek files in the repo (they're OFL — free and legal), record their hashes, and add a test. A silent font-suite update changing Kannada metrics is exactly the kind of regression that golden-masters and pinned fonts catch *before* a viewer does.

**7. One shared component library for Lines A, B, and C.** Masthead, lower thirds, credit strips, and outro cards should come from one `brand/` function set — not be re-implemented in each skill playbook. The 14 September reel's "hand-made masthead in the wrong position" is what happens when components are duplicated. One source of truth = footage edits look like the channel by default.

**8. A small editorial-plate family.** The always-a-visual plate (D25/D28) is a great restraint device. Extend it carefully: 2–3 drawn variants (weather, civic, general) from the same coastal geometry — never AI-generated — so even a photo-less story feels art-directed. Resist adding more than that; the plate's power is its uniformity.

*(Motion-wise: I'd add nothing. The engine already honours reading time, eased motion, and speech-synced cuts. The only addition worth considering is a photosensitivity check — no rapid full-frame flashes — which is one rule and one test.)*

---

## DEVELOPMENT — from "it works" to "it leaves evidence"

**1. Edition state file + resumable pipeline.** Make the 13 steps an explicit DAG with a `state.json` per edition: each step's status, timestamps, warnings, error codes. When step 9 fails, you resume at 9 instead of re-running the morning. End with an auto-generated `run_report.md` — what was fetched from where, what failed, what was warned, how long each render took. That report *is* your audit trail, and it feeds the expert system below.

**2. Schema versioning before the lock.** Add `schema_version` to story and edition JSON *now*, while v1.0 is still being decided. Six months from now, when the truth contract gains a `verified_by` field, you'll be able to migrate old editions instead of breaking on them.

**3. A model registry per edition.** Record in the edition JSON: Gemini model name, TTS engine + voice, Real-ESRGAN weights, Whisper model, font hashes. Five lines of code, and it buys you reproducibility, honest disclosure ("which AI made this?"), and a way to correlate quality changes with model changes. Pairs naturally with your decision-ledger ethos.

**4. An adversarial legal corpus.** Your blocklists are floors — so attack them on purpose. Build a regression set of near-miss Kannada headlines: guilt verbs with markers in the wrong place, variant spellings, conjunct forms, markers in the deck but not the headline. Each must fail. This turns "the legal check works" from a hope into a tested claim, and every real-world near-miss you encounter gets appended. (Add `hypothesis` fuzzing on `Story.validate()` while you're there — the validator should survive any garbage without crashing and without silently accepting it.)

**5. Decision–test traceability, auto-generated.** You have D1–D54 and 112 tests. Generate a matrix: every decision number mapped to the test(s) that enforce it. Any D-number with no test lights up red. Apply the same pattern to the skills' `LESSONS.md`: lesson → checklist line → automated test. This is the cheapest possible way to make sure "we learned it" actually means "the system now enforces it."

**6. Error-code taxonomy.** Every check emits a code (`LAW-03`, `TYPE-11`, `SOUND-02`) referenced in `DECISIONS.md`, shown in the run report and `APPROVAL.md`. Board discussions become precise; logs become searchable.

**7. Key separation and environment pinning.** Two things from the board issues become trivial engineering: separate API keys per role (fetch vs. voice — resolves #3 cleanly), and a full rebuild kit — `Brewfile`, `requirements.txt`, vendored fonts, a README that promises "this repo rebuilds the newsroom on a fresh Mac in one afternoon." On a one-Mac, one-editor operation, that document is key-person insurance.

**8. Idempotent render cache.** Hash the story JSON + assets; skip any render whose inputs are unchanged. On the 8 GB M1 this is the difference between "re-render the whole edition" and "re-render the two cards I edited."

*(Plus the ops basics already covered: launchd for 06:05, healthchecks ping, git tag at v1.0.)*

---

## EXPERTS — from AI personas with checklists to a calibrated editorial bench

**1. Structured verdicts from every expert.** The footage panel already scores with evidence — generalize it. Every expert (Kannada, legal, culture, voice, retention, social…) returns JSON: `{verdict, score, issues: [{severity: BLOCK|FIX|SUGGEST, evidence, estimate}]}`. Two things fall out: the human editor gets a *triaged queue with time estimates* instead of prose to read, and scores become trend data — you can see whether quality is drifting over weeks.

**2. Add the chair that's missing: Fact-Check Lead.** The biggest structural gap in the expert bench is that no expert's job is "prove every sentence against the source." Make the grounded-generation auditor from my earlier Tier 1 into a *named expert* with its own checklist, failure codes, and tests — not just a script buried in the fetch pipeline. Its BLOCK verdicts carry the same authority as the legal gate. Also consider a **Numbers Editor** (stats verified against official sources — numbers travel the farthest and are checked the least) and a **Community Editor** (first-24h comments are a hyperlocal channel's tip line and corrections intake). But resist panel bloat: merge overlapping checklists first; each expert costs real latency.

**3. A calibration bench.** You have perfect training data sitting in your own history: the Ganapathi film rated 50%, the seven fixes after the 14 September reel, every correction since. Freeze them as scored cases. Whenever you change an expert's prompt or checklist, re-run the bench — did verdicts get better or just different? Add a light "blind re-review": once per edition, two experts score one sampled card independently; disagreements expose ambiguous checklist items. This is how the bench *improves* instead of just existing.

**4. Every expert declares its limits.** The Chief Editor already states limits honestly — make it universal: each expert's verdict includes `could_not_check: [...]` (e.g., "cannot verify whether this rain figure matches IMD data"). It's the same ethos as "if the source material is the limit, say so" — and it tells the human exactly where their attention is non-optional.

**5. One-page role sheets.** For each chair: what it owns, what it may block on, its checklist, its escalation path. This is what lets a second human (a relief editor, a volunteer) step into the loop without a week of handover — direct insurance against the key-person risk.

**6. Give the Voice chair a lexicon.** TTS systems mangle local proper nouns — Byndoor, taluk names, deity names. Maintain a pronunciation-override lexicon for the synth engine, and pair it with the Whisper round-trip check ("did the voice actually say the words?") as the Voice expert's automated test.

**7. Scheduled expertise, not just embedded expertise.** Two calendars: a quarterly **law-update review** (IT Rules, BNS amendments — D49 already cites the 2021 amendments; the law will move again) and a pre-festival **culture pre-clearance** (greetings themes, imagery for upcoming observances). And optionally: one retired teacher/farmer/doctor as a volunteer reviewer for education/farm/health categories — free human expertise that no LLM panel replicates, and the kind of community involvement that makes a channel *of* its town rather than *about* it.

---

## Where to start

| Horizon | Design | Development | Experts |
|---|---|---|---|
| This week | #1 measured-width limits | #1 state.json + run report | #1 structured verdicts |
| This month | #2 contrast pass, #3 golden-masters | #4 legal corpus, #5 traceability matrix | #2 Fact-Check Lead, #4 limits declaration |
| This quarter | #4 specimen sheet, #6 fonts, #7 shared components | #2 schema versioning, #3 model registry, #8 cache | #3 calibration bench, #5 role sheets, #7 calendars |

The unifying principle across all three columns is the same one the system already believes in: **anything important should be enforced, measured, or evidenced — never remembered.** Design enforces itself through measured pixels; development enforces itself through tests and reports; experts enforce themselves through structured verdicts and calibration. None of it changes the architecture you've built — it hardens it, and it all runs on the machine you already own.


