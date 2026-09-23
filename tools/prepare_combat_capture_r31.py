"""Stage selected genuine capture and export isolated EVA candidates; never install."""
from pathlib import Path
import copy
import hashlib
import json
import shutil
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.signal import savgol_filter
from bvh_motion_r12 import load_bvh, save_npz
import retarget_human_r12 as retarget

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/facility_r31/motion_sources'
TUFFLES=ROOT/'external-assets/incoming/mocap/eva-action-source-r02/tuffles/HaleyTufflesPremadeMocapPack'
CMU=ROOT/'external-assets/incoming/mocap/eva-original-combat-seed-r01/cmu_bvh'
QUAT=ROOT/'external-assets/incoming/mocap/quaternius-ual2-standard/Universal Animation Library 2[Standard]'
SELECTED={
 'grapple_start':('Combat/ArmsGrappleStart.bvh','feet'),
 'shoulder_throw':('Combat/SpinThrowDown.bvh','feet'),
 'air_downstrike':('Combat/AerialSlapDownwards.bvh','air'),
 'get_up':('General/GettingUp.bvh','fall'),
}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def original(path,folder):
    target=OUT/folder/path.name;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path,target)
    assert sha(target)==sha(path)
    return target

def root_in_place(p):
    # Source locomotion delta is intentionally not applied. Keep the pelvis
    # rotation's bind-pivot compensation as local child translations so that
    # zeroing root X/Z does not make the entire actor swing around a distant pivot.
    delta=np.array([p.p['root'][0],0,p.p['root'][2]])
    local=p.q['root'].inv().apply(delta)
    for name,parent in retarget.eva.parents.items():
        if parent=='root':p.setp(name,p.p[name]+local)
    p.setp('root',[0,p.p['root'][1],0])

def actor_heading(human,support='feet'):
    angles=[]
    for frame in range(human.frames):
        source,_=human.sample(frame)
        if support=='air':
            # Floating feet have no grounded facing; use the aiming chest plane.
            right=source['shoulder_r']-source['shoulder_l']
            angles.append(np.arctan2(-right[2],right[0]))
        else:
            forward=(source['toe_l']-source['ankle_l'])+(source['toe_r']-source['ankle_r'])
            angles.append(np.arctan2(-forward[0],-forward[2]))
    angles=np.unwrap(angles)
    return savgol_filter(angles,min(7,(len(angles)-1)//2*2+1),2)

def align_actor_heading(p,heading,frame,support):
    # Foot-base heading identifies the actor's turn around the stage. Removing
    # it preserves pelvis-vs-feet and chest-vs-pelvis torque, rather than zeroing
    # every pelvis/chest yaw independently. For floor recovery, use final facing:
    # the horizontal foot projection is ambiguous while the actor lies down.
    angle=float(np.mean(heading[-8:])) if support=='fall' else float(np.interp(frame,np.arange(len(heading)),heading))
    counter=R.from_euler('y',-angle)
    p.setq('root',counter*p.q['root'])
    pivot=retarget.eva.P['root']
    p.setp('root',counter.apply(p.p['root']+pivot)-pivot)
    return angle

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    names=json.loads((ROOT/'run/projectseele-local-maps/eva_body_r25.json').read_text())['motion']['bones']
    assert all(name in retarget.eva.rig for name in names)
    fps=60;clips={};report=[]
    for name,(relative,support) in SELECTED.items():
        source=original(TUFFLES/'BVH Converted'/relative,'tuffles/original')
        data=load_bvh(source);up=R.from_euler('x',-90,degrees=True)
        data['positions']=up.apply(data['positions'].reshape(-1,3)).reshape(data['positions'].shape)
        data['rotations']=(up*R.from_quat(data['rotations'].reshape(-1,4))).as_quat().reshape(data['rotations'].shape)
        data['axis_conversion']='Z-up to Y-up, -90 degrees X'
        decoded=OUT/'tuffles'/f'{name}_source.npz';save_npz(decoded,data)
        human=retarget.Human(decoded);actor=retarget.Retarget(human)
        heading=actor_heading(human,support)
        duration=(human.frames-1)/human.fps
        count=round(duration*fps)+1;frames=[];contacts=[];errors=[];root_travel=[];joints=[]
        for frame in np.linspace(0,human.frames-1,count):
            pose,travel,meta=actor.pose(float(frame),support=support)
            # A clip that begins lying down has no upright first-frame head
            # calibration. Preserve the captured head-up direction explicitly.
            src,_=human.sample(float(frame))
            head_world=R.from_matrix(retarget.axes(src['head_end']-src['head'],src['shoulder_r']-src['shoulder_l']))
            pose.setq('head',R.from_matrix(pose.parent('head')[:3,:3]).inv()*head_world)
            if support=='fall':
                import author_eva_rifle_stances_r06 as surface
                floor=surface.floor(pose,['torso_lower','torso_upper','head','arm_l','arm_r','forearm_l','forearm_r','hand_l','hand_r','leg_l','leg_r','shin_l','shin_r','foot_l','foot_r'])
                if floor<0:pose.setp('root',pose.p['root']+[0,-floor,0])
            align_actor_heading(pose,heading,frame,support)
            root_in_place(pose)
            feet=tuple(bool(meta['contacts'][side]) for side in ('l','r')) if support!='air' else (False,False)
            frames.append(retarget.eva.encode(pose,contacts=feet,bone_names=names))
            errors.append(max(meta['errors'].values()))
            root_travel.append((travel*5/16).tolist())
            joints.append({k:pose.point(k).tolist() for k in ['root','torso_lower','torso_upper','head','arm_l','forearm_l','hand_l','arm_r','forearm_r','hand_r','leg_l','shin_l','foot_l','leg_r','shin_r','foot_r']})
        arr=np.asarray([frame['rotation_wxyz'] for frame in frames]);assert np.isfinite(arr).all() and np.allclose(np.linalg.norm(arr,axis=2),1,atol=2e-7)
        assert all(frame['root_m'][0]==0 and frame['root_m'][2]==0 for frame in frames)
        # Adjacent samples share the quaternion hemisphere for downstream linear tools.
        for i in range(1,len(frames)):
            for j in range(len(names)):
                if np.dot(frames[i-1]['rotation_wxyz'][j],frames[i]['rotation_wxyz'][j])<0:
                    frames[i]['rotation_wxyz'][j]=[-v for v in frames[i]['rotation_wxyz'][j]]
        clips['r31_'+name]={'duration_seconds':duration,'loop':False,'root_travel_m':[0,0,0],
            'frames':frames,'source_frame_range':[0,human.frames-1],'support':support}
        row={'clip':'r31_'+name,'source':str(source.relative_to(ROOT)),'source_url':'https://haleytuffles.com/motioncapture',
             'author_download':'https://www.mediafire.com/file/dlz7f4xyg1436ln/HaleyTufflesPremadeMocapPack.zip/file',
             'sha256':sha(source),'source_frames':human.frames,'source_fps':human.fps,'seconds':duration,'output_frames':count,
             'source_height_units':human.height,'hip_vertical_range_units':float(np.ptp(data['positions'][:,0,1])),
             'max_endpoint_ik_error_blocks':float(max(errors)),
             'license':'Author permits personal/commercial use, no credit required; author credit retained.',
             'status':'isolated retarget candidate, not installed or visually approved'}
        report.append(row)
        (OUT/'tuffles'/f'{name}_retarget_markers.json').write_text(json.dumps({'frames':joints,'excluded_actor_root_travel_blocks':root_travel},separators=(',',':')))
        print(name, human.frames, 'source frames ->',count,'EVA frames',duration,'seconds',flush=True)
    original(TUFFLES/'ReadME.txt','tuffles')
    result={'schema':2,'sample_rate':fps,'quaternion_order':'wxyz','bones':names,'clips':clips,
            'provenance':{'retarget':'Existing R12 measured limb-direction retarget + measured knee/elbow articulation',
             'source':'Haley Tuffles acting, iPiSoft recording, Blender cleanup',
             'root_policy':'Source root travel excluded; root X/Z exactly zero. Grounded clips remove actor foot-base heading; aerial strike removes chest aiming heading; floor recovery uses fixed final heading. Relative pelvis/feet and chest/pelvis torque preserved, bind-pivot compensation on root children.',
             'rig_key':1,'use':'Candidate for current NERV Unit-01 rig; UN rigs require their own hinge/limb support adaptation.',
             'changes':'Axis conversion, EVA proportions, per-limb retarget, support constraints, 60 Hz resample. No speed-up or authored hit IK.'}}
    (OUT/'eva_combat_capture_r31.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf8')
    cmu_manifest=json.loads((CMU.parent/'manifest.json').read_text(encoding='utf-8-sig'))
    for name in ('18_03.bvh','19_03.bvh','18_05.bvh','19_05.bvh'):
        p=original(CMU/name,'cmu_pair');data=load_bvh(p);save_npz(OUT/'cmu_pair'/(p.stem+'.npz'),data)
        source_entry=next(a for a in cmu_manifest['assets'] if a['file']=='cmu_bvh/'+name)
        assert sha(p)==source_entry['sha256']
        report.append({'clip':p.stem,'source':str(p.relative_to(ROOT)),'sha256':sha(p),'source_frames':len(data['positions']),'source_fps':data['fps'],
                       'source_url':'https://mocap.cs.cmu.edu/search.php?subjectnumber='+p.stem[:2],
                       'conversion_mirror_url':source_entry['conversion_mirror_url'],'bvh_conversion':cmu_manifest['bvh_conversion'],
                       'license_url':'https://mocap.cs.cmu.edu/','license':'Free for all uses; inclusion in products permitted, direct resale of data prohibited. CMU/NSF acknowledgement retained.',
                       'label':'Paired pull-and-resist' if p.stem.endswith('03') else 'Paired elbow pull-and-resist',
                       'status':'decoded paired interaction source; not a captured shoulder throw'})
    quat_path=original(QUAT/'Unreal-Godot/UAL2_Standard_RM.glb','quaternius_ual2')
    original(QUAT/'License.txt','quaternius_ual2');original(QUAT/'README.txt','quaternius_ual2')
    report.append({'group':'quaternius_ual2','source':str(quat_path.relative_to(ROOT)),'sha256':sha(quat_path),
                   'source_url':'https://quaternius.com/packs/universalanimationlibrary2.html','license':'CC0 1.0',
                   'animations_in_actual_standard_file':43,'type':'Authored game animation, not claimed as motion capture',
                   'status':'staged original GLB; action names and accessor durations inspected separately'})
    (OUT/'selected_sources.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

if __name__=='__main__':main()
