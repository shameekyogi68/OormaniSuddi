#!/bin/bash
# ಊರ್ಮನಿ ಸುದ್ದಿ — three copies, two media, one offsite.
#
#   bash scripts/backup.sh              back up now
#   bash scripts/backup.sh --status     when did each copy last happen
#   bash scripts/backup.sh --install    run it nightly at 22:30 via launchd
#
# Git covers everything it can: the code, the fonts, the licensed beds, the
# editions. Pushing is the offsite copy of all of that.
#
# This script covers the ONE thing git deliberately does not:
#
#   archive/    the published record — every edition as it went out, its
#               APPROVAL.md and SIGNOFF.json, the copy, the corrections ledger,
#               the metrics database, the calendar state. If a complaint
#               arrives in March about something published in November, this is
#               the only evidence that exists, and under IT Rules 2021 that is
#               not a thing to shrug at.
#
# The default backup is therefore SMALL — archive/ and the couple of registers
# that live outside it. That matters: an earlier version tarred 80 MB every
# night, 79 MB of which was already on GitHub, onto a disk that is 90% full.
#
#   --full   everything, including assets/ and fonts/ — a bare-metal restore
#            image for a new machine. Run it to an external drive when you have
#            one, not nightly.
#
# NOT backed up, on purpose: .env and .gemini_key. Putting live API keys in a
# tarball that syncs to a cloud folder trades a small risk for a larger one,
# and both keys can be reissued from the Google Cloud console in two minutes.
# Losing them costs a morning; leaking them costs more.
#
# Layout (D112):
#
#   .backups/record/<day>.tar.gz   each archive/<day>/ — and any big file in
#                                  archive/ — tarred ONCE, re-tarred only if it
#                                  changes. The published record costs its own
#                                  size, not a copy of itself every night.
#   .backups/oormani-<date>.tar.gz the small registers — pasted sources, the
#                                  calendar, archive/'s loose ledgers — every
#                                  night, the newest KEEP kept.
#   .backups/oormani-full-*.tar.gz --full images, the newest 3 kept.
#
# The second copy mirrors the same layout and is pruned the same way.
#
# Restore the record:   for f in .backups/record/*.tar.gz; do tar -xzf "$f"; done
# Restore the registers: tar -xzf "$(ls -t .backups/oormani-2*.tar.gz | head -1)"
#
# Deliberately dumb: tar and cp. Nothing to keep alive, no account, no service.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

LOCAL="${OORMANI_BACKUP_LOCAL:-$ROOT/.backups}"
STAMP="$(date +%Y-%m-%d)"
KEEP=14                    # daily archives to retain locally

# Where the second copy goes.
#
# An explicit OORMANI_BACKUP_DIR always wins — that is how you point this at an
# external drive. With nothing set, it falls back to iCloud Drive if the folder
# exists, because a backup that depends on somebody having exported a variable
# in the right shell is a backup that silently stops the day they open a new
# terminal. launchd does not read a shell profile at all, so the nightly job
# would have been the first thing to lose it.
ICLOUD="$HOME/Library/Mobile Documents/com~apple~CloudDocs/OormaniSuddi"
EXTERNAL="${OORMANI_BACKUP_DIR:-}"
EXTERNAL_IS_ICLOUD=0
if [ -z "$EXTERNAL" ] && [ -d "$(dirname "$ICLOUD")" ]; then
  EXTERNAL="$ICLOUD"
  EXTERNAL_IS_ICLOUD=1
  mkdir -p "$EXTERNAL" 2>/dev/null
fi

notify() {
  [ -n "${OORMANI_BACKUP_QUIET:-}" ] && return 0
  /usr/bin/osascript -e "display notification \"$2\" with title \"ಊರ್ಮನಿ ಸುದ್ದಿ\" subtitle \"$1\"" 2>/dev/null || true
}

case "${1:-run}" in
  --status)
    echo
    echo "  git         $(git -C "$ROOT" log -1 --format='%h %cr' 2>/dev/null || echo 'no commits')"
    REMOTE_STATE="$(git -C "$ROOT" rev-list --count '@{upstream}..HEAD' 2>/dev/null)"
    if [ -n "$REMOTE_STATE" ]; then
      [ "$REMOTE_STATE" = "0" ] && echo "  offsite     pushed, up to date" \
                                || echo "  offsite     ⚠️  $REMOTE_STATE commit(s) NOT pushed"
    else
      echo "  offsite     ⚠️  no upstream set — 'git push -u origin master'"
    fi
    LAST="$(ls -t "$LOCAL"/oormani-2*.tar.gz 2>/dev/null | head -1)"
    [ -n "$LAST" ] && echo "  local       $(basename "$LAST")  $(du -h "$LAST" | cut -f1)" \
                   || echo "  local       ⚠️  never run"
    echo "  record      $(ls "$LOCAL"/record/*.tar.gz 2>/dev/null | wc -l | tr -d ' ') archived day(s) held once  ($(du -sh "$LOCAL/record" 2>/dev/null | cut -f1))"
    if [ -n "$EXTERNAL" ] && [ -d "$EXTERNAL" ]; then
      LASTX="$(ls -t "$EXTERNAL"/oormani-*.tar.gz 2>/dev/null | head -1)"
      WHICH="$([ "$EXTERNAL_IS_ICLOUD" = "1" ] && echo 'iCloud Drive (default)' || echo "$EXTERNAL")"
      echo "  second      $WHICH"
      [ -n "$LASTX" ] && echo "              $(basename "$LASTX")" \
                      || echo "              ⚠️  never run"
      if [ "$EXTERNAL_IS_ICLOUD" = "1" ]; then
        echo "              ↳ a real external drive is better. Plug one in and:"
        echo "                export OORMANI_BACKUP_DIR=/Volumes/<drive>/OormaniSuddi"
        echo "                bash scripts/backup.sh --full"
      fi
    elif [ -n "$EXTERNAL" ]; then
      echo "  second      ⚠️  $EXTERNAL is not mounted"
    else
      echo "  second      ⚠️  nowhere set and no iCloud — this is one disk"
    fi
    FULLX="$(ls -t "$LOCAL"/oormani-full-*.tar.gz 2>/dev/null | head -1)"
    [ -n "$FULLX" ] && echo "  full image  $(basename "$FULLX")" \
                    || echo "  full image  ⚠️  never run — 'bash scripts/backup.sh --full'"
    echo
    echo "  git holds the code, fonts and beds. This holds archive/ and the"
    echo "  pasted sources — the published record, which git does not carry."
    echo
    exit 0
    ;;
  --install)
    PLIST="$HOME/Library/LaunchAgents/com.oormanisuddi.backup.plist"
    mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/logs"
    cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.oormanisuddi.backup</string>
  <key>ProgramArguments</key><array>
    <string>/bin/bash</string><string>$ROOT/scripts/backup.sh</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>StartCalendarInterval</key><dict>
    <key>Hour</key><integer>22</integer><key>Minute</key><integer>30</integer>
  </dict>
  <key>EnvironmentVariables</key><dict>
    <key>OORMANI_BACKUP_DIR</key><string>$EXTERNAL</string>
  </dict>
  <key>StandardOutPath</key><string>$ROOT/logs/backup.out.log</string>
  <key>StandardErrorPath</key><string>$ROOT/logs/backup.err.log</string>
  <key>ProcessType</key><string>Background</string>
</dict></plist>
PLISTEOF
    launchctl unload "$PLIST" 2>/dev/null
    launchctl load "$PLIST" || exit 1
    echo "✓ nightly backup installed (22:30)"
    echo "  second copy → $EXTERNAL"
    [ "$EXTERNAL_IS_ICLOUD" = "1" ] && \
      echo "  (iCloud Drive, the default. An external drive is better — plug one in, set OORMANI_BACKUP_DIR, and re-run --install.)"
    exit 0
    ;;
esac

mkdir -p "$LOCAL" "$ROOT/logs"

# Keep the newest $3 files in $1 matching $2. One path per line, read whole:
# the project lives under "My Apps", and `ls | xargs rm` split every path at
# that space, so nothing was ever pruned (D112).
prune() {
  local dir="$1" pattern="$2" keep="$3" n=0 f
  while IFS= read -r f; do
    n=$((n + 1))
    [ "$n" -gt "$keep" ] && rm -f -- "$f"
  done < <(ls -t "$dir"/$pattern 2>/dev/null)
}

FULL=0
[ "${1:-}" = "--full" ] && FULL=1

echo "$(date '+%Y-%m-%d %H:%M:%S')  backup ($([ "$FULL" = "1" ] && echo full || echo daily))"

# ── 1a · the published record, one tarball per item, written once ───────────
mkdir -p "$LOCAL/record"
RECORD_NEW=0
if [ -d "$ROOT/archive" ]; then
  for item in "$ROOT"/archive/*; do
    [ -e "$item" ] || continue
    name="$(basename "$item")"
    if [ -f "$item" ] && [ "$(wc -c < "$item")" -lt 1000000 ]; then
      continue                      # a small register — goes in the nightly
    fi
    tgt="$LOCAL/record/$name.tar.gz"
    if [ -f "$tgt" ] && [ -z "$(find "$item" -newer "$tgt" -print -quit)" ]; then
      continue                      # already held, and unchanged since
    fi
    tar -czf "$tgt.part" -C "$ROOT" "archive/$name" 2>/dev/null \
      && mv -f "$tgt.part" "$tgt" && RECORD_NEW=$((RECORD_NEW + 1))
  done
fi
echo "  record    $(ls "$LOCAL"/record/*.tar.gz 2>/dev/null | wc -l | tr -d ' ') item(s), $RECORD_NEW new or changed  ($(du -sh "$LOCAL/record" | cut -f1))"

# ── 1b · the registers, or the full image ────────────────────────────────────
if [ "$FULL" = "1" ]; then
  ARCHIVE="$LOCAL/oormani-full-$STAMP.tar.gz"
  # Everything needed to rebuild on a machine that has never seen this repo,
  # for the case where GitHub is also unreachable.
  CANDIDATES=(archive editions inbox/sources assets/bgm_options
              assets/LICENCES.json assets/pronunciation.json fonts
              brand templates scripts docs tests render.py requirements.txt
              AGENTS.md CLAUDE.md STANDARDS.md)
else
  ARCHIVE="$LOCAL/oormani-$STAMP.tar.gz"
  # Only what git does not have and the record above does not hold.
  CANDIDATES=(inbox/sources editions/greetings/calendar.json)
  for item in "$ROOT"/archive/*; do
    [ -f "$item" ] && [ "$(wc -c < "$item")" -lt 1000000 ] \
      && CANDIDATES+=("archive/$(basename "$item")")
  done
fi

TARGETS=()
for d in "${CANDIDATES[@]}"; do
  [ -e "$ROOT/$d" ] && TARGETS+=("$d")
done

if [ ${#TARGETS[@]} -gt 0 ]; then
  tar -czf "$ARCHIVE" -C "$ROOT" "${TARGETS[@]}" 2>/dev/null
  echo "  local     $(basename "$ARCHIVE")  ($(du -h "$ARCHIVE" | cut -f1))"
else
  ARCHIVE=""
  echo "  local     nothing outside the record to keep yet"
fi

# Prune each kind separately — a full image should outlive a fortnight of
# dailies, and mixing them meant one --full run evicted two weeks of record.
prune "$LOCAL" 'oormani-2*.tar.gz' "$KEEP"
prune "$LOCAL" 'oormani-full-*.tar.gz' 3

# ── 2 · the second medium ────────────────────────────────────────────────────
EXT_OK=0
if [ -n "$EXTERNAL" ] && [ -d "$EXTERNAL" ]; then
  COPIED=1
  mkdir -p "$EXTERNAL/record" || COPIED=0
  for f in "$LOCAL"/record/*.tar.gz; do
    [ -e "$f" ] || continue
    g="$EXTERNAL/record/$(basename "$f")"
    if [ ! -f "$g" ] || [ "$(wc -c < "$f")" != "$(wc -c < "$g")" ]; then
      cp -f "$f" "$g" || COPIED=0
    fi
  done
  if [ -n "$ARCHIVE" ]; then
    cp -f "$ARCHIVE" "$EXTERNAL/" || COPIED=0
  fi
  if [ "$COPIED" = "1" ]; then
    prune "$EXTERNAL" 'oormani-2*.tar.gz' "$KEEP"
    prune "$EXTERNAL" 'oormani-full-*.tar.gz' 3
    [ "$EXTERNAL_IS_ICLOUD" = "1" ] && echo "  second    iCloud Drive" \
                                    || echo "  second    $EXTERNAL"
    EXT_OK=1
  else
    echo "  second    ⚠️  could not write everything to $EXTERNAL"
  fi
else
  [ -n "$EXTERNAL" ] && echo "  second    ⚠️  $EXTERNAL not mounted" \
                     || echo "  second    ⚠️  nowhere to put a second copy"
fi

# ── 3 · offsite ──────────────────────────────────────────────────────────────
# Code only. The published record is not pushed to a remote by this script —
# that is a decision about where the channel's evidence lives, and it should be
# made deliberately rather than by a backup job.
AHEAD="$(git rev-list --count '@{upstream}..HEAD' 2>/dev/null || echo '?')"
if [ "$AHEAD" = "0" ]; then
  echo "  offsite   git up to date"
  GIT_OK=1
elif [ "$AHEAD" = "?" ]; then
  echo "  offsite   ⚠️  no upstream branch set"
  GIT_OK=0
else
  echo "  offsite   ⚠️  $AHEAD commit(s) unpushed — run: git push"
  GIT_OK=0
fi

if [ "$EXT_OK" = "1" ] && [ "$GIT_OK" = "1" ]; then
  echo "  ✓ three copies, two media, one offsite"
else
  echo "  ! this is fewer than three copies. See --status."
  notify "Backup incomplete" "Local copy written. See scripts/backup.sh --status"
fi
