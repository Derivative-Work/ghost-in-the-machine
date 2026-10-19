"""Write reference/stills.tsv: for every reference still (scripts/extract_stills.sh), the inspiration video and the
time in it the still was taken from. The stills themselves are not published (they are other creators' frames);
this index says where each one came from, so anyone with the videos can find or re-extract it.

Scene stills take the exact pts_time ffmpeg logged (scene_times.txt); interval stills are on the 5 s grid
(fps=1/5 picks the frame nearest each multiple of 5 s).

Usage: .venv/bin/python scripts/stills_index.py
"""
import hashlib
from pathlib import Path

VIDEOS = {  # slug -> YouTube ID (reference/inspiration.md)
    "accept-all": "eXqCFsJS6XE",
    "end-of-the-show": "tKrVYOUvrtA",
    "lgtm": "3TNpOD6bov8",
    "not-my-fault": "_e6D4ccRuSA",
    "run-it-again": "NgRkyAIJx5s",
}

rows = []
for slug, vid in VIDEOS.items():
    d = Path("reference/stills") / slug
    times = [float(x) for x in (d / "scene_times.txt").read_text().split()]
    stills = [("scene", p, times[i]) for i, p in enumerate(sorted((d / "scene").glob("*.jpg")))]
    stills += [("every5s", p, 5.0 * i) for i, p in enumerate(sorted((d / "every5s").glob("*.jpg")))]
    for kind, p, t in stills:
        rows.append((p, hashlib.sha256(p.read_bytes()).hexdigest(), vid, kind, t))

with open("reference/stills.tsv", "w") as f:
    f.write("# Reference stills (not published): the inspiration video and time each was taken from.\n"
            "file\tsha256\tyoutube_id\tkind\ttime_s\turl\n")
    for p, h, vid, kind, t in rows:
        f.write(f"{p}\t{h}\t{vid}\t{kind}\t{t:.3f}\thttps://www.youtube.com/watch?v={vid}&t={int(t)}s\n")
print(f"reference/stills.tsv: {len(rows)} stills")
