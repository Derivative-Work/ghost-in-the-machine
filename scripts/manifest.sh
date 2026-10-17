#!/usr/bin/env bash
# Regenerate MANIFEST.sha256 for every published large file (git-ignored, not inspiration, not regenerable).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
dirs=(audio renders takes reference/stills transcripts archive)
existing=()
for d in "${dirs[@]}"; do [ -d "$d" ] && existing+=("$d"); done
find "${existing[@]}" -type f -print0 \
  | while IFS= read -r -d '' f; do git check-ignore -q "$f" && printf '%s\0' "$f"; done \
  | sort -z | xargs -0 -r sha256sum > MANIFEST.sha256
echo "$(wc -l < MANIFEST.sha256) files in MANIFEST.sha256"
