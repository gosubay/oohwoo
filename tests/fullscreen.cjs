// Full screen: button behaviour per device, and fitting the game inside the safe area.
const assert=require('node:assert');
const {gameHarness}=require('./game-harness.cjs');

// 1. Harness device is an iPhone with no Fullscreen API: the button must explain Add to Home Screen.
{
 const g=gameHarness();
 assert.strictEqual(g.run('fullscreenSupported()'),false);
 assert.strictEqual(g.run('fullscreenDevice()'),'ios');
 g.run('toggleFullscreen()');
 assert.strictEqual(g.element('fullscreenHelp').style.display,'flex');
 assert.match(g.element('fullscreenHelpText').innerHTML,/Add to Home Screen/);
}

// 2. Device wording.
{
 const g=gameHarness();
 const device=ua=>g.run(`navigator.userAgent=${JSON.stringify(ua)};fullscreenDevice()`);
 assert.strictEqual(device('Mozilla/5.0 (Linux; Android 14; Pixel 8) Chrome/126 Mobile'),'android');
 assert.strictEqual(device('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Instagram 300.0'),'in-app');
 assert.strictEqual(device('Mozilla/5.0 (Windows NT 10.0) Chrome/126'),'other');
 assert.match(g.run(`fullscreenHelpHtml('in-app',false)`),/Open in browser/);
 assert.match(g.run(`fullscreenHelpHtml('android',true)`),/refused/);
}

// 3. A browser with the Fullscreen API: the button enters, then exits; the button hides during play.
{
 const g=gameHarness();
 const calls=[];
 Object.assign(g.sandbox.document,{fullscreenEnabled:true,fullscreenElement:null,
  documentElement:{requestFullscreen:()=>{calls.push('enter');return Promise.resolve();}},
  exitFullscreen:()=>{calls.push('exit');}});
 g.sandbox.window.screen={orientation:{lock:o=>{calls.push('lock '+o);return Promise.resolve();}}};
 assert.strictEqual(g.run('fullscreenSupported()'),true);
 g.run('toggleFullscreen()');
 g.sandbox.document.fullscreenElement=g.sandbox.document.documentElement;
 g.handlers.fullscreenchange[0]();
 assert.strictEqual(g.element('btnFullscreen').title,'Exit full screen');
 g.run('toggleFullscreen()');
 assert.deepStrictEqual(calls,['enter','lock portrait','exit']);
 g.run(`showScreen('game')`);
 assert.strictEqual(g.element('btnFullscreen').style.display,'none');
 g.run(`showScreen('main')`);
 assert.strictEqual(g.element('btnFullscreen').style.display,'flex');
}

// 4. A refused request shows the help instead of failing silently.
{
 const g=gameHarness();
 Object.assign(g.sandbox.document,{fullscreenEnabled:true,documentElement:{requestFullscreen:()=>{throw new Error('denied');}}});
 g.run('toggleFullscreen()');
 assert.strictEqual(g.element('fullscreenHelp').style.display,'flex');
}

// 5. Fitting: unchanged with no insets; kept clear of a notch and home bar when there are some.
{
 const g=gameHarness();
 const fit=(w,h,i)=>g.run(`fitGame(${w},${h},${JSON.stringify(i)})`);
 const none={top:0,right:0,bottom:0,left:0};
 assert.deepStrictEqual({...fit(390,844,none)},{scale:1,left:0,top:0});
 const wide=fit(1000,844,none); assert.strictEqual(wide.scale,1); assert.strictEqual(wide.left,305);
 const notch=fit(393,852,{top:59,right:0,bottom:34,left:0});
 assert.ok(notch.top>=59,'below the notch');
 assert.ok(notch.top+844*notch.scale<=852-34+1e-9,'above the home bar');
 assert.ok(notch.left>=0&&notch.left+390*notch.scale<=393+1e-9);
}
console.log('fullscreen: OK');
