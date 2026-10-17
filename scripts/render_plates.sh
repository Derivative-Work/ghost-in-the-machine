#!/usr/bin/env bash
# Render every Blender plate job in shots/shots.json, then the S20 thumbnail tiles.
# Usage: scripts/render_plates.sh <tier> <width> <height> <samples> <step>   e.g. animatic 640 360 8 2
set -euo pipefail
tier=$1; w=$2; h=$3; samples=$4; step=$5
out="$PWD/renders/$tier/plates"
mkdir -p "$out"
n=$(.venv/bin/python -c "import json;print(len(json.load(open('shots/shots.json'))['render_jobs']))")
for i in $(seq 0 $((n - 1))); do
  start=$(date +%s)
  blender -b --factory-startup --python scenes/blender/plates.py -- job "$i" "$out" "$w" "$h" "$samples" "$step" \
    2>&1 | grep -E '^JOB|Error|Traceback' || true
  echo "  job $i took $(( $(date +%s) - start )) s"
done
t20=$(.venv/bin/python -c "import json;s=[x for x in json.load(open('shots/shots.json'))['shots'] if x['id']=='S20'][0];print(s['start_s']+2)")
blender -b --factory-startup --python scenes/blender/plates.py -- tiles "$out/tiles" $((w / 2)) $((h / 2)) "$samples" "$t20" \
  2>&1 | grep -E '^TILES|Error|Traceback' || true
echo "ALL PLATES DONE"
