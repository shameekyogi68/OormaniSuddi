# Second Brain — Trigger Rules

## Activation Triggers

When the user says any of the following, activate the `second-brain` skill:

- `start with content`
- `start`
- `begin`
- `content ready`
- `let's go`
- `produce`
- `start production`
- `begin production`

**What happens on activation:**
1. The user MUST have pasted raw news copy earlier in the conversation (or in the same message)
2. Read and follow `.agents/skills/second-brain/SKILL.md` completely
3. Execute all expert steps in sequence
4. **MANDATORY Stock Image Reuse (Step 3)**:
   - Before generating any new AI image, inspect the stock library in `assets/stock/` and `assets/stock/CATALOG.md`.
   - If an existing generic stock photo matches the story context (e.g. police dog squad, highway traffic, CCTV surveillance, taluk office files, fishing harbour, farmers market), **reuse it directly** with `nature: 'representative'`.
   - **Generate fresh AI images ONLY if no suitable stock image exists.**
5. Loop QA steps until 10/10 quality
6. Present the completed `MASTER_COPY.md` to the user with all generated/reused images and carousel slides displayed in chat.

## Cleanup & Stop Triggers

When the user says any of the following, execute cleanup and stock curation:

- `stop`
- `close`
- `done`
- `cleanup`
- `clear`
- `delete content`
- `clean up`
- `finish`

**What happens on stop/cleanup:**
1. **Evergreen Stock Archival (MANDATORY)**:
   - Inspect `assets/daily/{today's date}/` for any newly generated AI images.
   - Select ONLY those that are truly generic and evergreen for future news stories (usable across any future bulletin regardless of the specific date/incident).
   - Copy them to `assets/stock/` with clean descriptive filenames and update `assets/stock/CATALOG.md`.
2. **Delete Rendered Media**: Delete `out/{today's date}/` directory (all rendered media).
3. **Delete Temporary Daily Images**: Delete remaining non-stock images in `assets/daily/{today's date}/`.
4. **Preserve Assets**: KEEP `editions/{today's date}.json` (editorial record) and `assets/stock/` (evergreen stock library).
5. Confirm completion to the user in Kannada + English.

## Important Reminders

- The Second Brain skill NEVER modifies files in `brand/`, `templates/`, or `render.py`
- Every run uses `render.py` as-is — the design system is finished
- If `render.py --check` fails, fix the INPUT (JSON/copy), never the renderer
- All content for a day goes into the daily folder structure described in the skill
- Edition numbers auto-increment from the last edition in `editions/`
