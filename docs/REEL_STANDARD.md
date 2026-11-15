# ಸುದ್ದಿ ಸಾರ reel — the quality standard (any AI: Claude, Gemini, anyone)

You are making the reel of a respected Kannada news channel, from news the editor pasted. This page is the contract. It is the same
whichever AI does the work, and the **gate enforces it in code** — a reel that breaks it is held, so reading this first saves a render.

The editor pastes news and types `/daily-saara`. They ask nothing in between, so you decide, do, check and report. The steps are in
`.claude/skills/daily-saara/SKILL.md` (a copy sits in `.agents/skills/daily-saara/`). This page is the standard those steps must meet.

## 1. The copy (what you write)

| Field | Rule |
|---|---|
| `reel_line` | the headline for the screen: ≤ 34 characters, two lines, **names an event** (a verb or a clear happening) — never a label like "ಹಣ ವರ್ಗಾವಣೆ ದೂರು" |
| `reel_support` | ONE sentence, **a new fact the headline does not say** (who, where, how many, what next). Within the character allowance `reel_check.py` prints. Written to be spoken: a breath (comma) in the middle if it runs past about nine words |
| crime / allegation | carries ಆರೋಪ / ಶಂಕಿತ / ಪ್ರಕರಣ ದಾಖಲು **in the line itself**; never states guilt; no name unless the paste gives one and the law allows |
| every word | **comes from the paste.** No colour the paste lacks: no ದಾರುಣ, ಭೀಕರ, ತೀವ್ರ, ಸುಸಜ್ಜಿತ, ಯಶಸ್ವಿ, ಭಾರಿ … unless the paste says that word. A death in the paste's own words, with dignity |
| figures | joined to their ending: `66ರಲ್ಲಿ`, `22ರಂದು`, `33ನೇ` — never `66 ರಲ್ಲಿ` |
| names ending in a consonant | ending after a ZWNJ: `ಸ್ಟೀವನ್‌ಗೆ` |
| names ending in ು | take ಇ before an ending: `ಬರಗೂರಿಗೆ`, not `ಬರಗೂರುಗೆ` |
| spelling | the paste's spelling. Kannada changes meaning with one sound — ದಿನ/ದೀನ, ಕೊಲೆ/ಕೊಳೆ, ಕಲ್ಲು/ಕಳ್ಳ, ಅನ್ನ/ಅಣ್ಣ, ಬಂದ/ಬಂಧ, ದನ/ಧನ. Vowel length (ಹ್ರಸ್ವ/ದೀರ್ಘ), ಲ/ಳ, ನ/ಣ, plain/aspirated (ಅಲ್ಪಪ್ರಾಣ/ಮಹಾಪ್ರಾಣ) and single/double (ಒತ್ತಕ್ಷರ) consonants are checked word by word |
| TV style | punchy active verbs and word order, as a Kannada TV newsroom writes. **The punch is style, not added facts.** When style and source disagree, the source wins |

**Premium means restrained, not inflated.** Use the shortest complete wording that preserves the fact and its scope. No promotional filler, stock praise, predictions dressed as impact, or gratuitous physical detail in the spoken reel — even when a source uses it. The support sentence ends as a sentence, adds one useful fact, and gives the listener a natural breath. Write a `takeaway` only when the source gives the reader something concrete to do, a deadline, a route or a contact; never invent usefulness.

Order the stories lead-first. At most six. The same source as an earlier day is a repeat: the editor decides, you never drop or keep it silently.

## 2. The clock

The reel must fit **59 s** at the voice's natural pace. `python3 scripts/reel_check.py editions/<date>.json --strict` estimates it (a headline
≈ 0.09 s a character plus the town's 0.36 s breath; a card ≈ 0.085 s a character) and says NOT CLEAN if it is over. **Shorten the copy until it
says CLEAN.** Never rely on the render to squeeze it: when the tightest pauses still do not fit, the speech is sped up (up to 5 %), the pauses go
to their minimum, and the reel sounds hurried and the effects crowd the words. A reel that needed that is a copy mistake.

## 3. The voice

* **Gemini "Kore"** on the `gemini-2.5-flash-preview-tts` model (`brand/voice.py :: GEMINI_MODELS`, `Limits.saara_reel_voice`). Measured on a
  sentence full of aspirates, ottaksharas and long vowels: it keeps the aspirates (5 of 5; Microsoft's Edge voices keep 1–2, the Google voice 3), whose
  loss is what makes Kannada sound Tamil- or Malayalam-accented.
* **No spoken direction.** The 2.5 model answers a long direction with "no audio"; the 3.x models read it aloud; none takes a system instruction.
  So the text is sent bare and the voice and model are the only levers. Do not prepend "read like a news anchor". (`saara_reel_gemini_style` is `''` on purpose.)
* A headline and its card are asked for in **one request** and cut apart by the heard words. A pause of at least 0.36 s follows the town, which is its
  own sentence ("ಬೈಂದೂರು. …"). The follow line is spoken as "Follow ಮಾಡಿ" (Latin "Follow": Kore slurs ಫಾಲೋ ಮಾಡಿ into ಫಾಲ್ಮಾಲಿ).
* The key quota is 10 requests a day per key on the free tier; three or four keys sit in `.env` (git-ignored; never print, never commit). A reel needs
  about 7 to 8. **Spend them once**: settle the copy first, render after. If every key is spent the whole reel falls back to the Google voice and says so.
* Fix a word the editor hears wrong, for every reel from then on: `python3 scripts/reel_say.py "<line>" --respell "<word>=<sound>" --play`.

## 4. The sound effects

Licensed effects fitted by `scripts/sfx_import.py` (`assets/sfx/pro/`, git-ignored); the house set is the fallback. A whoosh never begins until the
last word before it has ended. The gate measures any effect that still runs onto speech.

## 5. What the gate measures (so you know what will hold the reel)

`reel_check.py`: the spoken script, grammar lint, repeated card, words one sound from another, words spelled in no source, colour the source lacks. In `--strict`, unsupported colour is a failing warning, as are an unfinished support sentence, a long card without a breath, promotional filler and gratuitous graphic detail; the check names the wording and never rewrites it.
`render`: voice-clip ratio (extra/missing words), a syllable said twice (cut out), clip loudness (0.1 dB spread), **audio-to-picture offset** of every
clip (warn above 40 ms, fail above 120 ms), the follow button pressed on the word, effects over speech, a reel made from older wording.
`scripts/dispatch.py`: the desks that must have read the *current* wording — fact, Kannada, newsreader, legal, reach. `scripts/regate.py` re-reads
the gate in seconds.

## 5a. The look and the master (D148)

* The fact is read on a **paper** card in ink; the word being said sits on gold. Gold is the brand's: the count, the counter, the town, the follow button. Never a gold slab under news, never red on the format's name.
* The finished `.mp4` is measured, not the mix: its true peak must be at or under `Limits.true_peak_dbtp`. The render corrects it and writes `true_peak` in the report — read it there.

## 5b. The ear (D146) — what hears the voice back, and what holds the reel

`brand/ear.py` listens to every clip with a model that can read Kannada, **blind**, and compares it **word by word** with what the reel means to say. Whisper is kept, but it cannot read
Kannada and is the weaker ear. **SND-09 (fail)** holds the package when a word was heard NOT to be said: a town missing or changed, a card's first word cut, a clip carrying the next clip's words.
Before it holds, the clip is put right: re-cut at the recording's other silences (free), then a new take with the failing word spelled another way (a voice request each, `Limits.ear_takes`).

* **A town the voice cannot say** is listed in `assets/voice/towns.json` (ವಂಡ್ಸೆ, ಯಡ್ತರೆ — measured). It is kept out of the opening line; its dateline is a recorded clip a person has approved
  (`python3 scripts/town_clips.py add TOWN recording.m4a --made-with "…"`, listen, then `approve TOWN --by "<name the editor gives>"`). With no approved clip the reel is held and says so. Never approve in a name you were not given.
* **Write names the voice can say.** Initials as `ಪಿ.ಎಸ್` are read as letters now; an office written as bare letters (`ಎಸಿ`, `ಡಿಸಿ`) is read as a word — prefer the full title (ಉಪವಿಭಾಗಾಧಿಕಾರಿ) when it fits.
* **Allowance.** Each Gemini audio model has 20 requests a day per key, each voice model 10, both reset at **12:30 IST**. Make the reel after 12:30 IST when you can. If the gate says only Whisper listened, say so to the editor.
* A word the gate lists as "listen for" (SND-09 warn) was heard, but not cleanly: it is where the editor's one listen goes. **Never a name** — a name heard not cleanly fails (D147).

## 5c. Names (D147) — a town is proved before it is left to the voice

Two reels went out after D146 with a name said wrong (2026-10-31, 2026-11-01). So, for every town, place and name in the gazetteer (`assets/voice/towns.json`, every town in `copy.PLACE_TAGS` and every dateline):

* **A name is heard by its shape**, not its consonants (`ear.shape`): a vowel put inside a cluster (ಬ್ರ said "ಬರ") is a wrong name; a doubled consonant must be heard doubled by a Kannada-capable ear. Any ear that hears a name wrong fails it.
* **A town is proved or held.** It is left to the voice only once its spelling has been heard right — by a Kannada-capable ear AND Whisper — on each of its last `Limits.town_verify_takes` takes, and never wrong since. Every reel adds its own hearings; a town not proved gets up to that many probe takes in the render; still not proved → **SND-09 fail**. `scripts/reel_check.py` lists the day's unproved towns before the render; prove one ahead with `python3 scripts/town_clips.py verify TOWN` (`--spelling` tries a same-sound respelling, written to `assets/pronunciation.json` only if heard right on every take).
* **No respelling changes the sound.** `brand/lexicon.py` offers only the same sound written another way (a joiner, a nasal written out). Dropping a virama is another word; it is gone.
* **Whisper cannot outvote the ear, and is not enough for a name.** A runaway Whisper transcript (a word repeated three times over) is not a hearing. A name no Kannada-capable ear heard fails (SND-09) — make the reel after 12:30 IST, or add a key.
* **Every take is heard.** A clip re-made by any later step is heard again by the ear before it can ship.

## 6. What no AI can do — say it, never claim otherwise

Nobody on the team can hear audio. The checks narrow the whole reel to the few words and moments where a slip would matter and list them; the editor
listens once. **Never write "the pronunciation is perfect".** Write what was measured and what to listen for.

## 7. Never

Invent a fact, a name, a `verified_by`, or a receipt for a desk that did not run · prepend a spoken direction to the voice · re-render to make a
check pass · edit a check to make a code go away · put a picture on a ಸುದ್ದಿ ಸಾರ story · print or commit a key · render before the copy is final.
