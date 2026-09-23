"""Validate fractional recovery handoffs and hinge centres against measured support hulls."""
from pathlib import Path
import json,math,sys
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r31/recovery';profile=json.loads((OUT/'eva_recovery_r31.json').read_text());body=json.loads((ROOT/'run/projectseele-local-maps/eva_body_r31_review.json').read_text());names=profile['bones'];reports=[]
def smooth(x):x=np.clip(x,0,1);return x*x*x*(x*(x*6-15)+10)
def interpolate(a,b,t):
    return ({n:Slerp([0,1],R.concatenate([a[0][n],b[0][n]]))([t])[0] for n in a[0]},{n:a[1][n]*(1-t)+b[1][n]*t for n in a[1]})
for key,info in profile['models'].items():
    rig={b['name']:b for b in body['rigs'][key]};P={n:np.asarray(b['pivot'])*[-1,1,1]/16 for n,b in rig.items()};support={n:np.asarray(v) for n,v in info['support'].items()};anchor=np.array(info['anchor']);sole=np.array(info['sole_l'])
    def base():return ({n:R.from_euler('xyz',np.asarray(b.get('rotation',b.get('bindRotationDegrees',[0,0,0])))*[-1,-1,1],degrees=True) if '_axis_' in n else R.identity() for n,b in rig.items()},{n:np.zeros(3) for n in rig})
    def source(frame):
        q,p=base()
        for n,r in zip(names,frame['rotation_xyzw']):q[n]=R.from_quat(r)
        for n,v in zip(names,frame['positions']):p[n]=np.asarray(v)
        return q,p
    def matrices(pose):
        q,p=pose;result={}
        def get(n):
            if n not in result:
                m=np.eye(4);m[:3,:3]=q[n].as_matrix();m[:3,3]=p[n]+P[n]-m[:3,:3]@P[n];result[n]=get(rig[n]['parent'])@m if rig[n].get('parent') else m
            return result[n]
        for n in rig:get(n)
        return result
    def floor(m):return min(float((v@m[n][1,:3]+m[n][1,3]).min()) for n,v in support.items())
    idle=body['motion']['clips']['idle']['frames'][0];live=base()
    for n,q in zip(names,idle['rotation_wxyz']):live[0][n]=R.from_quat([-q[1],-q[2],q[3],q[0]])
    for n,v in idle.get('bone_position_xyz',{}).items():live[1][n]=np.asarray(v)*[-1,1,1]/16
    live[1]['root']=np.asarray(idle['root_m'])*[-1,1,1]*7
    for n,b in rig.items():
        if '_axis_' in n:live[0][n]=base()[0][n]
    live[1]['root'][1]-=floor(matrices(live));fallen=({n:q for n,q in live[0].items()},{n:p.copy() for n,p in live[1].items()})
    for n,a in {'root':[math.pi/2,0,.1],'torso_lower':[-.1,0,0],'torso_upper':[.1,-.12,0],'head':[.08,.30,-.1]}.items():fallen[0][n]=R.from_euler('XYZ',a)
    for side in ('l','r'):
        l=side=='l'
        for bone,a in {'leg_':[.24 if l else .12,0,-.12 if l else .12],'shin_':[-.60 if l else -.32,0,0],'arm_':[.18,0,-.32 if l else .27],'forearm_':[.48 if l else .68,0,0]}.items():fallen[0][bone+side]=R.from_euler('XYZ',a)
    fallen[1]['root'][1]-=floor(matrices(fallen));minimum=1e9;gap=0.;checked=0
    for duration in ((46,) if '--landing-only' in sys.argv else (46,64,100)):
        start=max(10,duration-44)
        for age in np.arange(0,duration,.25):
            if age<start:amount=1 if duration==46 else smooth(age/9);result=interpolate(live,fallen,amount);lock=ground=amount
            else:
                u=(age-start)/(duration-start);frame=u*(len(info['frames'])-1);a=int(frame);b=min(a+1,len(info['frames'])-1);captured=interpolate(source(info['frames'][a]),source(info['frames'][b]),frame-a);result=interpolate(fallen,captured,smooth(u/.18));settle=smooth((u-.8)/.2);result=interpolate(result,live,settle);lock=ground=1-settle
            for side in ('l','r'):
                for family,marker in [('shin_','r30_knee_socket_'),('forearm_','r30_elbow_socket_')]:
                    n=family+side;centre=P.get(marker+side,P[n]+[0,11.4/16,0] if family=='shin_' else np.array([-23.489652 if side=='l' else 23.489652,123.435069,7.737214])/16);delta=centre-P[n];result[1][n]=delta-result[0][n].apply(delta)
                    mats=matrices(result);parent=rig[n]['parent'];first=(mats[n]@np.r_[centre,1])[:3];second=(mats[parent]@np.r_[centre,1])[:3];gap=max(gap,float(np.linalg.norm(first-second))*5)
            mats=matrices(result);point=(mats['foot_l']@np.r_[sole,1])[:3];result[1]['root'][[0,2]]+=(anchor-point)[[0,2]]*lock;mats=matrices(result);low=floor(mats);result[1]['root'][1]-=low*(1 if low<0 else ground);mats=matrices(result);minimum=min(minimum,floor(mats)*5);checked+=1
    assert minimum>-1e-5 and gap<1e-5
    reports.append({'rig':key,'fractionalFrames':checked,'minimumRigidHullYBlocks':minimum,'maximumElbowKneeHingeGapBlocks':gap,'modelScaleChanged':False});print(json.dumps(reports[-1]),flush=True)
(OUT/('fractional_landing_check.json' if '--landing-only' in sys.argv else 'fractional_blend_check.json')).write_text(json.dumps({'status':'CPU fractional blend/contact validation; no native visual acceptance','models':reports},indent=2))
