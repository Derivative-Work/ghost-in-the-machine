#!/usr/bin/env bash
# Render Blender plate jobs from shots/shots.json at per-job sizes from config/render_profiles.json.
# Usage: scripts/render_plates.sh <tier> <profile> <step> [SHOT_ID ... | tiles]   e.g. c5 c5 1 S01 S02
#   No shot IDs: every job, then the S50 thumbnail stills ("tiles"). Frames already on disk are skipped, so a run
#   can be stopped and resumed (or continued on another machine).
set -euo pipefail
tier=$1; profile=$2; step=$3; shift 3
out="$PWD/renders/$tier/plates"
mkdir -p "$out"
# A profile may name its own screen-texture set (e.g. the 2x panels for 4K); plates.py reads it from GITM_PANELS.
panels=$(.venv/bin/python -c "import json;print(json.load(open('config/render_profiles.json'))['$profile'].get('panels',''))")
[ -n "$panels" ] && export GITM_PANELS="$PWD/$panels"
want=" $* "
[ $# -eq 0 ] && want=" ALL tiles "
n=$(.venv/bin/python -c "import json;print(len(json.load(open('shots/shots.json'))['render_jobs']))")
for i in $(seq 0 $((n - 1))); do
  shot=$(.venv/bin/python -c "import json;print(json.load(open('shots/shots.json'))['render_jobs'][$i]['shot'])")
  [[ "$want" == *" ALL "* || "$want" == *" $shot "* ]] || continue
  read -r w h samples < <(.venv/bin/python scripts/job_size.py "$profile" "$i")
  start=$(date +%s)
  blender -b --factory-startup --python scenes/blender/plates.py -- job "$i" "$out" "$w" "$h" "$samples" "$step" \
    2>&1 | grep -E '^JOB|Error|Traceback' || true
  echo "  job $i ($shot ${w}x${h} s$samples) took $(( $(date +%s) - start )) s"
done
if [[ "$want" == *" tiles "* ]]; then
  read -r w h samples < <(.venv/bin/python scripts/job_size.py "$profile" tiles)
  t20=$(.venv/bin/python -c "import json;s=[x for x in json.load(open('shots/shots.json'))['shots'] if x['id']=='S50'][0];print(s['start_s']+2)")
  blender -b --factory-startup --python scenes/blender/plates.py -- tiles "$out/tiles" "$w" "$h" "$samples" "$t20" \
    2>&1 | grep -E '^TILES|Error|Traceback' || true
fi
echo "PLATES DONE: $*"
