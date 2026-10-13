# Running the desks fast — parallelism and token discipline

> How to run this newsroom's agents quickly and cheaply, without losing the
> receipt-per-story trail. The contract is unchanged: **no agent verifies,
> signs, uploads or answers a complaint** (D87, D89, D97). Parallelism never
> touches those.

## The one rule that saves the most tokens

**An agent reads only its own file and `_CONVENTIONS.md`.** Every agent file
in `.claude/agents/` repeats this, because the expensive mistake is an agent
that reads AGENTS.md, DECISIONS.md, the code, and last week's editions to
answer one question about one story. A desk run costs roughly:

| what the agent reads | what it costs |
|---|---|
| its own agent file + `_CONVENTIONS.md` + the stories it was given | the baseline — this is the design |
| + `docs/DECISIONS.md` (140 KB) | several times the baseline, every run |
| + the brand/ engine "to be safe" | the baseline again, and nothing it learns there changes its verdict |

`DECISIONS.md` is ~140 KB of history. Nobody greps it whole:
`grep -n "^## D<number>" docs/DECISIONS.md` and read the one entry.

## Waves, and why they are the unit of parallelism

`python3 scripts/dispatch.py` lists who is due, in **waves**. A wave is a set
of desks that can all run at once because none of them writes what another
reads. Launch each wave as **one message of parallel Agent calls, one per
line** — that is the whole trick:

- **Within a wave** (e.g. the per-story desks: intake-editor, fact-checker,
  kannada-editor … on different stories): fully parallel. Each agent gets
  only its stories, files its own receipt, never sees the others.
- **Between waves**: sequential. The next wave's desks read the receipts the
  previous wave filed, so their answers build on checked copy, not guesses.

Never parallelize across a dependency. The package-inspector runs after the
desks, the gate-doctor after the inspector, sign-off after everything —
because each reads what the one before wrote.

## Batching: one run, several stories

A per-story desk reads up to `Limits.agent_batch_max` stories in **one run**
and still files a receipt per story (D97). Six spawns for six stories reload
the same instructions six times and buy nothing in care — the receipt is
filed per story, against that story's own hash. Batch first; spawn more
agents only when a batch genuinely won't fit in one run.

## What each parallel run must carry

1. **The stories it is responsible for** — pasted or as file paths, never
   "read today's edition and decide".
2. **Its own file path** — `python3 scripts/dispatch.py` says which; do not
   decide from memory (AGENTS.md rule, D97).
3. **Nothing else.** If an agent says it needs to read the engine, the
   templates, or the ledger to do its desk, the task was scoped wrong —
   rescope the task, not the reading list.

## Receipts are the sync primitive

Every desk files a receipt (`brand/dispatch.py :: write_receipt`) stamped
with a **hash of the wording it read**. This is what makes parallelism safe:

- A content edit changes the hash → `desk_gaps` recomputes who is due →
  desks become due again automatically. You never have to remember who read
  the old wording; the machine knows.
- Because the receipt binds to the wording, two desks working in parallel on
  the *same* story version cannot drift apart silently — the inspector
  checks the receipts against the current wording before approval.

So: file the receipt before moving on, and let the gap check, not your
memory, say when a desk is done.

## Cheaper sub-runs inside one agent

- **Grep before reading.** `grep -n` a file for the symbol you need instead
  of reading it whole — DECISIONS.md, review.py and motion.py especially.
- **One render, many checks.** `render.py --still` for a quick draft; never
  re-render to check one change — `--check` validates without pixels.
- **Run the fast suites, not everything.** The pre-commit set (everything
  but golden/animate/formats/speednews) is a few seconds; the full suite
  with golden is minutes. Match the run to the risk.

## What never parallelizes

- **Verification** (`scripts/verify.py --by`): one name, one person, given
  in chat at approval. Never assumed, never batched across editions.
- **Sign-off** (`scripts/sign_off.py`): after every desk, sequential, by a
  person.
- **Archive and discard**: one day at a time, by hand.
- **Money**: business desks propose; a person decides and moves the deal.

## A morning, compressed

1. Editor pastes the news → intake → `dispatch.py` prints wave 1.
2. Launch wave 1 as parallel Agent calls (batched per desk).
3. Wave 2 the same way, then wave 3.
4. `python3 scripts/sign_off.py out/DATE --by "<name>"` — a person, once.
5. `python3 scripts/archive_edition.py DATE` — Stop, later.

The pipeline's gates are code, so going fast never means going around them;
it means never reading what you don't need and never waiting on what doesn't
depend on you.
