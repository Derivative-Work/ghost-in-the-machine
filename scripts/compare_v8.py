"""C5 review aid: a sheet pairing a section cut with the approved animatic (v8) at 25% and 75% of every shot,
C5 on the left of each pair.

Usage: .venv/bin/python scripts/compare_v8.py <cut.mp4> <first_global_frame> <last_global_frame> <out.jpg>
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

cut, F0, F1, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
D = json.loads(Path("shots/shots.json").read_text())
V8 = "renders/animatic_v8/animatic_v8.mp4"
tmp = Path(tempfile.mkdtemp())


def grab(src, t):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.4f}", "-i", src, "-frames:v", "1", "-s", "480x270",
                    str(tmp / "g.png")], check=True)
    return Image.open(tmp / "g.png").copy()


pairs = []
for s in D["shots"]:
    if F0 <= s["start_frame"] < F1:
        for frac in (0.25, 0.75):
            f = int(s["start_frame"] + (s["end_frame"] - s["start_frame"]) * frac)
            pairs.append((grab(cut, (f - F0) / D["fps"]), grab(V8, f / D["fps"])))
sheet = Image.new("RGB", (1920, 270 * ((len(pairs) + 1) // 2)))
for i, (a, b) in enumerate(pairs):
    x, y = (i % 2) * 960, (i // 2) * 270
    sheet.paste(a, (x, y))
    sheet.paste(b, (x + 480, y))
sheet.save(out, quality=85)
print(out, len(pairs), "pairs")
