# Inbox

News comes in **pasted**, not scraped (D92). Nothing here is written by a
schedule; nothing here fetches.

1. **Keep the source.** Paste the article (or the press release, or your own
   notes) and keep it as the story's source:

   ```bash
   pbpaste | python3 scripts/intake.py source --url https://… --outlet Udayavani
   pbpaste | python3 scripts/intake.py source            # own reporting / press release
   ```

   With a URL it lands in `sources/<digest>.txt` — the file the fact desk
   (FACT-01, `scripts/fact_check.py`) reads. Without one it lands in
   `sources/own_<digest>.txt`.

2. **Write the edition** — `editions/YYYY-MM-DD.json`, every story with its
   `segment` (`speed`, `saara` or `mukhya`) and its `source_url`.

3. **Check it was not already published:**

   ```bash
   python3 scripts/intake.py seen editions/YYYY-MM-DD.json
   ```

   A story whose source URL ran on an earlier day is refused unless it is a
   real follow-up (`follows_up`, with a new fact).

4. **Check every figure against the pasted text:**

   ```bash
   python3 scripts/fact_check.py editions/YYYY-MM-DD.json
   ```

A person still opens the link and signs `verified_by` (D59).

| folder | what |
|---|---|
| `sources/` | the text of every source, as pasted — the fact desk's evidence |
| `receipts/` | proof kept for a day's claims (screenshots, PDFs) |
| `factcheck/` | optional: `<stem>.json` quotes proving a figure the source spells differently (created by the fact desk when needed) |
