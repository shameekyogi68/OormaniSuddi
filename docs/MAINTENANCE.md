# Leaving it alone for a year

The code is finished. What changes over a year is everything *around* it:
the Mac, the network services it talks to, Instagram, the law. This file
lists each of those, how you will notice, and what to do. It adds no rule —
if it disagrees with `AGENTS.md`, `AGENTS.md` is right.

---

## The one habit: `health.py`

```bash
python3 scripts/health.py
```

Every time you sit down. It is one page, it reads only this repository and
this Mac, and every line says what to do when it is not a ✓. If it is all
green, nothing below applies to you today.

| Line | Means | Do |
|---|---|---|
| `disk` ! or ✗ | under `Limits.disk_warn_gb` / `disk_min_gb` free | `python3 scripts/archive_edition.py <date>` for finished days; empty the Trash; `du -sh out build .backups` |
| `tools` ✗ | ffmpeg, Kannada shaping (raqm) or the fallback voice is gone | the line names the command |
| `backups` ✗ | the nightly copy has not run, or there is no second copy | `bash scripts/backup.sh --status` |
| `git` ✗ unpushed | GitHub — the offsite copy — is behind | `git push` |
| `contract` ✗ | a test fails | `python3 -m unittest discover tests`; read the failure before anything else |
| `reviews` 🔴 | a recurring review is due | `python3 scripts/whats_on.py --reviews` |
| `corrections` ✗ | a statutory clock is running | `python3 scripts/correction.py status` — the clock started when the message arrived |

---

## What will change underneath you

| What | What happens | How you notice | What to do |
|---|---|---|---|
| **The disk fills** | renders stop mid-way with an error about something else | `health.py` → `disk` | archive finished days; the nightly backup now holds the record once (D112), so it is not the cause |
| **A macOS or Homebrew update** | `python3` may become a new version with none of the packages | `ModuleNotFoundError: PIL` on any command | `python3 -m pip install --break-system-packages -r requirements.txt`, then `python3 scripts/health.py` |
| **A Pillow, raqm or font update** | Kannada rasterises a pixel differently; nobody touched the design | `tests.test_golden` fails; `health.py` → `contract` stays green | RUNBOOK "The golden test failed": compare `PROVENANCE.json` of a recent render with now, **look** at `out/_blessed/`, bless only if it looks right |
| **Pillow without raqm** | every conjunct renders broken | `health.py` → `tools` ✗ | `python3 -m pip install --break-system-packages --force-reinstall Pillow` |
| **ffmpeg changes or disappears** | no reel, no carousel video | `health.py` → `tools` ✗; `tests.test_animate` fails | `brew install ffmpeg` (or `brew reinstall ffmpeg`) |
| **Google's speech endpoint changes** | narration uses the fallback voice | the render prints `! TTS fell back google → edge`; `SND-02` if every engine fails | it is an unofficial endpoint (`translate_tts` in `brand/voice.py`). Short outages are retried (D110). If it stays down, the editor decides by ear: post with the fallback, or wait. `OORMANI_TTS_ENGINE=gemini` uses the Gemini key |
| **Gemini retires its preview TTS model** | only matters when Gemini is in use | an HTTP 404 naming `gemini-2.5-flash-preview-tts` | that one string in `brand/voice.py :: _gemini_tts_synthesize`, plus a decision entry |
| **An API key expires** | Gemini calls fail with 400/403 | the render's fallback line names it | a new key in `.env` (`GEMINI_API_KEY=…`) or `.gemini_key`. Never in git |
| **Instagram changes a rule** | hashtag cap, caption fold, carousel limits, Reels UI | Instagram's announcement, or numbers in `scripts/metrics.py report` | a **number** → `tokens.Limits` with a decision and a test (`python3 scripts/house_rule.py where "…"`); the playbook → `docs/INSTAGRAM.md`, labelled by how sure it is |
| **The law changes** | IT Rules amendments, BNS, a court ruling | the 90-day law review in `whats_on.py --reviews` | a legal rule → `brand/content.py`. Add the row to `tests/legal_corpus.json` **first**, watch it fail, then change the guard (D61) |
| **The Grievance Officer or contact changes** | IT Rules 2021 Part III needs a named, reachable person | — | `tokens.Brand.grievance_officer` / `grievance_email` / `grievance_phone`. Blank blocks every render (`OPS-01`), correctly |
| **Next year's festivals** | the calendar runs to October 2027 | `whats_on.py --days 90` goes quiet past it | extend `editions/greetings/calendar.json`; confirm every lunar date from a Udupi panchanga |

---

## The recurring reviews

`python3 scripts/whats_on.py --reviews` keeps the dates. What each one is:

- **metrics review, monthly.** `python3 scripts/metrics.py report`. Every number
  in `tokens.Limits` marked as a guess is a hypothesis until the channel's own
  numbers argue with it. Log last week's posts first (`metrics.py add …`).
- **law review, every 90 days.** Read the legal guards (`brand/content.py`)
  against anything new in the law; add near-misses to the corpus.
- **backup restore test, every 90 days.** Prove the copy restores:
  ```bash
  mkdir -p out/_restore && cd out/_restore
  for f in ../../.backups/record/*.tar.gz; do tar -xzf "$f"; done
  tar -xzf "$(ls -t ../../.backups/oormani-2*.tar.gz | head -1)"
  diff -rq archive ../../archive && echo "restores clean"
  cd ../.. && rm -rf out/_restore
  ```
- **licence audit, every 180 days.** `assets/LICENCES.json` — every music bed
  and font still licensed for what it is used for.

---

## A new Mac, from nothing

```bash
git clone https://github.com/shameekyogi68/OormaniSuddi.git "Oormani Suddi"
cd "Oormani Suddi"
brew install ffmpeg
python3 -m pip install --break-system-packages -r requirements.txt
bash scripts/install_hooks.sh
python3 -m unittest discover tests          # all green, golden included, before anything else
# the published record and the sources, from the second copy:
for f in "<second copy>"/record/*.tar.gz; do tar -xzf "$f"; done
tar -xzf "$(ls -t "<second copy>"/oormani-2*.tar.gz | head -1)"
bash scripts/backup.sh --install            # the nightly backup again
```

Then put the Gemini key in `.env` and run `python3 scripts/health.py`.

---

## Things not to do, however tempting on a deadline

- **Add an override flag** to a legal or sourcing check. D29: a guard that can
  be waived on a deadline gets waived on a deadline.
- **Hand-edit** `tests/golden.json`, `schemas/*.json`, `templates/registry.json`,
  `docs/TEMPLATES.md` or `docs/TRACEABILITY.md`. They are generated.
- **Delete or rename slides** in a render folder to "fix" it. Re-render the
  format; the gate checks the sequence (`PKG-06`).
- **Delete an edition JSON.** Stop means `archive_edition.py`.
- **Upgrade Homebrew or Python the morning of a big story.** Do it on a quiet
  day, then run `health.py` and the full test suite.

---

## When you come back to change something

1. `python3 scripts/house_rule.py where "…"` — a number, a legal rule, a place,
   or a house rule. Four homes, and only four.
2. Find or write its entry in `docs/DECISIONS.md` (`grep -n "^## D<n>"`).
3. The test first, then the code.
4. `python3 -m unittest discover tests` and the four regenerate commands in
   `AGENTS.md`.
