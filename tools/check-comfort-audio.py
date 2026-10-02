"""Numerical render quality/timing checks; does not replace listening approval."""
from pathlib import Path
import argparse, json, subprocess
import numpy as np
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--ffmpeg',required=True);args=p.parse_args()
report=json.loads((root/'docs/step5-audio.json').read_text(encoding='utf-8'))
def decode(file):
    raw=subprocess.check_output([args.ffmpeg,'-v','error','-i',str(root/file),'-ar','22050','-ac','2','-t','40.6','-f','f32le','pipe:1'])
    return np.frombuffer(raw,dtype='<f4').reshape(-1,2)
def envelope(x):
    x=np.mean(x*x,axis=1);hop=220
    return np.sqrt(x[:len(x)//hop*hop].reshape(-1,hop).mean(axis=1))
original=decode(report['source']);base=envelope(original)
for v in report['variants']:
    samples=decode(v['path']);env=envelope(samples)
    correlations=[]
    for lag in range(-10,11):
        a=base[10:-10];b=env[10+lag:len(env)-10+lag]
        correlations.append(float(np.corrcoef(a,b)[0,1]))
    best=int(np.argmax(correlations))-10
    v['envelopeLagSeconds']=best*220/22050
    v['envelopeCorrelation']=max(correlations)
    v['rmsRatio']=float(np.sqrt(np.mean(samples*samples)/np.mean(original*original)))
    assert abs(v['envelopeLagSeconds'])<=.04,(v['semitones'],best)
    assert v['envelopeCorrelation']>.85
    print(v['semitones'],round(v['envelopeLagSeconds'],4),round(v['envelopeCorrelation'],4),flush=True)
(root/'docs/step5-audio.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
