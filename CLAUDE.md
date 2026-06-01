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

- `MIN_FREQ = 100, MAX_FREQ = 600` — global detection window (covers bass to soprano)
- `playerMinFreq` / `playerMaxFreq` — personal calibration, saved to `localStorage`
- `freqToRatio(freq)` — maps player's calibrated range to 0–1 bird height
- `freqToNoteName(freq)` — Hz → "C3", "G4" etc. using MIDI math
- `voiceLabel(minHz, maxHz)` — returns "Bass 🎸", "Tenor", "Soprano 🎵" etc.
- `initMic()` — called on song card click (user gesture), not page load
- `ensureMicRunning()` — resumes suspended AudioContext

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
