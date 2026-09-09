"""Author a paired TV-inspired battle from measured rigs and explicit contact targets.

No anime frames or audio are embedded. World paths and skeletal poses are baked
together; the native director will consume the same clock and socket curves.
"""
import copy,json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
import build_eva_body_r05 as eva
from author_eva_rifle_stances_r06 import multiply
ROOT=eva.ROOT;OUT=ROOT/'artifacts/first_battle_world_r10/choreography';OUT.mkdir(parents=True,exist_ok=True)
FPS=30;DURATION=23.;UNIT=5/16;HEROMIRROR=np.array([-1,1,-1]);errors=[]
AXES={};HEAD_WRAP=None
def smooth(t):t=float(np.clip(t,0,1));return t*t*t*(10+t*(-15+6*t))
def mix(a,b,t):return np.asarray(a)*(1-t)+np.asarray(b)*t
def qmix(a,b,t):return Slerp([0,1],R.concatenate([a,b]))([np.clip(t,0,1)])[0]
def stable_ik(p,a,b,c,joint,target,pole,orientation):
    shoulder=p.point(a);u=joint-eva.P[a];v=eva.P[c]-joint;la=np.linalg.norm(u);lb=np.linalg.norm(v);delta=np.asarray(target)-shoulder;length=np.linalg.norm(delta);direction=delta/max(length,1e-8)
    distance=np.clip(length,abs(la-lb)+.001,la+lb-.001);along=(la*la-lb*lb+distance*distance)/(2*distance);h=math.sqrt(max(0,la*la-along*along));bend=np.asarray(pole)-direction*np.dot(pole,direction)
    if np.linalg.norm(bend)<1e-6:bend=np.cross(direction,[1,0,0])
    bend/=np.linalg.norm(bend);elbow=shoulder+along*direction+h*bend;axis=np.cross(elbow-shoulder,target-elbow);axis/=max(np.linalg.norm(axis),1e-8)
    rest_axis=np.cross(u,v)
    if np.linalg.norm(rest_axis)<1e-6:rest_axis=np.array([1.,0,0])
    rest_axis/=np.linalg.norm(rest_axis)
    if rest_axis[0]<0:rest_axis=-rest_axis
    reference=AXES.get(a,p.matrix(a)[:3,:3]@rest_axis)
    if axis@reference<0:axis=-axis
    AXES[a]=axis.copy()
    def frame(d,x):
        y=d/np.linalg.norm(d);x=x-y*np.dot(x,y);x/=np.linalg.norm(x);return np.column_stack((x,y,np.cross(x,y)))
    def orient(n,rest,d):p.setq(n,R.from_matrix(p.parent(n)[:3,:3]).inv()*R.from_matrix(frame(d,axis)@frame(rest,rest_axis).T))
    orient(a,u,elbow-shoulder);actual=(p.parent(b)@np.r_[joint,1])[:3];orient(b,v,target-actual);p.hinge(b,joint);p.setq(c,R.from_matrix(p.parent(c)[:3,:3]).inv()*orientation)
    return float(np.linalg.norm(p.point(c)-target))
def curve(keys,t):
    if t<=keys[0][0]:return np.array(keys[0][1],float)
    for (ta,a),(tb,b) in zip(keys,keys[1:]):
        if t<=tb:return mix(a,b,smooth((t-ta)/(tb-ta)))
    return np.array(keys[-1][1],float)
def hero_root(t):
    p=curve([(0,[0,0,0]),(1.2,[0,0,3]),(3,[0,0,3]),(5,[0,0,5]),(6.2,[0,0,5]),(8.5,[0,0,8]),(9.2,[0,0,9]),(10,[0,0,9]),(11.7,[0,0,52]),(19.4,[0,0,52]),(21.6,[0,0,59]),(23,[0,0,59])],t)
    if 10<t<11.7:p[1]=13*math.sin(math.pi*(t-10)/1.7)
    return p
def angel_root(t):
    p=curve([(0,[0,0,34]),(9.2,[0,0,34]),(10.7,[0,0,55]),(23,[0,0,55])],t)
    if 9.2<t<10.2:p[1]=.8*math.sin(math.pi*(t-9.2))
    return p

class AngelRig:
    def __init__(self):
        root=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele';d=json.loads((OUT.parent/'models/sachiel_rig.json').read_text());self.bones={b['name']:b for b in d['bones']};self.P={n:np.array(b['pivot'])*[-1,1,1] for n,b in self.bones.items()};self.parents={n:b.get('parent') for n,b in self.bones.items()};self.names=list(self.bones)
        mesh=json.loads((root/'mesh/sachiel.mesh.json').read_text());v=np.array(mesh['parts']['root']['vertices']).reshape(-1,8)[:,:3]*[-1,1,1];ids=np.array(mesh['skin']['indices']).reshape(-1,4);w=np.array(mesh['skin']['weights']).reshape(-1,4)
        _,indices=np.unique(np.round(v,6),axis=0,return_index=True);self.vertices=v[indices];self.ids=ids[indices];self.weights=w[indices]
        self.core=(np.array([0,12.63,1.42])-[0,d['source_floor'],0])*d['source_scale']*[-1,1,-1]
        self.eye=(np.array([0,15.05,1.40])-[0,d['source_floor'],0])*d['source_scale']*[-1,1,-1]
        self.waist=(np.array([0,8.405552,.129547])-[0,d['source_floor'],0])*d['source_scale']*[-1,1,-1]
    def pose(self):return AngelPose(self)
class AngelPose:
    def __init__(self,rig):self.rig=rig;self.q={n:R.identity() for n in rig.names};self.p={n:np.zeros(3) for n in rig.names};self.cache={}
    def setq(self,n,q):self.q[n]=q;self.cache.clear()
    def setp(self,n,p):self.p[n]=np.asarray(p);self.cache.clear()
    def matrix(self,n):
        if n in self.cache:return self.cache[n]
        local=eva.T(self.p[n])@eva.T(self.rig.P[n]);local[:3,:3]=self.q[n].as_matrix();local=local@eva.T(-self.rig.P[n]);parent=self.rig.parents[n];self.cache[n]=(self.matrix(parent) if parent else np.eye(4))@local;return self.cache[n]
    def parent(self,n):return self.matrix(self.rig.parents[n]) if self.rig.parents[n] else np.eye(4)
    def point(self,n,p=None):return (self.matrix(n)@np.r_[self.rig.P[n] if p is None else p,1])[:3]
    def ik(self,a,b,c,target,pole,orientation=None):
        pa,pb,pc=(self.rig.P[n] for n in [a,b,c]);shoulder=self.point(a);u,v=pb-pa,pc-pb;la,lb=np.linalg.norm(u),np.linalg.norm(v);delta=np.asarray(target)-shoulder;length=np.linalg.norm(delta);direction=delta/max(length,1e-8);distance=np.clip(length,abs(la-lb)+.001,la+lb-.001)
        along=(la*la-lb*lb+distance*distance)/(2*distance);h=math.sqrt(max(0,la*la-along*along));bend=np.asarray(pole)-direction*np.dot(pole,direction)
        if np.linalg.norm(bend)<1e-6:bend=np.cross(direction,[0,1,0])
        bend/=max(np.linalg.norm(bend),1e-8);joint=shoulder+along*direction+h*bend;axis=np.cross(joint-shoulder,target-joint)
        if np.linalg.norm(axis)<1e-6:axis=np.cross(direction,bend)
        axis/=max(np.linalg.norm(axis),1e-8)
        def frame(d,x):
            y=d/np.linalg.norm(d);x=x-y*np.dot(x,y);x/=np.linalg.norm(x);return np.column_stack((x,y,np.cross(x,y)))
        rest_axis=np.cross(u,v)
        if np.linalg.norm(rest_axis)<1e-6:rest_axis=np.array([1.,0,0])
        rest_axis/=np.linalg.norm(rest_axis)
        if rest_axis[0]<0:rest_axis=-rest_axis
        def orient(n,rest,d):self.setq(n,R.from_matrix(self.parent(n)[:3,:3]).inv()*R.from_matrix(frame(d,axis)@frame(rest,rest_axis).T))
        orient(a,u,joint-shoulder);orient(b,v,np.asarray(target)-self.point(b))
        if orientation is not None:self.setq(c,R.from_matrix(self.parent(c)[:3,:3]).inv()*orientation)
        return float(np.linalg.norm(self.point(c)-target))*UNIT
    def skin(self):
        matrices=np.array([self.matrix(n) for n in self.rig.names]);q=R.from_matrix(matrices[:,:3,:3]).as_quat();d=.5*multiply(np.c_[matrices[:,:3,3],np.zeros(len(q))],q)
        qs=q[self.rig.ids];ds=d[self.rig.ids];sign=np.where(np.sum(qs*qs[:,0:1,:],axis=-1,keepdims=True)<0,-1,1);w=self.rig.weights[:,:,None]
        q=np.sum(qs*w*sign,axis=1);d=np.sum(ds*w*sign,axis=1);norm=np.linalg.norm(q,axis=1,keepdims=True);q/=norm;d/=norm;d-=q*np.sum(q*d,axis=1,keepdims=True)
        return R.from_quat(q).apply(self.rig.vertices)+2*multiply(d,q*[-1,-1,-1,1])[:,:3]
    def ground(self):self.setp('root',self.p['root']+[0,-self.skin()[:,1].min(),0])
    def encode(self):
        qs=[]
        for n in self.rig.names:x,y,z,w=self.q[n].as_quat();qs.append([w,-x,-y,z])
        return dict(root_m=np.round(self.p['root']*[-1,1,1]/112,8).tolist(),rotation_wxyz=np.round(qs,8).tolist(),bone_position_xyz={n:np.round(v*[-1,1,1],7).tolist() for n,v in self.p.items() if n!='root' and np.linalg.norm(v)>1e-7})
ANGEL=AngelRig()
def angel_world(p,root,n,point=None):return root+p.point(n,point)*UNIT
def hero_world(p,root,n,point=None):return root+p.point(n,point)*HEROMIRROR*UNIT

def grip(side,t):
    u=smooth((t-6.2)/2.3);sign=1 if side=='r' else -1
    return np.array([sign*(14.2+2.3*u),38.3-4.3*u,20.6+.9*u])
def make_angel(t):
    t=min(t,18.6);p=ANGEL.pose();root=angel_root(t)
    for side in ['l','r']:p.setq('forearm_'+side,R.from_euler('x',-math.pi/2*(1-smooth((t-1.2)/2.4))))
    p.ground()
    if 6.2<=t<=8.5:
        for side in ['l','r']:
            target=(grip(side,t)-root)/UNIT;current=p.point('forearm_'+side)-p.point('arm_'+side);current/=np.linalg.norm(current)
            desired=np.array([-1 if side=='l' else 1,-.3,-.3]);desired/=np.linalg.norm(desired);pole=mix(current,desired,smooth((t-6.2)/.65))
            error=p.ik('arm_'+side,'forearm_'+side,'hand_'+side,target,pole,R.identity());errors.append(dict(time=t,kind='angel_grip_'+side,error=error))
    if 8.5<t<16.8:
        start,_=make_angel(8.5);u=smooth((t-8.5)/.65)
        for side,sign in [('l',-1),('r',1)]:
            for bone,desired in [('arm_'+side,R.from_euler('z',sign*.24)),('forearm_'+side,R.from_euler('x',-math.pi/2)),('hand_'+side,R.identity())]:p.setq(bone,qmix(start.q[bone],desired,u))
        p.setq('torso_lower',R.from_euler('x',math.pi/2*smooth((t-9.2)/1.5)));p.ground()
    if t>=16.8:
        start,_=make_angel(16.799);u=smooth((t-16.8)/1.8)
        for n in ANGEL.names:p.setq(n,start.q[n]);p.setp(n,start.p[n].copy())
        desired={'torso_lower':R.from_euler('x',math.radians(-50)),'torso_upper':R.from_euler('x',math.radians(-10))}
        for side in ['l','r']:desired['leg_'+side]=R.from_euler('x',math.radians(105));desired['shin_'+side]=R.from_euler('x',math.radians(-130))
        for n,q in desired.items():p.setq(n,qmix(start.q[n],q,u))
        p.setp('root',start.p['root']*(1-u));centre=p.point('torso_upper')*UNIT
        target_root=np.array([0,41,hero_root(t)[2]+1])-centre;root=mix(angel_root(16.8),target_root,u)
        root[1]=max(root[1],-p.skin()[:,1].min()*UNIT)
        wrap=smooth((t-17.1)/1.0)
        for side,sign in [('l',-1),('r',1)]:
            current=angel_world(p,root,'hand_'+side);target=mix(current,[sign*10,43,hero_root(t)[2]+1],wrap)
            if wrap>0:
                names=['arm_'+side,'forearm_'+side,'hand_'+side];before={n:p.q[n] for n in names}
                p.ik(*names,(target-root)/UNIT,np.array([sign,0,1]),R.from_euler('x',.5))
                for n in names:p.setq(n,qmix(before[n],p.q[n],wrap))
    return p,root

IDLE=eva.idle
HEAVY=json.loads((ROOT/'src/main/resources/assets/projectseele/motion/eva_heavy_right_cross_r05.json').read_text());heavy_frame=HEAVY['clips']['heavy_right_cross']['frames'][32];fist=eva.decode(heavy_frame,HEAVY['bones'])
HIT_Q=R.from_matrix(fist.matrix('hand_r')[:3,:3]);EVA_NAMES=list(eva.rig)
EYE=np.array(json.loads((ROOT/'run/projectseele-local-maps/eva_body_r06.json').read_text())['eye_positions']['1'])
SOLE={s:eva.feet[s][eva.feet[s][:,1]<eva.feet[s][:,1].min()+.6].mean(0) for s in ['l','r']}
_impact_pose,_impact_root=make_angel(9.2)
WAIST_CONTACT=angel_world(_impact_pose,_impact_root,'torso_lower',ANGEL.waist)+[0,0,-.12]
def hero_copy(p):
    q=eva.Pose();q.q=dict(p.q);q.p={n:v.copy() for n,v in p.p.items()};return q
def hip_at(p,height):
    current=(p.point('leg_l')+p.point('leg_r'))/2;p.setp('root',p.p['root']+[0,height/UNIT-current[1],0])
def hero_hand(p,root,side,target,orientation,curl=0,pole_weight=1):
    p.setq('wrist_'+side,R.identity());p.setp('wrist_'+side,[0,0,0]);tip=eva.P['finger_middle_'+side]-eva.P['hand_'+side]
    hand_target=(np.asarray(target)-root)*HEROMIRROR/UNIT-orientation.apply(tip)
    current=p.point('arm_'+side,eva.E[side])-p.point('arm_'+side);current/=np.linalg.norm(current);desired=np.array([-1 if side=='l' else 1,-.3,.25]);desired/=np.linalg.norm(desired)
    error=stable_ik(p,'arm_'+side,'forearm_'+side,'hand_'+side,eva.E[side],hand_target,mix(current,desired,pole_weight),orientation)*UNIT
    for n in eva.rig:
        if n.startswith('finger_') and n.endswith('_'+side):p.setq(n,qmix(IDLE.q[n],fist.q.get(n,IDLE.q[n]),curl))
    return error
def hero_foot(p,root,side,sole,orientation,pole):
    target=(np.asarray(sole)-root)*HEROMIRROR/UNIT;target[1]-=orientation.apply(eva.feet[side])[:,1].min()
    return stable_ik(p,'leg_'+side,'shin_'+side,'foot_'+side,eva.K[side],target,np.asarray(pole,float),orientation)*UNIT
def aim_head(p,root,target,weight):
    base=p.q['head'];up=np.array([0.,1,0]);parent=R.from_matrix(p.parent('head')[:3,:3])
    for _ in range(3):
        eye=hero_world(p,root,'head',EYE);forward=(np.asarray(target)-eye)*HEROMIRROR;forward/=max(np.linalg.norm(forward),1e-8);right=np.cross(forward,up)
        if np.linalg.norm(right)<1e-5:break
        right/=np.linalg.norm(right);vertical=np.cross(right,forward);world=R.from_matrix(np.column_stack((right,vertical,-forward)))
        angles=(parent.inv()*world).as_euler('xyz');angles=np.clip(angles,[-1.15,-.6,-.18],[.65,.6,.18]);p.setq('head',qmix(base,R.from_euler('xyz',angles),weight))
def step(a,b,t,lo,hi,lift):
    u=smooth((t-lo)/(hi-lo));p=mix(a,b,u);p[1]+=lift*math.sin(math.pi*u);return p
def make_hero(t,angel,aroot):
    global HEAD_WRAP
    p=hero_copy(IDLE);root=hero_root(t);hip=34.96;lower=0.;upper=0.;crouch=smooth((t-10.8)/.9)*(1-smooth((t-16.8)/1.7))
    if t<10:
        lower=-.12*smooth(t/2);upper=-.10*smooth((t-2)/3);hip-=3*smooth((t-3)/3)
        coil=smooth((t-9.65)/.35);hip=(1-coil)*hip+coil*30;lower=(1-coil)*lower-.10*coil;upper=(1-coil)*upper-.12*coil
    elif t<11.7:
        u=smooth((t-10.8)/.9);lower=-.10-.18*u;upper=-.12-.28*u;hip=30-13*u
    elif t<18.5:lower=-.28*crouch;upper=-.40*crouch;hip=34.96-17.96*crouch
    else:lower=upper=0
    impact=sum(math.exp(-((t-hit)/.16)**2) for hit in [12.75,14.15,16.05]);hip-=1.1*impact;upper-=.08*impact
    if 19.4<t<21.6:hip-=.8*math.sin(math.pi*(t-19.4)/2.2)
    p.setq('torso_lower',R.from_euler('x',lower));p.setq('torso_upper',R.from_euler('x',upper));hip_at(p,hip)
    soles={'l':np.array([10.5,0,3.2]),'r':np.array([-10.5,0,3.2])};orient={s:R.from_matrix(IDLE.matrix('foot_'+s)[:3,:3]) for s in ['l','r']}
    soles['l']=step(soles['l'],[10.5,0,7],t,.15,.95,1.1)
    soles['r']=step(soles['r'],[-10.5,0,11],t,5.2,6.1,1.5)
    kick_contact=None
    if 8.5<=t<10:
        target=WAIST_CONTACT
        # Contact is the boot's sole surface, not the ankle pivot six metres behind it.
        u=smooth((t-8.5)/.7) if t<=9.2 else 1-smooth((t-9.2)/.8)
        ground=np.array([10.5,0,7] if t<=9.2 else [10.5,0,11],float)
        ankle=ground+np.array([0,-orient['l'].apply(eva.feet['l'])[:,1].min()*UNIT,0]);ground_contact=ankle+orient['l'].apply(SOLE['l'])*HEROMIRROR*UNIT
        kick_contact=mix(ground_contact,target,u);orient['l']=qmix(orient['l'],R.from_euler('x',math.pi/2),u)
    if 10<=t<11.7:
        u=(t-10)/1.7;fold=math.sin(math.pi*u)
        for side,sign in [('l',1),('r',-1)]:soles[side]=root+[sign*(10.5+fold),6*fold,2-7*fold]
    if 11.7<=t<19.4:
        for side,sign in [('l',1),('r',-1)]:soles[side]=np.array([sign*11.5,0,54])
    if t>=19.4:
        for side,sign in [('l',1),('r',-1)]:soles[side]=step([sign*11.5,0,54],[sign*10.5,0,62.2],t,19.4+(0 if side=='l' else .9),20.5+(0 if side=='l' else .9),1.6)
    for side in ['l','r']:
        if side=='l' and kick_contact is not None:
            ankle=(kick_contact-root)*HEROMIRROR/UNIT-orient[side].apply(SOLE[side]);error=stable_ik(p,'leg_l','shin_l','foot_l',eva.K['l'],ankle,np.array([-.5,0,-1]),orient[side])*UNIT
        else:error=hero_foot(p,root,side,soles[side],orient[side],[-.5 if side=='l' else .5,0,-1])
        errors.append(dict(time=t,kind='eva_foot_'+side,error=error))
    basehands={s:hero_world(p,root,'hand_'+s,eva.P['finger_middle_'+s]) for s in ['l','r']}
    for side,sign in [('l',1),('r',-1)]:
        target=basehands[side];q=R.from_matrix(p.matrix('hand_'+side)[:3,:3]);curl=0
        if 0<=t<6.2:
            reach=smooth((t-.35)/1.1);tear=smooth((t-3)/2);handoff=smooth((t-5.2)/1)
            field=mix([sign*(7+5*tear),40-2*tear,21],grip('r' if side=='l' else 'l',6.2)+[0,.25,-1.05],handoff)
            target=mix(target,field,reach);q=qmix(q,R.from_euler('z',sign*(.48-.18*handoff)),reach);curl=.3*tear*(1-handoff)+.5*handoff
        if 6.2<=t<8.5:
            other='r' if side=='l' else 'l';target=grip(other,t)+[0,.25,-1.05];q=R.from_euler('z',sign*.3);curl=.5
        if 8.5<=t<10:
            u=smooth((t-8.5)/.6);target=mix(grip('r' if side=='l' else 'l',8.5)+[0,.25,-1.05],root+[sign*12,42,10],u);q=R.from_euler('z',sign*(.3+.05*u));curl=.5+.5*u
        if 10<=t<11.7:
            u=smooth((t-10)/.35);target=root+mix([sign*12,42,10],[sign*15,44,10],u);q=R.from_euler('z',sign*.35);curl=1-.7*u
        if 11.2<=t<17.6:
            core=angel_world(angel,aroot,'torso_upper',ANGEL.core);u=smooth((t-11.2)/.5)
            if side=='l':desired=core+[6,0,-1];hand_q=R.from_euler('x',-math.pi/2);desired_curl=.35
            else:
                desired=core+[-11,10,-5];hand_q=R.from_euler('x',-math.pi/2)*HIT_Q;desired_curl=1
                for start,hit,end in [(12.,12.75,13.4),(13.4,14.15,15.0),(15.2,16.05,16.8)]:
                    if start<=t<=end:
                        wind=core+[-14,15,-6];press=core+[0,6.0 if start>=15 else .35,0]
                        if t<hit-.36:desired=mix(core+[-11,10,-5],wind,smooth((t-start)/max(.1,hit-.36-start)))
                        elif t<hit:
                            strike=smooth((t-hit+.36)/.36);desired=mix(wind,press,strike)+[-4*math.sin(math.pi*strike),0,0]
                        elif t<hit+.10:desired=press
                        else:desired=mix(press,core+[-11,10,-5],smooth((t-hit-.1)/max(.1,end-hit-.1)))
                if 15<=t<15.35:
                    desired=mix(core+[-11,10,-5],core+[-5,0,-2],smooth((t-15)/.35))
                elif 15.35<=t<15.69:desired=mix(core+[-5,0,-2],core+[-14,15,-6],smooth((t-15.35)/.34))
                if 14.85<=t<15.6:desired_curl=1-.6*smooth((t-14.85)/.30)+.6*smooth((t-15.25)/.35)
            target=mix(target,desired,u);q=qmix(q,hand_q,u);curl=(1-u)*curl+u*desired_curl
        if 16.8<=t<19.4:
            u=smooth((t-16.8)/.8);target=mix(target,root+[sign*12,39,5],u);q=qmix(q,R.from_euler('z',sign*.3),u);curl=(1-u)*curl+.7*u
        if t>=19.4:
            u=1-smooth((t-19.4)/2.2);target=mix(basehands[side],root+[sign*12,39,5],u);q=qmix(q,R.from_euler('z',sign*.3),u);curl=.7*u
        pole_weight=smooth((t-.2)/1)*(1-smooth((t-19.4)/2.2))
        error=hero_hand(p,root,side,target,q,curl,pole_weight);errors.append(dict(time=t,kind='eva_hand_'+side,error=error))
    enemy_eye=angel_world(angel,aroot,'head',ANGEL.eye);core=angel_world(angel,aroot,'torso_upper',ANGEL.core)
    if t<16.8:
        target=mix(enemy_eye,core,smooth((t-9.8)/1));aim_head(p,root,target,smooth((t-.2)/1));HEAD_WRAP=p.q['head']
    else:p.setq('head',qmix(HEAD_WRAP if HEAD_WRAP is not None else IDLE.q['head'],IDLE.q['head'],smooth((t-16.8)/1.3)))
    return p,root

CAMERAS=[(0,[-58,48,69],[0,34,18]),(1.2,[-33,44,46],[0,41,20]),(4.2,[-44,48,36],[0,40,22]),(5.0,[-47,52,65],[0,38,22]),(6.2,[-30,40,25],[0,39,22]),(8.5,[-63,45,54],[0,27,28]),(10.,[-78,70,96],[0,38,47]),(11.7,[-34,46,96],[0,13,69]),(14.4,[-25,34,86],[0,14,69]),(16.8,[-56,48,84],[0,32,61]),(18.6,[-78,46,138],[0,30,63]),(19.4,[-44,46,116],[0,37,68]),(23.,[-44,46,116],[0,37,68])]
def main():
    global HEAD_WRAP
    AXES.clear();HEAD_WRAP=None
    hero=dict(bones=EVA_NAMES,frames=[],root_blocks=[],eye_blocks=[],look_blocks=[],socket_blocks=[],socket_outward_blocks=[],socket_up_blocks=[],hand_l_blocks=[],hand_r_blocks=[],foot_l_blocks=[],foot_r_blocks=[]);enemy=dict(bones=ANGEL.names,frames=[],root_blocks=[],eye_blocks=[],hand_l_blocks=[],hand_r_blocks=[],core_blocks=[],waist_blocks=[]);cameras=dict(position=[],target=[],fov=[]);floor=[]
    for i in range(round(DURATION*FPS)+1):
        t=i/FPS;a,aroot=make_angel(t);h,hroot=make_hero(t,a,aroot)
        hero['frames'].append(eva.encode(h,bone_names=EVA_NAMES));enemy['frames'].append(a.encode())
        for role,p,r,fn in [(hero,h,hroot,hero_world),(enemy,a,aroot,angel_world)]:
            role['root_blocks'].append(np.round(r,6).tolist())
            for side in ['l','r']:role['hand_'+side+'_blocks'].append(np.round(fn(p,r,'hand_'+side,eva.P['finger_middle_'+side] if role is hero else None),6).tolist())
        for side in ['l','r']:hero['foot_'+side+'_blocks'].append(np.round(hero_world(h,hroot,'foot_'+side,eva.P['foot_'+side]+SOLE[side]),6).tolist())
        hero['eye_blocks'].append(np.round(hero_world(h,hroot,'head',EYE),6).tolist());enemy['eye_blocks'].append(np.round(angel_world(a,aroot,'head',ANGEL.eye),6).tolist());enemy['core_blocks'].append(np.round(angel_world(a,aroot,'torso_upper',ANGEL.core),6).tolist());enemy['waist_blocks'].append(np.round(angel_world(a,aroot,'torso_lower',ANGEL.waist),6).tolist())
        direction=h.matrix('head')[:3,:3]@np.array([0,0,-1]);hero['look_blocks'].append(np.round(hroot+(h.point('head',EYE)+direction*64)*HEROMIRROR*UNIT,6).tolist())
        socket=hero_world(h,hroot,'torso_upper',np.array([0,52.9,4.35])/UNIT);rotation=h.matrix('torso_upper')[:3,:3]
        outward=(rotation@np.array([0,.8660254037844386,.5]))*HEROMIRROR;up=(rotation@np.array([0,.5,-.8660254037844386]))*HEROMIRROR
        hero['socket_blocks'].append(socket.round(6).tolist());hero['socket_outward_blocks'].append((socket+outward*2).round(6).tolist());hero['socket_up_blocks'].append((socket+up*2).round(6).tolist())
        cameras['position'].append(curve([(k,p) for k,p,_ in CAMERAS],t).round(6).tolist());cameras['target'].append(curve([(k,q) for k,_,q in CAMERAS],t).round(6).tolist());cameras['fov'].append(70)
        if i%30==0:print('AUTHORED',t,flush=True)
    result=dict(schema=1,fps=FPS,duration_ticks=460,reference='Original choreography based on TV episode 2; low-HP trigger is a game adaptation',eva=hero,angel=enemy,camera=cameras)
    path=ROOT/'src/main/resources/assets/projectseele/motion/first_battle_r10.json';path.write_text(json.dumps(result,separators=(',',':'))+'\n',encoding='utf8')
    (OUT/'authoring_errors.json').write_text(json.dumps(errors,indent=2),encoding='utf8');summary={k:max(r['error'] for r in errors if r['kind']==k) for k in {r['kind'] for r in errors}}
    (OUT/'authoring_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(summary)
if __name__=='__main__':main()
