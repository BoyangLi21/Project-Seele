"""Export evaluated private actor triangles, with both side and front review views."""
import argparse,json,struct,hashlib
import numpy as np
from pathlib import Path
import author_first_battle_r10 as b
import author_eva_rifle_stances_r06 as mesh
from preview_first_battle_r12 import angel_pose
OUT=b.ROOT/'artifacts/world_refinement_r14'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--clip',default='run/projectseele-local-maps/first_battle_r12.json');ap.add_argument('--label',default='before');ap.add_argument('--times',default='16.3,16.8,17.3,17.8,18.3,18.6');args=ap.parse_args()
 dest=OUT/('pair_'+args.label);dest.mkdir(parents=True,exist_ok=True)
 data=json.loads((b.ROOT/args.clip).read_text());parts=[n for n in mesh.MESH if n not in ['cannon','knife','lance','n2','entry_plug']]
 uv=np.vstack([np.array(b.eva.mesh['parts'][n]['vertices']).reshape(-1,8)[:,3:5] for n in parts]);raw=json.loads((b.eva.PACK/'mesh/sachiel.mesh.json').read_text());av=np.array(raw['parts']['root']['vertices']).reshape(-1,8);_,inverse=np.unique(np.round(av[:,:3]*[-1,1,1],6),axis=0,return_inverse=True)
 cached=None
 if 'surface_deformation_r14' in data:
  path=b.ROOT/args.clip;blob=(path.parent/'sachiel_wrap_r14.bin').read_bytes();start,count,fps,unique,full,base=struct.unpack('>6i',blob[4:28]);index=np.frombuffer(blob,dtype='>i4',count=full,offset=60);cache_uv=np.frombuffer(blob,dtype='>f4',count=full*2,offset=60+full*4).reshape(-1,2);cached=np.frombuffer(blob,dtype='>f4',offset=60+full*12).reshape(count,unique,3)
 records=[]
 for t in map(float,args.times.split(',')):
  f=t*30
  if abs(f-round(f))<.00002:f=float(round(f))
  i=int(np.floor(f));j=min(i+1,len(data['eva']['frames'])-1);blend=f-i;h=b.eva.decode(data['eva']['frames'][i],data['eva']['bones']);a=angel_pose(data['angel']['frames'][i],data['angel']['bones'])
  if blend>0:
   next_h=b.eva.decode(data['eva']['frames'][j],data['eva']['bones']);next_a=angel_pose(data['angel']['frames'][j],data['angel']['bones'])
   for pose,nxt in [(h,next_h),(a,next_a)]:
    for n in list(pose.q):pose.setq(n,b.qmix(pose.q[n],nxt.q[n],blend));pose.setp(n,b.mix(pose.p[n],nxt.p[n],blend))
  hero=np.vstack([mesh.vertices(h,n) for n in parts])*b.HEROMIRROR*5/16+b.mix(data['eva']['root_blocks'][i],data['eva']['root_blocks'][j],blend);enemy=a.skin()[inverse]*5/16+b.mix(data['angel']['root_blocks'][i],data['angel']['root_blocks'][j],blend)
  if cached is not None and start<=f<=start+count-1:enemy=b.mix(cached[i-start,index],cached[min(i-start+1,count-1),index],blend)
  normals=None
  if cached is not None and start<=f<=start+count-1:
   positions=b.mix(cached[i-start],cached[min(i-start+1,count-1)],blend);faces=index.reshape(-1,3);tri=positions[faces];normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);normals=np.zeros_like(positions)
   for k in range(3):np.add.at(normals,faces[:,k],normal)
   normals/=np.maximum(1e-8,np.linalg.norm(normals,axis=1))[:,None];normals=normals[index]
  name=f'{i:04d}'+(f'_{round(blend*1000):03d}' if blend>0 else '');np.savez_compressed(dest/(name+'.npz'),hero=hero,hero_uv=uv,angel=enemy,angel_uv=cache_uv if normals is not None else av[:,3:5],**({'angel_normals':normals} if normals is not None else {}));records.append(dict(name=name,time=t))
 (dest/'manifest.json').write_text(json.dumps(records));print(dest,flush=True)
 (dest/'source.json').write_text(json.dumps({'clip':hashlib.sha256((b.ROOT/args.clip).read_bytes()).hexdigest(),'surface':data.get('surface_deformation_r14','')}))
 (dest/'hero_parts.json').write_text(json.dumps([n for n in parts for _ in range(len(b.eva.mesh['parts'][n]['vertices'])//24)]))
if __name__=='__main__':main()
