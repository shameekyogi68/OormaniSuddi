# Templates

Generated from `templates/__init__.py` — do not edit by hand; run
`python3 docs/_build_templates_md.py` instead.

Three news formats and a greeting (D92). A story runs in exactly one news
format — the one its `segment` names. The shared Paper & Red drawing kit is
`brand/paper.py`.

```python
import templates as TP
TP.choose(story)                                     # its format, from segment
TP.get('saara').limits                               # the rules, as data
```

Or without Python at all — see [`AI_BRIEF.md`](AI_BRIEF.md):

```bash
python3 render.py editions/DATE.json                  # every segment present
python3 render.py editions/DATE.json --only saara roundup
```

## At a glance

| Template | Size | Takes | Use it when |
|---|---|---|---|
| [`saara`](#saara) | 1080×1350 | edition | Stories with segment "saara". |
| [`mukhya`](#mukhya) | 1080×1350 | story | Stories with segment "mukhya": breaking news, or the day's story that deserves its own post. |
| [`roundup`](#roundup) | 1080×1920 | edition | Stories with segment "speed": the day's quick hits, three or more. |
| [`greeting`](#greeting) | 1080×1920 | greeting | Festival and occasion wishes only — Gauri-Ganesha, Deepavali, Ugadi, Rajyotsava, Eid, Christmas and the like. |

---

## `saara`

ಸುದ್ದಿ ಸಾರ — the day's video bulletin: front-page cover (lead + teasers, D103) → one slide per story → sources and follow. Animated scan-wipe .mp4 per slide (D98–D100). No pictures, ever.

**When to use.** Stories with segment "saara". The everyday digest: useful, quick to read, forwarded. Needs Limits.saara_min_stories to Limits.saara_max_stories stories.

| | |
|---|---|
| file | `templates/saara.py` → `saara()` |
| takes | a `Edition` |
| output | 1080×1350 at 2× supersample, files |
| safe inset | 72, 72, 72, 72 (L, T, R, B) |
| format note | IG feed 4:5 — the tallest crop the feed allows |

**Requires.** `stories`, `date`, `segment: "saara"`

**Also accepts.** `deck`, `points`, `location`, `category`

**Limits.** `stories_min` = 2, `stories_max` = 6, `points` = 3

**Note.** Paper & Red (D92). A photograph on a saara story is ignored. Writes animated scan-wipe video slides saara_01_cover.mp4, saara_02.mp4 … saara_NN_sources.mp4 (D98–D100) to post as a video carousel, with saara_copy.txt and saara_caption.txt.

---

## `mukhya`

ಮುಖ್ಯ ಸುದ್ದಿ — one breaking or top story: photo cover → ಏನಾಗಿದೆ? → source and corrections. Animated scan-wipe .mp4 per slide (D98–D100).

**When to use.** Stories with segment "mukhya": breaking news, or the day's story that deserves its own post. Always a picture — a real one first; AI only when the editor was asked and said generate (photo_plan "ai", photo.approved_by).

| | |
|---|---|
| file | `templates/mukhya.py` → `mukhya()` |
| takes | a `Story` |
| output | 1080×1350 at 2× supersample, files |
| safe inset | 72, 72, 72, 72 (L, T, R, B) |
| format note | IG feed 4:5 — the tallest crop the feed allows |

**Requires.** `headline`, `category`, `sources`, `status`, `published_at`, `photo`, `segment: "mukhya"`

**Also accepts.** `deck`, `points`, `location`, `takeaway`

**Limits.** `per_day` = 2, `points` = 3

**Note.** Paper & Red (D92). A breaking story's kicker is the red ಬ್ರೇಕಿಂಗ್ block, computed from published_at, never asserted. Writes animated scan-wipe video slides mukhya_<k>_01_cover.mp4, _02_points.mp4, _03_source.mp4 (D98–D100) to post as a video carousel, and mukhya_<k>_copy.txt / _caption.txt.

---

## `roundup`

ಸ್ಪೀಡ್ ನ್ಯೂಸ್ — the day's stories as one quick-news reel.

**When to use.** Stories with segment "speed": the day's quick hits, three or more. A place and one line per story, spoken by the anchor while it is on screen. A story without a picture gets a type-only frame.

| | |
|---|---|
| file | `templates/roundup.py` → `render_roundup()` |
| takes | a `Edition` |
| output | 1080×1920 at 2× supersample, file |
| safe inset | 72, 230, 220, 480 (L, T, R, B) |
| format note | IG Reel / YT Short — right action rail 200px, bottom caption block up to 470px |

**Requires.** `stories`, `date`, `edition_no`, `strapline`

**Also accepts.** —

**Limits.** `stories_min` = 3, `reel_line_chars` = 46, `target_seconds_max` = 45

**Note.** Each story is cut to its own measured narration (2.8–6.0s), with a counter and one progress segment per story. The wipe moves pictures only: story text is gone before it starts and returns after it lands, so a cut never slices a headline. Laid out in the Reels safe zone, clear of the action rail and the caption. Every word spoken goes through the TTS normaliser; audio is measured and corrected in two passes to -14 LUFS. When the day runs past 45s the tail stories are left out and reported. Paper & Red (D92). Writes roundup_cover.jpg and roundup_caption.txt.

---

## `greeting`

A festival wish designed as a poster, not a bulletin: centred, gold foil, ornament, signed by the channel.

**When to use.** Festival and occasion wishes only — Gauri-Ganesha, Deepavali, Ugadi, Rajyotsava, Eid, Christmas and the like. Never for news: a news story set in this template reads as a celebration.

| | |
|---|---|
| file | `templates/greeting.py` → `greeting()` |
| takes | a `Greeting` |
| output | 1080×1920 at 2× supersample, files |
| safe inset | 72, 250, 72, 340 (L, T, R, B) |
| format note | IG story — top chrome ~230px, bottom reply bar ~320px |

**Requires.** `kind: "greeting"`, `occasion`

**Also accepts.** `wish`, `salutation`, `blessing`, `theme`, `photo`, `keep_clear`, `sign_label`, `date`, `tags`, `slug`

**Limits.** `occasion_chars` = 30, `wish_chars` = 26, `salutation_chars` = 34, `blessing_chars` = 96, `themes` = sacred lights harvest rajyotsava national serene

**Note.** Renders wish_9x16.jpg, wish_4x5.jpg and wish_1x1.jpg plus wish_copy.txt. A photograph MUST declare keep_clear — the band of the image, as fractions of its height, that holds the deity or subject — and no type is ever set inside it: the solver moves the picture, frames it in an arch, or refuses. An AI image is labelled on the poster and in the caption automatically. See DECISIONS.md D54.

---

## Adding one

1. Write `templates/<name>.py`. Take every colour, size and margin from
   `brand.tokens`; build from `brand.components`, not raw `ImageDraw`.
2. Flow the content, do not position it — see [`../STANDARDS.md`](../STANDARDS.md) §6.
3. Respect the format's safe inset.
4. Finish with `grain(sf, Grade.grain, Grade.grain_shadow_bias)`.
5. Add a `Spec` to `templates/__init__.py`.
6. Regenerate: `python3 -m templates --dump && python3 docs/_build_templates_md.py`
7. Add a golden case in `tests/test_golden.py` so the design is pinned.
