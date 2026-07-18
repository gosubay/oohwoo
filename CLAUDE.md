# CLAUDE.md — OohWoo

A single-file mobile browser rhythm game where you control a bird by singing into the microphone.

## What this is

**OohWoo** is a Flappy-Bird-style game played by singing. High pitch = fly up, low pitch = fly down, silence = glide down. Pipes are timed to melody notes (Twinkle Twinkle Little Star). Tropical rainforest theme.

Everything lives in one file: `ooh-woo-game.html`.

## Running it

```bat
start-game.bat          # double-click: starts Python server + opens browser
```

Or manually:
```bash
python -m http.server 8080
# then open http://localhost:8080/ooh-woo-game.html
```

**Must use `localhost` — `file://` blocks microphone access in Chrome.**

## Architecture

- Single HTML file (`ooh-woo-game.html`) — all game logic, rendering, and audio
- Web Audio API: `getUserMedia` → `AnalyserNode` → autocorrelation pitch detection
- Canvas 2D rendering: parallax background, animated bird, vine pipes
- `requestAnimationFrame` game loop at 60fps
- Keyboard/touch/mouse fallback when mic unavailable

## Key constants and functions

- `MIN_FREQ = 80, MAX_FREQ = 800` — global detection window (covers low male to high child voices)
- `playerMinFreq` / `playerMaxFreq` — personal calibration, saved to `localStorage`
- `freqToRatio(freq)` — maps player's calibrated range to 0–1 bird height
- `freqToNoteName(freq)` — Hz → "C3", "G4" etc. using MIDI math
- `voiceLabel(minHz, maxHz)` — returns "Bass 🎸", "Tenor", "Soprano 🎵" etc.
- `initMic()` — called on song card click (user gesture), not page load
- `ensureMicRunning()` — resumes suspended AudioContext

## Bird "feel" physics (gameLoop, ~line 1640)

Tuned 2026-07-18 to fix sluggish/unresponsive bird movement. Constants live near
`GRAVITY` above `gameLoop`:

- `GRAVITY = 900` (px/s²) / `GLIDE_MAX_SPEED = 260` (px/s) — when silent, the bird
  accelerates into a downward glide (not a hard drop) and caps at terminal velocity.
  Before this fix, `GRAVITY` was `0` and the bird just froze mid-air on silence.
- `MIC_GRACE_MS = 150` — brief mic dropouts (word gaps, breaths between lyrics)
  within this window still count as "singing," so the bird holds its last pitch
  instead of flickering into glide mode between every word.
- Chase-to-target uses a proportional term (`14 × dt`) PLUS a floor speed
  (`220 px/s`) — whichever moves the bird further that frame. This makes it
  actually arrive at the target pitch height instead of crawling the last
  stretch asymptotically (the old code used a flat `8 × dt` lerp with no floor).
- `OCTAVE_JUMP_FRAMES = 2` — a pitch reading that implies a jump > 0.35 of the
  playable range must repeat for 2 consecutive frames before it's trusted. Kills
  single-frame octave-detection glitches with zero added lag on normal singing
  (small/medium moves apply instantly, only large suspicious jumps wait one frame).
- No dead zone on small pitch changes — every frame updates the target height
  directly so gradual pitch slides look smooth, not stair-stepped. (A dead zone
  that ignored moves < 2% of range used to cause this.)
- Bird tilt (`birdAngle`) is now driven by the bird's actual pixel movement that
  frame, not by a velocity variable that stayed 0 in mic mode — so climbing tilts
  the nose up and diving tilts it down, even when the mic is controlling height.

## Screens

1. **Main menu** — song select + live pitch tester + "Set up my voice" calibration button
2. **Calibration** — 2-step: sing lowest note, then highest note (2-second hold each)
3. **Gameplay HUD** — bird, pipes, score, mic indicator dot
4. **Game over** — score + retry
5. **Song complete** — victory screen

## Mic indicator

- Grey = mic off
- Yellow = mic ready, waiting for sound
- Green = actively detecting pitch

## Team

- **Galvin** (`gosu`/`gosubay`) — owner, non-technical, directs via AI agents
- **Chong-U Lim** — technical contributor

Always include a plain-language summary of changes alongside technical detail.

## Commit style

Conventional Commits: `feat(game): short title` with a description of what actually changed.
