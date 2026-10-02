# Note judgement and results — 2026-10-02

Owner approved Perfect/Great/Good/Miss pitch, timing and coverage thresholds, then requested implementation. Perfect and Great build combo; Good and Miss reset it. This is the authorised note-judgement/results change, not completion of the remaining musical-path or combo-recovery work.

| Grade | Absolute pitch error | Arrival tolerance | Correct hold coverage | Performance weight |
| --- | --- | --- | --- | --- |
| Perfect | 35 cents | 100 ms | 80% | 1 |
| Great | 65 cents | 180 ms | 60% | 0.8 |
| Good | 90 cents | 250 ms | 35% | 0.5 |
| Miss | Does not qualify for Good | | | 0 |

Every note resolves once at its end. Time-weighted median absolute voiced error and category-specific hold coverage must both qualify. Stable arrival requires min(60 ms, 30% of note duration), timestamped at the beginning of the matching run. A pitch already held at onset has zero timing error. Repeated same-pitch notes do not require new vocal attacks. Silent gaps up to 80 ms are credited only when bounded by correct singing, with a total allowance of 15% of each note. Rests are not notes.

Judgement uses the raw detected pitch after the accepted register offset, before near-note movement assistance, against the transposed target and musical clock. No guessed capture-latency compensation is applied. Unobserved stall time is not credited. Distinct simultaneous target pitches cannot share a single input sample. Keyboard/touch practice uses its input pitch/height and is labelled on results; mic-off silence does not earn hits.

Points use grade weight multiplied by the existing combo multiplier. Performance rank excludes combo bonuses: 100 × (Perfect + 0.8 Great + 0.5 Good) / total notes. S/A/B/C/D/F thresholds are 95/85/75/65/50/below 50. Results also include hit rate, counts and best combo. Final grade text floats beside the bird, coloured gold/green/blue/red.

Validation: note-judgement.cjs covers boundaries, holds, gaps, median, frame rates, once-only scoring, combo, results, resets and stalls. Existing timing and combo tests now expect end-of-note scoring. The full test suite passes. Browser feedback/results review uses labelled simulated data in tools/judgement-review.html; live singing feel remains for the owner to test.

Intro follow-up: owner requested free voice testing before melody targets. Previously an octave above the selected key could clamp movement at the top until the first note established register alignment. Intro now accepts 80 ms of stable octave evidence around the melody's pitch span and locks that octave for warmup, retaining continuous higher/lower movement. Target-specific alignment resumes normally at the first note. No pitch snapping to targets occurs during intro. Warmup text replaces the rest instruction until the first onset. intro-flight.cjs exercises high/low movement, zero intro scoring, octave locking, retry and interrupted evidence; comfort, timing and graded scoring regression tests pass. Live owner testing remains necessary.
