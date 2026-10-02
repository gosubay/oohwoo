const assert=require('node:assert/strict');
const {gameHarness}=require('./game-harness.cjs');
async function main(){
 const {sandbox,run}=gameHarness();let requests=0,contexts=0,connections=0,resumes=0,closes=0,failResume=false,resolveCapture;
 const tracks=[];
 function stream(){const events={};const t={readyState:'live',stopCount:0,stop(){this.stopCount++;this.readyState='ended'},getSettings:()=>({latency:.012,echoCancellation:true,noiseSuppression:false,autoGainControl:false}),addEventListener:(name,fn)=>events[name]=fn};tracks.push({track:t,events});return {getAudioTracks:()=>[t],getTracks:()=>[t]}}
 const errors=[];sandbox.console={log(){},warn(...v){errors.push(v)}};
 sandbox.navigator.mediaDevices={getUserMedia(options){requests++;assert.equal(options.audio.echoCancellation,true);assert.equal(options.audio.autoGainControl,false);return new Promise(resolve=>resolveCapture=resolve)}};
 sandbox.window.AudioContext=class {
  constructor(options){contexts++;assert.equal(options.latencyHint,'interactive');this.state='suspended';this.sampleRate=48000;this.baseLatency=.003;this.outputLatency=.02}
  resume(){resumes++;if(failResume)return Promise.reject(Error('resume blocked'));this.state='running';return Promise.resolve()}
  createAnalyser(){return {fftSize:0}}
  createMediaStreamSource(){return {connect(){connections++},disconnect(){}}}
  close(){closes++;this.state='closed';return Promise.resolve()}
 };
 assert.equal(requests,0,'page load never requests microphone permission');
 const first=run('initMic()'),second=run('initMic()');assert.equal(first,second,'pending capture is shared');
 await Promise.resolve();assert.equal(requests,1);assert.equal(contexts,0);
 resolveCapture(stream());assert.equal(await first,true);assert.equal(await second,true);
 assert.equal(contexts,1);assert.equal(connections,1);assert.equal(run('micInitPromise'),null);
 assert.equal(run('micReady'),true);assert.equal(run('analyser.fftSize'),4096);
 assert.equal(run('micTiming.captureLatencyMs'),12);assert.equal(run('micTiming.baseLatencyMs'),3);
 assert.equal(await run('initMic()'),true);assert.equal(requests,1,'reuse ready capture');
 run('audioCtx.state="suspended"');assert.equal(await run('ensureMicRunning()'),true);assert.equal(resumes,2);
 failResume=true;run('audioCtx.state="suspended"');assert.equal(await run('initMic()'),false);assert.equal(requests,1);
 failResume=false;assert.equal(await run('initMic()'),true);
 // A lost device invalidates readings. Denial is recoverable and concurrent
 // retries still request only once, including synchronously thrown failures.
 tracks[0].track.readyState='ended';tracks[0].events.ended();assert.equal(run('micReady'),false);assert.equal(run('pitchReading.voiced'),false);
 sandbox.navigator.mediaDevices.getUserMedia=()=>{requests++;throw Error('permission denied')};
 const denied=run('initMic()'),denied2=run('initMic()');assert.equal(denied,denied2);
 assert.equal(await denied,false);assert.equal(run('micInitPromise'),null);
 sandbox.navigator.mediaDevices.getUserMedia=()=>{requests++;return Promise.resolve(stream())};
 assert.equal(await run('initMic()'),true);assert.equal(contexts,2);assert.equal(connections,2);
 assert.equal(tracks[0].track.stopCount,1);assert.equal(closes,1,'old context released');
 tracks[0].events.ended();assert.equal(run('micReady'),true,'old-device events cannot invalidate replacement');
 // Failure after permission but before source wiring releases newly captured
 // tracks and context, then allows another attempt.
 run('micReady=false');const normal=sandbox.window.AudioContext;
 sandbox.window.AudioContext=class extends normal{createMediaStreamSource(){throw Error('wiring failed')}};
 assert.equal(await run('initMic()'),false);assert.equal(tracks.at(-1).track.stopCount,1);assert.equal(run('micInitPromise'),null);
 sandbox.window.AudioContext=normal;assert.equal(await run('initMic()'),true);
 // No duplicate menu polling loops; pause menu/game transitions release the flag.
 const callbacks=[];sandbox.requestAnimationFrame=fn=>{callbacks.push(fn);return callbacks.length};
 run('micTesterRunning=false;state="main";startMicTester();startMicTester()');assert.equal(callbacks.length,1);
 run('state="playing"');callbacks[0]();assert.equal(run('micTesterRunning'),false);
 run('state="main";startMicTester()');assert.equal(callbacks.length,2);
 // Large sample rates get sufficient history without changing musical clocks.
 tracks.at(-1).track.readyState='ended';tracks.at(-1).events.ended();
 sandbox.window.AudioContext=class extends normal{constructor(options){super(options);this.sampleRate=96000}};
 assert.equal(await run('initMic()'),true);assert.equal(run('analyser.fftSize'),8192);
 assert.ok(errors.length>=3,'failure branches exercised');
 console.log('PASS: no permission at page load; one shared capture/context/source; ready reuse; suspended resume; denial and partial-setup cleanup/retry; track loss/replacement; reported latency; single tester loop; 96kHz buffer sizing. Mock devices do not establish real microphone compatibility.');
}
main().catch(error=>{console.error(error);process.exitCode=1});
