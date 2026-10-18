#!/usr/bin/env bash
# Render the first frame of a few C5 plate jobs on this machine and compare them with the plates already in
# renders/c5/plates (rendered on the GTX 970), so a new GPU's differences are measured before its plates are mixed in.
# Usage: scripts/gpu_parity.sh [SHOT_ID ...]   (default: S07 S27 S25, i.e. robot glow, stream, cloud + rays)
# Only shots that read no other plates: video_tiles (S50, S53) and river_screen (S54, S55) read frames from the
# output directory, which is empty here, so they render blank screens. Compare those from a full run instead.
set -euo pipefail
shots=${*:-S07 S27 S25}
out="$PWD/renders/parity/$(hostname)"
mkdir -p "$out"
for shot in $shots; do
  read -r i dir start < <(.venv/bin/python -c "
import json;J=json.load(open('shots/shots.json'))['render_jobs']
i=next(i for i,j in enumerate(J) if j['shot']=='$shot');print(i,J[i]['dir'],J[i]['start'])")
  read -r w h samples < <(.venv/bin/python scripts/job_size.py c5 "$i")
  # A step longer than any job renders only its first frame.
  blender -b --factory-startup --python scenes/blender/plates.py -- job "$i" "$out" "$w" "$h" "$samples" 100000 \
    2>&1 | grep -E '^JOB|Error|Traceback' || true
  f=$(printf %05d "$start")
  .venv/bin/python -c "
import numpy as np; from PIL import Image
a=np.asarray(Image.open('$out/$dir/$f.png').convert('RGB'),dtype=int); b=np.asarray(Image.open('renders/c5/plates/$dir/$f.png').convert('RGB'),dtype=int)
d=np.abs(a-b); print('$shot $dir f$f: mean |diff| %.3f, max %d, pixels differing %.2f%%' % (d.mean(), d.max(), 100*(d.max(2)>0).mean()))"
done
