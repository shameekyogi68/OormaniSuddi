# Conventions every desk shares (D89, D92)

Not an agent. Every agent in this folder says "Read
`.claude/agents/_CONVENTIONS.md` first"; this is that file. A rule written
once here cannot drift between eighteen copies.

## Workspace jail
Work only inside `/Users/shameekyogi/My Apps/Oormani Suddi`. Never read,
write or run anything outside it (AGENTS.md rule 10) — not a backup target,
not a download folder, not a web page. Intake is paste-only (D92): no agent
fetches, scrapes or searches the web for news, trends or pictures.

## The newsroom since D92
- **Three formats.** `roundup` = ಸ್ಪೀಡ್ ನ್ಯೂಸ್ (9:16 reel, one frame per
  story), `saara` = ಸುದ್ದಿ ಸಾರ (**a 9:16 reel since 2026-10-23, D132/D133**:
  `reel_saara.mp4`, Ink & Gold, no picture ever, one beat per story, cut from the
  measured voice; the 4:5 carousel is kept switched off and is made only on
  request or when the reel cannot be made), `mukhya` = ಮುಖ್ಯ ಸುದ್ದಿ (4:5 photo
  carousel for ONE breaking/top story). A carousel is posted as animated `.mp4`
  slides (AGENTS rule 11); each slide's finished `.jpg` still is in
  `out/<stem>/_review/` for inspection. The saara reel's evidence is
  `_review/reel_saara_t*.jpg` (eight frames), `reel_saara_cover.jpg` and
  `_review/reel_saara_report.json` (what the engine measured and found).
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
  For a `saara` story the reel shows **`reel_line`** (the headline, two lines) and
  **`reel_support`** (ONE complete sentence on the gold card, read aloud) — each
  is read ON ITS OWN, so each is checked on its own (facts, guilt, glyphs).
- A render folder is only this edition's if `out/<stem>/.edition` names it
  (D90). If it names another edition, say so before anything else.

## Receipts — how the team knows you ran
File your report through Bash with a heredoc:
```bash
python3 scripts/dispatch.py receipt --agent <you> \
    --edition editions/<file>.json [--story N [N …]] [--format roundup|reel_saara|saara|mukhya_N] \
    --verdict PASS|FIX|BLOCK|HELD|DONE --file - <<'EOF'
<your report>
EOF
```
The receipt is stamped with a hash of what you looked at. The fact and legal
desks' hash covers only the fact-bearing fields (headline, deck, points,
numbers, quote, sources, source_urls, location, dateline, category, the legal
flags, published_at, reel_line, reel_support): assigning a segment or adding a photo does
not make them due again; a copy edit does. A BLOCK is surfaced to a person —
no agent clears another agent's block.

## The business desks (D118)
`general-manager`, `revenue-manager`, `youtube-strategist`,
`facebook-strategist`, `ad-standards` and `finance-controller` run the
company, not the newsroom. They never touch an edition or news copy. They
read `docs/BUSINESS.md` and `docs/ADVERTISING.md`, and the private books in
`business/` (`python3 scripts/business.py status`). They write only inside
`business/` — their report in `business/reports/` (the file existing is
their receipt) and drafts in `business/drafts/`. A client's or a person's
details never leave `business/`. Money never buys news: a desk that is asked
to sell a story, a slot or a removal says no.

## What no agent ever does
- write `verified_by` / `verified_at` — a person opened the source (D59)
- sign off, publish, upload or post anything
- send a message, sign or accept a deal, invoice, pay or receive money, or
  clear a deal (`scripts/business.py deal clear --by`) — a person does (D118)
- invent a fact, figure, name, place or quote that is not in the kept source
- add an override, weaken a check, or edit engine code to make a code go away
- decide a story's `segment` or `photo_plan` for the editor — propose; the
  editor confirms
