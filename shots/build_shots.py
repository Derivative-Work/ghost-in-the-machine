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
S22_LEN, S23_LEN = 3.0, 8.0  # the ending (now S56: reload, then the cube vacuums the world) and the end card

# Anchors: ("section", name) | ("line", section, line_index) | ("bar", n) | ("event", key) | ("time", seconds)
R = lambda plate, cam, fx=(), **kw: dict(mode="render", plate=plate, cam=cam, fx=list(fx), **kw)
JS = dict(mode="js")
HOLD = lambda src, **kw: dict(mode="hold", src=src, **kw)
SPLIT = lambda seeds, cam="orbit", **kw: dict(mode="split", plate="chorus", cam=cam, seeds=seeds, lag_s=0.1, **kw)
# The feed (S50-S55): every tile, this video's included, is the robot dancing in the data stream at its own seed.
# Tiles render first: the main render (this video) carries the other videos flowing in its river from S53 on.
FEED_RENDER = dict(mode="js", renders=[dict(plate="stream", cam="wide", fx=["dance"], seed=sd, span=("S50", "S55"))
                                       for sd in [f"thumbnail_tiles.{i}" for i in range(23)]] +
                   [dict(plate="stream", cam="wide", fx=["dance", "video_tiles"], seed="main", span=("S50", "S55"))])

SHOTS = [
    # Intro
    dict(section="Intro", anchor=("time", 0.0), plate=R("default_cube_boot", "default"), layers=[]),
    dict(section="Intro", anchor=("bar", 1), plate=R("default_cube_boot", "default", ["box_open"]), layers=[]),
    dict(section="Intro", anchor=("bar", 2), plate=JS, layers=["bg2d", "terminal_boot"]),
    dict(section="Intro", anchor=("bar", 3), plate=R("robot", "screens", ["screens_power_on"]), layers=[]),
    dict(section="Intro", anchor=("bar", 4), plate=R("robot", "face", ["eyes_wake"]), layers=[]),
    # Verse 1
    dict(section="Verse 1", anchor=("section", "Verse 1"), plate=R("robot", "wide"), layers=[]),
    dict(section="Verse 1", anchor=("bar", 6), plate=R("robot", "face"), layers=["hearts"], zoom_out=(0.5, 0.45)),
    dict(section="Verse 1", anchor=("line", "Verse 1", 1), plate=JS, layers=["bg2d", "chat_autocomplete"]),
    dict(section="Verse 1", anchor=("line", "Verse 1", 2), plate=R("robot", "medium"), layers=["accept_banner"]),
    dict(section="Verse 1", anchor=("line", "Verse 1", 3), plate=R("robot", "medium", ["shrug"]), layers=["todo_caption", "boot_log"]),
    # Bridge 1
    dict(section="Bridge 1", anchor=("section", "Bridge 1"), plate=R("robot", "low", freeze_first=True),
         layers=["glitch_flicker"], transition="tear"),
    dict(id="S11b", section="Bridge 1", anchor=("section_plus", "Bridge 1", 0.6), plate=JS, layers=["bg2d", "song_match"]),
    dict(section="Bridge 1", anchor=("line", "Bridge 1", 1), plate=JS, layers=["bg2d", "icon_strip_fast"], big=True),
    dict(section="Bridge 1", anchor=("line", "Bridge 1", 2), plate=JS, layers=["bg2d", "big_accept"], big=True),
    dict(section="Bridge 1", anchor=("event", "bridge1_beat_gap"), plate=JS, layers=["bg2d", "big_accept_disabled", "progress_1of2"], big=True),
    dict(section="Bridge 1", anchor=("line", "Bridge 1", 4), plate=JS, layers=["bg2d", "flap_board"]),
    dict(section="Bridge 1", anchor=("line", "Bridge 1", 5), plate=JS, layers=["bg2d", "avg_merge"]),
    # Pre-Chorus 1
    dict(section="Pre-Chorus 1", anchor=("section", "Pre-Chorus 1"), plate=R("robot", "lullaby", ["mobile"]), layers=[]),
    # The count and the graph climb together on one shot (S19 merged into S18).
    dict(section="Pre-Chorus 1", anchor=("line", "Pre-Chorus 1", 1), plate=R("racks", "chart"), layers=["giant_counter"]),
    dict(section="Pre-Chorus 1", anchor=("bar", 28), plate=R("racks", "chart"), layers=[], drop=True),
    # Chorus 1
    dict(section="Chorus 1", anchor=("section", "Chorus 1"), plate=R("chorus", "orbit", ["fast_entry", "sheet_ghost"]),
         layers=["regen_button"], transition="whip"),
    dict(section="Chorus 1", anchor=("line", "Chorus 1", 1), plate=R("chorus", "dolly_zoom", ["missing_texture"]),
         layers=["loading_textures"]),
    dict(section="Chorus 1", anchor=("line", "Chorus 1", 2), plate=R("chorus", "low_up", ["head_up"]),
         layers=["the_rain", "context_meter"], zoom_out=(0.5, 0.3)),
    dict(section="Chorus 1", anchor=("line", "Chorus 1", 3), plate=JS, layers=["bg2d", "nine_replies", "same_stamps"]),
    dict(section="Chorus 1", anchor=("line", "Chorus 1", 4), plate=R("chorus", "wide_static", ["lights_fade"]), layers=[]),
    dict(section="Chorus 1", anchor=("line", "Chorus 1", 5), plate=R("chorus", "rise", ["cloud"]), layers=[]),
    # The props and the Generate button are in both stream shots (continuity); the robot presses Generate as S27 ends,
    # and the music stops (S28).
    dict(section="Chorus 1", anchor=("line", "Chorus 1", 6), plate=R("stream", "wide", ["dance", "refs", "gen_button"]), layers=[]),
    dict(section="Chorus 1", anchor=("bar", 43), plate=R("stream", "low", ["dance", "refs", "gen_button", "gen_press"]), layers=[]),
    dict(section="Chorus 1", anchor=("event", "stop1"), plate=JS, layers=["black_stop"]),
    dict(section="Chorus 1", anchor=("event", "stop1_end"), plate=JS, layers=["bg2d", "loading_verse2"],
         transition="glitch"),
    # Verse 2
    dict(section="Verse 2", anchor=("section", "Verse 2"), plate=JS, layers=["bg2d", "diff_scroll"]),
    dict(id="S30b", section="Verse 2", anchor=("bar", 49), plate=R("ship", "track"), layers=["check_stamp"]),
    dict(section="Verse 2", anchor=("line", "Verse 2", 1), plate=R("robot", "wide"), layers=["regen_fail"]),
    dict(section="Verse 2", anchor=("line", "Verse 2", 2), plate=R("seats", "front", ["robot_seated"]), layers=["ticket"]),
    dict(section="Verse 2", anchor=("bar", 53), plate=R("seats", "reverse_end", ["arena", "robot_seated"]), layers=[]),
    dict(section="Verse 2", anchor=("line", "Verse 2", 3), plate=R("tear", "pullback", ["score_fade"]), layers=["reward_panel"]),
    # Bridge 2: the freeze (static on purpose)
    dict(section="Bridge 2", anchor=("section", "Bridge 2"), plate=HOLD("S34"), layers=["devtools"]),
    dict(section="Bridge 2", anchor=("line", "Bridge 2", 1), plate=HOLD("S34"), layers=["devtools", "icon_strip_slow"]),
    dict(section="Bridge 2", anchor=("line", "Bridge 2", 2), plate=HOLD("S34"), layers=["devtools", "progress_2of2"]),
    # Pre-Chorus 2
    dict(section="Pre-Chorus 2", anchor=("section", "Pre-Chorus 2"), plate=HOLD("S34"), layers=["devtools_full"]),
    # Servers, numbers and graph on one shot (S40 and S41 merged into S39).
    dict(section="Pre-Chorus 2", anchor=("event", "drop2_end"), plate=R("racks", "crane_chart"), layers=["giant_counter"],
         transition="glitch"),
    dict(section="Pre-Chorus 2", anchor=("bar", 69), plate=JS, layers=[], drop=True),
    dict(section="Pre-Chorus 2", anchor=("bar", 70), plate=JS, layers=[], drop=True),
    # Chorus 2: Chorus 1 again, degrading
    dict(section="Chorus 2", anchor=("section", "Chorus 2"), plate=R("chorus", "orbit", ["fast_entry"]), layers=[],
         degrade=0.35, transition="whip"),
    dict(section="Chorus 2", anchor=("line", "Chorus 2", 1), plate=R("chorus", "dolly_zoom", ["missing_texture"]),
         layers=["loading_textures"], degrade=0.5),
    dict(section="Chorus 2", anchor=("line", "Chorus 2", 2), plate=R("chorus", "low_up", ["head_up"]),
         layers=["the_rain_heavy", "context_meter"], degrade=0.6),
    dict(section="Chorus 2", anchor=("line", "Chorus 2", 3), plate=JS, layers=["bg2d", "nine_replies", "same_stamps"],
         degrade=0.7),
    dict(section="Chorus 2", anchor=("event", "trunc"), plate=HOLD("S44"), layers=["output_truncated"], degrade=0.75,
         drop=True),  # v6: removed so S45 runs to the bass return
    # Final chorus: the split multiplies, then the feed
    dict(section="Final Chorus", anchor=("event", "bass_return"), plate=SPLIT(["main", "bridge_second_run"]), layers=[]),
    # The splits zoom out further on each line, repeating that line's earlier scene at more seeds.
    dict(section="Final Chorus", anchor=("line", "Final Chorus", 1),
         plate=SPLIT(["main", "bridge_second_run", "split_extra.0", "split_extra.1"], cam="dolly_zoom", fx=["missing_texture"]),
         layers=[]),
    dict(section="Final Chorus", anchor=("line", "Final Chorus", 2),
         plate=SPLIT(["main", "bridge_second_run"] + [f"split_extra.{i}" for i in range(7)], cam="low_up",
                     fx=["head_up"]), layers=["the_rain"]),
    dict(section="Final Chorus", anchor=("line", "Final Chorus", 3), plate=FEED_RENDER, layers=["grid_zoom"]),
    dict(section="Final Chorus", anchor=("line", "Final Chorus", 4), plate=JS, layers=["grid_dark"]),
    dict(section="Final Chorus", anchor=("line", "Final Chorus", 5), plate=JS, layers=["grid_scroll"]),
    # The feed's videos, seen top-down as a grid above the landscape, peel off one by one and drop into the river,
    # where they flow on with the tokens as the camera descends to the river view S54 opens on...
    dict(section="Final Chorus", anchor=("line", "Final Chorus", 6), plate=R("stream", "feed_dive", ["dance", "video_tiles"]),
         layers=["feed_titles"]),
    # ...then the river pulls back to be one of the screens around the robot; Regenerate is clicked over that scene.
    dict(section="Final Chorus", anchor=("event", "beat_end"), plate=R("robot", "screen_pullback", ["river_screen"]), layers=[]),
    dict(section="Final Chorus", anchor=("line", "Final Chorus", 7), plate=R("robot", "wide_hold", ["river_screen"]),
         layers=["cursor_regen_click"]),
    # Ending
    dict(section="Ending", anchor=("time", LAST_WORD_END), plate=R("default_cube_boot", "default", ["vacuum"], clock="local",
                                                                     black_after=3.0), layers=["reload"], seed="restart"),
    dict(section="End card", anchor=("time", LAST_WORD_END + S22_LEN), plate=JS, layers=["end_card"], no_globals=True),
]
# IDs: inserted shots carry a letter suffix (S11b) so the brief's existing IDs never change.
_n = 0
for s in SHOTS:
    if "id" not in s:
        _n += 1
        s["id"] = f"S{_n:02d}"
assert _n == 57, _n
# Merged shots keep their ID number reserved (so no other ID changes) but are not output.
SHOTS = [s for s in SHOTS if not s.get("drop")]

STOP1 = next(d for d in TM["events"]["dropouts"] if d["full"] and "Chorus 1" in d["sections"])
C2_LAST_END = [w for w in TM["words"] if w["section"] == "Chorus 2"][-1]["end"]


def line_start(section, idx):
    ws = [w for w in TM["words"] if w["section"] == section and w["line"] == idx]
    if not ws:
        # Lines are numbered as in the lyrics file, where Bridge 1's "(beat)" takes an index.
        raise KeyError(f"no words for {section} line {idx}")
    return ws[0]["start"]


def snap(t):
    """Nearest downbeat within a quarter bar; otherwise just before the anchor (never mid-word)."""
    near = min(DOWNBEATS, key=lambda d: abs(d - t))
    return near if abs(near - t) <= BAR / 4 else t - 0.1


def resolve(anchor):
    kind = anchor[0]
    if kind == "time":
        return anchor[1]
    if kind == "section":
        return next(s["start"] for s in TM["sections"] if s["name"] == anchor[1])
    if kind == "line":
        return snap(line_start(anchor[1], anchor[2]))
    if kind == "bar":
        return DOWNBEATS[anchor[1] - 1]
    if kind == "section_plus":
        return next(s["start"] for s in TM["sections"] if s["name"] == anchor[1]) + anchor[2]
    if kind == "event":
        ev = TM["events"]
        if anchor[1] == "bridge1_beat_gap":
            return snap(ev["bridge1_beat_gap"]["start"])
        if anchor[1] == "bass_return":
            return snap(ev["final_chorus_return"]["bass_return"])
        if anchor[1] == "stop1":
            return STOP1["start"]
        if anchor[1] == "stop1_end":
            return STOP1["end"]
        if anchor[1] == "drop2_end":
            return DROP2_END
        if anchor[1] == "trunc":
            return C2_LAST_END + 0.15
        if anchor[1] == "trunc_end":
            return C2_LAST_END + 0.15 + 0.8
        if anchor[1] == "beat_end":
            return DOWNBEATS[-1] + BAR
    raise ValueError(anchor)


def performance(shots):
    """The robot's eye expressions and gestures over time (v3). Plates read this by global time."""
    by_id = {s["id"]: s for s in shots}
    words = TM["words"]
    lines = {}
    for w in words:
        lines.setdefault((w["section"], w["line"]), []).append(w)
    sec = {x["name"]: x for x in TM["sections"]}
    ev = []
    for name in ("Chorus 1", "Chorus 2", "Final Chorus"):
        ev.append(dict(kind="expr", value="happy", t0=sec[name]["start"], t1=sec[name]["end"]))
    v1l3 = lines[("Verse 1", 3)]
    ev.append(dict(kind="expr", value="squint", t0=v1l3[0]["start"], t1=v1l3[-1]["end"] + 0.3))
    heart = next(w for w in lines[("Verse 1", 0)] if w["text"] == "heart")
    ev.append(dict(kind="expr", value="heart", t0=heart["start"] - 0.1, t1=heart["start"] + 1.6))
    ev.append(dict(kind="expr", value="sleepy", t0=by_id["S17"]["start_s"], t1=by_id["S17"]["end_s"]))
    s24 = by_id["S24"]
    beats = [b for b in TM["beats"] if s24["start_s"] <= b < s24["end_s"]]
    if len(beats) >= 7:
        ev.append(dict(kind="expr", value="xx", t0=beats[6], t1=s24["end_s"]))
    for (section, li), ws in lines.items():
        text = " ".join(w["text"] for w in ws)
        if text == "We are the ghost in the machine":
            ev.append(dict(kind="gesture", value="point", t0=ws[0]["start"] - 0.1, t1=ws[0]["start"] + 1.8))
        if text == "Tokens falling like the rain":
            ev.append(dict(kind="gesture", value="reach_up", t0=ws[0]["start"] - 0.1, t1=ws[-1]["end"] + 0.3))
    # Later entries win where they overlap (a squint inside a chorus would beat "happy").
    return [dict(e, t0=round(e["t0"], 3), t1=round(e["t1"], 3)) for e in ev]


def job_dir(plate, cam, fx, seed):
    return f"{plate}-{cam}{'-' + '+'.join(fx) if fx else ''}__{seed}"


def render_jobs(shots):
    """Blender work: one job per (shot, plate variant, seed, frame range). Output dir names encode the variant."""
    by_id = {s["id"]: s for s in shots}
    jobs = []

    def add(shot, plate, cam, fx, seed, start, end, **kw):
        jobs.append(dict(shot=shot, plate=plate, cam=cam, fx=fx, seed=seed, start=start, end=end,
                         dir=job_dir(plate, cam, fx, seed), clock_offset_s=kw.get("clock_offset_s", 0.0),
                         lag_frames=kw.get("lag_frames", 0)))

    for s in shots:
        p = s["plate"]
        f0, f1 = s["start_frame"], s["end_frame"]
        if p["mode"] == "render":
            end = f0 + round(p.get("black_after", 1e9) * FPS)
            add(s["id"], p["plate"], p["cam"], p["fx"], s["seed"], f0, min(f1, end),
                clock_offset_s=s["start_s"] if p.get("clock") == "local" else 0.0)
        elif p["mode"] == "montage":
            for seed, (a, b) in zip(p["seeds"], p["segments"]):
                add(s["id"], p["plate"], p["cam"], p["fx"], seed, a, b)
        elif p["mode"] == "split":
            lag = round(p["lag_s"] * FPS)
            for i, seed in enumerate(p["seeds"]):
                add(s["id"], p["plate"], p["cam"], p.get("fx", []), seed, f0 - lag * i, f1 - lag * i, lag_frames=lag * i)
        for extra in p.get("renders", []):
            a, b = extra["span"]
            add(s["id"], extra["plate"], extra["cam"], extra["fx"], extra["seed"], by_id[a]["start_frame"],
                by_id[b]["end_frame"])
    return jobs


def main():
    starts = [resolve(s["anchor"]) for s in SHOTS]
    total = LAST_WORD_END + S22_LEN + S23_LEN
    shots = []
    for i, spec in enumerate(SHOTS):
        start = starts[i]
        end = starts[i + 1] if i + 1 < len(SHOTS) else total
        assert end > start + 0.5, (spec["id"], start, end)
        shots.append({
            "id": spec["id"], "section": spec["section"], "anchor": list(spec["anchor"]),
            "start_s": round(start, 3), "end_s": round(end, 3),
            "start_frame": round(start * FPS), "end_frame": round(end * FPS),
            "plate": spec["plate"], "layers": spec["layers"], "seed": spec.get("seed", "main"),
            "global_layers": [] if spec.get("no_globals") else ["captions", "chrome"],
            "big_captions": spec.get("big", False), "degrade": spec.get("degrade", 0.0),
            "transition": spec.get("transition"), "zoom_out": spec.get("zoom_out"),
        })
    for sh in shots:
        p = sh["plate"]
        if p["mode"] == "montage":  # one re-roll per half bar
            n = len(p["seeds"])
            cuts = [sh["start_frame"] + round(i * BAR / 2 * FPS) for i in range(n)] + [sh["end_frame"]]
            p["segments"] = [(cuts[i], cuts[i + 1]) for i in range(n)]
    out = {"fps": FPS, "total_s": round(total, 3), "total_frames": round(total * FPS),
           "audio_end_s": END_OF_AUDIO, "shots": shots, "render_jobs": render_jobs(shots),
           "performance": performance(shots)}
    Path("shots/shots.json").write_text(json.dumps(out, indent=1) + "\n")

    def plate_desc(p):
        if p["mode"] == "render":
            return f"{p['plate']} / {p['cam']}" + (f" ({', '.join(p['fx'])})" if p["fx"] else "")
        if p["mode"] == "hold":
            return f"hold {p['src']}"
        if p["mode"] == "split":
            return f"{len(p['seeds'])}-up split of {p['plate']}" + (f" ({', '.join(p['fx'])})" if p.get("fx") else "")
        if p["mode"] == "montage":
            return f"{p['plate']} / {p['cam']} re-rolled at {len(p['seeds'])} seeds"
        return "JS (full frame)" if p.get("renders") is None else "JS grid over chorus / orbit"

    md = ["# Pipeline per shot (v3)", "",
          "Generated by `shots/build_shots.py` from the brief's v3 shot list and `timing/timing_map.json`. "
          "Do not edit by hand; edit the script.", "",
          "**Pipelines.** Blender 5.2 (Python, Eevee) renders 3D plates (`scenes/blender/plates.py`): each plate is a "
          "scene with named cameras and effects. One HTML page (`overlays/video.html`) renders every JS layer for any "
          "frame, captured by Puppeteer. `scripts/assemble.py` builds each frame's plate (rendered, held, or an N-up "
          "split), applies Chorus 2's degradation, composites the overlay, applies whip and glitch transitions, and "
          "pipes raw frames to ffmpeg with the audio. Every frame is a pure function of (t, seed).", "",
          "**Cutting.** Cuts land on the downbeat nearest the anchor if it is within a quarter bar, otherwise 0.1 s "
          "before it, so no cut falls mid-word.", "",
          f"{len(shots)} shots, average {total / len(shots):.2f} s. Video length {total:.2f} s "
          f"({round(total * FPS)} frames at {FPS} fps); audio ends at {END_OF_AUDIO:.2f} s.", "",
          "| ID | Section | Start (s) | Len (s) | Plate | JS layers | Notes |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for s in shots:
        notes = ", ".join(x for x in [f"degrade {s['degrade']}" if s["degrade"] else "",
                                       f"{s['transition']} in" if s["transition"] else "",
                                       "zoom-through out" if s["zoom_out"] else "",
                                       "big captions" if s["big_captions"] else "",
                                       f"seed {s['seed']}" if s["seed"] != "main" else ""] if x)
        md.append(f"| {s['id']} | {s['section']} | {s['start_s']:.2f} | {s['end_s'] - s['start_s']:.2f} | "
                  f"{plate_desc(s['plate'])} | {', '.join(s['layers']) or '—'} | {notes or '—'} |")
    Path("shots/pipeline.md").write_text("\n".join(md) + "\n")
    lens = [s["end_s"] - s["start_s"] for s in shots]
    print(f"{len(shots)} shots, avg {sum(lens) / len(lens):.2f} s, min {min(lens):.2f}, max {max(lens):.2f}; "
          f"{len(out['render_jobs'])} jobs, {sum(j['end'] - j['start'] for j in out['render_jobs'])} plate frames")
    for s in shots:
        print(f"  {s['id']} {s['start_s']:7.2f} {s['end_s'] - s['start_s']:5.2f}  {plate_desc(s['plate'])}  {s['layers']}")


if __name__ == "__main__":
    main()
