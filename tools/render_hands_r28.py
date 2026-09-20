"""Offline diagnostic of the same bounded right-finger angles used by R28."""
from pathlib import Path
import json,numpy as np
from scipy.spatial.transform import Rotation
import render_unit01_rig_preview as r
ROOT=Path(__file__).resolve().parents[1];PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele';OUT=ROOT/'artifacts/facility_r28/hands/after'

def main():
    OUT.mkdir(parents=True,exist_ok=True);records=[]
    for name in ('eva_unit00','eva_unit01','eva_unit02','eva_prototype','eva_un01'):
        mesh=json.loads((PACK/'mesh'/f'{name}.mesh.json').read_text());pv,pa,br=r.load_skeleton(mesh,PACK/'geo'/f'{name}.geo.json')
        anim='eva_unit01' if name in ('eva_prototype','eva_un01') else name
        _,_,base,offsets=r.select_animation(PACK/'animations'/f'{anim}.animation.json','idle',0)
        parts=[n for n in mesh['parts'] if n.endswith('_r') and n.startswith(('hand_','finger_'))]
        for pose in ('relaxed','fist','rifle','knife'):
            rotation=dict(base);positions=dict(offsets)
            for digit in ('index','middle','ring','little'):
                axis=f'finger_{digit}_axis_r';rotation[axis]=(0,0,0);positions[axis]=(0,0,0)
                angles=[12,20,10] if pose=='relaxed' else [64,82,48] if pose=='fist' else [18,28,12] if pose=='rifle' and digit=='index' else [55,74,36]
                for bone,angle in zip((f'finger_{digit}_r',f'finger_{digit}_tip_r',f'finger_{digit}_distal_r'),angles):rotation[bone]=(0,0,angle);positions[bone]=(0,0,0)
            thumb=np.asarray(pv['finger_thumb_r']);axis=np.cross(np.asarray(pv['finger_thumb_tip_r'])-thumb,np.asarray(pv['finger_middle_r'])-thumb);axis/=np.linalg.norm(axis)
            for bone,angle in zip(('finger_thumb_r','finger_thumb_tip_r','finger_thumb_distal_r'),[8,12,6] if pose=='relaxed' else [30,36,18]):
                angles=Rotation.from_rotvec(axis*np.deg2rad(angle)).as_euler('xyz',degrees=True);rotation[bone]=tuple(angles*np.array([-1,-1,1]));positions[bone]=(0,0,0)
            cache={}
            for bone in parts:r.bone_matrix(bone,pv,pa,rotation,positions,br,cache)
            views=[]
            for view in ('front','right'):
                scene=r.collect_scene(mesh,PACK/'textures/entity'/f'{name}.png',view,cache,pv,pa,(),parts)
                path=OUT/f'{name}_{pose}_{view}.png';r.render_scene(scene,view,path,f'{name} / {pose}',r.scene_bounds({view:scene},(),1.12),False);views.append(path)
            r.write_contact_sheet(views,OUT/f'{name}_{pose}.png',f'{name} right hand / {pose}')
            records.append(dict(unit=name,pose=pose,mesh_parts=len(parts),finger_rotation_max=82,preview='Offline same-angle diagnostic; native screenshots remain required'))
        print('Hand poses rendered',name,flush=True)
    (OUT/'receipt.json').write_text(json.dumps(records,indent=2))

if __name__=='__main__':main()
