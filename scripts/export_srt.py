"""Write the SRT captions deliverable from timing/timing_map.json, with the same line windows as the burned-in
captions in overlays/video.js (a line shows from 0.25 s before its first word until 0.25 s before the next line,
or 1 s after its last word, whichever is first). The text is the lyric as sung, without the on-screen gags.

Usage: .venv/bin/python scripts/export_srt.py  ->  deliverables/ghost_in_the_machine.en.srt
"""
import json
from pathlib import Path

words = json.loads(Path("timing/timing_map.json").read_text())["words"]
lines = []
for w in words:
    if lines and lines[-1]["key"] == (w["section"], w["line"]):
        lines[-1]["words"].append(w)
    else:
        lines.append({"key": (w["section"], w["line"]), "words": [w]})


def stamp(t):
    ms = round(t * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


out = []
for i, l in enumerate(lines):
    start, end = l["words"][0]["start"], l["words"][-1]["end"]
    nxt = lines[i + 1]["words"][0]["start"] if i + 1 < len(lines) else None
    show_to = min(nxt - 0.25, end + 1.0) if nxt is not None else end + 1.0
    text = " ".join(w["text"] for w in l["words"])
    out.append(f"{i + 1}\n{stamp(start - 0.25)} --> {stamp(show_to)}\n{text}\n")
dst = Path("deliverables/ghost_in_the_machine.en.srt")
dst.parent.mkdir(exist_ok=True)
dst.write_text("\n".join(out))
print(dst, len(out), "cues")
