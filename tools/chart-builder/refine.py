"""Conservative recording-based repair after lyric alignment.

Re-measure actual note interiors with three unfolded pitch readers; require
stable agreement from at least two and no stable conflicting reader.
No reference melody is used to select pitch. Explicit edits, owner-approved
sections, copied-tune arrangements, and crowded/unstable vocals are protected.
"""
import numpy as np

VERSION = 'recording-refinement-2026-10-10-v1'

def praat_track(samples, sr=16000):
    # Praat's multi-candidate path tracker supplies a third opinion when one
    # local-period estimator locks onto a subharmonic of the singer.
    import parselmouth
    p=parselmouth.Sound(samples.astype(np.float64),sampling_frequency=sr).to_pitch_ac(
        time_step=.01,pitch_floor=75,pitch_ceiling=1000,very_accurate=True,
        voicing_threshold=.55,octave_jump_cost=.35)
    f=p.selected_array['frequency'];strength=p.selected_array['strength']
    return p.xs(),69+12*np.log2(np.maximum(f,1e-9)/440),(f>0)&(strength>=.80)

def reading(track, start, end, tuning):
    t, m, voiced = track
    width = end-start
    use = (t >= start+min(.05,width*.2)) & (t < end-min(.04,width*.2))
    obs = m[use & voiced]-tuning
    if len(obs)<5: return None
    median = float(np.median(obs))
    return dict(median=median, frames=len(obs), coverage=float(len(obs)/max(1,use.sum())),
                stable=float(np.mean(np.abs(obs-median)<=.30)),
                candidateSupport=float(np.mean(np.abs(obs-round(median))<=.4)))

def protected(event, spec):
    if event.get('source') or spec.get('review',{}).get('sections',{}).get(event['section']) == 'owner-listening-approved':
        return True
    override=spec.get('sectionOverrides',{}).get(event['section'],{})
    if override.get('tuneFrom') or override.get('foldInto'):
        return True
    if any(e.get('field')=='midi' or e.get('op') in ('midi','split','join') for e in event.get('edits',[])):
        return True
    return False

def normalize_anchors(units):
    """Keep lexical evidence but remove contradictory transcript timestamps.

    A monotonic lyric sequence cannot move backward through a recording. Select
    the strongest monotonic subsequence; rejected timestamps carry no alignment
    penalty. We do NOT fabricate replacement times or drop the words themselves.
    """
    anchors=[i for i,u in enumerate(units) if u.get('start') is not None and not u.get('weak')]
    if not anchors:return
    score=[];back=[]
    for pos,index in enumerate(anchors):
        weight=2 if units[index].get('status') in ('heard','sung-variant') else 1
        options=[j for j in range(pos) if units[anchors[j]]['start']<=units[index]['start']]
        prev=max(options,key=lambda j:score[j]) if options else None
        score.append(weight+(score[prev] if prev is not None else 0));back.append(prev)
    keep=set();p=max(range(len(anchors)),key=lambda j:score[j])
    while p is not None:keep.add(anchors[p]);p=back[p]
    for i in anchors:
        if i in keep:continue
        u=units[i];u['anchorRepair']={'text':u['text'],'oldStart':u['start'],'oldEnd':u['end'],
          'reason':'transcript timestamp contradicts lyric order; retained word, discarded time'}
        u['start']=u['end']=None

def refine_events(events, spec, yin, raw, tuning, praat=None):
    changes=[]
    for event in events:
        if protected(event,spec): continue
        end=event.get('measuredEnd',event['end'])
        readings={name:reading(track,event['t'],end,tuning) for name,track in
                  [('yin',yin),('autocorrelation',raw)]+([('praat',praat)] if praat is not None else [])}
        reliable={name:r for name,r in readings.items() if r and r['coverage']>=.70 and
                  r['stable']>=.80 and r['candidateSupport']>=.80}
        pairs=[(a,b) for a in reliable for b in reliable if a<b and abs(reliable[a]['median']-reliable[b]['median'])<=.25]
        if not pairs: continue
        # If reliable readers disagree on different pitches, leave the note alone.
        if len({round(r['median']) for r in reliable.values()})>1: continue
        names=max(pairs,key=lambda pair:sum(reliable[n]['frames'] for n in pair))
        one,two=(reliable[n] for n in names)
        # A median alone can hide two pitches. Demand stable, well-observed interiors.
        candidate=int(round((one['median']+two['median'])/2))
        old=event['midi'];delta=abs(candidate-old)
        if candidate==old or not 45<=candidate<=84: continue
        # Nearby pitch or a single-octave correction only, not arbitrary register leaps.
        if delta>2 and delta!=12: continue
        edit={'field':'midi','old':old,'new':candidate,'reason':'two stable independent unfolded pitch readings agree',
              'confidence':'measured-consensus','review':'numerically-corrected; not-listening-verified',
              'method':VERSION,'readings':{name:{k:round(v,3) for k,v in r.items()} for name,r in reliable.items()}}
        event['midi']=candidate
        event.setdefault('edits',[]).append(edit)
        changes.append({'id':event['id'],'t':event['t'],'lyric':event['lyric'],**edit})
    return changes

def refine_attacks(events, spec, env):
    """Locate strong consonant/re-attack valleys near an existing boundary.

    Only touching same-pitch syllables qualify. Pitch transitions, scoops,
    explicit edits, section changes and already-approved passages are untouched.
    No missing syllable is invented, and no silence is padded for playability.
    """
    from acoustics import dips
    changes=[]
    for previous,event in zip(events,events[1:]):
        if protected(previous,spec) or protected(event,spec) or previous.get('edits') or event.get('edits'):continue
        if previous['section']!=event['section'] or previous['midi']!=event['midi']:continue
        if not previous['lyric'] or not event['lyric'] or event['t']-previous['end']>.08:continue
        if event.get('absorbedGlides') or event.get('attack'):continue
        boundary=event['t']
        candidates=[d for d in dips(*env,previous['t'],event['end'],edge=.09,spacing=.08)
                    if d['depth']<=.40 and .025<=abs(d['t']-boundary)<=.10 and
                    d['t']-previous['t']>=.12 and event['end']-d['t']>=.12]
        if not candidates:continue
        times,energy=env
        current=energy[np.abs(times-boundary)<=.015]
        cut=min(candidates,key=lambda d:abs(d['t']-boundary))
        valley=energy[np.abs(times-cut['t'])<=.01]
        # Do not replace an existing equally clear re-attack with another nearby dip.
        if not len(current) or not len(valley) or valley.min()>=.6*current.min():continue
        at=round(cut['t'],2)
        edit={'field':'t','old':boundary,'new':at,'previousEnd':previous['end'],
              'reason':'strong measured re-attack between repeated-pitch syllables','method':VERSION,
              'dipDepth':round(cut['depth'],3),'confidence':'measured-attack',
              'review':'numerically-corrected; not-listening-verified'}
        event['t']=at;previous['end']=at
        event['attack']={'source':'measured attack','t':at,'dipDepth':round(cut['depth'],3)}
        event.setdefault('edits',[]).append(edit)
        changes.append({'id':event['id'],'lyric':event['lyric'],**edit})
    return changes
