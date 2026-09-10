"""Readback of R14 layout protection, materials, routes and persistent facility identities."""
import json,hashlib,uuid,msvcrt
from collections import Counter
import numpy as np
import nbtlib
from regional_voxels import ROOT,WORLD,DIM
from query_blocks import iter_selected_sections,iter_block_entities,read_box,AIR
from scan_regional_completion import volume
OUT=ROOT/'artifacts/world_refinement_r14'
def identity(tag):return str(uuid.UUID(''.join(f'{int(n)&0xffffffff:08x}' for n in tag)))
def main():
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);checks={}
  selected={}
  census=json.loads((OUT/'reinforced_before.json').read_text())
  for row in census['sections']:selected.setdefault(tuple(row['chunk']),set()).add(row['section'])
  remaining=0;panels=0
  for cx,cz,sy,pal,indices in iter_selected_sections(WORLD,DIM,selected):
   for i,state in enumerate(pal):
    if 'reinforced_deep' in state:remaining+=int(np.count_nonzero(indices==i))
    if state=='projectseele:nerv_structural_panel':panels+=int(np.count_nonzero(indices==i))
  checks['reinforced_remaining_in_replaced_sections']=remaining;checks['structural_panels_in_replaced_sections']=panels
  old=np.load(OUT/'command_before.npz');lo=(2,-449,244);hi=(52,-391,366);now,pal=volume(lo,hi);o=old['lo'];before=old['blocks'][lo[1]-o[1]:hi[1]-o[1]+1,lo[2]-o[2]:hi[2]-o[2]+1,lo[0]-o[0]:hi[0]-o[0]+1]
  def canonical(s):return s.split('[')[0].replace('projectseele:nerv_structural_panel','minecraft:reinforced_deepslate')
  old_names=np.array([canonical(str(s)) for s in old['palette']]);new_names=np.array([canonical(str(s)) for s in pal]);changed=old_names[before]!=new_names[now]
  checks['main_command_geometry_changed_cells']=int(changed.sum());checks['main_command_measured_cells']=int(now.size)
  if changed.any():checks['command_changes']=[{'pos':[int(x+lo[0]),int(y+lo[1]),int(z+lo[2])],'before':str(old['palette'][before[y,z,x]]),'after':pal[now[y,z,x]]} for y,z,x in np.argwhere(changed)[:30]]
  a,p=volume((6,-329,303),(54,-315,351));checks['one_way_glass_cells']=int(np.array([s.startswith('projectseele:one_way_glass') and 'pyramid=true' in s for s in p])[a].sum());checks['one_way_glass_entities']=sum(str(tag['id'])=='projectseele:one_way_glass' for pos,tag in iter_block_entities(WORLD,DIM,(6,-329,303),(54,-315,351)))
  fleet=nbtlib.load(WORLD/'data/projectseele_eva_fleet.dat')['data']['Fleet'];checks['canonical_evas']=sorted(identity(x['Canonical']) for x in fleet)
  for file,key,label in [('projectseele_military_r07.dat','Entities','military'),('projectseele_r08_details.dat','Members','industrial')]:
   tag=nbtlib.load(WORLD/'dimensions/projectseele/geofront/data'/file)['data'][key];checks[label+'_identities']={str(k):identity(v) for k,v in tag.items()}
   baseline=nbtlib.load(ROOT/'backups/SEELE_R11_20260909_234420/world/dimensions/projectseele/geofront/data'/file)['data'][key];checks[label+'_identities_preserved']=checks[label+'_identities']=={str(k):identity(v) for k,v in baseline.items()}
  piano={pos:tag for pos,tag in iter_block_entities(WORLD,DIM,(12,-388,356),(12,-388,356))};checks['piano_lectern_book_preserved']=bool(piano and any('Book' in tag for tag in piano.values()))
  routes=json.loads((OUT/'native_world_complete.json').read_text(encoding='utf8'));catalog=json.loads((WORLD/'quality_walk_cases.json').read_text(encoding='utf8'));checks['native_routes']=len(routes);checks['native_routes_pass']=all(r['status']=='pass' for r in routes) and {r['id'] for r in routes}=={r['id'] for r in catalog}
  dirty=json.loads((ROOT/'artifacts/world_motion_r11/user_baseline.json').read_text());checks['user_resources_preserved']=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value for name,value in dirty.items())
  checks['receipts']=[{'path':str(p.relative_to(ROOT)),**json.loads(p.read_text())} for p in OUT.glob('*/applied_*/receipt.json')]
  passed=remaining==0 and not changed.any() and checks['one_way_glass_cells']==checks['one_way_glass_entities']==2344 and checks['piano_lectern_book_preserved'] and checks['native_routes_pass'] and checks['user_resources_preserved'] and checks['military_identities_preserved'] and checks['industrial_identities_preserved'] and checks['canonical_evas']==sorted(['4e449cf5-9726-4810-b07b-81aca77d0868','972271c6-dd86-472d-938e-4dc3a363f343','d0694537-3e22-4a39-a92a-cb14330ad150'])
  (OUT/'world_verification.json').write_text(json.dumps(dict(passed=bool(passed),checks=checks),ensure_ascii=False,indent=2),encoding='utf8');print('R14 world verification',passed,{k:v for k,v in checks.items() if not k.endswith('identities') and k!='receipts'},flush=True)
if __name__=='__main__':main()
