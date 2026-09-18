"""Move the personnel bridge outside the actual modelled hoist envelope.

The old bridge is reverted cell-for-cell to its cold R20 substrate. The
replacement is tied into the existing outer shell, below its roof beams.
"""
import copy,json,msvcrt
from pathlib import Path
import nbtlib
import regional_voxels as v
from query_blocks import read_box,iter_block_entities
ROOT=v.ROOT;OUT=ROOT/'artifacts/world_repair_r21';WORLD=ROOT/'run/saves/SEELE_R21_REVIEW'
FLOOR='projectseele:nerv_floor_panel';WALL='projectseele:nerv_wall_panel';STRUCT='projectseele:nerv_structural_panel';GLASS='projectseele:clear_glass';AIR='minecraft:air'

def main():
 with (WORLD/'session.lock').open('r+b') as lock:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 cold=Path(json.loads((OUT/'baseline.json').read_text())['backup'])/'world'
 v.WORLD=WORLD;v.OUT=OUT/'hoist_separation';p=v.Painter()
 lo=(-34,-369,-226);hi=(93,-361,-216)
 old=read_box(WORLD,v.DIM,lo,hi);base=read_box(cold,v.DIM,lo,hi)
 for y in range(lo[1],hi[1]+1):
  for z in range(lo[2],hi[2]+1):
   x=lo[0]
   while x<=hi[0]:
    q=x,y,z;s,t=old[q],base[q];end=x
    while end<hi[0] and (old[end+1,y,z],base[end+1,y,z])==(s,t):end+=1
    if s!=t:p.match((x,y,z,end,y,z),s,t,'r21/retire_hoist_intruding_gallery')
    x=end+1
 def b(box,state):p.fill(*box,state,'r21/separated_observation_gallery','owned')
 # Close the retired branch where it meets the north/south personnel spine.
 b((94,-369,-226,94,-361,-216),STRUCT);b((94,-368,-226,94,-368,-216),FLOOR)
 b((94,-367,-226,94,-362,-216),WALL);b((94,-366,-226,94,-363,-216),GLASS)
 # 16 metres south of the old centreline: the hoist's entire Z extent, up
 # to its service deck at craneZ+3.2, remains outside the north wall.
 b((-34,-369,-210,94,-361,-200),STRUCT)
 b((-33,-367,-209,94,-362,-201),AIR);b((-33,-368,-209,94,-368,-201),FLOOR)
 for z in (-210,-200):
  b((-33,-367,z,93,-362,z),WALL);b((-33,-366,z,93,-363,z),GLASS)
 for x in (-34,10,52,94):
  for z in (-210,-200):b((x,-369,z,x,-357,z),STRUCT)
 for x in range(-30,90,12):b((x,-361,-207,x+1,-361,-204),'projectseele:nerv_strip_light')
 # Exact two full MTR belts, with the central 5 m lane and flat end landings.
 for z,direction in [(-209,True),(-202,False)]:
  for x in range(-25,86):
   for dz,side in [(0,'left'),(1,'right')]:
    b((x,-368,z+dz,x,-368,z+dz),f'mtr:escalator_step[direction={str(direction).lower()},facing=east,orientation=flat,side={side},status=true]')
    b((x,-367,z+dz,x,-367,z+dz),f'mtr:escalator_side[facing=east,orientation=flat,side={side}]')
 # Full-width landing into the original requested entrance at X90/Z-221.
 b((94,-368,-209,111,-368,-201),FLOOR);b((94,-367,-209,111,-362,-201),AIR)
 # Move the three existing observation panels, keeping their content and
 # source identity. All direction panels get larger type and a taller face.
 records=json.loads((WORLD/'wayfinding_r21.json').read_text(encoding='utf8'))
 for r in records:
  q=tuple(r['position']);tag=copy.deepcopy(dict(iter_block_entities(WORLD,v.DIM,q,q))[q])
  if q[2]==-225:
   q=(q[0],q[1],q[2]+16);r['position']=list(q);tag['z']=nbtlib.Int(q[2])
   for backing in r['full_backing']:backing['pos'][2]+=16
  if q==(112,-365,-220):
   r['rows'][2]='后侧观察廊：沿东廊向南16米';tag['Row2']=nbtlib.String(r['rows'][2])
  p.put(*q,f"projectseele:station_departure_board[facing={r['facing']},wayfinding=true]",'r21/readable_direction_panel','owned');p.block_entities[q]=tag
 p.meta.update(mechanical_clearance={'north_wall_z':-210,'hoist_rest_z':-221.5,'hoist_maximum_positive_z':3.2,'gap':8.3},retired_bounds=[*lo,*hi],new_bounds=[-34,-369,-210,94,-361,-200])
 p.apply('personnel_bridge_outside_hoists')
 (WORLD/'wayfinding_r21.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
 cases=json.loads((WORLD/'quality_walk_cases.json').read_text());changed=[]
 for r in cases:
  if 'r21/upper_three_cages' in r['id']:
   r['path']=[[102.5,-367,-221.5],[102.5,-367,-205.5],[-29.5,-367,-205.5]]
   if r['id'].endswith('/return'):r['path'].reverse()
   changed.append(r)
 (WORLD/'quality_walk_cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8')
 (OUT/'full_walk_catalogue.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8')
 (OUT/'hoist_separation/retest_cases.json').write_text(json.dumps(changed,indent=2))
 for path in (OUT/'facility_contract.json',OUT/'spatial_contract_r21.json',WORLD/'spatial_contract_r21.json'):
  data=json.loads(path.read_text())
  for section in data['sections']:
   if section['id']=='commander_gallery':section['rects']=[[94,113,-287,-82],[-34,94,-210,-200],[-34,113,-287,-275]]
  for belt in data['belts']:
   if belt['id'].startswith('observer_cross/'):belt['origin'][2]+=16
  for r in data.get('walks',[]):
   replacement=next((c for c in changed if c['id']==r['id']),None)
   if replacement:r['path']=replacement['path']
  path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
 shots=ROOT/'run/projectseele-local-maps/r21_worldtour.json';data=json.loads(shots.read_text())
 for shot in data:
  if shot['name']=='three_cage_cross_gallery':shot['eye'][2]+=16;shot['target'][2]+=16
  if shot['name']=='nerv_airport_overview':shot['eye']=[775,190,73];shot['target']=[900,72,-104];shot['renderDistance']=24;shot['warmupTicks']=400
 shots.write_text(json.dumps(data,indent=2))
 print('Hoist-separated bridge and 12 larger signs installed; 2 route cases to retest')

if __name__=='__main__':main()
