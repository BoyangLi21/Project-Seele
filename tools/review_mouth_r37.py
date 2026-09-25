from pathlib import Path
import json,numpy as np
from scipy.spatial.transform import Rotation as R
import build_eva_body_r05 as rig
ROOT=Path(__file__).resolve().parents[1];ASSET=ROOT/'artifacts/combat_beast_r37/tv_jaw/assets/projectseele';OUT=ROOT/'artifacts/combat_beast_r37/tv_jaw_review'
def main():
    OUT.mkdir(parents=True,exist_ok=True);mesh=json.loads((ASSET/'mesh/eva_unit01.mesh.json').read_text());bones=json.loads((ASSET/'geo/eva_unit01.geo.json').read_text())['minecraft:geometry'][0]['bones']
    rig.rig={b['name']:b for b in bones};rig.P={n:np.array(b['pivot'])*[-1,1,1] for n,b in rig.rig.items()};rig.parents={n:b.get('parent') for n,b in rig.rig.items()};manifest=[]
    for opening in [0,.5,1]:
        p=rig.Pose();p.setq('r37_jaw',R.from_euler('x',-31*opening,degrees=True));p.setp('r37_jaw',[0,0,-.8*opening]);v=[];uv=[];colors=[];hv=[];huv=[];hc=[]
        for n,part in mesh['parts'].items():
            if n.startswith('r37_') and n!='r37_jaw' and opening==0:continue
            for name,b in rig.rig.items():
                if '_axis_' in name:p.setq(name,R.from_euler('xyz',np.array(b.get('rotation',[0,0,0]))*[-1,-1,1],degrees=True))
            a=np.array(part['vertices']).reshape(-1,8);raw=(a[:,:3]+part['pivot'])*[-1,1,1]
            skin=mesh.get('jointSkins',{}).get(n)
            if skin:
                from author_eva_rifle_stances_r06 import multiply
                transform=np.linalg.inv(p.matrix(n))@p.matrix(skin['otherBone']);q=R.from_matrix(transform[:3,:3]).as_quat();q*=1 if q[3]>=0 else -1;dual=.5*multiply(np.r_[transform[:3,3],0],q)
                w=np.array(skin['weights'])[:,None];qs=q*w+np.array([0,0,0,1])*(1-w);length=np.linalg.norm(qs,axis=1,keepdims=True);qs/=length;ds=dual*w/length;ds-=qs*(qs*ds).sum(1,keepdims=True)
                raw=R.from_quat(qs).apply(raw)+2*multiply(ds,qs*[-1,-1,-1,1])[:,:3]
            v.append((np.c_[raw,np.ones(len(raw))]@p.matrix(n).T)[:,:3]*5/16);uv.append(a[:,3:5]);colors.append(np.tile([*part.get('tint',[1,1,1]),1],(len(a),1)))
            if n=='head' or n.startswith('r37_'):hv.append(v[-1]);huv.append(uv[-1]);hc.append(colors[-1])
        for angle,offset in [('front',[0,80,0]),('side',[-80,12,0]),('angle',[-60,90,4])]:
            name=f'mouth_{opening}_{angle}';np.savez_compressed(OUT/(name+'.npz'),vertices=np.concatenate(v),uv=np.concatenate(uv),colors=np.concatenate(colors));manifest.append(dict(file=name,model='eva_unit01',camera_target=[0,2.9,50.8],camera_offset=offset,scale=14))
        name=f'mouth_{opening}_detail';np.savez_compressed(OUT/(name+'.npz'),vertices=np.concatenate(hv),uv=np.concatenate(huv),colors=np.concatenate(hc));manifest.append(dict(file=name,model='eva_unit01',camera_target=[0,2.9,50.8],camera_offset=[-60,90,4],scale=7))
    (OUT/'manifest.json').write_text(json.dumps(manifest))
if __name__=='__main__':main()
