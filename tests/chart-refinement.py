"""Audio-evidence repair rules, including conflicts and owner protections."""
import copy, os, sys
import numpy as np
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','tools','chart-builder'))
from refine import reading, refine_events, refine_attacks, normalize_anchors, praat_track

t=np.arange(0,1,.01)
def track(midi):return t,np.full(len(t),midi),np.ones(len(t),dtype=bool)
def event():return {'id':'n','t':0.,'end':1.,'midi':60,'lyric':'la','section':'verse'}
e=event();changes=refine_events([e],{},track(62.02),track(62.08),0,track(62.04))
assert e['midi']==62 and len(changes)==1
assert e['edits'][0]['confidence']=='measured-consensus'
e=event();refine_events([e],{},track(62),track(60),0,track(62));assert e['midi']==60,'conflicting stable estimator blocks repair'
e=event();refine_events([e],{},track(48),track(48),0,track(48));assert e['midi']==48,'unfolded octave agreement'
e=event();refine_events([e],{},track(55),track(55),0,track(55));assert e['midi']==60,'do not invent arbitrary leaps'
e=event();e['end']=.05;refine_events([e],{},track(62),track(62),0,track(62));assert e['midi']==60,'short fragments cannot prove pitch'
for spec in [{'review':{'sections':{'verse':'owner-listening-approved'}}},
             {'sectionOverrides':{'verse':{'tuneFrom':{'section':'first'}}}},
             {'sectionOverrides':{'verse':{'foldInto':[60,72]}}}]:
    e=event();refine_events([e],spec,track(62),track(62),0,track(62));assert e['midi']==60
e=event();e['edits']=[{'op':'midi'}];refine_events([e],{},track(62),track(62),0,track(62));assert e['midi']==60
e=event();e['source']='approved reference';refine_events([e],{},track(62),track(62),0,track(62));assert e['midi']==60

# Noisy melody, silence, and two equal stable pitches must not acquire invented consensus.
unstable=t,60+3*np.sin(t*60),np.ones(len(t),dtype=bool)
e=event();refine_events([e],{},unstable,unstable,0,unstable);assert e['midi']==60
silent=t,np.full(len(t),62),np.zeros(len(t),dtype=bool)
assert reading(silent,0,1,0) is None

times=np.arange(0,1,.005);rms=1-.9*np.exp(-((times-.54)/.015)**2)
notes=[{**event(),'id':'a','end':.60},{**event(),'id':'b','t':.60}]
changes=refine_attacks(notes,{},(times,rms))
assert len(changes)==1 and abs(notes[1]['t']-.54)<.011 and notes[0]['end']==notes[1]['t']
notes=[{**event(),'id':'a','end':.60},{**event(),'id':'b','t':.60,'midi':62}]
assert not refine_attacks(notes,{},(times,rms)),'pitch changes are not repeated attacks'
notes=[{**event(),'id':'a','end':.60},{**event(),'id':'b','t':.60}]
assert not refine_attacks(notes,{},(times,np.ones_like(times))),'no equal-time synthetic attack'

units=[{'text':str(i),'start':at,'end':at+.1,'weak':False,'status':'heard'} for i,at in enumerate([0.,1.,5.,2.,3.,4.])]
normalize_anchors(units)
assert units[2]['start'] is None and units[2]['text']=='2' and not units[2]['weak']
assert [u['start'] for u in units if u['start'] is not None]==[0.,1.,2.,3.,4.]
equal=[{'text':'a','start':0.,'end':.1,'weak':False} for _ in range(3)]
normalize_anchors(equal);assert all(u['start']==0 for u in equal)

# Third estimator identifies actual synthetic frequencies without expected-note input.
for hz in (110,220,440,880):
    samples=.2*np.sin(2*np.pi*hz*np.arange(16000)/16000)
    _,m,v=praat_track(samples)
    assert v.any() and abs(float(np.median(m[v]))-(69+12*np.log2(hz/440)))<.05
assert not praat_track(np.zeros(16000))[2].any()
print('PASS: pitch consensus/conflicts, explicit and approved protections, actual re-attacks, monotonic lyric anchors, real pitch tracking and silence.')
