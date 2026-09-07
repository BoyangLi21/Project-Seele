"""Derive the RMB impact centre from the selected Group-C finisher's actual rig."""
from pathlib import Path
import json,hashlib
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1]
def main():
    motion=ROOT/'src/main/resources/assets/projectseele/motion/eva_ordinary_attack_group_c_v1.json'
    geometry=ROOT/'src/main/resources/assets/projectseele/eva/eva_rig_schema.json'
    data=json.loads(motion.read_text(encoding='utf-8'));rig=json.loads(geometry.read_text(encoding='utf-8'))['bones'];rig={b['name']:b for b in rig};pivots={n:np.asarray(b['pivot'])*[-1,1,1]/16 for n,b in rig.items()}
    def T(v):
        m=np.eye(4);m[:3,3]=v;return m
    points=[]
    for frame in data['clips']['ordinary_attack_group_c_stage_3']['frames']:
        rotations=dict(zip(data['bones'],frame['rotation_wxyz']));cache={}
        def matrix(n):
            if n in cache:return cache[n]
            w,x,y,z=rotations.get(n,[1,0,0,0]);r=np.eye(4);r[:3,:3]=Rotation.from_quat([-x,-y,z,w]).as_matrix();local=T(pivots[n])@r@T(-pivots[n])
            if n=='root':local=T([0,frame['root_m'][1]*112/16,0])@local
            cache[n]=(matrix(rig[n]['parent']) if rig[n].get('parent') else np.eye(4))@local
            return cache[n]
        hands=[(matrix('hand_'+side)@np.r_[pivots['finger_middle_'+side],1])[:3]*[-5,5,-5] for side in ['r','l']]
        points.append([round(float(v),6) for v in (hands[0]+hands[1])/2])
    out=motion.with_name('eva_heavy_contact_r04.json');out.write_text(json.dumps({'schema':1,'coordinate_system':'world yaw zero; blocks relative to authoritative entity root','clip':'ordinary_attack_group_c_stage_3','source_sha256':hashlib.sha256(motion.read_bytes()).hexdigest(),'geometry_sha256':hashlib.sha256(geometry.read_bytes()).hexdigest(),'points_blocks':points},indent=2)+'\n',encoding='utf-8');print(out,len(points),'contact',points[17])
if __name__=='__main__':main()
