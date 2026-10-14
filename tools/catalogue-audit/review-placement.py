"""Independent numerical triage of ALL current notes, not a listening approval.

Uses a YIN-style difference function on 64 ms unwindowed frames, independent of
the builder's 186 ms autocorrelation/Viterbi/octave-neighbour pipeline. Does not
transpose, smooth into a key, change charts, or infer lyrics from pitch.
Run with --ffmpeg PATH. Outputs evidence and a per-note review queue.
"""
import argparse, hashlib, json, re, subprocess
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/catalogue-review-2026-10-03'
SR, WIN, HOP = 16000, 1024, 320

def read_audio(path, ffmpeg):
    raw = subprocess.run([ffmpeg, '-v', 'error', '-i', str(path), '-ac', '1',
                          '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)

def track(x):
    times, pitches, energies, confidences = [], [], [], []
    # YIN cumulative mean normalized difference, no expected melody as input.
    lo, hi = int(SR / 1100), int(SR / 75)
    for offset in range(0, max(0, len(x)-WIN+1), HOP*512):
        starts = np.arange(offset, min(len(x)-WIN+1, offset+HOP*512), HOP)
        frames = x[starts[:, None] + np.arange(WIN)[None, :]].astype(np.float64)
        frames -= frames.mean(axis=1, keepdims=True)
        ac = np.fft.irfft(np.abs(np.fft.rfft(frames, 2*WIN, axis=1))**2, axis=1)
        energy = np.concatenate([np.zeros((len(frames),1)), np.cumsum(frames**2,axis=1)],axis=1)
        lags = np.arange(1,hi+1)
        diff = np.maximum(0, energy[:,WIN-lags]+energy[:,WIN,None]-energy[:,lags]-2*ac[:,lags])
        cmnd = diff*lags / np.maximum(np.cumsum(diff,axis=1),1e-12)
        for i, start in enumerate(starts):
            curve = np.r_[1.,cmnd[i]]
            choices = np.where(curve[lo:hi] < .15)[0]
            lag = lo+int(choices[0]) if len(choices) else lo+int(np.argmin(curve[lo:hi]))
            while lag < hi-1 and curve[lag+1] < curve[lag]: lag += 1
            a,b,c = curve[lag-1:lag+2]
            delta = .5*(a-c)/(a-2*b+c) if abs(a-2*b+c)>1e-12 else 0
            hz = SR/(lag+np.clip(delta,-.5,.5))
            times.append((start+WIN/2)/SR)
            pitches.append(69+12*np.log2(hz/440))
            energies.append(np.sqrt(np.mean(frames[i]**2)))
            confidences.append(1-curve[lag])
    t,m,r,c = map(np.asarray,(times,pitches,energies,confidences))
    voiced = (c>.80)&(r>max(.008,float(np.percentile(r,95))*.08))&(m>38)&(m<90)
    return t,m,r,c,voiced

def spans(t, voiced, min_duration=.18, gap=.10):
    inds=np.flatnonzero(voiced)
    if not len(inds): return []
    groups=np.split(inds,np.flatnonzero(np.diff(t[inds])>gap)+1)
    return [[round(float(t[g[0]]-.01),3),round(float(t[g[-1]]+.01),3)]
            for g in groups if t[g[-1]]-t[g[0]]+.02>=min_duration]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',default='ffmpeg');parser.add_argument('--ffprobe',default='ffprobe');args=parser.parse_args()
    OUT.mkdir(exist_ok=True)
    html=(ROOT/'index.html').read_text(encoding='utf-8')
    tw=json.loads(re.search(r'<script id="twinkle-chart" type="application/json">([\s\S]*?)</script>',html)[1])
    charts=json.loads((ROOT/'docs/catalogue-analysis/charts.json').read_text(encoding='utf-8'))
    charts={'twinkle':{'recording':'1. Twinkle Twinkle Little Star','level':tw['level'],
                        'notes':[{**n,'t':n['onset']} for n in tw['notes']]},**charts}
    summary=[];queue=[]; all_evidence={}
    for key,chart in charts.items():
        name=chart['recording'];vocal=ROOT/'separated/vocals'/f'{name}.mp3'
        x=read_audio(vocal,args.ffmpeg);t,m,r,c,v=track(x)
        assets=[]
        for folder in ('songs','audio','separated/vocals'):
            path=ROOT/folder/f'{name}.mp3'
            meta=json.loads(subprocess.run([args.ffprobe,'-v','error','-show_entries','format=duration',
                    '-of','json',str(path)],capture_output=True,check=True,text=True).stdout)
            assets.append({'path':path.relative_to(ROOT).as_posix(),
                           'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                           'containerDuration':round(float(meta['format']['duration']),3)})
        words=json.loads((ROOT/'docs/catalogue-analysis/words'/f'{name}.json').read_text(encoding='utf-8'))
        events=[];rows=[]
        for i,n in enumerate(chart['notes']):
            begin,end=n['t'],n['end']; midi=n['midi'];duration=end-begin
            # Interior for pitch; boundary observations are kept separate.
            mask=(t>=begin+min(.05,duration*.2))&(t<end-min(.04,duration*.2))
            good=mask&v; observed=m[good];frames=int(good.sum())
            median=float(np.median(observed)) if frames else None
            agreement=float(np.mean(np.abs(observed-midi)<=.65)) if frames else 0.
            row={'index':i,'t':begin,'end':end,'midi':midi,'lyric':n.get('lyric',''),
                 'voicedFrames':frames,'voicedFraction':round(frames/max(1,int(mask.sum())),3),
                 'medianMidi':None if median is None else round(median,3),
                 'pitchAgreement':round(agreement,3),'flags':[]}
            if n.get('split'): row['flags'].append('equal-duration-syllable-split')
            if not n.get('lyric','').strip(): row['flags'].append('unlabelled-note-or-melisma')
            if frames<4 or row['voicedFraction']<.45: row['flags'].append('insufficient-independent-voice')
            elif agreement<.65:
                row['flags'].append('independent-pitch-disagreement')
                stable=float(np.mean(np.abs(observed-np.median(observed))<.4))
                if stable>=.8:
                    row['candidateMidi']=int(round(median))
                    row['candidateStatus']='second-estimator-only; inspect recording before adopting'
            # Candidate phrase/pitch starts. Repeated same-pitch attacks cannot be inferred this way.
            prev=chart['notes'][i-1] if i else None
            if prev is None or prev['midi']!=midi or begin-prev['end']>.15:
                match=v&(np.abs(m-midi)<=.65)
                near=[s for s in spans(t,match,min_duration=.08,gap=.021) if abs(s[0]-begin)<=.30 and s[1]>begin+.04]
                if near:
                    candidate=min(near,key=lambda s:abs(s[0]-begin))[0]
                    row['pitchAttackCandidate']=candidate
                    row['attackDeltaMs']=round((candidate-begin)*1000)
                    if abs(candidate-begin)>.1:row['flags'].append('attack-over-100ms-from-pitch-evidence')
            if row['flags']:queue.append({'song':key,**row})
            rows.append(row)
        voice_spans=spans(t,v)
        # Sections are acoustic candidates only, not verse/language boundaries.
        for a,b in voice_spans:
            if events and a-events[-1][1]<1.5:events[-1][1]=b
            else:events.append([a,b])
        full_words=words['words'];lv=chart['level']
        row={'song':key,'recording':name,'recordingSeconds':round(len(x)/SR,2),
             'playEnd':lv['end'],'melodyStart':lv['melodyStart'],'melodyEnd':lv['melodyEnd'],
             'notes':len(rows),'artificialSplits':sum('equal-duration-syllable-split' in n['flags'] for n in rows),
             'unlabelled':sum('unlabelled-note-or-melisma' in n['flags'] for n in rows),
             'pitchDisagreements':sum('independent-pitch-disagreement' in n['flags'] for n in rows),
             'weakVoice':sum('insufficient-independent-voice' in n['flags'] for n in rows),
             'attackFlags':sum('attack-over-100ms-from-pitch-evidence' in n['flags'] for n in rows),
             'transcriptLanguage':words['language'],
             'transcriptWordsAfterCut':sum(w['start']>=lv['end'] for w in full_words),
             'acousticSections':events,'status':'numerical-review; listening-unverified'}
        summary.append(row)
        all_evidence[key]={'assets':assets,'notes':rows,
                           'voicedSpans':voice_spans}
        print(key,len(rows),'notes;',row['pitchDisagreements'],'pitch flags;',row['artificialSplits'],'artificial splits',flush=True)
    provenance={'status':'candidate-evidence-only; not corrected charts or listening approval',
                'gameSha256':hashlib.sha256((ROOT/'index.html').read_bytes()).hexdigest(),
                'chartSourceSha256':hashlib.sha256((ROOT/'docs/catalogue-analysis/charts.json').read_bytes()).hexdigest(),
                'method':'Independent YIN-style difference estimator, 16 kHz, 64ms window, 20ms hop; shared vocal stems, no key snapping or neighbour octave correction. Pitch attacks do not locate consonants or repeated syllables.'}
    for filename,data in [('summary.json',{'provenance':provenance,'songs':summary}),
                          ('note-review-queue.json',{'provenance':provenance,'notes':queue}),
                          ('note-evidence.json',{'provenance':provenance,'songs':all_evidence})]:
        (OUT/filename).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
