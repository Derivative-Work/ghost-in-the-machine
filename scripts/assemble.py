"""Assemble a full-length cut from shots/shots.json: per frame, build the plate (a rendered frame, a held frame for
freezes, an N-up split, or nothing for full-frame JS shots), degrade it where the shot says so, composite the overlay
(overlays/video.html via Puppeteer, rendered in parallel), apply whip/glitch transitions at shot starts, and pipe raw
RGB to ffmpeg with the audio padded to the video's length.
The audio is the mastered take in config/audio.json; the timing map's file is the Suno take it was cleaned from.

Usage: .venv/bin/python scripts/assemble.py <tier> <width> <height> <plate_step> <jobs> [--hud] [--name NAME]
                                            [--composite-only] [--frames A:B] [--crf N]
  e.g. .venv/bin/python scripts/assemble.py animatic_v2 640 360 2 6 --hud --name animatic_v2
Reads renders/<tier>/plates (scripts/render_plates.sh); writes renders/<tier>/overlay/ and renders/<tier>/<name>.mp4.
Plates wider than the output (C5 renders 20% wider for the vertical cut) are cropped to their centre.
--frames A:B cuts only global frames A..B-1 (a section for C5 review), with the matching stretch of audio.
--vertical cuts the 9:16 version (pass W H = 1080 1920; frames default to config/vertical.json's shot range): each
plate is cropped to a 9:16 window centred at the shot's cx, the overlay's scene layers are rendered 16:9 at 1920
tall and cropped the same way, and the UI layers are rendered on the portrait stage. The 2-up split stacks.
--still writes frame A as renders/<tier>/<name>.png instead of a video (the thumbnail).
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
CRF = sys.argv[sys.argv.index("--crf") + 1] if "--crf" in sys.argv else "23"
D = json.loads(Path("shots/shots.json").read_text())
VERT = "--vertical" in sys.argv
VCFG = json.loads(Path("config/vertical.json").read_text())
_full = (0, D["total_frames"])
if VERT:
    _ids = [s["id"] for s in D["shots"]]
    _full = (D["shots"][_ids.index(VCFG["first_shot"])]["start_frame"], D["shots"][_ids.index(VCFG["last_shot"])]["end_frame"])
A, B = (map(int, sys.argv[sys.argv.index("--frames") + 1].split(":")) if "--frames" in sys.argv else _full)
FPS = D["fps"]
SHOTS = D["shots"]
SHOT = {s["id"]: s for s in SHOTS}
ROOT = Path("renders") / tier
PLATES = ROOT / "plates"
OVL = ROOT / "overlay"
OVL_SCENE, OVL_UI = ROOT / "overlay_v_scene", ROOT / "overlay_v_ui"  # the vertical cut's two overlay passes
SW = round(H * 16 / 9)  # vertical: the scene pass's 16:9 width at the output height
BASE = (9, 8, 11)
DOWNBEATS = json.loads(Path("timing/timing_map.json").read_text())["downbeats"]
ZOOM_FRAMES = 8
# Monochrome grain on the 3D plates (sigma in 8-bit levels). Blender's 1-level dither is smoothed away by the encoder,
# which then bands the robot's glows; grain this strong survives -tune grain. Text and UI stay clean.
GRAIN = 1.2


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


def cx_of(f):
    if not VERT:
        return 0.5
    s = shot_at(f)
    cx = VCFG["cx"].get(s["id"], 0.5)
    if isinstance(cx, list):  # pan across the shot
        k = (f - s["start_frame"]) / max(1, s["end_frame"] - s["start_frame"] - 1)
        k = 4 * k ** 3 if k < 0.5 else 1 - (-2 * k + 2) ** 3 / 2
        cx = cx[0] + (cx[1] - cx[0]) * k
    return round(cx, 4)  # rounded so the plate cache still hits


def window(iw, ih, w, h, cx=0.5):
    """The crop box of aspect w:h inside an iw x ih image, centred at cx of the image's centre 16:9 (plates may be
    wider than 16:9: their margin is room to reframe)."""
    cw = min(iw, round(ih * w / h))
    ch = min(ih, round(iw * h / w))
    core = min(iw, round(ih * 16 / 9))
    x0 = (iw - core) / 2 + cx * core - cw / 2
    x0 = min(max(x0, 0), iw - cw)  # fractional: a pan moves smoothly instead of in whole-pixel steps
    return x0, (ih - ch) / 2, x0 + cw, (ih - ch) / 2 + ch


@lru_cache(maxsize=64)
def load(path, size=None, cx=0.5):
    """A plate at `size` (default the output size), cropped to that aspect ratio first (centred at cx)."""
    w, h = size or (W, H)
    img = Image.open(path).convert("RGB")
    return img.resize((w, h), Image.LANCZOS, box=window(img.width, img.height, w, h, cx))


def base():
    return Image.new("RGB", (W, H), BASE)


def split(s, f):
    p = s["plate"]
    seeds = p["seeds"]
    lag = round(p["lag_s"] * FPS)
    n = round(len(seeds) ** 0.5)
    tw, th = W // n, H // n
    frames = []
    for i, seed in enumerate(seeds):
        j = job_for(s["id"], seed)
        # 4-up and 9-up tiles are rendered near their display size; load them straight to it
        frames.append(load(rendered(j, max(j["start"], min(j["end"] - 1, f - lag * i))),
                           None if len(seeds) == 2 else (tw - 2, th - 2)))
    img = base()
    if VERT:
        rows, cols = (2, 1) if len(seeds) == 2 else (n, n)
        tw, th = W // cols, H // rows
        for i, seed in enumerate(seeds):
            j = job_for(s["id"], seed)
            fr = load(rendered(j, max(j["start"], min(j["end"] - 1, f - lag * i))), (tw - 2, th - 2), cx_of(f))
            img.paste(fr, ((i % cols) * tw + 1, (i // cols) * th + 1))
        return img
    if len(seeds) == 2:  # side by side, each the centre half of its frame
        for i, fr in enumerate(frames):
            img.paste(fr.crop((W // 4, 0, W // 4 + W // 2, H)), (i * W // 2, 0))
        img.paste(Image.new("RGB", (max(2, W // 320), H), BASE), (W // 2 - max(1, W // 640), 0))
    else:
        for i, fr in enumerate(frames):
            img.paste(fr, ((i % n) * tw + 1, (i // n) * th + 1))
    return img


def plate(f, s=None):
    s = s or shot_at(f)
    p = s["plate"]
    if p["mode"] == "render":
        if p.get("freeze_first") and f == s["start_frame"]:
            return plate(f - 1)
        j = job_for(s["id"], s["seed"])
        return load(rendered(j, f), None, cx_of(f)) if f < j["end"] else base()
    if p["mode"] == "hold":
        src = SHOT[p["src"]]
        return plate(src["end_frame"] - 1, src)
    if p["mode"] == "split":
        return split(s, f)
    if p["mode"] == "feedlive":  # S53: the feed's own live tile (this video, dancing in the river) as a full frame
        return load(rendered(job_for("S50", "main"), f), None, cx_of(f))
    if p["mode"] == "montage":
        i = next(i for i, (a, b) in enumerate(p["segments"]) if a <= f < b)
        return load(rendered(job_for(s["id"], p["seeds"][i]), f), None, cx_of(f))
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
    cw, ch = w / (1 + k), h / (1 + k)
    x0, y0 = (w - cw) / 2, (h - ch) / 2
    return img.resize((w, h), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))


def zoom_about(img, scale, px, py):
    """Scale an image about a point given as fractions of its size, keeping the frame size. The source box is
    fractional: whole-pixel crops made slow zooms step."""
    w, h = img.size
    cw, ch = w / scale, h / scale
    x0 = min(max(px * w - cw * px, 0), w - cw)
    y0 = min(max(py * h - ch * py, 0), h - ch)
    return img.resize((w, h), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))


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
    elif s["transition"] == "tear" and i < 9:
        # S11: a hard glitch the video "covers up": RGB channels torn apart and horizontal bands jumping sideways.
        rgen = np.random.default_rng(1000 + f)  # deterministic per frame
        d = max(3, W // 60)
        a[..., 0] = np.roll(a[..., 0], d, axis=1)
        a[..., 2] = np.roll(a[..., 2], -d, axis=1)
        for _ in range(6):
            y0 = int(rgen.integers(0, H - 8))
            hgt = int(rgen.integers(4, max(6, H // 12)))
            a[y0:y0 + hgt] = np.roll(a[y0:y0 + hgt], int(rgen.integers(-W // 6, W // 6)), axis=1)
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
    if s["plate"]["mode"] in ("render", "split", "montage", "feedlive", "hold"):
        g = np.random.default_rng(f).normal(0, GRAIN, (img.height, img.width, 1))
        img = Image.fromarray(np.clip(np.asarray(img, dtype=np.float32) + g, 0, 255).round().astype(np.uint8))
    if VERT:
        sc = Image.open(OVL_SCENE / f"{f:05d}.png").convert("RGBA")
        sc = sc.convert("RGBa").resize((W, H), Image.LANCZOS, box=window(sc.width, sc.height, W, H, cx_of(f))).convert("RGBA")
        out = Image.alpha_composite(img.convert("RGBA"), sc)
        ovl = Image.open(OVL_UI / f"{f:05d}.png").convert("RGBA")
        out = Image.alpha_composite(out, ovl if ovl.size == (W, H) else ovl.resize((W, H))).convert("RGB")
    else:
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
    if VERT:
        render_pass(OVL_SCENE, SW, H, "&pass=scene")
        render_pass(OVL_UI, W, H, "&pass=ui&portrait=1")
    else:
        render_pass(OVL, W, H, "")


def render_pass(OVL, W, H, query):
    OVL.mkdir(parents=True, exist_ok=True)
    a0 = max(0, A - 1)  # a zoom-through into frame A also needs the frame before it
    chunk = (B - a0 + JOBS - 1) // JOBS
    extra = f"plates=../renders/{tier}/plates" + ("&hud=1" if HUD else "") + query
    procs = [subprocess.Popen(["node", "scripts/render_frames.mjs", "overlays/video.html", str(OVL), str(a),
                               str(min(B, a + chunk)), "main", str(W), str(H), str(FPS), extra],
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
             for a in range(a0, B, chunk)]
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
    master = json.loads(Path("config/audio.json").read_text())["master"]
    if master["duration_s"] != tm["audio"]["duration_s"] or master["source_sha256"] != tm["audio"]["sha256"]:
        raise RuntimeError("config/audio.json master isn't the timing map's take at its length")
    ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-i", master["file"],
                           # Pad the audio with silence to the video's exact length (the ending runs past the track),
                           # then take the stretch under frames A..B-1.
                           "-filter_complex", f"[1]apad=pad_dur={D['total_s'] - tm['audio']['duration_s']:.3f},"
                                              f"atrim={A / FPS:.6f}:{B / FPS:.6f},asetpts=PTS-STARTPTS[a]",
                           "-map", "0:v", "-map", "[a]", "-t", f"{(B - A) / FPS:.6f}",
                           # BT.709, converted and tagged: untagged, players assume 709 for HD while ffmpeg converted
                           # with 601, shifting the reds toward orange.
                           "-vf", "scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p,"
                                  "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv",
                           "-c:v", "libx264", "-preset", "medium", "-tune", "grain", "-crf", CRF,
                           "-c:a", "aac", "-b:a", "192k", str(out)], stdin=subprocess.PIPE)
    with Pool(JOBS) as pool:
        for buf in pool.imap(frame, range(A, B), chunksize=16):
            ff.stdin.write(buf)
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError("ffmpeg failed")
    print(out)


if __name__ == "__main__":
    if "--still" in sys.argv:
        B = A + 1
    if "--composite-only" not in sys.argv:
        render_overlay()
    if "--still" in sys.argv:
        Image.frombytes("RGB", (W, H), frame(A)).save(ROOT / f"{NAME}.png")
        print(ROOT / f"{NAME}.png")
    else:
        composite()
