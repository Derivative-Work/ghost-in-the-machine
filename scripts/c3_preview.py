"""C3 timing-map preview: captions (karaoke-timed per word) and beat flashes only, for checking sync by ear.

Writes an ASS file from timing/timing_map.json; ffmpeg burns it onto a plain base-colored 960x540 30 fps frame
with the final track.

Top left: section name, bar number. Bottom right: beat square (white = beat, accent = downbeat).
Top right: DROPOUT while a detected dropout runs. Captions: lower left, sung words turn white, upcoming dim.

Usage: .venv/bin/python scripts/c3_preview.py  ->  renders/draft/c3/timing_preview.{ass,mp4}
"""
import json
import subprocess
from pathlib import Path

TM = json.loads(Path("timing/timing_map.json").read_text())
OUT = Path("renders/draft/c3")
W, H = 960, 540


def ts(t):
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def ass_color(hexstr, alpha=0):
    h = hexstr.lstrip("#")
    return f"&H{alpha:02X}{h[4:6]}{h[2:4]}{h[0:2]}"


PAPER, ACCENT, MID, DIM = "#e6e4dc", "#d9502f", "#847d77", "#4a4550"


def header():
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Inter,40,{ass_color(PAPER)},{ass_color(DIM)},&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,1,60,60,90,1
Style: Mono,JetBrains Mono,16,{ass_color(MID)},{ass_color(MID)},&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,24,24,20,1
Style: Flag,JetBrains Mono,16,{ass_color(ACCENT)},{ass_color(ACCENT)},&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,9,24,24,20,1
Style: Box,JetBrains Mono,10,{ass_color(PAPER)},{ass_color(PAPER)},&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def lines_from_words(words):
    out, cur, key = [], [], None
    for w in words:
        k = (w["section"], w["line"])
        if k != key and cur:
            out.append(cur)
            cur = []
        cur.append(w)
        key = k
    if cur:
        out.append(cur)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ev = []
    lines = lines_from_words(TM["words"])
    for i, ln in enumerate(lines):
        start = ln[0]["start"] - 0.25
        nxt = lines[i + 1][0]["start"] - 0.25 if i + 1 < len(lines) else TM["audio"]["duration_s"]
        end = min(ln[-1]["end"] + 0.6, nxt)
        # \kf durations in centiseconds: a lead-in, then each word from its start to the next word's start.
        parts = [f"{{\\k{round((ln[0]['start'] - start) * 100)}}}"]
        for j, w in enumerate(ln):
            until = ln[j + 1]["start"] if j + 1 < len(ln) else w["end"]
            parts.append(f"{{\\kf{max(1, round((until - w['start']) * 100))}}}{w['text']} ")
        ev.append(f"Dialogue: 0,{ts(start)},{ts(end)},Caption,,0,0,0,,{''.join(parts).strip()}")
    for s in TM["sections"]:
        ev.append(f"Dialogue: 0,{ts(s['start'])},{ts(s['end'])},Mono,,0,0,0,,{s['name']}")
    for b in TM["bars"]:
        ev.append(f"Dialogue: 0,{ts(b['start'])},{ts(b['end'])},Mono,,0,0,44,,bar {b['index']}")
    down = set(TM["downbeats"])
    for t in TM["beats"]:
        color = ass_color(ACCENT) if t in down else ass_color(PAPER)
        size = 36 if t in down else 24
        x, y = W - 24 - size, H - 24 - size
        ev.append(f"Dialogue: 1,{ts(t)},{ts(t + 0.1)},Box,,0,0,0,,{{\\pos({x},{y})\\1c{color}\\p1}}"
                  f"m 0 0 l {size} 0 {size} {size} 0 {size}{{\\p0}}")
    for d in TM["events"]["dropouts"]:
        ev.append(f"Dialogue: 0,{ts(d['start'])},{ts(d['end'])},Flag,,0,0,0,,DROPOUT{' (full)' if d['full'] else ''}")
    ass = OUT / "timing_preview.ass"
    ass.write_text(header() + "\n".join(ev) + "\n", encoding="utf-8")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", f"color=c=0x09080b:s={W}x{H}:r=30",
                    "-i", TM["audio"]["file"],
                    "-vf", f"ass={ass}:fontsdir=assets/fonts",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", str(OUT / "timing_preview.mp4")], check=True)
    print(OUT / "timing_preview.mp4")


if __name__ == "__main__":
    main()
