# Templates

Generated from `templates/__init__.py` — do not edit by hand; run
`python3 docs/_build_templates_md.py` instead.

Nine templates. Each is one file in `templates/`, self-contained: no template
imports another, so you can read one without reading the rest.

```python
import templates as TP
TP.render('report_card', story, 'out/card.jpg')     # by name
TP.choose(story)                                     # let it pick
TP.get('report_card').limits                         # the rules, as data
```

Or without Python at all — see [`AI_BRIEF.md`](AI_BRIEF.md):

```bash
python3 render.py edition.json --only report_card carousel
```

## At a glance

| Template | Size | Takes | Use it when |
|---|---|---|---|
| [`report_card`](#report-card) | 1080×1350 | story | The default for almost everything. |
| [`text_card`](#text-card) | 1080×1350 | story | Only when you deliberately want a pure typographic poster with no visual at all. |
| [`quote_card`](#quote-card) | 1080×1080 | story | Use when the story IS somebody's words — a statement, an order read out, a reaction. |
| [`stat_card`](#stat-card) | 1080×1080 | story | Use when the story IS the number — rainfall totals, budgets, turnout, case counts. |
| [`story_card`](#story-card) | 1080×1920 | story | One per edition, usually the lead. |
| [`youtube_thumb`](#youtube-thumb) | 1280×720 | story | One per video. |
| [`carousel`](#carousel) | 1080×1080 | edition | One per edition. |
| [`broadsheet`](#broadsheet) | 1080×1620 | edition | One per edition, for readers who want everything at a glance. |
| [`bulletin`](#bulletin) | 1920×1080 | edition | One per edition. |
| [`reel`](#reel) | 1080×1920 | edition | One per edition — the lead only. |

---

## `report_card`

The flagship 4:5 news post: full-bleed photograph over an editorial stack.

**When to use.** The default for almost everything. With a photograph it leads on the picture; without one it draws an editorial plate, so the post still has a visual.

| | |
|---|---|
| file | `templates/report_card.py` → `report_card()` |
| takes | a `Story` |
| output | 1080×1350 at 2× supersample, file |
| safe inset | 72, 72, 72, 72 (L, T, R, B) |
| format note | IG feed 4:5 — the tallest crop the feed allows |

**Requires.** `headline`, `category`, `sources`, `status`, `published_at`

**Also accepts.** `photo`, `deck`, `points`, `takeaway`, `location`, `dateline`, `reporter`

**Limits.** `headline_chars` = 78, `deck_chars` = 190, `points` = 3, `point_chars` = 150

**Note.** Drops content in editorial order when it cannot fit everything: advisory, then standfirst, then facts from the bottom. On weather / health / civic / breaking the advisory survives instead, because the helpline is the point.

---

## `text_card`

4:5 typographic poster with no photograph.

**When to use.** Only when you deliberately want a pure typographic poster with no visual at all. For an ordinary story with no photograph, use report_card — it draws a plate.

| | |
|---|---|
| file | `templates/text_card.py` → `text_card()` |
| takes | a `Story` |
| output | 1080×1350 at 2× supersample, file |
| safe inset | 72, 72, 72, 72 (L, T, R, B) |
| format note | IG feed 4:5 — the tallest crop the feed allows |

**Requires.** `headline`, `category`, `sources`, `status`, `published_at`

**Also accepts.** `deck`, `points`, `takeaway`, `numbers`, `location`, `dateline`

**Limits.** `headline_chars` = 78, `deck_chars` = 190, `points` = 3

**Note.** Sets the headline much larger than report_card, because it has the whole frame.

---

## `quote_card`

A single voice on a duotone bed.

**When to use.** Use when the story IS somebody's words — a statement, an order read out, a reaction.

| | |
|---|---|
| file | `templates/quote_card.py` → `quote_card()` |
| takes | a `Story` |
| output | 1080×1080 at 2× supersample, file |
| safe inset | 72, 72, 72, 72 (L, T, R, B) |
| format note | Carousel slides, X, LinkedIn |

**Requires.** `headline`, `category`, `sources`, `status`, `published_at`, `quote`

**Also accepts.** `photo`, `location`

**Limits.** `quote_chars` = 240

**Note.** quote is a two-item list: [text, attribution]. The photograph, if any, is flattened to two tones so it cannot fight the words.

---

## `stat_card`

Big numerals with Kannada labels.

**When to use.** Use when the story IS the number — rainfall totals, budgets, turnout, case counts.

| | |
|---|---|
| file | `templates/stat_card.py` → `stat_card()` |
| takes | a `Story` |
| output | 1080×1080 at 2× supersample, file |
| safe inset | 72, 72, 72, 72 (L, T, R, B) |
| format note | Carousel slides, X, LinkedIn |

**Requires.** `headline`, `category`, `sources`, `status`, `published_at`, `numbers`

**Also accepts.** `deck`, `location`

**Limits.** `headline_chars` = 70, `numbers` = 3

**Note.** numbers is a list of [value, label] pairs. Three reads best; four starts to crowd.

---

## `story_card`

9:16 still for Instagram Stories and WhatsApp status.

**When to use.** One per edition, usually the lead. Also the right format for a single urgent alert.

| | |
|---|---|
| file | `templates/story_card.py` → `story_card()` |
| takes | a `Story` |
| output | 1080×1920 at 2× supersample, file |
| safe inset | 72, 250, 72, 340 (L, T, R, B) |
| format note | IG story — top chrome ~230px, bottom reply bar ~320px |

**Requires.** `headline`, `category`, `sources`, `status`, `published_at`

**Also accepts.** `photo`, `deck`, `location`

**Limits.** `headline_chars` = 78

**Note.** Critical content stays inside a 72/250/72/340 safe inset. The band below it carries the handle rather than dead black.

---

## `youtube_thumb`

16:9 thumbnail built to survive a 6× reduction.

**When to use.** One per video. Pass a short hook=, NOT the headline.

| | |
|---|---|
| file | `templates/youtube_thumb.py` → `youtube_thumb()` |
| takes | a `Story` |
| output | 1280×720 at 2× supersample, file |
| safe inset | 48, 40, 48, 96 (L, T, R, B) |
| format note | YT thumbnail — bottom-right 190x60 hidden by duration chip |

**Requires.** `headline`, `category`, `sources`, `status`, `published_at`

**Also accepts.** `photo`, `location`, `hook`

**Limits.** `hook_chars` = 34, `hook_words` = 7

**Note.** In a YouTube feed this is about 210 px wide. Anything longer than about seven words stops being readable there, and the renderer warns when you exceed it.

---

## `carousel`

The day's bulletin as a swipeable set: cover → one slide per story → sources and follow.

**When to use.** One per edition. This is the highest-reach format for a daily round-up.

| | |
|---|---|
| file | `templates/carousel.py` → `carousel()` |
| takes | a `Edition` |
| output | 1080×1080 at 2× supersample, files |
| safe inset | 72, 72, 72, 72 (L, T, R, B) |
| format note | Carousel slides, X, LinkedIn |

**Requires.** `stories`, `date`, `edition_no`, `strapline`

**Also accepts.** —

**Limits.** `stories` = 6

**Note.** Returns a list of paths. Slides carry a segmented progress bar; a slide whose story has no photograph is set as a statement card rather than left half-empty.

---

## `broadsheet`

The day's edition as a single front page.

**When to use.** One per edition, for readers who want everything at a glance. Also the best thing to forward on WhatsApp.

| | |
|---|---|
| file | `templates/broadsheet.py` → `broadsheet()` |
| takes | a `Edition` |
| output | 1080×1620 at 2× supersample, file |
| safe inset | 64, 56, 64, 56 (L, T, R, B) |
| format note | Daily edition 2:3 broadsheet |

**Requires.** `stories`, `date`, `edition_no`, `strapline`

**Also accepts.** —

**Limits.** `stories` = 5

**Note.** Lead story plus up to four in two columns; column cells are as tall as their content, not a fixed fraction.

---

## `bulletin`

16:9 long-form bulletin for YouTube.

**When to use.** One per edition. This is what the youtube_thumb is FOR — a vertical clip under 60s is a Short, and Shorts do not take a custom thumbnail.

| | |
|---|---|
| file | `templates/bulletin.py` → `bulletin()` |
| takes | a `Edition` |
| output | 1920×1080 at 2× supersample, file |
| safe inset | 96, 72, 96, 84 (L, T, R, B) |
| format note | YouTube long-form bulletin 16:9 |

**Requires.** `stories`, `date`, `edition_no`, `strapline`

**Also accepts.** `target_seconds`

**Limits.** `stories` = 8, `reel_line_chars` = 46

**Note.** Same engine as the reel at a landscape aspect: the type lays out as a broadcast lower-third instead of a full-height column. Opens the 1,000-subs + 4,000-watch-hours monetisation path, which a Shorts-only channel cannot realistically reach.

---

## `reel`

9:16 Short of the LEAD story, with mastered audio.

**When to use.** One per edition — the lead only. The carousel and the 16:9 bulletin carry the rest. Opens on the news, not a logo sting.

| | |
|---|---|
| file | `templates/reel.py` → `render_reel()` |
| takes | a `Edition` |
| output | 1080×1920 at 2× supersample, file |
| safe inset | 72, 230, 220, 480 (L, T, R, B) |
| format note | IG Reel / YT Short — right action rail 200px, bottom caption block up to 470px |

**Requires.** `stories`, `date`, `edition_no`, `strapline`

**Also accepts.** `target_seconds`

**Limits.** `stories` = 1, `reel_line_chars` = 46, `target_seconds_min` = 8, `target_seconds_max` = 45

**Note.** A reel is a glance in a vertical feed: one story, no sting, headline on frame 0. Writes reel_cover.jpg — set that as the Instagram / Shorts cover. Write a reel_line of ~45 chars. Audio is normalised to -14 LUFS / -1.5 dBTP.

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
