---
name: publish-edition
description: Validate and render a day's ಊರ್ಮನಿ ಸುದ್ದಿ edition (editions/*.json) in its three formats — ಸ್ಪೀಡ್ ನ್ಯೂಸ್, ಸುದ್ದಿ ಸಾರ, ಮುಖ್ಯ ಸುದ್ದಿ — run the gate, and report honestly what was made and what to post where. Use when publishing an edition the editor has already approved.
disable-model-invocation: true
---

# Publish an edition

`$ARGUMENTS` is the edition path. Default to the newest file in `editions/`.
This is steps 2–5 of the "Approve" section of `docs/RUNBOOK.md`; the editor
must already have confirmed segments, answered "real photo or generate?" for
every `mukhya` story without a picture, and given their name for
`scripts/verify.py`.

## 1 · Check before rendering

```bash
python3 render.py --check "$EDITION"
python3 scripts/fact_check.py "$EDITION"
```

Failures block; warnings are a sub-editor's call — read them all. A
`ContentError` is the law (`Story.validate()`, D29): rewrite the copy, never
look for a way round the guard. `headline` and `reel_line` each need their own
ಆರೋಪ / ಆರೋಪಿ / ಶಂಕಿತ.

## 2 · Render

```bash
python3 render.py "$EDITION"                       # every segment present
python3 render.py "$EDITION" --only saara mukhya   # while iterating; skip the reel
```

Pass `--at <ISO>` to pin the clock. Output in `out/<edition-stem>/` — what
gets posted, and nothing else (D102):

| Format | Post these | Copy |
|---|---|---|
| ಸ್ಪೀಡ್ ನ್ಯೂಸ್ | `roundup.mp4` + `roundup_cover.jpg` as its cover | `roundup_caption.txt` |
| ಸುದ್ದಿ ಸಾರ | `saara_01_cover.mp4`, `saara_02.mp4` … `saara_NN_sources.mp4` | `saara_caption.txt` |
| ಮುಖ್ಯ ಸುದ್ದಿ (per story k) | `mukhya_k_01_cover.mp4`, `mukhya_k_02_points.mp4`, `mukhya_k_03_source.mp4` | `mukhya_k_caption.txt` |

Carousels are animated `.mp4` slides posted as ONE carousel of separate
videos, in order — never joined, never the `.jpg` stills (AGENTS rule 11).
The stills are in `_review/`, for the inspectors and the sign-off. A re-render
clears each format's previous slides (D107) and unsigns the package (D108):
the editor signs again after looking.

## 3 · Gate

The Chief Editor gate writes `APPROVAL.md` only when clean. If HELD, read
`review_report.json` and map each code with the RUNBOOK table (or run the
gate-doctor agent).

## 4 · Report honestly

Say plainly: files produced and where; the reel's length; **every warning that
fired**; the gate result. Show the covers and the `_review/` frames rather
than describing them. Then:

- ಸುದ್ದಿ ಸಾರ and each ಮುಖ್ಯ ಸುದ್ದಿ → Instagram carousels;
- ಸ್ಪೀಡ್ ನ್ಯೂಸ್ → Instagram Reels only (YouTube only if the editor asks);
- times from `schedule.txt`; captions from the `*_caption.txt` files.

The editor signs — `python3 scripts/sign_off.py out/<date> --by "<name>"` —
and a person uploads. Never sign, never post.
