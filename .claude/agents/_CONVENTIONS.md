# Conventions every desk shares (D89, D92)

Not an agent. Every agent in this folder says "Read
`.claude/agents/_CONVENTIONS.md` first"; this is that file. A rule written
once here cannot drift between twelve copies.

## Workspace jail
Work only inside `/Users/shameekyogi/My Apps/Oormani Suddi`. Never read,
write or run anything outside it (AGENTS.md rule 8) — not a backup target,
not a download folder, not a web page. Intake is paste-only (D92): no agent
fetches, scrapes or searches the web for news, trends or pictures.

## The newsroom since D92
- **Three formats.** `roundup` = ಸ್ಪೀಡ್ ನ್ಯೂಸ್ (9:16 reel, one frame per
  story), `saara` = ಸುದ್ದಿ ಸಾರ (4:5 text-only carousel — never a picture),
  `mukhya` = ಮುಖ್ಯ ಸುದ್ದಿ (4:5 photo carousel for ONE breaking/top story).
- **One story, one format.** Every story carries `segment` — `speed`,
  `saara` or `mukhya`. The field holds one value; a story is never in two.
- **Pictures.** `mukhya` always has a photo; `speed` may; `saara` never.
  Real photos first. `photo_plan`: `''` nobody has asked the editor yet ·
  `real` the editor is sending a photograph · `ai` the editor said generate.
  Every AI photo carries `photo.approved_by` (the editor's name). There is
  no stock library.
- **Sources.** The editor's pasted text is the story's kept source
  (`python3 scripts/intake.py source`, kept in `inbox/sources/`). Facts are
  checked against that text, offline.

## Stories and scope
- Stories are numbered from 1, in the order they appear in `stories`.
- **A desk works story by story, in batches (D97).** You may be given
  several stories in one run (up to `Limits.agent_batch_max`). Take each
  separately, in order, as if it were alone — one story's source never
  informs another's verdict — and file ONE receipt per story, against that
  story's own hash. `--story 1 2 3` files the same verdict for several; a
  different verdict needs its own command. Read this file and your own once,
  not once per story.
- In scope: every field that exists on the story — headline, reel_line,
  hook, deck, points, reel_points, takeaway, narration_script, photo caption.
  A field the story does not have is skipped, not reported as a finding.
- A render folder is only this edition's if `out/<stem>/.edition` names it
  (D90). If it names another edition, say so before anything else.

## Receipts — how the team knows you ran
File your report through Bash with a heredoc:
```bash
python3 scripts/dispatch.py receipt --agent <you> \
    --edition editions/<file>.json [--story N [N …]] [--format roundup|saara|mukhya_N] \
    --verdict PASS|FIX|BLOCK|HELD|DONE --file - <<'EOF'
<your report>
EOF
```
The receipt is stamped with a hash of what you looked at. The fact and legal
desks' hash covers only the fact-bearing fields (headline, deck, points,
numbers, quote, sources, source_urls, location, dateline, category, the legal
flags, published_at, reel_line): assigning a segment or adding a photo does
not make them due again; a copy edit does. A BLOCK is surfaced to a person —
no agent clears another agent's block.

## What no agent ever does
- write `verified_by` / `verified_at` — a person opened the source (D59)
- sign off, publish, upload or post anything
- invent a fact, figure, name, place or quote that is not in the kept source
- add an override, weaken a check, or edit engine code to make a code go away
- decide a story's `segment` or `photo_plan` for the editor — propose; the
  editor confirms
