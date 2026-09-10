"""Rigid-limb contact rewrite of the final clinch; no mantle or vertex morph."""
import json,hashlib,shutil,argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
import author_first_battle_r12 as a
import finalize_first_battle_r12 as f
from preview_first_battle_r12 import angel_pose
b=a.b;eva=a.eva;U=a.UNIT;OUT=b.ROOT/'artifacts/staff_world_r15';START=482;END=558
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--install',action='store_true');args=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
 if args.install:
  src=OUT/'first_battle_r15.json';report=json.loads((OUT/'clinch_validation.json').read_text());assert report['passed'] and report['sha256']==hashlib.sha256(src.read_bytes()).hexdigest()
  target=b.ROOT/'run/projectseele-local-maps/first_battle_r15.json';temp=target.with_suffix('.tmp');shutil.copy2(src,temp);temp.replace(target);print('Verified R15 clinch installed');return
 d=json.loads((b.ROOT/'run/projectseele-local-maps/first_battle_r14.json').read_text());d.pop('surface_deformation_r14',None)
 heroes=[eva.decode(x,d['eva']['bones']) for x in d['eva']['frames']];angels=[angel_pose(x,d['angel']['bones']) for x in d['angel']['frames']];start=a.clone(angels[START],True);ar0=np.array(d['angel']['root_blocks'][START]);hip0=b.angel_world(start,ar0,'torso_lower');records=[];bends={}
 hstart=a.clone(heroes[START-1]);hend=a.clone(heroes[END])
 for i in range(START,END+1):
  t=i/30;hero=heroes[i];hr=np.array(d['eva']['root_blocks'][i]);weight=b.smooth((t-16.12)/.85);contact=b.smooth((t-17.65)/.75)
  for n in hero.q:
   if n.startswith(('arm_','forearm_','hand_','wrist_','finger_')):hero.setq(n,b.qmix(hstart.q[n],hend.q[n],b.smooth((t-START/30)/1.1)))
  standing,_,_=a.take('grab_b',170+(t-16.3)*35,True)
  standing.setq('root',R.from_euler('x',-.08))
  standing.setq('torso_upper',R.from_rotvec(standing.q['torso_upper'].as_rotvec()*.4))
  strides={'l':b.smooth((t-16.95)/.5),'r':b.smooth((t-17.2)/.45)}
  stride_gap=abs(strides['l']-strides['r']);rear=20+34*(1-(strides['l']+strides['r'])/2)
  pose=a.mix_pose(start,standing,weight,True);targetHip=hr+[7,24-7*stride_gap,rear];hip=b.mix(hip0,targetHip,b.smooth((t-16.1)/.85));hip[2]=b.mix(hip0[2],targetHip[2],b.smooth((t-START/30)/.43));ar=hip-pose.point('torso_lower')*U
  ease=b.smooth((t-START/30)/.23)
  for side,sign in [('l',-1),('r',1)]:
   q0=R.from_matrix(start.matrix('foot_'+side)[:3,:3]);q=b.qmix(q0,R.identity(),weight);feet=a.actors['grab_b',True].feet[side]
   stride=strides[side];goal=hr+[7+sign*5.5,-np.min(q.apply(feet)[:,1])*U+3*np.sin(np.pi*stride),20+34*(1-stride)];old=b.angel_world(start,ar0,'foot_'+side);plant=b.smooth((t-16.08)/.85);goal=b.mix(old,goal,plant);goal[0]+=sign*20*np.sin(np.pi*plant)*(1-.5*b.smooth((plant-.3)/.3))
   pole=b.mix([sign,0,0],[sign*.2,0,-1],plant)
   direction=a.retarget.unit((goal-ar)/U-pose.point('leg_'+side));bend=a.retarget.unit(pole-direction*np.dot(pole,direction),(sign,0,0))
   if side not in bends:
    old=pose.point('shin_'+side)-pose.point('leg_'+side);bends[side]=a.retarget.unit(old-direction*np.dot(old,direction),(sign,0,0))
   previous=a.retarget.unit(bends[side]-direction*np.dot(bends[side],direction),(sign,0,0));arc=eva.arc(previous,bend).as_rotvec();angle=np.linalg.norm(arc)
   if angle>np.radians(14):bend=R.from_rotvec(arc*np.radians(14)/angle).apply(previous)
   pole=bends[side]=bend
   names=['leg_'+side,'shin_'+side,'foot_'+side];before={n:pose.q[n] for n in names}
   a.retarget.solve_ik(pose,'leg_'+side,'shin_'+side,'foot_'+side,b.ANGEL.P['shin_'+side],(goal-ar)/U,pole,q)
   for n in names:pose.setq(n,b.qmix(before[n],pose.q[n],ease))
  # Opposite-facing partners: Sachiel's left arm grips EVA's right upper arm.
  for side,other,sign in [('l','r',-1),('r','l',1)]:
   shoulder=b.hero_world(hero,hr,'arm_'+other);target=shoulder+[sign*6.5,-10,1]
   q=b.qmix(R.from_matrix(pose.matrix('hand_'+side)[:3,:3]),R.from_euler('xyz',[-1.55,0,0]),b.smooth((t-START/30)/.55));tip=np.array([0,-2,-17.])
   opened=pose.point('arm_'+side)+np.array([sign*10,-10,-8])/U
   current=b.mix(pose.point('hand_'+side),opened,b.smooth((t-START/30)/.55));goal=(target-ar)/U-q.apply(tip);goal=b.mix(current,goal,contact)
   names=['arm_'+side,'forearm_'+side,'hand_'+side];before={n:pose.q[n] for n in names}
   error=a.retarget.solve_ik(pose,'arm_'+side,'forearm_'+side,'hand_'+side,b.ANGEL.P['forearm_'+side],goal,np.array([sign*.7,-1,-.1]),q)*U
   for n in names:pose.setq(n,b.qmix(before[n],pose.q[n],ease))
   records.append(dict(t=t,side=side,reach_error=float(error)))
  low=pose.skin()[:,1].min()*U+ar[1]
  if low<0:ar[1]-=low
  angels[i]=pose;d['angel']['root_blocks'][i]=ar.round(6).tolist()
 # The folded ankle chain is airborne during the recoil. Remove the IK twist
 # spike there before the two explicit planted lunge steps begin.
 segment=[a.clone(q,True) for q in angels[478:526]];limbs=[n+'_'+s for s in ['l','r'] for n in ['leg','shin','foot']]
 f.smooth_rotations(segment,limbs)
 for i in range(START,526):
  weight=b.smooth((i-START)/3)*(1-b.smooth((i-522)/3))
  for name in limbs:angels[i].setq(name,b.qmix(angels[i].q[name],segment[i-478].q[name],weight))
  ar=np.array(d['angel']['root_blocks'][i]);low=angels[i].skin()[:,1].min()*U+ar[1]
  if low<0:ar[1]-=low;d['angel']['root_blocks'][i]=ar.tolist()
 # Rotational interpolation can dip a sole between two clear keyframes.
 lift=np.zeros(END-START+1)
 for i in range(START,END):
  for w in [.25,.5,.75]:
   middle=a.mix_pose(angels[i],angels[i+1],w,True);root=b.mix(d['angel']['root_blocks'][i],d['angel']['root_blocks'][i+1],w);need=max(0,.02-(middle.skin()[:,1].min()*U+root[1]))
   lift[i-START]=max(lift[i-START],need);lift[i-START+1]=max(lift[i-START+1],need)
 from scipy.ndimage import maximum_filter1d
 lift=maximum_filter1d(lift,size=3)
 for i in range(START,END+1):d['angel']['root_blocks'][i][1]+=float(lift[i-START])
 for i in range(END+1,691):
  angels[i]=a.clone(angels[END],True);d['angel']['root_blocks'][i]=d['angel']['root_blocks'][END]
 cameras=json.loads(json.dumps(d['camera']));f.recompute(d,heroes,angels);d['camera']=cameras
 for i in range(START,END+1):
  t=i/30;weight=b.smooth((t-START/30)/.38);hr=np.array(d['eva']['root_blocks'][i]);ar=np.array(d['angel']['root_blocks'][i]);centre=(b.hero_world(heroes[i],hr,'torso_upper')+b.angel_world(angels[i],ar,'torso_upper'))/2
  eye=b.curve([(START/30,[95,62,82]),(17.2,[90,62,90]),(18.6,[72,52,89])],t)
  d['camera']['position'][i]=b.mix(cameras['position'][i],eye,weight).tolist();d['camera']['target'][i]=b.mix(cameras['target'][i],centre,weight).tolist()
 for i in range(END+1,583):
  for key in ['position','target']:d['camera'][key][i]=b.mix(d['camera'][key][END],d['camera'][key][i],b.smooth((i-END)/(583-END))).tolist()
 d['reference']='R15 anatomical clinch: capture-led recoil, planted two-step approach, then upper-arm restraint. Authored adaptation; the distorted vertex-morph mantle is retired.'
 p=OUT/'first_battle_r15.json';p.write_text(json.dumps(d,separators=(',',':')),encoding='utf8');(OUT/'clinch_audit.json').write_text(json.dumps(dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),contacts=records),indent=2));print('R15 clinch authored; visual and triangle review required',flush=True)
if __name__=='__main__':main()
