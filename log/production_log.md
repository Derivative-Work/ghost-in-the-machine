# Production log

Append-only. One entry per action: timestamp, step, what, exact command/prompt/script, outputs, why.

## 2026-10-17T11:18:53-04:00 — Setup: repo scaffolding

- **What:** Created directory layout, `.gitignore`, a pre-commit hook rejecting staged files over 50 MiB, and `scripts/manifest.sh` (SHA-256 manifest of large files).
- **Commands:** `mkdir -p log/prompts/suno scripts/hooks docs lyrics audio/track audio/stems reference/inspiration reference/stills archive style timing shots`; `git config core.hooksPath scripts/hooks`
- **Outputs:** `.gitignore`, `scripts/hooks/pre-commit`, `scripts/manifest.sh`, `log/production_log.md`, `log/human_interventions.md`
- **Why:** Brief, "Production rules": set up `.gitignore` and the 50 MiB check before the first commit.
- **Environment:** Claude Code (Opus 5.5); Blender 5.2.2 LTS; ffmpeg 8.0.1; Python 3.14.4; git. Node is **not installed** (needed for Puppeteer). GPU is a **GTX 970**, not the RTX 5090 listed in the brief.

## 2026-10-17T11:19:03-04:00 — Setup: import supplied assets

- **What:** Copied the human-supplied final track, Suno stems archive and inspiration videos from `~/Downloads/ghost-in-the-machine/` into the repo. The originals were left in place. Extracted the stems and moved the MIDI files into `audio/stems/midi/`. Checked each copy against the SHA-256 of its source.
- **Commands:**
  - `cp -p "$SRC/Ghost in the Machine.wav" "$SRC/Ghost in the Machine.mp3" audio/track/`
  - `cp -p "$SRC/Ghost in the Machine Stems.zip" audio/`
  - `unzip -q "audio/Ghost in the Machine Stems.zip" -d audio/stems && mv audio/stems/*.mid audio/stems/midi/`
  - `cp -p "$SRC"/inspiration/* reference/inspiration/`
  - `sha256sum -c` against the source hashes (all OK)
  - `scripts/manifest.sh`
- **Outputs:**
  - `audio/track/Ghost in the Machine.wav` (PCM s16le, 48 kHz stereo, 190.000 s; sha256 `78a7464c…`)
  - `audio/track/Ghost in the Machine.mp3`
  - `audio/Ghost in the Machine Stems.zip`
  - `audio/stems/`: 12 stems (Backing Vocals, Bass, Brass, Drums, FX, Guitar, Keyboard, Percussion, Strings, Synth, Vocals, Woodwinds), each as WAV and MP3, plus `audio/stems/midi/*.mid`
  - `reference/inspiration/`: 5 webm files + 1 VTT (git-ignored, never published)
  - `reference/inspiration.md` (links + hashes)
  - `MANIFEST.sha256` (39 files)
- **Why:** Brief, "Inputs" and "Production rules". Large files are kept out of git and hashed in the manifest. The inspiration videos are linked, not published, so they are left out of the manifest.
- **Note:** Track length is 190.0 s. This resolves the "exact length from the track" open item.

## 2026-10-17T11:21:00-04:00 — Setup: export brief and lyrics

- **What:** Exported the production brief (Claude Doc, rev 43) to markdown. Saved the as-sung lyrics, the source for captions, alignment and shots, and the lyrics as submitted to Suno, which were the human's prompt input. Both lyric texts are verbatim from the brief.
- **Commands:** Read the doc with the Claude Docs connector (`read` on project `X6qhGA5gWTDVtmLZHcsUcp`, node `37e9383a-74ca`). The agent wrote the files directly.
- **Outputs:** `docs/brief.md`, `lyrics/as_sung.txt`, `log/prompts/suno/lyrics_submitted.txt`
- **Why:** Brief, "Inputs": the brief arrives as a markdown export. "Lyrics": the as-sung version is the source of truth, and the submitted version is a Suno prompt that belongs in `log/prompts/`.
- **Still missing (blocks the rest of step 2):** Suno take ID, style prompt, settings, rejected takes. The planning chat export is also missing.

## 2026-10-17T11:23:00-04:00 — Pre-production step 2 (partial): log the track retroactively

- **What:** Logged in `human_interventions.md` the human actions that produced the track: the two lyric exceptions, the Suno run (R4/R1), and supplying the input files. Recorded below the changes Suno made during generation. These are **AI changes**, found with `diff log/prompts/suno/lyrics_submitted.txt lyrics/as_sung.txt` and confirmed by the human listening (per the brief).
- **Suno's changes (AI, not human):**
  1. Filled the empty third `[Chorus]` with four lines ending "Every song just sounds the same".
  2. Dropped the third bridge ("music drops out, close and quiet"), including "The hook, the lights, the open door".
  3. Dropped the key change from the final chorus.
  The generator removed the song's most self-aware moment and its one structural surprise. This is evidence for the video's thesis.
- **Outputs:** `log/human_interventions.md`, this entry.
- **Why:** Brief, pre-production step 2.
- **Still open:** Suno take ID, style prompt, settings and rejected takes go in `log/prompts/suno/` once the human supplies them. Step 2 and checkpoint C2 stay incomplete until then.

## 2026-10-17T11:28:42-04:00 — Inputs: planning chat export and Suno generation record

- **What:** Fetched the shared planning chat. Plain HTTP fetches returned a JavaScript shell page or were blocked by Cloudflare, so the agent rendered the page with headless Chrome via Puppeteer and captured the `chat_snapshots` API response. A first run from the scratchpad and a second run from the repo returned identical messages (32 in total). Converted the snapshot to markdown. Wrote the Suno generation record from the chat and from the human's answers.
- **Commands:**
  - `npm i` (`package.json`: puppeteer 24.43.1)
  - `npx puppeteer browsers install chrome-headless-shell` (installs chrome-headless-shell 148.0.7778.97)
  - `node scripts/fetch_share.mjs https://claude.ai/share/a6ed7466-9b29-4a36-8713-28484e011115 <scratch>/repo_run`
  - `python3 -I scripts/chat_snapshot_to_md.py docs/planning_chat/planning_chat.json <url> > docs/planning_chat/planning_chat.md`
- **Outputs:**
  - `docs/planning_chat/planning_chat.json` (raw snapshot)
  - `docs/planning_chat/planning_chat.md`
  - `log/prompts/suno/generation.md`
  - `package.json`, `package-lock.json`
  - `scripts/fetch_share.mjs`, `scripts/chat_snapshot_to_md.py`
- **Why:** The brief lists the planning chat as an input. Pre-production step 2 needs the style prompt and the take.
- **Environment note:** Chrome needs `--no-sandbox` because Ubuntu's AppArmor restricts unprivileged user namespaces. This is acceptable for loading claude.ai and local render pages. The render pipeline will need the same flag.
- **Step 2 status:** Still missing: the take ID, the rejected take, and the advanced options. C2 stays open but does not block step 1.

## 2026-10-17T11:36:04-04:00 — Environment: Python via uv

- **What:** The system Python 3.14 can't create venvs (`python3.14-venv` is not installed, and installing it needs sudo). Python 3.14 is also a poor target for librosa and WhisperX. The agent installed uv as a user-local binary from its GitHub release, with the checksum verified, then created a Python 3.12 environment.
- **Commands:**
  - Downloaded `uv-x86_64-unknown-linux-gnu.tar.gz` for uv 0.13.1 with `curl` and checked it with `sha256sum -c`
  - `install -m755 uv uvx ~/.local/bin/`
  - `uv python install 3.12` (cpython 3.12.15)
  - `uv sync`
- **Outputs:** `pyproject.toml`, `uv.lock`, `.venv/` (git-ignored; regenerate with `uv sync`). Packages: numpy 2.5.4, Pillow 13.0.0, scikit-learn 1.9.1.
- **Why:** Analysis now and the timing map in step 3 need numpy, librosa and WhisperX.

## 2026-10-17T11:36:04-04:00 — Step 1: extract reference stills

- **What:** For each inspiration video, extracted one still per scene change (ffmpeg scene score > 0.3) and one every 5 s, all scaled to 1280 px wide.
- **Command:** `scripts/extract_stills.sh <video> <slug>`, run for the five videos in parallel (4 m 40 s wall time)
- **Outputs:** `reference/stills/<slug>/{scene,every5s}/*.jpg`, `scene_times.txt`, `scene.log`
  - accept-all: 10 scene, 40 interval
  - end-of-the-show: 27 scene, 72 interval
  - lgtm: 4 scene, 61 interval
  - not-my-fault: 52 scene, 33 interval
  - run-it-again: 66 scene, 58 interval
  - Total 28 MB. Git-ignored and listed in the manifest.
- **Why:** Brief, pre-production step 1.
- **Note:** The scene threshold undercounts cuts in videos that use continuous camera moves (LGTM, Accept All). The style spec says so.

## 2026-10-17T11:36:04-04:00 — Step 1: measure stills, fetch fonts, write style spec

- **What:**
  - Ran k-means palettes (overall and saturated-accent), brightness/saturation stats and pacing per video, plus a pooled average with equal weight per video. Built contact sheets.
  - The agent reviewed all five every-5-s contact sheets by eye.
  - Downloaded the closest OFL fonts from the google/fonts repository.
  - Wrote the style spec and the averaged look.
- **Commands:**
  - `.venv/bin/python scripts/analyze_stills.py`
  - `curl -sSfL https://raw.githubusercontent.com/google/fonts/main/ofl/{inter,instrumentserif,jetbrainsmono}/...`
- **Outputs:**
  - `style/measurements.json`
  - `reference/stills/<slug>/contact_{every5s,scene}.jpg`
  - `assets/fonts/` (Inter, Instrument Serif, JetBrains Mono, OFL texts, SHA256SUMS)
  - `style/style_spec.md`
- **Key decisions (for C1):**
  - Base `#09080b`, paper `#e6e4dc`, primary accent `#d9502f`, secondary `#396ad3`
  - Inter / Instrument Serif Italic / JetBrains Mono
  - 30 fps
  - Faceless primitive humanoid with a screen face, on a dark void with a faint grid
- **Why:** Brief, pre-production step 1.

## 2026-10-17T11:37:11-04:00 — Step 2: Suno take ID recorded

- **What:** The human supplied the Suno share link. The agent followed its HTTP 307 redirect to the song page and recorded the take ID in the generation record. The page title "Ghost in the Machine" matches.
- **Command:** `curl -sS -o /dev/null -w '%{redirect_url}' https://suno.com/s/JgJfkiYbm5CbkSZm` → `https://suno.com/song/560f899d-2701-4829-ad85-e4b57b702506?sh=JgJfkiYbm5CbkSZm`
- **Outputs:** `log/prompts/suno/generation.md` (Chosen take ID row)
- **Why:** Brief, pre-production step 2, and the end card's "Music: Suno v6 (take ID from the log)".
- **Step 2 status:** The rejected take's ID and the advanced options are still unrecorded. They are nice to have, not blocking. C2 can be closed at the human's discretion.

## 2026-10-17T11:39:56-04:00 — Step 1 / C1: averaged-style test frame and review sheet

- **What:** Built one S02-style still with the full planned pipeline:
  - Puppeteer renders the generic UI textures and the transparent caption/chrome overlay from HTML. All HTML shares `overlays/tokens.css`.
  - Blender 5.2.2 Eevee renders the 3D plate: dark void, 1 m grid floor, faceless primitive humanoid with a screen face, two floating screens, cool key and accent rim lights, light haze, compositor bloom, Standard view transform.
  - ffmpeg composites the overlay onto the plate.
  - A review sheet places 10 reference stills (two per video) above the test frame.
- **Iterations:**
  1. A half-res preview showed four problems: the grid mask used object coordinates on a scaled plane and drew wedges; the character was underlit (key 120 W); the red haze was too strong (density 0.012, rim 350 W); the counter screen sat behind the head.
  2. Fixes: world-space Position for the grid; key 600 W; rim 160 W; density 0.004; counter moved to (5.2, 4.6, 2.4). The second preview passed review.
- **Commands:**
  - `node scripts/render_html.mjs overlays/panels/{consent,counter}.html renders/draft/c1/panel_{consent,counter}.png 1200 700`
  - `node scripts/render_html.mjs overlays/test_frame.html renders/draft/c1/overlay.png 1920 1080`
  - `blender -b --factory-startup --python scenes/blender/c1_test_frame.py -- renders/draft/c1 renders/draft/c1/plate_preview.png 50` (twice)
  - The same command at 100% → `plate.png` (21 s for the first, uncached render, then ~4 s at full res on the GTX 970)
  - `ffmpeg -i plate.png -i overlay.png -filter_complex overlay -frames:v 1 test_frame.png`
  - `.venv/bin/python scripts/c1_sheet.py renders/draft/c1/test_frame.png renders/draft/c1/c1_review_sheet.jpg`. The first run failed because three still numbers were mis-mapped from the contact-sheet grid; they were corrected to lgtm 0034, not-my-fault 0032, run-it-again 0029.
- **Outputs:** `renders/draft/c1/{panel_consent,panel_counter,overlay,plate_preview,plate,test_frame}.png`, `renders/draft/c1/c1_review_sheet.jpg` (git-ignored, in the manifest). Code: `overlays/`, `scenes/blender/c1_test_frame.py`, `scripts/render_html.mjs`, `scripts/c1_sheet.py`.
- **Why:** Brief, checkpoint C1: `style_spec.md` plus a contact sheet of reference stills beside a test frame in the averaged style.
- **Agent's own critique for C1:** The test frame is 3D-led. In the references, most compositions are type-led 2D UI with much larger lyric type. The 2D shots (S03, S05–S07, S10–S11, S14–S16) should push the caption to 12–18% of frame height.
- **Status:** Stopped at C1, waiting for human approval.

## 2026-10-17T11:44:06-04:00 — C1 approved; style spec finalized

- **What:** Replaced the spec's "Open questions for C1" section with the recorded decisions. Moving on to pre-production step 3 (timing map).
- **Outputs:** `style/style_spec.md`
- **Why:** Checkpoint C1 approved (see `human_interventions.md`).

## 2026-10-17T11:53:50-04:00 — Step 3: timing map

- **What:**
  - Beat tracking on the drums stem (librosa).
  - Forced alignment of `lyrics/as_sung.txt` against the vocals stem (torchaudio MMS_FA: 20 s emission chunks with 2 s context, one global CTC alignment).
  - Sections from the first word of each section, snapped to the downbeat.
  - Dropouts, music end and last line from the non-vocal stems' RMS.
- **Environment:**
  - Added librosa 1.0.0, soundfile, torch 2.8.0+cpu, torchaudio 2.8.0+cpu (CPU index, since the GTX 970 is sm_52) and faster-whisper.
  - The MMS_FA model was downloaded to `~/.cache/torch/hub/checkpoints/model.pt` and the faster-whisper `medium.en` model to the HF cache. Both are regenerable, not archived.
- **Results:**
  - Tempo **123.05 bpm**. The style prompt asked for 120. Beat interval median 0.488 s, std 9 ms. 368 beats, 92 bars, 4/4 assumed. Downbeat phase is 2, chosen by kick energy.
  - 309 words.
  - Sections: Intro 0–12.03, Verse 1 –27.77, Bridge 1 –49.39, Pre-Chorus 1 –59.19, Chorus 1 –96.27, Verse 2 –111.85, Bridge 2 –125.46, Pre-Chorus 2 –141.01, Chorus 2 –156.50, Final Chorus –189.76, Outro –190.00 (s).
- **Cross-check:**
  - Independent faster-whisper (`medium.en`) transcription of the vocals stem. Whisper skipped 0–30 s on the full run, so that span was rerun alone.
  - 288/309 words matched; start difference median 86 ms, p90 314 ms.
  - Whisper puts line-initial words 0.4–0.6 s earlier, but nearly every MMS line start sits on a vocal-stem onset (±50 ms), so the agent kept MMS. Unmatched words are Whisper mishearings: hum→home, line→life, ghost→ghosts.
  - Whisper hears "the lights are fading **now**" where the as-sung lyrics say "out", twice. Flagged for the human's ear check; the lyrics were not changed.
- **Found against the brief:**
  - **There is no music dropout in Bridge 2.** Drums and bass play throughout 111.85–125.46.
  - Suno put dropouts here instead:
    - Intro 4.5–11.8
    - Bridge 1 second half into Pre-Chorus 1, 43.8–51.1: drums out under "Maybe someone wrote it…"
    - A full stop at the end of Chorus 1, 90.5–92.2: under its last "We are the ghost in the machine"
    - **Pre-Chorus 2, 127.8–134.9:** drums and bass out under "And the servers hum… neon sky"
    - The ending, 186.5–190.0
  - In the final chorus, vocals enter at 156.73 but the bass returns at **158.52**, the actual "slam".
  - The music decays from 187.15, and the last line (187.64–189.76) sits over the tail.
- **Commands:**
  - `.venv/bin/python scripts/timing_map.py` (run 3 times: first pass; dropout/events rewrite; last_line index fix)
  - `.venv/bin/python scripts/transcribe_check.py`. It first failed because faster-whisper's PyAV decoder is incompatible with the installed av, so the script now decodes with librosa.
  - Ad-hoc per-bar stem-energy and onset analyses (stdin scripts; results in this entry)
  - `.venv/bin/python scripts/c3_preview.py`
- **Outputs:**
  - `timing/timing_map.json`, `timing/whisper_words.json`
  - `renders/draft/c3/timing_preview.{ass,mp4}` (960×540, 30 fps, captions, section/bar labels, beat flashes, dropout flags)
  - Check frames `renders/draft/c3/check_*.png`
- **Why:** Brief, pre-production step 3 and checkpoint C3.
- **Status:** Stopped at C3. The human checks sync by ear; corrections go in the intervention log.
