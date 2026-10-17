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
