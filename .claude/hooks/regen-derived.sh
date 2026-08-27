#!/usr/bin/env bash
# Regenerate the derived files after a source-of-truth edit.
#
# AGENTS.md says registry.json, schemas/*.json and TEMPLATES.md "are derived
# from code so they cannot drift". Nothing enforced that — it was an
# instruction a human had to remember. This makes it true.
#
# Reads the PostToolUse hook payload on stdin; does nothing unless the edited
# file is one the generators actually read.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-/Users/shameekyogi/Oormani Suddi}"
f=$(jq -r '.tool_input.file_path // .tool_response.filePath // empty' 2>/dev/null)
[ -n "$f" ] || exit 0

case "$f" in
  */templates/__init__.py|*/brand/content.py|*/brand/tokens.py) ;;
  *) exit 0 ;;
esac

cd "$ROOT" || exit 0
out=$(python3 -m templates --dump 2>&1 \
   && python3 schemas/_build.py 2>&1 \
   && python3 docs/_build_templates_md.py 2>&1)
rc=$?

if [ $rc -ne 0 ]; then
  printf '%s' "$out" >&2
  echo "regenerating derived files FAILED after editing $(basename "$f")" >&2
  exit 2   # blocking: feed the error back so it gets fixed now
fi

# Only speak up if something actually changed on disk.
if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  changed=$(git -C "$ROOT" status --porcelain -- \
              templates/registry.json schemas docs/TEMPLATES.md 2>/dev/null)
  if [ -n "$changed" ]; then
    jq -cn --arg m "Derived files regenerated after $(basename "$f") — registry.json / schemas / TEMPLATES.md are back in sync." \
       '{systemMessage:$m, suppressOutput:true}'
  fi
fi
exit 0
