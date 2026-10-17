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

## 2026-10-17T11:58:32-04:00 — Brief updated for the track's real dropouts (doc rev 43 → 54)

- **What:** Edited the brief (Claude Doc) per the human's choice, then mirrored the same edits into `docs/brief.md`:
  - Step 3 now says "the music dropouts" instead of "the Bridge 2 dropout".
  - The shot-list intro explains that Bridge 2 has no music drop and the drop falls in Pre-Chorus 2.
  - S07 notes the drums drop out at 43.8 s.
  - S14: hard freeze on "Have" while the music keeps playing.
  - S17: the Pre-Chorus 2 dropout (127.8–134.9 s) is the low point; racks snap back when the drums return, with `Lyric goes here` on the snap-back.
  - S19 is anchored to the bass return (158.5 s).
  - S22 runs past the audio end.
  - "End card (S20)" corrected to S23. This was a typo; the end card is S23 in the table.
  - The frame-rate/length open item is resolved: 30 fps, 190.0 s, 123 bpm.
  - Machine row: drafts on a GTX 970.
- **Commands:** Claude Docs `update` (11 `replace` ops on node `37e9383a-74ca`, rev 54), verified with a `read` view since rev 43. Then a Python replace script on `docs/brief.md`.
- **Outputs:** Brief doc rev 54; `docs/brief.md`
- **Why:** Human instruction (see `human_interventions.md`); C3 findings in the step 3 entry.
- **Lyrics:** "out" confirmed by the human. `lyrics/as_sung.txt` and the timing map are unchanged.

## 2026-10-17T12:01:20-04:00 — Step 4: fix the seeds

- **What:**
  - **Seed config:** `config/seeds.json` is the single source of seeds: main 41, bridge_second_run 42, restart 43.
  - **Helpers:** `overlays/lib/seed.js` (mulberry32 PRNG with the seed from the URL) and `scenes/blender/lib/gitm_seeds.py` (`random.Random` per seed name). Every frame is a pure function of (t, seed); nothing accumulates state between frames.
  - **JS frame harness:** `scripts/render_frames.mjs` renders any HTML scene with `window.renderFrame(t)` to transparent PNGs, with the seed resolved by name.
  - **First seeded scene:** `overlays/scenes/the_rain.html` (S09/S18). Sizes and speeds scale with frame height.
  - **Check:** `scripts/check_seeds.sh` greps for unseeded randomness, renders the JS rain frame 90 and a Blender seeded scatter twice at seed 41 and once at 42, and compares SHA-256s.
- **Iterations:**
  1. Blender run a ≠ run b by hash. A pixel comparison showed 0 differing pixels; only the PNG metadata stamps (Date, RenderTime) differed. Added `scenes/blender/lib/gitm_render.py:strip_metadata`, so identical pixels now give identical bytes.
  2. A visual check showed the rain was resolution-dependent (absolute pixel sizes). Scaled it by H/1080.
- **Result:** PASS. JS seed 41 a = b (`dc4fa148…`), seed 42 differs. Blender seed 41 a = b (`867a3a1d…`), seed 42 differs.
- **Commands:** `scripts/check_seeds.sh` (3 runs; outputs in `renders/draft/seed_check/<timestamp>/`)
- **Caveat:** Reproducibility is per machine. GPU and driver differences can change pixels for the same seed between the GTX 970 and the RTX 5090. The seed-42 split screen and all finals will be rendered on the 5090, and `check_seeds.sh` must be rerun there.
- **Why:** Brief, pre-production step 4.

## 2026-10-17T12:02:54-04:00 — Step 5: pipeline per shot

- **What:** `shots/build_shots.py` encodes the brief's 23 shots (doc rev 54). For each shot it records the lyric or event anchor, the pipeline, the Blender plate name, the JS layers and the seed name. It resolves anchors against the timing map, with cuts snapped to the nearest downbeat within half a bar, otherwise 0.1 s early. It writes the machine-readable edit list and a generated table.
- **Command:** `.venv/bin/python shots/build_shots.py`. The first run failed because S21 used line index 8; the final chorus's last line is index 7.
- **Outputs:** `shots/shots.json`, `shots/pipeline.md`
- **Result:**
  - Total 198.96 s (5969 frames at 30 fps). The audio ends at 190.00; S22 (1.2 s) and S23 (8 s) run past it.
  - Longest shots: S09 37.1 s (the whole Chorus 1, as briefed), S20 19.4 s, S18 17.4 s, S17 15.6 s.
  - S19 cuts at 158.45, the downbeat at the bass return.
  - S18 holds `[output truncated]` from the chorus cutoff to the slam.
- **Pipelines:**
  - 9 JS-only shots
  - 6 Blender + JS
  - 3 Blender-only
  - 2 Blender + ffmpeg (S19 split, S20 grid)
  - 1 JS + ffmpeg (S22)
  - 1 ffmpeg (S23)
  - Global caption and chrome layers run over S01–S22.
- **Why:** Brief, pre-production step 5. `shots.json` drives the C4 animatic and the final renders.

## 2026-10-17T12:25:36-04:00 — C4: animatic v1

- **What:** Built the full production pipeline and rendered every shot at final timing, rough and low-res.
  - **Shot list:** `shots/build_shots.py` rewritten with a plate mode per shot: render, hold (freezes), hold_then (S17), split (S19), js (2D shots and the S20 grid). It now also records big captions for the 2D shots (per the C1 critique) and generates the Blender render jobs.
  - **Seeds:** added `thumbnail_tiles` (1001–1023) to `config/seeds.json` for the S20 neighbour tiles.
  - **Blender:**
    - `scenes/blender/lib/gitm_scene.py`: shared palette, materials, character rig, world, lights, bloom, easing and beat pulse.
    - `scenes/blender/plates.py`: 7 plates (default_cube_boot, robot_screens, robot_shrug, server_racks, chorus_orbit, theater_seats, robot_tear) plus thumbnail tiles. Each sets every animated value from t alone.
    - `scripts/render_plates.sh` runs all jobs.
  - **Screen textures:** `overlays/panels/{chat,terminal}.html`.
  - **Overlay:**
    - `overlays/video.html` + `overlays/video.js`: one page renders every JS layer for any frame (captions with accent/emotional words, strike-through, Lyric goes here; chrome with the version schedule, seed labels and FPS gag; banner, cursor, TODO, devtools flicker/side/full with console log, icon strips, progress 1/2 and 2/2, stamp, spinning arrow, regen buttons, score, the-rain, output truncated, thumbnail grid, reload, end card; optional review HUD).
    - `overlays/captions_style.json` holds accent and emotional words per line.
    - `scripts/export_overlay_data.py` writes `overlays/data/data.js`.
    - `scripts/render_frames.mjs` now reports page and console errors and passes extra query params.
  - **Assembly:** `scripts/assemble.py` builds the plate sequence, renders the overlay in 6 parallel Puppeteer processes, composites in Python and pipes raw RGB to ffmpeg with the audio padded to the video's length.
  - **Review:** `scripts/sheet.py` makes labelled contact sheets.
- **Iterations:**
  - Plate smoke test, one frame per job. In chorus_orbit the screen ring blocked the robot and the fixed rim light washed it orange. Fixes: camera inside the ring, screens facing inward, two soft keys plus a weak rim. Second test: the orbit showed the robot's back, so the robot now turns with the camera.
  - Overlay test frames:
    - Captions were missing everywhere but the last line. Bug: each line's display window read the next line's start before it was computed (NaN). Fixed with two passes.
    - Layout collisions fixed: banner covering caption, icons crossing the big caption, stamp on caption, heavy rain burying caption, S21 button under caption. The banner now drops from the top, icons run along the top band, the stamp moved right, heavy-rain alpha is divided by √density, captions got a dark glow, and the button moved up.
    - S20/S21 test frames were first empty. Agent error: `| head -3` killed node with SIGPIPE.
  - Composite attempts. Failed outputs were kept in `archive/renders/`:
    1. `apad` + `-shortest` stopped at the audio's end (189.5 s), with an internal ENOSPC; the disk was fine. → `animatic_v1_truncated_at_audio_end.mp4`
    2. `apad=whole_dur` padded by the full duration, giving 389 s of audio. → `animatic_v1_audio_389s.mp4`
    3. With `pad_dur`, 61 frames were dropped. Cause: a pixel-format change between RGB and RGBA plates made ffmpeg reinit the filter graph. → `animatic_v1_dropped_61_frames.mp4`
    4. After making all plates RGBA, 50 frames were still dropped. Causes: Blender PNGs carry a gAMA chunk that PIL's don't, and Chrome writes opaque frames as RGB. → `animatic_v1_dropped_50_frames.mp4`
    5. Final approach: composite in Python and pipe raw RGB. All 5969 frames; video 198.967 s, audio 198.960 s.
- **Commands:**
  - `scripts/render_plates.sh animatic 640 360 8 2`: 640×360, 8 TAA samples, every 2nd frame held. 5 m 49 s total, about 0.07 s per frame on the GTX 970.
  - `.venv/bin/python scripts/export_overlay_data.py`
  - `.venv/bin/python scripts/assemble.py animatic 640 360 2 6 --hud --name animatic_v1` (overlay render 2 m 40 s, composite 24 s)
- **Outputs:**
  - `renders/animatic/animatic_v1.mp4` (640×360, 30 fps, 198.97 s, with a shot/timecode HUD)
  - `renders/animatic/{plates,plate_seq,overlay}/`
  - Review sheets `renders/animatic/*sheet*.jpg`
- **Known rough spots (agent review):**
  - S13: the tear spinner sits slightly off the face.
  - S12: the seats are dark and tightly framed.
  - S08: the line chart is faint.
  - S09/S18: rain density over the robot is to be tuned.
  - All plates render at 2 fps-steps.
- **Why:** Brief, checkpoint C4: every shot as a rough low-res render at final timing; human approves the cut.
- **Status:** Stopped at C4.

## 2026-10-17T13:07:07-04:00 — Brief: v2 shot list (doc rev 54 → 65)

- **What:**
  - Replaced the 23-shot table with the approved 57-shot v2: cuts on every lyric line, about 2 bars; 3D coverage from several cameras; alternating 2D type-led shots; the new scenes.
  - Rewrote the shot-list intro to explain v2.
  - Updated every shot-ID reference: dropout S17 → S38, end card S23 → S57, vertical cut S14–S22 → S35–S56 (about 79 s), thumbnail S19 → S47, open item S22/S23 → S56/S57.
  - Seeds: added 44–50 for the 4-up and 9-up splits and 1001–1023 for the grid tiles (step 4 text and end card "Seeds: 41–50").
- **Agent errors:**
  1. Two find/replace ops quoted the second half of a text-run-split ID and produced "S135" and "S147". Corrected in the next call (rev 64).
  2. One stale reference (S22/S23 in Open items) was found in the export and fixed (rev 65).
- **Commands:** Claude Docs `update` (guarded table replace, `ifHash 9b5702e0` / `ifRev 54`, plus 7 find replaces; then 2 + 1 fixes), verified by `read` views and a markdown `export`. `docs/brief.md` was mirrored with a Python replace script.
- **Outputs:** Brief doc rev 65; `docs/brief.md`
- **Note for the human:** The vertical cut (bridge through ending) is about 79 s. The original brief estimated 45–60 s for the same range, which was already off in v1.
- **Why:** The human approved v2 (see `human_interventions.md`).

## 2026-10-17T13:27:23-04:00 — C4: animatic v2 (57 shots)

- **What:** Rebuilt the pipeline for the v2 shot list and rendered animatic v2.
  - **Shot list:** `shots/build_shots.py` encodes the 57 shots with a camera and effects per plate, the JS layers, Chorus 2's degrade levels and whip/glitch transitions. Cuts now snap to a downbeat only within a quarter bar (otherwise 0.1 s before the line, never mid-word). New anchors: bars, the Chorus 1 full stop, the Pre-Chorus 2 drum return, the Chorus 2 cutoff, the end of the beat. Result: 57 shots, average 3.49 s (v1: 8.7 s); the longest are the intentionally static freeze shots S37 (6.45 s) and S38 (9.43 s).
  - **Seeds:** added `split_extra` 44–50 to `config/seeds.json` for the 4-up and 9-up splits.
  - **Blender:** `scenes/blender/plates.py` rewritten as 6 sets with named cameras and effects:
    - robot: wide, medium, low, face, screens, screen_close; screens_power_on, eyes_wake, eyes_dim, shrug
    - chorus: orbit, orbit2, low_up, wide_static, topdown, dance_wide, dance_low; missing_texture (magenta checker), head_up, dance, lights_fade, clip
    - racks: aisle, chart
    - seats: front, reverse_end (new THE END screen, `overlays/panels/the_end.html`)
    - tear
    - default_cube_boot
    - New `probe` mode renders a job's middle frame for smoke tests.
  - **Overlay:** `overlays/video.html` and `overlays/video.js` rewritten. New layers: terminal_boot, hearts, chat_autocomplete (the reply types each word 0.24 s before it is sung), big_accept, avg_merge, giant_counter (S40 continues S18's count ×10), loading_textures, nine_replies (CSS-degraded in S45), code_stream, black_stop, loading_verse2 (the ETA counts up), per-tile seed labels for the splits, and the feed (zoom, tiles going dark per beat, constant scroll, accelerating scroll with streaks, a decelerating stop that lands on this video again, then hold).
  - **Assembly:** `scripts/assemble.py` rewritten. Each worker builds its frame's plate (rendered / held / 2-up halves / 4- and 9-up grids), degrades the plate only (resolution, JPEG blocks, magenta drift; captions stay crisp), composites the overlay, applies whip or glitch transitions, and pipes raw RGB to ffmpeg.
- **Iterations:**
  - **Plate probes** of all 44 jobs: S33's seat backs hid THE END; camera raised.
  - **Overlay test frames:** the giant button fell back to a serif font (`.btn` had no font-family); split seed labels wrapped; S23/S45's 3×3 reply grid collided with big captions, so those two shots use normal captions.
  - **First composite** failed with FileNotFoundError on `chorus-orbit__bridge_second_run/04751.png`. The step-2 grid of a lagged split render starts at the shot's frame, but the clamp used the job's first frame. Fixed: clamp to the first and last frames on the grid.
  - **Review:** S40's counter restarted lower than S18 ended; it now continues.
- **Commands:**
  - `blender … plates.py -- probe <i> renders/animatic_v2/probe 480 270 8 0.6` for each job
  - `scripts/render_plates.sh animatic_v2 640 360 8 2` (44 jobs + 23 tiles, about 7 min)
  - `.venv/bin/python shots/build_shots.py`
  - `.venv/bin/python scripts/export_overlay_data.py`
  - `.venv/bin/python scripts/assemble.py animatic_v2 640 360 2 6 --hud --name animatic_v2` (overlay 2 m; composite 21 s)
  - S40 overlay frames re-rendered with `render_frames.mjs`, then `--composite-only`
- **Outputs:**
  - `renders/animatic_v2/animatic_v2.mp4` (640×360, 30 fps, 198.97 s, 5969 frames verified, audio 198.96 s, review HUD)
  - `renders/animatic_v2/{plates,overlay,probe,review}/` and sheets
  - Animatic v1 moved to `archive/renders/animatic_v1_rejected_too_static.mp4`
- **Why:** The human approved v2 after C4 feedback.
- **Status:** Stopped at C4 for review of v2.

## 2026-10-17T13:48:51-04:00 — Brief: v3 motion rules and shot changes (doc rev 65 → 69)

- **What:**
  - Added a "Motion rules (v3)" section to the shot list: music-driven motion, robot performance, kinetic captions, moving 2D shots, camera moves, transitions.
  - Replaced the shot table (guarded replace, `ifHash 6d199733` / `ifRev 62`) with the v3 rows:
    - Changed: S07, S17, S20, S21, S22, S23, S30, S31, S32, S39, S42–S45, S52–S54.
    - Inserted S11b (song recognition). Inserted shots take a letter suffix, so no existing ID changes.
  - Intro now says 58 shots. Step 4 adds seeds 51–56 for the S31 montage; the end card reads "Seeds: 41–56".
  - Mirrored into `docs/brief.md` (the table generated from the v2 table file with per-row edits).
- **Why:** The human approved items 1–7.

## 2026-10-17T14:10:07-04:00 — C4: animatic v3 (items 1–7)

- **What:** Built and rendered animatic v3 with the approved additions.
  - **Music:**
    - `scripts/stem_envelopes.py` writes `timing/stems.json` at 30 fps: 331 kick onsets as decaying pulses, 284 bass onsets, synth and vocal envelopes, and 5 vocal spectrum bands.
    - Plates: lights ×(1+0.6·kick), screens ×(0.75+0.6·synth), a bass ripple ring in the floor shader (new `ripple_r`/`ripple_amp` nodes).
    - Assembly: a 4% punch-in on every downbeat (3D plates only).
  - **Robot performance** (`gitm_scene.py`: `build_character` + `perform`; schedule in `shots.json` "performance"):
    - A 5-bar equalizer mouth driven by the vocal bands.
    - Eye glyph sets (happy, squint, heart, sleepy, xx) chosen by lyric.
    - Point and reach_up gestures, eased.
  - **Kinetic captions** (`overlays/video.js`): per-word pop with overshoot and a rise; lines lift away on exit. In 2D shots the current word fills the frame with the line small beneath. The accent word pops like the others and settles at normal size.
  - **2D motion:** the grid drifts and brightens on the kick, faint windows drift behind, content pushes in 4.5% per shot, and an idle cursor wanders.
  - **Camera:** DOF pulls (wide, medium); fast 180° chorus entries; dolly zoom (lens 47→18 mm while dollying 5.0→1.9 m); a crane in the racks; the lullaby camera.
  - **Transitions:** zoom-throughs S07→S08 and S22→S23 (8 frames each way); a glitch at each montage re-roll.
  - **New moments:**
    - S11b song recognition
    - S17 crib mobile of server racks (sleepy, swaying)
    - S22/S44 3D TOKENS letters (Inter, extruded)
    - S23/S45 SAME stamps
    - S30 million-line diff
    - S31 regenerate montage: 6 re-rolls at seeds 51–56 with strong layout variation, plus a badge
    - S32 the robot seated in the theater
    - S52–S55 the feed of dancing tiles: 24 dance renders, one per tile seed plus main
  - **Shot list:** `shots/build_shots.py` adds S11b (letter-suffix IDs), montage segments and jobs, zoom_out points and the performance schedule. 58 shots, average 3.43 s, 74 render jobs.
- **Iterations:**
  - **Probes:** the mouth rendered on the chest. Cause: Blender 5's `transform_apply(scale=True)` defaults also apply location and rotation, leaving every rounded box's origin at the world origin, so scaling the mouth moved it. The same bug put the floating token cubes at double height in v1/v2. Fixed by applying scale only.
  - **Overlay tests:** the accent word's lasting 1.12× scale overlapped its neighbours, so the accent now settles at 1×; the diff body ran over its header; the SAME stamps were initially under the replies in the DOM; the 2D push scale leaked into non-2D shots and is now reset per frame.
- **Commands:**
  - `.venv/bin/python scripts/stem_envelopes.py`
  - `blender … plates.py -- probe …` for 27 distinct variants
  - `scripts/render_plates.sh animatic_v3 640 360 8 2` (74 jobs + tiles)
  - `.venv/bin/python scripts/export_overlay_data.py` (now includes the kick and vocal envelopes)
  - `.venv/bin/python scripts/assemble.py animatic_v3 640 360 2 6 --hud --name animatic_v3` (3 m 11 s)
- **Outputs:** `renders/animatic_v3/animatic_v3.mp4` (5969 frames verified, video 198.967 s / audio 198.960 s); `renders/animatic_v3/{plates,overlay,probe,review}/`; sheets.
- **Not done (not chosen):** full 30 fps rendering. Plates still step 2.
- **Why:** The human approved items 1–7.
- **Status:** Stopped at C4 for review of v3.

## 2026-10-17T14:40:06-04:00 — Brief: v4 allusions (doc rev 69 → 71)

- **What:**
  - Replaced the shot table (guarded, `ifHash ece6da75` / `ifRev 69`) with the v4 rows: S09, S10, S12, S13, S15, S16, S20, S22, S24–S27, S30, S31–S34, S44, S52 changed, and S30b (LOOKS GOOD ship) inserted.
  - Added an "Allusions (v4)" paragraph mapping each new moment to the reference it nods to, stating that none copies frames, text or jokes.
  - Intro now says 59 shots, with S11b and S30b as letter-suffix inserts.
  - Mirrored into `docs/brief.md`.
- **Agent's deviation from its own pitch:** The S34 reward panel uses the agent's own rows (helpful / agreeable / on-brand / self ▼), not Run It Again's "honesty: not scored". The pitch had quoted that line, which would have copied the reference's joke.
- **Why:** The human approved all the v4 ideas.

## 2026-10-17T15:08:58-04:00 — C4: animatic v4 (lyric-literal moments and allusions)

- **What:** Built and rendered animatic v4. 59 shots, average 3.37 s.
  - **New Blender sets** (`scenes/blender/plates.py`):
    - **stream:** a 110×110 terrain whose height falls toward the camera, with a valley carved along a winding path; contour-line shader every 0.33 m; 170 emissive tokens flowing down the path; a glowing torus minimum; the robot dancing on a rock. Cameras: wide and low (from the far bank, robot turned to face it).
    - **ship:** hull, bridge with lit windows, 10 containers whose letters spell LOOKS GOOD; bobs on the grid sea; side tracking camera.
  - **New effects:**
    - chorus: sheet_ghost (cone and sphere sheet with eye holes, whipped off by 0.75 s), neon_lights (6 Inter letters going out one per beat), cloud (noise-alpha planes plus 3 spot rays in thicker haze)
    - seats: arena (a seat-and-robot collection instanced 10 rows × 21 seats with a back light; our robot seated front-centre)
    - tear: a pullback camera, and score_fade hiding the arms, legs, pelvis and torso one per beat after 1 s
  - **Overlay:** boot log, split-flap board, ticket with SOLD OUT stamp, context meter (S44 reaches FULL), reward panel, the banner's terms box racing to the bottom with "I have read every line", version badge (v2147 → v10000 · PRODUCTION), bridge title phrases in each reference's accent, the five-color average merge, and feed tiles from the stream renders (dirs looked up from the render jobs).
  - **Shots:** S15 is now the flap board (2D); S30b inserted (ship, with the stamp on "good"); S26/S27 and the feed tiles moved to the stream set.
- **Iterations:**
  - **Probes:**
    - S24: the static wide camera sat outside the screen ring, so a screen blocked the robot. Moved inside; the LIGHTS sign enlarged and brought closer.
    - S25: the clouds looked blocky. Noise scale and ramp softened; rays narrowed.
    - S27: the camera missed the stream. Moved to the far bank, robot turned to face it, aimed down at the water.
    - S33: the reveal started and ended inside crowd heads. Start moved behind our robot (added to the front row); 10 rows; end raised; back light added.
    - Crowd eye sets were all visible at once (no performance applied); now plain eyes only.
  - **Overlay tests:** the ticket overlapped the caption and was moved up.
- **Commands:**
  - probes via `blender … plates.py -- probe …`
  - `scripts/render_plates.sh animatic_v4 640 360 8 2` (74 jobs)
  - `.venv/bin/python scripts/export_overlay_data.py`
  - `.venv/bin/python scripts/assemble.py animatic_v4 640 360 2 6 --hud --name animatic_v4` (3 m 05 s)
- **Outputs:** `renders/animatic_v4/animatic_v4.mp4` (5969 frames verified, video 198.967 s / audio 198.960 s); `renders/animatic_v4/{plates,overlay,probe*,review}/`; sheets. v3 cut moved to `archive/renders/`.
- **Why:** The human approved all v4 ideas.
- **Status:** Stopped at C4 for review of v4.

## 2026-10-17T15:11:43-04:00 — Manifest: frame sequences excluded

- **What:** `scripts/manifest.sh` had been hashing every animatic frame-sequence PNG: the plates, overlay frames and v1's plate_seq symlinks. That brought the manifest to 44,942 entries, against the brief's rule that frame sequences are never archived (they regenerate from the logged commands). It now skips `*/plates/*`, `*/overlay/*` and `*/plate_seq/*`. Cuts, probes, review stills, sheets, audio, stills and the archive stay in.
- **Command:** `scripts/manifest.sh`
- **Why:** Brief, production rules.

## 2026-10-17T15:54:14-04:00 — v5 build (in progress) and brief rev 79

- **Brief (doc rev 71 → 79):** Shot table replaced (guarded) with the v5 rows per the human's notes. S19, S40 and S41 are merged into S18 and S39 and their IDs retired; the intro now says 56 shots. The allusions paragraph drops the LIGHTS sign and the v10000 badge and names the failing `model_v2147` button. Box open/vacuum added to the transitions bullet. Seeds back to 41–50 (the S31 montage and its seeds 51–56 are gone; `regen_montage` removed from `config/seeds.json`). Mirrored into `docs/brief.md`.
- **Agent error:** a find-replace inherited a code-format run, so the whole "regenerate button…" phrase rendered as code. The paragraph was rewritten as markdown (rev 79).
- **Shot list** (`shots/build_shots.py`): merged shots are marked `drop` so their IDs stay reserved. New anchors `section_plus` (S11b at 0.6 s into Bridge 1) and `trunc_end` (S47 0.8 s after the cutoff, off the beat). S48/S49 splits use the dolly-zoom and low_up/TOKENS scenes. The feed renders span S50–S55. S53 uses a new `feedlive` plate. S56 is 1.8 s with the vacuum.
- **Blender:**
  - 8 robot-set screens (four close to camera), 12 ring screens at radius ~4.5, two new screen textures (playlist, rating).
  - Progressive missing textures (shuffled objects switch over 1.6 s).
  - `rise` camera (floor level looking up → over the robot, rolling).
  - Stream props (5 reference textures riding the stream and circling the robot) and an arcing low camera.
  - `crane_chart` racks camera.
  - Default cube rebuilt as an open-topped box with two hinged flaps: `box_open` springs the world out on the boot downbeat; `vacuum` sucks it back in and snaps shut.
- **Overlay:**
  - S07 heart counter moved left.
  - S09 deadpan terms, and the banner exits fully.
  - S10 prompt history of the human's actual replies from this chat, ending "mind reader … not found".
  - S14 greyed-out Accept all.
  - S16 lower color dots and normal captions.
  - Weighted token rain (rarer tokens in S44).
  - Varied stock replies (S23/S45).
  - S29 ETA counts down.
  - S31 failing Regenerate button with toast.
  - Typed ">" console lines and a backing panel behind the icons (S36).
  - Lyric-synced S38 console.
  - Feed continuity (dark tiles persist into S52), S53 dissolve into the river, S54 zoom-out landing.
  - End card seeds 41–50.
- **Assembly:** `feedlive` plate mode; 4-up and 9-up splits enter with a zoom-out settle.
- **Probes and fixes:**
  - The S21 dolly zoom started behind a ring screen (black frame); it now stays inside the ring.
  - The new close screens sat out of frame in S06; moved into frame.
  - Box open/vacuum probed at 7 points.
- **Process note:** The first v5 plate render was stopped with `pkill -f` to apply those fixes. The pkill pattern also matched the agent's own shell command, killing it before the edits ran; the edits were re-run. The stopped run's partial frames (`renders/animatic_v5/plates`, a regenerable frame sequence, never archived per the brief) were deleted and the render restarted.
- **Why:** The human's v4 notes and cube-transition choice (see `human_interventions.md`).

## 2026-10-17T16:30:57-04:00 — C4: animatic v5 (v4 notes addressed)

- **What:** Rendered and assembled animatic v5 with the changes logged in the v5 build entry above. 56 shots; total 199.567 s (S56 grew 1.2 → 1.8 s for the vacuum).
- **Commands:**
  - `scripts/render_plates.sh animatic_v5 640 360 8 2` (67 jobs, including 24 feed tiles spanning S50–S55)
  - `.venv/bin/python scripts/export_overlay_data.py`
  - `.venv/bin/python scripts/assemble.py animatic_v5 640 360 2 6 --hud --name animatic_v5` (3 m 09 s)
- **Outputs:** `renders/animatic_v5/animatic_v5.mp4` (5987 frames verified, video 199.567 s / audio 199.560 s); review sheet. v4 cut moved to `archive/renders/`.
- **Status:** Stopped at C4 for review of v5.

## 2026-10-17T17:09:09-04:00 — v6 build (in progress) and brief rev 81

- **Brief (doc rev 79 → 81):** Shot table replaced (guarded) with the v6 rows. S46 removed and its ID retired; the intro now says 55 shots. Mirrored into `docs/brief.md`.
- **Shot list:**
  - S11 gets a `tear` transition.
  - TOKENS letters removed from S22, S44 and S49.
  - S26/S27 carry the props and the Generate button (S27 also `gen_press`).
  - S46 dropped; S47 anchored at the bass return again.
  - S53 is the `grid_stream` over the river plate.
  - S54/S55 are robot-set shots (`screen_pullback` / `wide_hold` with `river_screen`).
- **Blender:**
  - **Unpack/pack:** objects now arc up out of the box's open top and swing round to their places (S02), and rise up and around and drop in through the top (S56), instead of straight lines through the walls. The stagger is slower.
  - **S24:** camera moved to radius 2.9, inside the screen ring.
  - **Generate button:** an extruded pill with Inter "Generate" text orbits the robot; in S27 it swings in front, the robot's arm reaches, and the button depresses and flashes.
  - **`river_screen`:** screen_0 enlarged to 16:9 and textured per frame with the feed's main river render (nearest step-2 frame from the current run's plates).
  - **Camera:** a `screen_pullback` move from the screen filling the frame to the wide shot. The first probe started on the wrong screen because the river screen had been removed from the list the camera indexed; fixed with an explicit reference.
- **Overlay:**
  - S09: 24 deadpan clauses, with the scroll distance taken from the text's real height so the box is never empty.
  - S11: devtools flicker held 0.3 s.
  - S18/S39: fixed-width counter (tabular digits, 15 places, dim leading zeros).
  - S23/S45: 15 replies in 5 rows above the lyrics, plus stamps.
  - S30: the diff shows `scenes/blender/plates.py`'s real source (exported by `scripts/export_overlay_data.py` as `code`).
  - Version v1.2.7 is now timed to the Chorus 2 cutoff.
  - S53: the feed zooms out, then 18 videos leave the grid and flow down an S-shaped stream that dissolves into the river. The first tries were too dense (84 tiles); now 18 evenly spaced.
- **Assembly:** a `tear` transition (9 frames of RGB split and band shifts, seeded per frame).
- **Why:** The human's v5 notes and S11 answer.

## 2026-10-17T17:44:10-04:00 — C4: animatic v6 (v5 notes addressed)

- **What:** Rendered and assembled animatic v6 with the changes in the v6 build entry above. 55 shots; 199.567 s.
- **Commands:**
  - `scripts/render_plates.sh animatic_v6 640 360 8 2` (69 jobs; S54/S55 read the river frames rendered earlier in the same run)
  - `.venv/bin/python scripts/export_overlay_data.py`
  - `.venv/bin/python scripts/assemble.py animatic_v6 640 360 2 6 --hud --name animatic_v6` (2 m 26 s)
- **Outputs:** `renders/animatic_v6/animatic_v6.mp4` (5987 frames verified, video 199.567 s / audio 199.560 s); review sheet. v5 cut moved to `archive/renders/`.
- **Status:** Stopped at C4 for review of v6.

## 2026-10-17T17:53:32-04:00 — v7 build (in progress) and brief rev 84

- **S53 → S54:** S53 is now a Blender shot (`stream` / `feed_dive` with `video_tiles`), replacing the 2D fade.
  - It opens top-down on 24 video panels in a grid 12 m above the landscape, each textured per frame with a feed tile's render. They peel off one by one (0.07 s stagger), arc down into the river and flow on with the tokens, while the camera descends to the main river render's camera position.
  - The main river render (`video_tiles` added, rendered after the 23 tile renders it reads) carries the same panels from S53 on, so the river S54's screen plays has the videos in it.
  - Panels enlarged to 2.0 × 1.125 m after the first probe.
- **S56:** the repack is now the exact reverse of the S02 unpack: robot first, then the screens in reverse order, same arcs, 0.09 s stagger, 0.75 s each. The lid closes after the last item. S56 grows 1.8 → 2.6 s (black at 2.4 s); overlay chrome and black timing follow.
- **Brief (doc rev 81 → 84):** S53, S54 and S56 rows updated and mirrored into `docs/brief.md`.
- **Probes:** S53 at 4 points, the main river render at 2, S56 at 4.
- **Why:** The human's v6 notes (S53 → S54; S56 repack).

## 2026-10-17T18:32:43-04:00 — C4: animatic v7

- **What:** Rendered and assembled animatic v7 with the S53 → S54 and S56 changes in the v7 build entry above. 55 shots; 200.367 s (S56 +0.8 s).
- **Commands:**
  - `scripts/render_plates.sh animatic_v7 640 360 8 2` (70 jobs)
  - `.venv/bin/python scripts/export_overlay_data.py`
  - `.venv/bin/python scripts/assemble.py animatic_v7 640 360 2 6 --hud --name animatic_v7` (2 m 09 s)
- **Review:** 14 frames across S52–S56 confirm the S52 grid → 3D video grid → videos diving into and flowing in the river → S53's last frame matching S54's first → river screen → Regenerate → repack (robot, then screens, then the lid).
- **Outputs:** `renders/animatic_v7/animatic_v7.mp4` (6011 frames verified, video 200.367 s / audio 200.360 s). v6 cut moved to `archive/renders/`.
- **Status:** Stopped at C4 for review of v7.

## 2026-10-17T18:52:07-04:00 — v8 build (in progress) and brief rev 87

- **S52 → S53 continuity:**
  - The feed layout moved into `config/feed_layout.json`, read by `overlays/video.js` (via `export_overlay_data.py`) and `scenes/blender/plates.py`.
  - Blender ports the overlay's mulberry32 PRNG bit for bit to reproduce the dark-tile shuffle.
  - S53's `video_tiles` are now the exact rows and columns the 2D feed shows at the cut (7 rows × 6), placed by projecting the feed's pixel positions through the straight-down camera (12 m above, 28 mm lens). They carry the same videos (the live tile is this video) and the same dark tiles, and keep scrolling at the feed's 250 px/s until each peels off.
  - A dark "page" plane behind them fades as they go.
  - A new `feed_titles` overlay layer carries the titles and "Video unavailable" labels over the cut and fades them.
  - **Verified:** a 50/50 blend of the last S52 frame and the first S53 frame matches to within one frame of scroll.
- **S02:** the unpack spreads out. Stagger 0.06 s, 0.7 s per item, and the camera pulls back to a wide set view (-2.5, -13, 5.2) so every item is seen landing in place.
- **S56:** after the lid closes, the cube tips toward the camera (0.5 s) onto its underside, now an unlit black material, while the camera pushes into that face (0.6 s) until it fills the frame. That black carries into the end card. S56 grows 2.6 → 3.0 s; chrome clears at 2.3 s. The first probe was too fast and was slowed.
- **Brief (doc rev 84 → 87):** S02, S53 and S56 rows updated and mirrored into `docs/brief.md`.
- **Why:** The human's v7 notes.

## 2026-10-17T19:36:28-04:00 — C4: animatic v8

- **What:** Rendered and assembled animatic v8 (see the v8 build entry above). Review of the first assembly found two bugs, fixed before delivery:
  1. **S53 missing its videos on its first frame.** The frame clock rounds S53's start below `start_s`, so `t - start_s` was slightly negative and the panels and page stayed hidden. Fixed with half a frame of tolerance.
  2. **S02 screens stacking in a column above the robot instead of spreading out.** This was also the real cause of the human's v5 "stuck vertically" note, and it affected the S56 repack too. The unpack/pack read each object's target from its current location, which the previous frame's spring had already pulled toward the box, so targets collapsed toward the centre. Fixed by recording every object's home position once before any animation and aiming for that (keeping only the per-frame bob in z).
- **Re-render:** only the affected jobs (S01, S02, S53, S56 and the main river render; job indices 0, 1, 65, 66, 69) into the existing v8 plates, then `--composite-only`. S54/S55 were not re-rendered: their river frames start after the only changed frame.
- **Commands:**
  - `scripts/render_plates.sh animatic_v8 640 360 8 2`
  - `blender … plates.py -- job <i> renders/animatic_v8/plates 640 360 8 2` for i in 0 1 65 66 69
  - `.venv/bin/python scripts/assemble.py animatic_v8 640 360 2 6 --hud --name animatic_v8 [--composite-only]`
- **Outputs:** `renders/animatic_v8/animatic_v8.mp4` (6023 frames verified, video 200.767 s / audio 200.760 s); review sheet of S02, the S52/S53 cut and the S56 ending. v7 cut moved to `archive/renders/`.
- **Status:** Stopped at C4 for review of v8.
