"""Widen the measured EVA crouch support without replacing its mocap timing."""
from pathlib import Path
import copy,json,hashlib
import numpy as np
from scipy.spatial.transform import Rotation as R
import build_eva_body_r05 as rig
ROOT=rig.ROOT;OUT=ROOT/'artifacts/facility_r25/crouch';SOURCE=ROOT/'run/projectseele-local-maps/eva_body_r11.json'
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
def main():
 OUT.mkdir(parents=True,exist_ok=True);data=json.loads(SOURCE.read_text());motion=data['motion'];names=motion['bones'];report=[]
 for key in ('crouch_walk','unarmed_stance'):
  clip=motion['clips'][key];frames=[]
  for i,frame in enumerate(clip['frames']):
   level=i/(len(clip['frames'])-1)*3 if key=='unarmed_stance' else 1
   weight=float(smooth(level/.8)*(1-smooth((level-1)/.4)))
   if weight<1e-8:frames.append(frame);continue
   pose=rig.decode(frame,names);centre=(pose.point('leg_l')[0]+pose.point('leg_r')[0])/2;errors=[];positions={}
   for side,sign in [('l',-1),('r',1)]:
    old=pose.point('foot_'+side);target=old.copy();spread=centre+sign*13.0
    target[0]=old[0]*(1-weight)+(min(old[0],spread) if sign<0 else max(old[0],spread))*weight
    orientation=R.from_matrix(pose.matrix('foot_'+side)[:3,:3])
    error=rig.Pose.ik(pose,'leg_'+side,'shin_'+side,'foot_'+side,rig.K[side],target,np.array([sign*.18,-.05,-1.]),orientation)
    errors.append(error);positions[side]=dict(before=(old*5/16).tolist(),after=(pose.point('foot_'+side)*5/16).tolist())
   updated=copy.deepcopy(frame);updated.update(rig.encode(pose,frame.get('foot_contact',(True,True)),names));frames.append(updated)
   report.append(dict(clip=key,frame=i,blend=weight,foot_error_blocks=max(errors)*5/16,feet=positions))
  clip['frames']=frames
 data['r25_support_revision']={'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'description':'Keep timing/root and foot Y/Z; minimum crouch support half-width 13 model units; preserve static rifle kneel and prone clips'}
 target=OUT/'eva_body_r25.json';target.write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
 maxerr=max(q['foot_error_blocks'] for q in report);assert maxerr<.025,maxerr
 (OUT/'support_report.json').write_text(json.dumps(dict(source=str(SOURCE),target=str(target),changed_samples=len(report),max_ik_error_blocks=maxerr,samples=report),indent=2),encoding='utf8')
 print('Crouch support candidate',len(report),'samples; maximum IK error',maxerr)
if __name__=='__main__':main()
