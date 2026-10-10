"""Convert the checked-in public-domain scores into melody practice charts.

Only the explicit melody part is used, never a piano chord's highest note.
This is separate from the original recording-based catalogue generator.
Run: python tools/build-carol-practice.py
"""
from pathlib import Path
from fractions import Fraction
import json
import re
import struct
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCORES = ROOT / 'docs' / 'carol-scores'
PITCH = dict(C=0, D=2, E=4, F=5, G=7, A=9, B=11)


def abc_melody(path):
    text = path.read_text(encoding='utf-8')
    key = re.search(r'^K:\s*(\w+)', text, re.M)[1]
    unit = Fraction(re.search(r'^L:\s*([\d/]+)', text, re.M)[1]) * 4
    signature = {'A': dict(F=1, C=1, G=1), 'F': dict(B=-1), 'G': dict(F=1)}[key]
    body = text.split('K:', 1)[1].split('\n', 1)[1]
    body = ' '.join(line for line in body.splitlines()
                    if line.strip() and not re.match(r'^\s*(?:[A-Za-z]:|%)', line))
    body = re.sub(r'"[^"]*"', '', body)
    # Expand the repeats actually present in these sources, including two endings.
    if '|:' in body:
        before, repeated = body.split('|:', 1)
        common, after = repeated.split(':|', 1)
        if '|1' in common:
            common, first = common.split('|1', 1)
            assert after.startswith('2')
            body = before + common + first + '|' + common + after[1:]
        else:
            body = before + common + '|' + common + '|' + after
    pattern = r'([_=^]?)([A-Ga-gz])([,\x27]*)(\d*(?:/\d*)?)(-?)|([>|])'
    notes, beat, accidentals, tie, broken = [], Fraction(0), {}, False, False
    position = 0
    for match in re.finditer(pattern, body):
        # Fail rather than silently interpreting unsupported musical syntax.
        assert not re.sub(r'[\s\[\]:.()]', '', body[position:match.start()]), body[position:match.start()]
        position = match.end()
        accidental, letter, octave, length, next_tie, separator = match.groups()
        if separator == '|':
            accidentals = {}
            continue
        if separator == '>':
            extra = notes[-1][2] / 2
            notes[-1][2] += extra
            beat += extra
            broken = True
            continue
        if '/' in length:
            a, b = length.split('/')
            duration = unit * Fraction(int(a or 1), int(b or 2))
        else:
            duration = unit * int(length or 1)
        if broken:
            duration /= 2
            broken = False
        if letter == 'z':
            assert not tie
            beat += duration
            continue
        if accidental:
            accidentals[letter + octave] = {'=': 0, '^': 1, '_': -1}[accidental]
        midi = 60 + PITCH[letter.upper()] + (12 if letter.islower() else 0)
        midi += 12 * (octave.count("'") - octave.count(','))
        midi += accidentals.get(letter + octave, signature.get(letter.upper(), 0))
        if tie:
            assert notes[-1][1] == midi
            notes[-1][2] += duration
        else:
            notes.append([beat, midi, duration, ''])
        tie = bool(next_tie)
        beat += duration
    assert not re.sub(r'[\s\[\]:.()]', '', body[position:])
    transpose = {'A': -9, 'F': -5, 'G': -7}[key]
    return [[float(t), midi + transpose, float(d), word] for t, midi, d, word in notes]


def xml_melody(path):
    root = ET.parse(path).getroot()
    part = root.find("part[@id='P1']")  # Soprano/melody staff, explicitly checked.
    divisions, beat, notes, active_ties = 1, Fraction(0), [], {}
    for measure in part.findall('measure'):
        assert measure.find('.//repeat') is None, 'Expand score repeats before conversion'
        for item in measure:
            if item.tag == 'attributes' and item.find('divisions') is not None:
                divisions = int(item.findtext('divisions'))
            elif item.tag in ('backup', 'forward'):
                raise ValueError('Select a monophonic melody part first')
            elif item.tag == 'note':
                assert item.find('chord') is None, 'Select a monophonic melody part first'
                duration = Fraction(int(item.findtext('duration', '0')), divisions)
                pitch = item.find('pitch')
                if pitch is not None:
                    midi = 12 * (int(pitch.findtext('octave')) + 1) + PITCH[pitch.findtext('step')]
                    midi += int(pitch.findtext('alter', '0'))
                    word = item.findtext('lyric/text', '')
                    ties = {t.attrib['type'] for t in item.findall('tie')}
                    if 'stop' in ties:
                        index = active_ties.pop(midi)
                        notes[index][2] += duration
                    else:
                        index = len(notes)
                        notes.append([beat, midi, duration, word])
                    if 'start' in ties:
                        active_ties[midi] = index
                beat += duration
    assert not active_ties
    # Silent Night is in B-flat; The First Noel is in D. Transpose to C.
    transpose = 2 if path.stem == 'silentnight' else -2
    return [[float(t), midi + transpose, float(d), word] for t, midi, d, word in notes]


def midi_tracks(path):
    data = path.read_bytes()
    assert data[:4] == b'MThd'
    division = struct.unpack('>H', data[12:14])[0]
    tracks, offset = [], 8 + struct.unpack('>I', data[4:8])[0]
    while offset < len(data):
        assert data[offset:offset + 4] == b'MTrk'
        length = struct.unpack('>I', data[offset + 4:offset + 8])[0]
        buf = data[offset + 8:offset + 8 + length]
        offset += 8 + length
        pos, tick, status, active, notes = 0, 0, 0, {}, []

        def variable():
            nonlocal pos
            value = 0
            while True:
                byte = buf[pos]
                pos += 1
                value = (value << 7) | (byte & 127)
                if byte < 128:
                    return value

        while pos < len(buf):
            tick += variable()
            if buf[pos] & 128:
                status = buf[pos]
                pos += 1
            if status == 255:
                pos += 1  # meta type
                count = variable()
                pos += count
            elif status in (240, 247):
                count = variable()
                pos += count
            else:
                event, channel = status >> 4, status & 15
                a = buf[pos]
                pos += 1
                b = 0
                if event not in (12, 13):
                    b = buf[pos]
                    pos += 1
                key = (channel, a)
                if event == 9 and b:
                    assert key not in active
                    active[key] = tick
                elif event == 8 or (event == 9 and b == 0):
                    start = active.pop(key)
                    notes.append([start / division, a, (tick - start) / division, ''])
        assert not active
        tracks.append(sorted(notes))
    return tracks


def lane(semitones):
    steps, lanes = [0, 2, 4, 5, 7, 9, 11, 12], [0, .14, .29, .43, .57, .71, .86, 1]
    octave, local = divmod(semitones, 12)
    i = next(i for i in range(7) if local < steps[i + 1])
    return round(octave + lanes[i] + (local - steps[i]) / (steps[i + 1] - steps[i]) * (lanes[i + 1] - lanes[i]), 5)


def build():
    charts = {}
    specs = [('jinglebells', 100, 32), ('deckthehalls', 100, 16), ('silentnight', 45, 12),
             ('wewish', 108, 24), ('joytotheworld', 85, 12), ('firstnoel', 100, 12)]
    for key, tempo, quick_beats in specs:
        if key == 'joytotheworld':
            tracks = midi_tracks(SCORES / (key + '.mid'))
            # Mutopia's combined upper staff contains soprano + alto. Retain the
            # top line at each attack and verify the resulting line is monophonic.
            upper = tracks[1]
            grouped = {}
            for n in upper:
                if n[0] not in grouped or n[1] > grouped[n[0]][1]:
                    grouped[n[0]] = n
            source = [[t, midi - 2, d, w] for t, midi, d, w in grouped.values()]
            assert [n[1] for n in source[:8]] == [72, 71, 69, 67, 65, 64, 62, 60]
        elif (SCORES / (key + '.abc')).exists():
            source = abc_melody(SCORES / (key + '.abc'))
        else:
            source = xml_melody(SCORES / (key + '.xml'))
        assert source and all(d > 0 for t, m, d, w in source)
        assert all(a[0] + a[2] <= b[0] + 1e-7 for a, b in zip(source, source[1:])), key
        seconds = 60 / tempo
        notes = [dict(id=f'{key}-score-{i}', t=round(2 + t * seconds, 5),
                      end=round(2 + (t + d) * seconds, 5), midi=midi,
                      ratio=lane(midi - 60), note=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][midi % 12] + str(midi // 12 - 1),
                      lyric=word, phrase=f'{key}-score-phrase-{int(t // 12)}')
                 for i, (t, midi, d, word) in enumerate(source)]
        quick = [n for n, src in zip(notes, source) if src[0] < quick_beats]
        charts[key] = dict(tempo=tempo, tonicMidi=60, notes=notes, quickCount=len(quick),
                           status='Score-derived melody practice; listening review pending')
        print(key, len(notes), 'notes', notes[-1]['end'], 'seconds', 'range', min(n['midi'] for n in notes), max(n['midi'] for n in notes))
    html_path = ROOT / 'index.html'
    html = html_path.read_text(encoding='utf-8')
    block = '// <carol-practice>\n// Generated by tools/build-carol-practice.py from docs/carol-scores.\nconst CAROL_PRACTICE = ' + json.dumps(charts, ensure_ascii=False, separators=(',', ':')) + ';\n// </carol-practice>'
    if '// <carol-practice>' in html:
        html = re.sub(r'// <carol-practice>[\s\S]*?// </carol-practice>', lambda _: block, html)
    else:
        html = html.replace('const SONG_DATA = {', block + '\n\nconst SONG_DATA = {')
    with html_path.open('w', encoding='utf-8', newline='\r\n') as file:
        file.write(html)


if __name__ == '__main__':
    build()
