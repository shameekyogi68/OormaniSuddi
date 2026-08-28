---
name: publish-edition
description: Validate and render a day's bulletin from editions/*.json, then report what preflight and the output audit actually said. Use when publishing an edition of ಊರ್ಮನಿ ಸುದ್ದಿ.
disable-model-invocation: true
---

# Publish an edition

Renders a full package — posts, carousel, 9:16 story, YouTube thumbnail,
broadsheet, the 9:16 reel, the 16:9 YouTube bulletin, and the copy for each —
from one JSON file.

`$ARGUMENTS` is the edition path. Default to the newest file in `editions/`
when none is given.

## 1 · Check before rendering anything

```bash
python3 render.py --check "$EDITION"
```

A render takes about three minutes, most of it the reel. Never start one
against copy that has not cleared preflight.

**Failures block. Warnings do not — but read them, they are the useful ones:**

| Warning | What it means | Do |
|---|---|---|
| `no reel_line` on a long headline | that scene has to run long to stay readable | add a `reel_line` of ~45 chars |
| `needs Ns to read but the scene caps at 12.0s` | the viewer will be cut off mid-sentence | **cut the copy** — do not raise `hold_max` |
| `crime story: confirm nobody involved is a minor` | fires on every crime story, by design | confirm, then set `involves_minor` / `sexual_offence` if either applies |
| `photo licence is fair-dealing` | a defence, not a permission | keep a note of why |
| `Ns is under 60s, so YouTube will treat this as a Short` | the bulletin has too little copy for long-form | add a story or write fuller decks — it is **not** padded |
| `Ns is over 120s` | a long watch for a local bulletin | fewer stories, or tighter decks |

A `ContentError` is not a warning. `Story.validate()` enforces Indian
criminal-reporting law — see `docs/DECISIONS.md` D29. Rewrite the copy;
never reach for a way around the guard. The `headline` and `reel_line` are
checked on their own, so each needs its own ಆರೋಪ / ಆರೋಪಿ / ಶಂಕಿತ.

## 2 · Render

```bash
python3 render.py "$EDITION"
```

Add `--only posts carousel` to skip both videos while iterating on copy.
Pass `--at <ISO>` to pin the clock for a reproducible render.

The two videos are different products, not two sizes of one. `reel.mp4` is
9:16 and ~35s, for Instagram. `bulletin.mp4` is 16:9 and 60-120s, and it is
what `yt_thumbnail.jpg` is the thumbnail *for* — a Short ignores custom
thumbnails, so without the bulletin that thumbnail has nothing to sit on.
The bulletin roughly doubles render time; skip it with `--only` while drafting.

## 3 · Report honestly

Read the OUTPUT AUDIT section back to the user. Say plainly:

- how many files were produced, and where
- the reel's and the bulletin's total length, and their per-scene timings
- whether the bulletin landed in the 60-120s long-form zone
- **every warning that fired**, not just a "done" — the warnings are the
  reason this step exists

Show the lead post and the reel so they can be looked at, rather than
describing them.
