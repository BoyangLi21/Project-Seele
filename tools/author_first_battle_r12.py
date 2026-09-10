"""Full-body capture-led remake of the approved 23-second event sequence.

Capture remains the body prior. Only support and actual interacting surfaces
receive IK constraints; no source material is placed in public assets here.
"""
from pathlib import Path
from functools import lru_cache
import json,math
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
import retarget_human_r12 as retarget
import author_eva_rifle_stances_r06 as surface

b=retarget.battle;eva=retarget.eva;ROOT=eva.ROOT;OUT=ROOT/'artifacts/first_battle_refinement_r12';UNIT=5/16;MIRROR=b.HEROMIRROR;FPS=30;DURATION=23
b.stable_ik=retarget.solve_ik
HERO_NAMES=[n for n in eva.rig if not n.startswith('dorsal_')]
humans={name:retarget.Human(OUT/'sources'/(name+'.npz')) for name in ['heavy_push','heavy_pull','pull_a','resist_b','grab_a','grab_b','punch2','kick','frontkick','jump','fall','downstrike','land','pushed']}
actors={(name,angel):retarget.Retarget(h,angel) for name,h in humans.items() for angel in [False,True]}
evidence=[];hand_bends={};hand_previous={};GROUND_LEAN=-.7;GROUND_ROOT=np.array([0.,0,52.]);BRACE_INDEX=0;GRIP_INDEX=0;KICK_INDEX=0;KICK_TIP=b.SOLE['r'].copy()
_old=json.loads((OUT/'baseline_r10.json').read_text());_field=eva.decode(_old['eva']['frames'][72],_old['eva']['bones']);FIELD_HAND_Q={s:R.from_matrix(_field.matrix('hand_'+s)[:3,:3]) for s in ['l','r']}
def clone(p,angel=False):
 q=b.ANGEL.pose() if angel else eva.Pose();q.q=dict(p.q);q.p={n:v.copy() for n,v in p.p.items()};return q
def mix_pose(a,c,w,angel=False):
 p=clone(a,angel);w=float(np.clip(w,0,1))
 for n in p.q:p.setq(n,b.qmix(a.q[n],c.q[n],w));p.setp(n,b.mix(a.p[n],c.p[n],w))
 return p
@lru_cache(maxsize=4096)
def source(name,frame,angel=False,support='feet'):
 p,delta,meta=actors[name,angel].pose(frame,support=support);return p,delta,meta
def take(name,frame,angel=False,support='feet'):
 p,r,m=source(name,round(float(frame),6),angel,support);return clone(p,angel),r.copy(),m
def window(t,a,z,f0,f1):return float(np.interp(t,[a,z],[f0,f1]))
def map_keys(t,keys):return float(np.interp(t,[x[0] for x in keys],[x[1] for x in keys]))
def root_hero(t):
 p=b.curve([(0,[0,0,0]),(1.2,[0,0,3]),(3,[0,0,3]),(5.1,[0,0,5]),(6.3,[-10,0,19]),(8.3,[-10,0,19]),(9.7,[0,0,17]),(10,[0,0,17]),(11.7,[0,0,52]),(19.4,[0,0,52]),(21.6,[0,0,59]),(23,[0,0,59])],t)
 if 10<=t<11.7:p=b.mix(np.array([0.,0,17.]),GROUND_ROOT,(t-10)/1.7)
 if 11.7<=t<19.4:p=GROUND_ROOT.copy()
 if t>=19.4:p+=GROUND_ROOT-[0,0,52]
 return p
def root_angel(t):return b.curve([(0,[0,0,34]),(9.2,[0,0,34]),(10.7,[0,0,55]),(23,[0,0,55])],t)

def pound_pose(frame,lean=None):
 base,_,_=take('downstrike',0,False,'body');strike,_,meta=take('punch2',frame);reference,_,_=source('punch2',35);lean=GROUND_LEAN if lean is None else lean
 knee='l' if base.point('leg_l',eva.K['l'])[1]<base.point('leg_r',eva.K['r'])[1] else 'r';anchor=base.point('leg_'+knee,eva.K[knee]);delta=strike.q['root']*reference.q['root'].inv();base.setq('root',R.from_rotvec(delta.as_rotvec()*.45)*base.q['root']);base.setp('root',base.p['root']+anchor-base.point('leg_'+knee,eva.K[knee]))
 base.setq('torso_upper',R.from_euler('x',lean)*strike.q['torso_upper'])
 for n in HERO_NAMES:
  if n.startswith(('arm_','forearm_','hand_','wrist_','finger_')) or n in ['head','neck']:
   base.setq(n,strike.q[n]);base.setp(n,strike.p[n])
 shoulder=base.point('arm_r');hand=base.point('hand_r');direction=hand-shoulder;length=np.linalg.norm(direction);reach=(np.linalg.norm(eva.E['r']-eva.P['arm_r'])+np.linalg.norm(eva.P['hand_r']-eva.E['r']))*.78
 if length>reach:
  target=shoulder+direction*(reach/length);q=R.from_matrix(base.matrix('hand_r')[:3,:3]);pole=base.point('arm_r',eva.E['r'])-shoulder;retarget.solve_ik(base,'arm_r','forearm_r','hand_r',eva.E['r'],target,pole,q)
 low=surface.floor(base,['torso_lower','leg_l','leg_r','shin_l','shin_r','foot_l','foot_r']);base.setp('root',base.p['root']+[0,-low,0]);return base,dict(meta,kneel=True)

def hero_prior(t):
 if t<1.2:
  p,r,m=take('punch2',window(t,0,1.2,2,18));p=mix_pose(eva.idle,p,b.smooth(t/.6));return p,m
 if t<5.35:
  p,r,m=take('pull_a',window(t,1.2,5.35,90,400));old,_,_=take('punch2',18);return mix_pose(old,p,b.smooth((t-1.2)/.65)),m
 if t<8.5:
  p,r,m=take('grab_a',window(t,5.35,8.5,115,305));old,_,_=take('pull_a',400);return mix_pose(old,p,b.smooth((t-5.35)/.65)),m
 if t<10:
  frame=map_keys(t,[(8.5,0),(9.2,26),(10,54)]);p,r,m=take('frontkick',frame);old,_,_=take('grab_a',305);return mix_pose(old,p,b.smooth((t-8.5)/.4)),m
 if t<11.7:
  p,r,m=take('jump',window(t,10,11.7,0,29),False,'air');old,_,_=take('frontkick',54);return mix_pose(old,p,b.smooth((t-10)/.25)),dict(m,air=True)
 if t<16.8:
  # Recorded strong crosses drive the upper-body motion; recorded kneeling
  # supplies the support base. Source time always moves forward.
  frame=map_keys(t,[(11.7,25),(12.75,53),(13.4,84),(14.15,105),(15.2,132),(16.05,154),(16.8,174)]);p,m=pound_pose(frame);old,_,_=take('jump',29,False,'air');return mix_pose(old,p,b.smooth((t-11.7)/.32)),m
 if t<19.4:
  p,m=pound_pose(174);stand,_,_=take('punch2',2);return mix_pose(p,stand,b.smooth((t-16.8)/1.1)),dict(m,kneel=t<17.6)
 p,r,m=take('land',window(t,19.4,21.6,10,52));old,_,_=take('punch2',2);p=mix_pose(old,p,b.smooth((t-19.4)/.28));return mix_pose(p,eva.idle,b.smooth((t-21.6)/1.4)),m

def ground_angel_body(p):
 body_ids=[b.ANGEL.names.index(n) for n in ['torso_lower','torso_upper','head','neck','leg_l','leg_r','shin_l','shin_r','foot_l','foot_r']];mask=np.sum(np.where(np.isin(b.ANGEL.ids,body_ids),b.ANGEL.weights,0),axis=1)>.65
 p.setp('root',p.p['root']+[0,-p.skin()[mask,1].min(),0])
 for side in ['l','r']:
  arm_ids=[b.ANGEL.names.index(n+'_'+side) for n in ['arm','forearm','hand']];hand_mask=np.sum(np.where(np.isin(b.ANGEL.ids,arm_ids),b.ANGEL.weights,0),axis=1)>.6
  for _ in range(3):
   minimum=p.skin()[hand_mask,1].min()
   if minimum>=0:break
   target=p.point('hand_'+side)+[0,-minimum*.55+.03,0];q=R.from_matrix(p.matrix('hand_'+side)[:3,:3]);pole=np.array([0,1.,0]);retarget.solve_ik(p,'arm_'+side,'forearm_'+side,'hand_'+side,b.ANGEL.P['forearm_'+side],target,pole,q)
 p.ground()
 return p

def angel_prior(t):
 if t<5.35:
  p,r,m=take('grab_b',window(t,0,5.35,40,120),True);return p,m
 if t<8.5:
  p,r,m=take('grab_b',window(t,5.35,8.5,115,305),True);old,_,_=take('grab_b',120,True);return mix_pose(old,p,b.smooth((t-5.35)/.4),True),m
 if t<9.2:
  p,r,m=take('pushed',window(t,8.5,9.2,0,12),True);old,_,_=take('grab_b',305,True);return mix_pose(old,p,b.smooth((t-8.5)/.4),True),m
 if t<16.8:
  frame=map_keys(t,[(9.2,0),(10.7,48),(11.7,110),(12.1,119),(16.8,119)]);p,r,m=take('fall',frame,True,'fall');old,_,_=take('pushed',12,True);p=mix_pose(old,p,b.smooth((t-9.2)/.2),True)
  # The recorded fall rolls onto a side; settle the visible core upward for
  # the TV sequence before the pin, rotating about the pelvis rather than teleporting it.
  # Retain the actor's slightly rolled back rather than rotating the whole
  # body to force the chest normal upward (which lifts both long legs).
  impact=sum(math.exp(-((t-at)/.13)**2) for at in [12.75,14.15,16.05]);p.setq('torso_upper',p.q['torso_upper']*R.from_euler('xyz',[.055*impact,.025*impact,0]));p=ground_angel_body(p);return p,m
 # The creature's enclosing/self-destruction motion is an authored nonhuman
 # adaptation, explicitly separated from the captured human acting.
 old,_=angel_prior(16.799);target,root=b.make_angel(18.6);weight=b.smooth((t-16.8)/1.8);root+=GROUND_ROOT-[0,0,52];root=b.mix(root_angel(16.8),root,weight);p=mix_pose(old,target,weight,True);return p,dict(authored_wrap=True,root=root)

class Feet:
 def __init__(self,angel=False):self.angel=angel;self.anchors={};self.previous={};self.bends={};self.weights={}
 def apply(self,p,root,meta,enabled=True):
  if not enabled:self.anchors.clear();self.bends.clear();self.previous.clear();self.weights.clear();return
  P=b.ANGEL.P if self.angel else eva.P;mirror=np.ones(3) if self.angel else MIRROR
  goals={}
  for s in ['l','r']:
   contact=meta.get('contacts',{}).get(s,True);current=root+p.point('foot_'+s)*mirror*UNIT;orientation=R.from_matrix(p.matrix('foot_'+s)[:3,:3]);verts=actors['grab_b',True].feet[s] if self.angel else eva.feet[s]
   previous=self.previous.get(s,current);speed=np.linalg.norm((current-previous)[[0,2]]);self.previous[s]=current.copy()
   if s not in self.anchors:self.anchors[s]=current.copy()
   drift=np.linalg.norm((self.anchors[s]-current)[[0,2]])
   desired=float(contact)*np.clip(1-speed/.7,0,1)*np.clip((4-drift)/2,0,1)
   self.weights[s]=self.weights.get(s,0)+(desired-self.weights.get(s,0))*.28
   if self.weights[s]<.04:self.anchors[s]=current.copy()
   goal=b.mix(current,self.anchors[s],self.weights[s]);target=(goal-root)*mirror/UNIT
   floor=-root[1]/UNIT-orientation.apply(verts)[:,1].min()
   target[1]=max(target[1],floor)
   hip=p.point('leg_'+s);joint=P['shin_'+s] if self.angel else eva.K[s];length=np.linalg.norm(joint-P['leg_'+s])+np.linalg.norm(P['foot_'+s]-joint);horizontal=np.linalg.norm((target-hip)[[0,2]])
   # A scene alignment must never drag the hips toward a stale foot anchor.
   # Release the small XZ correction continuously as reach is exhausted.
   distance=np.linalg.norm(target-hip)
   if distance>length-.08:
    alpha=np.clip((length-.08-np.linalg.norm((current-root)*mirror/UNIT-hip))/max(1e-5,distance-np.linalg.norm((current-root)*mirror/UNIT-hip)),0,1);target=b.mix((current-root)*mirror/UNIT,target,alpha)
   goals[s]=(target,orientation,joint)
  for s,(target,q,joint) in goals.items():
   pole=p.point('leg_'+s,joint)-p.point('leg_'+s)
   direction=retarget.unit(target-p.point('leg_'+s));bend=retarget.unit(pole-direction*np.dot(pole,direction),(0,0,-1))
   if s in self.bends:
    previous=retarget.unit(self.bends[s]-direction*np.dot(self.bends[s],direction),(0,0,-1));arc=eva.arc(previous,bend).as_rotvec();angle=np.linalg.norm(arc)
    if angle>math.radians(18):bend=R.from_rotvec(arc*math.radians(18)/angle).apply(previous)
   self.bends[s]=bend;pole=bend
   if self.angel:error=retarget.solve_ik(p,'leg_'+s,'shin_'+s,'foot_'+s,joint,target,pole,q)*UNIT
   else:error=b.stable_ik(p,'leg_'+s,'shin_'+s,'foot_'+s,joint,target,pole,q)*UNIT
   evidence.append(dict(kind='foot_'+('angel_' if self.angel else 'eva_')+s,error=float(error)))

def constrain_hands(t,p,root,a,aroot):
 for side,sign in [('l',1),('r',-1)]:
  current=b.hero_world(p,root,'hand_'+side,eva.P['finger_middle_'+side]);target=current.copy();q=R.from_matrix(p.matrix('hand_'+side)[:3,:3]);weight=0;curl=1
  if .35<t<5.5:
   tear=b.smooth((t-3)/2);target=np.array([sign*(7+5*tear),40-2*tear,21.]);weight=b.smooth((t-.35)/.8)*(1-b.smooth((t-5.1)/.4));q=b.qmix(q,FIELD_HAND_Q[side],weight);curl=.35
  if 5.5<=t<8.5 and side=='r':
   target=a.skin()[GRIP_INDEX]*UNIT+aroot;target+=retarget.unit(root+[0,44,0]-target)*.08;weight=b.smooth((t-5.5)/.7)*(1-b.smooth((t-8.1)/.4));curl=.6
  if 11.68<t<16.9:
   core=b.angel_world(a,aroot,'torso_upper',b.ANGEL.core)
   if side=='l':target=a.skin()[BRACE_INDEX]*UNIT+aroot;target+=retarget.unit(root+[0,32,0]-target)*.3;weight=b.smooth((t-11.68)/.42);curl=.4
   elif t>=11.7:
    impacts=[]
    for at,frame in [(12.75,53),(14.15,105),(16.05,154)]:
     reference,_=pound_pose(frame);impacts.append((at,b.hero_world(reference,np.zeros(3),'hand_r',eva.P['finger_middle_r'])))
    impact=b.curve(impacts,t)
    # Warp the complete captured strike trajectory to the core. A narrow
    # correction pulse at contact would teleport the forearm through recovery.
    target=core+(current-root-impact)+[0,6*b.smooth((t-15.35)/.35) if t>15.35 else .45,0];weight=b.smooth((t-11.7)/.25);curl=1
   weight*=1-b.smooth((t-16.55)/.35)
  if weight>1e-4:
   wanted=b.mix(current,target,weight);tip=eva.P['finger_middle_'+side]-eva.P['hand_'+side];local=(wanted-root)*MIRROR/UNIT-q.apply(tip);shoulder=p.point('arm_'+side);direction=retarget.unit(local-shoulder);pole=p.point('arm_'+side,eva.E[side])-shoulder;bend=retarget.unit(pole-direction*np.dot(pole,direction),(1,0,0))
   if side in hand_bends:
    previous=retarget.unit(hand_bends[side]-direction*np.dot(hand_bends[side],direction),(1,0,0));arc=eva.arc(previous,bend).as_rotvec();angle=np.linalg.norm(arc)
    if angle>math.radians(18):bend=R.from_rotvec(arc*math.radians(18)/angle).apply(previous)
   hand_bends[side]=bend
   for name in ['arm_'+side,'forearm_'+side]:
    current_q=R.from_matrix(p.matrix(name)[:3,:3])
    if name in hand_previous:current_q=b.qmix(hand_previous[name],current_q,.6);p.setq(name,R.from_matrix(p.parent(name)[:3,:3]).inv()*current_q)
   error=retarget.solve_ik(p,'arm_'+side,'forearm_'+side,'hand_'+side,eva.E[side],local,bend,q)*UNIT
   for name in ['arm_'+side,'forearm_'+side]:hand_previous[name]=R.from_matrix(p.matrix(name)[:3,:3])
   for n in HERO_NAMES:
    if n.startswith('finger_') and n.endswith('_'+side):p.setq(n,b.qmix(eva.idle.q[n],b.fist.q.get(n,p.q[n]),1-(1-curl)*weight))
   evidence.append(dict(time=t,kind='hand_'+side,error=float(error),weight=float(weight)))
  else:
   hand_bends.pop(side,None)
   hand_previous.pop('arm_'+side,None);hand_previous.pop('forearm_'+side,None)
   for n in HERO_NAMES:
    if n.startswith('finger_') and n.endswith('_'+side):p.setq(n,b.fist.q.get(n,p.q[n]))
 if 8.5<t<10:
  weight=b.smooth((t-8.5)/.5)*(1-b.smooth((t-9.4)/.6));target=a.skin()[KICK_INDEX]*UNIT+aroot;reference,_=hero_prior(9.2);impact=b.hero_world(reference,root_hero(9.2),'foot_r',eva.P['foot_r']+KICK_TIP);q=R.from_matrix(p.matrix('foot_r')[:3,:3]);current=b.hero_world(p,root,'foot_r',eva.P['foot_r']+KICK_TIP);desired=current+(target-impact)*weight;ankle=(desired-root)*MIRROR/UNIT-q.apply(KICK_TIP);hip=p.point('leg_r');direction=retarget.unit(ankle-hip);pole=p.point('leg_r',eva.K['r'])-hip;bend=retarget.unit(pole-direction*np.dot(pole,direction),(0,0,-1))
  if 'kick' in hand_bends:
   previous=retarget.unit(hand_bends['kick']-direction*np.dot(hand_bends['kick'],direction),(0,0,-1));arc=eva.arc(previous,bend).as_rotvec();angle=np.linalg.norm(arc)
   if angle>math.radians(12):bend=R.from_rotvec(arc*math.radians(12)/angle).apply(previous)
  hand_bends['kick']=bend
  for name in ['leg_r','shin_r']:
   key='kick_'+name;current_q=R.from_matrix(p.matrix(name)[:3,:3])
   if key in hand_previous:current_q=b.qmix(hand_previous[key],current_q,.35);p.setq(name,R.from_matrix(p.parent(name)[:3,:3]).inv()*current_q)
  error=b.stable_ik(p,'leg_r','shin_r','foot_r',eva.K['r'],ankle,bend,q)*UNIT
  for name in ['leg_r','shin_r']:hand_previous['kick_'+name]=R.from_matrix(p.matrix(name)[:3,:3])
  evidence.append(dict(time=t,kind='kick_contact',error=float(error),weight=float(weight)))

def main():
 global GROUND_LEAN,GROUND_ROOT,BRACE_INDEX,GRIP_INDEX,KICK_INDEX,KICK_TIP
 from scipy.optimize import minimize_scalar
 a,_=angel_prior(12.75);core=b.angel_world(a,root_angel(12.75),'torso_upper',b.ANGEL.core)+[0,.45,0]
 def fit(lean):
  p,_=pound_pose(53,lean);hand=b.hero_world(p,np.zeros(3),'hand_r',eva.P['finger_middle_r']);placement=core-hand;return (hand[1]-core[1])**2*100+(placement[0]**2+(placement[2]-52)**2)*.002
 GROUND_LEAN=float(minimize_scalar(fit,bounds=(-1.35,-.1),method='bounded').x);p,_=pound_pose(53);hand=b.hero_world(p,np.zeros(3),'hand_r',eva.P['finger_middle_r']);GROUND_ROOT=core-hand;GROUND_ROOT[1]=0;print('R12 ground-strike placement',GROUND_LEAN,GROUND_ROOT,flush=True)
 vertices=a.skin()*UNIT+root_angel(12.75);shoulder=b.hero_world(p,GROUND_ROOT,'arm_l');torso_ids=[b.ANGEL.names.index(n) for n in ['torso_lower','torso_upper']];eligible=np.sum(np.where(np.isin(b.ANGEL.ids,torso_ids),b.ANGEL.weights,0),axis=1)>.65;distance=np.linalg.norm(vertices-shoulder,axis=1);BRACE_INDEX=int(np.where(eligible,distance,np.inf).argmin());print('R12 brace surface',BRACE_INDEX,vertices[BRACE_INDEX],distance[BRACE_INDEX],flush=True)
 ga,_=angel_prior(7);gp,_=hero_prior(7);verts=ga.skin()*UNIT+root_angel(7);elbow=b.angel_world(ga,root_angel(7),'forearm_l');shoulder=b.hero_world(gp,root_hero(7),'arm_r');ids=[b.ANGEL.names.index(n) for n in ['arm_l','forearm_l']];eligible=np.sum(np.where(np.isin(b.ANGEL.ids,ids),b.ANGEL.weights,0),axis=1)>.6;score=np.linalg.norm(verts-elbow,axis=1)**2+.13*np.linalg.norm(verts-shoulder,axis=1)**2;GRIP_INDEX=int(np.where(eligible,score,np.inf).argmin())
 ka,_=angel_prior(9.2);verts=ka.skin()*UNIT+root_angel(9.2);waist=b.angel_world(ka,root_angel(9.2),'torso_lower',b.ANGEL.waist);bone=b.ANGEL.names.index('torso_lower');eligible=np.sum(np.where(b.ANGEL.ids==bone,b.ANGEL.weights,0),axis=1)>.5;front=retarget.unit(root_hero(9.2)+[0,waist[1],0]-waist);score=np.linalg.norm(verts-waist,axis=1)**2-6*((verts-waist)@front);KICK_INDEX=int(np.where(eligible,score,np.inf).argmin())
 kp,_=hero_prior(9.2);q=R.from_matrix(kp.matrix('foot_r')[:3,:3]);direction=retarget.unit(verts[KICK_INDEX]-b.hero_world(kp,root_hero(9.2),'foot_r'));projection=(q.apply(eva.feet['r'])*MIRROR)@direction;KICK_TIP=eva.feet['r'][projection>projection.max()-.4].mean(0)
 b.AXES.clear();evidence.clear();hand_bends.clear();hand_previous.clear();hero=dict(bones=HERO_NAMES,frames=[],root_blocks=[],eye_blocks=[],look_blocks=[],socket_blocks=[],socket_outward_blocks=[],socket_up_blocks=[],hand_l_blocks=[],hand_r_blocks=[],foot_l_blocks=[],foot_r_blocks=[]);enemy=dict(bones=b.ANGEL.names,frames=[],root_blocks=[],eye_blocks=[],hand_l_blocks=[],hand_r_blocks=[],core_blocks=[],waist_blocks=[]);camera=dict(position=[],target=[],fov=[]);hero_feet=Feet();enemy_feet=Feet(True);floors=[]
 for i in range(691):
  t=i/FPS;a,am=angel_prior(t);p,hm=hero_prior(t);hr=root_hero(t);ar=root_angel(t)
  if 'root' in am:ar=am['root']
  hero_feet.apply(p,hr,hm,not hm.get('air') and not hm.get('kneel') and t<10 or t>=19.4);enemy_feet.apply(a,ar,am,t<9.2)
  if t<9.2:a.ground()
  constrain_hands(t,p,hr,a,ar)
  if 11.25<t<19.4:
   minimum=surface.floor(p,['torso_lower','leg_l','leg_r','shin_l','shin_r','foot_l','foot_r'])*UNIT+hr[1]
   if minimum<0:p.setp('root',p.p['root']+[0,-minimum/UNIT,0])
  # Captured head motion is retained; a modest target adjustment keeps the
  # fighting pair engaged without replacing the torso's performance.
  if t<16.8:b.aim_head(p,hr,b.angel_world(a,ar,'torso_upper',b.ANGEL.core) if t>11 else b.angel_world(a,ar,'head',b.ANGEL.eye),.35)
  hero['frames'].append(eva.encode(p,bone_names=HERO_NAMES));enemy['frames'].append(a.encode())
  for role,pose,root,fn in [(hero,p,hr,b.hero_world),(enemy,a,ar,b.angel_world)]:
   role['root_blocks'].append(np.round(root,6).tolist())
   for side in ['l','r']:role['hand_'+side+'_blocks'].append(np.round(fn(pose,root,'hand_'+side,eva.P['finger_middle_'+side] if role is hero else None),6).tolist())
  for side in ['l','r']:hero['foot_'+side+'_blocks'].append(np.round(b.hero_world(p,hr,'foot_'+side,eva.P['foot_'+side]+b.SOLE[side]),6).tolist())
  eye=b.hero_world(p,hr,'head',b.EYE);hero['eye_blocks'].append(eye.round(6).tolist());direction=p.matrix('head')[:3,:3]@np.array([0,0,-1]);hero['look_blocks'].append((eye+direction*MIRROR*20).round(6).tolist())
  for name,bone,marker in [('eye_blocks','head',b.ANGEL.eye),('core_blocks','torso_upper',b.ANGEL.core),('waist_blocks','torso_lower',b.ANGEL.waist)]:enemy[name].append(b.angel_world(a,ar,bone,marker).round(6).tolist())
  socket=b.hero_world(p,hr,'torso_upper',np.array([0,52.9,4.35])/UNIT);rotation=p.matrix('torso_upper')[:3,:3];outward=(rotation@np.array([0,.8660254,.5]))*MIRROR;up=(rotation@np.array([0,.5,-.8660254]))*MIRROR
  hero['socket_blocks'].append(socket.round(6).tolist());hero['socket_outward_blocks'].append((socket+outward*2).round(6).tolist());hero['socket_up_blocks'].append((socket+up*2).round(6).tolist())
  camera['position'].append(b.curve([(k,v) for k,v,_ in b.CAMERAS],t).round(6).tolist());camera['target'].append(b.curve([(k,v) for k,_,v in b.CAMERAS],t).round(6).tolist());camera['fov'].append(70)
  if i%15==0:
   low=surface.floor(p,['torso_lower','torso_upper','head','arm_l','arm_r','forearm_l','forearm_r','hand_l','hand_r','leg_l','leg_r','shin_l','shin_r','foot_l','foot_r'])*UNIT+hr[1];floors.append(dict(t=t,eva_floor=float(low),angel_floor=float(a.skin()[:,1].min()*UNIT+ar[1])))
  if i%60==0:print('R12 full-body capture draft',round(t,2),flush=True)
 result=dict(schema=1,fps=FPS,duration_ticks=460,reference='R12 full-body human motion adaptation; CMU paired interaction, BNR strike/kick, Tuffles jump/fall/kneeling strike; authored nonhuman wrap',eva=hero,angel=enemy,camera=camera)
 (OUT/'candidate_v1.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf-8');(OUT/'candidate_v1_contacts.json').write_text(json.dumps(evidence,indent=2));(OUT/'candidate_v1_floor.json').write_text(json.dumps(floors,indent=2));print('R12 draft baked; not installed')
if __name__=='__main__':main()
