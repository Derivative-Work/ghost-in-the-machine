"""Pre-production step 5: resolve the brief's shot list against the timing map and record the pipeline per shot.

Each shot starts at an anchor (section start, lyric line start, a word, or a timing-map event). A cut lands on the
downbeat nearest the anchor if one is within half a bar, otherwise 0.1 s before it. A shot ends where the next one
starts. Times are converted to frames at 30 fps (style spec).

Layers, bottom to top: Blender plate (Eevee) -> JS layers (Puppeteer, transparent PNG) -> global JS layers
(captions, chrome) -> ffmpeg composite. Global layers run over every shot unless the shot opts out.

Usage: .venv/bin/python shots/build_shots.py  ->  shots/shots.json, shots/pipeline.md
"""
import json
from pathlib import Path

FPS = 30
TM = json.loads(Path("timing/timing_map.json").read_text())
DOWNBEATS = TM["downbeats"]
BAR = 4 * 60 / TM["tempo_bpm"]
END_OF_AUDIO = TM["audio"]["duration_s"]

# (id, section, anchor, pipeline, blender plate, JS layers, seed name, notes)
# Anchors: ("section", name) | ("line", section, line_index) | ("word", section, line_index, word) |
#          ("event", key) | ("time", seconds, snap?)
SHOTS = [
    ("S01", "Intro", ("time", 0.0, False), "Blender + JS", "default_cube_boot", [], "main",
     "Default scene holds ~1 s, neon world boots on the first downbeat (4.4 s). Overlays fade in."),
    ("S02", "Verse 1", ("section", "Verse 1"), "Blender", "robot_screens", [], "main",
     "Robot on the grid among floating screens. Lines 1-2."),
    ("S03", "Verse 1", ("line", "Verse 1", 2), "JS", None, ["accept_banner"], "main",
     "Accept-all banner over the S02 plate (held); cursor clicks on \"agreed\"."),
    ("S04", "Verse 1", ("line", "Verse 1", 3), "Blender + JS", "robot_shrug", ["todo_caption"], "main",
     "Shrug; caption flashes // TODO: make this part sad."),
    ("S05", "Bridge 1", ("section", "Bridge 1"), "JS", None, ["glitch_devtools_flicker"], "main",
     "One-frame freeze on \"Have\", devtools flickers; music continues. Plate: last S04 frame + held S02."),
    ("S06", "Bridge 1", ("line", "Bridge 1", 1), "JS", None, ["icon_strip_fast"], "main",
     "Five generic icons whip past."),
    ("S07", "Bridge 1", ("event", "bridge1_beat_gap"), "JS", None, ["progress_1of2"], "main",
     "Progress bar Generating... 1 of 2, dismissed. Drums drop out 43.8-51.1 s."),
    ("S08", "Pre-Chorus 1", ("section", "Pre-Chorus 1"), "Blender", "server_racks", [], "main",
     "Racks pulse on beats; line chart climbs."),
    ("S09", "Chorus 1", ("section", "Chorus 1"), "Blender + JS", "chorus_orbit", ["the_rain", "regen_button"], "main",
     "Slow orbit, uniform easing; the-rain; regenerate button pulses in a corner. Full stop 90.5-92.2 s."),
    ("S10", "Verse 2", ("section", "Verse 2"), "JS", None, ["check_stamp"], "main",
     "Green check stamp on \"good\"; version -> v1.1."),
    ("S11", "Verse 2", ("line", "Verse 2", 1), "JS", None, ["regen_spin"], "main", "Spinning regenerate arrow."),
    ("S12", "Verse 2", ("line", "Verse 2", 2), "Blender", "theater_seats", [], "main", "Empty seats facing the grid."),
    ("S13", "Verse 2", ("line", "Verse 2", 3), "Blender + JS", "robot_tear", ["score_counter"], "main",
     "Close-up; tear is a loading spinner (screen face); score counter."),
    ("S14", "Bridge 2", ("section", "Bridge 2"), "JS", None, ["freeze_devtools"], "main",
     "Hard freeze on \"Have\" over music that keeps playing; devtools slides in and stays. Plate: held last S13 frame."),
    ("S15", "Bridge 2", ("line", "Bridge 2", 1), "JS", None, ["icon_strip_slow", "freeze_devtools"], "main",
     "S06 icons return one by one, readable."),
    ("S16", "Bridge 2", ("line", "Bridge 2", 2), "JS", None, ["progress_2of2", "freeze_devtools"], "main",
     "Generating... 2 of 2 over the frozen frame."),
    ("S17", "Pre-Chorus 2", ("section", "Pre-Chorus 2"), "Blender + JS", "server_racks",
     ["freeze_devtools_full", "lyric_goes_here"], "main",
     "Dropout 127.8-134.9 s: devtools expands; racks (S08 plate) snap back when drums return; one frame of "
     "Lyric goes here on the snap-back."),
    ("S18", "Chorus 2", ("section", "Chorus 2"), "Blender + JS", "chorus_orbit",
     ["the_rain_heavy", "strike_answer", "output_truncated"], "main",
     "Heavier rain; answer->song strike; [output truncated] when the chorus cuts off, held until the slam; "
     "version -> v1.2.7."),
    ("S19", "Final Chorus", ("event", "bass_return"), "Blender + ffmpeg", "chorus_orbit_split", [], "main+bridge_second_run",
     "Split screen seed 41 | 42, slightly out of sync; camera clips through the head; FPS counter -> ~12."),
    ("S20", "Final Chorus", ("line", "Final Chorus", 3), "Blender + ffmpeg", "thumbnail_grid", [], "main",
     "Zoom out to a grid of near-identical tiles (this scene at other seeds, invented titles)."),
    ("S21", "Final Chorus", ("line", "Final Chorus", 7), "JS", None, ["cursor_regen_click"], "main",
     "Cursor hovers the regenerate button and clicks. Music decays under the last line."),
    ("S22", "Ending", ("time", TM["words"][-1]["end"], False), "JS + ffmpeg", "default_cube_boot", ["reload"], "restart",
     "Page reloads; S01 restarts at seed 43; hard cut to black ~1 s in. Runs past the audio."),
    ("S23", "End card", ("time", TM["words"][-1]["end"] + 1.2, False), "ffmpeg", None, ["end_card"], "main",
     "Credits on black, one line at a time. No captions or chrome."),
]
S22_LEN, S23_LEN = 1.2, 8.0


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
        return anchor[1] if not anchor[2] else snap(anchor[1])
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


def main():
    starts = [resolve(s[2]) for s in SHOTS]
    total = TM["words"][-1]["end"] + S22_LEN + S23_LEN
    shots = []
    for i, (sid, section, anchor, pipe, plate, js, seed, notes) in enumerate(SHOTS):
        start = starts[i]
        end = starts[i + 1] if i + 1 < len(SHOTS) else total
        assert end > start, (sid, start, end)
        shots.append({
            "id": sid, "section": section, "anchor": list(anchor), "pipeline": pipe,
            "start_s": round(start, 3), "end_s": round(end, 3),
            "start_frame": round(start * FPS), "end_frame": round(end * FPS),
            "blender_plate": plate, "js_layers": js, "seed": seed,
            "global_layers": [] if sid == "S23" else ["captions", "chrome"],
            "notes": notes,
        })
    out = {"fps": FPS, "total_s": round(total, 3), "total_frames": round(total * FPS),
           "audio_end_s": END_OF_AUDIO, "shots": shots}
    Path("shots/shots.json").write_text(json.dumps(out, indent=1) + "\n")

    md = ["# Pipeline per shot", "",
          "Generated by `shots/build_shots.py` from the brief's shot list (doc rev 54) and `timing/timing_map.json`. "
          "Do not edit by hand; edit the script.", "",
          "**Pipelines.** Blender 5.2 (Python, Eevee) renders 3D plates. HTML/canvas scenes are captured frame by "
          "frame by Puppeteer (`scripts/render_frames.mjs`) as transparent PNGs. ffmpeg composites the layers, "
          "builds the S19 split screen and the S20 grid, and muxes the audio. Every frame is a pure function of "
          "(t, seed) (step 4).", "",
          "**Global layers** run over every shot except S23: `captions` (word-timed lyrics, style spec) and "
          "`chrome` (credit with version, seed label, FPS counter).", "",
          "**Framing.** 3D plates are rendered 20% wider than 16:9 so the 9:16 crop for the vertical cut "
          "(S14-S22) can reframe without re-rendering. JS layers are laid out per aspect ratio.", "",
          f"Video length {total:.2f} s ({round(total * FPS)} frames at {FPS} fps); audio ends at {END_OF_AUDIO:.2f} s.",
          "", "| ID | Section | Start (s) | End (s) | Frames | Pipeline | Blender plate | JS layers | Seed | Notes |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for s in shots:
        md.append(f"| {s['id']} | {s['section']} | {s['start_s']:.2f} | {s['end_s']:.2f} | "
                  f"{s['start_frame']}–{s['end_frame']} | {s['pipeline']} | {s['blender_plate'] or '—'} | "
                  f"{', '.join(s['js_layers']) or '—'} | {s['seed']} | {s['notes']} |")
    Path("shots/pipeline.md").write_text("\n".join(md) + "\n")
    for s in shots:
        print(f"{s['id']} {s['start_s']:7.2f} {s['end_s']:7.2f} {s['end_s'] - s['start_s']:5.2f}s {s['pipeline']}")


if __name__ == "__main__":
    main()
