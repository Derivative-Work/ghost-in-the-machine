"""Per-frame music envelopes from the stems, for everything that reacts to the music (v3 motion rules).

At the video frame rate (30 fps), for the whole video length (zeros after the audio ends):
  kick      0..1, decaying pulse on each low-band drum onset
  bass_on   onset times of bass notes (s), for the floor ripples
  synth     0..1, smoothed synth loudness
  vocal     0..1, smoothed lead-vocal loudness
  mouth     5 bands 0..1 of the lead vocal's spectrum (the robot's equalizer mouth)

Usage: .venv/bin/python scripts/stem_envelopes.py  ->  timing/stems.json
"""
import json
from pathlib import Path

import librosa
import numpy as np

FPS = 30
SR = 22050
HOP = SR // FPS  # 735 samples = one video frame
STEMS = Path("audio/stems")
SHOTS = json.loads(Path("shots/shots.json").read_text())
N = SHOTS["total_frames"]


def stem(name):
    y, _ = librosa.load(STEMS / f"Ghost in the Machine ({name}).wav", sr=SR, mono=True)
    return y


def fit(a):
    out = np.zeros(N, dtype=np.float32)
    out[:min(N, len(a))] = a[:N]
    return out


def norm(a, pct=98):
    hi = np.percentile(a, pct) or 1.0
    return np.clip(a / hi, 0, 1)


def smooth(a, k):
    return np.convolve(a, np.ones(k) / k, mode="same")


def decay_pulses(times, decay_s=0.18):
    env = np.zeros(N, dtype=np.float32)
    for t in times:
        f0 = int(round(t * FPS))
        span = np.arange(f0, min(N, f0 + int(decay_s * FPS * 5)))
        env[span] = np.maximum(env[span], np.exp(-(span - f0) / (decay_s * FPS)))
    return env


def main():
    drums = stem("Drums")
    low = librosa.onset.onset_strength(y=drums, sr=SR, hop_length=HOP, fmax=150, n_mels=32)
    kicks = librosa.onset.onset_detect(onset_envelope=low, sr=SR, hop_length=HOP, units="time", backtrack=False,
                                       delta=0.25)
    bass = stem("Bass")
    bass_on = librosa.onset.onset_detect(y=bass, sr=SR, hop_length=HOP, units="time", delta=0.3)
    synth = norm(smooth(librosa.feature.rms(y=stem("Synth"), hop_length=HOP)[0], 3))
    vox = stem("Vocals")
    vocal = norm(smooth(librosa.feature.rms(y=vox, hop_length=HOP)[0], 2))
    spec = np.abs(librosa.stft(vox, n_fft=2048, hop_length=HOP))
    freqs = librosa.fft_frequencies(sr=SR, n_fft=2048)
    edges = [150, 300, 600, 1200, 2400, 5000]
    bands = [norm(smooth(spec[(freqs >= a) & (freqs < b)].mean(axis=0), 2)) * vocal[:spec.shape[1]]
             for a, b in zip(edges, edges[1:])]
    out = {
        "fps": FPS, "frames": N,
        "kick": np.round(decay_pulses(kicks), 3).tolist(),
        "kick_times": np.round(kicks, 3).tolist(),
        "bass_on": np.round(bass_on, 3).tolist(),
        "synth": np.round(fit(synth), 3).tolist(),
        "vocal": np.round(fit(vocal), 3).tolist(),
        "mouth": [np.round(fit(b), 3).tolist() for b in bands],
    }
    Path("timing/stems.json").write_text(json.dumps(out) + "\n")
    print(f"{len(kicks)} kicks, {len(bass_on)} bass onsets, {N} frames; vocal mean {np.mean(vocal):.2f}")


if __name__ == "__main__":
    main()
