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
