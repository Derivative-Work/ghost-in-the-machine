"""C5: cut each review section at full quality as soon as its plates are on disk, with a contact sheet.

For each section in config/c5_sections.json (in order): wait until every plate frame the section reads exists in
renders/c5/plates, then run scripts/assemble.py c5 1920 1080 1 <jobs> --frames A:B --crf 18 --name c5_<section>, and
write renders/c5/sheets/<section>.jpg from each shot's middle frame. Sections already cut are skipped.

Usage: .venv/bin/python scripts/c5_sections.py [section_name ...]   (default: all, in order)
"""
import json
import subprocess
import sys
import time
from pathlib import Path

D = json.loads(Path("shots/shots.json").read_text())
SHOT = {s["id"]: s for s in D["shots"]}
IDS = [s["id"] for s in D["shots"]]
PLATES = Path("renders/c5/plates")
OUT = Path("renders/c5")
SECTIONS = json.loads(Path("config/c5_sections.json").read_text())["sections"]


def shots_in(a, b):
    return D["shots"][IDS.index(a):IDS.index(b) + 1]


def needed(shots):
    """Plate files the section reads: every frame of its shots' jobs, plus the held frame of a freeze's source."""
    files = []
    for s in shots:
        if s["plate"]["mode"] == "hold":
            src = SHOT[s["plate"]["src"]]
            j = next(j for j in D["render_jobs"] if j["shot"] == src["id"] and j["seed"] == src["seed"])
            files.append(PLATES / j["dir"] / f"{min(src['end_frame'], j['end']) - 1:05d}.png")
        for j in D["render_jobs"]:
            if j["shot"] == s["id"]:
                files += [PLATES / j["dir"] / f"{f:05d}.png" for f in range(j["start"], j["end"])]
    return files


def cut(name, a, b):
    shots = shots_in(a, b)
    mp4 = OUT / f"c5_{name}.mp4"
    if mp4.exists():
        print(name, "already cut")
        return
    feed = any(s["id"] in ("S50", "S51", "S52", "S53", "S54", "S55") for s in shots)
    files = needed(shots + ([SHOT["S50"]] if feed else []))
    if feed:  # the feed's still thumbnails, rendered last
        seeds = json.loads(Path("config/seeds.json").read_text())["thumbnail_tiles"]
        files += [PLATES / "tiles" / f"tile_{x}.png" for x in seeds]
    while True:
        missing = [f for f in files if not f.exists()]
        if not missing:
            break
        print(f"{name}: waiting for {len(missing)} plate frames (next {missing[0]})", flush=True)
        time.sleep(120)
    A, B = shots[0]["start_frame"], shots[-1]["end_frame"]
    t0 = time.time()
    subprocess.run([".venv/bin/python", "scripts/assemble.py", "c5", "1920", "1080", "1", "4", "--frames", f"{A}:{B}",
                    "--crf", "18", "--name", f"c5_{name}"], check=True)
    sheets = OUT / "sheets"
    stills = sheets / name
    stills.mkdir(parents=True, exist_ok=True)
    args = []
    for s in shots:
        mid = (s["start_frame"] + s["end_frame"]) // 2
        png = stills / f"{s['id']}_{mid:05d}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp4), "-vf", f"select=eq(n\\,{mid - A})",
                        "-frames:v", "1", "-s", "640x360", str(png)], check=True)
        args.append(f"{s['id']} {mid / D['fps']:.2f}s={png}")
    subprocess.run([".venv/bin/python", "scripts/sheet.py", str(sheets / f"{name}.jpg"), "4", "#000000", *args], check=True)
    print(f"CUT {name}: frames {A}-{B} in {time.time() - t0:.0f} s -> {mp4}", flush=True)


want = sys.argv[1:]
for name, a, b in SECTIONS:
    if not want or name in want:
        cut(name, a, b)
print("SECTIONS DONE")
