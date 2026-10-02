// Actual HUD logic with synthetic pitches; no live singing is implied.
const assert = require('node:assert/strict');
const {gameHarness} = require('./game-harness.cjs');
const {run, element} = gameHarness();
run(`currentSong='twinkle';comfort=null;songPreferences.twinkle=-12;
  micEnabled=micReady=true;registerOffset=0;gameTime=1;
  pipeSchedule=[{t:1,end:2,ratio:.29,midi:66,phrase:1}];`);
const feedback = element('pitchFeedback'), status = element('micStatus'), target = element('noteHint');
function sing(midi) {
  run(`trackedMidi=${midi};updatePitchFeedback(hzOf(${midi}));`);
}
sing(54);
assert.equal(target.textContent,'Sing Mi · F#3');
assert.equal(status.textContent,'🎤 You: F#3');
assert.equal(feedback.textContent,'On pitch — hold!');
sing(52); assert.equal(feedback.textContent,'Sing higher ↑');
sing(56); assert.equal(feedback.textContent,'Sing lower ↓');
// Clamped geometry cannot turn a wrong voice into "on pitch".
run('pitchRatioSmooth=.29;flightRatioFiltered=.29');
sing(52); assert.equal(feedback.textContent,'Sing higher ↑');
sing(54.64); assert.equal(feedback.textContent,'On pitch — hold!');
sing(54.66); assert.equal(feedback.textContent,'Sing lower ↓');
// Actual octave name stays honest even when the game accepts another register.
run('registerOffset=12;trackedMidi=54;updatePitchFeedback(hzOf(66))');
assert.equal(status.textContent,'🎤 You: F#4');
assert.equal(feedback.textContent,'On pitch — hold!');
run('updatePitchFeedback(-1)');
assert.equal(status.textContent,'🎤 You: — · No steady note');
assert.equal(feedback.textContent,'Sing the guide note');
run('gameTime=2;updatePitchFeedback(hzOf(54))');
assert.equal(target.textContent,'Listen · breathe');
assert.equal(feedback.textContent,'Listen · breathe');
run('gameTime=.9;updatePitchFeedback(hzOf(54))');
assert.equal(feedback.textContent,'Listen · breathe');
run('gameTime=1;micEnabled=false;updatePitchFeedback(hzOf(54))');
assert.equal(feedback.textContent,'Sing the guide note');
assert.equal(status.textContent,'🎤 Mic off · use Mic ON to sing');
run('updatePitchFeedback(-1,true)');
assert.equal(feedback.textContent,'Enable your mic for singing feedback');
// Both transposition and timing affect the target, independent of original Do/Re/Mi.
run('micEnabled=true;songPreferences.twinkle=-11;trackedMidi=55;updatePitchFeedback(hzOf(55))');
assert.equal(target.textContent,'Sing Mi · G3');
assert.equal(status.textContent,'🎤 You: G3');
assert.equal(feedback.textContent,'On pitch — hold!');
console.log('PASS: letter/octave names, transposed targets, pitch direction/tolerance, rests, silence, mic-off, alternate register and visual independence.');
