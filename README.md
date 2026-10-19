# Ghost in the Machine

An AI-made, code-animated music video: a glossy pop song about AI that is deliberately the statistical average of the
AI-made songs about AI it belongs to. Claude Code (Opus 5.5) wrote and rendered every frame with Blender, JavaScript
and ffmpeg; Suno v6 made the music. A human only approved or rejected work, corrected sync, fixed technical failures
and ran Suno, and every such action is logged.

## Downloads

Large files stay out of git and are published as a **GitHub Release** of this repository (*link added at
publish*). The release holds everything that can't be regenerated, plus the finished videos:

- the main video (3840×2160) and the vertical cut (2160×3840);
- the Suno track, stems and MIDI, and the mastered track;
- the session transcripts.

Everything else, every plate, overlay frame, animatic and superseded cut, regenerates from the code with the commands
in the production log. [MANIFEST.sha256](MANIFEST.sha256) lists all of them with SHA-256 hashes to check a rebuild
against. The reference stills are not published; [reference/stills.tsv](reference/stills.tsv) says where each came
from.

## The making-of record

- [docs/brief.md](docs/brief.md): the production brief and shot list.
- [log/production_log.md](log/production_log.md): every action the agent took, with commands and outputs.
- [log/human_interventions.md](log/human_interventions.md): every human action, with the rule that allowed it.
- [log/prompts/](log/prompts/): every prompt sent to Suno and other models.
- [docs/handoff.md](docs/handoff.md): current state, setup and how to render.

## Licences

- **Video and assets:** [CC BY-NC-SA 4.0](LICENSE-media.md). That file lists exactly what it covers, and what it
  doesn't (fonts, reference stills).
- **Code:** [MIT](LICENSE).

## Credits

- **Music:** Suno v6, generated and chosen by a human. Lyrics by Claude, merged by a human, revised by Suno.
- **Animation, edit, captions and thumbnail:** Claude Code with Claude Opus 5.5.
- **Mastering:** Claude, with music-deslop, a post-filter model for AI-generated music that Claude Code built and
  trained from a human-written spec, on Creative Commons audio only. The model is private for now. Settings and provenance are in the production log ("Audio master").
- **Tools:** Blender 5.2 (Eevee), ffmpeg with libx264, Node.js with Puppeteer and Chrome headless shell, Python with
  NumPy, Pillow, librosa, soundfile, scikit-learn, PyTorch and faster-whisper (lyric alignment).
- **Fonts:** [Inter](https://github.com/rsms/inter), [Instrument Serif](https://github.com/Instrument/instrument-serif)
  and [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono), SIL Open Font License 1.1.

### Mastering model training data

The music-deslop model was trained only on audio from these datasets, each licensed under
[Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/). The audio was cut into
segments, made stereo, mixed, processed (reverb, EQ, compression, mastering, codecs and other degradations) and used
to synthesise training pairs. No dataset audio is in this repository or in the video.

- **Slakh2100** (redux mixes). Ethan Manilow, Gordon Wichern, Prem Seetharaman and Jonathan Le Roux, "Cutting Music
  Source Separation Some Slakh: A Dataset to Study the Impact of Training Data Quality and Quantity", IEEE WASPAA
  2019. https://zenodo.org/records/4599666
- **VocalSet 1.2.** Julia Wilkins, Prem Seetharaman, Alison Wahl and Bryan Pardo, "VocalSet: A Singing Voice
  Dataset", ISMIR 2018. https://zenodo.org/records/1442513
- **CSTR VCTK Corpus 0.92.** Junichi Yamagishi, Christophe Veaux and Kirsten MacDonald, "CSTR VCTK Corpus: English
  Multi-speaker Corpus for CSTR Voice Cloning Toolkit (version 0.92)", University of Edinburgh, The Centre for Speech
  Technology Research, 2019. https://doi.org/10.7488/ds/2645

The degraded training inputs were also made with the
[ACE-Step 1.5 VAE](https://huggingface.co/ACE-Step/Ace-Step1.5) (MIT), the
[Descript Audio Codec](https://github.com/descriptinc/descript-audio-codec) (MIT) and FFmpeg (LAME, the native AAC
encoder and libopus). No generator output (Suno, ElevenMusic or ACE-Step songs) was used for training.

## Inspiration

The genre references are linked, never redistributed: [reference/inspiration.md](reference/inspiration.md).
