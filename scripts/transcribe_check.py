"""Independent check on the forced alignment: transcribe the vocals stem with faster-whisper (word timestamps).

The transcript is never used as lyrics (as-sung lyrics are the source of truth); it only shows what is sung when.
Usage: .venv/bin/python scripts/transcribe_check.py [model]  ->  timing/whisper_words.json
"""
import json
import sys

import librosa
from faster_whisper import WhisperModel

model_name = sys.argv[1] if len(sys.argv) > 1 else "medium.en"
model = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=12)
# Decode with librosa: faster-whisper's PyAV decoder is incompatible with the installed av version.
audio, _ = librosa.load("audio/stems/Ghost in the Machine (Vocals).wav", sr=16000, mono=True)
segments, info = model.transcribe(audio, language="en",
                                  word_timestamps=True, vad_filter=False, beam_size=5,
                                  condition_on_previous_text=False)
out = []
for s in segments:
    print(f"[{s.start:7.2f} - {s.end:7.2f}] {s.text.strip()}")
    out.append({"start": s.start, "end": s.end, "text": s.text.strip(),
                "words": [{"w": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2),
                           "p": round(w.probability, 3)} for w in s.words]})
json.dump({"model": model_name, "segments": out}, open("timing/whisper_words.json", "w"), indent=1)
