# ಸುದ್ದಿ ಸಾರ reel — the quality standard (read before you write or render anything)

The full contract is [`docs/REEL_STANDARD.md`](../../docs/REEL_STANDARD.md). Read it first; this page is only the part that is
easy to get wrong. If the two ever disagree, the standard and the gate (`brand/review.py`, `scripts/reel_check.py`) are right.

1. **Shorten the copy until `python3 scripts/reel_check.py editions/<date>.json --strict` says CLEAN.** NOT CLEAN means the reel will
   be sped up and sound hurried, and the sound effects will crowd the words. Never ignore it; never "fix it in the render".
2. **Every word of `reel_line` / `reel_support` comes from the paste.** TV style is verbs and word order, never added colour
   (ದಾರುಣ, ಭೀಕರ, ತೀವ್ರ, ಸುಸಜ್ಜಿತ, ಯಶಸ್ವಿ …) the paste does not use.
3. **A headline names an event; a card adds a NEW fact.** The town is its own sentence ("ಬೈಂದೂರು. …").
4. **Do not prepend a spoken direction to the voice** ("read like a news anchor …"): the current Gemini models read it aloud or refuse it.
   The voice is Kore on `gemini-2.5-flash-preview-tts`; it is the model and the voice name that matter, not a prompt.
5. **Spend the voice quota once.** Settle the copy and let every desk read it, then render. A re-render after a change asks again for every changed story.
6. **Never say the pronunciation is perfect.** You cannot hear. Report what was measured (`_review/reel_saara_report.json`: `sync.worst_ms`,
   each clip's `ratio`, `voice_engine`) and list what the editor should listen for.
7. Keys live in `.env`; never print or commit one.
