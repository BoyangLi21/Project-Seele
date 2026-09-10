"""Cold final evidence aggregation; no world or asset writes."""
from pathlib import Path
import json,hashlib,uuid,msvcrt
from collections import Counter
import numpy as np
import nbtlib
import scan_regional_completion as scan
from regional_voxels import ROOT,WORLD,DIM
from query_blocks import read_box,iter_block_entities,AIR

OUT=ROOT/'artifacts/world_motion_r11'
def load(path):return json.loads(path.read_text(encoding='utf-8'))
def identity(tag):return str(uuid.UUID(''.join(f'{int(n)&0xffffffff:08x}' for n in tag)))

def main():
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  checks={}
  for name,digest in load(OUT/'user_baseline.json').items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
  checks['user_dirty_resources_preserved']=True
  walks=load(OUT/'map/all_native_walk_first.json');catalog=load(WORLD/'quality_walk_cases.json');assert len(walks)==len(catalog)==8538 and all(x['status']=='pass' for x in walks)
  assert {x['id'] for x in walks}=={x['id'] for x in catalog};checks['native_world_routes']=8538
  terrain={x['name']:dict(x,source='terrain_expanded.json') for x in load(OUT/'terrain_expanded.json')['cases']}
  for x in load(OUT/'terrain_turn_final_pass.json')['cases']:terrain[x['name']]=dict(x,source='terrain_turn_final_pass.json')
  assert len(terrain)==10 and all(x['passed'] for x in terrain.values());checks['terrain_cases']=list(terrain.values())
  for name in ['canonical_first_all_pass.json','canonical_optimized_pass.json']:
   d=load(OUT/name);assert not d['error'] and all(x['passed'] for x in d['checks'])
  d=load(OUT/'mechanics_final_pass.json');assert not d['error'] and all(d['checks'].values());checks['mechanics']=d['checks']
  assert load(OUT/'vertex_equivalence.json')['passed'];checks['vertex_submission']=load(OUT/'vertex_equivalence.json')
  report=load(WORLD/'r11_final_identities.json');assert report['passed'] and report['military_original_identities']==31 and report['industrial_members']==84 and report['un_cell']=='WET';checks['main_identities']=report
  backup=ROOT/'backups/SEELE_R11_20260909_234420/world'
  for relative,key in [('data/projectseele_eva_fleet.dat','Fleet'),('dimensions/projectseele/geofront/data/projectseele_military_r07.dat','Entities'),('dimensions/projectseele/geofront/data/projectseele_r08_details.dat','Members')]:
   now=nbtlib.load(WORLD/relative)['data'][key];old=nbtlib.load(backup/relative)['data'][key]
   if key=='Fleet':assert {identity(x['Canonical']) for x in now}=={identity(x['Canonical']) for x in old}
   else:assert {k:identity(v) for k,v in now.items()}=={k:identity(v) for k,v in old.items()}
  lo=(6,-329,303);hi=(54,-315,351);a,pal=scan.volume(lo,hi);panes=np.array([x.startswith('projectseele:one_way_glass') and 'pyramid=true' in x for x in pal])[a]
  assert int(panes.sum())==2344;bes={pos for pos,be in iter_block_entities(WORLD,DIM,lo,hi) if str(be['id'])=='projectseele:one_way_glass'};assert len(bes)==2344;checks['one_way_glass_preserved']=2344
  for lo,hi,expected in [((6426,77,-6226),(6458,120,-6137),'projectseele:lcl[level=0]'),((6426,77,-6136),(6458,141,-6136),'minecraft:barrier')]:
   a,pal=scan.volume(lo,hi);assert np.array([s==expected for s in pal])[a].all(),expected
  checks['un_hangar']='WET / CLOSED'
  retired=[]
  for item in load(OUT/'map/residue_decisions.json'):
   if item['decision']=='retired':retired.extend(item['component'])
  for pos in retired:assert read_box(WORLD,DIM,tuple(pos),tuple(pos)).get(tuple(pos)) in AIR
  assert len(retired)==8;checks['removed_detached_blocks']=8
  checks['world_census']={k:v for k,v in load(OUT/'map/whole_world_census.json').items() if k not in ['natural_residue_candidates','seconds']}
  for receipt in (OUT/'un/facility_signs').glob('applied_*/receipt.json'):assert load(receipt)['verified']
  checks['un_vehicle_models']=len(load(OUT/'un/vehicle_stencils.json'));assert checks['un_vehicle_models']==7
  result=dict(passed=True,world=str(WORLD),checks=checks,followup='User-approved 23-second fight order; human-motion reauthoring remains the next task, not claimed complete here.')
  (OUT/'final_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print('R11 cold final evidence PASS: 8538 routes, 10 terrain cases, 14 mechanics checks, original 3+31+84 identities, UN capsule, 2344 glazing panes')
if __name__=='__main__':main()
