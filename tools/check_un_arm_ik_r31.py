"""Independent float32 FK/IK perturbation audit of the measured UN elbow plane.

Reads production code and rigs; does not compile, render, or modify them.
"""
from pathlib import Path
import copy,hashlib,json,math
import numpy as np
from scipy.spatial.transform import Rotation as R
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r31/ik_review';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'src/main/java/com/projectseele/client/render/EvaRigTransforms.java';source_sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest();body=json.loads((ROOT/'run/projectseele-local-maps/eva_body_r31_review.json').read_text());F=np.float32
def normal(v):return np.asarray(v,dtype=F)/F(np.linalg.norm(v))
def frame(direction,axis):
    y=normal(direction);x=normal(axis-y*np.dot(axis,y));return np.stack((x,y,np.cross(x,y)),axis=1).astype(F)
def angle(a,b):return math.degrees(R.from_matrix(a.astype(float).T@b.astype(float)).magnitude())
class Pose:
    def __init__(self,rig):
        self.rig=rig;self.P={n:(np.asarray(b['pivot'])*[-1,1,1]/16).astype(F) for n,b in rig.items()};self.q={n:R.from_euler('xyz',np.asarray(b.get('rotation',[0,0,0]))*[-1,-1,1],degrees=True).as_matrix().astype(F) for n,b in rig.items()};self.p={n:np.zeros(3,dtype=F) for n in rig};self.cache={}
    def matrix(self,n):
        if n not in self.cache:
            m=np.eye(4,dtype=F);m[:3,:3]=self.q[n];m[:3,3]=self.p[n]+self.P[n]-self.q[n]@self.P[n];parent=self.rig[n].get('parent');self.cache[n]=(self.matrix(parent)@m).astype(F) if parent else m
        return self.cache[n]
    def parent(self,n):return self.matrix(self.rig[n]['parent']) if self.rig[n].get('parent') else np.eye(4,dtype=F)
    def point(self,n,p):return (self.matrix(n)@np.r_[p,F(1)].astype(F))[:3]
    def dirty(self):self.cache={}
    def assign(self,n,q):self.q[n]=R.from_matrix(q.astype(float)).as_matrix().astype(F);self.dirty()
def sample(rig,kind):
    p=Pose(rig)
    if kind=='dormant':return p
    clip=body['motion']['clips']['unarmed_stance'];f=clip['frames'][round({'standing':0,'crouching':1/3,'prone':1}[kind]*(len(clip['frames'])-1))]
    for n,q in zip(body['motion']['bones'],f['rotation_wxyz']):p.q[n]=R.from_quat([-q[1],-q[2],q[3],q[0]]).as_matrix().astype(F)
    for n,v in f.get('bone_position_xyz',{}).items():p.p[n]=(np.asarray(v)*[-1,1,1]/16).astype(F)
    p.p['root']=(np.asarray(f['root_m'])*[-1,1,1]*7).astype(F);p.dirty();return p
def solve(p,side,target,hand_rotation,pole,anatomical):
    upper='arm_'+side;lower='forearm_'+side;wrist='wrist_'+side;hand='hand_'+side;centre=p.P['r30_elbow_socket_'+side];shoulder=p.point(upper,p.P[upper]);u=centre-p.P[upper];v=p.P[hand]-centre;a=F(np.linalg.norm(u));b=F(np.linalg.norm(v));delta=target-shoulder;length=F(np.linalg.norm(delta));direction=normal(delta) if length>1e-6 else np.array([0,-1,0],dtype=F)
    distance=F(max(abs(a-b)+.001,min(a+b-.001,length)));along=F((a*a-b*b+distance*distance)/(2*distance));height=F(math.sqrt(max(0,float(a*a-along*along))));bend=pole-direction*np.dot(pole,direction)
    if np.dot(bend,bend)<1e-8:bend=np.array([0,0,1],dtype=F)-direction*direction[2]
    bend=normal(bend);joint=shoulder+direction*along+bend*height;du=joint-shoulder;dl=target-joint;axis=np.cross(du,dl)
    if np.dot(axis,axis)<1e-8:axis=np.cross(du,bend)
    axis=normal(axis);rest_axis=normal(np.cross(u,v)) if anatomical else np.array([1,0,0],dtype=F);current_side=p.matrix(upper)[:3,:3]@rest_axis;dot=float(np.dot(axis,current_side))
    if dot<0:axis=-axis
    for n in (lower,wrist,hand):p.p[n][:]=0
    p.q[wrist]=np.eye(3,dtype=F);p.dirty()
    def orient(n,rest,wanted):
        world=frame(wanted,axis)@frame(rest,rest_axis).T;p.assign(n,p.parent(n)[:3,:3].T@world)
    orient(upper,u,du);actual=(p.parent(lower)@np.r_[centre,F(1)])[:3];orient(lower,v,target-actual);d=centre-p.P[lower];p.p[lower]=d-p.q[lower]@d;p.dirty();p.assign(hand,p.parent(hand)[:3,:3].T@hand_rotation)
    elbow=p.point(upper,centre);hinge=p.point(lower,centre);w=p.point(hand,p.P[hand]);error=float(np.linalg.norm(w-target))*5
    length_error=max(abs(float(np.linalg.norm(elbow-shoulder)-a)),abs(float(np.linalg.norm(w-elbow)-b)))*5
    return {'dot':dot,'target_error_blocks':error,'hinge_gap_blocks':float(np.linalg.norm(elbow-hinge))*5,'length_error_blocks':length_error,'rotations':{n:p.q[n].copy() for n in (upper,lower,hand)}}
reports=[];failures=[]
for unit,key in [('00','3'),('01','4')]:
    rig={b['name']:b for b in body['rigs'][key]}
    for kind in ('dormant','standing','crouching','prone'):
        for side in ('l','r'):
            for chest in (-2,0,2):
                base=sample(rig,kind);base.q['torso_upper']=base.q['torso_upper']@R.from_euler('x',chest,degrees=True).as_matrix().astype(F);base.dirty();upper='arm_'+side;hand='hand_'+side;centre=base.P['r30_elbow_socket_'+side];shoulder=base.point(upper,base.P[upper]);target=base.point(hand,base.P[hand]);pole=base.point(upper,centre)-shoulder;orientation=base.matrix(hand)[:3,:3].copy();reach=float(np.linalg.norm(centre-base.P[upper])+np.linalg.norm(base.P[hand]-centre));reachable=float(np.linalg.norm(target-shoulder))<reach-.001
                row={'unit':unit,'pose':kind,'side':side,'chest_degrees':chest,'armArticulationRuns':reachable,'reach_blocks':reach*5};results={}
                # Tiny noncoplanar target/pole roundoff is what a float matrix
                # chain introduces even when the intended reset pose is planar.
                for mode in ('legacy_X','anatomical'):
                    values=[]
                    for epsilon in (-1e-6,-1e-7,-1e-8,0,1e-8,1e-7,1e-6):
                        p=copy.deepcopy(base);p.dirty();t=target+np.array([0,0,epsilon],dtype=F);value=solve(p,side,t,orientation,pole,mode=='anatomical');values.append(value)
                    reference=values[3];spread=max(angle(reference['rotations'][n],v['rotations'][n]) for v in values for n in reference['rotations']);jump=max(angle(a['rotations'][n],b['rotations'][n]) for a,b in zip(values,values[1:]) for n in a['rotations'])
                    results[mode]={'maximum_rotation_perturbation_degrees':spread,'maximum_adjacent_jump_degrees':jump,'minimum_reference_dot_abs':min(abs(v['dot']) for v in values),'maximum_target_error_blocks':max(v['target_error_blocks'] for v in values),'maximum_hinge_gap_blocks':max(v['hinge_gap_blocks'] for v in values),'maximum_length_error_blocks':max(v['length_error_blocks'] for v in values)}
                row.update(results);reports.append(row)
                if reachable and (results['anatomical']['maximum_adjacent_jump_degrees']>1 or results['anatomical']['maximum_length_error_blocks']>.002 or results['anatomical']['maximum_hinge_gap_blocks']>.002):failures.append(row)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_sha,'Production solver changed while reading the audit'
summary={'source_sha256':source_sha,'cases':len(reports),'reachable_cases':sum(r['armArticulationRuns'] for r in reports),'legacy_maximum_jump_degrees':max(r['legacy_X']['maximum_adjacent_jump_degrees'] for r in reports),'anatomical_maximum_jump_degrees':max(r['anatomical']['maximum_adjacent_jump_degrees'] for r in reports),'anatomical_maximum_length_error_blocks':max(r['anatomical']['maximum_length_error_blocks'] for r in reports),'anatomical_maximum_hinge_gap_blocks':max(r['anatomical']['maximum_hinge_gap_blocks'] for r in reports),'failures':len(failures),'note':'Independent float32 matrix audit; not a claim of native Gecko/JOML execution. Unreachable hand intents are reported; the production articulation gate skips them.'}
(OUT/'un_arm_ik_perturbation.json').write_text(json.dumps({'summary':summary,'cases':reports,'failures':failures},indent=2));print(json.dumps(summary,indent=2),flush=True)
