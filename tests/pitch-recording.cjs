// Validate real-recording numerical evidence from tools/pitch-review.html.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const code=html.slice(html.indexOf('const PITCH_RMS_MIN'),html.indexOf('function detectPitch()')).replace(/\r\n/g,'\n');
const chart=JSON.parse(html.match(/<script id="twinkle-chart" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const report=JSON.parse(fs.readFileSync(path.join(root,'docs/step4-browser.json'),'utf8'));
assert.equal(report.estimatorSha256,crypto.createHash('sha256').update(code).digest('hex'),'browser evidence must match current estimator');
assert.equal(report.asset.sha256,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,report.asset.path))).digest('hex'));
assert.equal(report.asset.path,chart.provenance.assets.find(a=>a.role==='vocal').path);
assert.equal(report.notes.length,chart.notes.length);
report.notes.forEach((n,i)=>{assert.equal(n.id,chart.notes[i].id);assert.equal(n.expectedMidi,chart.notes[i].midi);assert.ok(n.voicedFrames>=5);assert.ok(Math.abs(n.centsError)<50)});
assert.equal(report.liveMicrophoneVerified,false,'recorded audio must not be labelled a live microphone test');
assert.ok(Number.isFinite(report.performance.p95Ms));
console.log('PASS: actual recorded-vocal asset and estimator hashes; 42/42 median pitches within 50 cents with usable voiced samples. This does not establish a low live singer or end-to-end latency.');
