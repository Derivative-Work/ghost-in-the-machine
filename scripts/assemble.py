"""Assemble a full-length cut: plate sequence (rendered / held / frozen / split per shots.json), overlay frames
(overlays/video.html via Puppeteer, in parallel), then ffmpeg composite + audio.

Usage: .venv/bin/python scripts/assemble.py <tier> <width> <height> <plate_step> <jobs> [--hud] [--name NAME] [--composite-only]
  e.g. .venv/bin/python scripts/assemble.py animatic 640 360 2 6 --hud --name animatic_v1
Reads renders/<tier>/plates (from scripts/render_plates.sh); writes renders/<tier>/{plate_seq,overlay}/ and
renders/<tier>/<name>.mp4.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image

tier, W, H, STEP, JOBS = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
HUD = "--hud" in sys.argv
NAME = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else tier
D = json.loads(Path("shots/shots.json").read_text())
FPS = D["fps"]
SHOT = {s["id"]: s for s in D["shots"]}
ROOT = Path("renders") / tier
PLATES = ROOT / "plates"
SEQ = ROOT / "plate_seq"
OVL = ROOT / "overlay"
SEQ.mkdir(parents=True, exist_ok=True)
BASE = SEQ / "_base.png"
# Every plate frame is RGBA like Blender's PNGs: a pixel-format change mid-sequence makes ffmpeg reinit the
# filter graph and drop frames.
Image.new("RGBA", (W, H), "#09080b").save(BASE)


def job_for(shot_id, plate, seed):
    return next(j for j in D["render_jobs"] if j["shot"] == shot_id and j["plate"] == plate and j["seed"] == seed)


def rendered(job, f):
    g = job["start"] + (f - job["start"]) // STEP * STEP
    return PLATES / f"{job['plate']}__{job['seed']}" / f"{g:05d}.png"


def plate_path(f, shot=None):
    s = shot or next(x for x in D["shots"] if x["start_frame"] <= f < x["end_frame"])
    p = s["plate"]
    mode = p["mode"]
    if mode == "render":
        if p.get("freeze_first") and f == s["start_frame"]:
            return plate_path(f - 1)
        j = job_for(s["id"], p["plate"], s["seed"])
        return rendered(j, f) if f < j["end"] else BASE
    if mode == "hold":
        src = SHOT[p["src"]]
        return plate_path(src["end_frame"] - 1, src)
    if mode == "hold_then":
        if f < round(p["until"] * FPS):
            src = SHOT[p["src"]]
            return plate_path(src["end_frame"] - 1, src)
        return rendered(job_for(s["id"], p["plate"], s["seed"]), f)
    if mode == "split":
        return ("split", s, f)
    return BASE


def split_frame(s, f, out):
    p = s["plate"]
    lag = round(p["lag_s"] * FPS)
    a = Image.open(rendered(job_for(s["id"], p["plate"], p["seeds"][0]), f)).convert("RGBA")
    jb = job_for(s["id"], p["plate"], p["seeds"][1])
    b = Image.open(rendered(jb, max(jb["start"], f - lag))).convert("RGBA")
    w, h = a.size
    img = Image.new("RGBA", (w, h))
    img.paste(a.crop((w // 4, 0, w // 4 + w // 2, h)), (0, 0))
    img.paste(b.crop((w // 4, 0, w // 4 + w // 2, h)), (w // 2, 0))
    img.paste(Image.new("RGBA", (max(2, w // 320), h), "#09080b"), (w // 2 - max(1, w // 640), 0))
    img.save(out)


def build_plate_seq():
    for f in range(D["total_frames"]):
        out = SEQ / f"{f:05d}.png"
        if out.is_symlink() or out.exists():
            out.unlink()
        src = plate_path(f)
        if isinstance(src, tuple):
            split_frame(src[1], src[2], out)
        else:
            if not Path(src).exists():
                raise FileNotFoundError(f"frame {f}: {src}")
            os.symlink(Path(src).resolve(), out)
    print("plate_seq:", D["total_frames"], "frames")


def render_overlay():
    OVL.mkdir(parents=True, exist_ok=True)
    n = D["total_frames"]
    chunk = (n + JOBS - 1) // JOBS
    extra = f"plates=../renders/{tier}/plates" + ("&hud=1" if HUD else "")
    procs = [subprocess.Popen(["node", "scripts/render_frames.mjs", "overlays/video.html", str(OVL), str(a),
                               str(min(n, a + chunk)), "main", str(W), str(H), str(FPS), extra],
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
             for a in range(0, n, chunk)]
    errs = [p.communicate()[1] for p in procs]
    bad = [e for e in errs if "PAGE ERROR" in e]
    if bad or any(p.returncode for p in procs):
        raise RuntimeError("overlay render failed:\n" + "\n".join(e[-2000:] for e in errs))
    print("overlay:", len(list(OVL.glob("*.png"))), "frames")


def composite_frame(f):
    plate = Image.open(SEQ / f"{f:05d}.png").convert("RGBA")
    ovl = Image.open(OVL / f"{f:05d}.png").convert("RGBA")
    return Image.alpha_composite(plate, ovl).convert("RGB").tobytes()


def composite():
    """Alpha-composite plate + overlay in Python and pipe raw RGB to ffmpeg. PNGs from Blender (gAMA chunk), PIL
    and Chrome (RGB when opaque) differ in format; fed to ffmpeg directly, each change reinits its filter graph and
    drops frames."""
    from multiprocessing import Pool
    out = ROOT / f"{NAME}.mp4"
    tm = json.loads(Path("timing/timing_map.json").read_text())
    ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-i", tm["audio"]["file"],
                           # Pad the audio with silence to the video's exact length (S22-S23 run past the track).
                           "-filter_complex", f"[1]apad=pad_dur={D['total_s'] - tm['audio']['duration_s']:.3f}[a]",
                           "-map", "0:v", "-map", "[a]", "-t", str(D["total_s"]),
                           "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", str(out)], stdin=subprocess.PIPE)
    with Pool(JOBS) as pool:
        for buf in pool.imap(composite_frame, range(D["total_frames"]), chunksize=16):
            ff.stdin.write(buf)
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError("ffmpeg failed")
    print(out)


if __name__ == "__main__":
    if "--composite-only" not in sys.argv:
        build_plate_seq()
        if "--plates-only" not in sys.argv:
            render_overlay()
    composite()
