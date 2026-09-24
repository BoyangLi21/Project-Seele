"""Render the real EVA mesh using the Java dynamics output, without pose replacement."""
from pathlib import Path
import json,numpy as np
from scipy.spatial.transform import Rotation as R
import author_tv_combat_r34 as a
from review_tv_combat_r34 import mesh
ROOT=a.ROOT;BASE=ROOT/'artifacts/combat_rebuild_r35/jbullet';OUT=BASE/'mesh_review'

def main():
    OUT.mkdir(parents=True,exist_ok=True);actor=a.Actor(1);definition=json.loads((BASE/'eva_body_definition.json').read_text());frames=json.loads((BASE/'back_fall.json').read_text())['frames'];manifest=[]
    def ordered(n,seen,result):
        if n in seen:return
        parent=actor.rig.parents[n]
        if parent:ordered(parent,seen,result)
        seen.add(n);result.append(n)
    order=[];seen=set()
    for n in actor.P:ordered(n,seen,order)
    for index,t in enumerate([0,.15,.30,.5,.75,1.,1.4,2.]):
        sample=frames[round(t*60)];desired={n:np.array(m).reshape(4,4) for n,m in sample['deformation'].items()}
        for m in desired.values():m[:3,3]/=.0125
        desired['root']=desired['torso_lower'];p=actor.rig.decode(definition['initial_visual_pose'],a.common.NAMES)
        for n in order:
            if n not in desired:continue
            local=np.linalg.inv(p.parent(n))@desired[n];q=R.from_matrix(local[:3,:3]);p.setq(n,q);p.setp(n,local[:3,3]-actor.P[n]+q.apply(actor.P[n]))
        v,uv=mesh(actor,p,'eva_unit01');file=f'physical_{index}';np.savez_compressed(OUT/(file+'.npz'),vertices=v*5/16,uv=uv)
        centre=(v.min(0)+v.max(0))*.5*5/16
        manifest.append({'file':file,'model':'eva_unit01','index':index,'row':0,'phase':t,'camera_target':[float(centre[0]),float(-centre[2]),float(centre[1])]})
    (OUT/'manifest.json').write_text(json.dumps(manifest));print(OUT)
if __name__=='__main__':main()
