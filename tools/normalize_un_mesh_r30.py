"""Remove collapsed triangles and provide finite unit normals after geometry clipping."""
import json
from pathlib import Path
import numpy as np
def normalize(mesh):
    removed=repaired=0
    for name,part in mesh['parts'].items():
        data=np.asarray(part['vertices']).reshape(-1,3,8);assert np.isfinite(data).all(),name
        cross=np.cross(data[:,1,:3]-data[:,0,:3],data[:,2,:3]-data[:,0,:3]);length=np.linalg.norm(cross,axis=1);keep=length>1e-10;removed+=int((~keep).sum());data=data[keep];cross=cross[keep];length=length[keep];v=data.reshape(-1,8);n=np.linalg.norm(v[:,5:8],axis=1);bad=n<1e-6;repaired+=int(bad.sum())
        # Stored Geo-space X is reflected; the runtime restores it together
        # with these normals, so its outward normal is opposite stored winding.
        if bad.any():v[bad,5:8]=-np.repeat(cross/length[:,None],3,axis=0)[bad]
        # Generated hardware uses solid material cells. Keep sampling well
        # inside their centres: a bake's island margin can otherwise bleed
        # neighbouring white/gold cells into the tips of tiny triangles.
        if 'r30_palette_region' in mesh:
            palette=data[:,:,3].min(1)>=.937499
            if palette.any():
                u=data[palette,:,3].mean(1);vv=data[palette,:,4].mean(1);col=np.clip(np.floor((u-.9375)/.0625*4),0,3);row=np.clip(np.floor(vv*3),0,2)
                data[palette,:,3]=(.9375+(col+.5)*.0625/4)[:,None]+np.array([-2,2,-2])[None,:]/4096
                data[palette,:,4]=((row+.5)/3)[:,None]+np.array([-2,-2,2])[None,:]/4096
        v[:,5:8]/=np.linalg.norm(v[:,5:8],axis=1,keepdims=True);assert np.isfinite(v).all();part['vertices']=np.round(v,6).ravel().tolist()
        if name in mesh['jointSkins']:
            spec=mesh['jointSkins'][name];spec['influences']={key:np.asarray(values)[np.repeat(keep,3)].tolist() for key,values in spec['influences'].items()}
    mesh['triangleCount']=sum(len(p['vertices'])//24 for p in mesh['parts'].values());return removed,repaired
if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]/'artifacts/facility_r30/models'
    for unit in ('00','01'):
        folder=root/('un'+unit);p=folder/'runtime/assets/projectseele/mesh/eva_prototype.mesh.json';data=json.loads(p.read_text());removed,repaired=normalize(data);p.write_text(json.dumps(data,separators=(',',':')))
        report=json.loads((folder/'mechanical_finish.json').read_text());report.update(triangle_count=data['triangleCount'],degenerate_faces_removed=removed,zero_normals_repaired=repaired);(folder/'mechanical_finish.json').write_text(json.dumps(report,indent=2));print(unit,data['triangleCount'],removed,repaired,flush=True)
