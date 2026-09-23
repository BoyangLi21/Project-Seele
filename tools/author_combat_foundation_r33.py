"""A shared planted boxing stance, authored from one ACCAD performer.

Preserve captured pelvis/chest counter-rotation and heel roll; constrain the
support toes, not the entire leg animation. Source BVH remains private.
"""
from pathlib import Path
import copy, json, zipfile, hashlib
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp
from bvh_motion_r12 import load_bvh, save_npz
import author_gameplay_motion_r32 as old
import retarget_human_r12 as rt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/combat_foundation_r33'
SOURCES=OUT/'sources'
SELECT={'jab':'Male2_E1_JabLeft','cross':'Male2_E4_CrossRight',
        'hook':'Male2_E5_HookLeft','heavy':'Male2_E14_BodyCrossRight'}

def normalized(name):
    path=SOURCES/(name+'.bvh')
    if not path.exists():
        with zipfile.ZipFile(ROOT/'external-assets/incoming/mocap/accad-eva-seed-r01/third_party_raw/Male2_bvh.zip') as z:
            path.write_bytes(z.read(name+'.bvh'))
    m=load_bvh(path); names=list(m['names']); p=m['positions']; q=m['rotations']
    direction=sum(p[:6,names.index(s+'ToeBase')]-p[:6,names.index(s+'Foot')] for s in ('Left','Right')).mean(0)
    rot=R.from_euler('y',np.arctan2(direction[0],-direction[2]))
    p=rot.apply(p.reshape(-1,3)).reshape(p.shape)
    q=(rot*R.from_quat(q.reshape(-1,4))).as_quat().reshape(q.shape)
    # ACCAD has hand endpoints, unlike the CMU adapter's finger and thumb names.
    for side,short in [('Left','L'),('Right','R')]:
        for alias,original in [(side+'FingerBase',side+'Hand_End'),(short+'Thumb',side+'ForeArm')]:
            idx=names.index(original);p=np.concatenate([p,p[:,idx:idx+1]],axis=1);q=np.concatenate([q,q[:,idx:idx+1]],axis=1);names.append(alias)
    m.update(names=names,positions=p,rotations=q);return m

def human(name):
    m=normalized(name);ref=normalized('Male2_A1_Stand');
    m['positions']=np.concatenate([ref['positions'][20:21],m['positions']]);m['rotations']=np.concatenate([ref['rotations'][20:21],m['rotations']])
    path=SOURCES/(name+'_normalized.npz');save_npz(path,m);h=rt.Human(path)
    h.reference_frame=0;h.basis=R.identity();h.reference=m['positions'][1,0].copy();h.reference[1]=0
    h.floor=min(np.percentile(m['positions'][1:,h.index[h.map['ankle_'+s]],1],4) for s in ('l','r'))
    return h

def blend(a,b,t):
    p=rt.battle.ANGEL.pose() if isinstance(a,rt.battle.AngelPose) else rt.battle.hero_copy(a)
    for n in p.q:
        p.setq(n,Slerp([0,1],R.concatenate([a.q[n],b.q[n]]))([np.clip(t,0,1)])[0]);p.setp(n,a.p[n]*(1-t)+b.p[n]*t)
    return p

def ease(t):t=np.clip(t,0,1);return t*t*t*(10+t*(-15+6*t))

def make(key):
    old.configure(key);rig=rt.eva;humans={label:human(name) for label,name in SELECT.items()}
    actors={label:rt.Retarget(h,calibrated_trunk=True) for label,h in humans.items()}
    guard,_,_=actors['jab'].pose(1,support='feet')
    old.rotate_stage(guard,rig,R.from_euler('y',-25,degrees=True))
    guard.setq('head',R.from_matrix(guard.parent('head')[:3,:3]).inv())
    toe_local={}
    for side in ('l','r'):
        points=rig.feet[side];tip=points[points[:,2]<np.percentile(points[:,2],20)]
        toe_local[side]=np.array([np.mean(tip[:,0]),np.min(tip[:,1]),np.mean(tip[:,2])])
    anchors={s:guard.point('foot_'+s)+guard.matrix('foot_'+s)[:3,:3]@toe_local[s] for s in ('l','r')}
    guard_feet={s:R.from_matrix(guard.matrix('foot_'+s)[:3,:3]) for s in ('l','r')}
    clips={}; metrics={}
    for label,h in humans.items():
        actor=actors[label];lead='l' if label in ('jab','hook') else 'r'
        samples=[h.sample(i)[0] for i in range(1,h.frames)]
        extension=np.array([np.linalg.norm(p['wrist_'+lead]-p['shoulder_'+lead]) for p in samples])
        peak=int(np.argmax(extension))
        lo=max(1,peak-round(h.fps*.42));hi=min(h.frames-1,peak+round(h.fps*.70))
        first,origin,_=actor.pose(lo,support='feet');records=[];errors=[];positions=[]
        contact_pose,contact_delta,_=actor.pose(peak+1,support='feet');contact_pose.setp('root',contact_pose.p['root']+contact_delta-origin)
        fist=rig.P['hand_'+lead]+.55*(rig.P['finger_middle_'+lead]-rig.P['hand_'+lead])
        contact_point=contact_pose.point('hand_'+lead,fist);facing=R.from_euler('y',np.arctan2(contact_point[0],-contact_point[2]))
        foot_reference={s:R.from_matrix(first.matrix('foot_'+s)[:3,:3]) for s in ('l','r')}
        # Keep the actor's weight shift as pelvis motion inside the stance, not
        # as a root translation that collides while the legs continue playing.
        for f in np.linspace(lo,hi,round((hi-lo)/h.fps*60)+1):
            p,delta,_=actor.pose(f,support='feet');t=(f-lo)/(hi-lo)
            shift=(delta-origin);shift[1]=0
            p.setp('root',p.p['root']+shift)
            w=min(ease(t/.20),ease((1-t)/.26))
            foot_rotations={s:guard_feet[s]*foot_reference[s].inv()*R.from_matrix(p.matrix('foot_'+s)[:3,:3]) for s in ('l','r')}
            old.rotate_stage(p,rig,facing)
            p=blend(guard,p,w)
            for s in ('l','r'):
                foot_rotations[s]=Slerp([0,1],R.concatenate([guard_feet[s],foot_rotations[s]]))([w])[0]
            # Project the pelvis to the reachable intersection for the longer
            # EVA legs, before solving either knee. No bone scaling/stretch.
            for iteration in range(10):
                for side in ('l','r'):
                    orient=foot_rotations[side];target=anchors[side]-orient.apply(toe_local[side])
                    hip=p.point('leg_'+side);reach=np.linalg.norm(actor.knees[side]-rig.P['leg_'+side])+np.linalg.norm(rig.P['foot_'+side]-actor.knees[side])
                    v=hip-target;length=np.linalg.norm(v)
                    if length>reach*.997:p.setp('root',p.p['root']-v*(1-reach*.997/length))
            for side in ('l','r'):
                orient=foot_rotations[side];target=anchors[side]-orient.apply(toe_local[side])
                pole=p.point('shin_'+side)-p.point('leg_'+side)
                errors.append(rt.solve_ik(p,'leg_'+side,'shin_'+side,'foot_'+side,actor.knees[side],target,pole,orient)*5/16)
            for n in p.q:
                if n.startswith('finger_'):p.setq(n,rt.battle.fist.q.get(n,p.q[n]))
            p.setq('head',R.from_matrix(p.parent('head')[:3,:3]).inv())
            records.append(rig.encode(p,bone_names=old.NAMES));positions.append({s:(p.point('foot_'+s)+p.matrix('foot_'+s)[:3,:3]@toe_local[s]).tolist() for s in ('l','r')})
        contact=np.clip((peak+1-lo)/(hi-lo),.15,.75)
        clips['r32_'+label]={'duration_seconds':(hi-lo)/h.fps,'loop':False,'frames':records,'leading_side':lead,'contact_phase':float(contact),
            'trajectory_m':[[0,0,0]]*len(records),'support':'feet','stance_locked':True}
        metrics[label]={'source_frames':[lo,hi],'contact':float(contact),'facing_correction_degrees':float(facing.as_rotvec()[1]*180/np.pi),'max_toe_error_blocks':max(errors),'frames':len(records)}
    g=rig.encode(guard,bone_names=old.NAMES)
    clips['r32_guard']={'duration_seconds':2.,'loop':True,'frames':[g,g],'leading_side':'l','contact_phase':.5,'trajectory_m':[[0,0,0],[0,0,0]],'support':'feet','stance_locked':True}
    step_sources={}
    steps={'advance':('Male2_E3_Advance',34,64,[0,0,-1]),
           'retreat':('Male2_E5_Retreat',77,108,[0,0,1]),
           'left':('Male2_E9_SideStepLeft',17,44,[-1,0,0]),
           'right':('Male2_E10_SideStepRight',10,41,[1,0,0])}
    for name,(source,lo,hi,direction) in steps.items():
        h=human(source);actor=rt.Retarget(h,calibrated_trunk=True)
        p0,origin,_=actor.pose(lo,support='feet');p1,end,_=actor.pose(hi,support='feet');delta=end-origin
        rotation=R.from_euler('y',np.arctan2(delta[0],-delta[2])-np.arctan2(direction[0],-direction[2]))
        poses=[]
        for f in np.linspace(lo,hi,61):
            p,_,meta=actor.pose(f,support='feet');old.rotate_stage(p,rig,rotation);poses.append(p)
        # Distribute the small cycle seam error over the whole stride. Preserve
        # the captured lower/upper body coupling, never graft idle arms onto legs.
        first,last=poses[0],poses[-1];records=[]
        for i,p in enumerate(poses):
            w=ease(i/(len(poses)-1))
            for n in p.q:
                correction=first.q[n]*last.q[n].inv()
                p.setq(n,R.from_rotvec(correction.as_rotvec()*w)*p.q[n]);p.setp(n,p.p[n]+(first.p[n]-last.p[n])*w)
            p.setq('head',R.from_matrix(p.parent('head')[:3,:3]).inv())
            records.append(rig.encode(p,bone_names=old.NAMES))
        records[-1]=copy.deepcopy(records[0])
        clips['r32_'+name]={'duration_seconds':(hi-lo)/h.fps,'loop':True,'frames':records,'leading_side':'l','contact_phase':.5,
                             'trajectory_m':[[0,0,0]]*len(records),'stride_blocks':float(np.linalg.norm(delta)*5/16),'support':'feet'}
        step_sources[name]={'source':'ACCAD Male2 optical capture / '+source,'sha256':hashlib.sha256((SOURCES/(source+'.bvh')).read_bytes()).hexdigest(),'source_frames_zero_based':[lo-1,hi-1],'license':'CC BY 3.0'}
    data=json.loads((ROOT/f'run/projectseele-local-maps/eva_gameplay_r32_{key}.json').read_text())
    data['clips'].update(clips);data['combat_foundation']=33
    data['support_toes']={s:(toe_local[s]/16).tolist() for s in ('l','r')}
    data['sources'].update({label:{'source':'ACCAD Male2 optical capture / '+name,'sha256':hashlib.sha256((SOURCES/(name+'.bvh')).read_bytes()).hexdigest(),'source_frames':metrics[label]['source_frames']} for label,name in SELECT.items()})
    for label in SELECT:
        data['sources'][label]['source_frames_zero_based']=[v-1 for v in data['sources'][label].pop('source_frames')];data['sources'][label]['license']='CC BY 3.0'
    data['sources'].update(step_sources)
    data['sources']['guard']={'source':'ACCAD Male2 optical capture / '+SELECT['jab'],'sha256':hashlib.sha256((SOURCES/(SELECT['jab']+'.bvh')).read_bytes()).hexdigest(),'source_frames_zero_based':[0,0],'license':'CC BY 3.0','modifications':'Quarter-turned guard, retargeted support toes and stabilized gaze'}
    dest=OUT/'profiles';dest.mkdir(exist_ok=True);(dest/f'eva_gameplay_r32_{key}.json').write_text(json.dumps(data,separators=(',',':')))
    return metrics

def make_angel():
    rig=rt.battle.ANGEL;actors={k:rt.Retarget(human(SELECT[k]),angel=True,calibrated_trunk=True) for k in ('jab','cross','hook')}
    guard,_,_=actors['jab'].pose(1,support='feet');old.rotate_stage(guard,rig,R.from_euler('y',-25,degrees=True));anchors={};toe={};neutral=rig.pose();neutral.ground()
    for s in ('l','r'):
        v=actors['jab'].feet[s];tip=v[v[:,2]<np.percentile(v[:,2],25)]
        toe[s]=np.array([np.mean(tip[:,0]),np.min(tip[:,1]),np.mean(tip[:,2])]);anchors[s]=neutral.point('foot_'+s)+neutral.matrix('foot_'+s)[:3,:3]@toe[s]
    path=OUT/'profiles/sachiel_gameplay_r32.json';data=json.loads((ROOT/'run/projectseele-local-maps/sachiel_gameplay_r32.json').read_text())
    for label,actor in actors.items():
        h=actor.human;side='r' if label=='cross' else 'l';points=[h.sample(i)[0] for i in range(1,h.frames)]
        peak=int(np.argmax([np.linalg.norm(p['wrist_'+side]-p['shoulder_'+side]) for p in points]));lo=max(1,peak-round(h.fps*.42));hi=min(h.frames-1,peak+round(h.fps*.70))
        first,origin,_=actor.pose(lo,support='feet');records=[]
        impact,impact_delta,_=actor.pose(peak+1,support='feet');impact.setp('root',impact.p['root']+impact_delta-origin)
        aim=impact.point('hand_'+side);facing=R.from_euler('y',np.arctan2(aim[0],-aim[2]))
        foot_reference={s:R.from_matrix(first.matrix('foot_'+s)[:3,:3]) for s in ('l','r')}
        for frame in np.linspace(lo,hi,69):
            p,delta,_=actor.pose(frame,support='feet');p.setp('root',p.p['root']+delta-origin);t=(frame-lo)/(hi-lo)
            w=min(ease(t/.20),ease((1-t)/.26));feet={s:foot_reference[s].inv()*R.from_matrix(p.matrix('foot_'+s)[:3,:3]) for s in ('l','r')}
            old.rotate_stage(p,rig,facing);p=blend(guard,p,w)
            feet={s:R.from_rotvec(feet[s].as_rotvec()*w) for s in ('l','r')}
            for _ in range(10):
                for s in ('l','r'):
                    orientation=feet[s];target=anchors[s]-orientation.apply(toe[s]);hip=p.point('leg_'+s)
                    length=np.linalg.norm(actor.knees[s]-rig.P['leg_'+s])+np.linalg.norm(rig.P['foot_'+s]-actor.knees[s]);v=hip-target;reach=np.linalg.norm(v)
                    if reach>length*.997:p.setp('root',p.p['root']-v*(1-length*.997/reach))
            for s in ('l','r'):
                orientation=feet[s];target=anchors[s]-orientation.apply(toe[s]);pole=p.point('shin_'+s)-p.point('leg_'+s)
                rt.solve_ik(p,'leg_'+s,'shin_'+s,'foot_'+s,actor.knees[s],target,pole,orientation)
            p.setq('head',R.from_matrix(p.parent('head')[:3,:3]).inv())
            records.append(p.encode())
        data['clips']['r32_'+label]={'duration_seconds':(hi-lo)/h.fps,'loop':False,'frames':records,'leading_side':side,'contact_phase':float((peak+1-lo)/(hi-lo)),
                                    'trajectory_m':[[0,0,0]]*len(records),'support':'feet','stance_locked':True}
        data['sources'][label]={'source':'ACCAD Male2 optical capture / '+SELECT[label],'sha256':hashlib.sha256((SOURCES/(SELECT[label]+'.bvh')).read_bytes()).hexdigest(),'source_frames_zero_based':[lo-1,hi-1],'license':'CC BY 3.0'}
    data['combat_foundation']=33;path.write_text(json.dumps(data,separators=(',',':')));print('Sachiel grounded jab/cross/hook',flush=True)

if __name__=='__main__':
    import argparse,shutil
    ap=argparse.ArgumentParser();ap.add_argument('--rig',type=int);ap.add_argument('--angel',action='store_true');a=ap.parse_args();SOURCES.mkdir(parents=True,exist_ok=True)
    if a.angel:make_angel();raise SystemExit(0)
    report={}
    for key in ([a.rig] if a.rig is not None else range(5)):
        report[key]=make(key);print(key,report[key],flush=True)
    make_angel()
    (OUT/'authored_support.json').write_text(json.dumps(report,indent=2))
