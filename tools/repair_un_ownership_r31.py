"""Correct measured thigh-shell and shoulder-blade ownership without changing neutral geometry or pivots."""
from pathlib import Path
from collections import defaultdict
import argparse,json,hashlib
import numpy as np
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r31/models'
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
def main(unit):
    folder=ART/('un'+unit);asset=folder/'runtime/assets/projectseele';path=asset/'mesh/eva_prototype.mesh.json';m=json.loads(path.read_text());geo_path=asset/'geo/eva_prototype.geo.json';geo_bytes=geo_path.read_bytes();bones={b['name']:b for b in json.loads(geo_bytes)['minecraft:geometry'][0]['bones']};matrices={}
    def matrix(n):
        if n in matrices:return matrices[n]
        b=bones[n];p=np.array(b['pivot'])*[-1,1,1];r=Rotation.from_euler('xyz',np.array(b.get('rotation',[0,0,0]))*[-1,-1,1],degrees=True).as_matrix();q=np.eye(4);q[:3,:3]=r;q[:3,3]=p-r@p;matrices[n]=matrix(b['parent'])@q if b.get('parent') else q;return matrices[n]
    new={};weights_out={};transfers=[];before_tri=sum(len(p['vertices'])//24 for p in m['parts'].values());max_error=0.;changed_vertices=0
    def append(target,values,weights):
        new.setdefault(target,[]).append(values)
        weights_out.setdefault(target,[]).append(weights)
    for owner,part in m['parts'].items():
        a=np.asarray(part['vertices'],float).reshape(-1,8);count=len(a);rigid=owner not in m.get('jointSkins',{});spec=m.get('jointSkins',{}).get(owner)
        effective={owner:np.ones(count)} if rigid else {n:np.asarray(w,float).copy() for n,w in spec['influences'].items()}
        neutral=(a[:,:3]+part['pivot'])*[-1,1,1];neutral=(np.c_[neutral,np.ones(count)]@matrix(owner).T)[:,:3];normal=(a[:,5:8]*[-1,1,1])@matrix(owner)[:3,:3].T
        target_field=np.full(count,'',object);changed=np.zeros(count,bool)
        for side,sign in [('l',-1),('r',1)]:
            leg='leg_'+side;pylon='pylon_'+side;hip=np.array(bones[leg]['pivot'])*[-1,1,1];knee=np.array(bones['r30_knee_socket_'+side]['pivot'])*[-1,1,1]
            # The observed incorrect shell follows the thigh axis. The
            # centreline skirt is outside this anatomical envelope.
            y=neutral[:,1];x=neutral[:,0]*sign;z=neutral[:,2];t=np.clip((hip[1]-y)/(hip[1]-knee[1]),0,1);axis_x=abs(hip[0])+(abs(knee[0])-abs(hip[0]))*t
            radial=((x-axis_x)/(11.5 if unit=='01' else 9.5))**2+(z/np.where(z<0,29 if unit=='01' else 18,15))**2
            influence=smooth((113-y)/8)*smooth((x-(8.0 if unit=='01' else 7.0))/3.5)*smooth((1.3-radial)/.3)*smooth((y-knee[1]-1)/3)
            from_hip=effective.get('torso_lower',np.zeros(count));amount=from_hip*influence
            if np.any(amount>1e-7):
                effective['torso_lower']=from_hip-amount;effective[leg]=effective.get(leg,np.zeros(count))+amount;changed|=amount>1e-7;target_field[amount>1e-7]='hip_'+side
            p=np.array(bones[pylon]['pivot'])*[-1,1,1]
            radial=((x-abs(p[0]))/(7.8 if unit=='00' else 7.4))**2+((z-p[2])/(16 if unit=='00' else 23))**2
            influence=smooth((y-150)/7)*smooth((1.35-radial)/.4)
            for source in ('arm_'+side,'forearm_'+side):
                original=effective.get(source,np.zeros(count));amount=original*influence
                if np.any(amount>1e-7):
                    effective[source]=original-amount;effective[pylon]=effective.get(pylon,np.zeros(count))+amount;changed|=amount>1e-7;target_field[amount>1e-7]='blade_'+side
        changed_vertices+=int(changed.sum());tri_changed=changed.reshape(-1,3).any(1)
        if not tri_changed.any():append(owner,a,effective);continue
        append(owner,a[np.repeat(~tri_changed,3)],{n:w[np.repeat(~tri_changed,3)] for n,w in effective.items()})
        selected=np.flatnonzero(tri_changed);destinations=defaultdict(list)
        for i in selected:
            rows=slice(i*3,i*3+3);active=[n for n,w in effective.items() if w[rows].max()>1e-6]
            fields=target_field[rows];label=next((str(f) for f in fields if f),'')
            target=active[0] if len(active)==1 else ('r21_join_leg_'+label[-1] if label.startswith('hip') else 'r21_join_pylon_'+label[-1])
            destinations[target].append(i)
        for target,tri_ids in destinations.items():
            idx=(np.asarray(tri_ids)[:,None]*3+np.arange(3)).ravel();v=a[idx].copy();inv=np.linalg.inv(matrix(target));local=(np.c_[neutral[idx],np.ones(len(idx))]@inv.T)[:,:3];v[:,:3]=local*[-1,1,1]-bones[target]['pivot'];v[:,5:8]=(normal[idx]@inv[:3,:3].T)*[-1,1,1]
            # Do not quantize neutral vertex positions during the ownership handoff.
            reconstructed=(np.c_[(v[:,:3]+bones[target]['pivot'])*[-1,1,1],np.ones(len(idx))]@matrix(target).T)[:,:3];max_error=max(max_error,float(np.abs(reconstructed-neutral[idx]).max()))
            append(target,v,{n:w[idx] for n,w in effective.items()});transfers.append({'from':owner,'to':target,'triangles':len(tri_ids),'sourceTriangleIdSha256':hashlib.sha256(np.asarray(tri_ids,dtype=np.int32).tobytes()).hexdigest(),'sourceTriangleRanges':ranges(tri_ids),'neutralBounds':[neutral[idx].min(0).tolist(),neutral[idx].max(0).tolist()]})
    parts={};skins={};max_weight_error=0.
    for n,batches in new.items():
        a=np.concatenate(batches);parts[n]={'pivot':m['parts'][n]['pivot'],'vertices':a.ravel().tolist()};all_names=set().union(*(w.keys() for w in weights_out[n]));all_weights={key:np.concatenate([w.get(key,np.zeros(len(v))) for v,w in zip(batches,weights_out[n])]) for key in all_names};all_weights={key:w for key,w in all_weights.items() if w.max(initial=0)>1e-6}
        total=np.sum(list(all_weights.values()),axis=0);all_weights={key:w/total for key,w in all_weights.items()}
        total=np.sum(list(all_weights.values()),axis=0);max_weight_error=max(max_weight_error,float(np.abs(total-1).max(initial=0)));assert np.allclose(total,1,atol=1e-6),n
        if len(all_weights)!=1 or next(iter(all_weights))!=n:skins[n]={'influences':{key:w.tolist() for key,w in all_weights.items()}}
    m['parts']=parts;m['jointSkins']=skins;m['triangleCount']=sum(len(p['vertices'])//24 for p in parts.values());assert before_tri==m['triangleCount'];assert geo_path.read_bytes()==geo_bytes
    m['r31_ownership']={'method':'Observed actual owner-coloured mesh; anatomical thigh axis/shoulder blade envelopes and existing owner relations; continuous boundary weights','changedVertices':changed_vertices,'neutralMaxError':max_error,'weightMaxError':max_weight_error}
    path.write_text(json.dumps(m,separators=(',',':')));report={'unit':unit,'beforeTriangles':before_tri,'afterTriangles':m['triangleCount'],'changedVertices':changed_vertices,'neutralMaxError':max_error,'weightMaxError':max_weight_error,'rigSha256Unchanged':hashlib.sha256(geo_bytes).hexdigest(),'transfers':transfers};(folder/'ownership_repair.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='transfers'}),flush=True)
def ranges(values):
    result=[];start=previous=values[0]
    for v in values[1:]:
        if v!=previous+1:result.append([int(start),int(previous)]);start=v
        previous=v
    result.append([int(start),int(previous)]);return result
def prune_only(unit):
    path=ART/('un'+unit)/'runtime/assets/projectseele/mesh/eva_prototype.mesh.json';m=json.loads(path.read_text());removed=[]
    for owner,spec in list(m['jointSkins'].items()):
        weights={n:np.asarray(w) for n,w in spec['influences'].items() if max(w,default=0)>1e-6}
        if set(weights)=={owner}:del m['jointSkins'][owner];removed.append(owner)
        else:
            sums=np.sum(list(weights.values()),axis=0);spec['influences']={n:(w/sums).tolist() for n,w in weights.items()}
    path.write_text(json.dumps(m,separators=(',',':')));print('Restored rigid GPU parts:',unit,removed,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',choices=('00','01'),required=True);p.add_argument('--prune-only',action='store_true');a=p.parse_args();prune_only(a.unit) if a.prune_only else main(a.unit)
