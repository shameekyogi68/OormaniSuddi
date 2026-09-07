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
3. Execute all 8 expert steps in sequence
4. Loop the Final QA step until 10/10 quality
5. Present the completed `MASTER_COPY.md` to the user

## Cleanup Triggers

When the user says any of the following, execute cleanup:

- `close`
- `done`
- `cleanup`
- `clear`
- `delete content`
- `clean up`

**What happens on cleanup:**
1. Delete `out/{today's date}/` directory (all rendered media)
2. Delete `assets/daily/{today's date}/` directory (AI-generated images)
3. KEEP `editions/{today's date}.json` (editorial record — lightweight, no storage concern)
4. Confirm deletion to the user in Kannada + English

## Important Reminders

- The Second Brain skill NEVER modifies files in `brand/`, `templates/`, or `render.py`
- Every run uses `render.py` as-is — the design system is finished
- If `render.py --check` fails, fix the INPUT (JSON/copy), never the renderer
- All content for a day goes into the daily folder structure described in the skill
- Edition numbers auto-increment from the last edition in `editions/`
