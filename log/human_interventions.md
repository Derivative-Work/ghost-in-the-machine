# Human interventions

Every human action: timestamp, what, why, and which production rule allows it. Rules:
(R1) approve/reject a take, render or plan; (R2) correct A/V sync; (R3) fix technical failures the agent cannot; (R4) run Suno when the agent has no access. Anything else is an EXCEPTION.

## Before 2026-10-17T10:38 (exact time unknown) — Lyrics merged from Claude's drafts — EXCEPTION

- **What:** A human merged several of Claude's lyric drafts from the planning chat into the version submitted to Suno (`log/prompts/suno/lyrics_submitted.txt`).
- **Why:** To assemble one lyric sheet from several drafts.
- **Rule:** None. Human edits to lyrics are forbidden, so this is logged as an exception.

## Before 2026-10-17T10:38 (exact time unknown) — "Regenerate, regenerate" chorus line reverted — EXCEPTION

- **What:** A human reverted the chorus's "Regenerate, regenerate" line before submitting.
- **Why:** It didn't flow.
- **Rule:** None. This is a human edit to lyrics, logged as an exception.

## Before 2026-10-17T10:38 (exact time unknown) — Track generated in Suno v6 — R4 (choice of take: R1)

- **What:** A human ran Suno v6 with the submitted lyrics and chose the final take. The take ID, style prompt, settings and rejected takes are **pending from the human**.
- **Why:** The agent has no access to Suno.
- **Rule:** R4 (run Suno's interface); choosing the take is R1.
- **Evidence:** `audio/track/Ghost in the Machine.wav`, file mtime 2026-10-17T10:38 in `~/Downloads`. Stems zip mtime 10:53.

## 2026-10-17T11:18 — Source files supplied to the agent

- **What:** A human placed the track, stems and inspiration videos in `~/Downloads/ghost-in-the-machine/` and pointed the agent at the brief.
- **Why:** Inputs listed in the brief.
- **Rule:** Not a touch on the work (supplying inputs). Logged for completeness.

## 2026-10-17T11:28:42-04:00 — Suno details supplied; planning chat shared

- **What:** A human confirmed that the style prompt was the one in the planning chat and that the first take was chosen, and shared the planning chat link. This adds detail to the earlier "Track generated in Suno v6" entry, which stays unchanged because this log is append-only.
- **Why:** So the track can be logged retroactively (brief, pre-production step 2).
- **Rule:** R1 (the take choice, made before the agent started). Supplying information is not a touch on the work.

## Before 2026-10-17T11:28:42-04:00 — Node installed

- **What:** A human installed Node (v24.22.0 via nvm, npm 11.19.1).
- **Why:** The Puppeteer overlay pipeline needs it, and the agent found it missing during setup.
- **Rule:** R3 (fix technical failures the agent cannot: broken install).

## 2026-10-17T11:28:42-04:00 — Hardware plan: draft here, final on the RTX 5090

- **What:** A human directed that draft renders run on this machine (GTX 970), with the full run moving to a separate RTX 5090 machine once it is ready.
- **Why:** The 5090 box is not ready yet.
- **Rule:** R1 (approving a plan). Not a creative change.

## 2026-10-17T11:37:11-04:00 — Suno share link supplied

- **What:** A human shared the Suno link for the chosen take.
- **Why:** So the take ID can be logged retroactively.
- **Rule:** Supplying information, not a touch on the work.

## 2026-10-17T11:44:06-04:00 — C1 approved

- **What:** The human approved the style spec and test frame ("LGTM"). The open questions default to the agent's recommendations: 60 FPS counter, red-orange plus blue accents.
- **Why:** Checkpoint C1.
- **Rule:** R1 (approve a plan).

## 2026-10-17T11:58:32-04:00 — Bridge 2 approach chosen; "out" confirmed; brief update requested

- **What:**
  - The human chose the agent's recommended approach to the missing Bridge 2 dropout and asked for the brief to be updated. The freeze stays on Bridge 2 over music that keeps playing, and the Pre-Chorus 2 dropout becomes the reveal's low point.
  - The human confirmed the lyric is "fading **out**", not "now" as Whisper heard it: "it's clearer in my (cleaned-by-a-generated-model) master".
- **Why:** C3 findings. The track's dropouts differ from the brief.
- **Rule:** R1 (choosing between plans). The creative change itself was made by the agent. The lyric confirmation changes nothing.
- **Open:** It is unclear whether `audio/track/Ghost in the Machine.wav` is that cleaned master or the raw Suno file, and which model cleaned it. The agent has asked.

## 2026-10-17T11:59:12-04:00 — C3 closed; master timing confirmed identical

- **What:** The human said "the timing is locked, the model just emphasizes consonants and cymbals". The agent reads this as two things: the AI-cleaned master is timing-identical to `audio/track/Ghost in the Machine.wav`, so the timing map stands; and C3 is approved. The human made no sync corrections.
- **Why:** Checkpoint C3.
- **Rule:** R1 (approve a plan) and R2 (A/V sync; no corrections requested).
- **Open:** Before the final mux, the human needs to supply the cleaned master file and the cleaning tool's name and settings. These go in `log/prompts/` as an AI processing step.

## 2026-10-17T13:00:23-04:00 — C4 feedback: sync approved; more scenes and cuts requested

- **What:** The human reviewed animatic v1: "the lyrics synchronization is spot on but clearly I did not review the spec closely enough -- it needs more scenes and cuts as it feels pretty static right now. Suggest some more". The agent is proposing additions. Nothing has been changed yet.
- **Why:** The cut feels static. 23 shots average 8.7 s; S09 alone is 37 s.
- **Rule:** R1 (rejecting a plan; creative direction given in words, the agent makes the change).
