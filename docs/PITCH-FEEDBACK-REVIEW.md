# Singing feedback

Galvin authorised higher/lower/on-pitch prompts and letter note names after confirming the Low, Middle and High Twinkle setups work and the reference is audible.

The game now separates the current guide target (for example, “Sing Mi · F#3”) from the microphone's closest detected note (“You: E3”). Octave numbers are included; letter names come from actual frequency, before assistance or visual smoothing. Do/Re/Mi describe the target's position within the selected song key, so Do is not always C.

During an authored note, accepted pitch within the existing 65-cent tolerance shows “On pitch — hold!”; lower or higher input requests the corresponding correction. Actual detected/register-aligned MIDI controls this feedback, independently of bird height. Supported alternate octave singing can still match while displaying its honest actual octave name. Silence and microphone dropouts clear the sung note immediately, including during the bird's movement grace period. Intro/rest periods ask the player to listen/breathe. Keyboard and touch input do not claim to detect a sung note. The target label was moved below the top controls to avoid their overlap.

Validation: `node tests/pitch-feedback.cjs`, `node tests/flight-steadiness.cjs`, `node tests/comfort.cjs` and `node tests/timing.cjs` pass. Synthetic input covers sharp note naming, target transposition, tolerance, direction, alternate octaves, silence, rests and mic-off states. Browser inspection verifies HUD placement and the honest microphone-off state. Direction prompts with a real microphone still need the owner's live check.

This change adds feedback only. Existing movement and prototype coin scoring remain. Sustained-note scoring independent of animation and the remaining Step 6 path changes are not implemented by this feedback adjustment.
