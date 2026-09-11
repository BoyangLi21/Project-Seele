"""Contact-constrained legs and a ballistic pounce for the private TV battle."""
from pathlib import Path
import argparse,copy,hashlib,json
import numpy as np
from scipy.spatial.transform import Rotation as R
import author_first_battle_r12 as a
import finalize_first_battle_r12 as f
from preview_first_battle_r12 import angel_pose

b=a.b;e=a.eva;U=a.UNIT;M=a.MIRROR
ROOT=e.ROOT;OUT=ROOT/'artifacts/grounded_battle_r18';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'run/projectseele-local-maps/first_battle_r15.json'
LIMBS=[n+'_'+s for s in ('l','r') for n in ('leg','shin','foot')]

def world(p,root,bone,point=None):return b.hero_world(p,root,bone,point)
def shift(p,delta):p.setp('root',p.p['root']+np.asarray(delta)*M/U)
def smooth(t,lo,hi):return b.smooth((t-lo)/(hi-lo))

def basis(direction,normal):
    y=a.retarget.unit(direction);x=a.retarget.unit(normal-y*np.dot(y,normal),(1,0,0))
    return np.column_stack((x,y,np.cross(x,y)))

def leg(p,side,ankle,knee_hint,foot_q,previous):
    upper='leg_'+side;lower='shin_'+side;foot='foot_'+side
    points=p.rig.P if isinstance(p,b.AngelPose) else e.P
    h=p.point(upper);k=points[lower] if isinstance(p,b.AngelPose) else e.K[side];u=k-points[upper];v=points[foot]-k
    la=np.linalg.norm(u);lb=np.linalg.norm(v);d=ankle-h;direction=a.retarget.unit(d)
    distance=np.clip(np.linalg.norm(d),abs(la-lb)+.001,la+lb-.001)
    along=(la*la-lb*lb+distance*distance)/(2*distance)
    bend=a.retarget.unit(knee_hint-h-direction*np.dot(knee_hint-h,direction),(0,0,-1))
    target_knee=h+direction*along+bend*np.sqrt(max(0,la*la-along*along))
    normal=a.retarget.unit(np.cross(target_knee-h,ankle-target_knee),(1,0,0))
    reference=previous if previous is not None else p.parent(upper)[:3,:3]@np.array([1.,0,0])
    if np.dot(normal,reference)<0:normal=-normal
    for name,rest,wanted in ((upper,u,target_knee-h),(lower,v,ankle-target_knee)):
        rotation=R.from_matrix(basis(wanted,normal)@basis(rest,np.array([1.,0,0])).T)
        p.setq(name,R.from_matrix(p.parent(name)[:3,:3]).inv()*rotation)
        if name==lower:
            delta=k-points[lower];p.setp(lower,delta-p.q[lower].apply(delta))
    p.setq(foot,R.from_matrix(p.parent(foot)[:3,:3]).inv()*foot_q)
    return normal,float(np.linalg.norm(p.point(foot)-ankle)*U)

def hips_on_knees(p,root,knees,desired):
    # Both thighs retain their actual lengths. The pelvis follows the nearest
    # point on the two-sphere intersection instead of pulling planted knees.
    h=[world(p,root,'leg_'+s) for s in ('l','r')]
    centres=[knees[s]-q for s,q in zip(('l','r'),h)]
    axis=centres[1]-centres[0];distance=np.linalg.norm(axis);axis/=distance
    radius=np.linalg.norm(e.K['l']-e.P['leg_l'])*U
    if distance>=2*radius:raise ValueError('Knee stance exceeds thigh reach')
    centre=(centres[0]+centres[1])/2
    direction=desired-(h[0]+h[1])/2-centre;direction-=axis*np.dot(direction,axis)
    delta=centre+a.retarget.unit(direction,(0,1,0))*np.sqrt(radius*radius-distance*distance/4)
    shift(p,delta)

def kneepad_floor(p,root,side):
    joint=world(p,root,'leg_'+side,e.K[side])
    vertices=np.vstack([a.surface.vertices(p,n+'_'+side) for n in ('leg','shin')])*M*U+root
    nearby=np.linalg.norm(vertices-joint,axis=1)<7
    return float(vertices[nearby,1].min())

def seated_support(original,root,knees,ankles,feet,desired,normals):
    contact={s:k.copy() for s,k in knees.items()}
    # Contact belongs to the rendered kneepad, not the hidden skeletal joint.
    for iteration in range(5):
        p=a.clone(original);hips_on_knees(p,root,contact,desired)
        for s in ('l','r'):
            leg(p,s,(ankles[s]-root)*M/U,(contact[s]-root)*M/U,feet[s],normals[s])
        error={s:kneepad_floor(p,root,s)-.03 for s in ('l','r')}
        if max(abs(v) for v in error.values())<.01:break
        for s in ('l','r'):contact[s][1]-=error[s]
    return p,contact

def support_reach(p,original,previous):
    from scipy.optimize import least_squares
    base=p.q['torso_upper'];targets={s:original.point('hand_'+s) for s in ('l','r')}
    lengths={s:(np.linalg.norm(e.E[s]-e.P['arm_'+s]),np.linalg.norm(e.P['hand_'+s]-e.E[s])) for s in ('l','r')}
    def residual(delta):
        p.setq('torso_upper',R.from_rotvec(delta)*base);result=list(np.asarray(delta)*.12)
        result.extend((np.asarray(delta)-previous)*.025)
        for s in ('l','r'):
            length=np.linalg.norm(targets[s]-p.point('arm_'+s));la,lb=lengths[s]
            result.extend([max(0,length-(la+lb-.08))*8,max(0,abs(la-lb)+.08-length)*8])
        return result
    if max(residual(np.zeros(3))[-4:])<1e-6:return np.zeros(3)
    solved=least_squares(residual,np.clip(previous,-.12,.12),bounds=(-.12,.12),max_nfev=28,ftol=1e-7,xtol=1e-7,gtol=1e-7).x
    p.setq('torso_upper',R.from_rotvec(solved)*base)
    return solved

def author():
    data=json.loads(SOURCE.read_text());heroes=[e.decode(q,data['eva']['bones']) for q in data['eva']['frames']]
    angels=[angel_pose(q,data['angel']['bones']) for q in data['angel']['frames']]
    before=[a.clone(p) for p in heroes];roots=np.array(data['eva']['root_blocks'])
    hips=np.array([(world(p,r,'leg_l')+world(p,r,'leg_r'))/2 for p,r in zip(heroes,roots)])
    centre=np.median(hips[366:485],axis=0);centre[0]=0;centre[1]=17.;centre[2]+=2
    knees={s:centre+[sign*11,4.6-centre[1],4.6] for s,sign in (('l',1),('r',-1))}
    foot_q={s:R.from_euler('x',-np.pi/2) for s in ('l','r')}
    ankles={}
    for s in ('l','r'):
        y=-foot_q[s].apply(e.feet[s])[:,1].min()*U+.03
        length=np.linalg.norm(e.P['foot_'+s]-e.K[s])*U
        ankles[s]=knees[s]+[0,y-knees[s][1],-np.sqrt(length*length-(y-knees[s][1])**2)]
    normals={s:None for s in ('l','r')};records=[]
    entry=before[339];released_arms=None;torso_delta=np.zeros(3);right_contact=None
    for i in range(339,len(heroes)):
        t=i/30;original=before[i];p=a.clone(original);root=roots[i]
        weight=smooth(t,11.3,11.95);release=smooth(t,16.3,17.0)
        contact_knees=knees
        if weight*(1-release)>1e-6:
            support=a.clone(p);desired=centre+(hips[i]-np.median(hips[366:485],axis=0))*[.12,.10,.22]
            if 12.2<t<12.5:desired[2]+=.9*np.sin(np.pi*(t-12.2)/.3)*np.exp(-6*(t-12.2))
            support,contact_knees=seated_support(p,root,knees,ankles,foot_q,desired,normals)
            shift(p,(support.p['root']-p.p['root'])*M*U*weight*(1-release))
        shift(p,[0,3.4*smooth(t,16.3,16.75)*(1-smooth(t,17.05,17.55)),0])
        p.setq('torso_upper',R.from_euler('x',.20*weight*(1-release))*p.q['torso_upper'])
        for s,sign in (('l',1),('r',-1)):
            start,end=(16.3,17.08) if s=='l' else (16.92,17.70)
            step=smooth(t,start,end)
            standing=world(before[558],roots[558],'foot_'+s)
            stand_q=R.from_matrix(before[558].matrix('foot_'+s)[:3,:3])
            q=b.qmix(foot_q[s],stand_q,step)
            goal=b.mix(ankles[s],standing,step)
            goal[1]=-q.apply(e.feet[s])[:,1].min()*U+.03+2.6*np.sin(np.pi*step)
            after=smooth(t,18.6,20.0)
            goal=b.mix(goal,world(original,root,'foot_'+s),after)
            q=b.qmix(q,R.from_matrix(original.matrix('foot_'+s)[:3,:3]),after)
            h=world(p,root,'leg_'+s)
            hint=b.mix(contact_knees[s],h+np.array([sign*.35,-.1,1])*20,step)
            normal,error=leg(p,s,(goal-root)*M/U,(hint-root)*M/U,q,normals[s]);normals[s]=normal
            if weight<1:
                for n in (f'leg_{s}',f'shin_{s}',f'foot_{s}'):
                    p.setq(n,b.qmix(entry.q[n],p.q[n],weight));p.setp(n,b.mix(entry.p[n],p.p[n],weight))
                q=b.qmix(R.from_matrix(entry.matrix('foot_'+s)[:3,:3]),q,weight)
                p.setq('foot_'+s,R.from_matrix(p.parent('foot_'+s)[:3,:3]).inv()*q)
            records.append({'frame':i,'side':s,'ankle_error':error,'knee':world(p,root,'leg_'+s,e.K[s]).tolist(),'ankle':world(p,root,'foot_'+s).tolist()})
        # Keep the original brace and strike contacts while the supported
        # pelvis settles. The established clinch torso is restored by 17 s.
        if i<=481:
            if i>=366:torso_delta=support_reach(p,original,torso_delta)
            for s in ('l','r'):
                goal=original.point('hand_'+s);q=R.from_matrix(original.matrix('hand_'+s)[:3,:3])
                pole=original.point('arm_'+s,e.E[s])-original.point('arm_'+s)
                a.retarget.solve_ik(p,'arm_'+s,'forearm_'+s,'hand_'+s,e.E[s],goal,pole,q)
            if i==481:released_arms=a.clone(p);right_contact=world(p,root,'hand_r')
        elif i<=490:
            # Once the rib strike finishes, hands are no longer world anchors.
            # Carry the supported pose into the authored withdrawal continuously.
            fade=b.smooth((i-481)/9)
            for n in p.q:
                if n.startswith(('arm_','forearm_','hand_','wrist_','finger_')):
                    p.setq(n,b.qmix(released_arms.q[n],original.q[n],fade))
                    p.setp(n,b.mix(released_arms.p[n],original.p[n],fade))
            for s in ('l','r'):
                delta=e.E[s]-e.P['forearm_'+s]
                p.setp('forearm_'+s,delta-p.q['forearm_'+s].apply(delta))
        if 482<=i<=501:
            u=smooth(t,16.05,16.70);current=world(p,root,'hand_r')
            goal=b.mix(right_contact,current,u)+np.array([-12.,3.,0.])*np.sin(np.pi*u)
            q=R.from_matrix(p.matrix('hand_r')[:3,:3]);shoulder=p.point('arm_r')
            target=(goal-root)*M/U;reach=np.linalg.norm(e.E['r']-e.P['arm_r'])+np.linalg.norm(e.P['hand_r']-e.E['r'])-.08
            direction=target-shoulder
            if np.linalg.norm(direction)>reach:target=shoulder+a.retarget.unit(direction)*reach
            a.retarget.solve_ik(p,'arm_r','forearm_r','hand_r',e.E['r'],target,np.array([.8,-.4,.3]),q)
        heroes[i]=p
        if i%60==0:print('R18 supported pose',i,flush=True)
    # A directed cinematic trajectory still obeys constant downward acceleration.
    # The landing pose is lower than takeoff, so this is a ballistic arc between
    # the actual hip heights, not a sine-shaped floating translation.
    first,last=303,366;h0=hips[first,1];h1=(world(heroes[last],roots[last],'leg_l')[1]+world(heroes[last],roots[last],'leg_r')[1])/2
    for i in range(first,last+1):
        u=(i-first)/(last-first);target=h0+(h1-h0)*u+4*20*u*(1-u)
        now=(world(heroes[i],roots[i],'leg_l')[1]+world(heroes[i],roots[i],'leg_r')[1])/2
        shift(heroes[i],[0,target-now,0])
    # Once a landing surface is reached, contact brakes the free-flight arc.
    # A short upper envelope also protects the interpolated frames at contact.
    from scipy.ndimage import maximum_filter1d
    correction=[]
    for i in range(345,367):
        correction.append(max(0,.03-a.surface.floor(heroes[i],f.PARTS)*U-roots[i,1]))
    correction=maximum_filter1d(correction,size=3)
    for i,dy in zip(range(345,367),correction):shift(heroes[i],[0,dy,0])
    # Sachiel's old fallen legs hung above the EVA's shoulders. Spread the
    # feet to supported positions on either side of its pelvis before the pin.
    angel_normals={s:None for s in ('l','r')}
    for i in range(303,483):
        t=i/30;weight=smooth(t,10.3,11.35)
        if weight<=0:continue
        original=angels[i];p=a.clone(original,True);root=np.array(data['angel']['root_blocks'][i])
        for s,sign in (('l',-1),('r',1)):
            q=R.from_euler('y',-sign*np.pi/3);feet=a.actors['grab_b',True].feet[s]
            goal=np.array([sign*24,-q.apply(feet)[:,1].min()*U+.03,62.])
            hint=np.array([sign*18,8,64.])
            angel_normals[s],_=leg(p,s,(goal-root)/U,(hint-root)/U,q,angel_normals[s])
        p=a.mix_pose(original,p,weight,True)
        for s,sign in (('l',-1),('r',1)):
            q=b.qmix(R.from_matrix(original.matrix('foot_'+s)[:3,:3]),R.from_euler('y',-sign*np.pi/3),weight)
            p.setq('foot_'+s,R.from_matrix(p.parent('foot_'+s)[:3,:3]).inv()*q)
        low=p.skin()[:,1].min()*U+root[1]
        if low<.02:data['angel']['root_blocks'][i][1]+=.02-low
        angels[i]=p
    # The kick transfers an immediate horizontal impulse, followed by braking.
    # Keep the authored kick contact and final ground position exactly fixed.
    ar=np.array(data['angel']['root_blocks']);first,last=276,321
    for i in range(first,last+1):
        u=(i-first)/(last-first);ar[i]=b.mix(ar[first],ar[last],1-(1-u)**2)
    data['angel']['root_blocks']=ar.tolist()
    cameras=copy.deepcopy(data['camera']);floors=f.recompute(data,heroes,angels);data['camera']=cameras
    data['reference']='R18 supported TV battle: anatomically directed knee planes, paired planted knees and toes, sequential rise steps, ballistic pounce. R15 rigid Sachiel retained.'
    target=OUT/'candidate_v13.json';target.write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
    (OUT/'author_metrics.json').write_text(json.dumps({'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'knees':{k:v.tolist() for k,v in knees.items()},'ankles':{k:v.tolist() for k,v in ankles.items()},'floor_samples':floors,'contacts':records},indent=2),encoding='utf8')
    print('Candidate only:',target,flush=True)

if __name__=='__main__':author()
