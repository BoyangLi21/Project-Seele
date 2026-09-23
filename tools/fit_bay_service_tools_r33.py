"""Fit original robot tool contacts to the five actual docked body surfaces."""
from pathlib import Path
import json,hashlib
import numpy as np
import render_unit01_rig_preview as render
ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele'

def front(triangles,x,y):
    a=triangles[:,0,:2];b=triangles[:,1,:2]-a;c=triangles[:,2,:2]-a;d=np.array([x,y])-a
    det=b[:,0]*c[:,1]-b[:,1]*c[:,0];valid=abs(det)>1e-9
    u=np.divide(d[:,0]*c[:,1]-d[:,1]*c[:,0],det,out=np.zeros(len(det)),where=valid)
    v=np.divide(b[:,0]*d[:,1]-b[:,1]*d[:,0],det,out=np.zeros(len(det)),where=valid)
    mask=valid&(u>=0)&(v>=0)&(u+v<=1)
    if not mask.any():return None
    return float((triangles[:,0,2]+u*(triangles[:,1,2]-triangles[:,0,2])+v*(triangles[:,2,2]-triangles[:,0,2]))[mask].min())

def main():
    result={'schema':1,'frame':'NERV fixed gantry / UN entity origins; front is -Z; body-render lift included','targets':{},'sources':{}}
    for key,name in enumerate(['eva_unit00','eva_unit01','eva_unit02','eva_prototype','eva_un01']):
        path=PACK/'mesh'/(name+'.mesh.json');geo=PACK/'geo'/(name+'.geo.json');mesh=json.loads(path.read_text());pv,pa,br=render.load_skeleton(mesh,geo);cache={};parts=[]
        for bone,part in mesh['parts'].items():
            matrix=np.asarray(render.bone_matrix(bone,pv,pa,{},{},br,cache));a=np.asarray(part['vertices']).reshape(-1,mesh['stride'])[:,:3]+part['pivot'];a*=(-1,1,1)
            parts.append(((np.c_[a,np.ones(len(a))]@matrix.T)[:,:3]*.3125).reshape(-1,3,3))
        triangles=np.concatenate(parts);points=[]
        for side in [-1,1]:
            for index,y in enumerate([8,16.4,24.8,33.2,41.6,49.6]):
                expected=side*(4.4 if index<3 else 3.4 if index<5 else 2.6)*(1.25 if key>=3 else 1)
                candidates=[]
                for dx in [0,-.25,.25,-.5,.5,-1,1,-2,2]:
                    x=expected+dx;z=front(triangles,x,y)
                    if z is not None:candidates.append((abs(dx),x,z))
                if not candidates:raise ValueError((name,side,index,'No body surface'))
                _,x,z=min(candidates)
                # NERV gantries stand at bed+.04, the body at bed+1 with a .05
                # render lift. UN machinery shares the EVA's entity origin.
                points.append([round(x,4),round(y+(.05 if key>=3 else 1.01),4),round(z-.15,4)])
        result['targets'][str(key)]=points
        result['sources'][name]={'mesh_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'geo_sha256':hashlib.sha256(geo.read_bytes()).hexdigest()}
        print(name,points,flush=True)
    path=ROOT/'src/main/resources/assets/projectseele/mesh/bay_service_targets_r33.json';path.write_text(json.dumps(result,separators=(',',':')))
if __name__=='__main__':main()
