"""R37: distinct two-hit normal chain, high/mid claws, and grounded low follow-up."""
from pathlib import Path
import json,copy,numpy as np
from scipy.spatial.transform import Rotation as R
import author_combat_performance_r36 as perf
import author_combat_r35 as rigs
import author_gameplay_motion_r32 as common
import combat_hand_pose_r36 as fingers
from study_combat_performance_r36 import decode

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/combat_beast_r37/profiles'

def claw(actor,p):
    fingers.apply(p,actor.rig.rig,.55)
    for side in ('l','r'):
        for digit in ('index','middle','ring','little'):
            for suffix,angle in [('',27),('_tip',64),('_distal',46)]:p.setq(f'finger_{digit}{suffix}_{side}',R.from_euler('z',angle,degrees=True))
    return p

def clean_fast_capture(actor,data,clip):
    # A short symmetric quaternion filter removes captured/retargeted elbow
    # singularities without shifting the contact event or replacing its path.
    from scipy.ndimage import convolve1d
    frames=clip['frames'];q=np.array([f['rotation_wxyz'] for f in frames])
    for i in range(1,len(q)):q[i]*=np.where((q[i]*q[i-1]).sum(-1)<0,-1,1)[:,None]
    kernel=np.array([1,4,6,4,1])/16
    for _ in range(2):q=convolve1d(q,kernel,axis=0,mode='nearest');q/=np.linalg.norm(q,axis=-1,keepdims=True)
    for i,f in enumerate(frames):
        f['rotation_wxyz']=q[i].tolist();p=decode(actor,data,f)
        for side in ('l','r'):
            for bone,joint in [('forearm_'+side,actor.elbows[side]),('shin_'+side,actor.knees[side])]:
                offset=joint-actor.P[bone];p.setp(bone,offset-p.q[bone].apply(offset))
        frames[i]=perf.record(actor,p,f['foot_contact'])
    clip['capture_cleanup']='two symmetric five-frame quaternion passes; anatomical joint centres restored'
    return clip

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--rigs',default='0,1,2,3,4');args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);common.OUT=OUT.parent/'sources';common.OUT.mkdir(exist_ok=True)
    for key in map(int,args.rigs.split(',')):
        actor=rigs.Actor(key);name=f'eva_gameplay_r32_{key}.json';data=json.loads((ROOT/'artifacts/combat_direction_r36/profiles'/name).read_text())
        guard=perf.sample(actor,data,data['clips']['r32_guard'],.5)
        raw,source=perf.captured(actor,'ArmsSinglePunch2',False,'cross')
        data['clips']['r32_cross']=perf.convert(actor,data,raw,'cross',guard);data['sources']['cross']=source
        data['ordinary_sequence']=['jab','cross'];data['combat_revision']=37
        if key==1:
            # Stalking posture keeps the long hands below the ribs. Every
            # attack still retains the complete captured body's timing.
            feral=copy.deepcopy(guard)
            feral.setq('torso_upper',feral.q['torso_upper']*R.from_euler('x',-12,degrees=True))
            for side in ('l','r'):feral.setq('forearm_'+side,R.from_euler('x',.55))
            claw(actor,feral)
            for label,source_name,mirror,duration in [
                ('berserk_l','ArmsSlap',True,.9),('berserk_r','ArmsLariat',False,.85),
                ('berserk_upper','ArmsSlapUpwards',False,.8),('berserk_drive','ArmsSinglePunch2',True,1.0),
                ('berserk_down','SlapDownwards',False,1.1)]:
                raw,source=perf.captured(actor,source_name,mirror,'heavy' if label=='berserk_down' else 'jab')
                c=perf.convert(actor,data,raw,label,feral);c['duration_seconds']=duration
                for i,f in enumerate(c['frames']):
                    p=claw(actor,decode(actor,data,f));c['frames'][i]=perf.record(actor,p,f['foot_contact'])
                if label=='berserk_upper':
                    release=decode(actor,data,c['frames'][68])
                    for i in range(69,len(c['frames'])):
                        p=perf.mix(copy.deepcopy(release),copy.deepcopy(feral),perf.ease((i-68)/(len(c['frames'])-1-68)))
                        c['frames'][i]=perf.record(actor,p,c['frames'][68]['foot_contact'] if i<90 else [True,True])
                c['intent']='high_mid_feral' if label!='berserk_down' else 'fallen_target_followup'
                c=clean_fast_capture(actor,data,c)
                data['clips']['r32_'+label]=c;data['sources'][label]=source
            idle=copy.deepcopy(data['clips']['r32_guard']);idle['frames']=[perf.record(actor,copy.deepcopy(feral),[True,True]) for _ in idle['frames']]
            data['clips']['r32_berserk_guard']=idle
            run=copy.deepcopy(common.BODY['motion']['clips']['run']);frames=[]
            for f in run['frames']:
                p=claw(actor,decode(actor,common.BODY['motion'],f));frames.append(perf.record(actor,p,f.get('foot_contact',[False,False])))
            run.update(frames=frames,trajectory_m=[[0,0,0]]*len(frames),leading_side='l',contact_phase=.45)
            data['clips']['r32_berserk_run']=run
        (OUT/name).write_text(json.dumps(data,separators=(',',':')),encoding='utf8');print('R37',key,flush=True)
    d=json.loads((ROOT/'artifacts/combat_direction_r36/profiles/sachiel_gameplay_r32.json').read_text());d['combat_revision']=37
    (OUT/'sachiel_gameplay_r32.json').write_text(json.dumps(d,separators=(',',':')),encoding='utf8')
if __name__=='__main__':main()
