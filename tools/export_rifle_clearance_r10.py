"""Extract a minimal functional support hull relative to the rifle grip; no textures or render mesh are shipped."""
import json
import numpy as np
from scipy.spatial import ConvexHull
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
 data=json.loads((ROOT/'run/resourcepacks/eva_real_model/assets/projectseele/mesh/eva_pallet_smg.mesh.json').read_text())
 points=[]
 for p in data['parts'].values():points.extend((np.array(p['vertices']).reshape(-1,8)[:,:3]+p['pivot']).tolist())
 v=np.unique(np.round(points,6),axis=0)*[-1,1,1]/16;v=(v-np.array([24.49137,88.34269,.87469])/16)*5*.72
 # The renderer maps local X to right, Y to -forward, Z to -up.
 v*= [1,-1,-1];hull=v[ConvexHull(v).vertices]
 dest=ROOT/'src/main/resources/assets/projectseele/motion/rifle_clearance_r10.json';dest.write_text(json.dumps(dict(schema=1,frame='grip-relative right/forward/up in blocks',points=np.round(hull,7).tolist()),indent=2)+'\n',encoding='utf8');print('Functional rifle support vertices',len(hull))
