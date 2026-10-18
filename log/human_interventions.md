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

## 2026-10-17T13:04:04-04:00 — v2 shot list approved

- **What:** The human approved ("go ahead") the agent's proposal: cut on every lyric line (~2 bars) for about 55 shots; multi-camera coverage of the 3D scenes; alternating 3D and 2D type-led shots; new scenes (intro inserts, hearts, autocomplete chat, giant counter, missing textures, nine identical replies, lights fading, top-down, dance in a code stream, black full stop, loading screen, THE END reverse shot, degraded Chorus 2, multiplying split screen, tiles going dark, endless feed scroll); style-spec transitions. The Bridge 2 freeze and Pre-Chorus 2 dropout stay static on purpose.
- **Why:** C4 feedback: the cut was too static.
- **Rule:** R1 (approving a plan).

## 2026-10-17T13:33:00-04:00 — C4 feedback on animatic v2: more ideas, more dynamic scenes

- **What:** The human reviewed animatic v2: "hm suggest some more, including ways to make the existing scenes more dynamic". The agent is proposing additions. Nothing has been changed yet.
- **Why:** Within-shot motion still reads as static.
- **Rule:** R1 (creative direction given in words; the agent makes the change).

## 2026-10-17T13:36:59-04:00 — v3 additions approved (items 1–7)

- **What:** The human said "do 1-7" to the agent's list:
  1. Everything reacts to the stems: drums → downbeat punch-ins and light pulses; bass → floor ripples; synth → screen flicker; vocals → the robot's mouth.
  2. Robot performance: singing equalizer mouth, eye expressions per lyric, gestures.
  3. Kinetic captions; words that break into 3D.
  4. Camera moves: dolly zoom on "not what it seems", fast 180° chorus entries, cranes, depth-of-field pulls.
  5. 2D shots that keep moving.
  6. Zoom-through and match-cut transitions.
  7. New moments: regenerate montage, million-line diff, song recognition, server-rack crib mobile, the robot alone in the theater, a dancing feed.
- Item 8 (render the animatic at the full 30 fps) was **not** chosen. v3 keeps step 2.
- **Rule:** R1 (approving a plan).

## 2026-10-17T14:25:38-04:00 — C4 feedback on animatic v3: lyric-literal and reference-alluding ideas

- **What:** The human reviewed animatic v3: "It needs some more still, try to find some that use the words or allude to the source videos (such as a literal \"data stream\" alluding to \"Run It Again\" 's backdrop evoking gradient descent during RLHF)". The agent is researching the references and proposing additions. Nothing has been changed yet.
- **Rule:** R1 (creative direction given in words; the agent makes the change).

## 2026-10-17T14:29:36-04:00 — v4 additions approved (all)

- **What:** The human said "Do them all" to the agent's list of lyric-literal and reference-alluding ideas:
  - data stream down a loss landscape (S26–27, feed tiles)
  - reward panel with robot pieces fading (S34)
  - v2147 → v10000 PRODUCTION badge (S31)
  - LOOKS GOOD container ship (S30)
  - top-down from inside a cloud (S25)
  - SOLD OUT front-row ticket (S32)
  - arena of identical robots (S33)
  - terms box scrolled to "I have read every line" (S09)
  - "mind reader … not found" boot log (S10)
  - split-flap AUTHOR — NOT FOUND board (S15)
  - context-window meter (S22)
  - neon LIGHTS sign going out (S24)
  - bedsheet ghost (S20)
  - bridge title phrases in each reference's accent color (S12–S13)
  - five-color average merge (S16)
- **Rule:** R1 (approving a plan). All allusions are generic redraws; no reference frames, text or jokes are copied.

## 2026-10-17T15:42:39-04:00 — C4 feedback on animatic v4 (nitpicks) and cube-transition choice

- **What:** The human reviewed animatic v4 with these notes (verbatim):
  - "let's have more than 4 screens, and perhaps bring them closer to the camera"
  - "transitions into and out of the default cube are jarring -- suggest some options for this, but mine are: a generic right click context menu (not necessarily Blender's), the box opening and revealing or vacuuming the things before/after it"
  - "at S07, the "heart" counter directly overlaps the graph label, making them both hard to read"
  - "at S09, make the text inside the box more tongue-in-cheek. also, it doesn't clear the frame once it's done creating a continuity error"
  - "at S10, there's probably a self-referential joke here about how my responses in this chat have been "LGTM" or "give me more" or some variation of it, and then complaining that it's not working (like I am literally doing right now)"
  - "at S11, the song detector should appear much sooner"
  - "at S13 into S14, the "Accept" button should stay visible but grayed out afterwards while "generating" is up"
  - "at S16, the large text is not doing too many favors -- just get rid of it here and bring the color circles down"
  - "S18 and 19 can probably be combined -- the graph very much correlates with the count"
  - "the transition into missing textures at S21 is a little jarring -- maybe have them go out one at a time"
  - "S22 can use more tokens than just `the`"
  - "same for S23 -- find some other common Claude and ChatGPTisms to put in here (but not so many that they're all unique)"
  - "S24's "LIGHTS" is a little too on the nose -- with more screens, it won't be necessary"
  - "S25 is too static, and also the wrong direction: start looking up from the bottom (so it's explicitly not "looking down"), then pan and rotate up centered on the robot"
  - "S27 could use some more motion -- perhaps some other references put in the stream itself and flying around"
  - "S29's ETA countdown should be decreasing"
  - "S31 could use an actual "regenerate" button being clicked rather than the fast cuts, but make it appear to fail"
  - "for S36: animate the lines beginning with `>` so it looks like someone is actually typing them. the contrast between the icons and the backdrop is not great."
  - "S38 could use some more messages relevant to the lyrics at that moment"
  - "the end of S38 into S41 can be combined so that the bits with the numbers, the servers, and the graph are all on the same scene (correlating with the line)"
  - "S43: same as S21" / "S44: same as S22, add more distinct ones at this point" / "S45: same as S23"
  - "S46 is up for way too long, and shouldn't be timed to the beat (it's an error)"
  - "S48 and S49 should reference different versions of same scenes as the lyrics from above as it zooms out further"
  - "continuity between S51 and S52"
  - "S53: the scroll becomes the river from before including the robot"
- **Choice:** Asked to pick a default-cube transition from four options (box opens/vacuums, context menu, unfold into the floor, cube becomes the head), the human chose "Box opens / vacuums".
- **Rule:** R1 (creative direction in words and a choice between plans; the agent makes every change).

## 2026-10-17T16:57:58-04:00 — C4 feedback on animatic v5

- **What:** The human's notes (verbatim):
  - "S02: I was expecting things to be unpacked from the box, not stuck vertically"
  - "S09: there's not enough terms so it's completely black most of the time"
  - "S11: the dev console is showing up for a frame or two"
  - "S18: use fixed-width numbers so that the width is not constantly changing as it grows"
  - "S22: we don't need the falling \"TOKENS\" letters anymore now that there's more variance in the words"
  - "S23: fill the screen with them without obscuring the lyrics (maybe two more rows)"
  - "S24: this is starting from behind the screen and lingering so I can't see any of the rest of the scene"
  - "S26: for continuity with S27, this needs to also have the elements from there"
  - "S27: add a \"generate\" button flying around the robot, and make it push it at the end"
  - "S30: instead of placeholder code, use the actual code from this repository"
  - "S44: same as S22"; "S45: same as S23"
  - "S46: just get rid of it entirely so that S45 can have more time"
  - "S53: the videos themselves should become the data stream by zooming out, then animating them"
  - "S54: it should become one of the screens around the robot at S56 rather than going back out to the YouTube-style scroll"
  - "S55: regenerate button on top of S54 as revised"
  - "S56: contents need to go up and around the box rather than clipping into it"
- **Rule:** R1 (creative direction in words; the agent makes the changes).

## 2026-10-17T17:03:09-04:00 — S11 flicker clarified

- **What:** Asked whether S11's devtools flicker should be removed, turned into a clearer glitch, or held longer, the human answered: "make it both read as a glitch, and also longer".
- **Rule:** R1 (choosing between plans).

## 2026-10-17T17:50:42-04:00 — C4 feedback on animatic v6

- **What:** "so close: for S53 into S54, I want the videos to become an actual part of the stream rather than doing a fadeout"
- **Rule:** R1 (creative direction in words; the agent makes the change).

## 2026-10-17T17:51:04-04:00 — C4 feedback on animatic v6 (follow-up)

- **What:** "also S56's repacking needs the same treatment as the unpacking"
- **Rule:** R1 (creative direction in words; the agent makes the change).

## 2026-10-17T18:47:58-04:00 — C4 feedback on animatic v7

- **What:** "The box open still needs to have them contents spread out. There is a continuity issue between S52 and S53: make sure the videos line up between cuts. Transition to the end credits by rotating the cube onto an unlit face."
- **Rule:** R1 (creative direction in words; the agent makes the changes).

## 2026-10-17T20:02:16-04:00 — C4 closed; C5 started on this machine

- **What:** After the agent's render-time estimate (~4 h at use-matched resolutions on the GTX 970), the human said "yes, start it here for now". The agent reads this as approval of animatic v8 (C4) and as the go-ahead for C5 full-quality renders on this machine, to move to the RTX 5090 box when it is ready.
- **Rule:** R1 (approve a plan / the cut).

## 2026-10-17T20:50:35-04:00 — C5 section 2 rejected: stray big "Maybe"

- **What:** The human reported "C5 section 2 of 8 at 00:14 has a stray frame of the big 'Maybe'". The agent found the cause and re-cut the section.
- **Rule:** R1 (reject a render).

## 2026-10-17T21:09:21-04:00 — C5 section 3 rejected: SAME stamps misaligned

- **What:** The human reported "the 'SAME' stamps are misaligned" (S23). The agent found the cause and re-cut the section.
- **Rule:** R1 (reject a render).

## 2026-10-18T06:05:44-04:00 — C5 section 7 rejected: S53 camera jerks

- **What:** The human reported "just after the transition from the scrolling videos scene to the final dancing robot at the stream, the animation itself is jerking" (S53). The agent found the cause, re-rendered the affected plates and is re-cutting the section.
- **Rule:** R1 (reject a render).

## 2026-10-18T06:16:42-04:00 — C5 sections 3 and 6 rejected: "Loading textures" text oscillates

- **What:** The human reported "both 'loading textures |' bits needs to have a placeholder when the box is not shown -- the position appears to oscillate because its width is changing and it's right-aligned" (S21, S43). The agent fixed the overlay and is re-cutting both sections.
- **Rule:** R1 (reject a render).

## 2026-10-18T06:45:40-04:00 — C5: banding on the robot and stutter in slow text zooms reported

- **What:** The human reported "some color banding on the robot and jumpiness in the slow zooms on text scenes, likely caused by the render color depth and resolution" and asked whether it could be fixed efficiently on this machine. The agent diagnosed both, fixed them in the pipeline and is re-cutting all eight sections.
- **Rule:** R1 (reject a render).

## 2026-10-18T07:56:48-04:00 — Move to the RTX 5090 box

- **What:** The human said "let's move it all over to the other box -- write up anything you haven't already so it can get started as soon as I copy over the directory". The human will copy the repo directory to the RTX 5090 box.
- **Rule:** R3 (a technical step the agent can't do itself: moving the project between machines).
