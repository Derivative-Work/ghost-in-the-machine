"""Assemble a full-length cut from shots/shots.json: per frame, build the plate (a rendered frame, a held frame for
freezes, an N-up split, or nothing for full-frame JS shots), degrade it where the shot says so, composite the overlay
(overlays/video.html via Puppeteer, rendered in parallel), apply whip/glitch transitions at shot starts, and pipe raw
RGB to ffmpeg with the audio padded to the video's length.

Usage: .venv/bin/python scripts/assemble.py <tier> <width> <height> <plate_step> <jobs> [--hud] [--name NAME]
                                            [--composite-only]
  e.g. .venv/bin/python scripts/assemble.py animatic_v2 640 360 2 6 --hud --name animatic_v2
Reads renders/<tier>/plates (scripts/render_plates.sh); writes renders/<tier>/overlay/ and renders/<tier>/<name>.mp4.
"""
import io
import json
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image

tier, W, H, STEP, JOBS = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
HUD = "--hud" in sys.argv
NAME = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else tier
D = json.loads(Path("shots/shots.json").read_text())
FPS = D["fps"]
SHOTS = D["shots"]
SHOT = {s["id"]: s for s in SHOTS}
ROOT = Path("renders") / tier
PLATES = ROOT / "plates"
OVL = ROOT / "overlay"
BASE = (9, 8, 11)
DOWNBEATS = json.loads(Path("timing/timing_map.json").read_text())["downbeats"]
ZOOM_FRAMES = 8


def shot_at(f):
    return next(s for s in SHOTS if s["start_frame"] <= f < s["end_frame"])


def job_for(shot_id, seed):
    return next(j for j in D["render_jobs"] if j["shot"] == shot_id and j["seed"] == seed)


def rendered(job, f):
    """The rendered frame at or before f on the job's step grid (the animatic renders every STEP-th frame)."""
    s0 = job["start"] + job["lag_frames"]
    first = s0 - (s0 - job["start"]) // STEP * STEP          # first frame on the grid inside the job
    last = s0 + (job["end"] - 1 - s0) // STEP * STEP          # last frame on the grid inside the job
    g = min(max(s0 + (f - s0) // STEP * STEP, first), last)
    return PLATES / job["dir"] / f"{g:05d}.png"


@lru_cache(maxsize=64)
def load(path):
    return Image.open(path).convert("RGB").resize((W, H))


def base():
    return Image.new("RGB", (W, H), BASE)


def split(s, f):
    p = s["plate"]
    seeds = p["seeds"]
    lag = round(p["lag_s"] * FPS)
    frames = []
    for i, seed in enumerate(seeds):
        j = job_for(s["id"], seed)
        frames.append(load(rendered(j, max(j["start"], min(j["end"] - 1, f - lag * i)))))
    img = base()
    if len(seeds) == 2:  # side by side, each the centre half of its frame
        for i, fr in enumerate(frames):
            img.paste(fr.crop((W // 4, 0, W // 4 + W // 2, H)), (i * W // 2, 0))
        img.paste(Image.new("RGB", (max(2, W // 320), H), BASE), (W // 2 - max(1, W // 640), 0))
    else:
        n = round(len(seeds) ** 0.5)
        tw, th = W // n, H // n
        for i, fr in enumerate(frames):
            img.paste(fr.resize((tw - 2, th - 2)), ((i % n) * tw + 1, (i // n) * th + 1))
    return img


def plate(f, s=None):
    s = s or shot_at(f)
    p = s["plate"]
    if p["mode"] == "render":
        if p.get("freeze_first") and f == s["start_frame"]:
            return plate(f - 1)
        j = job_for(s["id"], s["seed"])
        return load(rendered(j, f)) if f < j["end"] else base()
    if p["mode"] == "hold":
        src = SHOT[p["src"]]
        return plate(src["end_frame"] - 1, src)
    if p["mode"] == "split":
        return split(s, f)
    if p["mode"] == "feedlive":  # S53: the feed's own live tile (this video, dancing in the river) as a full frame
        return load(rendered(job_for("S50", "main"), f))
    if p["mode"] == "montage":
        i = next(i for i, (a, b) in enumerate(p["segments"]) if a <= f < b)
        return load(rendered(job_for(s["id"], p["seeds"][i]), f))
    return base()


def punch(img, f):
    """v3: the camera punches in ~4% on every downbeat and eases back."""
    t = f / FPS
    prior = [d for d in DOWNBEATS if d <= t]
    if not prior:
        return img
    k = 0.04 * np.exp(-(t - prior[-1]) / 0.22)
    if k < 0.002:
        return img
    w, h = img.size
    cw, ch = int(w / (1 + k)), int(h / (1 + k))
    x0, y0 = (w - cw) // 2, (h - ch) // 2
    return img.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.BILINEAR)


def zoom_about(img, scale, px, py):
    """Scale an image about a point given as fractions of its size, keeping the frame size."""
    w, h = img.size
    cw, ch = w / scale, h / scale
    x0 = min(max(px * w - cw * px, 0), w - cw)
    y0 = min(max(py * h - ch * py, 0), h - ch)
    return img.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((w, h), Image.BILINEAR)


def degrade(img, k, f):
    """Regeneration loss: lower resolution, compression blocks, a drift toward magenta. k in 0..1."""
    w, h = img.size
    small = img.resize((max(16, int(w * (1 - 0.7 * k))), max(9, int(h * (1 - 0.7 * k)))), Image.BILINEAR)
    buf = io.BytesIO()
    small.save(buf, "JPEG", quality=max(4, int(40 - 36 * k)))
    img = Image.open(buf).convert("RGB").resize((w, h), Image.NEAREST)
    a = np.asarray(img).astype(np.float32)
    a[..., 0] *= 1 + 0.18 * k
    a[..., 2] *= 1 + 0.08 * k
    a[..., 1] *= 1 - 0.12 * k
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def transition(img, s, f):
    i = f - s["start_frame"]
    a = np.asarray(img).astype(np.float32)
    if s["transition"] == "whip" and i < 6:
        k = 1 - i / 6  # horizontal motion smear that settles over 6 frames
        shift = int(W * 0.08 * k) + 1
        acc = np.zeros_like(a)
        n = 8
        for j in range(n):
            acc += np.roll(a, int(shift * j / n) - shift // 2, axis=1)
        a = acc / n
    elif s["transition"] == "glitch" and i < 4:
        d = max(2, W // 100) * (4 - i)
        a[..., 0] = np.roll(a[..., 0], d, axis=1)
        a[..., 2] = np.roll(a[..., 2], -d, axis=1)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def composite_image(f):
    s = shot_at(f)
    img = plate(f, s)
    if s["plate"]["mode"] in ("render", "split", "montage", "feedlive"):
        img = punch(img, f)
    if s["plate"]["mode"] == "split" and len(s["plate"]["seeds"]) > 2 and f - s["start_frame"] < ZOOM_FRAMES:
        # The 4-up and 9-up land like a further zoom out: they start slightly enlarged and settle.
        k = (f - s["start_frame"]) / ZOOM_FRAMES
        img = zoom_about(img, 1 + 0.35 * (1 - k) ** 2, 0.5, 0.5)
    if s["degrade"]:
        img = degrade(img, s["degrade"], f)
    ovl = Image.open(OVL / f"{f:05d}.png").convert("RGBA")
    if ovl.size != (W, H):
        ovl = ovl.resize((W, H))
    out = Image.alpha_composite(img.convert("RGBA"), ovl).convert("RGB")
    if s["transition"]:
        out = transition(out, s, f)
    if s["plate"]["mode"] == "montage":  # each re-roll lands with a short glitch
        for a, _ in s["plate"]["segments"][1:]:
            if 0 <= f - a < 3:
                out = transition(out, dict(s, transition="glitch", start_frame=a - 1), f)
    return out


def frame(f):
    s = shot_at(f)
    out = composite_image(f)
    # Zoom-through: the outgoing shot dives into a point (a screen); the next shot grows out of it.
    if s.get("zoom_out") and f >= s["end_frame"] - ZOOM_FRAMES:
        k = (f - (s["end_frame"] - ZOOM_FRAMES)) / ZOOM_FRAMES
        out = zoom_about(out, 1 + 2.5 * k * k, *s["zoom_out"])
    idx = SHOTS.index(s)
    prev = SHOTS[idx - 1] if idx else None
    if prev and prev.get("zoom_out") and f < s["start_frame"] + ZOOM_FRAMES:
        k = (f - s["start_frame"] + 1) / ZOOM_FRAMES
        bg = zoom_about(composite_image(prev["end_frame"] - 1), 3.5, *prev["zoom_out"])
        sc = 0.25 + 0.75 * (1 - (1 - k) ** 2)
        fg = out.resize((max(2, int(W * sc)), max(2, int(H * sc))), Image.BILINEAR)
        px, py = prev["zoom_out"]
        x = int(px * W - fg.width * px)
        y = int(py * H - fg.height * py)
        bg.paste(fg, (x, y))
        out = bg
    return out.tobytes()


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


def composite():
    """Composite in Python and pipe raw RGB to ffmpeg: PNGs from Blender (gAMA chunk), PIL and Chrome (RGB when
    opaque) differ in format, and fed to ffmpeg directly each change reinits its filter graph and drops frames."""
    out = ROOT / f"{NAME}.mp4"
    tm = json.loads(Path("timing/timing_map.json").read_text())
    ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-i", tm["audio"]["file"],
                           # Pad the audio with silence to the video's exact length (the ending runs past the track).
                           "-filter_complex", f"[1]apad=pad_dur={D['total_s'] - tm['audio']['duration_s']:.3f}[a]",
                           "-map", "0:v", "-map", "[a]", "-t", str(D["total_s"]),
                           "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", str(out)], stdin=subprocess.PIPE)
    with Pool(JOBS) as pool:
        for buf in pool.imap(frame, range(D["total_frames"]), chunksize=16):
            ff.stdin.write(buf)
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError("ffmpeg failed")
    print(out)


if __name__ == "__main__":
    if "--composite-only" not in sys.argv:
        render_overlay()
    composite()
