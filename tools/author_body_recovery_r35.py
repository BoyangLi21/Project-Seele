"""Full recorded recovery, retaining roll/brace/plant stages omitted by R31's trim."""
from pathlib import Path
import json,numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.interpolate import PchipInterpolator
import author_gameplay_motion_r32 as common
import anatomical_hinge_r35 as hinge
from author_tv_combat_r34 import Actor
ROOT=Path(__file__).resolve().parents[1];PATH=ROOT/'artifacts/combat_rebuild_r35/jbullet/articulated_bodies_r35.json'

def main():
    data=json.loads(PATH.read_text());common.TUFFLES=common.TUFFLES.parent/'General';human,source=common.human('GettingUp');reports={}
    if (human.frames-2)/human.fps<3:raise ValueError('Recovery source is not the complete floor get-up')
    for key in [0,1,2,3,4,'sachiel']:
        actor=Actor(key);retarget=common.rt.Retarget(human,angel=actor.angel,calibrated_trunk=True);frames=[];features=[];origin=None
        source_duration=(human.frames-2)/human.fps;duration=4.35
        clock=PchipInterpolator([0,1.1,2.55,duration],[0,1.15,4.6,source_duration])
        for seconds in np.linspace(0,duration,round(duration*30)+1):
            at=1+float(clock(seconds))*human.fps
            p,travel,_=retarget.pose(float(at),support='fall')
            if origin is None:origin=travel.copy()
            p.setp('root',p.p['root']+travel-origin)
            for s in ('l','r'):
                for upper,lower,end,joint,axis in [('leg_'+s,'shin_'+s,'foot_'+s,actor.knees[s],[-1,0,0]),('arm_'+s,'forearm_'+s,'hand_'+s,actor.elbows[s],[1,0,0])]:
                    goal=p.point(end).copy();orientation=R.from_matrix(p.matrix(end)[:3,:3]);pole=(p.parent(lower)@np.r_[joint,1])[:3]-p.point(upper)
                    hinge.solve(p,actor.P,upper,lower,end,joint,goal,pole,axis,orientation)
            if not actor.angel:
                for n,b in actor.rig.rig.items():
                    if n.startswith('finger_'):p.setq(n,R.from_euler('xyz',np.asarray(b.get('rotation',[0,0,0]))*[-1,-1,1],degrees=True))
                frames.append(actor.rig.encode(p,bone_names=common.NAMES))
            else:frames.append(p.encode())
            front=p.matrix('torso_upper')[:3,:3]@np.array([0,0,-1])
            features.append([float(front[1]),float(p.point('head')[1]*5/16)])
        recovery={'duration_seconds':duration,'source_duration_seconds':source_duration,'sample_rate':30,'bones':actor.names,'frames':frames,'features':features,'source':source,'stage_policy':'Retain roll, hand-brace and foot-plant; compress the seated pause with a monotone smooth clock, and match the physical resting orientation at entry.'}
        data['models'][str(key)]['recovery']=recovery;reports[str(key)]={'frames':len(frames),'duration':duration,'initial_front_y':features[0][0],'end_head_height':features[-1][1]};print(key,reports[str(key)],flush=True)
    PATH.write_text(json.dumps(data,separators=(',',':')));(PATH.parent/'recovery_sources.json').write_text(json.dumps(reports,indent=2))
if __name__=='__main__':main()
