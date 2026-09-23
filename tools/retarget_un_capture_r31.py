"""Retarget the R31 source clips to measured UN rigs, without Tiger hinge offsets."""
from pathlib import Path
import copy
import hashlib
import json
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R
import retarget_human_r12 as rt
import author_eva_rifle_stances_r06 as surface
from prepare_combat_capture_r31 import SELECTED, root_in_place, actor_heading, align_actor_heading

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/facility_r31/motion_sources'
PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele'

def configure(key,body,name):
    rig={b['name']:b for b in body['rigs'][str(key)]}
    module=rt.eva
    module.rig=rig;module.parents={n:b.get('parent') for n,b in rig.items()}
    module.P={n:np.asarray(b['pivot'],float)*[-1,1,1] for n,b in rig.items()}
    module.K={s:module.P['r30_knee_socket_'+s] for s in ('l','r')}
    module.E={s:module.P['r30_elbow_socket_'+s] for s in ('l','r')}
    mesh=json.loads((PACK/'mesh'/(name+'.mesh.json')).read_text())
    hulls={};feet={}
    for bone,part in mesh['parts'].items():
        verts=(np.asarray(part['vertices']).reshape(-1,8)[:,:3]+part['pivot'])*[-1,1,1]
        vertices=np.unique(np.round(verts,6),axis=0)
        if len(vertices)>4:
            try:vertices=vertices[ConvexHull(vertices).vertices]
            except Exception:pass
        hulls[bone]=vertices
        if bone in ('foot_l','foot_r'):feet[bone[-1]]=vertices-module.P[bone]
    module.feet=feet;module.idle=module.Pose()
    for bone,spec in rig.items():
        module.idle.setq(bone,R.from_euler('xyz',np.asarray(spec.get('rotation',[0,0,0]))*[-1,-1,1],degrees=True))
    def floor(p,names):
        return min((np.c_[hulls[n],np.ones(len(hulls[n]))]@p.matrix(n).T)[:,1].min() for n in names if n in hulls)
    surface.floor=floor
    return hulls

def main():
    body=json.loads((ROOT/'run/projectseele-local-maps/eva_body_r25.json').read_text())
    names=body['motion']['bones'];summary=[]
    for key,model,short in ((3,'eva_prototype','un00'),(4,'eva_un01','un01')):
        hulls=configure(key,body,model)
        clips={};evidence=[];snapshots={}
        for name,(_,support) in SELECTED.items():
            human=rt.Human(OUT/'tuffles'/(name+'_source.npz'));actor=rt.Retarget(human)
            heading=actor_heading(human,support)
            duration=(human.frames-1)/human.fps;count=round(duration*60)+1;frames=[];errors=[];gaps=[];floors=[];feet=[]
            preview=[]
            for index,frame in enumerate(np.linspace(0,human.frames-1,count)):
                pose,travel,meta=actor.pose(float(frame),support=support)
                source,_=human.sample(float(frame))
                world=R.from_matrix(rt.axes(source['head_end']-source['head'],source['shoulder_r']-source['shoulder_l']))
                pose.setq('head',R.from_matrix(pose.parent('head')[:3,:3]).inv()*world)
                # Finger axes belong to the new mesh's bind frames. Gameplay owns
                # the grip curl; never inherit the old Tiger fist offsets.
                for bone,spec in rt.eva.rig.items():
                    if bone.startswith('finger_'):
                        pose.setq(bone,R.from_euler('xyz',np.asarray(spec.get('rotation',[0,0,0]))*[-1,-1,1],degrees=True))
                        pose.setp(bone,[0,0,0])
                if support=='fall':
                    low=surface.floor(pose,['torso_lower','torso_upper','head','arm_l','arm_r','forearm_l','forearm_r','hand_l','hand_r','leg_l','leg_r','shin_l','shin_r','foot_l','foot_r'])
                    if low<0:pose.setp('root',pose.p['root']+[0,-low,0])
                align_actor_heading(pose,heading,frame,support)
                root_in_place(pose)
                contact=tuple(bool(meta['contacts'][side]) for side in ('l','r')) if support!='air' else (False,False)
                record=rt.eva.encode(pose,contacts=contact,bone_names=names);frames.append(record)
                errors.append(max(meta['errors'].values()))
                for side in ('l','r'):
                    gaps.append(float(np.linalg.norm(pose.point('arm_'+side,rt.eva.E[side])-pose.point('forearm_'+side)))*5/16)
                    gaps.append(float(np.linalg.norm(pose.point('leg_'+side,rt.eva.K[side])-pose.point('shin_'+side)))*5/16)
                floors.append(float(surface.floor(pose,['foot_l','foot_r']))*5/16)
                feet.append([pose.point('foot_'+side).tolist() for side in ('l','r')])
                if index in {round(q*(count-1)) for q in (0,.2,.4,.6,.8,1)}:
                    visible=['torso_lower','torso_upper','head','arm_l','arm_r','forearm_l','forearm_r','hand_l','hand_r','leg_l','leg_r','shin_l','shin_r','foot_l','foot_r']
                    preview.append({'frame':index,'phase':index/(count-1),
                        'joints':{n:(pose.point(n)*5/16).tolist() for n in visible},
                        'body_hull_floor_blocks':float(surface.floor(pose,visible))*5/16})
            for i in range(1,len(frames)):
                for j in range(len(names)):
                    if np.dot(frames[i-1]['rotation_wxyz'][j],frames[i]['rotation_wxyz'][j])<0:
                        frames[i]['rotation_wxyz'][j]=[-v for v in frames[i]['rotation_wxyz'][j]]
            rotations=np.asarray([f['rotation_wxyz'] for f in frames])
            assert np.isfinite(rotations).all() and np.allclose(np.linalg.norm(rotations,axis=2),1,atol=3e-7)
            assert all(f['root_m'][0]==0 and f['root_m'][2]==0 for f in frames)
            assert max(gaps)<1e-8
            clips['r31_'+name]={'duration_seconds':duration,'loop':False,'root_travel_m':[0,0,0],'frames':frames,'support':support}
            displacement=np.diff(np.asarray(feet)[:,:,[0,2]],axis=0)*5/16
            contactmask=np.array([f['foot_contact'] for f in frames])
            steps=np.linalg.norm(displacement,axis=2)[contactmask[1:]&contactmask[:-1]]
            evidence.append({'clip':'r31_'+name,'rig_key':key,'frames':count,
                'max_hinge_gap_blocks':max(gaps),'max_endpoint_ik_error_blocks':max(errors),
                'minimum_foot_hull_y_blocks':min(floors),'max_contact_foot_delta_per_sample_blocks':float(steps.max()) if len(steps) else None,
                'contact_lock_applied':False,'note':'Foot displacement is uncorrected capture/retarget movement, not a claim of planted-foot gameplay validation.'})
            snapshots['r31_'+name]=preview
            print(short,name,count,'hinge gap',max(gaps),flush=True)
        result={'schema':2,'sample_rate':60,'quaternion_order':'wxyz','bones':names,'clips':clips,
                'provenance':{'rig_key':key,'model':model,'source':'Same Haley Tuffles originals as eva_combat_capture_r31.json',
                 'retarget':'R12 direction retarget with measured R30 UN elbow/knee sockets; no Tiger +11.4 offsets',
                 'root_policy':'Source root travel excluded; root X/Z exactly zero. Grounded clips remove actor foot-base heading; aerial strike removes chest aiming heading; floor recovery uses fixed final heading. Relative pelvis/feet and chest/pelvis torque preserved, bind-pivot compensation on root children.',
                 'hands':'New rig finger bind frames preserved; runtime grasp curl/contact IK remains required',
                 'body_rig_sha256':hashlib.sha256(json.dumps(body['rigs'][str(key)],sort_keys=True).encode()).hexdigest(),
                 'status':'isolated candidate; no runtime/private pack overwritten'}}
        (OUT/f'eva_combat_capture_r31_{short}.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf8')
        (OUT/f'{short}_retarget_evidence.json').write_text(json.dumps({'checks':evidence,'actual_pose_joints':snapshots},indent=2))
        summary.extend(evidence)
    (OUT/'un_retarget_summary.json').write_text(json.dumps(summary,indent=2))

if __name__=='__main__':main()
