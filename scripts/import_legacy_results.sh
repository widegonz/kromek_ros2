#!/usr/bin/env bash
# Non-destructive data migration: preserve originals.
set -eo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${1:-$HOME/kromek_ws/results}"
DEST="$ROOT/data/legacy_results"
[[ -d "$SRC" ]] || { echo "Nothing to import: $SRC"; exit 0; }
mkdir -p "$DEST"
# -n prevents overwrite; preserving original timestamps. Requires GNU cp (Ubuntu).
cp -an "$SRC/." "$DEST/"
echo "Copied missing files from $SRC into $DEST (originals preserved)."
