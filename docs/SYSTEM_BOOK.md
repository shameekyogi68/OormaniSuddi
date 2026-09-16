# ಊರ್ಮನಿ ಸುದ್ದಿ — System Book

**How the Oormani Suddi newsroom machine works**

> ನಮ್ಮ ಊರು • ನಮ್ಮ ಧ್ವನಿ · `@oormanisuddi` · ಕರಾವಳಿ — coastal Karnataka
>
> **Prepared:** 15 September 2026 · **Status:** Locked on D55–D58 (16 September 2026). Code is the source of truth; this book is the map.
> **Written from:** the project's source code and rule files as they stand today

This document explains the whole system: every format it makes, how each one is designed and built, the words written around it, the checks that stop mistakes before publishing, who is responsible for what, and the decisions that locked v1.0.

**Lock (D55):** No source, no claim. No human verification, no edition. No `APPROVAL.md`, no upload. YouTube gets tape. Generated pictures say they are generated.

| At a glance | |
|---|---|
| Production lines | 3 main (news from written copy, long YouTube videos from footage, reels from footage) + 2 occasional (festival greetings, YouTube Live overlay) |
| Design templates | 11 |
| Daily newsroom | 4 human stops (Desk, Picture, Package, Gate) around code gates |
| Footage sign-off | `APPROVAL_FOOTAGE.md` via `brand/review.py` |
| Automated tests (law, copy, design) | 120+ |
| Written decisions explaining each rule | D1–D58 |

---

## Contents

1. [Summary for the board](#1-summary-for-the-board)
2. [A day, start to finish](#2-a-day-start-to-finish)
3. [Gathering the news](#3-gathering-the-news)
4. [The truth contract](#4-the-truth-contract-what-every-story-must-declare)
5. [Every format we make](#5-every-format-we-make)
6. [AI news reel (9:16)](#6-ai-news-reel-916-narrated)
7. [YouTube bulletin (16:9)](#7-youtube-bulletin-169)
8. [Long YouTube video from footage](#8-long-youtube-video-from-real-footage)
9. [Reel / Short from footage](#9-instagram-reel--youtube-short-from-real-footage)
10. [Festival greetings](#10-festival-greetings)
11. [YouTube Live overlay](#11-youtube-live-overlay)
12. [The design system](#12-the-design-system)
13. [Captions, descriptions, hashtags](#13-captions-descriptions-hashtags-and-first-comments)
14. [Publishing schedule](#14-publishing-schedule)
15. [Voice, music and sound](#15-voice-music-and-sound)
16. [Image policy and stock library](#16-image-policy-and-the-stock-library)
17. [The 13-step AI newsroom](#17-the-13-step-ai-newsroom-second-brain)
18. [Checks and approval](#18-checks-and-approval)
19. [Platform strategy](#19-platform-strategy)
20. [Who is responsible for what](#20-who-is-responsible-for-what)
21. [Known limits](#21-known-limits)
22. [Decisions needed to lock the system](#22-decisions-needed-to-lock-the-system)
23. [Sign-off and lock procedure](#23-sign-off-and-lock-procedure)
24. [Reference: files, commands, terms](#24-reference-files-commands-and-terms)

---

## 1. Summary for the board

Oormani Suddi is a Kannada local news channel for coastal Karnataka, run from one Mac by a very small team. The system turns news into finished, branded, legally checked posts and videos, and writes every caption, description, hashtag set and posting time that goes with them. **It never posts anything by itself.** A person uploads each item, following a schedule the system writes.

### The production lines

| Line | What goes in | What comes out | How automated |
|---|---|---|---|
| **A · Daily news package** | News text as a JSON file | Instagram posts, swipeable carousel, Story card, front-page image, narrated vertical reels, 16:9 YouTube bulletin and thumbnail, all copy, and the schedule | Fully automated. Images are stock or AI-generated; the voice is text-to-speech. |
| **B · Long YouTube video** | Phone clips of an event (e.g. Seneshwara temple Ganapathi, Byndoor) | 3–5 minute branded film: AI sharpening, colour grade, cleaned real sound with licensed instrumental music, chapters, and the YouTube package | Tool-assisted. Client brief → preview → 1440p master. |
| **C · Instagram Reel / YouTube Short** | The same clips | 30–45 s vertical video: hook in 1.5 s, reel masthead, organiser credits, captions inside safe zones, caption and Shorts copy | Tool-assisted, built from the reel posted on 14 September. |
| **D · Festival greetings** | Occasion, wish, blessing, photo | Centred gold-foil posters in 9:16, 4:5 and 1:1 plus caption | Automated. A separate design genre from news. |
| **E · YouTube Live overlay** | The team's `LIVE BG.png` | Branded bottom band with room for up to 4 partner logos | Automated. |

### What makes it trustworthy

- **The law is enforced in code, not left to memory.** A crime headline that states guilt before a conviction cannot be rendered. Children and sexual-offence victims cannot be identified. Every picture must say where it came from, whether it shows the real scene, and what licence allows its use.
- **"Breaking" and "Live" cannot be claimed.** Breaking is calculated from the publish time and expires after 12 hours. Live needs a real stream link.
- **AI images are labelled on every frame that shows them**, and in the caption.
- **A final machine gate writes `APPROVAL.md`** only when every mechanical check passes. No file, no publishing.

### What the board is asked to do

Section 22 lists **20 points where the rule files disagree with each other or with the code**, plus policy questions only the owners can answer (for example, whether AI-made reels may go on YouTube, and who the named grievance officer is). Each has a recommendation.

Once the board decides:
1. The decisions are written into the rules, code and tests.
2. Everything is saved as version 1.0.
3. Later changes go through the change-control procedure in Section 23.

---

## 2. A day, start to finish

This is the daily news line (line A) as designed. Times are IST.

1. **06:05 · News fetch.** `scripts/fetch_daily_news.py` collects Udupi-district headlines from four sources and writes Kannada news paragraphs to `inbox/today.txt`.
2. **Editor starts production.** The editor pastes or confirms the news and types **start with content**. This activates the 13-step newsroom.
3. **Copy, legal checks, reel choice.** The Kannada expert, sub-editor and legal checks shape each story into the JSON contract. Only 10/10 stories become reels.
4. **Images.** Stock library first; a new AI image only if nothing fits; otherwise the brand's editorial plate. A culture and legal check inspects every image.
5. **Validate.** `render.py --check` runs the truth contract and preflight without drawing anything.
6. **Render.** `render.py` draws the requested formats, synthesises the voice, and writes captions and the schedule.
7. **Review and approve.** Voice, retention, social, schedule, legal and final-QA steps run. Then the Chief Editor code gate writes `APPROVAL.md` if everything is clean.
8. **Master copy.** `MASTER_COPY.md` puts every caption, first comment, title, description, tag list and time on one page.
9. **People post.** A person uploads each file at its scheduled time and pastes the first comment immediately.
10. **Close the day.** The editor types **stop**. Evergreen images go to the stock library, the day's renders and temporary images are deleted, and the edition JSON is kept as the record.

Lines B and C (footage edits) run whenever clips arrive. Each follows its own playbook in `.claude/skills/` (Sections 8 and 9).

---

## 3. Gathering the news

### The automatic fetch (`scripts/fetch_daily_news.py`)

The morning news intake begins with an automated scraping and editorial synthesis engine located in `scripts/fetch_daily_news.py`. Designed to execute unattended daily at **06:05 AM IST**, the pipeline harvests raw coastal Karnataka reports across all seven taluks of Udupi district, deduplicates coverage across multiple publications, synthesises the stories into pure formal Kannada using Google Gemini, validates the text against linguistic rules, and deposits the output into `inbox/today.txt` for the morning editorial desk.

```bash
python3 scripts/fetch_daily_news.py   # manual or cron execution (06:05 IST)
```

```
[4 Redundant News Sources]
  ├── Udayavani Web (HTML scraper: h2/h3 tags)
  ├── Udayavani District RSS (XML / CDATA parser)
  ├── Google News Regional RSS (English, 24h taluk query)
  └── OneIndia Kannada RSS (Keyword-filtered coastal feed)
            │
            ▼ (HTTP timeout 10s, modern desktop User-Agent, isolated try/except)
[Graceful Ingestion: min. 3 unique headlines required]
            │
            ▼
[Cryptographic Deduplication: MD5 on first 60 normalised chars]
            │
            ▼
[Gemini 3.6 Flash Synthesis: 3-attempt exponential backoff (4s, 8s)]
  ├── Byndoor & Kundapura prioritized first
  ├── Pure formal Kannada (ಶುದ್ಧ ಕನ್ನಡ), Latin numerals (25, 100)
  └── 4–7 rich journalistic paragraphs (who, what, where, when, why, how)
            │
            ▼
[Automated Quality Gate]
  ├── Story count audit (>= 3 paragraphs)
  ├── English word detection (flags loanwords >= 4 chars)
  └── Kannada numeral check (rejects ೦-೯)
            │
       ┌────┴────────────────────────┐
       ▼                             ▼
[PASS] inbox/today.txt        [FAIL] inbox/.fetch_failed
(ready for editorial desk)    (records timestamp & failure reason)
```

---

### The 4 redundant scraping engines

Because local news portals frequently experience downtime, malformed feeds, or CMS changes, the pipeline never depends on a single endpoint. Four independent scraping engines gather headlines in parallel; any source can fail, timeout, or return empty results without halting the remaining engines.

| Engine | Target URL / Feed | Method & Extraction Logic | Filters & Limits |
|---|---|---|---|
| **1. Udayavani Web HTML** | `https://www.udayavani.com/district-news/udupi-news` | Direct HTTP GET using a desktop User-Agent header (`Macintosh; Intel Mac OS X 10_15_7`). Scrapes `<h2>` and `<h3>` tags via regex (`<h[23][^>]*>(.*?)</h[23]>`). | Strips inner HTML tags; discards boilerplate items (e.g. `ಇನ್ನಷ್ಟು`); rejects snippets shorter than 15 characters; caps at top **12 headlines**. |
| **2. Udayavani RSS Feed** | `https://www.udayavani.com/rss/udupi-district-news` | XML stream retrieval with dual-layer parsing: standard XML tree plus lenient CDATA regex fallback (`<title><!\[CDATA\[(.*?)\]\]></title>`) to survive malformed XML entities. | Discards channel-level feed title; filters for headline text > 15 characters; caps at top **10 headlines**. |
| **3. Google News Regional (EN)** | `news.google.com/rss/search?q=Udupi+OR+Kundapura+OR+Byndoor+OR+Brahmavar+OR+Karkala+OR+Kaup+OR+Hebri+when:1d&hl=en-IN&gl=IN&ceid=IN:en` | Standard RSS XML item parsing across all seven Udupi taluks within the last 24 hours (`when:1d`). | Strips trailing publisher attribution suffixes (e.g. ` - Deccan Herald`, ` - The Hindu`); captures institutional, administrative, and police alerts reported in English media; caps at top **15 headlines**. |
| **4. OneIndia Kannada RSS** | `https://kannada.oneindia.com/rss/kannada-news-fb.xml` | XML feed parser paired with a regional keyword whitelist covering coastal place names in both Kannada and English. | **Keyword whitelist:** `ಉಡುಪಿ, ಕುಂದಾಪುರ, ಬೈಂದೂರು, ಬ್ರಹ್ಮಾವರ, ಕಾರ್ಕಳ, ಕಾಪು, ಹೆಬ್ರಿ, ಮಣಿಪಾಲ, ಶಿರ್ವ, ಕರಾವಳಿ, ಮಂಗಳೂರು, ದಕ್ಷಿಣ ಕನ್ನಡ, ಉತ್ತರ ಕನ್ನಡ, ಮಲ್ಪೆ, ಪಿತ್ರೋಡಿ` (plus English equivalents). Retains top **8 Udupi-specific items** and up to **5 general Karnataka items** for state policy alerts. |

---

### Network hardening and resilience

1. **Strict HTTP Timeouts (`HTTP_TIMEOUT = 10s`)**: Every network call is guarded by a 10-second socket timeout so that slow or unresponsive servers never hang the unattended morning process.
2. **Realistic User-Agent**: Requests mimic a modern desktop browser (`Mozilla/5.0 ... AppleWebKit/537.36`) to avoid anti-bot blocks and 403 Forbidden responses.
3. **Fail-Safe Isolation**: Each scraping function catches all exceptions (`try/except Exception`), logs the skipped source and error class, and returns an empty list. The run continues unabated.
4. **Minimum Source Quota (`MIN_SOURCES = 3`)**: If the combined harvest yields fewer than 3 unique headlines across all sources (e.g. complete internet outage or regional blocking), the script logs an error, writes a failure marker to `inbox/.fetch_failed`, and exits with code 1 instead of prompting Gemini with empty context.

---

### Cryptographic deduplication

News stories are frequently syndicated across multiple portals or reported in both Kannada and English. The deduplication stage (`deduplicate()`) normalises and fingerprints every incoming headline:

- **Normalisation**: Converts all text to lowercase, removes punctuation (`[^\w\s]`), and collapses multiple spaces into a single space.
- **Fingerprinting**: Takes the first 60 characters of the normalised string and computes an MD5 checksum:
  ```python
  key = hashlib.md5(norm[:60].encode()).hexdigest()
  ```
- **Result**: Identical reports with slightly different trailing headlines or punctuation are merged, preserving only distinct regional stories before synthesis.

---

### AI editorial synthesis (`synthesize_with_retry`)

The deduplicated headline digest is passed to Google Gemini (`gemini-3.6-flash`) via the `google.genai` SDK using an authoritative editorial prompt (`EDITORIAL_PROMPT`).

#### Editorial guidelines enforced in prompt
- **Journalistic Identity**: Written from the persona of a senior investigative local journalist and news desk editor with 10+ years of coastal Karnataka experience at *ಊರ್ಮನಿ ಸುದ್ದಿ*.
- **The 5 Ws and 1 H**: Every item must capture the essential journalistic anchors: ಯಾರು (Who), ಏನು (What), ಎಲ್ಲಿ (Where), ಯಾವಾಗ (When), ಏಕೆ (Why), and ಹೇಗೆ (How).
- **Substantive Coverage**: 3–5 rich, informative sentences per story detailing administrative directives, police findings, official contact/procedure details, or civic impact.
- **Geographic Hierarchy**: Stories from Byndoor (ಬೈಂದೂರು) and Kundapura (ಕುಂದಾಪುರ) must be placed first in the broadcast hierarchy, followed by broader taluks (Brahmavara, Udupi, Karkala, Kaup, Hebri).
- **Linguistic Purity**: Pure formal Kannada (ಶುದ್ಧ ಕನ್ನಡ). Zero English loanwords, transliterations, or code-mixed terms. Latin numerals mandatory (`25`, `100`); Kannada numerals (`೨೫`) prohibited.
- **Zero Meta-Commentary**: The output starts immediately with the news on the very first word. No greetings, no English datelines, no category headers (e.g. `ಸ್ಥಳೀಯ ಸುದ್ದಿ`), and no sign-offs.
- **Zero Hallucination Clause**: Paraphrases verified facts; excludes rumors and unverified social media speculation. If no authentic news meets the threshold: `ಇಂದು ಯಾವುದೇ ಹೊಸ ಸುದ್ದಿ ಇಲ್ಲ.`

#### Retry mechanism and backoff
To guard against transient API throttling or network blips:
- **3 Attempt Quota (`MAX_RETRIES = 3`)**: The synthesizer retries up to 3 times.
- **Exponential Backoff (`BACKOFF_BASE = 4s`)**: Waits 4 seconds before the second attempt and 8 seconds before the third (`wait = BACKOFF_BASE * (2 ** (attempt - 1))`).
- If all 3 attempts fail, the error is recorded in `inbox/.fetch_failed`.

---

### Post-synthesis quality gate (`quality_check`)

Before writing to the disk, the script audits the generated text against brand rules:
1. **Story Count**: Verifies that at least 3–4 stories were produced (warns if `< 3`).
2. **English Word Audit**: Scans for English words with 4 or more letters (`\b[a-zA-Z]{4,}\b`), whitelisting standard web protocols (`http`, `https`, `www`, `com`, `html`).
3. **Numeral Verification**: Checks for accidental Kannada numeral glyphs (`[೦-೯]`).

Warnings are logged to stdout for editor review but do not block the pipeline so that morning production can proceed.

---

### File I/O and downstream newsroom handshake

- **Output File (`inbox/today.txt`)**: On a successful run, the validated Kannada paragraphs are written to `inbox/today.txt`, and a terminal preview of the first 3 stories is printed.
- **Failure Marker (`inbox/.fetch_failed`)**: If any critical step fails (missing API key, under minimum headline threshold, or API exhaustion), the script writes the ISO timestamp and error reason to `inbox/.fetch_failed`.
- **Downstream Alerting**: When the editor opens the daily newsroom and runs `start with content`, the automated workflow checks `inbox/`:
  - If `today.txt` exists and `.fetch_failed` is absent, the editor reviews and confirms the drafted copy.
  - If `.fetch_failed` exists, the newsroom flags the failure immediately, allowing the editor to inspect the log or paste raw copy manually.
- **Run Reset**: Each new execution of `fetch_daily_news.py` automatically deletes any stale `.fetch_failed` marker.

> ⚠️ **Board policy issues concerning the fetch script:**
> - **Issue #2 (Invented Detail):** The scraper sends only headlines to Gemini but requests 3–5 detailed sentences. The board must decide whether to fetch full article bodies or treat fetched text strictly as tips for editor confirmation (see Section 22, #2).
> - **Issue #3 (Gemini Key Usage):** AGENTS rule 2 states the Gemini key is reserved for voice synthesis, yet `fetch_daily_news.py` uses it for news drafting. The board must formally approve dual-use or issue a dedicated key (see Section 22, #3).
> - **Issue #19 (Unattended Cron/launchd):** The script is built for 06:05 AM execution, but currently runs only on manual invocation. A system `launchd` plist or cron job must be deployed to make morning harvesting fully autonomous (see Section 22, #19).

---

### Other ways news enters the newsroom

- **Pasted Copy**: The editor pastes raw reports, press notes, or police releases into the chat before typing *start with content*. The newsroom extracts facts and verifies sources.
- **Video Footage**: Camera or mobile phone clips arrive in an event directory (e.g. `Ganapathi Video/` or `assets/footage/`) for Lines B and C.
- **Archival Staging**: `inbox/processed_YYYY-MM-DD.txt` stores the raw intake that was used for any completed edition.

---

## 4. The truth contract: what every story must declare

Every item passes through `brand/content.py`. It is the single door into the system: a story is plain JSON, and misspelt or unknown fields are rejected loudly rather than ignored.

`Story.validate()` runs before anything is drawn. **There is deliberately no override switch.** A rule that can be waived on a deadline would be waived on a deadline (decision D29).

### Story fields

| Field | Meaning and rule |
|---|---|
| `headline` | Required. Kannada. About 78 characters fits a 4:5 card; longer text is set smaller. |
| `sources` | Required, at least one. Own reporting must say so: `ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ`. |
| `category` | One of 11 (Section 12). Sets the rail colour and the Kannada kicker. |
| `status` | Printed on the card. confirmed `ದೃಢಪಟ್ಟ ವರದಿ` · developing `ಬೆಳವಣಿಗೆಯಲ್ಲಿದೆ` · unconfirmed `ಪರಿಶೀಲನೆಯಲ್ಲಿದೆ` · official `ಅಧಿಕೃತ ಪ್ರಕಟಣೆ` |
| `published_at` | Time with IST offset. Drives the dateline and the 12-hour breaking window. |
| `deck` | One or two sentences under the headline, up to ~180 characters. |
| `points` | Supporting facts. Cards carry three comfortably. |
| `takeaway` | What the reader should do (helpline, deadline). On weather, health, civic and breaking stories it outranks the facts when space is short. |
| `location`, `dateline`, `reporter` | Place in Kannada (readers look for it first), bureau line, reporter. |
| `photo`, `gallery` | Main picture and extra pictures, each with full provenance. Reels need one gallery photo per fact. |
| `reel_line` | Short video headline, about 45 characters (max 46). |
| `reel_points` | Short on-screen forms of each fact, ~60 characters. The voice still reads the full fact. |
| `hook` | Thumbnail line, about 7 words / 34 characters maximum. |
| `narration_script` | Optional editor-written script, read word for word; the picture still follows its sentences. |
| `is_reel` | Whether this story earns its own reel. |
| `quote`, `numbers` | `[text, attribution]` for a quote card; `[value, label]` pairs for a statistics card. |
| `live_url` | A real stream URL. The only thing that earns a `ನೇರ ಪ್ರಸಾರ` badge. |
| `correction` | If this card corrects an earlier one, what changed. |
| `involves_minor`, `sexual_offence`, `convicted` | Legal flags (see below). |
| `template` | Force a specific design; otherwise the system chooses. |

An **edition** is one day's package. It has a `date`, an `edition_no` (the previous number plus one; 15 September was No. 117), a `strapline` (default `ಕರಾವಳಿ ಬುಲೆಟಿನ್`) and the stories. One object drives the carousel, reels, bulletin and front page, so they cannot disagree.

### Picture provenance

Every photograph must declare a **credit**, a **licence** and its **nature**. The rules that follow from those:
- A licence other than `own` also needs a `source_url`.
- A picture of the actual scene needs a caption.
- A picture more than 2 days older than the story must be marked as a file photo.

| Nature | Label printed on the card |
|---|---|
| actual | none needed; caption required |
| file | `ಸಂಗ್ರಹ ಚಿತ್ರ` |
| representative | `ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ` |
| handout | `ಹಂಚಿಕೆ ಚಿತ್ರ` |
| graphic | `ಗ್ರಾಫಿಕ್ಸ್` |
| ai | `ಎಐ ರಚಿತ ಚಿತ್ರ` |

| Licence | Meaning |
|---|---|
| own | The channel shot or made it |
| licensed | Rights obtained |
| cc | Creative Commons |
| public-domain | No rights restrictions |
| handout | Official release |
| fair-dealing | Reporting defence. Allowed with a warning, because it is a defence, not a permission. |

The disclosure travels **with each image**, not with the story. Any card showing a picture prints its label, caption and `ಕೃಪೆ:` credit (D49, following the 2021 IT Rules amendments on synthetic content).

### Criminal-reporting law, enforced

| Law | What the system refuses |
|---|---|
| **BNS §356** (defamation), plus contempt once a case is in court | On crime or breaking stories with no conviction: a guilt verb (`ಕೊಂದ, ಕದ್ದ, ವಂಚಿಸಿದ, ಹಲ್ಲೆ ಮಾಡಿದ`…) without an allegation marker (`ಆರೋಪ, ಆರೋಪಿ, ಶಂಕಿತ, ಎನ್ನಲಾಗಿದೆ, ಪ್ರಕರಣ ದಾಖಲು, ದೂರು ದಾಖಲು, ತನಿಖೆ`). **The headline and the reel line are checked on their own**, because each is seen alone in a thumbnail or forward. A marker in the deck does not protect the headline. |
| **Juvenile Justice Act 2015 §74** | When a child is involved: no actual-scene photo, and no name with an age like "(15)" in the headline, deck or facts. |
| **POCSO 2012 §23, BNS §72** | For sexual offences: no actual or handout photo; no village, street, colony, school or college as location (district or taluk only); no names with ages. |
| Order of checks | Legal checks run *before* an old breaking story is moved back to normal styling, so a story's age never weakens them. |

Preflight adds warnings:
- A reminder to set the minor and sexual-offence flags on every crime story.
- A flag when crime copy mentions children but the minor flag is not set.
- A warning on graphic words that can limit YouTube ads (`ರಕ್ತಸಿಕ್ತ, ಬರ್ಬರ ಹತ್ಯೆ`…).

---

## 5. Every format we make

Eleven templates live in `templates/`, one file each, and none depends on another. `templates/__init__.py` records for each one what it takes, its size, when to use it and its limits.

| Template | Size | File(s) | Platform | When to use | Limits |
|---|---|---|---|---|---|
| **report_card** | 1080×1350 | `post_NN.jpg` | Instagram feed | Default for almost everything. With a photo it leads on the picture; without one it draws the editorial plate. | headline 78, deck 190, 3 facts of 150 |
| **text_card** | 1080×1350 | post | Instagram feed | Only when a pure type poster is wanted | headline 78, deck 190, 3 facts |
| **quote_card** | 1080×1080 | post | Instagram | When the story is someone's words; photo flattened to two tones | quote 240 |
| **stat_card** | 1080×1080 | post | Instagram | When the story is a number: rainfall, budget, turnout | headline 70, 3 numbers |
| **story_card** | 1080×1920 | `story_9x16.jpg` | IG Story, WhatsApp status | One per edition (usually the lead), or a single urgent alert | headline 78 |
| **youtube_thumb** | 1280×720 | `yt_thumbnail.jpg` | YouTube | One per long video; built to read at 210 px wide | hook 34 chars, 7 words |
| **carousel** | 1080×1080 | `carousel_01_cover.jpg` … `_sources.jpg` | Instagram | One per edition: cover, one slide per story, sources/follow slide, progress bar | 6 stories (up to 8 slides) |
| **broadsheet** | 1080×1620 | `broadsheet.jpg` | WhatsApp, Telegram | The day as one front page: lead + up to 4 in two columns | 5 stories |
| **reel** | 1080×1920 | `reel_NN.mp4` + cover | Instagram Reels | One per reel-worthy story, narrated (Section 6) | reel line 46; 8–45 s |
| **bulletin** | 1920×1080 | `bulletin.mp4` | YouTube long-form | Whole edition as a 60–120 s video (Section 7) | 8 stories |
| **greeting** | 1080×1920 + 4:5 + 1:1 | `wish_9x16.jpg`, `wish_4x5.jpg`, `wish_1x1.jpg` | All | Festival wishes only, never news (Section 10) | occasion 30, wish 26, blessing 96 |

**Automatic choice** when no template is named:
- A story with a quote → quote card.
- Numbers and no photo → statistics card.
- Everything else → report card.

**Targeted delivery.** Only the formats the editor asks for are rendered, e.g. `--only carousel reel`.

**Footage formats** are made outside the templates by the two editing tools: long YouTube films at 2560×1440 (Section 8) and reels/Shorts at 1080×1920 (Section 9).

### How the still posts are composed

- **Report card.** Full-bleed photograph fading into an editorial stack: masthead, category rail and kicker, headline, deck, facts, takeaway, disclosure strip, sources, footer. When everything cannot fit, it drops content in editorial order: takeaway, then deck, then facts from the bottom. On weather, health, civic and breaking stories the takeaway is kept instead.
- **Text card.** Headline high, detail anchored at the foot, horizon glow between. The headline is set larger than on the report card.
- **Quote card.** One voice on a two-tone photo bed, so the picture supports the words.
- **Statistics card.** Large numerals with Kannada labels.
- **Story card.** Built from the bottom up inside a 72/250/72/340 px safe inset. The band below carries the handle rather than dead black.
- **Thumbnail.** An ink column with the type on the left, the photo full height on the right, and a gold seam between. It uses the same frame language as the bulletin, so the thumbnail and the video's first frame look like one publication.
- **Carousel.** Segmented progress bar. A slide with no photo becomes a statement card, not a half-empty one.
- **Broadsheet.** Column cells grow with their content.

---

## 6. AI news reel (9:16, narrated)

Made by `templates/reel.py` on the engine in `brand/motion.py`, with the voice from `brand/voice.py`. There is one reel per story marked `is_reel`. Under AGENTS rule 7 these are published to **Instagram Reels only**.

### Structure: one card per spoken sentence

| Card | On screen | Spoken |
|---|---|---|
| lead | Masthead, category badge, `reel_line` on frame 0 over the hero photo | Opening word plus headline, e.g. `ನಮಸ್ಕಾರ, ಕರಾವಳಿ ಸುದ್ದಿ.` (`ನಮಸ್ಕಾರ, ಪ್ರಮುಖ ಸುದ್ದಿ.` for accidents, deaths, police stories) |
| fact0–fact2 | Short fact (`reel_points`) over its own gallery photo, with that photo's disclosure | The full fact, linked with `ಇನ್ನು, / ಇದೇ ವೇಳೆ, / ಸ್ಥಳೀಯ ವರದಿಗಳ ಪ್ರಕಾರ,` (max 3 facts) |
| advisory | Takeaway with a drawn badge | `ಸಾರ್ವಜನಿಕರ ಗಮನಕ್ಕೆ:` + takeaway |
| signoff / outro | Logo, brand and follow line over a veiled photo (~2.4 s) | `ಕ್ಷಣ ಕ್ಷಣದ ನಿಖರ ಕರಾವಳಿ ಸುದ್ದಿಗಳಿಗಾಗಿ ಊರ್ಮನಿ ಸುದ್ದಿ ಫಾಲೋ ಮಾಡಿ — ಇದು ನಮ್ಮ ಊರು, ನಮ್ಮ ಧ್ವನಿ.` |

### How it is built

- **Cut from the speech (D45).** Each sentence is synthesised and measured separately, and every cut lands in the pause between sentences, so the card on screen is always the sentence being heard. `audit_sync` checks the finished file. Before this, a fact card appeared 15 seconds before its sentence was spoken.
- **Reading time is honoured (D26).** Viewers read Kannada at about 7 characters per second on moving video. If the voice finishes before a card can be read, the card holds in silence rather than cutting early. Cards run 5–12 s.
- **Opens on the news (D39).** There is no logo sting at the start; the masthead brands every scene.
- **Nothing appears abruptly (D16).** Text rises on eased curves with a small stagger. Photos move with slow, eased Ken Burns zooms. Scene changes are wipes with a gold edge (D48).
- **Fact type at news size (D47).** 46–74 px, and the end card holds a picture, not black.
- **No missing letters (D46).** Any character the fonts cannot draw is substituted or reported before rendering. Badges use drawn marks, not symbol characters.
- **Safe zones (D18).** Critical content stays inside 72 px left, 230 top, 220 right and 480 bottom, clear of Instagram's buttons and caption.
- **Sound.** Music ducks once, cleanly, under the voice. Broadcast hits come from `sfx/`. The master is −14 LUFS and −1.5 dBTP (D17).
- **Cover.** `reel_NN_cover.jpg` is written from the opening frame (D33). Set it as the cover on upload.
- **Silent-reel guard.** If voice synthesis fails, the render completes silently and leaves `reel_NN.NARRATION_FAILED`. The Chief Editor gate then blocks the package.
- **Speed.** Type is drawn once per scene at 2× and reused on every frame; only the photo moves. A reel renders in minutes.

### Targets set by the newsroom

The newsroom sets these targets:
- Length 28–42 seconds.
- Hook within 1.5 seconds.
- At most three facts.
- One distinct photo per fact.

What the gate does:
- **Fails** a reel with fewer gallery photos than facts.
- **Warns** above 48 s and above 60 s.
- **Fails** above 90 s or below 8 s.

*These numbers disagree with the newsroom text in places; see issues #6 and #7.*

---

## 7. YouTube bulletin (16:9)

`templates/bulletin.py` uses the same engine as the reel, laid out as a broadcast lower-third (D34, D36, D38) and paced for someone who chose to watch.

- **Carries more.** Each scene shows the print headline and the deck (up to 6 lines), not the short reel line (D37).
- **Length follows the copy.** A scene may hold up to 30 s. Real four-story editions come out at 84–97 s with no padding. The floor is 60 s, because YouTube treats shorter video as a Short and Shorts cannot use a custom thumbnail (D32).
- **A length target drops stories; it never speeds scenes up** (D44).
- **Layout.** Progress bar flush to the top edge (D35). Up to 8 stories. Safe margins 96/72/96/84 px.
- **4K.** The same design is supported at 3840×2160 by drawing at twice the size, not on a bigger canvas (D40).
- **Thumbnail.** `yt_thumbnail.jpg` is made for this video.
- **Purpose.** Long-form watch hours count towards YouTube monetisation (1,000 subscribers + 4,000 hours); Shorts do not.

> ⚠️ The bulletin is AI imagery with a synthetic voice. AGENTS rule 7 says YouTube uploads must be real footage, yet the generated schedule still puts `bulletin.mp4` on YouTube at 08:30. This is **issue #1**.

---

## 8. Long YouTube video from real footage

- **Playbook:** `.claude/skills/youtube-longform-edit/SKILL.md`, with `LESSONS.md`.
- **Tools:** in its `tools/` folder.
- **First job:** the Seneshwara temple Ganapathi film (Byndoor, 14 September 2026). The client rated it about 50% of expectations, and its lessons are written into the playbook.

### The client's non-negotiables

1. **Real on-location sound stays.** Firecrackers, bells, chants, crowd and speech are cleaned and kept audible.
2. **Music is royalty-free and instrumental only.** No vocals, bhajan lyrics or dialogue. The licence is recorded.
3. **Brand masthead at the top for the whole runtime**, exactly as on reels. Logo, wordmark and gold tagline sit top-left; date and weekday top-right, on a soft dark veil. No corner watermark.
4. **Clips in file-number order** unless told otherwise.
5. **Names exactly as the client wrote them.** `ಸೇನೇಶ್ವರ` was once filed as "Someshwara". Unconfirmed text stays off screen.
6. **Premium means professional to a viewer**, not just good numbers.
7. **Nothing is done until checked**, with an evidence-based Chief Editor sign-off.
8. **Live progress** with an honest, measured time remaining.

### Process

| Step | What happens | Time on the M1, 8 GB |
|---|---|---|
| A · Intake | `intake.py` makes a contact sheet per clip; every sheet is looked at | 5–10 min |
| B · One brief | One batch of up to 4 questions: original files (WhatsApp copies are 848×464), length and style, exact names and ceremony stages, music with licence and download permission | 1 message |
| C · Edit list | `project.json`: segments, sections, cold open, cards, music | 10–15 min |
| D · Cards check | `make_cards.py --preview`: title, lower thirds and masthead as PNG | 2 min |
| E · Preview | `build.py --preview --detach`, watched by `monitor.py`: a 1080p cut for the client | 15–30 min |
| F · Master | AI upscale + 1440p master, detached, auto-restart after a crash | ~1 s per frame + 20 min |
| G · QC and sign-off | `qc_report.md`, QC frame sheet, 12-expert panel, then the YouTube package | 10 min |

### Creative standards

- **Structure:**
  - Cold open (3–6 s) on the most striking moment, with its sound.
  - Brand intro (4–5 s).
  - Three acts matching the real stages: arrival or procession, main ritual, people and blessings.
  - Hero finale held 8–12 s.
  - Outro (6–7 s): thanks, subscribe, handle.
- **Pacing:** action shots 3–6 s, ritual and deity 7–12 s, rarely over 15 s. Vary wide, medium and close. The usual result is 3–5 min from ~15 min of raw footage.
- **Transitions:**
  - Near-hard cut (0.1 s) within a section.
  - 0.5 s dissolve for a jump inside one clip.
  - 0.8 s dissolve between sections.
  - Dip to black around cards.
  - No spins, glitches or flashy wipes on devotional content.
- **Graphics:** lower thirds only for confirmed names, never over the deity's face. Chapters only from confirmed section labels (YouTube needs at least 3 chapters, each at least 10 s). Kannada is set with Pillow + raqm so letters join correctly.
- **Respect** (the culture expert can veto): the deity is shown steady and held. No comic effects, no speeded-up rituals, no cutting away at the peak of an aarti, no child's face as thumbnail or hero frame.

### Picture

- **AI resolution enhancement:** Real-ESRGAN general-x4v3 on the Mac's GPU. It upscales 4× with an adjustable denoise/detail blend (default 0.5), then resizes to delivery size.
- **Colour:** handled explicitly as BT.709 with correct range tags. Graded for consistent shot-to-shot colour, natural skin, unclipped whites and no neon greens.
- **Master:** 2560×1440, H.264 High, CRF 15, BT.709 tags, fast-start, AAC 320 kb/s. Also delivered: a 1080p preview, a chapters file and a before/after crop image.

### Sound mix

| Stage | Setting |
|---|---|
| Real sound, per shot | De-clip → high-pass 90 Hz → low-pass 15 kHz → noise reduction → gentle 2.5:1 compression |
| Level match | Each shot to −18 LUFS, gain capped at +10 dB |
| Placement | Each shot placed at its exact timeline position (continuous timestamps) |
| Real-sound bus | 3:1 compression at −24 dB |
| Music | Starts on a phrase at a chosen offset. Separate levels for cards/story/ritual (shipped 0.80 / 0.62 / 0.55). 1 s fade-in, 3 s fade-out. Optional ducking under loud real sound. |
| Master | Limiter, then two-pass linear loudness normalisation to −14 LUFS, −1 dBTP, without pumping |

**Music policy**
- **First choice:** the proven instrumental track in `assets/bgm_options/ganapathi/` (licence recorded in the example project).
- **Otherwise:** Pixabay Music under the Pixabay Content License. Avoid anything titled bhajan, song or aarti.
- **Proof it is instrumental:** the client listens to it under the preview.
- **Downloads:** every one needs the client's yes, stating file name, source, size and licence.
- **Content ID:** temple loudspeakers playing film songs can trigger it, so those stretches are kept short or lowered.

### The 12-expert panel

Each expert owns a checklist. The Chief Editor scores every dimension out of 10 with evidence (numbers, timestamps, the sheet). Anything below 9 is fixed. If the source material is the limit, that is stated plainly instead.

| Expert | Pass bar |
|---|---|
| Story Producer | The story can be stated in one line; cold open chosen; every clip viewed |
| Editor | No dragging shot; no repeated angle back to back; hero moments held |
| Colourist | Same-location shots match; natural skin; no clipping or banding |
| Restoration Engineer | Visible gain over plain scaling at 100%; no waxy faces or halos |
| Sound Engineer | −14 LUFS ±1, true peak ≤ −1 dBTP, no clicks, chants intelligible |
| Music Supervisor | Licence recorded, no vocals, starts on a phrase, ends resolved |
| Motion & Brand Designer | Cards follow the design standard; masthead for the full runtime |
| Kannada Language & Culture | Spelling matches the client's text; dignity of the ritual |
| YouTube Growth | Hook in the first 5 s; valid chapters; description ends with the engagement question |
| Legal & Monetisation | Music licence on file; no loudspeaker copyright audio; no child close-up in the thumbnail |
| Technical QC | `qc_report.md` all pass; sheet inspected; file plays start to end |
| Chief Editor | Scores with evidence; limits stated honestly |

### Delivery and YouTube package

- **Title:** Kannada first, then an English keyword tail, ~70 characters visible. Example: `ಬೈಂದೂರು ಸೇನೇಶ್ವರ ದೇವಸ್ಥಾನ ಗಣಪತಿ ಪ್ರತಿಷ್ಠಾಪನೆ | Byndoor Ganesha 2026`.
- **Thumbnail:** hero frame from the master, at most 4 Kannada words, the logo, and never a child's face as the focus.
- **Description:** in order:
  1. A 2-line hook.
  2. Place, date and event.
  3. Chapters.
  4. Music credit.
  5. 3–5 hashtags.
  6. Last line exactly: `ನಿಮ್ಮ ಅಭಿಪ್ರಾಯ ಏನು? ಕಮೆಂಟ್ ಮಾಡಿ.`
- **Settings:** News & Politics or People & Blogs; Made for Kids: No; chapters on; a pinned comment asking which moment viewers liked.
- **Running the Mac:**
  - One heavy job at a time.
  - Renders run detached so they survive the chat closing.
  - Closing Chrome roughly doubles speed.
  - A status table is updated at every stage change.
  - `_work/` is deleted only after asking.

---

## 9. Instagram Reel / YouTube Short from real footage

- **Playbook:** `.claude/skills/reels-shorts-edit/SKILL.md`.
- **Tool:** `tools/reel_build.py`, which reuses the long-format engine.
- **Built from:** the Ganapathi reel posted on 14 September 2026 at 22:21 (44.7 s).
- **Platforms:** because it is real footage, one file serves both Instagram Reels and YouTube Shorts.
- **Rendering:** the checking commands (`--check`, `--dry-run`, `--overlays`) never write video. A video is rendered only when the client asks for one.

### Short-form rules

1. **Hook in the first 1.5 s**, with sound, cut hard. The model is the 1.3 s firecracker burst.
2. **15–60 s**, aiming for 30–45 s. The tool warns above 60 s and refuses above 90 s.
3. **Reel masthead at the top**, drawn by the same code as the AI reels, and off during the outro card.
4. **Everything readable sits inside Instagram's safe zones** (72 / 230 / 220 / 480 px).
5. **Captions and credits only with wording the client confirmed.**
6. **Music ducks under real sound**: threshold 0.15, ratio 6, attack 5 ms, release 180 ms.
7. **Loudness −13 LUFS.** True peak −1.5 dBTP before AAC encoding; QC fails the file if it is above −1.0 after encoding.

### Cut

- **Shape:**
  1. Hook (≤1.5 s).
  2. Build of 2–4 s shots with rising energy.
  3. Hero moments of 5–6 s, with a slow 1.0→1.055 push-in on 2–4 shots.
  4. A calm 2–3 s breather.
  5. A warm human closer.
  6. A 2.2 s outro card.
- **Shots:** 1.2–4 s in the build, nothing over 7 s, about 10–14 shots for 45 s. Snap cuts (0.12 s) by default; no dissolves between crowds.
- **Framing:** portrait clips are centre-cropped with adjustable focus. Landscape clips are cropped or placed on a blurred copy of themselves. The tool warns when a crop keeps less than 40% of the frame.
- **Text:**
  - 3–4 short captions (1.5–2.5 s), centred, at most 856 px wide, never over the deity.
  - Organiser credit in gold and white, above the bottom safe zone.
  - Outro: logo, `ಊರ್ಮನಿ ಸುದ್ದಿ` in gold, and "Follow @oormanisuddi" in the brand font.
- **Optional loop:** end on motion that matches the hook, so replays feel continuous.

### Technical specification

| | |
|---|---|
| Canvas | 1080×1920, 30 fps, BT.709 |
| Upscale | AI (Real-ESRGAN) by default; plain grade for previews |
| Grade | Contrast 1.10, saturation 1.18, gamma 0.97, warm balance |
| Encode | H.264 High, CRF 17, max 25 Mb/s, 2 s keyframes, AAC 256 kb/s, fast-start |
| Output | `<slug>_1080x1920.mp4` and `<slug>_copy.txt`; QC sheet with safe-zone guides |
| Cover | Chosen from the QC sheet, subject inside the centre 1080×1350 (profile-grid crop) |

**Copy file**
- **Instagram caption:** headline, engagement question, 📍 place, 🕐 date and time, status, credit, source, corrections contact, hashtags.
- **First comment.**
- **Shorts title** under 60 characters.
- **Shorts description** ending with `ನಿಮ್ಮ ಅಭಿಪ್ರಾಯ ಏನು? ಕಮೆಂಟ್ ಮಾಡಿ.` and `#Shorts`.

**Panel:** the same as long-format, with two changes. A Hook & Retention Editor replaces the Story Producer and Editor. An Instagram & Shorts Growth Expert checks length (30–45 s), cover, first comment and title.

**Fixed after the 14 September reel:**
- True peak was −0.2 dBFS.
- Credits sat under Instagram's caption area.
- The outro line was set in Helvetica.
- 464-pixel-wide WhatsApp footage got no AI upscale.
- A hand-made masthead was in the wrong position.
- Chaining clips left audio gaps.
- The build script lived in a temporary folder.

---

## 10. Festival greetings

`templates/greeting.py`, with ornaments from `brand/ornament.py`. Decision D54: a wish set in news grammar reads like a report about a festival. The first Gauri-Ganesha poster was rejected for exactly that.

- **Symmetry.** The poster is centred: the eye enters at the salutation, passes through the image, and lands on the festival's name.
- **The name is the hero.** It is set in the serif typeface in gold foil, never flat yellow.
- **The deity is never covered.** A photo must declare `keep_clear`, the vertical band that holds the deity. The layout:
  1. Moves the picture so no text enters that band.
  2. If it cannot, frames the picture in a temple arch.
  3. If that also fails, refuses to render.
- **Signed, not mastheaded.** `ಶುಭ ಕೋರುವವರು` above the brand; no dateline, category or "special" label.
- **Disclosed.** An AI image is labelled on the poster and in the caption.
- **Fields:** salutation (34), occasion (30), wish (26), blessing (~60, max 96), theme, photo, sign label, date, tags, slug. The themes are sacred, lights, harvest, rajyotsava, national and serene. A theme changes only the ground and light; gold stays the accent.
- **Output:** `out/greetings/<slug>/` with 9:16, 4:5 and 1:1 posters and `wish_copy.txt`. Example input: `editions/greetings/2026-09-14_ganesh_chaturthi.json`.

---

## 11. YouTube Live overlay

`scripts/live_overlay.py` reads the team's `LIVE BG.png`: 1920×1080, transparent above, a maroon band below. **It measures the band's height and colour from that file on every run**, so if the team moves the band, the overlay follows. The picture area is forced fully transparent and checked.

- **Band content:**
  - **Left:** ringed logo, brand name and tagline.
  - **Centre:** `ಕ್ಷಣ ಕ್ಷಣದ ಕರಾವಳಿ ಸುದ್ದಿಗಾಗಿ` and `ಸಬ್‌ಸ್ಕ್ರೈಬ್ ಮಾಡಿ, ಬೆಲ್ ಒತ್ತಿ` with a drawn bell.
  - **Right:** the handle, or up to 4 partner logos on white tiles under `ಸಹಯೋಗ`.
- **Made for phones.** Few words, set large, because 1920 px plays about 400 px wide.
- **"LIVE" is not baked in**, because the recording stays after the stream ends. An optional separate badge is provided.
- **Output:** `out/live/live_bg.png`, `live_bug.png` (corner logo), `live_badge.png`, `live_preview.jpg`.

---

## 12. The design system

All values live in `brand/tokens.py`. The written standard is `STANDARDS.md`, and the reason behind each rule is in `docs/DECISIONS.md`. No template contains its own colour, font size or margin. The palette was sampled from the channel logo.

### Colour

| Token | Hex | Role |
|---|---|---|
| ink 950 | `#03050A` | Ground and type |
| gold 500 | `#F5B301` | **The only accent** (the sunset disc in the logo) |
| red | `#C81E1E` | Alerts only (the logo's speed strokes) |
| paper | `#F7F5F1` | Warm white, never pure white |

**Category colours appear only on the thin rail (D9):**

| Category | Kannada | Rail |
|---|---|---|
| breaking | ಬ್ರೇಕಿಂಗ್ | red |
| crime | ಅಪರಾಧ ವರದಿ | deep red |
| weather | ಹವಾಮಾನ | amber |
| civic | ಆಡಳಿತ | sea blue |
| health | ಆರೋಗ್ಯ | teal |
| education | ಶಿಕ್ಷಣ | indigo |
| culture | ಸಂಸ್ಕೃತಿ | dark gold |
| sport | ಕ್ರೀಡೆ | moss |
| farm | ಕೃಷಿ | moss |
| obituary | ನಿಧನ ವಾರ್ತೆ | plum |
| explainer | ವಿಶ್ಲೇಷಣೆ | light sea |

### Rules

- **Type:**
  - Noto Sans Kannada Bold for headlines.
  - Anek Kannada for body text.
  - Noto Serif Kannada for quotes and greetings.
  - SF for Latin text; Latin faces fall back to Kannada automatically (D4).
- **Kannada craft:**
  - Text is drawn on baselines (D2).
  - Line spacing comes from the em (D1).
  - No letter-spacing on Kannada (D3).
  - Translucent text gets its own layer (D24).
  - 19 px minimum size.
- **Numerals:** Latin only, never mixed with Kannada numerals on one card (D20).
- **Restraint:** hairlines not borders, square corners, no frame around the canvas (D10); brand rules are gilded (D29).
- **Photographs:**
  - Gentle house grade with a filmic highlight roll-off (D30).
  - Default focal point (0.5, 0.42) (D7).
  - Photos fade their own edges and are never painted over (D5).
  - Smooth scrim (D6).
- **Always a visual (D25):** no photo means the editorial plate, a designed coastal scene with a ruled sea and sun (D28, D31).
- **Finish:**
  - Film grain is mandatory (D8).
  - Everything is drawn at 2× and downsampled once (D21).
  - JPEG quality 95, with full colour detail (4:4:4).
- **Layout:** content flows and is never positioned by hand (D11). Gaps between items are clearly larger than gaps between lines (D12).

### Safe zones by format

| Format | Size | Safe inset (L, T, R, B) | Why |
|---|---|---|---|
| Post / forward | 1080×1350 | 72, 72, 72, 72 | Tallest crop the IG feed allows |
| Square / carousel | 1080×1080 | 72, 72, 72, 72 | Carousel, X |
| Story | 1080×1920 | 72, 250, 72, 340 | Top bar ~230 px, reply bar ~320 px |
| Reel | 1080×1920 | 72, 230, 220, 480 | Action buttons right, caption block bottom |
| Thumbnail | 1280×720 | 48, 40, 48, 96 | Duration chip hides bottom-right |
| Broadsheet | 1080×1620 | 64, 56, 64, 56 | Print-style margins |
| Bulletin | 1920×1080 | 96, 72, 96, 84 | Typographic margin only |

**Brand constants**
- **Name:** `ಊರ್ಮನಿ ಸುದ್ದಿ`
- **Tagline:** `ನಮ್ಮ ಊರು • ನಮ್ಮ ಧ್ವನಿ`
- **Handle:** `@oormanisuddi`. The gate checks its exact casing in every copy file.
- **Coverage:** `ಕರಾವಳಿ`
- **Logo:** `assets/logo.png` is the master; the circle and card cut-outs are made from it.

---

## 13. Captions, descriptions, hashtags and first comments

`brand/copy.py` writes all the words around the artwork from the story's own fields; nothing is pre-written for a particular story. It exists because copy drives discovery: Instagram search reads caption text, and YouTube ranks largely on title and description (D31).

### Instagram caption, in this order

1. **Hook line.** The thumbnail hook, else the reel line, else the headline. The place name is added in front if missing, and the line must fit in the first **125 characters** (the part shown before "more").
2. **Deck**, if it is not already in the hook.
3. **Facts** as `▪` bullets.
4. **⚠️ Takeaway.**
5. **`ತಿದ್ದುಪಡಿ:` correction**, if any.
6. **Call to action by category:**
   - Crime: `ಈ ಸುದ್ದಿ ಊರಿಗೆ ತಲುಪಲಿ — ಶೇರ್ ಮಾಡಿ.`
   - Weather: `ನಿಮ್ಮ ಊರಿನ ಪರಿಸ್ಥಿತಿ ಹೇಗಿದೆ? ಕಾಮೆಂಟ್ ಮಾಡಿ.`
   - Obituary: `ಮತ್ತಷ್ಟು ಕರಾವಳಿ ಸುದ್ದಿಗೆ ಫಾಲೋ ಮಾಡಿ.`
   - All others: `ನಿಮಗೆ ಏನನ್ನಿಸುತ್ತೆ? ಕಾಮೆಂಟ್ ಮಾಡಿ · ಊರಿಗೆ ತಲುಪಲಿ ಎಂದು ಶೇರ್ ಮಾಡಿ.`
7. **Facts block:** 📍 place, 🕐 date and time, `ಸ್ಥಿತಿ:` status, picture disclosure with `ಕೃಪೆ:` credit, `📌 ಮೂಲ:` sources.
8. **Corrections contact:** `ತಿದ್ದುಪಡಿ ಅಥವಾ ಮಾಹಿತಿಗೆ ಸಂಪರ್ಕಿಸಿ: Instagram DM @oormanisuddi · ಬಯೋದಲ್ಲಿರುವ WhatsApp ಸಂಖ್ಯೆ`
9. **Hashtags.**

The limit is 2,200 characters. If it runs over, facts are dropped from the bottom; **sourcing is never trimmed**. Emoji are kept to four structural markers so the caption reads like a newsroom, not a personal account.

### First comment (paste immediately after posting)

- **Weather:** "Is it like this in [place] now? Reply." The place takes the correct Kannada case ending, e.g. `ಉಡುಪಿಯಲ್ಲಿ ಈಗ ಹೇಗಿದೆ? ರಿಪ್ಲೈ ಮಾಡಿ.`
- **Crime:** `[place] — ಮೂಲ: ಸತ್ಯಾಧಾರಿತ ವರದಿ. ಇನ್ನಷ್ಟು ಕರಾವಳಿ ಸುದ್ದಿಗೆ ಫಾಲೋ ಮಾಡಿ.`
- **Others:** "Are you from [place]?", e.g. `ನೀವು ಉಡುಪಿಯವರಾ? ರಿಪ್ಲೈ ಮಾಡಿ — @oormanisuddi`
- **Grammar guard (D42):** Kannada case endings attach to the word (`ಉಡುಪಿಯಲ್ಲಿ`, not "ಉಡುಪಿ ನಲ್ಲಿ"). If a place name cannot be analysed safely, a phrasing that needs no ending is used instead of a guess.

### Hashtags

The default is 8 tags (platform maximum 30), with duplicates removed. They are ordered from most specific to least:

1. **Place:** the Kannada place, its English name, and English name + News (e.g. `ಬೈಂದೂರು` `Byndoor` `ByndoorNews`). 22 coastal places are mapped.
2. **Category:** e.g. weather → `ಹವಾಮಾನ` `WeatherAlert` `KarnatakaRains`.
3. **Core, always:** `oormanisuddi` `ಕರಾವಳಿ` `ಕರಾವಳಿಸುದ್ದಿ` `KaravaliNews`.
4. **Wide, only if room:** `CoastalKarnataka` `ಕನ್ನಡಸುದ್ದಿ` `KannadaNews` `Karnataka`. Huge tags put a new channel in a pool it cannot win.

### YouTube

- **Title:**
  - Built from the hook, reel line or headline, with the place in front.
  - Bulletin titles add the date and `ಕರಾವಳಿ ಬುಲೆಟಿನ್`.
  - Hard limit 100 characters; about 60 are displayed.
  - **No #Shorts is added**, because YouTube classifies Shorts by shape and length.
- **Description**, in order:
  1. Opens on the story (the first two lines are the search snippet).
  2. Brand and tagline.
  3. `ಕರಾವಳಿ ಬುಲೆಟಿನ್` with the date.
  4. Each story numbered, with its deck, up to 3 facts, place, status, sources and picture note.
  5. Corrections contact.
  6. Follow and subscribe lines.
  7. `💬 ನಿಮ್ಮ ಅಭಿಪ್ರಾಯ ಏನು? ಕಮೆಂಟ್ ಮಾಡಿ!`
  8. Hashtags (YouTube shows the first three above the title).

  Limit 5,000 characters.
- **Tags:** up to 20, collected from each story's hashtags.

### Other copy

- **Carousel caption**, in order:
  1. The lead story's hook (never the date first).
  2. `ಸ್ವೈಪ್ ಮಾಡಿ — ಇಂದಿನ N ಸುದ್ದಿ.`
  3. All headlines.
  4. Call to action.
  5. Combined sources.
  6. Corrections contact.
  7. Hashtags.
- **Alt text:** describes the card for screen readers: brand, category, headline, and what the picture shows (or that it is a brand graphic).
- **WhatsApp forward:** bold headline, deck, • facts, takeaway, place and time, sources, brand and handle. No hashtags, and no symbols that older phones show as boxes.
- **X post:** place and line with the handle, within 280 characters.
- **Files written:** `post_NN_copy.txt/.json`, `carousel_copy.*`, `reel_NN_copy.*`, `bulletin_copy.*`. These contain Instagram and YouTube copy only. WhatsApp and X text is generated but not written to them (issue #17).
- **`MASTER_COPY.md`**, made by the social media expert from its template, contains:
  - The schedule table.
  - Carousel caption, first comment and alt text.
  - For each reel: IG caption, first comment, Shorts title, YouTube description, tags, WhatsApp and X text.
  - Bulletin title, description and tags.
  - A file listing.

---

## 14. Publishing schedule

`render.py` writes `schedule.txt` and `schedule.json` from the files it actually rendered (D43), so the plan never lists a file that does not exist. The times are starting positions for coastal Karnataka; move them to what the channel's own analytics show after a month.

| IST | Platform | File | Why |
|---|---|---|---|
| 08:30 | YouTube | `bulletin.mp4` + `yt_thumbnail.jpg` | First, so it has the whole day to gather watch time |
| 09:00 | Instagram | Carousel, all slides | Morning scroll; carousels get a second impression |
| 09:15 | IG Story / WhatsApp | `story_9x16.jpg` | Points to the carousel already up |
| 11:30 · 14:30 · 17:30 · 20:30 | Reels (see issue #1) | `reel_NN.mp4` + cover + first comment | At least 2.5 h apart so our reels don't compete; a 5th reel steps 2.5 h later (up to 23:45) |
| 20:00 | WhatsApp / Telegram | `broadsheet.jpg` | Day's front page, forwarded once the day is complete |

Footage edits (lines B and C) are posted when ready and are not in this generated plan.

---

## 15. Voice, music and sound

### Voiceover (AI news reels)

- **Engine.** The default is Google's Kannada voice at 1.15× tempo.
  - Microsoft's neural Sapna voice was tried and rejected by the owner's native ear. It remains one setting away (`OORMANI_TTS_ENGINE=edge`).
  - Gemini TTS is also available.
  - **On voice, the native listener decides.**
- **Per-sentence synthesis.** Each beat is its own clip, measured and joined with designed pauses, so cuts land between sentences.
- **Written Kannada becomes spoken Kannada (D50):**
  - "40%" is read `ಶೇಕಡಾ 40`.
  - "₹1.10 ಲಕ್ಷ" becomes whole amounts, with `ರೂಪಾಯಿ` spoken after the number.
  - Dots in initials like "ಕೆ. ಜೆ." are removed.
  - Abbreviations and units are expanded.
  - Ranges are read as ranges.
  - Clock times take correct case endings.

  Each of these once caused an audible fault.
- **Hazard check.** The gate fails narration that still contains any of these:
  - A decimal inside a figure.
  - Dotted initials.
  - ₹.
  - A % sign.
  - A digital clock time.
  - A beat over 150 characters.

  It also warns about pauses in the audio longer than a designed gap.

### Music and effects

| Asset | Use | Licence status |
|---|---|---|
| `assets/news_bgm.mp3` | Default bed for AI reels and bulletins | Described as in-house royalty-free; **no source record** in the project |
| `assets/bgm_options/01–10_*.mp3` | Breaking-news stingers and themes | **No licence notes; treat as unverified** (issue #16) |
| `bgm_options/ganapathi/journey_to_the_golden_temple_tokyorifft.mp3` | Proven instrumental for devotional edits | Recorded in the example project |
| `bgm_options/ganapathi/ganpati_bappa_morya_kontraa.mp3` | Rejected: contains dialogue | Do not use |
| `sfx/` (9 files) | Broadcast hits and whooshes | Described as open or owned |
| `render.py --bgm` | Custom track for one render | Editor's responsibility |

### Loudness targets

| Format | Loudness | True peak |
|---|---|---|
| AI reel and bulletin | −14 LUFS | −1.5 dBTP |
| Long YouTube from footage | −14 LUFS ±1 | −1 dBTP |
| Reel / Short from footage | −13 LUFS | −1.5 before AAC, ≤ −1.0 after |

---

## 16. Image policy and the stock library

Order of preference in the daily newsroom (AGENTS rule 2 and Step 3):

1. **Reuse the stock library** in `assets/stock/`. Each image is documented in `CATALOG.md` with a ready-made photo entry. Reuse it with nature `representative`, licence `own`, credit `AI ಚಿತ್ರ — ಊರ್ಮನಿ ಸುದ್ದಿ`, and an honest caption.
2. **Generate a new AI image** only when nothing in stock fits. It uses nature `ai` and must be shown in the chat for the editor to see.
3. **No image:** the template draws the editorial plate.
4. **Never** scrape low-quality web photos. **Never** use the Gemini key to make images.

**Culture and legal image check (Step 4):**
- No distortion or mockery of Yakshagana, Hulivesha, Daivaradhane or temple ritual.
- No children's faces, victim trauma or gore.
- Images are regenerated until they pass.

**Stock library today (17 images):**
- **Civic and law:** stray dogs on a street, court complex, police CCTV room, police dog squad, taluk revenue office, highway traffic patrol.
- **Places and daily life:** fishing harbour, NH66 traffic, vented dam, weekly farmers' market, leopard trap cage.
- **Culture and festivals:** Badagutittu Yakshagana, Shiva linga darshana, Ganesh Chaturthi altar, Ganeshotsava idol, Gauri-Ganesha altar, Ganahoma ritual.

**End of day:** *stop* copies truly generic new images into stock, updates the catalogue, and deletes `assets/daily/{date}/` and `out/{date}/`.

---

## 17. The 13-step AI newsroom ("second brain")

Defined in `.agents/skills/second-brain/SKILL.md` and triggered by `.agents/rules/second-brain-triggers.md`. An AI assistant plays each expert in turn, following written checklists.

**It never changes the design engine, the templates or `render.py`.** If a check fails, the input is fixed, not the renderer.

- **Start words:** start with content, start, begin, content ready, let's go, produce, start production, begin production.
- **Stop words:** stop, close, done, cleanup, clear, delete content, clean up, finish.

| Step | Expert | Responsibility | Output / gate |
|---|---|---|---|
| 1 | Kannada Language Expert `ಕನ್ನಡ ಭಾಷಾ ತಜ್ಞ` | Natural, grammatical Kannada; Latin numerals; headline < 78, reel line < 46; short reel points | Clean copy |
| 2 | Sub-Editor & Reel Gatekeeper `ಸಂಪಾದಕ` | Real sources (ask if unknown); accurate status; allegation markers on headline and reel line; legal flags; realistic publish time; no invented facts; respectful obituaries; picks only 10/10 stories for reels (drama, public stakes, shareability) | `is_reel` per story |
| 3 | Photojournalism Expert `ಛಾಯಾಗ್ರಾಹಕ` | Stock first, then AI, else plate; one gallery photo per reel fact; provenance fields | `assets/daily/{date}/` |
| 4 | Visual Culture, Ethics & Legal Image Checker | Cultural dignity; no minors, trauma or gore; 10/10 before layout | Approved images |
| 5 | Design QA `ವಿನ್ಯಾಸಕ` | Save `editions/{date}.json`; run `render.py --check`; fix all failures | Clean preflight |
| 6 | Content Manager `ವಿಷಯ ವ್ಯವಸ್ಥಾಪಕ` | Render only what was asked (`--only …`) | `out/{date}/` |
| 7 | Broadcast Voiceover & Anchor QA | Pronunciation, pace, speech-to-card sync, no silent reels | Voice approved |
| 8 | Audience Retention & Algorithm Expert | Hook in 1.5 s, 28–42 s, no frozen visuals, clean ducking, legible text, engagement question | 10/10, or loop back to steps 1, 3 or 7 |
| 9 | Social Media Expert | Captions, first comments, Shorts titles, descriptions, tags | `MASTER_COPY.md` |
| 10 | Scheduling & Analytics Expert | Validate and present `schedule.txt` | Schedule in master copy |
| 11 | Legal, Copyright & Monetisation Guard | Ad-safe imagery and wording; music/SFX licences; IT Rules, POCSO, victim privacy | Zero legal or ad risk |
| 12 | Final QA / Loop Controller `ಗುಣಮಟ್ಟ ನಿಯಂತ್ರಕ` | Every file present and correct; loops earlier steps until all pass | All green |
| 13 | Chief Editor & Manager `ಮುಖ್ಯ ಸಂಪಾದಕ` | (a) Run the code gate, never just claim it; (b) review extracted frames and copy with a consumer's eye; (c) loop until green | `APPROVAL.md` |

**Daily folders:** `editions/{date}.json` is kept permanently. `assets/daily/{date}/` and `out/{date}/` are deleted on *stop*. A separate short skill, `.claude/skills/publish-edition`, covers publishing an edition.

**What the newsroom must not do:**
- Invent facts, sources, quotes or credits.
- Suppress provenance labels.
- Override `Story.validate()`.
- Mark a story "breaking" by hand.
- Hard-code design values.

---

## 18. Checks and approval

Checks are layered, from "cannot be drawn" to "cannot be approved". **Only the machine checks are guaranteed.** The expert scores in Sections 8, 9 and 17 are judgements, made by an AI assistant or a person against written checklists.

| Layer | Where | Effect | What it checks |
|---|---|---|---|
| Truth contract | `content.py` | **Blocks** | Sources, provenance, licence, legal guards, live link, unknown fields |
| Preflight | `qa.py preflight()` | **Fails** / warns | **Fails:** headline far over budget, mixed numerals, images with no disclosure, characters no font can draw. **Warns:** long deck or facts, too many facts, aged breaking, fair-dealing, crime-flag reminder, AI imagery, long facts without reel points, no reel line, unconfirmed status, no location, uncaptioned actual photo, ad-unsafe words, child words in crime copy |
| Channel compliance | `qa.py compliance()` | Warns | A published contact route exists (IT Rules 2021 Part III) |
| Output inspection | `qa.py inspect()` | **Fails** / warns | **Fails:** wrong pixel size. **Warns:** file size over 8 MB (thumbnails 2 MB, forwards 5 MB), crushed blacks over 55%, clipped whites over 6%, nothing brighter than mid-grey |
| Sync audit | `motion.py audit_sync` | Checks | Cuts land in the speech gaps |
| Chief Editor gate | `review.py review()` | **Blocks** | Handle spelling in every copy file; every file named in master copy or schedule exists; each reel readable, has audio, 8–90 s, has cover, no narration-failure marker; crime lines carry allegation markers; AI imagery disclosed in reel caption; no missing glyphs; gallery photos ≥ reel facts; narration hazards. **Warnings:** over 48 or 60 s, over 300 MB, uncaptioned carousel stories, long pauses, posts under 90 min apart |
| Evidence | `review.py evidence()` | — | Every carousel slide, every cover, and 8 evenly spaced frames from every reel, saved to `_review/` |
| Approval | `review.py approve()` | **Green signal** | Writes `APPROVAL.md` only when nothing fails, listing checks and non-blocking notes; deletes an old approval if the package now fails |
| Footage QC | editing tools, `qc` stage | **Fails** | Duration, loudness, true peak on the final file, codec and colour tags, frame sheet with safe-zone guides |

### Tests and automatic safeguards on the code

- **112 tests** across three files:
  - `tests/test_contract.py`: provenance, breaking/live, JSON handling, preflight, licensing, criminal reporting, copy and grammar, schedule, bulletin pacing, speech-locked reels, glyphs, disclosure, spoken Kannada, Chief Editor gate, TTS hazards, greetings.
  - `test_greeting.py`: the deity is never covered.
  - `test_golden.py`: the approved design (next bullet).
- **Golden test.** Renders a fixed test edition with a frozen clock and compares image fingerprints with the approved design.
  - A failure means the design changed; inspect `out/_blessed/` before approving the new version.
  - It also checks that rendering twice gives identical bytes.
- **Editor hooks** in `.claude/settings.json`:
  - Editing the golden fingerprints is refused.
  - Contract tests run automatically after any change to `brand/` or `templates/`.
  - The registry, schemas and `TEMPLATES.md` are regenerated so they cannot drift.
- **Reproducibility.** The clock can be frozen with `OORMANI_NOW` (D22). Random effects never use unstable seeds (D28).

---

## 19. Platform strategy

> **AGENTS rule 7, set from September 2026 analytics:** on YouTube, AI text-to-speech slideshow reels averaged **37 views** (the latest got 1–4), while real footage averaged **397**. That is a tenfold gap.

- **YouTube:**
  - Uploads must contain real camera footage, a real human voice, or a face-to-camera read.
  - AI graphics may be used for thumbnails, lower thirds and overlays on real footage, never as the whole video.
  - Every description ends with `ನಿಮ್ಮ ಅಭಿಪ್ರಾಯ ಏನು? ಕಮೆಂಟ್ ಮಾಡಿ.`
- **Instagram:** AI carousels and AI reels remain the main daily format.
- **AI reels from `render.py`:** Instagram Reels only by default. They go to YouTube Shorts only when the editor explicitly asks, e.g. a major story with no footage.
- **Footage reels:** both Instagram and YouTube Shorts.
- **WhatsApp / Telegram:** broadsheet and forwards, the channel's main local growth route.
- **Monetisation:**
  - The YouTube Partner Programme needs 1,000 subscribers and 4,000 long-form watch hours; Shorts views do not count towards the hours.
  - Ad safety: no blood, wounds, gore or sensational clickbait.

---

## 20. Who is responsible for what

| Responsibility | People (owner / editor) | AI assistant | Code (enforced) |
|---|---|---|---|
| Which news runs; truth of facts and sources | **Accountable** — verifies and approves | Shapes copy, asks for missing sources | Requires sources and status |
| Legal safety of crime copy | Sets minor / sexual-offence / conviction flags correctly | Sub-editor and legal checklist | Refuses guilt statements and identifying detail |
| Images | Approves every AI image shown in chat | Stock reuse, generation, culture check | Provenance and disclosure on every frame |
| Design quality | Final look; approves any design change | Design QA, evidence-frame review | Templates, tokens, inspection, golden test |
| Voice | Native-ear decision on voice and pronunciation | Voiceover QA | Speech normalisation, hazard and pause checks |
| Captions, hashtags, titles, descriptions | Reads before posting | Master copy | Generates copy; checks handle and referenced files |
| Publishing | **Uploads every post**, sets covers, pastes first comments on time | Presents the schedule | Generates schedule from rendered files |
| Footage edits | Supplies original files, exact names, event date and time; approves music downloads and preview | Runs playbook and 12-expert panel, reports progress | Build tools, QC report |
| Music licences | Approves each track and download | Finds tracks, records licence | Licence field required in footage project |
| Reader complaints and corrections | Answers IG DMs / WhatsApp within IT Rules timelines (acknowledge 24 h, resolve 15 days) | Adds correction field when asked | Prints contact route; warns if missing |
| End of day | Types *stop* | Archives stock, deletes temporary files | — |
| Rules and changes | **Board locks policy**; owner approves every change | Implements changes with a decision note and tests | Tests fail if the contract is broken |
| Secrets and machine | Keeps `.env` and `.gemini_key` private | Never reads or exposes them; stays inside the project folder | Keys loaded only by the voice code |

---

## 21. Known limits

- **The expert steps are AI judgements, not guarantees.** A "10/10" score is only as good as the checklist and the evidence looked at. Taste, cultural judgement and news judgement remain human responsibilities.
- **The system cannot check whether a fact is true.** It checks that a source is named and the wording is legal, not that the source is right.
- **Legal detection is word-based.** A guilt statement worded in a way not on the list, or a name given without an age, can pass. The guards are over-eager but not complete.
- **Source quality caps footage quality.** WhatsApp copies (848×464) cannot be fully recovered by AI upscaling; getting the originals is the biggest lever.
- **One 8 GB M1 Mac.** A 3-minute AI 1440p master takes about 2 hours on a free machine, and far longer when memory runs out. The operating system can kill jobs, and they then restart.
- **Instrumental proof is by listening.** There is no automatic vocal detector.
- **No automatic uploading, analytics or scheduler.** Schedule times are informed starting points, not measured results for this channel.
- **External dependencies.** The Udayavani, Google News and OneIndia feeds can change format; Google's TTS endpoint and the Gemini API can change or throttle.
- **The voice is synthetic.** Under rule 7 it suits Instagram only.
- **The work is not saved as a version.** See issue #18.

---

## 22. Decisions needed to lock the system

These were found by reading the rule files against each other and against the code. Each needs a board decision; the recommendation is the author's view.

Severity: 🔴 **High** (legal, trust or strategy risk) · 🟠 **Medium** (quality or consistency) · 🔵 **Low** (documentation)

### #1 · May AI-made videos go on YouTube? 🔴 High
AGENTS rule 7 says no. But:
- The generated schedule posts the AI bulletin to YouTube at 08:30 and every AI reel to "Instagram Reels + YouTube Shorts".
- The master-copy template does the same.
- Newsroom Step 8 says AI Shorts "remain active on YouTube".

**Recommendation:** keep rule 7. Change the schedule so AI reels go to Instagram only and the AI bulletin is optional (off by default). Remove the contradicting lines in Step 8 and the template.

### #2 · The morning fetch can invent detail 🔴 High
The fetch sends only headlines to Gemini but asks for 3–5 detailed sentences per story, including "background causes, official statements, procedures". Detail not in any source can appear, which conflicts with "never invent facts". The output also carries no source per story.

**Recommendation:** treat fetched text as tips only. Either:
- fetch the full article text and require the model to use only that, or
- reduce the output to one-line leads with source links, so the editor verifies before production.

### #3 · Gemini key used for news writing 🔴 High
The rules say the Gemini key is strictly for voice synthesis. `fetch_daily_news.py` uses it to write the daily news.

**Recommendation:** decide explicitly. Either allow text use and update the rule, or give the fetch its own key with a billing limit.

### #4 · No named Grievance Officer 🔴 High
AGENTS rule 5 says the grievance officer and email are filled in. In code both are blank on purpose, and captions print "Instagram DM and the WhatsApp number in the bio". IT Rules 2021 Part III asks a news publisher to name a Grievance Officer.

**Recommendation:** name an officer and a monitored email in `tokens.Brand`. Captions and the closing slide then print them automatically.

### #5 · One image policy 🔴 High
Three positions conflict:
- **Rule 2:** "AI imagery only, or the plate; never web photos."
- **Step 8:** "zero fallback to the plate".
- **The contract** allows licensed, Creative Commons and handout photos, and rule 7 wants real footage on YouTube.

On top of that, stock images are AI-made but reused as "representative". The frame therefore says `ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ`, not `ಎಐ ರಚಿತ ಚಿತ್ರ`, and the AI-disclosure checks do not run for them. (The credit line does say "AI ಚಿತ್ರ".)

**Recommendation:** order of preference is own or licensed real photos, then stock, then new AI, then the plate. Any generated image, including stock, always uses nature `ai`.

### #6 · Reel length limits disagree 🟠 Medium
- **Step 8:** 28–42 s target, and "strictly rejected" over 60 s.
- **Template registry:** maximum 45 s.
- **The gate:** warns at 48 and 60 s, fails only above 90 s.

**Recommendation:** lock 28–45 s, warn above 45 s, fail above 60 s, and make the gate match.

### #7 · Card length rule disagrees 🟠 Medium
- **Step 8:** no card over 8 s; a beat at most 120 characters; the lead at most 85.
- **Code:** 150 characters per beat; cards up to 12 s.

**Recommendation:** choose one set of numbers and put it in `tokens.Motion` and the gate.

### #8 · Reel opening greeting 🟠 Medium
Step 8 bans filler openings like `ನಮಸ್ಕಾರ…` in the first 1.5 s, but the voice engine starts every reel with `ನಮಸ್ಕಾರ, ಕರಾವಳಿ ಸುದ್ದಿ.`

**Recommendation:** open directly on the headline, and let the native ear confirm it sounds right.

### #9 · Reel posting times 🟠 Medium
Code and Step 8 use 11:30, 14:30, 17:30 and 20:30. Step 10 uses 11:30, 15:30, 19:00 and 21:30.

**Recommendation:** keep the code times until a month of analytics exists, then review. Fix Step 10.

### #10 · Unregistered categories slip through 🟠 Medium
The 15 September edition uses "governance", which is not one of the 11 categories. It silently falls back to explainer colour and hashtags.

**Recommendation:** reject unknown categories at validation, or add "governance" as a 12th category.

### #11 · Footage edits bypass the Chief Editor code gate 🟠 Medium
Lines B and C have their own QC report and panel, but no `APPROVAL.md` from `review.py`.

**Recommendation:** require an approval file for footage edits too, covering QC pass, licence recorded, names confirmed and engagement question present.

### #12 · Loudness targets differ by format 🔵 Low
AI reels are −14 LUFS / −1.5 dBTP, long-format −14 / −1, and footage reels −13 / −1.5.

**Recommendation:** confirm the differences are intended, or set −14 LUFS / −1.5 dBTP everywhere.

### #13 · "Carousel must be 100% photographs" 🔵 Low
Step 8 calls it a failure, the gate only warns, and rule 2 prefers the plate over poor images.

**Recommendation:** keep it as a warning, in line with #5.

### #14 · Project folder path in the rules is wrong 🔵 Low
AGENTS rule 6 and CLAUDE.md name `/Users/shameekyogi/Oormani Suddi`; the real folder is `/Users/shameekyogi/My Apps/Oormani Suddi`.

**Recommendation:** correct both files.

### #15 · Documentation counts and descriptions are stale 🔵 Low
AGENTS, CLAUDE.md and TEMPLATES.md say "nine templates"; there are eleven. The voice file's header describes Microsoft's voice as the engine, but the default is Google.

**Recommendation:** update the wording.

### #16 · Music provenance 🟠 Medium
`news_bgm.mp3` and the ten news tracks in `bgm_options` have no recorded source or licence.

**Recommendation:** add a licence register (title, source, licence, date) and remove anything that cannot be proven.

### #17 · WhatsApp and X copy 🔵 Low
The code generates them but writes only Instagram and YouTube copy files, while the master-copy template still has slots for both.

**Recommendation:** decide whether the channel uses X. Keep the WhatsApp text in the master copy, and drop X if it is unused.

### #18 · Nothing is locked yet 🔴 High
The last saved version is commit `35b609c`. Since then about 50 files have changed and several new parts are unsaved: the Chief Editor gate, greetings, the stock library, both editing playbooks and the scripts. There is no dependency list (`requirements.txt`), so the setup cannot be rebuilt reliably on another machine.

**Recommendation:** after the board's decisions, apply them, run all tests, save everything as version 1.0 with a tag, and add a pinned dependency list.

### #19 · Morning fetch is not scheduled 🔵 Low
The script is written to run unattended at 06:05, but no scheduler is configured.

**Recommendation:** decide whether to schedule it. If so, alert the editor when `.fetch_failed` appears.

### #20 · Where footage and outputs live 🔵 Low
`Ganapathi Video/` (with an 851 MB master) sits inside the project, alongside the loose files `LIVE BG.png`, `ThumbnailPhoto.jpg` and `image.png`.

**Recommendation:** keep footage in an agreed media folder that is excluded from version control, and keep only `LIVE BG.png` as a named input.

---

## 23. Sign-off and lock procedure

### Board decision sheet

| # | Decision | Recommendation | Board decision |
|---|---|---|---|
| 1 | AI videos on YouTube | Instagram only; bulletin off by default | |
| 2 | Morning fetch content | Tips with sources, verified by the editor | |
| 3 | Gemini key use | Separate key for text, or update the rule | |
| 4 | Grievance Officer | Name a person and a monitored email | |
| 5 | Image policy | Real licensed → stock → AI → plate; generated = `ai` | |
| 6 | Reel length | 28–45 s; fail above 60 s | |
| 7 | Card and beat length | One set of numbers in code | |
| 8 | Reel opening word | Start on the headline | |
| 9 | Reel times | 11:30 / 14:30 / 17:30 / 20:30 for now | |
| 10 | Unknown categories | Reject, or add "governance" | |
| 11 | Approval file for footage edits | Required | |
| 12 | Loudness standard | −14 LUFS / −1.5 dBTP everywhere | |
| 13 | Carousel photo coverage | Warning, not failure | |
| 14–15 | Path and documentation fixes | Correct | |
| 16 | Music licence register | Create; remove unproven tracks | |
| 17 | X and WhatsApp copy | Keep WhatsApp; X only if used | |
| 18 | Version 1.0 lock | Save, tag, dependency list | |
| 19 | Scheduled fetch | Owner's choice, with failure alert | |
| 20 | Media folder | Outside version control | |
| — | Posting times, hashtags, CTAs, voice, brand look | Approve as documented in Sections 12–15 | |

**Signed:** ______________________ **Date:** ____________

### How locking works

1. Record the board's answers in `docs/DECISIONS.md` as new numbered decisions (D55 onwards), each saying what breaks without it.
2. Change the rule files (AGENTS.md, newsroom skill, triggers, editing playbooks) and the code constants to match. Add or update a test for every rule a machine can check.
3. Run the contract tests and the full suite, including the golden design test. If the design moved, inspect `out/_blessed/`.
4. Save everything as one version, tag it `v1.0-board-approved`, and add a pinned dependency list.
5. **Change control from then on.** Any change to a rule, limit, time, colour or wording needs:
   - the owner's approval,
   - a new decision entry,
   - a passing test run,
   - a new version tag.

   Day-to-day news, images and footage need no approval; they already pass through the gates.
6. **Review after 30 days of analytics:** posting times, reel length, hashtags and the YouTube strategy. That review is the only planned change.

---

## 24. Reference: files, commands and terms

### Where each responsibility lives

| Path | Responsibility |
|---|---|
| `render.py` | Entry point: JSON in, finished package out; describe/schema/check modes; routes greetings; writes copy, schedule, review and approval |
| `brand/content.py` | Story, Photo, Edition; the truth contract; clock; legal guards |
| `brand/tokens.py` | Colour, type scale, grid, formats, safe zones, motion timing, brand constants, categories |
| `brand/typo.py` | Kannada-safe text engine: baselines, wrapping, fitting, glyph checks |
| `brand/surface.py` | Canvas, photo grade, scrims, grain, gilded rules, logo, editorial plate |
| `brand/components.py` | Masthead, eyebrow, headline, deck, facts, takeaway, credit strip, sources, footer |
| `brand/ornament.py` | Greeting ornaments: foil text, dividers, filigree, mandala, arch frame |
| `brand/motion.py` | Reel and bulletin engine, sync audit, audio master |
| `brand/voice.py` | Narration beats, spoken-Kannada normalisation, TTS engines |
| `brand/copy.py` | Captions, hashtags, YouTube metadata, alt text, WhatsApp, X, schedule |
| `brand/qa.py`, `brand/review.py` | Preflight, compliance, output inspection; Chief Editor gate and approval |
| `templates/` | Eleven templates and the registry |
| `schemas/`, `docs/TEMPLATES.md` | Input contract and template reference, generated from code |
| `docs/AI_BRIEF.md` | Instructions for any AI tool supplying content |
| `STANDARDS.md`, `docs/DECISIONS.md` | Design standard; the reason behind every rule |
| `AGENTS.md`, `CLAUDE.md` | The seven overriding rules and the standard workflow |
| `.agents/skills/second-brain/` | 13-step newsroom and master-copy template |
| `.claude/skills/youtube-longform-edit/` | Long-format playbook, lessons, tools, AI models |
| `.claude/skills/reels-shorts-edit/` | Reel/Short playbook and build tool |
| `scripts/` | Morning fetch, live overlay, old wishes script (now forwards to the greeting template) |
| `editions/`, `inbox/` | Daily editorial records and greetings; fetched news |
| `assets/`, `fonts/`, `sfx/` | Logo masters, stock, daily images, music; house faces; sound effects |
| `tests/` | Contract, greeting and golden tests |
| `out/` | Rendered deliverables (`out/reference/` is the tracked visual baseline) |

### Commands

```bash
python3 render.py editions/2026-09-15.json              # full package
python3 render.py editions/2026-09-15.json --only carousel reel
python3 render.py --check editions/2026-09-15.json      # validate only
python3 render.py --describe                            # every template and its rules
python3 render.py --schema story                        # input contract
python3 render.py editions/greetings/<file>.json        # festival wish
python3 scripts/fetch_daily_news.py                     # morning news fetch
python3 scripts/live_overlay.py --partner logos/a.png   # live overlay
python3 -m unittest tests.test_contract                 # contract tests
python3 -m unittest discover tests                      # all tests incl. golden
python3 -m templates --dump && python3 schemas/_build.py && python3 docs/_build_templates_md.py
```

### Terms

| Term | Meaning |
|---|---|
| Carousel | An Instagram post of several swipeable images |
| Reel / Short | Vertical 9:16 video on Instagram / YouTube |
| Safe zone | The part of the frame not covered by the app's buttons and captions |
| Provenance | Where an image came from and what right we have to use it |
| TTS | Text-to-speech: a computer-generated voice |
| LUFS / dBTP | Measured loudness / highest true peak; platforms turn down audio above their targets |
| Ducking | Music automatically lowered while speech or real sound plays |
| Real-ESRGAN | An AI model that increases video resolution and cleans compression damage |
| BT.709 | The standard colour space for HD video; tagging it keeps colours correct on every player |
| Golden test | A test comparing new renders to the approved design, pixel for pixel |
| Editorial plate | The brand's drawn coastal graphic, used when there is no suitable photo |
| APPROVAL.md | The file written only when a package passes every machine check |
| Edition | One day's set of stories and everything made from it |

---

*ಊರ್ಮನಿ ಸುದ್ದಿ · ನಮ್ಮ ಊರು • ನಮ್ಮ ಧ್ವನಿ · @oormanisuddi — written from the project source as of 15 September 2026.*
