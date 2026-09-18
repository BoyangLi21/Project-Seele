"""Promote verified, explicitly edited cells; retain unrelated main-world state.

New FULL chunks may be copied only where the main and cold baseline are still
the same unfinished chunk. Existing FULL chunks use precise state comparisons.
"""
from pathlib import Path
from collections import defaultdict
import argparse,copy,json,msvcrt,shutil,datetime
import numpy as np,nbtlib
import regional_voxels as v
from query_blocks import iter_selected_sections,iter_block_entities,dimension_dir
from transplant_s22_authority import read_region,parse_chunk,build_region,chunk_blob
from apply_s20_approved_semantic_repairs import atomic_replace
from stage_native_transit_repair import hashes
ROOT=v.ROOT;OUT=ROOT/'artifacts/world_repair_r21';MAIN=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906';REVIEW=ROOT/'run/saves/SEELE_R21_REVIEW'
def masks():
 raw=defaultdict(list)
 for receipt in OUT.rglob('receipt.json'):
  directory=receipt.parent
  if not directory.name.startswith('applied_') or not (directory/'delta').is_dir() or (directory/'ROLLED_BACK.json').exists():continue
  d=json.loads(receipt.read_text());
  if not d.get('verified') or Path(d['world']).resolve()!=REVIEW.resolve():continue
  for path in (directory/'delta').glob('c.*.npz'):
   cx,cz=map(int,path.stem.split('.')[1:]);a=np.load(path);raw[cx,cz].append(a['offsets'].astype(np.int32)+int(a['minimum'])*256)
 return {k:np.unique(np.concatenate(parts)) for k,parts in raw.items()}
def region(path):return read_region(path) if path.exists() and path.stat().st_size>=8192 else (bytes(4096),[None]*1024)
def full(blob):return bool(blob) and str(parse_chunk(blob).get('Status','')).removeprefix('minecraft:')=='full'

def armament_plan():
 folder=MAIN/'dimensions/projectseele/geofront/entities';regions={};cargo=None;found=[]
 for path in folder.glob('r.*.mca'):
  if path.stat().st_size<8192:continue
  stamps,blobs=read_region(path);dirty=False
  for slot,blob in enumerate(blobs):
   if not blob:continue
   root=parse_chunk(blob);keep=[]
   for entity in root.get('Entities',[]):
    if str(entity.get('id'))=='projectseele:nerv_armament_station':
     assert cargo is None,'Multiple armament actors require classification'
     cargo=copy.deepcopy(entity);found.append(dict(uuid=list(map(int,entity['UUID'])),position=list(map(float,entity['Pos']))))
    else:keep.append(entity)
   if len(keep)!=len(root.get('Entities',[])):
    root['Entities']=nbtlib.List[nbtlib.Compound](keep);blobs[slot]=chunk_blob(root);dirty=True
  if dirty:regions[path]=(stamps,blobs)
 assert cargo is not None,'Original armament identity missing'
 assert found[0]['position']==[30.5,81.0,-120.5],('Armament moved since survey',found)
 cargo['Pos']=nbtlib.List[nbtlib.Double]([120.5,80,-35.5])
 for k in ('StationState','PhaseTicks'):cargo[k]=nbtlib.Int(0)
 for k in ('LiftProgress','HatchProgress','DoorProgress'):cargo[k]=nbtlib.Float(0)
 cargo['DeployQueued']=nbtlib.Byte(0)
 dest=folder/'r.0.-1.mca';slot=29*32+7
 if dest not in regions:regions[dest]=region(dest)
 stamps,blobs=regions[dest]
 root=parse_chunk(blobs[slot]) if blobs[slot] else nbtlib.File({'DataVersion':nbtlib.Int(3465),'Position':nbtlib.IntArray([7,-3]),'Entities':nbtlib.List[nbtlib.Compound]()})
 root['Entities'].append(cargo);blobs[slot]=chunk_blob(root)
 return {p:build_region(t,b) for p,(t,b) in regions.items()},found
def main(apply=False):
 baseline=json.loads((OUT/'baseline.json').read_text());cold=Path(baseline['backup'])/'world';mask=masks();required=set(mask)
 for name in ('airport/required_chunks.json','airport/flight_required_chunks.json'):
  required.update(map(tuple,json.loads((OUT/name).read_text())))
 proof_path=OUT/'map_acceptance.json'
 if apply:assert json.loads(proof_path.read_text())['passed'],'Complete physical, visual and global audits before installing'
 if apply:assert not (OUT/'main_install.json').exists(),'R21 already installed; make a separate follow-up patch'
 assert hashes(MAIN/'mtr/projectseele/geofront')==hashes(cold/'mtr/projectseele/geofront'),'Main railway changed during review'
 cp=MAIN/'dimensions/projectseele/geofront/data/capabilities.dat';caps=nbtlib.load(cp);g=caps['data']['movingelevators:elevator_groups']['130;269']['group']
 assert not int(g['isMoving']) and int(g['floorData'][0]['isCageAvailable']), 'Public main cabin must be at its lower stop'
 assert list(map(int,g['floors']))==[-442,81], 'Unexpected public lift stops'
 entity_plan,original_armament=armament_plan()
 if apply:main(False)
 stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=OUT/('main_before_'+stamp);groups=defaultdict(list)
 for x,z in required:groups[x//32,z//32].append((x,z))
 generated=[];locks=[]
 try:
  for world in (MAIN,REVIEW):
   lock=(world/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);locks.append(lock)
  assert nbtlib.load(MAIN/'level.dat')['Data']['WorldGenSettings']['seed']==nbtlib.load(REVIEW/'level.dat')['Data']['WorldGenSettings']['seed']
  for (rx,rz),coords in sorted(groups.items()):
   name=f'r.{rx}.{rz}.mca';target=dimension_dir(MAIN,v.DIM)/'region'/name;stamps,blobs=region(target);original=None;source=None;changed=False
   for x,z in coords:
    slot=(z%32)*32+x%32
    if full(blobs[slot]):continue
    if original is None:original=region(dimension_dir(cold,v.DIM)/'region'/name)[1]
    assert blobs[slot]==original[slot],('Main unfinished chunk changed since baseline',x,z)
    if source is None:source=region(dimension_dir(REVIEW,v.DIM)/'region'/name)[1]
    assert full(source[slot]),('Review chunk not FULL',x,z)
    if apply:blobs[slot]=source[slot];changed=True
    generated.append([x,z])
   if changed:
    before=backup/'new_chunk_regions'/name;before.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():shutil.copy2(target,before)
    target.parent.mkdir(parents=True,exist_ok=True);atomic_replace(target,build_region(stamps,blobs))
 finally:
  for lock in locks:lock.close()
 selected={key:set(map(int,offsets//4096)) for key,offsets in mask.items()}
 def measured(world):return {(x,z,y):(p,a) for x,z,y,p,a in iter_selected_sections(world,v.DIM,selected,skip_unfinished=True)}
 before=measured(cold);current=measured(MAIN);after=measured(REVIEW);v.WORLD=MAIN;v.OUT=OUT/'promotion';p=v.Painter();expected=0
 dynamic={tuple(q[:3]) for g in json.loads((REVIEW/'regional_boarding_gates.json').read_text())['gates'] for q in g['stairs']}
 for (cx,cz),offsets in sorted(mask.items()):
  for sy in sorted(selected[cx,cz]):
   key=cx,cz,sy
   if key not in current:continue
   ids=offsets[offsets//4096==sy]%4096;pal,a=current[key];ap,aa=after[key];bp,bb=before.get(key,(pal,a));rows=[]
   for index in ids:
    index=int(index);old=pal[a[index]];target=ap[aa[index]];q=(cx*16+(index&15),sy*16+(index>>8),cz*16+((index>>4)&15))
    if q in dynamic:target='minecraft:air'
    if old==target:continue
    assert old==bp[bb[index]],('User changed an edited main cell',q,old,bp[bb[index]],target)
    rows.append((q,old,target));expected+=1
   i=0
   while i<len(rows):
    q,old,new=rows[i];end=i+1
    while end<len(rows) and rows[end][0][1:]==q[1:] and rows[end][0][0]==rows[end-1][0][0]+1 and rows[end][1:]==(old,new):end+=1
    p.match((*q,rows[end-1][0][0],q[1],q[2]),old,new,'r21/verified_geometry');i=end
  lo=(cx*16,min(selected[cx,cz])*16,cz*16);hi=(cx*16+15,max(selected[cx,cz])*16+15,cz*16+15)
  for q,tag in iter_block_entities(REVIEW,v.DIM,lo,hi):
   code=q[1]*256+(q[2]&15)*16+(q[0]&15)
   if np.searchsorted(offsets,code)<len(offsets) and offsets[np.searchsorted(offsets,code)]==code:p.block_entities[q]=copy.deepcopy(tag)
 p.meta.update(expected_changed_cells=expected,new_full_chunks=generated,source=str(REVIEW),baseline=str(cold),dynamic_boarding_cells_reset_to_air=True)
 if not apply:p.save_plan('verified_final_cells');print('R21 main preflight',expected,'existing cells;',len(generated),'new FULL chunks');return
 result=p.apply('verified_final_cells');assert result['counts']['cells']==expected,('Incomplete main cell application',result,expected)
 metadata=['battlefield_r21.json','regional_boarding_gates.json','nerv_airport_r21.json','regional_plan.json','regional_states.json','quality_walk_cases.json','spatial_contract_r21.json','wayfinding_r21.json']
 for name in metadata:
  source=REVIEW/name
  if not source.exists():continue
  (backup/'metadata').mkdir(parents=True,exist_ok=True)
  if (MAIN/name).exists():shutil.copy2(MAIN/name,backup/'metadata'/name)
  shutil.copy2(source,MAIN/name)
 # Native transit store is changed only if no user edit happened since the
 # frozen source. Other dimensions and every unrelated save file are retained.
 target=MAIN/'mtr/projectseele/geofront';source=REVIEW/'mtr/projectseele/geofront'
 assert hashes(target)==hashes(cold/'mtr/projectseele/geofront'),'Main railway changed during review'
 shutil.copytree(target,backup/'mtr');old=hashes(target);new=hashes(source)
 for name in sorted(set(old)|set(new)):
  path=(target/name).resolve();assert path.is_relative_to(target.resolve())
  if name in new:path.parent.mkdir(parents=True,exist_ok=True);atomic_replace(path,(source/name).read_bytes())
  elif path.is_file():path.unlink()
 assert hashes(target)==new
 shutil.copy2(cp,backup/'capabilities.dat')
 assert not int(g['isMoving']) and int(g['floorData'][0]['isCageAvailable']), 'Public main cabin must be at its lower stop for migration'
 g['floors']=nbtlib.IntArray([-442,75]);g['floorData'][1]['name']=nbtlib.String('第三新东京 · 浅层前厅');caps.save(cp)
 for path,data in entity_plan.items():
  dest=backup/'entities'/path.name;dest.parent.mkdir(parents=True,exist_ok=True)
  if path.exists():shutil.copy2(path,dest)
  atomic_replace(path,data)
  assert path.read_bytes()==data
 (OUT/'main_install.json').write_text(json.dumps(dict(world=str(MAIN),backup=str(backup),changed_cells=expected,generated_chunks=len(generated),verified_geometry=True,armament_identity_preserved=original_armament,armament_position=[120.5,80,-35.5],player_data_unchanged=True),indent=2))
 print('R21 geometry, railway, original armament and recessed lift installed')
def transactional_apply():
 main(False)
 required=set(masks())
 for name in ('airport/required_chunks.json','airport/flight_required_chunks.json'):
  required.update(map(tuple,json.loads((OUT/name).read_text())))
 paths={dimension_dir(MAIN,v.DIM)/'region'/f'r.{x//32}.{z//32}.mca' for x,z in required}
 metadata=['battlefield_r21.json','regional_boarding_gates.json','nerv_airport_r21.json','regional_plan.json','regional_states.json','quality_walk_cases.json','spatial_contract_r21.json','wayfinding_r21.json']
 paths.update(MAIN/n for n in metadata)
 paths.add(MAIN/'dimensions/projectseele/geofront/data/capabilities.dat')
 paths.update(armament_plan()[0])
 for world in (MAIN,REVIEW):
  folder=world/'mtr/projectseele/geofront'
  paths.update(MAIN/'mtr/projectseele/geofront'/n for n in hashes(folder))
 backup=OUT/('transaction_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
 existed=[];absent=[]
 for path in sorted(paths):
  relative=path.resolve().relative_to(MAIN.resolve())
  if path.exists():
   target=backup/'before'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target);existed.append(str(relative))
  else:absent.append(str(relative))
 (backup/'journal.json').write_text(json.dumps(dict(world=str(MAIN),existed=existed,absent=absent),indent=2))
 try:
  main(True)
  (backup/'COMPLETED.json').write_text((OUT/'main_install.json').read_text())
 except BaseException:
  for relative in existed:atomic_replace(MAIN/relative,(backup/'before'/relative).read_bytes())
  for relative in absent:
   path=(MAIN/relative).resolve();assert path.is_relative_to(MAIN.resolve())
   if path.is_file():path.unlink()
  (backup/'ROLLED_BACK.json').write_text(json.dumps({'restored_files':len(existed),'removed_new_files':len(absent)}))
  raise

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--apply',action='store_true');args=a.parse_args()
 transactional_apply() if args.apply else main(False)
