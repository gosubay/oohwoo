"""
convert_to_timestamps.py
Reads ooh-woo-game.html, finds every NOTE_ARRAY + its BPM,
converts beats -> t (absolute seconds), writes back.
"""
import re, sys

with open(r'C:\Claude\Code\OohWoo\ooh-woo-game.html', encoding='utf-8') as f:
    src = f.read()

# Map const-name -> bpm from SONG_DATA block
# e.g.  twinkle: { get notes() { return TWINKLE_NOTES; }, bpm: 120 },
CONST_TO_BPM = {
    'TWINKLE_NOTES':        120,
    'BROTHER_JOHN_NOTES':   112,
    'HUMPTY_DUMPTY_NOTES':  100,
    'HEAD_SHOULDERS_NOTES': 123,
    'LONDON_BRIDGE_NOTES':  108,
    'ITSY_BITSY_NOTES':      89,
    'BAA_BAA_NOTES':         99,
    'MARY_LAMB_NOTES':      123,
    'ROW_BOAT_NOTES':        96,
    'MORE_TOGETHER_NOTES':  117,
    'LITTLE_BUNNY_NOTES':   123,
    'RAIN_RAIN_NOTES':       89,
    'FINGER_FAMILY_NOTES':  112,
    'WHEELS_BUS_NOTES':      89,
    'OLD_MCDONALD_NOTES':    92,
    'IF_HAPPY_NOTES':       129,
    'FIVE_MONKEYS_NOTES':   123,
    'BABY_SHARK_NOTES':     144,
    'BA_LUO_BO_NOTES':       96,
    'XIAO_YAN_ZI_NOTES':   103,
    'RASA_SAYANG_NOTES':     89,
    'CHAN_MALI_CHAN_NOTES':   92,
}

# Regex: find each note object  {note:'X4', ratio:N, beats:N, lyric:'...'}
# We'll work per-array: find the array block, convert in order.

# Matches both single-quoted and double-quoted lyrics, e.g. lyric:'foo' or lyric:"it's"
note_re = re.compile(
    r'\{note:\'([^\']+)\',\s*ratio:([\d.]+),\s*beats:([\d.]+),\s*lyric:([\'"])(.*?)\4\}'
)

def convert_array(block, bpm):
    beat_dur = 60.0 / bpm
    t = 0.0
    def replacer(m):
        nonlocal t
        note, ratio, beats, lyric = m.group(1), m.group(2), float(m.group(3)), m.group(5)
        t_val = round(t, 3)
        # Always output with single quotes; escape any apostrophe as HTML entity &#39;
        safe_lyric = lyric.replace("'", "&#39;")
        result = f"{{note:'{note}', ratio:{ratio}, t:{t_val:.3f}, lyric:'{safe_lyric}'}}"
        t += beats * beat_dur
        return result
    return note_re.sub(replacer, block)

# Process each named array
out = src
for const_name, bpm in CONST_TO_BPM.items():
    # Find the block:  const CONST_NAME = [\n...];
    pattern = re.compile(
        r'(const ' + const_name + r'\s*=\s*\[)(.*?)(\];)',
        re.DOTALL
    )
    def repl(m, bpm=bpm):
        return m.group(1) + convert_array(m.group(2), bpm) + m.group(3)
    out, count = pattern.subn(repl, out)
    print(f'  {const_name}: {count} array(s) converted at {bpm} BPM')

# Also update buildPipes call signature and SONG_DATA bpm fields
# Remove bpm fields from SONG_DATA lines like:   bpm: 120 },
out = re.sub(r',\s*bpm:\s*\d+', '', out)

with open(r'C:\Claude\Code\OohWoo\ooh-woo-game.html', 'w', encoding='utf-8') as f:
    f.write(out)

print('Done.')
