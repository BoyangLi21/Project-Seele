"""Export the actual local surfaces for a choreography contact-sheet inspection."""
from pathlib import Path
import json,sys
import numpy as np
from scipy.spatial.transform import Rotation as R
import author_tv_combat_r34 as author
from author_eva_rifle_stances_r06 import multiply
ROOT=author.ROOT;OUT=ROOT/'artifacts/combat_direction_r34/pose_review'

def mesh(actor,p,name):
    d=json.loads((ROOT/f'run/resourcepacks/eva_real_model/assets/projectseele/mesh/{name}.mesh.json').read_text())
    if actor.angel:
        v=np.asarray(d['parts']['root']['vertices']).reshape(-1,8);source=v[:,:3]*[-1,1,1]
        ids=np.asarray(d['skin']['indices']).reshape(-1,4);w=np.asarray(d['skin']['weights']).reshape(-1,4,1)
        matrices=np.array([p.matrix(n) for n in d['skin']['bones']]);q=R.from_matrix(matrices[:,:3,:3]).as_quat();dual=.5*multiply(np.c_[matrices[:,:3,3],np.zeros(len(q))],q)
        qs=q[ids];ds=dual[ids];sign=np.where(np.sum(qs*qs[:,0:1,:],axis=-1,keepdims=True)<0,-1,1)
        q=np.sum(qs*w*sign,axis=1);dual=np.sum(ds*w*sign,axis=1);norm=np.linalg.norm(q,axis=1,keepdims=True);q/=norm;dual/=norm;dual-=q*np.sum(q*dual,axis=1,keepdims=True)
        return R.from_quat(q).apply(source)+2*multiply(dual,q*[-1,-1,-1,1])[:,:3],v[:,3:5]
    vertices=[];uv=[]
    for n,part in d['parts'].items():
        if n not in p.q:continue
        v=np.asarray(part['vertices']).reshape(-1,8);points=(v[:,:3]+part['pivot'])*[-1,1,1]
        vertices.append((np.c_[points,np.ones(len(points))]@p.matrix(n).T)[:,:3]);uv.append(v[:,3:5])
    return np.concatenate(vertices),np.concatenate(uv)

def main():
    OUT.mkdir(parents=True,exist_ok=True);manifest=[]
    for key,name,clip in [(1,'eva_unit01','hook'),('sachiel','sachiel','cross')]:
        actor=author.Actor(key);data=json.loads((author.OUT/('sachiel_gameplay_r32.json' if actor.angel else 'eva_gameplay_r32_1.json')).read_text());c=data['clips']['r32_'+clip]
        for index,t in enumerate([0,.24,.45,.66,.93]):
            f=c['frames'][round(t*(len(c['frames'])-1))]
            if actor.angel:
                p=actor.rig.pose()
                for n,q in zip(actor.names,f['rotation_wxyz']):w,x,y,z=q;p.setq(n,R.from_quat([-x,-y,z,w]))
                for n,v in f.get('bone_position_xyz',{}).items():p.setp(n,np.asarray(v)*[-1,1,1])
                p.setp('root',np.array(f['root_m'])*112*[-1,1,1])
            else:p=author.rt.eva.decode(f,common_names:=author.common.NAMES)
            v,uv=mesh(actor,p,name);file=f'{name}_{index}';np.savez_compressed(OUT/(file+'.npz'),vertices=v*5/16,uv=uv)
            manifest.append({'file':file,'model':name,'index':index,'row':int(actor.angel),'phase':t})
    (OUT/'manifest.json').write_text(json.dumps(manifest))
if __name__=='__main__':main()
