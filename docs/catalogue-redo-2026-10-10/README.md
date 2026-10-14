# Recording-based catalogue rebuild - 10 October 2026

All 22 songs were rebuilt and applied to the game: 4,587 notes across Full song and Quick play. This is an automatic recording-based repair, not a claim that every passage has been listening-verified.

## Changes

- Re-measured pitches with three readers. Changes require two stable, agreeing readings and no stable conflicting reading. Explicit arrangements and approved notes are protected.
- Moved repeated-syllable boundaries to nearby measured vocal attacks. A split needs audio evidence; lyrics alone do not create notes.
- Removed artificial 160 ms note-length padding so releases follow recorded singing.
- Removed four contradictory transcript timing anchors while retaining their words, then realigned lyrics.
- Preserved the approved Twinkle chart, existing language/repeat coverage, and the previously chosen Baby Shark, Xiao Yan Zi, and Chan Mali Chan exclusions.
- The listening catalogue is optional. The owner is not required to manually audit every song.

| Song | Notes | Pitch fixes | Attack fixes | Anchors removed | Releases changed | Full / Quick (seconds) |
|---|---:|---:|---:|---:|---:|---:|
| 1. Twinkle Twinkle Little Star | 84 | 0 | 0 | 0 | 0 | 88.9 / 40.6 |
| 2. Brother John - Two Tigers | 128 | 0 | 0 | 0 | 0 | 106.5 / 21.8 |
| 3. Humpty Dumpty | 149 | 0 | 0 | 0 | 6 | 84.0 / 18.2 |
| 4. Head Shoulders Knees Toes | 158 | 0 | 1 | 0 | 2 | 86.5 / 19.6 |
| 5. London Bridge | 145 | 0 | 0 | 0 | 0 | 94.9 / 25.7 |
| 6. Itsy Bitsy Spider | 175 | 3 | 4 | 0 | 28 | 94.9 / 23.2 |
| 7. Baa Baa Black Sheep | 147 | 0 | 0 | 0 | 2 | 97.6 / 20.7 |
| 8. Mary Had A Little Lamb | 166 | 0 | 2 | 0 | 13 | 97.9 / 23.7 |
| 9. Row Row Row Your Boat | 100 | 0 | 0 | 0 | 8 | 53.4 / 21.5 |
| 10. The More We Get Together | 152 | 0 | 0 | 0 | 19 | 79.4 / 25.0 |
| 11. Little Bunny | 190 | 1 | 0 | 3 | 15 | 87.6 / 19.9 |
| 12. Rain Rain Go Away | 315 | 6 | 0 | 0 | 12 | 179.3 / 29.2 |
| 13. Finger Family | 203 | 0 | 0 | 0 | 6 | 105.0 / 21.1 |
| 14. Wheels On The Bus | 279 | 0 | 1 | 0 | 25 | 133.5 / 26.3 |
| 15. Old McDonald Had a Farm | 575 | 3 | 8 | 0 | 40 | 234.4 / 28.0 |
| 16. If you're happy and you know it | 287 | 4 | 4 | 0 | 60 | 106.7 / 18.9 |
| 17. 5 Little Monkeys | 351 | 4 | 0 | 0 | 15 | 165.9 / 17.7 |
| 18. Baby Shark | 226 | 0 | 10 | 1 | 32 | 137.6 / 19.7 |
| 19. Ba Luo Bo | 228 | 0 | 0 | 0 | 13 | 139.8 / 18.8 |
| 20. Xiao Yan Zi - Little Bird | 185 | 0 | 0 | 0 | 1 | 155.0 / 27.7 |
| 21. Rasa Sayang | 82 | 0 | 0 | 0 | 4 | 58.9 / 30.9 |
| 22. Chan Mali Chan | 262 | 0 | 2 | 0 | 27 | 135.5 / 22.6 |

Release counts include moved repeated-note boundaries; they are not additional independent corrections. Three songs retained identical playable notes because this pass found no supported change.

## Verification

- A fresh full `build_charts.py --check` completed with no differences.
- Asset hashes, all chart intervals, both modes, protected Twinkle reference, and exact generated game block passed validation.
- 69 existing chart-builder fixtures and new consensus, conflict, attack, timestamp-order, and real pitch-tracker tests passed.
- All 15 selected game test files passed, including complete simulations of all 44 song/mode combinations. The synthetic microphone report writer was excluded to preserve an existing local report change; the microphone estimator was not edited.

## Limits

Crowded vocals, shouts and weak lyric transcripts remain uncertain in some passages, particularly Baby Shark and the later Mandarin Rain Rain verses. Diagnostic flags remain visible in the generated correction review. These conservative repairs do not pretend an ambiguous recording has a uniquely proven note. Normal playtesting can identify a specific passage for further work; it is not a prerequisite for using these charts.

See [the generated correction review](../CATALOGUE-CORRECTION-REVIEW.md) for sections and remaining diagnostic flags. The full machine-readable evidence is in ../catalogue-analysis/charts.json.
