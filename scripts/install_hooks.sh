#!/bin/bash
# Install the git hooks. Run once per checkout.
#
#   bash scripts/install_hooks.sh
#   bash scripts/install_hooks.sh --remove
#
# Hooks are not cloned with a repo, so this has to be a deliberate step on any
# machine the newsroom is rebuilt on. scripts/hooks/ is the version-controlled
# source; .git/hooks/ is the copy git actually runs.

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/scripts/hooks"
DST="$ROOT/.git/hooks"

if [ "${1:-}" = "--remove" ]; then
  rm -f "$DST/pre-commit"
  echo "✓ hooks removed"
  exit 0
fi

mkdir -p "$DST"
for h in "$SRC"/*; do
  name="$(basename "$h")"
  cp "$h" "$DST/$name"
  chmod +x "$DST/$name"
  echo "✓ $name"
done
echo
echo "  The contract and the fast suites now run before every commit (~4s)."
echo "  The golden design test does not — it takes two minutes and belongs in"
echo "  a deliberate run. CI covers the rest."
