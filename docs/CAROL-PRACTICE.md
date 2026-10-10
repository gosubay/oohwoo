# Seasonal catalogue and score-based melody practice

Added 10 October 2026 at Galvin's request. The catalogue now has All, Nursery Rhymes,
Christmas Songs and Chinese New Year Songs. The original 22 entries are under Nursery
Rhymes. Six Christmas carols are playable melody practice; eight unique CNY titles are
listed as coming soon. The repeated He Xin Nian request is one entry.

## Christmas practice

Galvin explicitly chose score-based practice with generated piano-style audio in this
chat. This adds a separate route alongside the recording-based chart workflow. Existing
recordings and their Full song / Quick play definitions are unchanged.

Each carol offers **Melody practice** (one complete notated melody cycle, including the
score's internal repeats) and **Short practice** (an opening excerpt). These are not
advertised as complete multi-verse vocal recordings. There is a two-second lead-in and
a short ending tail. Audio and targets share exactly the same note starts, durations
and selected key. The piano-style melody remains audible with the optional guide off.
It is synthesized locally, with no downloaded performer recording or soundfont.

Sources are checked into `docs/carol-scores/`; exact download URLs are in `sources.json`.

| Song | Source | Selection |
| --- | --- | --- |
| Jingle Bells | [John Chambers ABC](https://trillian.mit.edu/~jc/music/abc/program/xmas/Jingle_Bells_VC-A-32-3.abc) | Traditional verse and chorus; repeat and alternate endings expanded |
| Deck the Halls | [1927 Everyday Song Book transcription](https://trillian.mit.edu/~jc/music/book/EverydaySongBook/105_Deck_the_Hall.abc) | Historical melody; opening repeat expanded |
| Silent Night | [Hymns and Carols MusicXML](https://www.hymnsandcarolsofchristmas.com/Hymns_and_Carols/XML/STILLE_NACHT.xml) | Explicit first melody staff; XML declares Public Domain |
| We Wish You a Merry Christmas | [Thornton Rose / John Chambers ABC](https://trillian.mit.edu/~jc/music/abc/xmas/song/We_Wish_You_a_Merry_Christmas-G-16-wW.abc) | Traditional opening and good-tidings refrain |
| Joy to the World | [Mutopia Antioch](https://www.mutopiaproject.org/ftp/HandelGF/antioch/) | Soprano from the combined upper-staff MIDI; LilyPond source declares Public Domain |
| The First Noel | [Hymns and Carols MusicXML](https://www.hymnsandcarolsofchristmas.com/Hymns_and_Carols/XML/First_Nowell.xml) | First melody staff; Douglas D. Anderson transcription explicitly released to Public Domain |

The ABC files retain their transcriber attribution. Only the historical melody is
used, with transposition and a chosen practice tempo; no modern harmonization is used.
Two initially inspected modern orchestral XML arrangements were rejected and are not
included. These are score-derived practice drafts, not owner-listening-verified charts.

Rebuild with `python tools/build-carol-practice.py`. It changes only the separate
`carol-practice` block in `index.html`; it never rebuilds the original catalogue block.
`tools/download-carol-scores.py` downloads missing sources (requires requests and network).

## Chinese New Year entries

Gong Xi Fa Cai (Andy Lau), Gong Xi Gong Xi (Chen Gexin), Cai Shen Dao (Sam Hui),
Hao Yun Lai (Zu Hai), He Xin Nian, Bai Nian (Zhuo Yiting), Tao Hua Duo Duo Kai
(Ah Niu), and Xin Nian Dao are catalogue entries only. No audio, lyrics or melody
charts for these titles are included. Artist names identify the requested versions;
they do not indicate affiliation. Specific composition/recording clearance and source
selection remain pending. He Xin Nian, Bai Nian and Xin Nian Dao in particular need an
exact version identified before sourcing a chart.

## Verification

`node tests/song-categories.cjs` checks filtering and wraparound, unavailable entries,
known melody openings, both practice lengths through a complete game simulation,
generated audio pitches, chart/audio lead-ins and regeneration after key changes.
The existing recording catalogue tests still cover all 22 original songs.

For future piano scores, MusicXML/MIDI is preferable to a scanned PDF. Select the actual
singing melody, expand repeats, join tied notes, preserve rests, choose a tempo, then
generate audio and targets from the same events. A score alone cannot reproduce the
timing of a separate singer's recording; that still needs recording-based alignment.
