// Exercise actual range/tracking functions; synthetic PCM is labelled explicitly.
const assert=require('node:assert/strict'), fs=require('node:fs'), crypto=require('node:crypto');
const {gameHarness}=require('./game-harness.cjs');
const {sandbox,run,element}=gameHarness();
let clock=1000; sandbox.performance={now:()=>clock};
const stored=new Map(); sandbox.localStorage={getItem:k=>stored.get(k)||null,setItem:(k,v)=>stored.set(k,String(v)),removeItem:k=>stored.delete(k)};
run(`stopPreview=()=>{};playPreview=()=>{};drawSelectBg=()=>{};state='select';currentSong='twinkle';guideVoice='Low';`);
function target(ratio,phrase=1){run(`pipeSchedule=[{t:0,end:2,ratio:${ratio},phrase:${phrase}}];gameTime=.5;`)}
function settle(midi,ratio,phrase=1){target(ratio,phrase);clock+=100;run(`singingToRatio(hzOf(${midi}))`);clock+=90;return run(`singingToRatio(hzOf(${midi}))`)}
// Absolute upward crossing, including several octaves: no modulo-12 fold.
for(const start of [38,50,62,74]){
 run('resetRegister()'); settle(start,0);
 const outputs=[];
 for(let midi=start;midi<=start+25;midi++) outputs.push(run(`singingToRatio(hzOf(${midi}),'twinkle',undefined)`));
 assert.ok(outputs.every((v,i)=>!i||v>outputs[i-1]),`ascending register ${start}`);
}
for(const octave of [-12,0,12]){
 run('resetRegister()');
 for(const [midi,ratio] of [[50,0],[52,.14],[54,.29],[55,.43],[57,.57],[59,.71],[61,.86],[62,1]]){
   assert.equal(settle(midi+octave,ratio),ratio);
   assert.equal(run(`voiceMatchesTarget(hzOf(${midi+octave}),${ratio})`),true);
 }
}
// No chart-following: the same held Do cannot hit Sol or La.
run('resetRegister()'); settle(50,0);
for(const ratio of [.57,.71,.29]){
 target(ratio); clock+=100;
 assert.notEqual(run('singingToRatio(hzOf(50))'),ratio);
 assert.equal(run(`voiceMatchesTarget(hzOf(50),${ratio})`),false);
}
target(.57);run('resetRegister()');settle(57,.57);
assert.equal(run('singingToRatio(hzOf(57.6))'),.57);
assert.equal(run('voiceMatchesTarget(hzOf(57.6),.57)'),true);
run('singingToRatio(hzOf(57.8))');assert.equal(run('voiceMatchesTarget(hzOf(57.8),.57)'),false);
assert.equal(run('singingToRatio(-1)'),-1);
assert.equal(run('voiceMatchesTarget(-1,.57)'),false);
assert.equal(run('trackedMidi'),null);
// Recenter between phrases only after consistent octave-equivalent evidence.
run('resetRegister()');settle(50,0,1);target(.14,2);
clock+=10;run('singingToRatio(hzOf(64))');assert.equal(run('registerOffset'),0);
clock+=30;run('singingToRatio(hzOf(64))');assert.equal(run('registerOffset'),0);
clock+=60;assert.equal(run('singingToRatio(hzOf(64))'),.14);assert.equal(run('registerOffset'),12);
// Mid-phrase octave changes stay absolute rather than silently wrapping down.
target(.29,2);clock+=200;assert.ok(run('singingToRatio(hzOf(78))')>1);
assert.equal(run('registerOffset'),12);
// Silence interrupts register evidence instead of counting the silent time.
run('resetRegister()');settle(50,0,1);target(.14,2);
clock+=10;run('singingToRatio(hzOf(64))');clock+=10;run('singingToRatio(-1)');
clock+=300;run('singingToRatio(hzOf(64))');assert.equal(run('registerOffset'),0);
// Detector -> actual mapping at low/high registers (not a mocked Hz detector).
for(const midi of [45,57,69,81]){
 const freq=440*2**((midi-69)/12);sandbox.pcm=Float32Array.from({length:4096},(_,i)=>.2*Math.sin(2*Math.PI*freq*i/48000));
 const detected=run('analysePitchPCM(pcm,48000).frequency');
 assert.ok(Math.abs(1200*Math.log2(detected/freq))<5);
 run('songPreferences.twinkle=-17;resetRegister()');target(0);clock+=100;run(`singingToRatio(${detected})`);clock+=100;
 assert.equal(run(`singingToRatio(${detected})`),0);
}
// Fitting preserves intervals; transposition cannot make an insufficient span fit.
run('comfort={low:45,high:55};songPreferences={}');assert.equal(run('songShift("twinkle")'),-16);
assert.equal(run('comfortFits("twinkle")'),true);
const before=run('songShift("twinkle")');run('adjustSongKey(-1)');assert.equal(run('songShift("twinkle")'),before-1);
assert.ok(stored.has('oohwoo_song_keys_v1'));
run('state="playing";adjustSongKey(1)');assert.equal(run('songShift("twinkle")'),before-1);
run('state="select";comfort={low:48,high:53};songPreferences={};updateComfortUI()');
assert.equal(run('comfortFits("twinkle")'),false);assert.equal(element('btnPlaySong').disabled,true);
assert.match(element('comfortMessage').textContent,/narrower arrangement/);
run('comfort=null;songPreferences={};updateComfortUI()');assert.equal(element('btnPlaySong').disabled,false);
for(let shift=-36;shift<=24;shift++){
 run(`songPreferences.twinkle=${shift}`);
 const key=run(`backingKey(${shift})`);assert.ok(key>=-5&&key<=6);
 assert.ok((shift-key)%12===0);
 const hz=run('guideFrequency(.71,"twinkle")');assert.ok(Math.abs(hz-440*2**((71+shift-69)/12))<1e-7);
}
// Setup at different frame rates: measured data, skip, silence/retry, not defaults as fake success.
for(const fps of [30,60,120,144]){
 run(`comfort=null;startCalibration();calPhase=1;detectPitch=()=>hzOf(calBaseMidi+CAL_STEPS[Math.min(2,Math.floor(calElapsed/2))])`);
 for(let i=0;i<Math.ceil(fps*6)+2&&run('isCalibrating');i++)run(`runDRMFrame(${1/fps})`);
 assert.equal(run('isCalibrating'),false);assert.equal(run('comfort.measured'),true);assert.equal(run('comfort.matched'),true);
 assert.equal(run('comfort.low'),45);assert.equal(run('comfort.high'),54);
 assert.ok(stored.has('oohwoo_comfort_v1'));
}
// Wrong pitches and a matching pitch class in another octave must fail setup.
for (const offset of [3,12,-12]) {
 run(`startCalibration();calPhase=1;detectPitch=()=>hzOf(calBaseMidi+CAL_STEPS[Math.min(2,Math.floor(calElapsed/2))]+${offset})`);
 for(let i=0;i<61;i++) run('runDRMFrame(.1)');
 assert.equal(run('calPhase'),0);assert.equal(run('calSamples.every(a=>a.length===0)'),true);
 assert.match(element('calSetupStatus').textContent,/Not all three notes matched/);
}
// Stable input that is slightly sharp is accepted, without shifting the reference key.
run('startCalibration();calPhase=1;detectPitch=()=>hzOf(calBaseMidi+CAL_STEPS[Math.min(2,Math.floor(calElapsed/2))]+.4)');
for(let i=0;i<61&&run('isCalibrating');i++) run('runDRMFrame(.1)');
assert.equal(run('comfort.low'),45);assert.equal(run('comfort.high'),54);
assert.equal(run('songShift("twinkle")'),-17);
assert.ok(run('comfort.observed[0]>comfort.low'));
run('startCalibration();calPhase=1;detectPitch=()=>-1');
for(let i=0;i<61;i++)run('runDRMFrame(.1)');
assert.equal(run('calPhase'),0);assert.match(element('calSetupStatus').textContent,/Retry/);
const saved=run('JSON.stringify(comfort)');run('stopComfortSetup()');assert.equal(run('JSON.stringify(comfort)'),saved);
// Rendered asset provenance, pitch, sample duration, and unchanged originals.
const report=JSON.parse(fs.readFileSync('docs/step5-audio.json','utf8'));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
assert.equal(hash(report.source),report.sourceSha256);assert.equal(report.variants.length,11);
for(const v of report.variants){assert.equal(hash(v.path),v.sha256);assert.ok(Math.abs(v.probeCentsError)<12);assert.equal(v.decodedDuration,40.6)}
// Actual playback setup shares selected key and fixed deadlines, without rate changes.
const requested=[],tones=[],starts=[],sources=[];
const noop=()=>{};
sandbox.fetch=async url=>{requested.push(url);return {ok:true,arrayBuffer:async()=>new ArrayBuffer(0)}};
sandbox.window.AudioContext=class {
 constructor(){this.currentTime=50;this.state='running';this.destination={}}
 decodeAudioData(){return Promise.resolve({duration:40.6})}
 createBufferSource(){const source={connect:noop,start(...v){starts.push(v)},stop:noop};sources.push(source);return source}
 createGain(){return {gain:{value:0,setValueAtTime:noop,linearRampToValueAtTime:noop},connect:noop,disconnect:noop}}
 createOscillator(){const tone={frequency:{},connect:noop,disconnect:noop,start:noop,stop:noop};tones.push(tone);return tone}
 close(){return Promise.resolve()}
};
(async()=>{
 for(const shift of [-15,0,5,14]){
  run(`currentSong='twinkle';guideEnabled=true;comfort=null;songPreferences.twinkle=${shift};audioBufferCache={}`);
  await run('playBackingTrack()');
  const key=run(`backingKey(${shift})`);
  assert.equal(requested.at(-1),key===0?report.source:`audio/comfort/twinkle-key-${key}.mp3`);
  assert.deepEqual(starts.at(-1),[51.7,0,40.6]);
  assert.equal(sources.at(-1).playbackRate,undefined,'runtime does not change playback rate');
  const authored=JSON.parse(run('JSON.stringify(TWINKLE_CHART.notes)'));
  tones.splice(-42).forEach((tone,i)=>assert.ok(Math.abs(tone.frequency.value-440*2**((authored[i].midi+shift-69)/12))<1e-7));
  const requests=requested.length;await run('loadSongBuffer("twinkle",backingCtx)');assert.equal(requested.length,requests,'selected-key cache reuse');
  run('stopBackingTrack()');
 }
 console.log('PASS: absolute octave crossings, coherent register alternatives, bounded near-note assistance, wrong held pitch/silence rejection, actual-detector low/high synthetic input, key fitting, reversible adjustments, insufficient-range gate, three 2-second setup steps at 30–144fps, retry/skip, guide/key agreement, 11 rendered backing assets, selected-key cache/playback and fixed deadlines. Human comfort/listening approval remains pending.');
})().catch(e=>{console.error(e);process.exitCode=1});

