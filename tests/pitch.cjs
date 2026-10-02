const {gameHarness}=require('./game-harness.cjs');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {performance}=require('node:perf_hooks');
const h=gameHarness(),run=h.run;
function tone(freq,rate,amplitude=.2,harmonics=[1],length=4096,phase=0){
 const out=new Float32Array(length);
 for(let i=0;i<length;i++)out[i]=amplitude*harmonics.reduce((sum,g,k)=>sum+g*Math.sin(2*Math.PI*freq*(k+1)*i/rate+phase),0);
 return out;
}
function detect(pcm,rate){h.sandbox.pcm=pcm;h.sandbox.sampleRate=rate;run('micReady=true;micEnabled=true;audioCtx={sampleRate};pitchBuffer=new Float32Array(pcm.length);analyser={getFloatTimeDomainData:b=>b.set(pcm)}');const t=performance.now();const hz=run('detectPitch()');return {hz,candidateHz:run('debugHz'),confidence:run('debugAcMax'),rms:run('debugRms'),computeMs:performance.now()-t}}
module.exports={tone,detect,h};
if(require.main===module){
 const assert=require('node:assert/strict'),results=[],times=[],transitions=[];
 const cents=(a,b)=>1200*Math.log2(a/b);
 function check(name,pcm,rate,expected,tolerance=12){
  const result=detect(pcm,rate);times.push(result.computeMs);
  if(expected<0)assert.equal(result.hz,-1,name);
  else {assert.ok(result.hz>0,`${name} rejected`);assert.ok(Math.abs(cents(result.hz,expected))<tolerance,`${name}: ${result.hz} vs ${expected}`)}
  results.push({name,sampleRate:rate,inputHz:expected,detectedHz:result.hz,centsError:expected>0?cents(result.hz,expected):null,confidence:result.confidence});
 }
 for(const rate of [22050,44100,48000,96000])for(const hz of [80,82.41,110,130.81,220,293.66,440,880,1200,1590,1600]){
  for(const amp of [.02,.2,.6])for(const phase of [0,.73])check(`sine ${hz} amp ${amp} phase ${phase}`,tone(hz,rate,amp,[1],rate>64000?8192:4096,phase),rate,hz);
 }
 for(const rate of [44100,48000])for(const hz of [82.41,110,220,440,880]){
  for(const coeff of [[1,.6,.3,.15],[.4,1,.6,.25],[0,1,.5]])check(`harmonics ${hz} ${coeff}`,tone(hz,rate,.12,coeff),rate,hz);
 }
 let seed=98765;const random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/2**32*2-1};
 for(const rate of [44100,48000]){
  check('silence',new Float32Array(4096),rate,-1);
  check('DC only',new Float32Array(4096).fill(.2),rate,-1);
  check('very quiet sine',tone(110,rate,.001),rate,-1);
  check('white noise',Float32Array.from({length:4096},()=>random()*.2),rate,-1);
  let pink=0;check('low-pass noise',Float32Array.from({length:4096},()=>pink=.88*pink+.12*random()),rate,-1);
  check('out of range low',tone(70,rate),rate,-1);
  check('out of range high',tone(1700,rate),rate,-1);
  const noisy=tone(110,rate,.16,[1,.6,.3]);for(let i=0;i<noisy.length;i++)noisy[i]+=random()*.03;
  check('voiced with modest noise',noisy,rate,110);
  const dc=tone(110,rate);for(let i=0;i<dc.length;i++)dc[i]+=.4;check('voice with DC',dc,rate,110);
  const clipped=tone(110,rate,1.5,[1,.4]);for(let i=0;i<clipped.length;i++)clipped[i]=Math.max(-.9,Math.min(.9,clipped[i]));check('clipped harmonics',clipped,rate,110);
  const fading=tone(110,rate,.2,[1,.4]);for(let i=0;i<fading.length;i++)fading[i]*=.25+.75*i/fading.length;check('amplitude ramp',fading,rate,110);
  // With effectively only the second harmonic, the input genuinely repeats at
  // 220 Hz. No chart-aware guess is allowed to force an absent 110 Hz period.
  check('ambiguous dominant second harmonic',tone(110,rate,.2,[.03,1,0]),rate,220);
  for(const [from,to] of [[0,110],[110,220],[220,110],[110,440],[440,110],[110,0]]){
   let stableAt=null,first=null;
   for(let ms=0;ms<=100;ms+=5){
    const pcm=new Float32Array(4096),end=Math.round(ms*rate/1000);
    for(let i=0;i<pcm.length;i++){const time=(end-pcm.length+i)/rate,f=time<0?from:to;pcm[i]=f? .2*(Math.sin(2*Math.PI*f*time)+.4*Math.sin(4*Math.PI*f*time)):0}
    const out=detect(pcm,rate).hz,match=to===0?out<0:out>0&&Math.abs(cents(out,to))<20;
    if(match){first??=ms;stableAt??=ms}else stableAt=null;
   }
   assert.ok(stableAt!==null&&stableAt<=60,`${rate} transition ${from}->${to}: ${stableAt}`);
   transitions.push({sampleRate:rate,fromHz:from,toHz:to,firstMatchMs:first,stableByMs:stableAt});
  }
 }
 detect(tone(110,48000),48000);detect(new Float32Array(4096),48000);
 assert.equal(run('getCurrentNoteName(82.41)'),'E2 (82Hz)');assert.equal(run('getCurrentNoteName(110)'),'A2 (110Hz)');assert.equal(run('getCurrentNoteName(880)'),'A5 (880Hz)');
 assert.equal(run('pitchReading.voiced'),false);assert.equal(run('debugHz'),0,'silence clears last pitch');
 run('micEnabled=false');assert.equal(run('detectPitch()'),-1);assert.equal(run('debugAcMax'),0,'disabled mic clears stale confidence');
 for(let i=0;i<100;i++)detect(tone(110,48000),48000);
 const warm=[];const pcm=tone(110,48000);for(let i=0;i<300;i++)warm.push(detect(pcm,48000).computeMs);
 const estimator=h.html.slice(h.html.indexOf('const PITCH_RMS_MIN'),h.html.indexOf('function detectPitch()')).replace(/\r\n/g,'\n');
 warm.sort((a,b)=>a-b);const report={kind:'synthetic PCM through actual game detector; no lane/matching mocks',estimatorSha256:crypto.createHash('sha256').update(estimator).digest('hex'),cases:results,transitions,
  performance:{runtime:process.version,platform:process.platform,measured:'this host, Node VM; not mobile browser',medianMs:warm[150],p95Ms:warm[285],maxMs:warm.at(-1)}};
 fs.writeFileSync(path.resolve(__dirname,'../docs/step4-synthetic.json'),JSON.stringify(report,null,2)+'\n');
 console.log(`PASS: ${results.length} actual-detector signal cases; ${transitions.length} transitions stable within 60 ms; Node warm median ${warm[150].toFixed(3)} ms, p95 ${warm[285].toFixed(3)} ms. Live voice is not established by these tests.`);
}
