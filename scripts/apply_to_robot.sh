#!/usr/bin/env bash
# Run FROM an extracted release directory, not from live ~/kromek_ros2 checkout.
set -eo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DST="${1:-$HOME/kromek_ros2}"
[[ "$SRC" != "$DST" ]] || { echo 'Already in target; no update needed.'; exit 0; }
[[ -d "$DST/src/kromek_driver" && -d "$DST/src/kromek_interfaces" ]] || { echo "Unexpected target repository: $DST" >&2; exit 1; }
if pgrep -f '/kromek_ros2/(build|install)/kromek_driver.*sigma50_node' >/dev/null; then
  echo 'Stop running Kromek driver before updating!' >&2; exit 1
fi
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="$DST/.backups/pre_rc1_$STAMP"
mkdir -p "$BACKUP"
for name in src scripts tests docs README.md .gitignore; do
    if [[ -e "$DST/$name" ]]; then cp -a "$DST/$name" "$BACKUP/"; fi
done
for name in src scripts tests docs systemd README.md .gitignore; do
    if [[ -d "$SRC/$name" ]]; then
        mkdir -p "$DST/$name"
        cp -a "$SRC/$name/." "$DST/$name/"
    elif [[ -f "$SRC/$name" ]]; then
        cp -a "$SRC/$name" "$DST/$name"
    fi
done
# NEVER touch vendor/, data/, build/, install/, log/ or system-installed files.
echo "Updated source/scripts; backup at $BACKUP"
echo 'Run: python3 -m unittest discover -s tests -v && ./scripts/build_ros.sh'
