# Ghost in the Machine

An AI-made, code-animated music video. The agent does the production; the human may only approve or reject (R1), correct A/V sync (R2), fix technical failures the agent can't (R3), and run Suno (R4).

**Start here:** `docs/handoff.md`. It covers current state, setup on a new box, remaining work and lessons. Then read `docs/brief.md` (the production brief, mirrored from the Claude Doc) and the latest entries of `log/production_log.md` and `log/human_interventions.md`.

Rules that apply to every step:
- **Logs:** append to `log/production_log.md` for every action. Log every human action with its rule in `log/human_interventions.md`. Prompts go in `log/prompts/`.
- **Commits:** one git commit per logged step.
- **Assets:** never delete or overwrite an asset. Superseded or rejected files go to `archive/` (cuts) or `renders/<tier>/plates_superseded_<why>/` (plates).
- **Large files** stay out of git; run `scripts/manifest.sh` after adding any. Frame sequences, caches, venvs and node_modules are never archived.
- **Inspiration videos** (`reference/inspiration/`) are never published.
