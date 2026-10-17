"""Pre-production step 5: resolve the brief's shot list against the timing map and record the pipeline per shot.

Each shot starts at an anchor (section start, lyric line start, or a timing-map event). A cut lands on the
downbeat nearest the anchor if one is within half a bar, otherwise 0.1 s before it. A shot ends where the next one
starts. Times are converted to frames at 30 fps (style spec).

Layers, bottom to top: plate (Blender/Eevee render, a held frame, or nothing) -> JS layers (Puppeteer, one page
renders every layer for any frame, transparent PNG) -> ffmpeg composite + audio. Global JS layers (captions,
chrome) run over every shot unless the shot opts out.

Plate modes:
  render       Blender renders `plate` for the shot's frames (animation in global time unless clock="local").
  hold         Every frame is the last plate frame of shot `from` (a freeze).
  hold_then    Hold `from`'s last frame until `until` seconds, then render `plate` (S17).
  split        Render `plate` at two seeds; left half seed A, right half seed B delayed by `lag_s` (S19).
  js           No plate; a JS layer draws the full frame (2D type-led shots, the S20 grid).

Usage: .venv/bin/python shots/build_shots.py  ->  shots/shots.json, shots/pipeline.md
"""
import json
from pathlib import Path

FPS = 30
TM = json.loads(Path("timing/timing_map.json").read_text())
DOWNBEATS = TM["downbeats"]
BAR = 4 * 60 / TM["tempo_bpm"]
END_OF_AUDIO = TM["audio"]["duration_s"]
LAST_WORD_END = TM["words"][-1]["end"]
DROP2_END = next(d["end"] for d in TM["events"]["dropouts"] if "Pre-Chorus 2" in d["sections"])
S22_LEN, S23_LEN = 1.2, 8.0

# Anchors: ("section", name) | ("line", section, line_index) | ("event", key) | ("time", seconds)
SHOTS = [
    dict(id="S01", section="Intro", anchor=("time", 0.0), pipeline="Blender + JS",
         plate=dict(mode="render", plate="default_cube_boot"), layers=[], seed="main",
         notes="Default scene holds until the first downbeat (4.4 s), then the neon world boots. Overlays fade in."),
    dict(id="S02", section="Verse 1", anchor=("section", "Verse 1"), pipeline="Blender",
         plate=dict(mode="render", plate="robot_screens"), layers=[], seed="main",
         notes="Robot on the grid among floating screens. Lines 1-2."),
    dict(id="S03", section="Verse 1", anchor=("line", "Verse 1", 2), pipeline="JS over held plate",
         plate=dict(mode="hold", src="S02"), layers=["accept_banner"], seed="main",
         notes="Accept-all banner over the held S02 frame; cursor clicks on \"agreed\" without pausing."),
    dict(id="S04", section="Verse 1", anchor=("line", "Verse 1", 3), pipeline="Blender + JS",
         plate=dict(mode="render", plate="robot_shrug"), layers=["todo_caption"], seed="main",
         notes="Shrug; caption flashes // TODO: make this part sad."),
    dict(id="S05", section="Bridge 1", anchor=("section", "Bridge 1"), pipeline="Blender + JS",
         plate=dict(mode="render", plate="robot_screens", freeze_first=True), layers=["glitch_flicker"], seed="main",
         notes="One-frame freeze on \"Have\" and a devtools flicker, then the video carries on as if nothing happened."),
    dict(id="S06", section="Bridge 1", anchor=("line", "Bridge 1", 1), pipeline="JS (2D)",
         plate=dict(mode="js"), layers=["bg2d", "icon_strip_fast"], seed="main", big_captions=True,
         notes="Five generic icons whip past like a trailer."),
    dict(id="S07", section="Bridge 1", anchor=("event", "bridge1_beat_gap"), pipeline="JS (2D)",
         plate=dict(mode="js"), layers=["bg2d", "progress_1of2"], seed="main", big_captions=True,
         notes="Progress bar Generating... 1 of 2, dismissed. Drums drop out 43.8-51.1 s."),
    dict(id="S08", section="Pre-Chorus 1", anchor=("section", "Pre-Chorus 1"), pipeline="Blender",
         plate=dict(mode="render", plate="server_racks"), layers=[], seed="main",
         notes="Racks pulse on the beat; a line chart climbs into the sky."),
    dict(id="S09", section="Chorus 1", anchor=("section", "Chorus 1"), pipeline="Blender + JS",
         plate=dict(mode="render", plate="chorus_orbit"), layers=["the_rain", "regen_button"], seed="main",
         notes="Slow orbit, uniform easing; the-rain from \"Tokens falling\"; regenerate button pulses. "
               "Full stop 90.5-92.2 s."),
    dict(id="S10", section="Verse 2", anchor=("section", "Verse 2"), pipeline="JS (2D)",
         plate=dict(mode="js"), layers=["bg2d", "check_stamp"], seed="main", big_captions=True,
         notes="Half-second green check stamp on \"good\"; version ticks to v1.1."),
    dict(id="S11", section="Verse 2", anchor=("line", "Verse 2", 1), pipeline="JS (2D)",
         plate=dict(mode="js"), layers=["bg2d", "regen_spin"], seed="main", big_captions=True,
         notes="Spinning regenerate arrow."),
    dict(id="S12", section="Verse 2", anchor=("line", "Verse 2", 2), pipeline="Blender",
         plate=dict(mode="render", plate="theater_seats"), layers=[], seed="main",
         notes="Row of empty theater seats facing the grid."),
    dict(id="S13", section="Verse 2", anchor=("line", "Verse 2", 3), pipeline="Blender + JS",
         plate=dict(mode="render", plate="robot_tear"), layers=["score_counter"], seed="main",
         notes="Close-up; the single tear is a loading spinner on the screen face; a score counter ticks."),
    dict(id="S14", section="Bridge 2", anchor=("section", "Bridge 2"), pipeline="JS over held plate",
         plate=dict(mode="hold", src="S13"), layers=["devtools"], seed="main",
         notes="Hard freeze on \"Have\" while the music keeps playing; devtools slides in and stays."),
    dict(id="S15", section="Bridge 2", anchor=("line", "Bridge 2", 1), pipeline="JS over held plate",
         plate=dict(mode="hold", src="S13"), layers=["devtools", "icon_strip_slow"], seed="main",
         notes="The S06 icons return one at a time, slow enough to read."),
    dict(id="S16", section="Bridge 2", anchor=("line", "Bridge 2", 2), pipeline="JS over held plate",
         plate=dict(mode="hold", src="S13"), layers=["devtools", "progress_2of2"], seed="main",
         notes="Generating... 2 of 2 over the frozen frame."),
    dict(id="S17", section="Pre-Chorus 2", anchor=("section", "Pre-Chorus 2"), pipeline="JS over held plate, then Blender",
         plate=dict(mode="hold_then", src="S13", until=DROP2_END, plate="server_racks"), layers=["devtools_full"],
         seed="main",
         notes="Dropout: devtools expands to fill the frozen frame; at the drums' return (134.9 s) it snaps shut and "
               "the S08 racks are back; one frame of caption reads Lyric goes here."),
    dict(id="S18", section="Chorus 2", anchor=("section", "Chorus 2"), pipeline="Blender + JS",
         plate=dict(mode="render", plate="chorus_orbit"), layers=["the_rain_heavy", "output_truncated"], seed="main",
         notes="Heavier rain; the caption strikes \"answer\" for \"song\"; [output truncated] when the chorus cuts "
               "off, held until the slam; version ticks to v1.2.7."),
    dict(id="S19", section="Final Chorus", anchor=("event", "bass_return"), pipeline="Blender x2 + split",
         plate=dict(mode="split", plate="chorus_orbit", seeds=["main", "bridge_second_run"], lag_s=0.1),
         layers=[], seed="main+bridge_second_run",
         notes="Split screen seed 41 | 42, slightly out of sync; camera clips through the head; FPS counter ~12."),
    dict(id="S20", section="Final Chorus", anchor=("line", "Final Chorus", 3), pipeline="Blender (tiles) + JS grid",
         plate=dict(mode="js", renders=[dict(plate="chorus_orbit", seed="main")]), layers=["thumbnail_grid"],
         seed="main",
         notes="Zoom out: the video is one tile in a grid of near-identical thumbnails (this scene at other seeds, "
               "invented titles)."),
    dict(id="S21", section="Final Chorus", anchor=("line", "Final Chorus", 7), pipeline="JS",
         plate=dict(mode="js"), layers=["thumbnail_grid", "cursor_regen_click"], seed="main",
         notes="Over the held grid, the cursor hovers a generic regenerate button and clicks on \"machine\"."),
    dict(id="S22", section="Ending", anchor=("time", LAST_WORD_END), pipeline="Blender + JS",
         plate=dict(mode="render", plate="default_cube_boot", clock="local", black_after=1.0), layers=["reload"],
         seed="restart",
         notes="Page reloads; S01 restarts at seed 43; hard cut to black ~1 s in. Runs past the audio."),
    dict(id="S23", section="End card", anchor=("time", LAST_WORD_END + S22_LEN), pipeline="JS",
         plate=dict(mode="js"), layers=["end_card"], seed="main", no_globals=True,
         notes="Credits on black, one line at a time. No captions or chrome."),
]


def line_start(section, idx):
    ws = [w for w in TM["words"] if w["section"] == section and w["line"] == idx]
    if not ws:
        # Lines are numbered as in the lyrics file, where Bridge 1's "(beat)" takes an index.
        raise KeyError(f"no words for {section} line {idx}")
    return ws[0]["start"]


def snap(t):
    near = min(DOWNBEATS, key=lambda d: abs(d - t))
    return near if abs(near - t) <= BAR / 2 else t - 0.1


def resolve(anchor):
    kind = anchor[0]
    if kind == "time":
        return anchor[1]
    if kind == "section":
        return next(s["start"] for s in TM["sections"] if s["name"] == anchor[1])
    if kind == "line":
        return snap(line_start(anchor[1], anchor[2]))
    if kind == "event":
        ev = TM["events"]
        if anchor[1] == "bridge1_beat_gap":
            return snap(ev["bridge1_beat_gap"]["start"])
        if anchor[1] == "bass_return":
            return snap(ev["final_chorus_return"]["bass_return"])
    raise ValueError(anchor)


def render_jobs(shots):
    """Blender work: one job per (plate, seed, frame range)."""
    jobs = []
    for s in shots:
        p = s["plate"]
        f0, f1 = s["start_frame"], s["end_frame"]
        if p["mode"] == "render":
            end = f0 + round(p.get("black_after", 1e9) * FPS)
            jobs.append(dict(shot=s["id"], plate=p["plate"], seed=s["seed"], start=f0, end=min(f1, end),
                             clock_offset_s=s["start_s"] if p.get("clock") == "local" else 0.0))
        elif p["mode"] == "hold_then":
            jobs.append(dict(shot=s["id"], plate=p["plate"], seed=s["seed"], start=round(p["until"] * FPS), end=f1,
                             clock_offset_s=0.0))
        elif p["mode"] == "split":
            lag = round(p["lag_s"] * FPS)
            for i, seed in enumerate(p["seeds"]):
                jobs.append(dict(shot=s["id"], plate=p["plate"], seed=seed, start=f0 - lag * i, end=f1 - lag * i,
                                 clock_offset_s=0.0))
        for extra in p.get("renders", []):
            jobs.append(dict(shot=s["id"], plate=extra["plate"], seed=extra["seed"], start=f0, end=f1,
                             clock_offset_s=0.0))
    return jobs


def main():
    starts = [resolve(s["anchor"]) for s in SHOTS]
    total = LAST_WORD_END + S22_LEN + S23_LEN
    shots = []
    for i, spec in enumerate(SHOTS):
        start = starts[i]
        end = starts[i + 1] if i + 1 < len(SHOTS) else total
        assert end > start, (spec["id"], start, end)
        shots.append({
            "id": spec["id"], "section": spec["section"], "anchor": list(spec["anchor"]),
            "pipeline": spec["pipeline"], "start_s": round(start, 3), "end_s": round(end, 3),
            "start_frame": round(start * FPS), "end_frame": round(end * FPS),
            "plate": spec["plate"], "layers": spec["layers"], "seed": spec["seed"],
            "global_layers": [] if spec.get("no_globals") else ["captions", "chrome"],
            "big_captions": spec.get("big_captions", False), "notes": spec["notes"],
        })
    out = {"fps": FPS, "total_s": round(total, 3), "total_frames": round(total * FPS),
           "audio_end_s": END_OF_AUDIO, "shots": shots, "render_jobs": render_jobs(shots)}
    Path("shots/shots.json").write_text(json.dumps(out, indent=1) + "\n")

    md = ["# Pipeline per shot", "",
          "Generated by `shots/build_shots.py` from the brief's shot list (doc rev 54) and `timing/timing_map.json`. "
          "Do not edit by hand; edit the script.", "",
          "**Pipelines.** Blender 5.2 (Python, Eevee) renders 3D plates (`scenes/blender/plates.py`). One HTML page "
          "(`overlays/video.html`) renders every JS layer for any frame and is captured by Puppeteer "
          "(`scripts/render_frames.mjs`) as transparent PNGs. An assembly step maps each frame to its plate (rendered, "
          "held for freezes, or split for S19), and ffmpeg composites and muxes the audio. Every frame is a pure "
          "function of (t, seed) (step 4).", "",
          "**Global layers** run over every shot except S23: `captions` (word-timed lyrics, style spec; large in the "
          "2D shots) and `chrome` (credit with version, seed label, FPS counter).", "",
          "**Framing.** 3D plates are rendered 20% wider than 16:9 so the 9:16 crop for the vertical cut "
          "(S14-S22) can reframe without re-rendering. JS layers are laid out per aspect ratio.", "",
          f"Video length {total:.2f} s ({round(total * FPS)} frames at {FPS} fps); audio ends at {END_OF_AUDIO:.2f} s.",
          "", "| ID | Section | Start (s) | End (s) | Frames | Pipeline | Plate | JS layers | Seed | Notes |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for s in shots:
        p = s["plate"]
        plate = {"render": p.get("plate"), "hold": f"hold {p.get('src')}", "js": "—",
                 "hold_then": f"hold {p.get('src')} → {p.get('plate')}",
                 "split": f"{p.get('plate')} ×2"}[p["mode"]]
        md.append(f"| {s['id']} | {s['section']} | {s['start_s']:.2f} | {s['end_s']:.2f} | "
                  f"{s['start_frame']}–{s['end_frame']} | {s['pipeline']} | {plate} | "
                  f"{', '.join(s['layers']) or '—'} | {s['seed']} | {s['notes']} |")
    Path("shots/pipeline.md").write_text("\n".join(md) + "\n")
    for s in shots:
        print(f"{s['id']} {s['start_s']:7.2f} {s['end_s']:7.2f} {s['plate']['mode']:9} {s['layers']}")
    print(len(out["render_jobs"]), "render jobs,", sum(j["end"] - j["start"] for j in out["render_jobs"]), "plate frames")


if __name__ == "__main__":
    main()
