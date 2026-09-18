"""Audit all measured reachable floor edges and every registered pyramid room."""
from pathlib import Path
import json
import numpy as np
from scipy.ndimage import label,find_objects
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r23/safety';OUT.mkdir(parents=True,exist_ok=True)
d=np.load(ROOT/'artifacts/facility_r23/navigation/check_after/measured_public_space.npz');a=d['blocks'];pal=d['palette'];reachable=d['reachable'];lo=d['lo'];hi=d['hi']
air=np.array([str(s).split('[')[0] in {'minecraft:air','minecraft:cave_air','minecraft:void_air','minecraft:light'} for s in pal])[a]
edges=np.zeros_like(reachable);gaps=[]
for dz,dx in ((1,0),(-1,0),(0,1),(0,-1)):
 neighbour=np.roll(air,(-dz,-dx),(1,2));below=np.roll(neighbour,1,0)&np.roll(neighbour,2,0)&np.roll(neighbour,3,0)
 fall=reachable&neighbour&np.roll(neighbour,-1,0)&below
 fall[:3]=False;fall[-3:]=False;fall[:,:3]=False;fall[:,-3:]=False;fall[:,:,:3]=False;fall[:,:,-3:]=False
 for yy,zz,xx in np.argwhere(fall):gaps.append(dict(floor=[int(xx+lo[0]),int(yy+lo[1]),int(zz+lo[2])],outward=[dx,dz]))
 edges|=fall
components,count=label(edges);clusters=[]
for n,box in enumerate(find_objects(components),1):
 ys,zs,xs=box;coords=np.argwhere(components[box]==n)+[ys.start,zs.start,xs.start];world=coords[:,[2,0,1]]+lo
 clusters.append(dict(count=len(coords),lo=world.min(0).tolist(),hi=world.max(0).tolist(),sample=world[:5].tolist()))
rooms=[]
sources=['artifacts/world_expansion_20260907/geometry_all/places.json','artifacts/first_battle_world_r10/world_art/pyramid_rooms/places.json']
coords=np.argwhere(reachable);points=coords[:,[2,0,1]]+lo;trees={int(y):cKDTree(points[points[:,1]==y]) for y in np.unique(points[:,1])}
for path in sources:
 for room in json.loads((ROOT/path).read_text(encoding='utf8'))['rooms']:
  if not(room['id'].startswith('hq/') or '/pyramid/' in room['id']):continue
  pos=room['entry'];tree=trees.get(pos[1]);distance,near=tree.query(pos) if tree else (float('inf'),None)
  rooms.append(dict(**room,nearest_reachable=tree.data[near].astype(int).tolist() if near is not None else None,distance=round(float(distance),2),entry_connected=bool(distance<=3.1)))
report=dict(reachable_floor_cells=int(reachable.sum()),fall_edges=gaps,clusters=sorted(clusters,key=lambda c:-c['count']),rooms=rooms,room_count=len(rooms),unconnected_room_entries=[r['id'] for r in rooms if not r['entry_connected']])
(OUT/'pyramid_edges.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('REACHABLE',report['reachable_floor_cells'],'FALL EDGES',len(gaps),'clusters',count,'ROOMS',len(rooms),'unconnected',report['unconnected_room_entries'])
for r in report['clusters'][:35]:print(r)
