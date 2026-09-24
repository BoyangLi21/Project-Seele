"""Export actual anatomical joint and collision frames for the Java physics probe."""
from pathlib import Path
import json
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.spatial import ConvexHull
import author_gameplay_motion_r32 as common
import anatomical_hinge_r35 as hinge
from author_tv_combat_r34 import Actor
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/combat_rebuild_r35/jbullet';S=.0125

def mat(r=None,p=None):
    m=np.eye(4)
    if r is not None:m[:3,:3]=r
    if p is not None:m[:3,3]=p
    return m
def scale(m):
    m=m.copy();m[:3,3]*=S;return m
def axis_frame(axis):
    z=hinge.unit(axis);x=hinge.unit(np.cross([0,1,0],z),[1,0,0]);y=np.cross(z,x)
    return np.column_stack((x,y,z))
def cone_frame(axis):
    x=hinge.unit(axis);y=hinge.unit(np.cross([0,0,1],x),[1,0,0]);return np.column_stack((x,y,np.cross(x,y)))
def build(key):
    actor=Actor(key);e=actor.rig;P=e.P;K=actor.knees;E=actor.elbows
    name='sachiel_gameplay_r32.json' if actor.angel else f'eva_gameplay_r32_{key}.json'
    doc=json.loads((ROOT/'artifacts/combat_foundation_r33/profiles'/name).read_text());frame=doc['clips']['r32_guard']['frames'][0]
    if actor.angel:
        p=e.pose()
        for n,q in zip(doc['bones'],frame['rotation_wxyz']):w,x,y,z=q;p.setq(n,R.from_quat([-x,-y,z,w]))
        for n,v in frame.get('bone_position_xyz',{}).items():p.setp(n,np.asarray(v)*[-1,1,1])
        p.setp('root',np.asarray(frame['root_m'])*112*[-1,1,1])
    else:p=e.decode(frame,common.NAMES)
    for s in ('l','r'):
        for a,b,c,j,n,pole in [('leg_'+s,'shin_'+s,'foot_'+s,K[s],[-1,0,0],[0,0,-1]),('arm_'+s,'forearm_'+s,'hand_'+s,E[s],[1,0,0],[-.6 if s=='l' else .6,-.4,.25])]:
            goal=p.point(c).copy();orient=R.from_matrix(p.matrix(c)[:3,:3]);hinge.solve(p,P,a,b,c,j,goal,p.parent(a)[:3,:3]@np.array(pole),n,orient)
        if 'wrist_'+s in p.q:p.setq('wrist_'+s,R.identity())
        p.setq('hand_'+s,R.identity())
    definitions=[]
    hip=(P['leg_l']+P['leg_r'])*.5
    def box(bone,parent,centre,size,mass,joint,cone,axis=(0,1,0)):
        bind=mat(p=centre);definitions.append(dict(name=bone,parent=parent,shape='box',size=size,mass=mass,bind=scale(bind).ravel().tolist(),initial=(scale(p.matrix(bone))@scale(bind)).ravel().tolist(),joint=scale(mat(cone_frame(axis),joint)).ravel().tolist(),cone=cone))
    def limb(bone,parent,first,last,radius,mass,axis=None):
        vector=last-first;align=common.rt.eva.arc([0,1,0],vector).as_matrix();bind=mat(align,(first+last)*.5)
        row=dict(name=bone,parent=parent,shape='capsule',size=[radius,float(np.linalg.norm(vector)*S)-2*radius],mass=mass,bind=scale(bind).ravel().tolist(),initial=(scale(p.matrix(bone))@scale(bind)).ravel().tolist(),joint=scale(mat(axis_frame(axis) if axis is not None else cone_frame(vector),first)).ravel().tolist(),cone=[2.5,2.3,1.75] if bone.startswith('arm_') else [1.75,1.25,.9])
        if axis is not None:
            u=first-P[parent];v=last-first;row['hinge']=list(hinge.limits(u,v,axis))
        definitions.append(row)
    box('torso_lower',None,hip+[0,-8,0],[.18,.16,.13],16,hip,[.5,.5,.35])
    box('torso_upper','torso_lower',(P['torso_upper']+P['head'])*.5,[.25,.22,.16],27,P['torso_upper'],[1.05,.75,1.15])
    box('head','torso_upper',P['head']+[0,7,0],[.14,.17,.14],4,P['head'],[.85,.85,1.60])
    for s in ('l','r'):
        limb('arm_'+s,'torso_upper',P['arm_'+s],E[s],.075,3.2)
        limb('forearm_'+s,'arm_'+s,E[s],P['hand_'+s],.072,2.7,[1,0,0])
        box('hand_'+s,'forearm_'+s,P['hand_'+s]+[0,-3,0],[.08,.10,.07],1,P['hand_'+s],[.95,1.35,2.9],P['hand_'+s]-E[s])
        limb('leg_'+s,'torso_lower',P['leg_'+s],K[s],.09,10)
        limb('shin_'+s,'leg_'+s,K[s],P['foot_'+s],.085,6,[-1,0,0])
        low=actor.feet[s].min(0);high=actor.feet[s].max(0)
        box('foot_'+s,'shin_'+s,P['foot_'+s]+(low+high)*.5,((high-low)*.5*S).tolist(),2,P['foot_'+s],[.40,.40,.30])
    render_rig=list(e.bones.values()) if actor.angel else common.BODY['rigs'][str(key)]
    by_name={row['name']:row for row in definitions}
    for row in definitions:row['hulls']=[];row['hull_planes']=[]
    def add_hull(owner,vertices):
        inverse=np.linalg.inv(np.asarray(by_name[owner]['bind']).reshape(4,4));v=(np.c_[vertices,np.ones(len(vertices))]@inverse.T)[:,:3]
        v=np.unique(np.round(v,6),axis=0)
        if len(v)<4:return
        try:hull=ConvexHull(v)
        except Exception:return
        by_name[owner]['hulls'].append(np.round(v[hull.vertices],6).tolist())
        by_name[owner]['hull_planes'].append(np.unique(np.round(hull.equations,6),axis=0).tolist())
    if actor.angel:
        owners={}
        for i,n in enumerate(e.names):
            owner=n
            while owner not in by_name and owner is not None:owner=e.parents.get(owner)
            if owner is not None:owners[i]=owner
        dominant=e.ids[np.arange(len(e.ids)),np.argmax(e.weights,axis=1)]
        for owner in by_name:
            mask=np.isin(dominant,[i for i,n in owners.items() if n==owner]);vertices=e.vertices[mask]*S
            if len(vertices):add_hull(owner,vertices)
    if not actor.angel:
        model_name=['eva_unit00','eva_unit01','eva_unit02','eva_prototype','eva_un01'][key]
        mesh=json.loads((ROOT/f'run/resourcepacks/eva_real_model/assets/projectseele/mesh/{model_name}.mesh.json').read_text())
        for bone,part in mesh['parts'].items():
            if bone not in e.parents or bone.startswith('finger_') or bone in ('cannon','knife','shield','lance','n2'):continue
            owner=bone
            while owner not in by_name and owner is not None:owner=e.parents.get(owner)
            if owner is None:continue
            vertices=(np.asarray(part['vertices']).reshape(-1,8)[:,:3]+part['pivot'])*[-1,1,1]*S
            add_hull(owner,vertices)
    initial=p.encode() if actor.angel else e.encode(p,bone_names=common.NAMES)
    return {'scale_from_pixels':S,'bones':actor.names,'render_rig':render_rig,'initial_visual_pose':initial,'bodies':definitions,'policy':'Pose-controlled movement hands off to constrained dynamics only after loss of support. This is an isolated physics prototype.'}
def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--keep-recovery',action='store_true');args=ap.parse_args()
    previous=json.loads((OUT/'articulated_bodies_r35.json').read_text())['models'] if args.keep_recovery else {}
    OUT.mkdir(parents=True,exist_ok=True);models={str(key):build(key) for key in [0,1,2,3,4,'sachiel']}
    for key,model in models.items():
        if key in previous and 'recovery' in previous[key]:model['recovery']=previous[key]['recovery']
    (OUT/'eva_body_definition.json').write_text(json.dumps(models['1'],indent=2))
    (OUT/'articulated_bodies_r35.json').write_text(json.dumps({'schema':'projectseele.articulated-body.v1','models':models},separators=(',',':')))
    print('Exported six articulated rigs with separate anatomical, COM and render frames')
if __name__=='__main__':main()
