"""Continuous unarmed stance path and alternating supported crawl from the measured R06 body."""
import json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
import build_eva_body_r05 as rig
import author_eva_rifle_stances_r06 as body
from author_first_battle_r10 import stable_ik,AXES
rig.Pose.ik=stable_ik
ROOT=rig.ROOT;OUT=ROOT/'artifacts/world_motion_r11/motion';OUT.mkdir(parents=True,exist_ok=True)
def frame(along,across):
 y=np.asarray(along,float);y/=np.linalg.norm(y);x=np.asarray(across,float);x-=y*(x@y);x/=np.linalg.norm(x);return np.column_stack((x,y,np.cross(x,y)))
def palms(p,phase=0,moving=False):
 for side,sign in [('l',-1),('r',1)]:
  shoulder=p.point('arm_'+side);u=(phase+(0 if side=='l' else .5))%1
  # Pull while supported, then recover the released hand above the ground.
  pull=u/.64 if u<.64 else (1-u)/.36
  forward=44-22*pull if moving else 37
  lift=5*math.sin(math.pi*(u-.64)/.36) if moving and u>=.64 else 0
  target=shoulder+np.array([sign*5,0,-forward]);target[1]=5+lift
  localAlong=rig.P['finger_middle_'+side]-rig.P['hand_'+side];localAcross=rig.P['finger_index_'+side]-rig.P['finger_little_'+side]
  q=R.from_matrix(frame([0,0,-1],[1,0,0])@frame(localAlong,localAcross).T)
  for n in ['wrist_'+side,'hand_'+side]:p.setq(n,R.identity());p.setp(n,np.zeros(3))
  p.ik('arm_'+side,'forearm_'+side,'hand_'+side,rig.E[side],target,np.array([sign,-.7,0.]),q)
  for n in rig.rig:
   if n.startswith('finger_') and n.endswith('_'+side) and '_axis_' not in n:p.setq(n,R.identity())
def main():
 data=rig.load(ROOT/'run/projectseele-local-maps/eva_body_r06.json');motion=data['motion'];names=motion['bones']
 standing=rig.decode(motion['clips']['idle']['frames'][0],names);squat=rig.decode(motion['clips']['crouch_idle']['frames'][0],names);lying=rig.decode(motion['clips']['rifle_stance']['frames'][-1],names)
 palms(lying);support=body.blend_pose(squat,lying,.57)
 keys=[standing,squat,support,lying];frames=[];AXES.clear()
 for i in range(181):
  at=i/60;segment=min(2,int(at));p=body.blend_pose(keys[segment],keys[segment+1],at-segment,segment==0)
  frames.append(rig.encode(p,bone_names=names))
 motion['clips']['unarmed_stance']={'duration_seconds':3,'loop':False,'frames':frames}
 crawl=[];mins=[];AXES.clear()
 for i in range(61):
  phase=i/60;p=body.clone(lying);wave=math.sin(phase*2*math.pi)
  p.setq('torso_lower',p.q['torso_lower']*R.from_euler('z',wave*.045));p.setq('torso_upper',p.q['torso_upper']*R.from_euler('z',-wave*.035))
  for s,sign in [('l',1),('r',-1)]:p.setq('leg_'+s,p.q['leg_'+s]*R.from_euler('xyz',[sign*wave*.10,sign*wave*.035,0]));p.setq('shin_'+s,p.q['shin_'+s]*R.from_euler('x',max(0,sign*wave)*-.18))
  palms(p,phase,True);lowest=body.floor(p,['torso_lower','torso_upper','leg_l','leg_r','shin_l','shin_r','foot_l','foot_r','hand_l','hand_r','forearm_l','forearm_r']);p.setp('root',p.p['root']+[0,max(0,.16-lowest),0]);mins.append(lowest*5/16)
  crawl.append(rig.encode(p,bone_names=names))
 motion['clips']['prone_crawl']={'duration_seconds':2,'loop':True,'frames':crawl};dest=ROOT/'run/projectseele-local-maps/eva_body_r11.json';dest.write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
 (OUT/'low_pose_manifest.json').write_text(json.dumps(dict(stances=181,crawl=61,source='R06 supported prone + recorded squat, authored alternating arm recovery',original_minimum=mins),indent=2))
 print('R11 low stance/crawl database',dest)
if __name__=='__main__':main()
