"""Find short-lived picture states in a cut (C5 review aid): runs of fewer than MIN frames between two hard changes,
like the 4-frame big "Maybe" at the end of S14. Prints each with its time and the shot it falls in, and writes a
strip of the frames around it for a look. Intended effects (glitch transitions, flickers, re-roll glitches) will
show up too; the point is that nothing short goes unseen.

Usage: .venv/bin/python scripts/flash_check.py <cut.mp4> <first_global_frame> <out_dir> [MIN=8]
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

src, F0, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
MIN = int(sys.argv[4]) if len(sys.argv) > 4 else 8
out.mkdir(parents=True, exist_ok=True)
D = json.loads(Path("shots/shots.json").read_text())
w, h = 160, 90
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                     capture_output=True, check=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))  # d[i]: change from frame i to i+1
thr = max(6.0, np.percentile(d, 99) * 0.6)
hard = np.where(d > thr)[0]
found = []
for a, b in zip(hard, hard[1:]):
    if b - a < MIN:
        found.append((a + 1, b))  # frames a+1..b are the short state
for k, (a, b) in enumerate(found):
    g = F0 + a
    s = next(s for s in D["shots"] if s["start_frame"] <= g < s["end_frame"])
    print(f"{g / D['fps']:7.2f}s  global f{g}-{F0 + b}  ({b - a + 1} frames)  {s['id']}  section t={a / D['fps']:.2f}s")
    lo, hi = max(0, a - 2), min(len(fr), b + 3)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-frames:v", "1",
                    "-vf", f"trim=start_frame={lo}:end_frame={hi},scale=320:180,tile={hi - lo}x1",
                    str(out / f"{k:02d}_{s['id']}_f{g}.png")], check=True)
print(f"{len(found)} short states (threshold {thr:.1f}, MIN {MIN})")
