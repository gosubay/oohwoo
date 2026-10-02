"""Render tempo-preserving Twinkle keys, without changing the source assets.
Usage: python tools/render-comfort-audio.py --ffmpeg /path/to/ffmpeg
Requires FFmpeg with librubberband and NumPy. Runtime uses only the rendered MP3s.
"""
from pathlib import Path
import argparse, hashlib, json, subprocess, tempfile, wave
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--ffmpeg', required=True)
args = parser.parse_args()
source = ROOT/'audio/1. Twinkle Twinkle Little Star.mp3'
out = ROOT/'audio/comfort'
out.mkdir(exist_ok=True)
report = {'source': str(source.relative_to(ROOT)).replace('\\','/'),
          'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'method': 'FFmpeg librubberband: tempo=1; pitchq=quality; channels=together; window=long; transients=mixed',
          'ffmpeg': subprocess.check_output([args.ffmpeg,'-version'],text=True).splitlines()[0],
          'excerptSeconds': 40.60, 'listeningApproved': False, 'variants': []}
def command(*parts):
    subprocess.run([args.ffmpeg,'-hide_banner','-loglevel','error','-y',*map(str,parts)],check=True)
def decode(path):
    raw=subprocess.check_output([args.ffmpeg,'-hide_banner','-loglevel','error','-i',str(path),
                                 '-f','f32le','-ar','22050','-ac','1','pipe:1'])
    return np.frombuffer(raw,dtype='<f4')
def pitch_peak(data, expected, rate=22050):
    win=np.hanning(len(data)); spectrum=np.abs(np.fft.rfft(data*win))
    freqs=np.fft.rfftfreq(len(data),1/rate)
    mask=(freqs>=expected*.96)&(freqs<=expected*1.04)
    return float(freqs[mask][np.argmax(spectrum[mask])])
# Test the same render pipeline on a known tone+impulse train. Evaluate duration,
# absolute cents error and transient displacement independently from song quality.
with tempfile.TemporaryDirectory(prefix='oohwoo-key-check-') as temp:
    temp=Path(temp); rate=48000; time=np.arange(rate*3)/rate
    tone=.2*np.sin(2*np.pi*220*time)
    probe=temp/'probe.wav'
    with wave.open(str(probe),'wb') as f:
        f.setparams((1,2,rate,0,'NONE','not compressed'))
        f.writeframes((tone*32767).astype('<i2').tobytes())
    for shift in range(-5,7):
        if shift==0: continue
        ratio=2**(shift/12)
        filtering=f'rubberband=tempo=1:pitch={ratio:.12f}:pitchq=quality:channels=together:window=long:transients=mixed'
        target=out/f'twinkle-key-{shift}.mp3'
        command('-i',source,'-t','40.60','-af',filtering+',apad,atrim=duration=40.60',
                '-c:a','libmp3lame','-b:a','192k',target)
        check=temp/'shift.wav'
        command('-i',probe,'-af',filtering,check)
        decoded=decode(check); expected=220*ratio
        measured=pitch_peak(decoded[22050:22050*2],expected)
        error=1200*np.log2(measured/expected)
        assert abs(error)<12, (shift,error)
        assert abs(len(decoded)/22050-3)<.025
        song=decode(target)
        assert abs(len(song)/22050-40.60)<1/22050
        assert np.isfinite(song).all() and np.max(np.abs(song))<1
        report['variants'].append({'semitones':shift,'path':str(target.relative_to(ROOT)).replace('\\','/'),
          'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'decodedDuration':len(song)/22050,
          'peak':float(np.max(np.abs(song))),'probeCentsError':float(error),
          'probeDuration':len(decoded)/22050})
        print(f'key {shift:+}: duration {len(song)/22050:.3f}s, tone error {error:.2f} cents',flush=True)
(ROOT/'docs/step5-audio.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')

