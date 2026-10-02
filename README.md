# OohWoo

## Approved rebuild plan — 2026-10-01

The approved next version prioritises forgiving singing, near-hover during silence,
and combo-driven scenery acceleration while musical timing stays fixed. The current
build below does not yet implement that full design.

- [Gameplay specification](docs/GAMEPLAY-SPEC.md): approved design decisions and acceptance criteria.
- [Implementation handover](docs/IMPLEMENTATION-HANDOVER.md): current code, known failures, baseline, and verification limits.
- [Staged task briefs](docs/TASK-BRIEFS.md): stage boundaries, model assignments, and approval status.

Implementation proceeds one approved stage at a time. The first reference level is
one Twinkle verse; full songs remain the intended product experience.

OohWoo is a mobile browser rhythm game controlled by singing. Higher pitch
moves the bird up, lower pitch moves it down, and melody notes appear as
collectible targets timed to the backing track.

## Current Build

- 22 songs with timestamped melody data
- Microphone pitch detection and personal voice calibration
- English and Chinese titles where available
- Karaoke lyrics, note hints, scoring, and combos
- Keyboard, touch, and mouse fallback controls
- Single HTML file with no build step

## Run the Game

Double-click:

```bat
start-game.bat
```

Or start a local server manually:

```bash
python -m http.server 8080
```

Then open:

`http://localhost:8080/ooh-woo-game.html`

Use `localhost`; opening the HTML through `file://` blocks microphone access in
Chrome.

## Controls

- **Voice:** Sing higher or lower to move vertically.
- **Keyboard:** Number keys `1` to `8` select note heights.
- **Touch/mouse:** Hold to use the fallback movement control.
- **Escape:** Pause or resume.
- **Q while paused:** Return to song selection.
- **F1:** Toggle the pitch debug display.

## Project Structure

The complete game is in `ooh-woo-game.html`. MP3 backing tracks are stored in
`audio/`.

See:

- `ROADMAP.md` for current priorities and known issues
- `DESIGN.md` for implementation decisions and timing architecture
- `AGENTS.md` for contributor instructions

## Timing Model

The selected MP3 is loaded before gameplay begins. Music and gameplay are then
scheduled together, and every note target is positioned from the backing
track's audio clock and its timestamp.

Combo tiers increase points and visual glow only. They never change target
speed or musical timing.
