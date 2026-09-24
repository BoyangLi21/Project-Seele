"""Rejected wrist-path experiment, retained only for comparison (2026-09-25).

The active author is author_combat_performance_r36.py.

The ground-strike paths below are newly authored rather than renamed earlier
ground attacks. Unchanged aerial, roar and recovery assets retain their own
provenance. Coordinates are model pixels, with -Z forward. A phrase has a loaded
pose, a passing contact pose and a braking pose; cubic tangents carry momentum
through contact instead of easing to zero.
"""
from pathlib import Path
import json, argparse, copy
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation as R, RotationSpline
import author_combat_r35 as riglib
import anatomical_hinge_r35 as hinge

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/combat_direction_r36/profiles'

def spline(t, keys):
    return PchipInterpolator([k[0] for k in keys],np.asarray([k[1] for k in keys],float),axis=0)(np.clip(t,keys[0][0],keys[-1][0]))

def ease(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)

class Actor(riglib.Actor):
    def __init__(self,key):
        super().__init__(key)
        self.poles={}
        h=self.height
        # The uncommitted stance is tall and asymmetric, not a permanent squat.
        for s,sign in [('l',-1),('r',1)]:
            self.foot_base[s]=np.array([sign*h*(.115 if self.angel else .102),-self.feet[s][:,1].min(),sign*h*.055])

    def guard_hands(self):
        h=self.height
        if self.angel:return {'l':h*np.array([-.285,.49,-.095]),'r':h*np.array([.26,.54,-.11])}
        return {'l':h*np.array([-.20,.73,-.19]),'r':h*np.array([.215,.62,-.105])}

    def blocked(self,body,hands,feet,foot_angles=None,open_hand=0,attached=()):
        # Body: lean, pelvis twist, chest twist, side lean, compression, lateral, forward.
        lean,hip,chest,roll,compression,lateral,forward=body;h=self.height
        p=self.pose(lean,hip,chest,roll,compression*h,lateral*h)
        p.setp('root',p.p['root']+np.array([0,0,forward*h]))
        orientations={s:R.from_euler('xyz',foot_angles.get(s,[0,0,0]),degrees=True) if foot_angles else R.identity() for s in ('l','r')}
        goals={s:np.asarray(feet[s],float).copy() for s in ('l','r')}
        for s in ('l','r'):
            goals[s][1]=-orientations[s].apply(self.feet[s])[:,1].min()+feet[s][1]-self.foot_base[s][1]
        self.solve_feet(p,goals,orientations)
        for s,sign in [('l',-1),('r',1)]:
            target=np.asarray(hands[s]);shoulder=p.point('arm_'+s)
            if s in attached:target=(p.matrix('torso_upper')@np.r_[target,1])[:3]
            # Poles follow the shoulder girdle. Fixed world poles inverted the
            # upper arm when the chest crossed its centre line.
            pole=R.from_euler('y',hip+chest,degrees=True).apply([sign*.85,-.55,.55])
            vector=target-shoulder;direction=hinge.unit(vector)
            reach=np.linalg.norm(self.elbows[s]-self.P['arm_'+s])+np.linalg.norm(self.P['hand_'+s]-self.elbows[s])
            target=shoulder+direction*np.clip(np.linalg.norm(vector),reach*.47,reach*.965)
            wanted=pole-direction*np.dot(pole,direction);confidence=np.linalg.norm(wanted);wanted=hinge.unit(wanted)
            if s in self.poles:
                old_direction,old_pole,old_angle=self.poles[s]
                transported=riglib.base.rt.eva.arc(old_direction,direction).apply(old_pole)
                transported=hinge.unit(transported-direction*np.dot(transported,direction))
                twist=np.arctan2(direction@np.cross(transported,wanted),np.clip(transported@wanted,-1,1))
                # Parallel-transport the bend plane across straight-arm/pole
                # singularities. A pole cannot teleport across the upper arm.
                pole=R.from_rotvec(direction*np.clip(twist,-.105,.105)*min(1,confidence)).apply(transported)
            else:pole=wanted
            u=self.elbows[s]-self.P['arm_'+s];v=self.P['hand_'+s]-self.elbows[s];axis=np.array([1.,0,0])
            parallel=axis*(axis@v);perpendicular=v-parallel;aa=u@perpendicular;bb=u@np.cross(axis,v);cc=u@parallel
            neutral,_=hinge.limits(u,v,axis);distance=np.linalg.norm(target-shoulder)
            flex=neutral+np.arccos(np.clip(((distance*distance-u@u-v@v)/2-cc)/max(np.hypot(aa,bb),1e-8),-1,1))
            if s in self.poles:flex=float(np.clip(flex,old_angle-.12,old_angle+.12))
            distance=np.sqrt(max(0,u@u+v@v+2*(aa*np.cos(flex)+bb*np.sin(flex)+cc)))
            target=shoulder+direction*distance
            self.poles[s]=(direction.copy(),pole.copy(),float(flex))
            hinge.solve(p,self.P,'arm_'+s,'forearm_'+s,'hand_'+s,self.elbows[s],target,pole,[1,0,0])
            p.setq('hand_'+s,R.identity())
        if not self.angel:
            for n in p.q:
                if n.startswith('finger_'):
                    if '_axis_' in n:
                        spec=self.rig.rig[n]
                        p.setq(n,R.from_euler('xyz',np.asarray(spec.get('rotation',[0,0,0]))*[-1,-1,1],degrees=True))
                    else:
                        thumb='thumb' in n
                        angle=(24 if thumb else 38) if '_tip_' in n else (12 if thumb else 24) if '_distal_' in n else (35 if thumb else 62)
                        p.setq(n,R.from_euler('z',angle*(1-open_hand*.65),degrees=True))
        return p

    def guard(self):
        self.poles={}
        frames=[]
        for t in np.linspace(0,1,81):
            wave=np.sin(t*2*np.pi)
            b=[-7 if self.angel else -10,0,0,wave*.7,.018+wave*.0015,0,0]
            p=self.blocked(b,self.guard_hands(),self.foot_base,attached=('l','r'))
            frames.append(self.encode(p,[True,True]))
        return self.pack(frames,'l',.45,np.zeros((len(frames),3)),3.6,'watch')

    def pack(self,frames,lead,contact,travel,duration,intent):
        return dict(duration_seconds=duration,loop=intent=='watch',frames=frames,leading_side=lead,contact_phase=contact,
                    trajectory_m=np.asarray(travel).tolist(),support='authored_steps',stance_locked=False,
                    step_contacts=[f['foot_contact'] for f in frames],intent=intent)

    def attack(self,label,feral=False,low=False):
        self.poles={}
        h=self.height;lead='r' if label in ('cross','heavy','stomp') else 'l';other='r' if lead=='l' else 'l'
        sign=-1 if lead=='l' else 1;g=self.guard_hands();start=g[lead]/h;counter=g[other]/h
        # Seven independently timed body controls. Contact stays at .45 so the
        # existing server input/damage windows keep their meaning.
        contact=.55 if label=='heavy' else .45
        load=.30 if label=='heavy' else .25;passage=contact+.105;brake=.76
        times=[0,load,contact,passage,brake,1]
        rest=[-7 if self.angel else -10,0,0,0,.018,0,0]
        if self.angel:
            specs={
              'jab': ([-.34,.67,.04],[-.045,.76,-.43],[.19,.65,-.37],[-16,-15,-24,-7,.028,.02,-.025],.095,'long_backhand'),
              'cross': ([.28,.73,.16],[.10,.78,-.42],[.10,.76,-.45],[-12,12,18,3,.020,-.01,-.032],.085,'forearm_lance'),
              'hook': ([-.44,.58,.07],[-.10,.65,-.45],[.29,.55,-.31],[-23,18,35,-13,.042,.025,-.035],.12,'low_sweep'),
              'heavy': ([.28,1.08,.08],[.12,.67,-.44],[.15,.39,-.37],[-34,-8,-12,12,.09,0,-.045],.12,'one_arm_crush'),
              'shove': ([-.23,.70,-.015],[-.12,.72,-.43],[-.13,.68,-.45],[-24,0,0,0,.038,0,-.045],.13,'two_hand_drive'),
              'stomp': ([.34,.72,-.03],[.31,.68,-.17],[.31,.60,-.18],[-19,0,0,-8,.04,-.025,-.02],.06,'stamp')}
        else:
            specs={
              'jab': ([-.33,.84,.10],[-.025,.78,-.47],[.22,.65,-.36],[-25,18,24,-11,.05,.018,-.025],.125,'stepping_forearm'),
              'cross': ([.34,.88,.15],[.005,.79,-.47],[-.29,.62,-.34],[-29,-22,-31,12,.06,-.022,-.02],.055,'reverse_body_drive'),
              'hook': ([-.31,1.05,.055],[.015,.74,-.45],[.20,.41,-.40],[-38,16,20,-14,.10,.014,-.035],.095,'diagonal_hammer'),
              'heavy': ([.19,1.15,.065],[.12,.68,-.45],[.15,.36,-.37],[-43,0,0,0,.13,0,-.045],.12,'two_arm_breaker'),
              'shove': ([-.22,.75,-.025],[-.105,.71,-.44],[-.13,.66,-.44],[-30,0,0,0,.065,0,-.03],.1,'drive'),
              'stomp': ([.31,.87,.02],[.31,.74,-.15],[.31,.61,-.10],[-22,0,0,9,.04,-.025,-.02],.06,'stamp')}
        chamber,hit,follow,drive,distance,intent=specs[label]
        if not self.angel and not feral and label in ('cross','hook'):
            distance=0
        if feral:
            chamber=[sign*.39,.92,.13];hit=[sign*.05,.72,-.49];follow=[-sign*.25,.39,-.40]
            drive=[-43,-sign*20,-sign*23,sign*15,.13,-sign*.025,-.05];distance=.17;intent='feral_rake'
        if low:
            chamber=[sign*.26,.99,.03];hit=[sign*.09,.30,-.40];follow=[-sign*.025,.20,-.34]
            drive=[-51,-sign*12,-sign*13,sign*8,.18,0,-.035];distance=.055;intent='grounded_downstrike'
        loaded=[-3 if not feral else -22,sign*15,sign*26,-sign*6,.045 if label!='heavy' else .085,-sign*.025,.025]
        overshoot=np.array(drive,float);overshoot[0]-=5;overshoot[4]+=.012
        settle=np.array(rest,float);settle[1]=drive[1]*.28;settle[2]=drive[2]*.28;settle[4]=.03
        bodies=list(zip(times,[rest,loaded,drive,overshoot,settle,rest]))
        # The strike passes its contact pose with nonzero velocity and then
        # brakes below/across the ribs. A separate release clip handles idle.
        hands=list(zip(times,[start,chamber,hit,follow,np.asarray(start)+[-sign*.045,-.06,.04],start]))
        if label in ('heavy','hook') or low:
            hands.insert(1,(load*.45,[sign*.42,.87,-.08]))
        else:
            hands.insert(2,(load+.07,[sign*.42,.83,-.13]))
        if self.angel and label=='cross':
            # Palm holds the axis while the bone lance extends and retracts.
            hands=[(0,start),(.29,chamber),(.45,hit),(.65,follow),(.85,start+np.array([0,-.05,.05])),(1,start)]
        def body_at(t):
            b=spline(t,bodies);b[1]=spline(min(1,t+.025),bodies)[1];b[2]=spline(max(0,t-.018),bodies)[2];return b
        def shoulder_at(t,side):
            b=body_at(t);p=self.pose(b[0],b[1],b[2],b[3],b[4]*h,b[5]*h);p.setp('root',p.p['root']+[0,0,b[6]*h]);return p.point('arm_'+side)
        # Interpolate the strike around the shoulder on a continuous spherical
        # path. Cartesian chords from high chambers to low targets cut through
        # the shoulder itself, especially on the broad UN rig.
        swing_curves={}
        def swing_path(t,keys,side):
            if side not in swing_curves:
                times=[k[0] for k in keys];vectors=[np.asarray(v)*h-shoulder_at(at,side) for at,v in keys];directions=[hinge.unit(v) for v in vectors]
                rotations=[riglib.base.rt.eva.arc([0,0,-1],directions[0])]
                for previous,d in zip(directions,directions[1:]):rotations.append(riglib.base.rt.eva.arc(previous,d)*rotations[-1])
                swing_curves[side]=(RotationSpline(times,R.concatenate(rotations)),PchipInterpolator(times,[np.linalg.norm(v) for v in vectors]))
            rotation,radius=swing_curves[side]
            return shoulder_at(t,side)+rotation(t).apply([0,0,-1])*float(radius(t))
        frames=[];travel=[]
        for t in np.linspace(0,1,101):
            body=body_at(t)
            root=float(spline(t,[(0,0),(.15,0),(contact,distance*.82),(brake,distance),(1,distance)]))*h
            feet={};contacts=[];angles={}
            for side in ('l','r'):
                # Only the committed lead foot advances. Rear catches once,
                # after the strike; it does not flick between every key pose.
                a,b=(.06,contact-.06) if side==lead else (.54,.74)
                u=float(np.clip((t-a)/(b-a),0,1));step=distance*h*ease(u)
                lift=np.sin(np.pi*u)**2*h*(.045 if side==lead else .025)
                if distance==0:
                    u=0;step=0;lift=0
                if label=='stomp' and side==lead:
                    u=float(np.clip((t-.10)/(.48-.10),0,1));lift=np.sin(np.pi*u)*h*.18;step=distance*h*ease(u)
                feet[side]=self.foot_base[side]+[0,lift,root-step]
                plant=u<=.0001 or u>=.9999;contacts.append(plant)
                heel=0 if side==lead else float(spline(t,[(0,0),(load,-12),(contact,-22),(.66,-12),(.78,0),(1,0)]))
                angles[side]=[heel,(-sign*9 if side!=lead else -sign*4)*np.sin(np.pi*t)**2,0]
            palms={lead:swing_path(t,hands,lead)}
            if label=='shove' or label=='heavy' and not self.angel:
                palms[other]=swing_path(t,[(at,np.asarray(v)*[-1,1,1]) for at,v in hands],other)
            elif self.angel and label=='cross':
                palms[other]=spline(t,[(0,counter),(load,[-.24,.77,-.28]),(contact,[-.26,.78,-.27]),(passage,[-.30,.70,-.18]),(1,counter)])*h
            else:
                palms[other]=spline(t,[(0,counter),(load,counter+[sign*.025,.06,-.025]),(contact,[ -sign*.25,.57,.085]),(passage,[-sign*.30,.48,.055]),(1,counter)])*h
            attached=() if label=='shove' or label=='heavy' and not self.angel else (other,)
            p=self.blocked(body,palms,feet,angles,1 if feral else 0,attached)
            frames.append(self.encode(p,contacts));travel.append([0,0,-root/112])
        result=self.pack(frames,lead,contact,travel,1.55 if label=='heavy' else 1.15,intent)
        result['both_hands']=label=='shove' or label=='heavy' and not self.angel
        result['release_phase']=.74
        return result,{}

    def walk(self,name):
        self.poles={}
        h=self.height;direction=np.array({'advance':[0,0,-1],'retreat':[0,0,1],'left':[-1,0,0],'right':[1,0,0]}[name],float)
        stride=h*(.55 if self.angel else .48);frames=[]
        for t in np.linspace(0,1,101):
            feet={};contacts=[];angles={}
            for side,offset in [('l',0),('r',.5)]:
                phase=(t+offset)%1
                if phase<.62:
                    pos=.31-phase;lift=0;plant=True
                    roll=float(spline(phase,[(0,8),(.09,0),(.40,0),(.62,-16)]))
                else:
                    u=(phase-.62)/.38;pos=-.31+.62*ease(u);lift=np.sin(np.pi*u)*h*.055;plant=False;roll=-16+24*ease(u)
                feet[side]=self.foot_base[side]+direction*pos*stride+[0,lift,0];contacts.append(plant)
                angles[side]=[roll if name in ('advance','retreat') else 0,0,0]
            weight=np.sin(t*2*np.pi)
            body=[-9 if self.angel else -14,weight*6,-weight*4,weight*-1.8,.025+(1-np.cos(t*4*np.pi))*.004,weight*.012,0]
            hands=self.guard_hands()
            for s,sign in [('l',1),('r',-1)]:hands[s]=hands[s]+[0,0,weight*h*.055*sign]
            p=self.blocked(body,hands,feet,angles,attached=('l','r'));frames.append(self.encode(p,contacts))
        frames[-1]=copy.deepcopy(frames[0]);c=self.pack(frames,'l',.45,np.zeros((len(frames),3)),1.8,'walk');c.update(loop=True,stride_blocks=float(stride*5/16));return c

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--rig');args=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    keys=[int(args.rig) if args.rig!='sachiel' else args.rig] if args.rig else [0,1,2,3,4,'sachiel']
    for key in keys:
        actor=Actor(key);name='sachiel_gameplay_r32.json' if actor.angel else f'eva_gameplay_r32_{key}.json'
        data=json.loads((ROOT/'artifacts/combat_rebuild_r35/profiles'/name).read_text())
        for label in ('jab','cross','hook','heavy','shove','stomp'):data['clips']['r32_'+label]=actor.attack(label)[0]
        data['clips']['r32_guard']=actor.guard()
        for name2 in ('advance','retreat','left','right'):data['clips']['r32_'+name2]=actor.walk(name2)
        if not actor.angel:
            for side,label in [('l','hook'),('r','cross')]:data['clips']['r32_berserk_'+side]=actor.attack(label,True)[0]
            for label in ('jab','cross','hook','heavy'):data['clips']['r32_low_'+label]=actor.attack(label,low=True)[0]
        data.update(combat_foundation=36,choreography='separate_character_phrases_r36')
        for n,c in data['clips'].items():
            if 'intent' in c:data['sources'][n[4:]]={'source':'Original R36 pose blocking with passing contact, support timing and separate character direction','license':'MIT','intent':c['intent']}
        (OUT/name).write_text(json.dumps(data,separators=(',',':')));print('R36',key,flush=True)

if __name__=='__main__':
    raise SystemExit('This wrist-path candidate was rejected. Use author_combat_performance_r36.py.')
