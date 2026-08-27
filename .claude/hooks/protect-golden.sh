#!/usr/bin/env bash
# Refuse a hand-edit of the pinned design hashes.
#
# tests/golden.json is only meaningful if it cannot be edited to make a
# failing test go away. The supported route is:
#
#     python3 -m tests.test_golden --bless
#
# which re-renders into out/_blessed/ so the new design can be LOOKED AT
# before the hashes are accepted. Editing the file by hand skips the looking,
# which is the entire point of the file.
set -uo pipefail

f=$(jq -r '.tool_input.file_path // empty' 2>/dev/null)
case "$f" in
  */tests/golden.json)
    jq -cn '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason:
          "tests/golden.json pins the rendered design and is not hand-edited. If the design changed on purpose, run `python3 -m tests.test_golden --bless`, then LOOK at out/_blessed/ before accepting the new hashes. If it changed by accident, fix the code instead."
      }
    }'
    ;;
esac
exit 0
