"""Pre-production step 3: build timing/timing_map.json from the locked track.

- Beats/tempo: librosa beat tracking on the drums stem; bar phase (downbeats) chosen as the beat offset whose
  low-band onset energy is strongest, assuming 4/4.
- Words: MMS forced alignment (torchaudio MMS_FA, the aligner WhisperX-style pipelines use) of lyrics/as_sung.txt
  against the vocals stem. Emissions are computed in overlapping chunks; one global CTC alignment.
- Sections: each lyric section starts at its first word (snapped back to the nearest downbeat within 1 bar);
  Intro before the first vocal, Outro after the last word.
- Events: first vocal, the "(beat)" gap in Bridge 1, every music dropout (drums < 15% of their median or all
  instruments < 30% of theirs, for at least 1.5 s), the final chorus's return, and where the music ends.
  Suno did not put the dropout in Bridge 2 as the lyrics' "(music drops out)" tag asked; the map records where
  the dropouts actually are and leaves bridge2_dropout null.

Usage: .venv/bin/python scripts/timing_map.py   ->  timing/timing_map.json
"""
import hashlib
import json
import re
from pathlib import Path

import librosa
import numpy as np
import torch
import torchaudio

TRACK = Path("audio/track/Ghost in the Machine.wav")
STEMS = Path("audio/stems")
LYRICS = Path("lyrics/as_sung.txt")
OUT = Path("timing/timing_map.json")
VOCAL_STEMS = {"Vocals", "Backing Vocals"}
SR_BEAT = 22050
HOP = 512


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stem(name):
    return STEMS / f"Ghost in the Machine ({name}).wav"


# ---------- lyrics ----------

def parse_lyrics():
    """Return sections: [{name, note, lines: [[display words]]}]. Section names are numbered on repeats."""
    sections, counts = [], {}
    for raw in LYRICS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"\[(.+?)\]\s*(?:\((.+)\))?$", line)
        if m:
            base = m.group(1)
            counts[base] = counts.get(base, 0) + 1
            sections.append({"name": f"{base} {counts[base]}", "base": base, "note": m.group(2), "lines": []})
            continue
        if line == "(beat)":
            sections[-1]["lines"].append(["(beat)"])
            continue
        sections[-1]["lines"].append(line.split())
    # "Chorus 1/2" are only numbered when repeated; "Final Chorus 1" -> "Final Chorus".
    for s in sections:
        if counts[s["base"]] == 1:
            s["name"] = s["base"]
    return sections


def normalize(word):
    w = word.lower().replace("’", "'")
    w = re.sub(r"[^a-z' -]", "", w).replace("-", " ")
    return [p for p in w.split() if p.strip("'")]


# ---------- beats ----------

def beats_and_bars(duration):
    y, sr = librosa.load(stem("Drums"), sr=SR_BEAT, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=HOP, units="frames")
    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=HOP)
    # Low-band onset strength (kick) at each beat; the 4/4 phase with the most kick energy is beat 1.
    low = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP, fmax=150, n_mels=32)
    strength = low[np.clip(beat_frames, 0, len(low) - 1)]
    phase = int(np.argmax([strength[p::4].mean() for p in range(4)]))
    downbeats = beat_times[phase::4]
    bars = []
    for i, t in enumerate(downbeats):
        end = downbeats[i + 1] if i + 1 < len(downbeats) else duration
        bars.append({"index": i + 1, "start": round(float(t), 3), "end": round(float(end), 3)})
    return float(np.atleast_1d(tempo)[0]), beat_times, downbeats, bars, phase


# ---------- word alignment ----------

def align_words(sections):
    bundle = torchaudio.pipelines.MMS_FA
    model = bundle.get_model(with_star=False).eval()
    dictionary = bundle.get_dict(star=None)
    wav, sr = torchaudio.load(stem("Vocals"))
    wav = torchaudio.functional.resample(wav.mean(0, keepdim=True), sr, bundle.sample_rate)

    # Emissions in 20 s chunks with 2 s of context on each side, trimmed and concatenated.
    chunk, ctx = 20 * bundle.sample_rate, 2 * bundle.sample_rate
    pieces = []
    with torch.inference_mode():
        for start in range(0, wav.shape[1], chunk):
            a, b = max(0, start - ctx), min(wav.shape[1], start + chunk + ctx)
            em, _ = model(wav[:, a:b])
            frames_per_sample = em.shape[1] / (b - a)
            lo = round((start - a) * frames_per_sample)
            hi = lo + round(min(chunk, wav.shape[1] - start) * frames_per_sample)
            pieces.append(em[:, lo:hi])
    emission = torch.cat(pieces, dim=1)
    sec_per_frame = wav.shape[1] / bundle.sample_rate / emission.shape[1]

    # Flatten words; each display word may normalize to several aligner tokens ("Oh-oh" -> "oh", "oh").
    words = []
    for si, s in enumerate(sections):
        for li, line in enumerate(s["lines"]):
            if line == ["(beat)"]:
                continue
            for w in line:
                for part in normalize(w):
                    words.append({"display": w, "norm": part, "section": si, "line": li})
    tokens = [dictionary[c] for w in words for c in w["norm"] if c in dictionary]
    aligned, scores = torchaudio.functional.forced_align(emission, torch.tensor([tokens], dtype=torch.int32), blank=0)
    spans = torchaudio.functional.merge_tokens(aligned[0], scores[0].exp())

    out, k = [], 0
    for w in words:
        n = sum(1 for c in w["norm"] if c in dictionary)
        ws = spans[k:k + n]
        k += n
        out.append({**w, "start": ws[0].start * sec_per_frame, "end": ws[-1].end * sec_per_frame,
                    "score": float(np.mean([t.score for t in ws]))})
    # Merge split display words ("Oh-oh") back into one entry.
    merged = []
    for w in out:
        if merged and merged[-1]["display"] == w["display"] and merged[-1]["section"] == w["section"] \
                and merged[-1]["line"] == w["line"] and merged[-1]["_parts"] < len(normalize(w["display"])):
            merged[-1]["end"] = w["end"]
            merged[-1]["score"] = (merged[-1]["score"] + w["score"]) / 2
            merged[-1]["_parts"] += 1
        else:
            merged.append({**w, "_parts": 1})
    return merged


# ---------- events ----------

def stem_rms():
    """Per-stem RMS envelopes (smoothed over 0.5 s) for every non-vocal stem, plus their sum."""
    env = {}
    for f in sorted(STEMS.glob("*.wav")):
        name = re.search(r"\((.+)\)", f.name).group(1)
        if name in VOCAL_STEMS:
            continue
        y, sr = librosa.load(f, sr=SR_BEAT, mono=True)
        r = librosa.feature.rms(y=y, hop_length=HOP)[0]
        k = int(0.5 * SR_BEAT / HOP)
        env[name] = np.convolve(r, np.ones(k) / k, mode="same")
    env["_all"] = sum(env.values())
    times = librosa.frames_to_time(np.arange(len(env["_all"])), sr=SR_BEAT, hop_length=HOP)
    return times, env


def runs(times, mask, min_len):
    out, cur = [], None
    for t, m in zip(times, mask):
        if m and cur is None:
            cur = t
        if not m and cur is not None:
            if t - cur >= min_len:
                out.append((float(cur), float(t)))
            cur = None
    if cur is not None and times[-1] - cur >= min_len:
        out.append((float(cur), float(times[-1])))
    return out


def find_dropouts(times, env, sections):
    drums, total = env["Drums"], env["_all"]
    mask = (drums < 0.15 * np.median(drums)) | (total < 0.30 * np.median(total))
    result = []
    for a, b in runs(times, mask, 1.5):
        inside = [s["name"] for s in sections if s["start"] < b and s["end"] > a]
        result.append({"start": round(a, 3), "end": round(b, 3), "sections": inside,
                       "full": bool(np.mean(total[(times >= a) & (times < b)]) < 0.30 * np.median(total))})
    return result


def snap_to_downbeat(t, downbeats, max_back):
    prior = downbeats[downbeats <= t + 0.05]
    if len(prior) and t - prior[-1] <= max_back:
        return float(prior[-1])
    return float(t)


def main():
    info = torchaudio.info(str(TRACK))
    duration = info.num_frames / info.sample_rate
    sections = parse_lyrics()
    tempo, beat_times, downbeats, bars, phase = beats_and_bars(duration)
    bar_len = 4 * 60 / tempo
    words = align_words(sections)

    sec_out = [{"name": "Intro", "start": 0.0}]
    for si, s in enumerate(sections):
        ws = [w for w in words if w["section"] == si]
        start = snap_to_downbeat(ws[0]["start"], downbeats, bar_len)
        sec_out.append({"name": s["name"], "note": s["note"], "start": round(start, 3),
                        "first_word": round(ws[0]["start"], 3), "last_word": round(ws[-1]["end"], 3),
                        "lines": [" ".join(l) for l in s["lines"]]})
    sec_out.append({"name": "Outro", "start": round(max(w["end"] for w in words), 3)})
    for i, s in enumerate(sec_out):
        s["end"] = sec_out[i + 1]["start"] if i + 1 < len(sec_out) else round(duration, 3)

    times, env = stem_rms()
    dropouts = find_dropouts(times, env, sec_out)
    b2 = next(s for s in sec_out if s["name"] == "Bridge 2")
    b2_drop = [d for d in dropouts if "Bridge 2" in d["sections"]]
    final = next(s for s in sec_out if s["name"] == "Final Chorus")
    # "Beat slams back": first time in the final chorus the bass is back above half its median.
    bass = env["Bass"]
    back = np.where((times >= final["start"]) & (bass > 0.5 * np.median(bass)))[0]
    bass_return = float(times[back[0]]) if len(back) else None
    total = env["_all"]
    loud = np.where(total > 0.5 * np.median(total))[0]
    music_end = float(times[loud[-1]])
    b1 = next(i for i, s in enumerate(sections) if s["name"] == "Bridge 1")
    beat_line = sections[b1]["lines"].index(["(beat)"])
    before = [w for w in words if w["section"] == b1 and w["line"] == beat_line - 1][-1]
    after = [w for w in words if w["section"] == b1 and w["line"] == beat_line + 1][0]

    result = {
        "generated_by": "scripts/timing_map.py",
        "audio": {"file": str(TRACK), "sha256": sha256(TRACK), "duration_s": round(duration, 3),
                  "sample_rate": info.sample_rate},
        "tempo_bpm": round(tempo, 2),
        "time_signature": "4/4 (assumed)",
        "downbeat_phase": phase,
        "beats": [round(float(t), 3) for t in beat_times],
        "downbeats": [round(float(t), 3) for t in downbeats],
        "bars": bars,
        "sections": sec_out,
        "events": {
            "first_vocal": round(words[0]["start"], 3),
            "bridge1_beat_gap": {"start": round(before["end"], 3), "end": round(after["start"], 3)},
            "dropouts": dropouts,
            "bridge2_dropout": b2_drop[0] if b2_drop else None,
            "bridge2_dropout_note": None if b2_drop else
            "No music dropout in Bridge 2 despite the lyric tag; see dropouts for where Suno put them.",
            "final_chorus_return": {"vocal": final["first_word"], "downbeat": final["start"],
                                    "bass_return": None if bass_return is None else round(bass_return, 3)},
            "music_end": round(music_end, 3),
            "last_line": {"start": round(next(w for w in words if (w["section"], w["line"]) ==
                                              (words[-1]["section"], words[-1]["line"]))["start"], 3),
                          "end": round(words[-1]["end"], 3)},
        },
        "words": [{"text": w["display"], "start": round(w["start"], 3), "end": round(w["end"], 3),
                   "score": round(w["score"], 3), "section": sections[w["section"]]["name"], "line": w["line"]}
                  for w in words],
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1) + "\n")
    low = sorted(result["words"], key=lambda w: w["score"])[:8]
    print(f"tempo {tempo:.2f} bpm, {len(beat_times)} beats, {len(bars)} bars, phase {phase}, {len(words)} words")
    for s in sec_out:
        print(f"  {s['name']:<14} {s['start']:7.2f} - {s['end']:7.2f}")
    print("events", json.dumps(result["events"], indent=1))
    print("lowest-confidence words", [(w["text"], w["start"], w["score"]) for w in low])


if __name__ == "__main__":
    main()
