#!/usr/bin/env bash
# Run the genuineness contract after any edit to the engine.
#
# tests.test_contract runs in ~0.002s and covers Story.validate() — the
# criminal-reporting guards, provenance, licensing. Three ways to defeat the
# guilt-assertion guard shipped undetected before this existed; each is now a
# test, and this makes them run the moment the engine is touched rather than
# at the next full render.
#
# Exits 2 on failure so the error is fed straight back instead of being
# discovered later.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-/Users/shameekyogi/Oormani Suddi}"
f=$(jq -r '.tool_input.file_path // .tool_response.filePath // empty' 2>/dev/null)
[ -n "$f" ] || exit 0

case "$f" in
  */brand/*.py|*/templates/*.py) ;;
  *) exit 0 ;;
esac

cd "$ROOT" || exit 0
out=$(python3 -m unittest tests.test_contract 2>&1)
if [ $? -ne 0 ]; then
  printf '%s\n' "$out" >&2
  echo "The genuineness contract FAILED after editing $(basename "$f"). \
These tests encode Indian criminal-reporting law (BNS 356, JJ Act 74, POCSO 23) \
— see docs/DECISIONS.md D29. Fix the code, not the test." >&2
  exit 2
fi
exit 0
