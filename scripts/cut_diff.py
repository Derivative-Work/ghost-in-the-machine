"""C5 review aid: which frames differ between two cuts of the same section (e.g. a re-cut against the archived
cut it replaces), listed with their shot and whether they are a shot's first frame.

Usage: .venv/bin/python scripts/cut_diff.py <new.mp4> <old.mp4> <first_global_frame> [threshold=2.0]
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

new, old, F0 = sys.argv[1], sys.argv[2], int(sys.argv[3])
thr = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
D = json.loads(Path("shots/shots.json").read_text())
w, h = 192, 108


def frames(src):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3).astype(np.int16)


a, b = frames(new), frames(old)
n = min(len(a), len(b))
d = np.abs(a[:n] - b[:n]).mean(axis=(1, 2, 3))
changed = [i for i in range(n) if d[i] > thr]
starts = {s["start_frame"] for s in D["shots"]}
other = []
for i in changed:
    g = F0 + i
    s = next(s for s in D["shots"] if s["start_frame"] <= g < s["end_frame"])
    tag = "first frame" if g in starts else "OTHER"
    if tag == "OTHER":
        other.append(g)
    print(f"f{g} {s['id']} diff {d[i]:.1f} {tag}")
print(f"{len(changed)} changed frames of {n} (lengths {len(a)}/{len(b)}); {len(other)} not at a shot's first frame")
