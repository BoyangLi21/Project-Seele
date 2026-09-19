"""Candidate drop edges on the connected, documented headquarters circulation."""
from pathlib import Path
import json,gzip
import numpy as np
from scipy.ndimage import label
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r25';WORLD=ROOT/'run/saves/SEELE_R25_REVIEW'
def main():
 out=ART/'edge_audit';out.mkdir(parents=True,exist_ok=True)
 with np.load(ART/'navigation/measured_public_space.npz') as data:
  a=data['blocks'];pal=data['palette'].tolist();lo=data['lo'];hi=data['hi'];walk=data['reachable']
 shapes=json.loads((WORLD/'native_collision_shapes.json').read_text())
 def boxes(state):return shapes.get(state,[] if state.split('[')[0] in ('minecraft:air','minecraft:cave_air','minecraft:void_air','minecraft:light') else [[0,0,0,1,1,1]])
 free=np.array([not any(b[3]>.2 and b[0]<.8 and b[5]>.2 and b[2]<.8 and b[4]>.05 for b in boxes(s)) for s in pal])
 support=np.array([any(b[4]>.7 and b[0]<=.5<=b[3] and b[2]<=.5<=b[5] for b in boxes(s)) for s in pal])
 accepted={'projectseele:nerv_floor_panel','projectseele:nerv_structural_panel','projectseele:nerv_wall_panel','minecraft:smooth_stone','minecraft:white_concrete','minecraft:gray_concrete','minecraft:light_gray_concrete','minecraft:polished_deepslate','projectseele:period_station_floor'}
 public_floor=np.array([s.split('[')[0] in accepted or s.startswith('mtr:escalator_step') for s in pal])
 risks=[];flags=np.zeros(a.shape,bool)
 for y,z,x in np.argwhere(walk):
  if y<4 or y>=a.shape[0]-2 or x<2 or x>=a.shape[2]-2 or z<2 or z>=a.shape[1]-2 or not public_floor[a[y-1,z,x]]:continue
  X,Y,Z=int(x+lo[0]),int(y+lo[1]),int(z+lo[2])
  # The accepted command tiers include intentional desks and their tops.
  # They remain separate from this public-corridor repair classification.
  if 6<=X<=52 and -445<=Y<=-388 and 262<=Z<=365:continue
  for dz,dx in ((0,1),(0,-1),(1,0),(-1,0)):
   zz,xx=z+dz,x+dx
   if walk[y-1:y+2,zz,xx].any() or not free[a[y,zz,xx]] or not free[a[y+1,zz,xx]] or support[a[y-3:y,zz,xx]].any():continue
   flags[y,z,x]=True;risks.append(dict(from_pos=[X,Y,Z],open_side=[int(X+dx),Y,int(Z+dz)],floor=pal[a[y-1,z,x]]))
 labels,count=label(flags,structure=np.ones((3,3,3),bool));clusters=[]
 for i in range(1,count+1):
  points=np.argwhere(labels==i)[:,[2,0,1]]+lo;clusters.append(dict(id=i,positions=len(points),min=points.min(0).tolist(),max=points.max(0).tolist()))
 report=dict(scope='All seven-destination-connected public nodes in the documented headquarters domains; command desk tiers excluded',nodes=int(walk.sum()),candidate_faces=len(risks),clusters=clusters,risks=risks)
 (out/'candidates.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 print('Public nodes',report['nodes'],'candidate drop faces',len(risks),'clusters',clusters,flush=True)
if __name__=='__main__':main()
