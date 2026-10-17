# Style spec

Pre-production step 1. Measured from 264 stills (one every 5 s) and 159 scene-change stills across the five inspiration videos (`reference/inspiration.md`). Numbers come from `style/measurements.json` (`scripts/analyze_stills.py`, seed 41). Qualitative notes come from the agent reviewing the contact sheets in `reference/stills/<slug>/contact_*.jpg`.

**Headline finding:** the genre isn't cyan-and-magenta synthwave. It's a **near-black UI canvas with one saturated accent hue per video, kinetic lyric typography and mocked-up interfaces**, cut every one or two bars, with occasional 3D scenes. The brief's "neon grid" and "robot" placeholders survive in a quieter form (see "The average").

## Per-video observations

| Video | Res / fps | Base | Accent | Type | 2D/3D | Character | Pacing (observed) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Accept All | 1440p / 30 | near-black, deep-blue gradients | electric blue `#3b6ed8`, secondary orange `#b25e28` | heavy grotesque caps + italic serif for single words | mixed: 3D city of gift boxes, Earth globe, phone mockups, cookie banners | chibi pixel girl (later pixel-dissolved) | ~3–5 s per composition; few hard cuts, mostly camera moves and morphs |
| The End of the Show | 2160p / 30 | dark charcoal rooms, cream paper | red/coral `#dc5746`, navy `#2b4075`, gold | white sans + large italic serif lyric words; mono UI | mostly 3D: dark interiors, a city, an arena, volumetric haze | faceless grey mannequins in beanies | ~5 s; 27 measured cuts |
| LGTM | 1440p / 60 | `#0c0e13` slate, plus cream "document" scenes | terminal green `#51f784`, secondary salmon `#c2604c` | heavy grotesque, green highlight words, code mono | mostly 2D UI (chat, Jira-like tickets, code), some 3D (ship, cube) | small orange blocky robot | ~5 s; continuous camera, so only 4 measured cuts |
| Not My Fault | 1080p / 60 | black and cream paper, about evenly split | orange `#e48240`, red-orange `#e24118` | grotesque with the current word in accent and upcoming words dimmed; mono labels; one handwritten script | almost all 2D: forms, tickets, timetables, receipts | none (the model is the narrator) | 3.1 s; 52 cuts |
| Run It Again | 1080p / 30 | `#080608` wine-black, cream paper | hot pink `#db1e6c` / `#f93389` | heavy grotesque with neon glow, italic serif, mono terminal | mostly 2D UI with fake-3D tunnels and type rings | none | 4.3 s; 66 cuts |

**Shared by all five:** about 50% of pixels are near-black (`dark_fraction` 0.32–0.60). Each video has exactly one dominant accent hue, and accent pixels make up 3–16% of the frame. Heavy grotesque sans headline type is always present. On-screen UI (chat bubbles, consent dialogs, terminals, dashboards, receipts, tickets, progress bars) dominates. Giant counters tick up (`9,406,832,711,679`, `+90,112`, `v10000`). A cursor clicks things. Tiny monospace "chrome" labels sit in the frame corners.

**Shared by four of five:** cream "paper" scenes (`#e6e4dc`, about 20% of frames) cut against the dark. An italic serif is used for single emotional words. Lyrics are revealed word by word with the sung word highlighted.

**Shared by three of five:** 30 fps. 3D scenes built from simple primitives with emissive screens as light sources. A simple, faceless character.

## The average (the look of this video)

### Palette

| Role | Hex | Basis |
| --- | --- | --- |
| Base (canvas) | `#09080b` | Pooled cluster 1 (39% of pixels) |
| Surface (panels, UI cards) | `#1d1d24` | Pooled cluster 2 (21%) |
| Line / muted text | `#4b3d42` → use `#4a4550` | Pooled cluster 4, desaturated slightly toward neutral |
| Mid grey (3D matte, secondary text) | `#847d77` | Pooled cluster 6 |
| Paper (light scenes) | `#e6e4dc` | Pooled cluster 3 (20%); the cream shared by four videos |
| Primary accent | `#d9502f` (red-orange) | Most common accent family: End of the Show, Not My Fault, plus the secondary accents in LGTM and Accept All. Pooled `#c85440` / `#b64b27`, brightened to read on black |
| Secondary accent | `#396ad3` (blue) | Second accent family: Accept All, End of the Show. Pooled `#396ad3` |
| Glow tint | primary at 60% for bloom | Accent text glows in three of five |

Each video's own hue (green, pink) is **not** used, so no single reference can be named from the frame. The red-orange/blue pair is the average, and it is also the most generic thumbnail pairing there is. **Ratio target:** ~80% of frames dark, ~20% paper; accents ≤ 10% of pixels in any frame.

### Typography (all OFL, in `assets/fonts/`)

| Use | Font | Matches |
| --- | --- | --- |
| Lyric headlines, titles, big counters | **Inter** Black/ExtraBold (800–900), tight tracking (−2%) | The heavy grotesque in all five |
| Emotional single words inside a line | **Instrument Serif Italic** | The italic serif in four of five ("thoughtful", "little", "That's fine.") |
| UI chrome, code, console, corner labels, credit overlay | **JetBrains Mono** 400–500 | Terminal/mono labels in four of five |

### Captions (lyrics)

- Word-by-word reveal timed to the forced alignment. The sung word is white (on dark) or base (on paper). Words still to come show dimmed at 30% opacity; words already sung stay at full. One word per line can take the primary accent, the line's key noun.
- Inter ExtraBold at about 7% of frame height, left-aligned in the lower-left third. Lines break by phrase, not by width.
- A word marked as emotional switches to Instrument Serif Italic at 110% size (at most one per section).
- The SRT carries plain text only.

### Camera and motion

- **2D UI scenes:** a static frame with a slow push-in (about 3% scale over the shot), and UI elements entering on the beat.
- **3D scenes:** slow dolly or orbit at about 10–20°/bar. Low angle on the character, wide establishing shots. No handheld shake.
- **Easing:** everything uses one cubic ease-in-out (`cubic-bezier(0.65, 0, 0.35, 1)`). This is the brief's joke, and it matches the uniform easing seen across the references.
- **Transitions:** hard cuts on the downbeat dominate (Not My Fault, Run It Again). Secondary transitions are zoom-through into a screen (Accept All, End of the Show), pixel-dissolve or glitch with RGB split (Accept All, Run It Again), and a whip-pan on chorus entries.

### Lighting (3D)

Dark void or room. One cool key at low intensity, a primary-accent rim light, emissive screens as the main light, faint volumetric haze, and bloom on everything emissive. Eevee with bloom and soft shadows.

### Recurring objects

Floating screens and phone mockups; chat bubbles; consent banners ("Accept all"); terminals and code; dashboards with big counters; receipts and tickets; progress bars; cursor clicks; rubber stamps ("APPROVED", "SOLD"); version numbers. The shot list already uses almost all of these. All are generic redraws.

### Character and setting

- **Character (replaces "robot"):** a faceless, low-poly humanoid built from Blender primitives. It has a matte mid-grey body (`#847d77`) from rounded boxes and capsules, and its head is a rounded box whose front is a dark **screen face** showing two simple glyph eyes in the primary accent. It averages the mannequins, the blocky robot and the chibi figure without copying any of them. The screen face carries the S13 tear-as-spinner gag.
- **Setting (replaces "neon grid"):** a dark void (base color) with a faint perspective grid floor (lines `#4a4550` at 40%, fading to black at the horizon) and floating UI panels as set dressing. This keeps the brief's grid, but subdued, the way it appears in LGTM and Run It Again.

### Format

- **Aspect ratio:** 16:9 main, 9:16 vertical cut (brief). All five references are 16:9.
- **Resolution:** 1920×1080 delivery. 3D is rendered with ~20% horizontal margin so the vertical crop works (brief).
- **Frame rate: 30 fps.** This is the mode and median of the five (three at 30, two at 60). It also halves render time on the GTX 970 draft machine.

### Pacing

- One composition per lyric line, about 2–4 s, which is one to two bars at the style prompt's 120 bpm (to be confirmed by beat tracking in step 3). Cuts land on downbeats.
- Measured average shot length across all five is 3.1–18 s. This is reliable only for the videos that cut hard; the continuous-camera ones (Accept All, LGTM) undercount. Visually, all five change composition about every 5 s or faster.

## C1 decisions (approved 2026-10-17)

The human replied "LGTM" to the spec and test frame. The two open questions were not answered separately, so the agent's recommendations stand:

1. **FPS counter:** the overlay reads 60, although the video is 30 fps. The lie fits the theme. It drops to ~12 in S19.
2. **Accent pair:** red-orange `#d9502f` primary, blue `#396ad3` secondary.

## Not copied

No frame, character design, logo or asset from the references is reproduced. Only measured properties are carried over: palette clusters, type classes, pacing, and shared object categories.
