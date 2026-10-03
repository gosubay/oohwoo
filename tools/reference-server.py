"""Local-only chart inspection server. Run from the repository root; requires numpy.
Browser Web Audio decodes MP3s; this server measures the uploaded mono PCM in memory.
No source audio is changed. POST is restricted to the one analysis endpoint.
"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json, re, hashlib, numpy as np

ROOT = Path(__file__).resolve().parents[1]
RATE = 11025
pcm = {}

def analyse():
    chart_text = re.search(r'<script id="twinkle-chart" type="application/json">(.*?)</script>', (ROOT/'index.html').read_text(encoding='utf-8'), re.S)[1]
    chart = json.loads(chart_text)
    src, backing, vocal = [pcm[k] for k in ('source', 'backing', 'vocal')]
    size = min(map(len, (src, backing, vocal)))
    # Estimate gain and reconstruction error; correlated vocals alone do not prove vocal leakage.
    a = np.column_stack([backing[:size:8], vocal[:size:8]])
    coeff = np.linalg.lstsq(a, src[:size:8], rcond=None)[0]
    residual = src[:size:8] - a @ coeff
    def alignment(stem):
        x = src[8*RATE:40*RATE:4]; y = stem[8*RATE:40*RATE:4]
        # First differences emphasise shared attacks; compare +/- 100 ms.
        x, y = np.diff(x), np.diff(y)
        scores = []
        for lag in range(-275, 276):
            xx, yy = (x[-lag:], y[:lag]) if lag < 0 else (x[:-lag], y[lag:]) if lag else (x, y)
            scores.append(float(np.dot(xx, yy) / np.sqrt(np.dot(xx,xx)*np.dot(yy,yy))))
        i = int(np.argmax(scores))
        return {'stemDelaySeconds': round((i-275)*4/RATE,6), 'correlation': scores[i]}
    # Autocorrelation of vocal stem: independent of expected pitch, 180–1000 Hz.
    frames=[]
    for t in np.arange(9.8, 40.6, .01):
        y=vocal[int(t*RATE):int(t*RATE)+2048].astype(float); y-=y.mean()
        rms=float(np.sqrt(np.mean(y*y)))
        z=np.fft.rfft(y,4096); ac=np.fft.irfft(z*z.conj())[:2048]
        ac/=np.arange(2048,0,-1)
        ac/=max(ac[0],1e-12)
        lo,hi=int(RATE/1000),int(RATE/180)
        peaks=[i for i in range(lo+1,hi) if ac[i]>ac[i-1] and ac[i]>=ac[i+1]]
        if peaks:
            best=max(ac[i] for i in peaks)
            lag=next(i for i in peaks if ac[i]>=max(.7,best-.06)) if best>=.7 else max(peaks,key=lambda i:ac[i])
            delta=.5*(ac[lag-1]-ac[lag+1])/(ac[lag-1]-2*ac[lag]+ac[lag+1])
            midi=69+12*np.log2((RATE/(lag+delta))/440)
            frames.append({'time':round(float(t+.093),3),'rms':round(rms,5),'midi':round(float(midi),3),'confidence':round(float(ac[lag]),3)})
    notes=[]
    for n in chart['notes']:
        f=[f for f in frames if n['onset']+.1<=f['time']<=n['end']-.08 and f['rms']>.01 and f['confidence']>.7]
        med=float(np.median([f['midi'] for f in f])) if f else None
        notes.append({'id':n['id'],'expectedMidi':n['midi'],'medianMidi':round(med,3) if med else None,'frames':len(f)})
    return {'chartSha256':hashlib.sha256(chart_text.encode()).hexdigest(),
        'assets':chart['provenance']['assets'],
        'method':'Web Audio decode, mono 11025 Hz; numpy autocorrelation, 186 ms frames / 10 ms hops. Numerical evidence, not listening.',
        'durations':{k:len(v)/RATE for k,v in pcm.items()},'alignment':{'backing':alignment(backing),'vocal':alignment(vocal)},
        'sourceReconstruction':{'gains':coeff.tolist(),'relativeRmsError':float(np.sqrt(np.mean(residual**2)/np.mean(src[:size:8]**2)))},
        'notes':notes,'frames':frames}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
    def do_POST(self):
        if self.path == '/pitch-report':
            length = int(self.headers.get('Content-Length', '0'))
            if self.headers.get('Origin') not in ('http://localhost:8081','http://127.0.0.1:8081') or not 0 < length < 200_000:
                self.send_error(400); return
            try:
                report = json.loads(self.rfile.read(length))
                if report.get('kind') != 'Decoded real Twinkle vocal recording through current game estimator; not live microphone evidence' or len(report.get('notes',[])) != 42:
                    raise ValueError('Invalid pitch report')
                (ROOT/'docs/step4-browser.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            except (ValueError,TypeError):
                self.send_error(400); return
            self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(b'{"saved":true}'); return
        key=self.path.removeprefix('/analyse/')
        length=int(self.headers.get('Content-Length','0'))
        if key not in ('source','backing','vocal') or not 0<length<8_000_000:
            self.send_error(400); return
        if self.headers.get('Origin') not in ('http://localhost:8081','http://127.0.0.1:8081'):
            self.send_error(403); return
        pcm[key]=np.frombuffer(self.rfile.read(length),dtype='<f4').copy()
        result=analyse() if len(pcm)==3 else {'received':key}
        if len(pcm)==3:
            (ROOT/'docs/twinkle-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
        data=json.dumps({k:v for k,v in result.items() if k!='frames'}).encode()
        self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(data)

if __name__=='__main__':
    print('Twinkle review: http://localhost:8081/tools/twinkle-review.html',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8081),Handler).serve_forever()
