"""Author continuous full-body giant combat phrases and their support schedule.

Original choreography: compression -> stepping drive -> contact -> follow-through
-> recovery. References are recorded in docs/COMBAT_DIRECTION_R34.md. No pose is
scaled, and the same exported skeleton is consumed by skinning and hit sweeps.
"""
from pathlib import Path
import copy, json
import numpy as np
from scipy.spatial.transform import Rotation as R
import author_gameplay_motion_r32 as common
import retarget_human_r12 as rt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/combat_direction_r34/profiles'

def smooth(t):
    t=np.clip(t,0.,1.);return t*t*t*(10+t*(-15+6*t))

def curve(t,keys):
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t<=b:return np.asarray(x)*(1-smooth((t-a)/(b-a)))+np.asarray(y)*smooth((t-a)/(b-a))
    return np.asarray(keys[-1][1],float)

def direction_arc(a,b,t,side):
    a=rt.unit(a);b=rt.unit(b);dot=np.clip(a@b,-1,1)
    if dot<-.72:
        # A fist travelling from behind the shoulder to the front goes around
        # the shoulder, never through its centre (the IK singularity).
        normal=rt.unit(a-b);pole=np.array([side,.35,-.25]);middle=rt.unit(pole-normal*(pole@normal),(0,1,0))
        if middle@(a+b)<0:middle=-middle
        return direction_arc(a,middle,t*2,side) if t<.5 else direction_arc(middle,b,t*2-1,side)
    angle=np.arccos(dot)
    return rt.unit(a*(1-t)+b*t) if angle<1e-4 else rt.unit((np.sin((1-t)*angle)*a+np.sin(t*angle)*b)/np.sin(angle))

class Actor:
    def __init__(self,key):
        self.angel=key=='sachiel';self.key=key
        if not self.angel:common.configure(key)
        self.rig=rt.battle.ANGEL if self.angel else rt.eva
        self.P=self.rig.P;self.height=float(self.P['head'][1]);self.feet={}
        self.knees={s:self.P['shin_'+s] if self.angel else rt.eva.K[s] for s in ('l','r')}
        self.elbows={s:self.P['forearm_'+s] if self.angel else rt.eva.E[s] for s in ('l','r')}
        for s in ('l','r'):
            if self.angel:
                i=self.rig.names.index('foot_'+s);w=np.sum(np.where(self.rig.ids==i,self.rig.weights,0),axis=1)
                self.feet[s]=self.rig.vertices[w>.6]-self.P['foot_'+s]
            else:self.feet[s]=rt.eva.feet[s]
        self.width=max(abs(self.P['foot_l'][0]),self.height*(.12 if self.angel else .115))
        self.foot_base={s:np.array([(-1 if s=='l' else 1)*self.width,-self.feet[s][:,1].min(),(-1 if s=='l' else 1)*self.height*.055]) for s in ('l','r')}
        self.names=self.rig.names if self.angel else common.NAMES
        self.axes={}

    def anatomical_ik(self,p,a,b,c,joint,target,pole):
        """Keep one continuous hinge plane, including at full extension.

        A shortest-arc rotation per segment has an undefined twist near 180
        degrees. Construct both limb frames from their common hinge instead.
        """
        shoulder=p.point(a);u=joint-self.P[a];v=self.P[c]-joint
        la,lb=np.linalg.norm(u),np.linalg.norm(v);direction=rt.unit(np.asarray(target)-shoulder)
        length=np.clip(np.linalg.norm(np.asarray(target)-shoulder),abs(la-lb)+.01,(la+lb)*.987)
        target=shoulder+direction*length
        bend=rt.unit(np.asarray(pole)-direction*np.dot(pole,direction),(0,0,1))
        axis=rt.unit(-np.cross(direction,bend),(1,0,0))
        previous=self.axes.get(a)
        if previous is not None:
            previous=rt.unit(previous-direction*np.dot(previous,direction),axis)
            angle=np.arctan2(np.dot(direction,np.cross(previous,axis)),np.dot(previous,axis))
            axis=R.from_rotvec(direction*np.clip(angle,-.13,.13)).apply(previous)
            bend=rt.unit(np.cross(direction,axis))
        self.axes[a]=axis.copy()
        rest=rt.unit(np.cross(u,v),(1,0,0))
        along=(la*la-lb*lb+length*length)/(2*length);height=np.sqrt(max(0,la*la-along*along))
        middle=shoulder+direction*along+bend*height
        def orient(n,original,wanted):
            world=R.from_matrix(rt.axes(wanted,axis)@rt.axes(original,rest).T)
            p.setq(n,R.from_matrix(p.parent(n)[:3,:3]).inv()*world)
        orient(a,u,middle-shoulder);orient(b,v,target-middle)
        delta=joint-self.P[b];p.setp(b,delta-p.q[b].apply(delta))
        return target

    def pose(self,lean=-12,yaw=0,chest_yaw=0,roll=0,drop=9,shift=0):
        p=self.rig.pose() if self.angel else rt.battle.hero_copy(rt.eva.idle)
        for n in p.q:p.setq(n,R.identity());p.setp(n,[0,0,0])
        p.setp('root',[shift,-drop,0])
        p.setq('torso_lower',R.from_euler('xyz',[lean*.32,yaw,roll*.35],degrees=True))
        p.setq('torso_upper',R.from_euler('xyz',[lean*.68,chest_yaw,roll*.65],degrees=True))
        # Partial counter-rotation retains the physical neck follow-through.
        head=R.from_euler('xyz',[-lean*.48,-(yaw+chest_yaw)*.48,-roll*.30],degrees=True)
        p.setq('head',head)
        return p

    def solve_feet(self,p,goals,orientations=None):
        orientations=orientations or {s:R.identity() for s in ('l','r')}
        for _ in range(8):
            for s in ('l','r'):
                hip=p.point('leg_'+s);reach=np.linalg.norm(self.knees[s]-self.P['leg_'+s])+np.linalg.norm(self.P['foot_'+s]-self.knees[s])
                delta=hip-goals[s];length=np.linalg.norm(delta)
                if length>reach*.991:p.setp('root',p.p['root']-delta*(1-reach*.991/length))
        for s in ('l','r'):
            rt.solve_ik(p,'leg_'+s,'shin_'+s,'foot_'+s,self.knees[s],goals[s],np.array([0,0,-1.]),orientations[s])

    def solve_hands(self,p,goals):
        for s in ('l','r'):
            sign=-1 if s=='l' else 1
            # A fist follows the forearm, with a stable wrist roll. Never aim the
            # wrist independently through a backwards elbow configuration.
            shoulder=p.point('arm_'+s);target=np.array(goals[s],float)
            self.anatomical_ik(p,'arm_'+s,'forearm_'+s,'hand_'+s,self.elbows[s],target,np.array([sign*.9,-.65,.55]))
            p.setq('hand_'+s,R.identity())
        if not self.angel:
            for n in p.q:
                if n.startswith('finger_'):p.setq(n,rt.battle.fist.q.get(n,p.q[n]))

    def encode(self,p,contacts):
        f=p.encode() if self.angel else rt.eva.encode(p,contacts=contacts,bone_names=common.NAMES)
        f['foot_contact']=list(contacts);return f

    def guard_hands(self):
        h=self.height
        return {'l':np.array([-.16*h,.75*h,-.22*h]),'r':np.array([.17*h,.70*h,-.15*h])} if not self.angel else {'l':np.array([-.26*h,.70*h,-.18*h]),'r':np.array([.26*h,.72*h,-.20*h])}

    def attack(self,label,feral=False):
        self.axes={}
        h=self.height;is_heavy=label=='heavy';lead='r' if label in ('cross','heavy','stomp') else 'l'
        s=-1 if lead=='l' else 1;other='l' if lead=='r' else 'r'
        distance={'jab':.115,'cross':.14,'hook':.11,'heavy':.17,'shove':.115,'stomp':.08}[label]*h
        if feral:distance*=1.45
        chamber=.24 if not is_heavy else .35;contact=.45 if not is_heavy else .55
        frames=[];travel=[];supports=[];stats=[]
        references={}
        def body_at(t):
            recoil=float(curve(t,[(0,0),(chamber,1),(contact,0),(.64,-.15),(1,0)]))
            finish=float(curve(t,[(0,0),(chamber,0),(contact,1),(.67,.75),(1,0)]))
            y=s*(recoil*22-finish*27);cy=s*(recoil*22-finish*30)
            lean=-12+recoil*10-finish*(24 if is_heavy else 9)
            drop=9+recoil*(12 if is_heavy else 5)+finish*(16 if is_heavy else 3)
            if self.angel:y*=.72;cy*=.72
            if feral:lean-=12+recoil*10;drop+=10+recoil*8
            return self.pose(lean,y,cy,s*finish*7,drop,-s*recoil*3)
        def hand_at(p,t,keys,side):
            word='arm_'+side;radius=np.linalg.norm(self.elbows[side]-self.P[word])+np.linalg.norm(self.P['hand_'+side]-self.elbows[side])
            for (ta,va),(tb,vb) in zip(keys,keys[1:]):
                if t<=tb:
                    for kt in (ta,tb):
                        if (kt,word) not in references:references[kt,word]=body_at(kt).point(word)
                    a=np.asarray(va)-references[ta,word];b=np.asarray(vb)-references[tb,word]
                    weight=smooth((t-ta)/(tb-ta));length=np.clip((1-weight)*np.linalg.norm(a)+weight*np.linalg.norm(b),radius*.42,radius*.985)
                    return p.point(word)+direction_arc(a,b,weight,-1 if side=='l' else 1)*length
            return np.asarray(keys[-1][1])
        for t in np.linspace(0,1,91):
            drive=float(curve(t,[(0,0),(.08,0),(contact,distance*.9),(.73,distance),(1,distance)]))
            recoil=float(curve(t,[(0,0),(chamber,1),(contact,0),(.64,-.15),(1,0)]))
            finish=float(curve(t,[(0,0),(chamber,0),(contact,1),(.67,.75),(1,0)]))
            body_yaw=s*(recoil*22-finish*27)
            chest_yaw=s*(recoil*22-finish*30)
            lean=-12+recoil*10-finish*(24 if is_heavy else 9)
            drop=9+recoil*(12 if is_heavy else 5)+finish*(16 if is_heavy else 3)
            if self.angel:body_yaw*=.72;chest_yaw*=.72
            if feral:lean-=12+recoil*10;drop+=10+recoil*8
            p=self.pose(lean,body_yaw,chest_yaw,s*finish*7,drop,-s*recoil*3)
            goals={};contacts=[]
            for side in ('l','r'):
                a,b=(.06,contact-.04) if side==lead else (.58,.92)
                u=float(np.clip((t-a)/(b-a),0,1));lift=np.sin(np.pi*u)*h*(.040 if side==lead else .032)
                step=distance*smooth(u)
                goals[side]=self.foot_base[side]+np.array([0,lift,drive-step])
                if label=='stomp' and side==lead:
                    lift=h*.19*np.sin(np.pi*np.clip((t-.08)/(.49-.08),0,1))
                    goals[side][1]=self.foot_base[side][1]+lift
                contacts.append(bool(u<=.001 or u>=.999))
            self.solve_feet(p,goals)
            hands=self.guard_hands();start=hands[lead].copy()
            if label=='jab':
                keys=[(0,start),(chamber,[-.34*h,.86*h,.07*h]),(contact,[.01*h,.82*h,-.43*h]),(.63,[.22*h,.69*h,-.34*h]),(1,start)]
            elif label=='cross':
                keys=[(0,start),(chamber,[.31*h,.81*h,.15*h]),(contact,[-.025*h,.79*h,-.47*h]),(.65,[-.18*h,.73*h,-.40*h]),(1,start)]
            elif label=='hook':
                keys=[(0,start),(chamber,[-.42*h,.86*h,.015*h]),(.35,[-.37*h,.87*h,-.20*h]),(contact,[0,.82*h,-.46*h]),(.65,[.30*h,.68*h,-.28*h]),(1,start)]
            elif label=='heavy':
                keys=[(0,start),(chamber,[.12*h,1.14*h,.06*h]),(.45,[.09*h,1.11*h,-.22*h]),(contact,[.03*h,.76*h,-.47*h]),(.68,[.10*h,.44*h,-.40*h]),(1,start)]
            elif label=='shove':
                keys=[(0,start),(chamber,[-.23*h,.81*h,-.03*h]),(contact,[-.08*h,.76*h,-.44*h]),(.64,[-.10*h,.69*h,-.41*h]),(1,start)]
            else:keys=[(0,start),(.25,[s*.30*h,.87*h,-.10*h]),(.5,[s*.30*h,.74*h,-.24*h]),(1,start)]
            hands[lead]=hand_at(p,t,keys,lead)
            if label in ('heavy','shove'):
                hands[other]=hand_at(p,t,[(kt,np.asarray(v)*[-1,1,1]) for kt,v in keys],other)
            else:
                # Counterarm opens during compression and retracts behind the
                # ribs as the striking shoulder crosses the centre line.
                standby=hands[other].copy()
                counter=[(0,standby),(chamber,standby+[-s*.05*h,.035*h,0]),(contact,standby+[0,0,.14*h]),(.67,standby+[0,0,.10*h]),(1,standby)]
                hands[other]=hand_at(p,t,counter,other)
            self.solve_hands(p,hands)
            frames.append(self.encode(p,contacts));travel.append([0,0,-float(drive)/112]);supports.append(contacts)
            stats.append({side:p.point('hand_'+side).tolist() for side in ('l','r')})
        return {'duration_seconds':1.55 if is_heavy else 1.15,'loop':False,'frames':frames,'leading_side':lead,'contact_phase':contact,
                'trajectory_m':travel,'support':'authored_steps','stance_locked':False,'step_contacts':supports,'both_hands':label in ('heavy','shove')},stats

    def roar(self):
        self.axes={}
        frames=[];h=self.height
        for t in np.linspace(0,1,91):
            strain=float(curve(t,[(0,0),(.15,.35),(.28,1),(.78,.90),(1,0)]))
            p=self.pose(-12+strain*20,0,0,0,9+strain*7);p.setq('head',R.from_euler('x',strain*32,degrees=True))
            self.solve_feet(p,self.foot_base);hands=self.guard_hands()
            for side in ('l','r'):
                goal=np.array([(-1 if side=='l' else 1)*h*.26,h*.57,h*.025]);hands[side]=hands[side]*(1-strain)+goal*strain
            self.solve_hands(p,hands);frames.append(self.encode(p,[True,True]))
        return {'duration_seconds':3.5,'loop':False,'frames':frames,'leading_side':'l','contact_phase':.5,'trajectory_m':[[0,0,0]]*len(frames),'support':'feet'}

    def guard(self):
        self.axes={}
        frames=[]
        for t in np.linspace(0,1,61):
            breath=np.sin(t*2*np.pi)
            p=self.pose(-12-breath*.8,0,0,0,9+breath*.65)
            self.solve_feet(p,self.foot_base);self.solve_hands(p,self.guard_hands());frames.append(self.encode(p,[True,True]))
        return {'duration_seconds':3,'loop':True,'frames':frames,'leading_side':'l','contact_phase':.5,'trajectory_m':[[0,0,0]]*len(frames),'support':'feet'}

    def walk(self,name):
        self.axes={}
        h=self.height;direction=np.array({'advance':[0,0,-1],'retreat':[0,0,1],'left':[-1,0,0],'right':[1,0,0]}[name],float)
        stride=h*.48;frames=[]
        for t in np.linspace(0,1,81):
            goals={};contacts=[]
            for side in ('l','r'):
                phase=(t+(0 if side=='l' else .5))%1
                if phase<.60:
                    v=.30-phase;lift=0;plant=True
                else:
                    u=(phase-.60)/.40;v=-.30+smooth(u)*.60;lift=np.sin(np.pi*u)*h*.055;plant=False
                goals[side]=self.foot_base[side]+direction*v*stride+np.array([0,lift,0]);contacts.append(plant)
            bob=(1-np.cos(4*np.pi*t))*.9
            yaw=np.sin(2*np.pi*t)*5
            p=self.pose(-14,yaw,-yaw*.7,np.sin(2*np.pi*t)*2,9+bob)
            self.solve_feet(p,goals);hands=self.guard_hands()
            for side in ('l','r'):
                hands[side]=hands[side]+np.array([0,0,np.sin(2*np.pi*t+(0 if side=='l' else np.pi))*h*.045])
            self.solve_hands(p,hands);frames.append(self.encode(p,contacts))
        frames[-1]=copy.deepcopy(frames[0])
        return {'duration_seconds':1.6,'loop':True,'frames':frames,'leading_side':'l','contact_phase':.5,'trajectory_m':[[0,0,0]]*len(frames),'stride_blocks':float(stride*5/16),'support':'feet'}

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--rig');args=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    keys=[int(args.rig) if args.rig!='sachiel' else args.rig] if args.rig else [0,1,2,3,4,'sachiel'];report={}
    for key in keys:
        actor=Actor(key);name='sachiel_gameplay_r32.json' if actor.angel else f'eva_gameplay_r32_{key}.json'
        data=json.loads((ROOT/'artifacts/combat_foundation_r33/profiles'/name).read_text());stats={}
        for label in ('jab','cross','hook','heavy','shove','stomp'):
            data['clips']['r32_'+label],stats[label]=actor.attack(label)
            data['sources'][label]={'source':'Original TV-directed R34 choreography; analytic anatomical IK and staged foot contacts','license':'MIT','reference':'docs/COMBAT_DIRECTION_R34.md'}
        data['clips']['r32_guard']=actor.guard()
        if not actor.angel:
            data['clips']['r32_berserk_roar']=actor.roar()
            for side,label in [('l','hook'),('r','cross')]:data['clips']['r32_berserk_'+side]=actor.attack(label,feral=True)[0]
        for name2 in ('advance','retreat','left','right'):data['clips']['r32_'+name2]=actor.walk(name2)
        for name2 in ['guard','advance','retreat','left','right']+([] if actor.angel else ['berserk_l','berserk_r','berserk_roar']):
            data['sources'][name2]={'source':'Original R34 choreography with continuous anatomical hinge planes','license':'MIT','reference':'docs/COMBAT_DIRECTION_R34.md'}
        data['combat_foundation']=34;data['choreography']='tv_directed_full_body_r34'
        (OUT/name).write_text(json.dumps(data,separators=(',',':')))
        report[str(key)]={label:{'hand_excursion_blocks':float(np.linalg.norm(np.ptp(np.array([f[clip['leading_side']] for f in stats[label]]),axis=0))*5/16),'travel_blocks':abs(clip['trajectory_m'][-1][2])*35} for label in stats for clip in [data['clips']['r32_'+label]]}
        print(key,report[str(key)],flush=True)
    (OUT.parent/'authored_phrases.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':main()
