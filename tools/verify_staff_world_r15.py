"""Read back protected geometry, identities, player state and the completed R15 audit."""
import json,hashlib,uuid,msvcrt
from pathlib import Path
import numpy as np,nbtlib
from regional_voxels import ROOT,WORLD,DIM
from scan_regional_completion import volume
from query_blocks import iter_block_entities
from refine_staff_facilities_r15 import MATERIALS
OUT=ROOT/'artifacts/staff_world_r15'
def uid(tag):return str(uuid.UUID(''.join(f'{int(n)&0xffffffff:08x}' for n in tag)))
def canonical(s):
 name=str(s).split('[')[0];name='projectseele:nerv_structural_panel' if name=='minecraft:reinforced_deepslate' else name;return MATERIALS.get(name,name)
def main():
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);checks={};detail={}
  old=np.load(ROOT/'artifacts/world_refinement_r14/command_before.npz');lo=(2,-449,244);hi=(52,-391,366);a,p=volume(lo,hi);o=old['lo'];before=old['blocks'][lo[1]-o[1]:hi[1]-o[1]+1,lo[2]-o[2]:hi[2]-o[2]+1,lo[0]-o[0]:hi[0]-o[0]+1];left=np.array([canonical(s) for s in old['palette']])[before];right=np.array([canonical(s) for s in p])[a];diff=left!=right
  detail['command_geometry_changed_cells']=int(diff.sum());checks['command_layout_preserved']=not diff.any()
  if diff.any():detail['command_changes']=[dict(pos=[int(x+lo[0]),int(y+lo[1]),int(z+lo[2])],before=str(old['palette'][before[y,z,x]]),after=p[a[y,z,x]]) for y,z,x in np.argwhere(diff)[:30]]
  a,p=volume((6,-329,303),(54,-315,351));panes=int(np.array([s.startswith('projectseele:one_way_glass') and 'pyramid=true' in s for s in p])[a].sum());entities=sum(str(t['id'])=='projectseele:one_way_glass' for _,t in iter_block_entities(WORLD,DIM,(6,-329,303),(54,-315,351)));checks['one_way_glass_preserved']=panes==entities==2344
  checks['piano_book_preserved']=any('Book' in t for _,t in iter_block_entities(WORLD,DIM,(12,-388,356),(12,-388,356)))
  fleet=nbtlib.load(WORLD/'data/projectseele_eva_fleet.dat')['data']['Fleet'];detail['fleet']=[dict(uuid=uid(t['Canonical']),phase=str(t['Phase'])) for t in fleet];checks['canonical_eva_ids']=sorted(t['uuid'] for t in detail['fleet'])==sorted(['4e449cf5-9726-4810-b07b-81aca77d0868','972271c6-dd86-472d-938e-4dc3a363f343','d0694537-3e22-4a39-a92a-cb14330ad150'])
  for name,key in [('projectseele_military_r07.dat','Entities'),('projectseele_r08_details.dat','Members')]:
   rel=Path('dimensions/projectseele/geofront/data')/name;now=nbtlib.load(WORLD/rel)['data'][key];old=nbtlib.load(ROOT/'backups/SEELE_R11_20260909_234420/world'/rel)['data'][key];checks[name+'_identities_preserved']={str(k):uid(v) for k,v in now.items()}=={str(k):uid(v) for k,v in old.items()}
  baseline=Path(json.loads((OUT/'main_backup.json').read_text())['backup']);old=nbtlib.load(baseline/'level.dat')['Data']['Player'];now=nbtlib.load(WORLD/'level.dat')['Data']['Player'];keys=['Pos','Rotation','Dimension','Inventory','EnderItems','SelectedItemSlot','playerGameType','abilities','Health','foodLevel','XpLevel','XpTotal','XpP']
  detail['player_fields']={k:now.get(k)==old.get(k) for k in keys};checks['player_restored']=all(detail['player_fields'].values())
  roster=json.loads((WORLD/'nerv_staff_r15.json').read_text(encoding='utf8'));checks['roster_228']=len(roster['stations'])==228;checks['military_68']=sum(s['role'].startswith('un_') for s in roster['stations'])==68;checks['city_surface_empty']=not any(s['feet'][1]>=0 and s['feet'][0]<6000 for s in roster['stations'])
  path=WORLD/'dimensions/projectseele/geofront/data/projectseele_staff_r15.dat';saved=nbtlib.load(path)['data']['Members'];detail['materialized_staff']=len(saved);checks['named_staff_saved']=all(n in saved for n in ['misato','ritsuko','maya','hyuga','aoba','legacy_ward/nurse','legacy_ward/technician'])
  catalog=json.loads((WORLD/'quality_walk_cases.json').read_text());fresh=json.loads((OUT/'native_world_r15.json').read_text());checks['full_catalog_restored']=len(catalog)==8550;checks['native_201_pass']=len(fresh)==201 and all(r['status']=='pass' for r in fresh)
  user=json.loads((ROOT/'artifacts/world_motion_r11/user_baseline.json').read_text());checks['user_assets_preserved']=all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==v for n,v in user.items())
  report=dict(passed=all(checks.values()),checks=checks,detail=detail);(OUT/'world_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['passed'] else 1)
if __name__=='__main__':main()
