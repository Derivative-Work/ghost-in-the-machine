# Handoff: GTX 970 draft box → RTX 5090 box

Written 2026-10-18 when the project moved boxes. The agent on the new box has none of the earlier conversation. This file, `docs/brief.md`, `log/production_log.md` and `log/human_interventions.md` carry the whole context. Read them in that order; the logs are long, so read the last ~15 entries of each closely.

## 0. Update: the first session on the RTX 5090 box (2026-10-18 afternoon)

Read this first. It supersedes parts of §1 and §5 below.

- **Box:** set up per §3. Node comes from nvm (`~/.nvm`, loaded in `~/.bashrc`; non-interactive shells need `export PATH=$HOME/.nvm/versions/node/v24.22.0/bin:$PATH`).
- **Benchmarks:** ~0.3 s/frame at 2304×1080 and ~1.0 s at 4608×2160. Three Blender processes in parallel give 2.1–2.3× the throughput of one; a fourth adds little.
- **Parity:** the 5090's Eevee output is bit-identical to the 970's, so plates can be mixed.
- **The human's decisions** (`log/human_interventions.md`, 15:59:33):
  - **4K masters.** The main video is 3840×2160; the vertical is 2160×3840, cropped from the same plates (3D upscaled 1.78×). This replaces §5.2 and §5.3.
  - **Audio:** the music-deslop master, `audio/master/…` via `config/audio.json`. `assemble.py` muxes it. This replaces §5.6.
  - **End card:** mastering credit, GitHub link and licence line. The interventions count is re-exported (§5.4 done for now; re-export again if more entries land before C6).
  - **Licences:** `LICENSE` (MIT, code) and `LICENSE-media.md` (CC BY-NC-SA 4.0). `README.md` carries the credits, and the torrent and IA links go there at publish, not on the card.
- **4K pipeline:**
  - Profile `4k` (was `c5v`) and tier `renders/c5_4k/`.
  - 2× screen textures in `renders/c5_4k/panels` (`GITM_PANELS`).
  - Overlay canvases rasterise at the output size (`K` in `overlays/video.js`).
  - `c5_sections.py --tier c5_4k --size 3840x2160` cuts the 4K sections.
- **Next:**
  1. Cut the eight sections at 4K and check them (flash check, compare with the 1080p C5 cuts).
  2. Send them to the human for C5 approval. 4K masters are far over the 30 MiB upload limit, so ask how they want to review.
  3. Then the main video, the vertical (`--vertical`, 2160 3840), the thumbnail and C6, as in §5.
- **Later (same day):** C5 was approved (all eight 4K sections; chorus 2's degradation made heavier first). The human decided:
  - keep the thumbnail as it is;
  - don't ship `reference/stills` (out of the manifest; `reference/stills.tsv` gives each one's source and time);
  - publish large files as a GitHub Release instead of a torrent and the Internet Archive.

  This replaces §5.7's thumbnail question and §5.8's stills question and torrent/IA plan. The brief (rev 95) and README match.
- **Published (2026-10-18):** C6 approved. The release is https://github.com/Derivative-Work/ghost-in-the-machine/releases/tag/v1.0 (tag on d96d8cc), the repo is public, and the video is on YouTube: https://www.youtube.com/watch?v=6RcYUoG1t0I. The production is complete.

## 1. Where things stand

- **Checkpoints:** C1 style, C2 track, C3 timing and C4 animatic (v8) are approved. **C5 is in review.** All eight sections are cut at full quality from the current code (`renders/c5/c5_<n>_<name>.mp4`, crf 18) and sent to the human. **None is approved yet.** C6 (final) has not started.
- **C5 sections** (`config/c5_sections.json`):
  1. intro/verse 1 (S01–S10)
  2. bridge 1/pre-chorus 1 (S11–S18)
  3. chorus 1 (S20–S29)
  4. verse 2 (S30–S34)
  5. bridge 2/pre-chorus 2 (S35–S39)
  6. chorus 2 (S42–S45)
  7. final chorus (S47–S55)
  8. ending (S56–S57)
- **Human rejections during C5, all fixed and re-cut:**
  - section 2's stray big "Maybe";
  - section 3's SAME stamps;
  - the S53 camera jerk;
  - the "Loading textures" caret shift (S21, S43);
  - robot banding and slow text-zoom stutter (every section).

  Each has a log entry with cause and fix. The superseded cuts are in `archive/renders/c5/`.
- **Plates:** every C5 plate was rendered on the GTX 970 (`renders/c5/plates`, 15 GB, 64 Eevee samples, sizes in `config/render_profiles.json` → `c5`). These are the frames the human is reviewing.
- **Last pipeline changes**, none of which needed plate re-renders:
  - grain on 3D plates;
  - BT.709 convert and tag;
  - `will-change` on the 2D push;
  - fractional crops in the compositor.

  All in `scripts/assemble.py` and `overlays/video.js`; see the log entry "Banding, colour matrix and zoom stutter".

## 2. Copying the directory

Copy the whole repo directory, including `.git` (git hooks live in `scripts/hooks`, via `core.hooksPath`). It is ~46 GB. To save space or time, these can be skipped because they regenerate:

| Path | Size | Note |
| --- | --- | --- |
| `.venv/`, `node_modules/` | 1.7 GB | Recreated in step 3; a copied venv has this box's absolute paths and won't work |
| `renders/animatic*/plates`, `renders/animatic*/overlay` | ~20 GB | Animatic frame sequences. Keep each `renders/animatic_v*/animatic_v*.mp4`: they are the record of what was approved |
| `renders/c5/plates_superseded_*` | 8 GB | Plates replaced by fixes; kept only so nothing is deleted. Don't copy them if you skip the above |

**Don't skip** `renders/c5/plates` (the reviewed frames), `audio/`, `assets/`, `reference/`, `archive/`, `log/` or `MANIFEST.sha256`.

## 3. Setting up the new box

The same versions keep renders comparable. Draft box: Blender 5.2.2 LTS (snap), ffmpeg 8.0.1 (with libx264), Node v24.22.0 (nvm), uv with Python 3.12, NVIDIA driver 580.

```bash
cd <repo>
# Blender 5.2.2 LTS on PATH as `blender`, ffmpeg 8.x with libx264, Node 24, uv
npm ci                                                 # puppeteer 24.43.1 (pinned)
npx puppeteer browsers install chrome-headless-shell   # the overlay renderer; lives in ~/.cache/puppeteer
uv sync                                                # .venv with Python 3.12
git config core.hooksPath scripts/hooks                # already set in .git/config if .git was copied
sha256sum -c --quiet MANIFEST.sha256                   # every published large file arrived intact
```

- **Headless GPU:** Eevee needs OpenGL/EGL from the NVIDIA driver. The RTX 5090 (Blackwell) needs driver ≥ 570. If `blender -b` fails to create a GPU context, that's the cause.
- **PyTorch** is pinned to the CPU index (`pyproject.toml`). It was only used for lyric alignment, which is done, so leave it.
- **Fonts** are bundled (`assets/fonts`, loaded by `overlays/tokens.css`); nothing to install.

## 4. First things to run on the new box

1. `scripts/check_seeds.sh`: per-machine reproducibility (log, step 4 says it must be rerun on the 5090). Log the result.
2. `scripts/gpu_parity.sh`: renders the first frame of S07, S27 and S25 and compares with the 970's plates. On the 970 it gives 0 difference. Log the numbers. They decide whether 5090 plates can be mixed with 970 plates inside one cut. Eevee differences between GPUs are usually tiny noise, but measure it.
3. Time one job before any long run, e.g. `scripts/render_plates.sh c5 c5 1 S07` into a scratch tier, so estimates are real.

## 5. Work that remains, in order

1. **Get the human's C5 approval for each section** (R1). Log each one in `log/human_interventions.md`. Fix and re-cut rejected sections. See §7 for the method.
2. **Decide with the human: re-render the finals on the 5090, or keep the 970 plates.**
   - The log (step 4) originally said finals would render on the 5090.
   - C5 then ran on the 970, and those are the frames being approved.
   - Recommendation: keep the approved 970 plates for the 16:9 cut, and use the 5090 for the vertical plates (next item) and any re-renders a rejection requires.
   - Don't re-render the 16:9 plates without asking.
3. **Vertical cut (9:16, S35–S56), at double resolution.** Today its 3D shots are 1080-tall plates cropped and upscaled 1.78×. The profile `c5v` (twice the c5 sizes) is ready but **untested**:
   ```bash
   scripts/render_plates.sh c5v c5v 1 S34 S39 S42 S43 S44 S47 S48 S49 S50 S53 S54 S55 S56 tiles
   .venv/bin/python scripts/assemble.py c5v 1080 1920 1 4 --vertical --crf 18 --name vertical
   ```
   - That's 48 jobs, 18,289 frames at 4× the pixels (S50's 24 feed seeds are most of it). S34 is there only because S35 holds its last frame.
   - The human hasn't decided between this and the current upscale. Ask before the long run.
   - Test first with `--still --frames F:F+1` on a few frames per shot (S47 2-up, S48 4-up, S49 9-up, S53, S54).
   - The reframing (`config/vertical.json`) uses fractions of the frame, so it carries over unchanged.
4. **Before C6:**
   - Re-export the overlay data (`.venv/bin/python scripts/export_overlay_data.py`) so the end card's "Human interventions" count includes the C5 rejections (it currently reads 23).
   - Then re-cut section 8, where the end card lives.
5. **Main video:**
   ```bash
   .venv/bin/python scripts/assemble.py c5 1920 1080 1 4 --crf 18 --name ghost_in_the_machine
   ```
   That's the full 6023 frames. Then flash-check it and compare it with the approved sections (`scripts/cut_diff.py`).
6. **Final audio mux** with the human's AI-cleaned master.
   - The human must supply the file, plus the cleaning tool's name and settings, for the log (R4/R3 boundary; ask).
   - The current cuts use `audio/track/Ghost in the Machine.wav`, the Suno take, via `timing/timing_map.json`.
7. **Deliverables:**
   - `deliverables/ghost_in_the_machine.en.srt`: regenerate with `scripts/export_srt.py` if any timing changed.
   - Burned-in captions are already in the cut.
   - Thumbnail `deliverables/thumbnail.jpg` (S47 f4782): **the human hasn't decided** between keeping it as the brief describes and enlarging the labels or dropping the caption.
8. **Session transcripts:** the brief publishes the Claude Code session transcripts with the large files.
   - `scripts/export_transcripts.sh` copies this project's sessions verbatim from `~/.claude/projects/<path>/` into `transcripts/claude-code/` (git-ignored, hashed in the manifest).
   - The draft box's session is `b87d228d-f2f7-4dc6-a9be-1ebd8959e099`. The human exports it on the draft box before copying.
   - Run the script on the 5090 box too, at the end, for its own sessions.
   - The draft session contains the human's personal email address 9 times. It comes from context Claude Code injects automatically, not from the work. **Ask the human whether to redact it** in a separate copy before publishing; keep the verbatim export unchanged.
9. **C6:** final approval, log audit, `scripts/manifest.sh`, then publishing (torrent + Internet Archive; brief).
   - Open question to raise then: `reference/stills/` holds frames taken from the inspiration videos and is in the manifest. The brief says never publish the inspiration videos; confirm with the human whether those stills ship.

## 6. Production rules (from the brief; easy to break)

- **Human actions:** the human may only approve or reject (R1), correct A/V sync (R2), fix technical failures the agent can't (R3), and run Suno (R4). Log every human action with its rule in `log/human_interventions.md`.
- **Logging and commits:** append-only `log/production_log.md`, one entry per action, with prompts in `log/prompts/`. One git commit per logged step, ending with the session's Co-Authored-By/Claude-Session lines.
- **Assets:** never delete or overwrite an asset. Superseded or rejected cuts go to `archive/` with a reason in the name (`*_rejected_<why>`, `*_superseded_<why>`). Superseded plates go to `renders/<tier>/plates_superseded_<why>/`.
- **Large files:**
  - They stay out of git. `scripts/manifest.sh` hashes them; rerun it before each commit that adds any.
  - Frame sequences, caches, venvs and node_modules are never archived.
  - The pre-commit hook rejects files over 50 MiB.
- **Inspiration videos** (`reference/inspiration/`) are never published; link to them instead.

## 7. Methods and lessons from C5

- **Re-cutting a section:** archive the old mp4 first. `scripts/c5_sections.py [section ...]` skips sections whose mp4 exists, waits for missing plates, and writes `renders/c5/sheets/`. A section takes 1–3.5 min here.
- **Checks after any change:**
  - `scripts/flash_check.py <cut> <first_frame> <out>`: short states between hard changes.
  - `scripts/cut_diff.py <new> <old> <first_frame>`: which frames changed, and whether each is a shot's first frame.
  - `scripts/compare_v8.py`: C5 against the approved animatic at 25% and 75% of every shot.

  After a layout change, look at a frame from every affected shot. A whole-frame diff misses small things like a caret.
- **When a flash check flags frames inside a camera move, measure the camera.** The S53 jerk was a `to_track_quat` roll flip on a straight-down camera, which the flash check had flagged and I misattributed. Don't aim a straight-down camera with `look_at`.
- **Choosing the shot:** the overlay picks the shot by frame (`start_frame`), not by `start_s`. They differ by up to one frame.
- **Plate resolution:** `render_plates.sh` skips frames already on disk, so a stopped run resumes. To re-render, move frames away; never delete them.
- **Encoding:** BT.709 tagged, `-tune grain`, grain only on 3D plates (`GRAIN` in `assemble.py`). Judge banding on the crf 18 masters, not on bitrate-capped copies.
- **Sending to the human:** uploads are limited to 30 MiB. Larger cuts go as capped review copies (`-tune grain -b:v 6–7M`) from the scratchpad, and the human is told the master's path.
- **Long jobs:** run them in the background and record start/end times in the log. Shell `while read` loops miss a last line without a newline.
