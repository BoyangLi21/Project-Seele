"""R05 deterministic retarget: actual crouch gait and a separate right cross."""
from pathlib import Path
import json,copy,hashlib
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
from scipy.spatial import ConvexHull
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/motion_review_r05';PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
rig={b['name']:b for b in load(PACK/'geo/eva_unit01.geo.json')['minecraft:geometry'][0]['bones']};P={n:np.array(b['pivot'])*[-1,1,1] for n,b in rig.items()};parents={n:b.get('parent') for n,b in rig.items()};mesh=load(PACK/'mesh/eva_unit01.mesh.json');base=load(ROOT/'src/main/resources/assets/projectseele/motion/eva_connected_locomotion_v1.json');bones=base['bones']
K={s:P['shin_'+s]+[0,11.4,0] for s in ['l','r']};E={s:np.array([(-1 if s=='l' else 1)*23.489652,123.435069,7.737214]) for s in ['l','r']}
def T(v):
 m=np.eye(4);m[:3,3]=v;return m
class Pose:
 def __init__(self):self.q={n:R.identity() for n in rig};self.p={n:np.zeros(3) for n in rig};self.cache={}
 def matrix(self,n):
  if n in self.cache:return self.cache[n]
  m=T(self.p[n])@T(P[n]);m[:3,:3]=self.q[n].as_matrix();m=m@T(-P[n]);self.cache[n]=(self.matrix(parents[n]) if parents[n] else np.eye(4))@m;return self.cache[n]
 def parent(self,n):return self.matrix(parents[n]) if parents[n] else np.eye(4)
 def point(self,n,p=None):return (self.matrix(n)@np.r_[P[n] if p is None else p,1])[:3]
 def setq(self,n,q):self.q[n]=q;self.cache.clear()
 def setp(self,n,p):self.p[n]=np.asarray(p);self.cache.clear()
 def hinge(self,n,c):delta=c-P[n];self.setp(n,delta-self.q[n].apply(delta))
 def ik(self,a,b,c,joint,target,pole,orientation=None):
  shoulder=self.point(a);va=joint-P[a];vb=P[c]-joint;la=np.linalg.norm(va);lb=np.linalg.norm(vb);d=np.asarray(target)-shoulder;length=np.linalg.norm(d);d/=max(length,1e-8);dist=np.clip(length,abs(la-lb)+.001,la+lb-.001);along=(la*la-lb*lb+dist*dist)/(2*dist);h=np.sqrt(max(0,la*la-along*along));bend=pole-d*np.dot(pole,d)
  if np.linalg.norm(bend)<1e-8:bend=np.cross(d,[1,0,0])
  bend/=np.linalg.norm(bend);elbow=shoulder+d*along+bend*h
  du=elbow-shoulder;dl=target-elbow;axis=np.cross(du,dl)
  if np.linalg.norm(axis)<1e-6:axis=np.cross(du,bend)
  axis/=np.linalg.norm(axis)
  if axis@self.parent(a)[:3,0]<0:axis*=-1
  def frame(d,side):
   y=d/np.linalg.norm(d);x=side-y*np.dot(side,y);x/=np.linalg.norm(x);return np.column_stack((x,y,np.cross(x,y)))
  def orient(n,rest,direction):
   world=R.from_matrix(frame(direction,axis)@frame(rest,np.array([1.,0,0])).T);self.setq(n,R.from_matrix(self.parent(n)[:3,:3]).inv()*world)
  orient(a,va,du);actual=(self.parent(b)@np.r_[joint,1])[:3];orient(b,vb,target-actual);self.hinge(b,joint)
  if orientation is not None:self.setq(c,R.from_matrix(self.parent(c)[:3,:3]).inv()*orientation)
  return float(np.linalg.norm(self.point(c)-target))
def arc(a,b):
 a=np.asarray(a)/np.linalg.norm(a);b=np.asarray(b)/np.linalg.norm(b);dot=np.clip(a@b,-1,1)
 if dot<-.99999:
  axis=np.cross(a,[1,0,0]);axis=axis/np.linalg.norm(axis) if np.linalg.norm(axis)>.01 else np.array([0,0,1]);return R.from_rotvec(axis*np.pi)
 q=np.r_[np.cross(a,b),1+dot];q/=np.linalg.norm(q);return R.from_quat(q)
def decode(f,bone_names=None):
 p=Pose()
 for n,q in zip(bone_names or bones,f['rotation_wxyz']):w,x,y,z=q;p.q[n]=R.from_quat([-x,-y,z,w])
 for n,v in f.get('bone_position_xyz',{}).items():p.p[n]=np.array(v)*[-1,1,1]
 p.p['root']=np.array(f['root_m'])*112*[-1,1,1];return p
def encode(p,contacts=(True,True),bone_names=None):
 qs=[]
 for n in bone_names or bones:
  x,y,z,w=p.q[n].as_quat();qs.append([w,-x,-y,z])
 return {'root_m':np.round(p.p['root']*[-1,1,1]/112,8).tolist(),'rotation_wxyz':np.round(qs,8).tolist(),'foot_contact':[bool(v) for v in contacts],'bone_position_xyz':{n:np.round(v*[-1,1,1],7).tolist() for n,v in p.p.items() if n!='root' and np.linalg.norm(v)>.00001}}
feet={}
for s in ['l','r']:
 part=mesh['parts']['foot_'+s];v=(np.array(part['vertices']).reshape(-1,mesh['stride'])[:,:3]+part['pivot'])*[-1,1,1]-P['foot_'+s];v=np.unique(v,axis=0);feet[s]=v[ConvexHull(v).vertices]
idle=decode(base['clips']['idle']['frames'][0]);idle_q={n:q for n,q in idle.q.items()}
def source(path):
 d=load(path);points={n:np.asarray(p)[:,[1,2,0]]*[-1,1,-1] for n,p in d['points'].items()};return points,d['fps']
def body(points,i,scale,progress,travel_scale=1,stationary=False,arms=False):
 p=Pose();p.q=dict(idle_q);hip=points['Hips'][i];origin=points['Hips'][0].copy();origin[1]=0;delta=points['Hips'][-1]-points['Hips'][0];delta[1]=0;origin+=delta*progress
 def source_pos(n):
  v=(points[n][i]-origin)*scale;v[[0,2]]*=travel_scale;return v
 neck=points['Neck'][i]-hip;lean=np.clip(np.arctan2(-neck[2],neck[1]),-.3,.8);across=points['LeftArm'][i]-points['RightArm'][i];yaw=np.arctan2(across[2],-across[0]);roll=0
 p.setq('root',R.identity());p.setq('torso_lower',R.from_euler('xyz',[-lean*.6,yaw*.35,roll]));p.setq('torso_upper',R.from_euler('xyz',[-lean*.4,yaw*.65,0]));p.setq('aim_pitch',R.identity());p.setq('neck',R.from_euler('x',lean*.22));p.setq('head',R.from_euler('x',lean*.78))
 ankle_ground=min(np.percentile(points[n][:,1],8) for n in ['LeftFoot','RightFoot']);desired_hip=source_pos('Hips');desired_hip[1]=(hip[1]-ankle_ground)*scale+18.56
 if not arms:desired_hip[1]-=5
 oldhip=(p.point('leg_l')+p.point('leg_r'))/2;p.setp('root',desired_hip-oldhip)
 errors=[];contacts=[]
 for s,word in [('l','Left'),('r','Right')]:
  v=points[word+'ToeBase'][i]-points[word+'Foot'][i];yawfoot=np.clip(np.arctan2(-v[0],-v[2]),-.21,.21);orient=R.from_euler('y',yawfoot);target=source_pos(word+'Foot');step_ground=min(points['LeftFoot'][i,1],points['RightFoot'][i,1]);lift=max(0,(points[word+'Foot'][i,1]-step_ground)*scale);contact=lift<1.6
  if stationary:lift=0;contact=True
  target[1]=(0 if contact else lift)-orient.apply(feet[s])[:,1].min()
  knee=source_pos(word+'Leg');pole=knee-p.point('leg_'+s)
  errors.append(p.ik('leg_'+s,'shin_'+s,'foot_'+s,K[s],target,pole,orient));contacts.append(contact)
  if arms:
   upper=points[word+'ForeArm'][i]-points[word+'Arm'][i];lower=points[word+'Hand'][i]-points[word+'ForeArm'][i];la=np.linalg.norm(E[s]-P['arm_'+s]);lb=np.linalg.norm(P['hand_'+s]-E[s]);shoulder=p.point('arm_'+s);u=upper/np.linalg.norm(upper);v=lower/np.linalg.norm(lower);target=shoulder+u*la+v*lb;orientation=arc(np.array([0,-1,0]),v)
   errors.append(p.ik('arm_'+s,'forearm_'+s,'hand_'+s,E[s],target,u));p.setq('hand_'+s,R.identity())
  else:
   pitch=.10*np.sin(progress*2*np.pi+(0 if s=='l' else np.pi));p.setq('arm_'+s,R.from_euler('xyz',[.32+pitch,0,(-.14 if s=='l' else .14)]));p.setq('forearm_'+s,R.from_euler('x',.95))
 return p,contacts,max(errors)
def main():
 crouch,fps=source(OUT/'mco_crouch_source.json');leg=sum(np.median(np.linalg.norm(crouch[a]-crouch[b],axis=1)) for a,b in [('LeftUpLeg','LeftLeg'),('LeftLeg','LeftFoot')]);scale=(np.linalg.norm(K['l']-P['leg_l'])+np.linalg.norm(P['foot_l']-K['l']))/leg
 n=len(crouch['Hips']);travel=np.linalg.norm((crouch['Hips'][-1]-crouch['Hips'][0])[[0,2]])*scale*5/16;travel_scale=15/travel;frames=[];err=[]
 for i in range(n):
  p,c,e=body(crouch,i,scale,i/(n-1),travel_scale);frames.append(encode(p,c));err.append(e)
 frames[-1]=copy.deepcopy(frames[0]);new=copy.deepcopy(base);new['clips']['crouch_walk']={'duration_seconds':(n-1)/fps,'loop':True,'root_travel_m':[0,0,15/35],'frames':frames}
 # A symmetric, two-foot support stance at the captured average pelvis height.
 still={k:np.repeat(np.mean(v,axis=0)[None,:],2,axis=0) for k,v in crouch.items()};still['Hips'][:,[0,2]]=0
 for k in still:
  if k!='Hips':still[k][:,[0,2]]-=np.mean(crouch['Hips'],axis=0)[[0,2]]
 for k in ['LeftFoot','RightFoot']:still[k][:,1]=min(np.percentile(crouch[k][:,1],8),still[k][0,1])
 low,_,e=body(still,0,scale,0,travel_scale,True);lowframe=encode(low);new['clips']['crouch_idle']={'duration_seconds':2,'loop':True,'root_travel_m':[0,0,0],'frames':[lowframe,lowframe]}
 # Interpolate the pose with independent grounded ankle targets through both directions.
 for name,reverse in [('stand_to_crouch',False),('crouch_to_stand',True)]:
  fs=[]
  for i in range(49):
   t=i/48;t=t*t*(3-2*t);t=1-t if reverse else t;p=Pose()
   for b in rig:p.q[b]=Slerp([0,1],R.concatenate([idle.q[b],low.q[b]]))([t])[0];p.p[b]=(1-t)*idle.p[b]+t*low.p[b]
   for s in ['l','r']:
    a=idle.point('foot_'+s);b=low.point('foot_'+s);target=(1-t)*a+t*b;orientation=R.from_matrix(idle.matrix('foot_'+s)[:3,:3]);orientation=Slerp([0,1],R.concatenate([orientation,R.from_matrix(low.matrix('foot_'+s)[:3,:3])]))([t])[0];target[1]=-orientation.apply(feet[s])[:,1].min();p.ik('leg_'+s,'shin_'+s,'foot_'+s,K[s],target,np.array([0,0,-1.]),orientation)
   fs.append(encode(p))
  new['clips'][name]={'duration_seconds':.8,'loop':False,'root_travel_m':[0,0,0],'frames':fs}
 new['provenance']={'source':'MoCap Online Demo MOB1_CrouchWalk_F; private local retarget','source_hash':hashlib.sha256((OUT/'mco_crouch_source.json').read_bytes()).hexdigest(),'stride_blocks':15,'joint_correction':'Measured knee articulation +11.4 model units; ankle soles grounded'}
 dest=PACK/'motion/eva_connected_locomotion_r05.json';dest.write_text(json.dumps(new,separators=(',',':')),encoding='utf-8')
 (OUT/'crouch_preview.json').write_text(json.dumps({'schema':2,'bones':bones,'clips':{k:v for k,v in new['clips'].items() if 'crouch' in k}},separators=(',',':')),encoding='utf-8')
 print('CROUCH',n,'scale',scale,'stride',15,'max IK',max(err),'static',e)
 # Different, complete heavy attack. Do not reuse the rejected Group-C recovery segment.
 points,fps=source(OUT/'Male2_E4_CrossRight.json');maxf=int(np.argmax(-(points['RightHand'][:,2]-points['Hips'][:,2])));start=max(0,maxf-13);end=min(len(points['Hips'])-1,maxf+30);points={k:v[start:end+1] for k,v in points.items()};leg=sum(np.median(np.linalg.norm(points[a]-points[b],axis=1)) for a,b in [('LeftUpLeg','LeftLeg'),('LeftLeg','LeftFoot')]);scale=(np.linalg.norm(K['l']-P['leg_l'])+np.linalg.norm(P['foot_l']-K['l']))/leg;fs=[];contact=[]
 heavy_bones=list(dict.fromkeys(bones+['wrist_l','wrist_r']+[n for n in rig if n.startswith('finger_thumb')]))
 closed=load(PACK/'animations/eva_unit01.animation.json')['animations']['animation.eva_unit01.smash']['bones']
 for i in range(len(points['Hips'])):
  p,c,e=body(points,i,scale,i/(len(points['Hips'])-1),1,False,True)
  # Axis helpers are inverse-bind frames of the generated digits. Erasing
  # them makes an otherwise closed fist splay through the palm.
  for b in heavy_bones:
   if '_axis_' in b:p.setq(b,R.from_euler('xyz',np.array(rig[b].get('rotation',[0,0,0]))*[-1,-1,1],degrees=True))
   elif b.startswith('finger_') and b in closed:
    values=closed[b].get('rotation',[0,0,0]);values=values[min(values,key=float)] if isinstance(values,dict) else values
    p.setq(b,R.from_euler('xyz',np.array(values)*[-1,-1,1],degrees=True))
  fs.append(encode(p,c,heavy_bones));contact.append((p.point('hand_r',P['finger_middle_r'])*[-5/16,5/16,-5/16]).tolist())
 original=fs;fs=[];contact=[];impact=(maxf-start)/(end-start)
 for i in range(73):
  t=i/72;phase=t*impact/.45 if t<=.45 else impact+(t-.45)*(1-impact)/.55;f=phase*(len(original)-1);a=int(f);b=min(a+1,len(original)-1);p=decode(original[a],heavy_bones);other=decode(original[b],heavy_bones)
  for n in rig:p.q[n]=Slerp([0,1],R.concatenate([p.q[n],other.q[n]]))([f-a])[0];p.p[n]=(1-f+a)*p.p[n]+(f-a)*other.p[n]
  fs.append(encode(p,bone_names=heavy_bones));contact.append((p.point('hand_r',P['finger_middle_r'])*[-5/16,5/16,-5/16]).tolist())
 # Align the performer to the pilot's forward axis at contact. Keep the
 # entire performance (including feet) in that one rotated reference frame.
 def hand_without_travel(frame):
  p=decode(frame,heavy_bones);p.setp('root',[0,p.p['root'][1],0]);return p.point('hand_r',P['finger_middle_r'])*[-5/16,5/16,-5/16]
 at=.45*(len(fs)-1);i=int(at);impact_point=(1-at+i)*hand_without_travel(fs[i])+(at-i)*hand_without_travel(fs[i+1]);alignment=-np.arctan2(impact_point[0],impact_point[2]);turn=R.from_euler('y',alignment);aligned=[];contact=[]
 for frame in fs:
  p=decode(frame,heavy_bones);p.setq('root',turn*p.q['root']);p.setp('root',turn.apply(p.p['root']));aligned.append(encode(p,bone_names=heavy_bones));contact.append(hand_without_travel(aligned[-1]).tolist())
 fs=aligned
 heavy={'schema':2,'sample_rate':60,'quaternion_order':'wxyz','bones':heavy_bones,'clips':{'heavy_right_cross':{'duration_seconds':1.2,'loop':False,'contact_phase':.45,'frames':fs}},'provenance':{'source':'ACCAD Male2 E4 CrossRight','trim':[start,end],'pilot_forward_alignment_degrees':float(np.degrees(alignment)),'contact_space':'entity relative, excludes physics-owned root X/Z','license':'CC BY 3.0; ACCAD / Ohio State University'}}
 heavy['provenance'].update(source_url='https://accad.osu.edu/research/motion-lab/mocap-system-and-data',license_url='https://creativecommons.org/licenses/by/3.0/',source_sha256=hashlib.sha256((OUT/'Male2_E4_CrossRight.json').read_bytes()).hexdigest(),changes='Trim, EVA limb proportions and foot constraints, measured elbow hinge, articulated fist, 1.2-second time mapping')
 (ROOT/'src/main/resources/assets/projectseele/motion/eva_heavy_right_cross_r05.json').write_text(json.dumps(heavy,separators=(',',':')),encoding='utf-8');(OUT/'heavy_contacts.json').write_text(json.dumps(contact),encoding='utf-8');(ROOT/'src/main/resources/assets/projectseele/motion/eva_heavy_contact_r05.json').write_text(json.dumps({'schema':1,'contact_phase':.45,'points_blocks':contact}),encoding='utf-8');print('HEAVY',len(fs),'contact',.45)
 # Shared server/client pose data; third-party crouch data remains local.
 support={}
 for name in ['torso_lower','torso_upper','head','leg_l','leg_r','shin_l','shin_r','foot_l','foot_r']:
  part=mesh['parts'].get(name)
  if not part:continue
  v=(np.array(part['vertices']).reshape(-1,mesh['stride'])[:,:3]+part['pivot'])*[-1,1,1];v=np.unique(v,axis=0);support[name]=v[ConvexHull(v).vertices].tolist()
 local={'motion':new,'rig':list(rig.values()),'support':support,'rifle_mocap':load(PACK/'motion/rifle_mocap_r04.json'),'prone':load(PACK/'animations/eva_unit01.animation.json')['animations']['animation.eva_unit01.prone']['bones'],'grip':load(PACK/'animations/eva_unit01.animation.json')['animations']['animation.eva_unit01.rifle_aim']['bones']}
 local['rigs']={str(v):load(PACK/f'geo/eva_unit0{v}.geo.json')['minecraft:geometry'][0]['bones'] for v in range(3)}
 (ROOT/'run/projectseele-local-maps/eva_body_r05.json').write_text(json.dumps(local,separators=(',',':')),encoding='utf-8')
if __name__=='__main__':main()
