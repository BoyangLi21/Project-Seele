"""Join freestanding sign poles to their frames and specify the U1/U2 interchange."""
from pathlib import Path
import copy,gzip,json,nbtlib,numpy as np
from scipy.spatial import cKDTree
import regional_voxels as v
from query_blocks import read_box,iter_block_entities
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R25_REVIEW';OUT=ROOT/'artifacts/facility_r25/map_finish'
def main():
 v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();d=json.loads((ROOT/'artifacts/facility_r25/station_maps/contract.json').read_text(encoding='utf8'))
 with gzip.open(WORLD/'nerv_routes_r24.json.gz','rt',encoding='utf8') as stream:g=json.load(stream)
 nodes=np.asarray(g['nodes']);tree=cKDTree(nodes[:,:3]);added=0;changed=0
 for row in d['boards']:
  for x,y,z in row['supports']:
   q=(x,y+1,z);state=read_box(WORLD,v.DIM,q,q)[q]
   assert state=='minecraft:air',('Unexpected sign frame cell',q,state)
   p.match((*q,*q),state,'minecraft:iron_bars[east=false,north=false,south=false,waterlogged=false,west=false]','r25/route_map_post_meets_panel_frame');added+=1
  if row['station']!='NERV 总部':continue
  q=tuple(row['position']);original=next(iter_block_entities(WORLD,v.DIM,q,q))[1];tag=copy.deepcopy(original);node=tree.query(row['reader'])[1];cursor=node;goal=3 if row['line']=='U1' else 2
  for _ in range(6):cursor=int(nodes[cursor,3+goal])
  nx,nz={'north':(0,-1),'south':(0,1),'east':(1,0),'west':(-1,0)}[row['facing']];dx,dy,dz=nodes[cursor,:3]-nodes[node,:3];r=dx*nz-dz*nx;f=-dx*nx-dz*nz
  arrow='→' if r>abs(f) else '←' if -r>abs(f) else '↑' if f>=0 else '↶'
  target='U2 整备线 · 发射区' if row['line']=='U1' else 'U1 总部线 · 地面入口'
  rows=list(map(str,tag['MapRows']));rows[-1]=arrow+'  换乘 '+target+' / 站厅步道'
  tag['MapRows']=nbtlib.List[nbtlib.String]([nbtlib.String(s) for s in rows]);state=read_box(WORLD,v.DIM,q,q)[q]
  p.update_block_entity(q,state,original,tag,'r25/explicit_hq_interchange');changed+=1
 p.meta.update(upper_post_segments=added,hq_interchange_maps=changed);p.apply('connected_sign_posts_and_hq_transfer')
 (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Joined posts',added,'HQ interchange maps',changed)
if __name__=='__main__':main()
