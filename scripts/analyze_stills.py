"""Measure the inspiration videos from their extracted stills, for style/style_spec.md.

Per video: overall palette and accent (saturated) palette by k-means over the 5-second stills, brightness and
saturation stats, and shot pacing from the scene-change times. Then the same palettes pooled across all five
videos (each video weighted equally) as the starting point for the averaged look. Also writes contact sheets.

Usage: .venv/bin/python scripts/analyze_stills.py  ->  style/measurements.json, reference/stills/<slug>/contact_*.jpg
"""
import colorsys
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

SEED = 41  # analysis seed; matches the main video seed so reruns are identical
STILLS = Path("reference/stills")
VIDEOS = {
    "accept-all": "Accept All - Claude Opus 5.5 Music Video ｜ HEADLINER [eXqCFsJS6XE].webm",
    "end-of-the-show": "I made a Music Video with Claude about AI TAKING OVER ｜ The End Of The Show [tKrVYOUvrtA].webm",
    "lgtm": "LGTM (Looks Good to Me) - Claude Opus 5.5 music video [3TNpOD6bov8].webm",
    "not-my-fault": "Not My Fault — the AI's music video about your vague prompts [_e6D4ccRuSA].webm",
    "run-it-again": "Run It Again - Claude Opus 5.5 Music Video [NgRkyAIJx5s].webm",
}
PIXELS_PER_FRAME = 4000


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    s = info["streams"][0]
    num, den = map(int, s["r_frame_rate"].split("/"))
    return {"width": s["width"], "height": s["height"], "fps": round(num / den, 3),
            "duration_s": float(info["format"]["duration"])}


def sample_pixels(frames, rng):
    chunks = []
    for f in frames:
        px = np.asarray(Image.open(f).convert("RGB").resize((320, 180))).reshape(-1, 3)
        chunks.append(px[rng.choice(len(px), PIXELS_PER_FRAME, replace=False)])
    return np.concatenate(chunks).astype(np.float32) / 255.0


def hsv(px):
    return np.array([colorsys.rgb_to_hsv(*p) for p in px])


def palette(px, k):
    km = KMeans(n_clusters=k, n_init=4, random_state=SEED).fit(px)
    counts = np.bincount(km.labels_, minlength=k) / len(px)
    order = np.argsort(-counts)
    return [{"hex": "#%02x%02x%02x" % tuple(int(round(c * 255)) for c in km.cluster_centers_[i]),
             "share": round(float(counts[i]), 3)} for i in order]


def accents(px, hsv_px, k):
    # Saturated, reasonably bright pixels: the neon/brand colors that sit on top of the dark base.
    mask = (hsv_px[:, 1] > 0.5) & (hsv_px[:, 2] > 0.35)
    if mask.sum() < k * 50:
        return [], float(mask.mean())
    return palette(px[mask], k), round(float(mask.mean()), 3)


def contact_sheet(frames, out, cols=8, width=240):
    thumbs = [Image.open(f).convert("RGB").resize((width, width * 9 // 16)) for f in frames]
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * width, rows * width * 9 // 16), "black")
    for i, t in enumerate(thumbs):
        sheet.paste(t, ((i % cols) * width, (i // cols) * width * 9 // 16))
    sheet.save(out, quality=85)


def main():
    rng = np.random.default_rng(SEED)
    results, pooled, pooled_hsv = {}, [], []
    for slug, name in VIDEOS.items():
        d = STILLS / slug
        frames = sorted((d / "every5s").glob("*.jpg"))
        scenes = sorted((d / "scene").glob("*.jpg"))
        meta = probe(Path("reference/inspiration") / name)
        px = sample_pixels(frames, rng)
        h = hsv(px)
        acc, acc_share = accents(px, h, 6)
        n_shots = len(scenes) + 1
        results[slug] = {
            **meta,
            "stills_every5s": len(frames),
            "scene_changes": len(scenes),
            "avg_shot_length_s": round(meta["duration_s"] / n_shots, 2),
            "mean_brightness": round(float(h[:, 2].mean()), 3),
            "dark_fraction": round(float((h[:, 2] < 0.15).mean()), 3),
            "mean_saturation": round(float(h[:, 1].mean()), 3),
            "accent_fraction": acc_share,
            "palette": palette(px, 8),
            "accents": acc,
        }
        # Equal weight per video in the pooled palette regardless of length.
        idx = rng.choice(len(px), 60000, replace=len(px) < 60000)
        pooled.append(px[idx])
        pooled_hsv.append(h[idx])
        contact_sheet(frames, d / "contact_every5s.jpg")
        contact_sheet(scenes[:96], d / "contact_scene.jpg")
        print(slug, results[slug]["avg_shot_length_s"], "s/shot,", len(frames), "stills")
    px, h = np.concatenate(pooled), np.concatenate(pooled_hsv)
    acc, acc_share = accents(px, h, 8)
    results["_pooled"] = {
        "note": "All five videos, equal weight per video.",
        "mean_brightness": round(float(h[:, 2].mean()), 3),
        "dark_fraction": round(float((h[:, 2] < 0.15).mean()), 3),
        "mean_saturation": round(float(h[:, 1].mean()), 3),
        "accent_fraction": acc_share,
        "avg_shot_length_s": round(float(np.mean([r["avg_shot_length_s"] for r in results.values()])), 2),
        "palette": palette(px, 8),
        "accents": acc,
    }
    Path("style").mkdir(exist_ok=True)
    Path("style/measurements.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
