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
