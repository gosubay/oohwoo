// Run with node tests/timing.cjs. Exercises the actual inline game in a fake DOM.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const noop = () => {};
const drawing = new Proxy({}, { get: () => noop });
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {
    style: {}, dataset: {}, classList: { add: noop, remove: noop, toggle: noop },
    addEventListener: noop, querySelectorAll: () => [],
    getContext: () => drawing, getBoundingClientRect: () => ({ width: 390, height: 844 }),
    textContent: '', innerHTML: '',
  });
  return elements.get(id);
}
const sandbox = vm.createContext({
  console, Math, Date, Float32Array, Uint8Array, setTimeout: noop, clearTimeout: noop,
  navigator: { userAgent: 'iPhone test' },
  setInterval: noop, clearInterval: noop, requestAnimationFrame: () => 1,
  cancelAnimationFrame: noop, performance: { now: () => 1000 },
  localStorage: { getItem: k => k === 'oohwoo_play_mode_v1' ? 'quick' : null, setItem: noop },
  window: { innerWidth: 390, innerHeight: 844, addEventListener: noop },
  document: { getElementById: element, addEventListener: noop, querySelectorAll: () => [] },
});
const html = fs.readFileSync(require('node:path').join(__dirname, '../index.html'), 'utf8');
element('twinkle-chart').textContent = html.match(/<script id="twinkle-chart" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
vm.runInContext(script, sandbox);
const run = code => vm.runInContext(code, sandbox);
run('drawBackground = drawHitZone = drawBird = drawCoin = () => {};');
assert.equal(run('BIRD_X_MIC === HIT_ZONE_X && BIRD_X_KEY === HIT_ZONE_X'), true);
assert.equal(run(`Object.values(SONG_DATA).every(song => buildPipes(song.notes, song.introOffset).every(n =>
  Math.abs(PIPE_SPAWN_X + PIPE_W / 2 - PIPE_SPEED * (n.t - n.spawnTime) - HIT_ZONE_X) < 1e-8))`), true);
assert.equal(run('buildPipes(TWINKLE_NOTES, 0)[41].t'), 38.66);
assert.equal(run(`Object.values(SONG_DATA).every(song => song.notes.every((n,i,a) => !i || n.t >= a[i-1].t))`), true);
function simulate(fps) {
  return run(`
    startGame('twinkle'); keyRatio = 0.71; micEnabled = false;
    lastTime = 1000;
    for (let frame = 1; frame <= ${fps / 5}; frame++) gameLoop(1000 + frame * 1000 / ${fps});
    birdY;
  `);
}
assert.ok(Math.abs(simulate(30) - simulate(120)) < 0.001, 'same movement at 30 and 120 fps');
run(`startGame('twinkle'); gameLoop(1000);`);
assert.equal(run('Number.isFinite(birdAngle)'), true, 'first frame has a valid angle');
run(`
  startGame('twinkle');
  gameTime = pipeSchedule[0].spawnTime; lastTime = 1000; gameLoop(1000);
`);
assert.equal(run('karaokeActiveIdx'), -1, 'spawning does not advance lyrics');
run(`gameTime = pipeSchedule[0].t; gameLoop(1000);`);
assert.equal(run('karaokeActiveIdx'), 0, 'lyrics advance at onset');
// Final judgement waits for a note's end; correctness is independent of bird travel.
function scoreHeldNote(semitones=0, late=0) {
  run(`startGame('twinkle');micEnabled=true;micReady=true;keyRatio=-1;touchHeld=false;
    getBackingTrackTime=()=>null;gameTime=2;lastTime=1000;
    pipeSchedule=buildPipes([{t:2,end:3,midi:songTonicMidi(currentSong),ratio:0}]);
    noteJudgements=pipeSchedule.map(n=>makeNoteJudgement(n,null));judgementLastTime=2;
    nextPipeIdx=0;birdY=ratioToY(1);birdVY=0;
    detectPitch=()=>gameTime<2+${late} ? -1 : hzOf(songTonicMidi(currentSong)+songShift(currentSong)+${semitones});`);
  run('gameLoop(1016.6666667)');
  assert.equal(run('score'),0,'no final award at onset');
  assert.ok(run('Math.abs(birdY-ratioToY(0))')>32,'bird still in transit');
  for(let f=2;f<=62;f++) run(`gameLoop(${1000+f*1000/60})`);
  return run('noteJudgements[0].result.name');
}
assert.equal(scoreHeldNote(),'Perfect');
assert.equal(scoreHeldNote(4),'Miss');
assert.equal(scoreHeldNote(0,.15),'Great');
assert.equal(scoreHeldNote(0,.3),'Miss');
// Response envelope: smooth onset, fast arrival, no overshoot at multiple refresh rates.
for (const fps of [30, 60, 120, 144]) {
  const result = run(`(() => {
    birdY = ratioToY(0); birdVY = 0;
    const target = ratioToY(0.71), distance = birdY - target;
    let first = 0, overshot = false;
    for (let i = 0; i < Math.ceil(${fps} * 0.15); i++) {
      followPitch(target, 1 / ${fps});
      if (!i) first = (ratioToY(0) - birdY) / distance;
      if (birdY < target) overshot = true;
    }
    return { first, remaining: (birdY - target) / distance, overshot };
  })()`);
  assert.ok(result.first < 0.37, `gentle first frame at ${fps} fps`);
  assert.ok(result.remaining < 0.03, `arrives promptly at ${fps} fps`);
  assert.equal(result.overshot, false);
}
assert.equal(run(`(() => {
  birdY = 500; birdVY = -800;
  followPitch(650, 1 / 60);
  return birdY > 500 && birdY < 650;
})()`), true, 'reversals immediately follow the new direction');
assert.equal(run('ratioToY(0) === PLAY_BOT - BIRD_R && ratioToY(1) === PLAY_TOP + BIRD_R'), true,
  'extreme notes have reachable centres');
// Actual microphone branch: attacks, isolated glitches, and sustained changes.
// Step 5 replaces stateless octave folding. Sequential register/assistance
// tests live in comfort.cjs; keep timing and movement assertions here.
assert.equal(run(`(() => {
  resetRegister();
  const heldDo = guideFrequency(0, 'twinkle', 'Low');
  return singingToRatio(heldDo, 'twinkle', 0.57);
})()`), 0, 'the expected note cannot turn held Do into Sol');
assert.equal(run(`(() => {
  const freq = guideFrequency(0.29, 'twinkle', 'Low');
  assistedLane = null; playerMinFreq = 80; playerMaxFreq = 1200;
  const wide = singingToRatio(freq, 'twinkle', 0.29);
  assistedLane = null; playerMinFreq = 200; playerMaxFreq = 300;
  return wide === singingToRatio(freq, 'twinkle', 0.29);
})()`), true, 'calibration width does not stretch musical lanes');
// Verify guide scheduling with an audio stub; notes use the same absolute onsets as coins.
assert.equal(run(`(() => {
  const tones = [];
  const fakeContext = {
    destination: {},
    createGain: () => ({ gain: { value: 0, setValueAtTime() {}, linearRampToValueAtTime() {} }, connect() {}, disconnect() {} }),
    createOscillator: () => {
      const tone = { frequency: {value: 0}, connect() {}, disconnect() {},
        start(t) { this.when = t; }, stop(t) { this.end = t; } };
      tones.push(tone); return tone;
    },
  };
  scheduleGuide(fakeContext, 'twinkle', 50);
  const notes = buildPipes(TWINKLE_NOTES, 0);
  return tones.length === notes.length && tones.every((tone, i) =>
    Math.abs(tone.when - 50 - notes[i].t) < 1e-8 && Math.abs(tone.end - 50 - notes[i].end) < 1e-8 &&
    Math.abs(tone.frequency.value - guideFrequency(notes[i].ratio, 'twinkle')) < 1e-8);
})()`), true, 'guide audio and targets share timestamps and pitches');
run(`
  startGame('twinkle'); keyRatio = -1; micEnabled = true;
  detectPitch = () => guideFrequency(0,'twinkle');
  performance.now = () => 1000; gameLoop(1000);
`);
assert.equal(run('pitchRatioSmooth'), 0, 'first sung attack does not wait for jump confirmation');
run('detectPitch = () => guideFrequency(.71,"twinkle"); performance.now = () => 1010; gameLoop(1010);');
assert.equal(run('pitchRatioSmooth'), 0, 'isolated large pitch glitch is held');
run('performance.now = () => 1036; gameLoop(1036);');
assert.equal(run('pitchRatioSmooth'), 0.71, 'sustained jump is accepted after 25ms');
run('detectPitch = () => -1; performance.now = () => 1100; gameLoop(1100);');
assert.equal(run('pitchRatioSmooth'), 0.71, 'brief syllable gap holds the pitch');
run('performance.now = () => 1300; gameLoop(1300); performance.now = () => 1350; gameLoop(1350);');
assert.ok(run('birdVY') > 0, 'silence returns to a downward glide');
console.log('PASS: timing, lyrics, sustained-note judgement, 30–144fps motion, microphone transitions, unchanged geometry intervals and guide scheduling. Register acceptance is tested separately.');
