"""Author contact-supported firearm postures on the measured EVA skeleton."""
from pathlib import Path
import json,copy
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
from scipy.spatial import cKDTree
import build_eva_body_r05 as rig

ROOT=rig.ROOT;OUT=ROOT/'artifacts/motion_review_r06';OUT.mkdir(exist_ok=True)
BODY_NAMES=list(dict.fromkeys(rig.bones+['wrist_l','wrist_r']+[n for n in rig.rig if n.startswith('finger_thumb')]))
MESH={n:(np.array(p['vertices']).reshape(-1,8)[:,:3]+p['pivot'])*[-1,1,1] for n,p in rig.mesh['parts'].items()}
RIFLE=rig.load(rig.PACK/'mesh/eva_pallet_smg.mesh.json')['parts']['cannon']
PC=np.array([24.49137,88.34269,.87469]);BLOCK=16/5
def mat(q,translation=None):
    m=np.eye(4);m[:3,:3]=q.as_matrix()
    if translation is not None:m[:3,3]=translation
    return m
SKIN={}
for a,b in [('arm_l','forearm_l'),('arm_r','forearm_r'),('shin_l','foot_l'),('shin_r','foot_r')]:
    distance,index=cKDTree(MESH[b]).query(MESH[a]);seam=np.unique((MESH[a][distance<.002]+MESH[b][index[distance<.002]])*.5,axis=0)
    if len(seam)<3:continue
    for n,other in [(a,b),(b,a)]:
        distance,index=cKDTree(seam).query(MESH[n]);t=np.maximum(0,1-distance/6);weight=.5*t*t*(3-2*t);weight[distance<.002]=.5
        rest=MESH[n].copy();rest[distance<.002]=seam[index[distance<.002]];SKIN[n]=(other,weight[:,None],rest)
def multiply(a,b):
    a=np.asarray(a);b=np.asarray(b);return np.concatenate((a[...,:3]*b[...,3:]+b[...,:3]*a[...,3:]+np.cross(a[...,:3],b[...,:3]),a[...,3:]*b[...,3:]-np.sum(a[...,:3]*b[...,:3],axis=-1,keepdims=True)),axis=-1)
def vertices(p,n):
    if n not in SKIN:return (np.c_[MESH[n],np.ones(len(MESH[n]))]@p.matrix(n).T)[:,:3]
    other,w,rest=SKIN[n];a=p.matrix(n);b=p.matrix(other);qa=R.from_matrix(a[:3,:3]).as_quat();qb=R.from_matrix(b[:3,:3]).as_quat()
    if qa@qb<0:qb=-qb
    da=.5*multiply(np.r_[a[:3,3],0],qa);db=.5*multiply(np.r_[b[:3,3],0],qb)
    q=(1-w)*qa+w*qb;norm=np.linalg.norm(q,axis=1,keepdims=True);q/=norm;d=((1-w)*da+w*db)/norm;d-=q*np.sum(d*q,axis=1,keepdims=True)
    return R.from_quat(q).apply(rest)+2*multiply(d,q*[-1,-1,-1,1])[:,:3]
def floor(p,names):return min(vertices(p,n)[:,1].min() for n in names)
def clone(p):
    q=rig.Pose();q.q=dict(p.q);q.p={n:v.copy() for n,v in p.p.items()};return q
def foot_target(side,x,z,q):return np.array([x,-q.apply(rig.feet[side])[:,1].min(),z])
def solve_feet(p,targets,orientations,poles,constrain=False):
    for s in ['l','r']:
        p.setq('ankle_'+s,R.identity())
        rig.Pose.ik(p,'leg_'+s,'shin_'+s,'foot_'+s,rig.K[s],targets[s],np.array(poles[s],float),orientations[s])
        if constrain:
            direction=targets[s]-p.point('leg_'+s);direction/=np.linalg.norm(direction);pole=np.array(poles[s],float)
            best=None
            for angle in [0]+[v for a in np.linspace(.08,1.3,17) for v in (a,-a)]:
                candidate=R.from_rotvec(direction*angle).apply(pole)
                rig.Pose.ik(p,'leg_'+s,'shin_'+s,'foot_'+s,rig.K[s],targets[s],candidate,orientations[s])
                low=floor(p,['leg_'+s,'shin_'+s,'foot_'+s]);score=abs(angle)+1000*max(0,-low)
                if best is None or score<best[0]:best=(score,candidate)
                if low>=-.04:break
            rig.Pose.ik(p,'leg_'+s,'shin_'+s,'foot_'+s,rig.K[s],targets[s],best[1],orientations[s])
def hip_at(p,y):
    current=(p.point('leg_l')+p.point('leg_r'))/2;p.setp('root',p.p['root']+np.array([0,y-current[1],0]))
def idle():return rig.decode(rig.base['clips']['idle']['frames'][0])
def kneel(height=53):
    p=idle();p.setq('torso_lower',R.from_euler('x',-.10));p.setq('torso_upper',R.from_euler('xyz',[-.08,-.10,0]));hip_at(p,height)
    qs={'l':R.from_euler('y',-.05),'r':R.from_euler('xyz',[-2.22,.04,0])}
    targets={'l':foot_target('l',-18,-35,qs['l']),'r':foot_target('r',18,56,qs['r'])}
    solve_feet(p,targets,qs,{'l':[0,0,-1],'r':[0,-1,-.25]});p.setq('head',R.from_matrix(p.parent('head')[:3,:3]).inv())
    return p
def prone(ankle=-2.1,out=.4):
    p=idle();old=rig.load(rig.PACK/'animations/eva_unit01.animation.json')['animations']['animation.eva_unit01.prone']['bones']
    for n in ['root','torso_lower','torso_upper','neck','head']:
        for channel,value in old.get(n,{}).items():
            if isinstance(value,dict):value=value[min(value,key=float)]
            if channel=='rotation':p.setq(n,R.from_euler('xyz',np.array(value)*[-1,-1,1],degrees=True))
            elif channel=='position':p.setp(n,np.array(value)*[-1,1,1])
    p.setq('head',R.from_matrix(p.parent('head')[:3,:3]).inv())
    # Belly/chest support determines body height; a down-pointing boot must not jack it up.
    p.setp('root',p.p['root']+[0,-floor(p,['torso_lower','torso_upper']),0])
    hip=(p.point('leg_l')+p.point('leg_r'))/2;length=sum([np.linalg.norm(rig.K['l']-rig.P['leg_l']),np.linalg.norm(rig.P['foot_l']-rig.K['l'])])
    qs={s:R.from_euler('xyz',[ankle,(-.10 if s=='l' else .10),0]) for s in ['l','r']}
    targets={s:foot_target(s,(-24 if s=='l' else 24),hip[2]+length*.97,qs[s]) for s in ['l','r']}
    solve_feet(p,targets,qs,{'l':[-out,1-out,0],'r':[out,1-out,0]})
    return p
def smooth(t):
    t=np.clip(t,0,1);return float(np.clip(t*t*t*(10+t*(-15+6*t)),0,1))
def blend_pose(a,b,t,first_step=False):
    body_t=smooth((t-.1)/.9) if first_step else smooth(t);p=rig.Pose()
    for n in rig.rig:
        p.q[n]=Slerp([0,1],R.concatenate([a.q[n],b.q[n]]))([body_t])[0]
        p.p[n]=(1-body_t)*a.p[n]+body_t*b.p[n]
    core=floor(p,['torso_lower','torso_upper'])
    if core<0:p.setp('root',p.p['root']+[0,-core,0])
    targets={};qs={};poles={}
    for s in ['l','r']:
        u=smooth(t/.45) if first_step and s=='l' else smooth((t-.45)/.4) if first_step else smooth(t)
        ma=a.matrix('foot_'+s);mb=b.matrix('foot_'+s);qa=R.from_matrix(ma[:3,:3]);qb=R.from_matrix(mb[:3,:3]);qs[s]=Slerp([0,1],R.concatenate([qa,qb]))([u])[0]
        target=(1-u)*a.point('foot_'+s)+u*b.point('foot_'+s)
        lift=8*np.sin(np.pi*u) if first_step else 4*np.sin(np.pi*u)
        target[1]=-qs[s].apply(rig.feet[s])[:,1].min()+lift;targets[s]=target
        hint=(1-body_t)*a.point('leg_'+s,rig.K[s])+body_t*b.point('leg_'+s,rig.K[s]);poles[s]=hint-p.point('leg_'+s)
    solve_feet(p,targets,qs,poles,True)
    return p
def aim(p,prone_weight=0):
    forward=np.array([0.,0,-1]);up=np.array([0.,1,0]);right=np.array([1.,0,0]);shoulder=p.point('arm_r')
    pocket=shoulder-right*2.3*BLOCK+forward*5*BLOCK-up*3.1*BLOCK
    stock=pocket+up*5*BLOCK;grip=stock+forward*(49.700046*.72)-up*(7.656318*.72)
    gun_q=R.from_euler('x',np.pi/2);gun=rig.T(grip)@mat(gun_q)@np.diag([.72,.72,.72,1])@rig.T(-PC)
    attachment=rig.T([-1.97646,7.68353,.33048])@rig.T(PC)@mat(R.from_euler('xyz',[-45.37424,18.77208,31.40634],degrees=True))@np.diag([.72,.72,.72,1])@rig.T(-PC)
    hand=rig.T((right-up*1.5)*BLOCK)@gun@np.linalg.inv(attachment)
    qr=R.from_matrix(hand[:3,:3]);tr=(hand@np.r_[rig.P['hand_r'],1])[:3]
    qleft=R.from_euler('xyz',[94.97409,-33.31161,-2.51789],degrees=True)*R.from_euler('xyz',[-12.09838,10.32404,-.10716],degrees=True)
    qreference=R.from_euler('xyz',[45.25275,8.19676,16.13605],degrees=True)*R.from_euler('xyz',[94.81682,21.17865,-15.83803],degrees=True)*R.from_euler('xyz',[-45.37424,18.77208,31.40634],degrees=True)
    ql=gun_q*qreference.inv()*qleft
    tl=grip+forward*2*BLOCK-up*3.3*BLOCK-ql.apply((rig.P['finger_middle_l']-rig.P['hand_l'])*.65)
    for s,target,q,pole in [('r',tr,qr,[1,-.8,0]),('l',tl,ql,[-1,-1,0])]:
        for n in ['wrist_'+s,'hand_'+s]:p.setq(n,R.identity());p.setp(n,np.zeros(3))
        rig.Pose.ik(p,'arm_'+s,'forearm_'+s,'hand_'+s,rig.E[s],target,np.array(pole,float),q)
    grip_bones=rig.load(rig.PACK/'animations/eva_unit01.animation.json')['animations']['animation.eva_unit01.rifle_aim']['bones']
    for n in BODY_NAMES:
        if '_axis_' in n:p.setq(n,R.from_euler('xyz',np.array(rig.rig[n].get('rotation',[0,0,0]))*[-1,-1,1],degrees=True))
        elif n.startswith('finger_') and n in grip_bones:
            v=grip_bones[n].get('rotation',[0,0,0]);v=v[min(v,key=float)] if isinstance(v,dict) else v
            p.setq(n,R.from_euler('xyz',np.array(v)*[-1,-1,1],degrees=True))
    # Bring the dominant eye to the fixed sight line by rotating the head at its joint.
    eye=np.array([2.4,170.3048,-12.01874]);rest=eye-rig.P['head'];joint=p.point('head');sight=grip+up*4.5*BLOCK
    offset=sight-joint;across=offset-forward*np.dot(offset,forward);radius=np.linalg.norm(rest)
    if np.linalg.norm(across)<radius:
        target=across+forward*np.sqrt(radius*radius-np.dot(across,across))
        q=rig.arc(rest,target);p.setq('head',R.from_matrix(p.parent('head')[:3,:3]).inv()*q)
    return gun
def save_pose(p,name,gun=None):
    vs=[];fs=[];uv=[];count=0
    for n,v in MESH.items():
        if n not in p.q:continue
        posed=vertices(p,n)*[-5/16,5/16,-5/16];posed=posed[:,[0,2,1]]*[1,-1,1]
        vs.extend(posed);fs.extend(np.arange(count,count+len(v)).reshape(-1,3));uv.extend(np.array(rig.mesh['parts'][n]['vertices']).reshape(-1,8)[:,3:5]*[1,-1]+[0,1]);count+=len(v)
    body_faces=len(fs)
    if gun is not None:
        v=(np.array(RIFLE['vertices']).reshape(-1,8)[:,:3]+RIFLE['pivot'])*[-1,1,1]
        v=(np.c_[v,np.ones(len(v))]@gun.T)[:,:3]*[-5/16,5/16,-5/16];v=v[:,[0,2,1]]*[1,-1,1]
        vs.extend(v);fs.extend(np.arange(count,count+len(v)).reshape(-1,3));uv.extend(np.array(RIFLE['vertices']).reshape(-1,8)[:,3:5]*[1,-1]+[0,1])
    np.savez_compressed(OUT/(name+'.npz'),v=np.array(vs),f=np.array(fs),uv=np.array(uv),body_faces=body_faces)
    (OUT/(name+'.json')).write_text(json.dumps(rig.encode(p,bone_names=BODY_NAMES)),encoding='utf-8')
    print(name,'height',round(max(vertices(p,n)[:,1].max() for n in MESH if n in p.q)*5/16,2),'ground',
          {n:round(floor(p,[n])*5/16,3) for n in ['torso_lower','torso_upper','leg_r','shin_r','foot_l','foot_r']},flush=True)
def main():
    candidates=[(h,kneel(h)) for h in np.arange(48,64,.25)]
    score=lambda v:abs(v)+max(0,-v)*100
    h,p=min(candidates,key=lambda item:score(floor(item[1],['leg_r','shin_r'])))
    knee=clone(p);print('Kneeling hip',h,flush=True);gun=aim(p);save_pose(p,'kneel_aim',gun)
    candidates=[(a,o,prone(a,o)) for a in np.arange(-2.8,-1.7,.06) for o in [.2,.4,.6,.8]]
    angle,out,p=min(candidates,key=lambda item:score(floor(item[2],['leg_l','shin_l','leg_r','shin_r','foot_l','foot_r']))+.01*(item[0]+2.8)**2)
    lying=clone(p);print('Prone ankle',np.degrees(angle),'out',out,flush=True);gun=aim(p,1);save_pose(p,'prone_aim',gun)
    support=blend_pose(knee,lying,.58);keys=[idle(),knee,support,lying];frames=[];minimum=1e9
    for i in range(181):
        level=i/60;segment=min(2,int(level));t=level-segment;p=blend_pose(keys[segment],keys[segment+1],t,segment==0)
        minimum=min(minimum,floor(p,['torso_lower','torso_upper','leg_l','shin_l','leg_r','shin_r','foot_l','foot_r'])*5/16)
        frames.append(rig.encode(p))
    data=rig.load(ROOT/'run/projectseele-local-maps/eva_body_r05.json');data['motion']['clips']['rifle_stance']={'duration_seconds':3,'loop':False,'frames':frames}
    data['motion']['clips']['rifle_kneel']={'duration_seconds':1,'loop':True,'frames':[rig.encode(knee),rig.encode(knee)]}
    data['eye_positions']={'0':[0,171.04278,-11.15695],'1':[2.4,170.3048,-12.01874],'2':[3,171,-12]}
    (OUT/'eva_body_r06_draft.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    print('STANCE PATH',len(frames),'minimum support',minimum,flush=True)
if __name__=='__main__':main()
