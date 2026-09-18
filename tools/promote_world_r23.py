"""Transactional promotion of R22/R23 exact cells and new registered equipment."""
from pathlib import Path
from collections import defaultdict
import argparse,copy,datetime,json,msvcrt,shutil,uuid
import numpy as np,nbtlib
import regional_voxels as v
from query_blocks import iter_selected_sections,iter_block_entities,dimension_dir
from transplant_s22_authority import read_region,parse_chunk,build_region,chunk_blob
from apply_s20_approved_semantic_repairs import atomic_replace
from stage_native_transit_repair import hashes
ROOT=v.ROOT;OUT=ROOT/'artifacts/facility_r23/promotion';MAIN=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906';REVIEW=ROOT/'run/saves/SEELE_R22_REVIEW'
EXTERNAL_LOCKS=None
def region(p):return read_region(p) if p.exists() and p.stat().st_size>=8192 else (bytes(4096),[None]*1024)
def full(blob):return blob is not None and str(parse_chunk(blob).get('Status','')).removeprefix('minecraft:')=='full'
def masks():
 raw=defaultdict(list)
 for root in (ROOT/'artifacts/access_r22',ROOT/'artifacts/facility_r23'):
  for path in root.rglob('c.*.npz'):
   if path.parent.name!='delta' or not path.parent.parent.name.startswith('applied_') or path.is_relative_to(OUT):continue
   if (path.parent.parent/'ROLLED_BACK.json').exists():continue
   # The first R22 application wrote four regions before failing on an
   # unfinished chunk. Its actual deltas also belong to the combined mask.
   x,z=map(int,path.stem.split('.')[1:]);a=np.load(path);raw[x,z].append(a['offsets'].astype(np.int32)+int(a['minimum'])*256)
 boxes=[(11,-390,351,17,-385,358),(6425,77,-6227,6459,141,-6136),(6265,77,-6227,6299,141,-6136)]
 for row in json.loads((ROOT/'artifacts/world_rebuild_r20/lifts/sweep_masks.json').read_text()):boxes.append(tuple(row['sweep'][0]+row['sweep'][1]))
 for loX,loY,loZ,hiX,hiY,hiZ in boxes:
  for x in range(loX//16,hiX//16+1):
   for z in range(loZ//16,hiZ//16+1):
    a=np.array([y*256+(zz&15)*16+(xx&15) for y in range(loY,hiY+1) for zz in range(max(loZ,z*16),min(hiZ,z*16+15)+1) for xx in range(max(loX,x*16),min(hiX,x*16+15)+1)],dtype=np.int32);raw[x,z].append(a)
 return {q:np.unique(np.concatenate(parts)) for q,parts in raw.items()}
def datafile(world,name):
 for p in (world/'data'/name,world/'dimensions/projectseele/geofront/data'/name):
  if p.exists():return p
 raise FileNotFoundError(name)
def main(apply=False):
 OUT.mkdir(parents=True,exist_ok=True);cold=Path(json.loads((ROOT/'artifacts/access_r22/baseline.json').read_text())['backup'])/'world';mask=masks();selected={q:set(map(int,ids//4096)) for q,ids in mask.items()};expected=0;generated=[];mtr=Path('mtr/projectseele/geofront')
 assert hashes(MAIN/mtr)==hashes(cold/mtr),'Main railway changed after the R22 baseline'
 if apply:
  assert json.loads((ROOT/'artifacts/facility_r23/final_acceptance.json').read_text())['passed']
  assert not (OUT/'installed.json').exists(),'Already installed; author a follow-up patch'
 groups=defaultdict(list)
 for x,z in mask:groups[x//32,z//32].append((x,z))
 stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=OUT/('main_before_'+stamp);saved={};absent=set();locks=[]
 def save(p):
  rel=p.resolve().relative_to(MAIN.resolve())
  if str(rel) in saved or str(rel) in absent:return
  if p.exists():
   dst=backup/'before'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst);saved[str(rel)]=str(dst)
  else:absent.add(str(rel))
 def write(p,data):
  save(p);p.parent.mkdir(parents=True,exist_ok=True);atomic_replace(p,data)
 try:
  for world in (MAIN,REVIEW):
   if EXTERNAL_LOCKS is not None:continue
   lock=(world/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);locks.append(lock)
  assert nbtlib.load(MAIN/'level.dat')['Data']['WorldGenSettings']['seed']==nbtlib.load(REVIEW/'level.dat')['Data']['WorldGenSettings']['seed']
  for (rx,rz),coords in groups.items():
   relative=Path('dimensions/projectseele/geofront/region')/f'r.{rx}.{rz}.mca';target=MAIN/relative;stamps,blobs=region(target);original=region(cold/relative)[1];source=None;dirty=False
   for x,z in coords:
    slot=(z&31)*32+(x&31)
    if full(blobs[slot]):continue
    assert blobs[slot]==original[slot],('Main unfinished terrain changed',x,z)
    if source is None:source=region(REVIEW/relative)[1]
    assert full(source[slot]),('Source chunk not full',x,z)
    generated.append([x,z])
    if apply:blobs[slot]=source[slot];dirty=True
   if dirty:write(target,build_region(stamps,blobs))
 finally:
  for lock in locks:lock.close()
 def measure(world):return {(x,z,y):(p,a) for x,z,y,p,a in iter_selected_sections(world,v.DIM,selected,skip_unfinished=True)}
 before,current,after=measure(cold),measure(MAIN),measure(REVIEW);v.WORLD=MAIN;v.OUT=OUT;p=v.Painter();conflicts=[]
 for (cx,cz),offsets in sorted(mask.items()):
  for sy in sorted(selected[cx,cz]):
   key=cx,cz,sy
   if key not in current:continue
   ids=offsets[offsets//4096==sy]%4096;pal,a=current[key];ap,aa=after[key];bp,bb=before.get(key,(pal,a));changes=[]
   for index in ids:
    index=int(index);old=pal[a[index]];target=ap[aa[index]];q=(cx*16+(index&15),sy*16+(index>>8),cz*16+((index>>4)&15))
    if old==target:continue
    if old!=bp[bb[index]]:conflicts.append(dict(pos=q,current=old,baseline=bp[bb[index]],proposed=target));continue
    changes.append((q,old,target));expected+=1
   i=0
   while i<len(changes):
    q,old,new=changes[i];end=i+1
    while end<len(changes) and changes[end][0][1:]==q[1:] and changes[end][0][0]==changes[end-1][0][0]+1 and changes[end][1:]==(old,new):end+=1
    p.match((*q,changes[end-1][0][0],q[1],q[2]),old,new,'r23/verified_final_geometry');i=end
  lo=(cx*16,min(selected[cx,cz])*16,cz*16);hi=(cx*16+15,max(selected[cx,cz])*16+15,cz*16+15)
  for q,tag in iter_block_entities(REVIEW,v.DIM,lo,hi):
   code=q[1]*256+(q[2]&15)*16+(q[0]&15);idx=np.searchsorted(offsets,code)
   if idx<len(offsets) and offsets[idx]==code:p.block_entities[q]=copy.deepcopy(tag)
 assert not conflicts,conflicts[:20]
 p.meta.update(expected_cells=expected,new_full_chunks=generated,combined_r22_r23=True,partial_r22_delta_included=True)
 if not apply:p.save_plan('verified_final_cells');print('Promotion preflight',expected,'cells;',len(generated),'new full chunks');return
 for cx,cz in mask:save(MAIN/'dimensions/projectseele/geofront/region'/f'r.{cx//32}.{cz//32}.mca')
 try:
  applied=p.apply('verified_final_cells',session_lock=None if EXTERNAL_LOCKS is None else EXTERNAL_LOCKS[MAIN]);assert applied['counts']['cells']==expected
  names=['regional_plan.json','regional_states.json','quality_walk_cases.json','native_transit_r20.json','native_transit_r22.json','native_transit_r23.json','regional_wayfinding.json','military_readiness_r23.json','.projectseele_command_sliding_doors_r01.json','spatial_contract_r23.json','wayfinding_r23.json']
  for name in names:
   source=REVIEW/name
   if source.exists():write(MAIN/name,source.read_bytes())
  old,new=hashes(MAIN/mtr),hashes(REVIEW/mtr)
  for name in sorted(set(old)|set(new)):
   path=(MAIN/mtr/name).resolve();assert path.is_relative_to((MAIN/mtr).resolve())
   if name in new:write(path,(REVIEW/mtr/name).read_bytes())
   elif path.exists():save(path);path.unlink()
  assert hashes(MAIN/mtr)==new
  cp=MAIN/'dimensions/projectseele/geofront/data/capabilities.dat';source=nbtlib.load(REVIEW/'dimensions/projectseele/geofront/data/capabilities.dat');caps=nbtlib.load(cp);baseline=nbtlib.load(cold/'dimensions/projectseele/geofront/data/capabilities.dat')
  key='movingelevators:elevator_groups';assert caps['data'][key].snbt()==baseline['data'][key].snbt(),'Main elevators changed during review'
  save(cp);caps['data'][key]=copy.deepcopy(source['data'][key]);caps.save(cp)
  military=datafile(REVIEW,'projectseele_military_r07.dat');target=datafile(MAIN,'projectseele_military_r07.dat');source=nbtlib.load(military);state=nbtlib.load(target);ids={k:copy.deepcopy(value) for k,value in source['data']['Entities'].items() if k.startswith(('vehicle/r23/','owner/vehicle/r23/'))};wanted={tuple(map(int,q)) for q in ids.values()};assert len(wanted)==198
  from verify_main_r20 import entities
  incoming=entities(REVIEW);present=entities(MAIN);cold_entities=entities(cold);assert not wanted&set(present);assert wanted<=set(incoming)
  def numeric_id(value):
   raw=uuid.UUID(value).bytes;return tuple(int.from_bytes(raw[i:i+4],'big',signed=True) for i in range(0,16,4))
  un_check=json.loads((ROOT/'artifacts/facility_r23/validation/client_un_pass.json').read_text());relocate={numeric_id(row[k]) for row in un_check['checks'] for k in ('airframe','plug')};assert len(relocate)==4
  for uid in relocate:
   assert uid in incoming and uid in present and uid in cold_entities
   assert present[uid].snbt()==cold_entities[uid].snbt(),('Original UN actor changed in Main during review',uid)
   assert not incoming[uid].get('Passengers'),('UN recovery must finish before promotion',uid)
  regions={};found=set()
  for path in (MAIN/'dimensions/projectseele/geofront/entities').glob('r.*.mca'):
   if path.stat().st_size<8192:continue
   stamps,blobs=region(path);dirty=False
   for slot,blob in enumerate(blobs):
    if not blob:continue
    root=parse_chunk(blob);kept=[];changed=False
    for entity in root.get('Entities',[]):
     uid=tuple(map(int,entity.get('UUID',[])))
     if uid in relocate:
      assert not entity.get('Passengers'),('A Main UN actor still has an occupant',uid);found.add(uid);changed=True
     else:kept.append(entity)
    if changed:root['Entities']=nbtlib.List[nbtlib.Compound](kept);blobs[slot]=chunk_blob(root);dirty=True
   if dirty:regions[path]=(stamps,blobs)
  assert found==relocate,('Could not locate the four original UN actors',relocate-found)
  for uid in wanted|relocate:
   entity=copy.deepcopy(incoming[uid]);x,z=math_floor(float(entity['Pos'][0]))//16,math_floor(float(entity['Pos'][2]))//16;path=MAIN/'dimensions/projectseele/geofront/entities'/f'r.{x//32}.{z//32}.mca'
   if path not in regions:regions[path]=region(path)
   stamps,blobs=regions[path];slot=(z&31)*32+(x&31);root=parse_chunk(blobs[slot]) if blobs[slot] else nbtlib.File({'DataVersion':nbtlib.Int(3465),'Position':nbtlib.IntArray([x,z]),'Entities':nbtlib.List[nbtlib.Compound]()});root['Entities'].append(entity);blobs[slot]=chunk_blob(root)
  for path,(stamps,blobs) in regions.items():write(path,build_region(stamps,blobs))
  save(target);state['data']['Entities'].update(ids)
  for field in ('Phase','Cursor'):state['data'][field]=copy.deepcopy(source['data'][field])
  assert str(state['data']['Phase'])=='WET';state.save(target)
  annex=datafile(MAIN,'projectseele_un01_annex_r20.dat');a=nbtlib.load(annex);b=nbtlib.load(datafile(REVIEW,annex.name));assert list(a['data']['Unit'])==list(b['data']['Unit']);save(annex)
  for field in ('Phase','Cursor'):a['data'][field]=copy.deepcopy(b['data'][field])
  assert str(a['data']['Phase'])=='WET';a.save(annex)
  for name in ['projectseele_un_locations_r22.dat']:
   try:source=datafile(REVIEW,name)
   except FileNotFoundError:continue
   dest=MAIN/source.relative_to(REVIEW)
   if not dest.exists():write(dest,source.read_bytes())
  receipt=dict(installed=True,world=str(MAIN),source=str(REVIEW),changed_cells=expected,new_full_chunks=generated,added_vehicles=144,added_control_nodes=54,original_un_actors_returned_with_same_uuids=4,un_bays_wet_closed=True,backup=str(backup),player_data_unchanged=True)
  (OUT/'installed.json').write_text(json.dumps(receipt,indent=2));(backup/'journal.json').write_text(json.dumps(dict(saved=saved,previously_absent=sorted(absent)),indent=2));print('R22/R23 main promotion complete',receipt)
 except BaseException:
  for rel,src in saved.items():atomic_replace(MAIN/rel,Path(src).read_bytes())
  for rel in absent:
   path=(MAIN/rel).resolve();assert path.is_relative_to(MAIN.resolve())
   if path.is_file():path.unlink()
  (backup/'ROLLED_BACK.json').write_text(json.dumps(dict(saved=saved,previously_absent=sorted(absent)),indent=2));raise
def math_floor(value):return int(__import__('math').floor(value))
def transactional_apply():
 global EXTERNAL_LOCKS
 OUT.mkdir(parents=True,exist_ok=True);stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=OUT/('transaction_'+stamp);backup.mkdir();locks={}
 try:
  for world in (MAIN,REVIEW):
   lock=(world/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);locks[world]=lock
  EXTERNAL_LOCKS=locks;main(False)
  paths={MAIN/'dimensions/projectseele/geofront/region'/f'r.{x//32}.{z//32}.mca' for x,z in masks()}
  for world in (MAIN,REVIEW):
   paths.update(MAIN/p.relative_to(world) for p in (world/'dimensions/projectseele/geofront/entities').glob('r.*.mca'))
   paths.update(MAIN/'mtr/projectseele/geofront'/name for name in hashes(world/'mtr/projectseele/geofront'))
  names=['regional_plan.json','regional_states.json','quality_walk_cases.json','native_transit_r20.json','native_transit_r22.json','native_transit_r23.json','regional_wayfinding.json','military_readiness_r23.json','.projectseele_command_sliding_doors_r01.json','spatial_contract_r23.json','wayfinding_r23.json']
  paths.update(MAIN/name for name in names);paths.add(MAIN/'dimensions/projectseele/geofront/data/capabilities.dat')
  for name in ('projectseele_military_r07.dat','projectseele_un01_annex_r20.dat','projectseele_un_locations_r22.dat'):
   for world in (MAIN,REVIEW):
    try:paths.add(MAIN/datafile(world,name).relative_to(world))
    except FileNotFoundError:pass
  saved=[];absent=[]
  for path in sorted(paths):
   relative=path.resolve().relative_to(MAIN.resolve())
   if path.exists():
    dest=backup/'before'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest);saved.append(str(relative))
   else:absent.append(str(relative))
  (backup/'journal.json').write_text(json.dumps(dict(saved=saved,previously_absent=absent),indent=2))
  try:
   main(True);(backup/'COMPLETED.json').write_text((OUT/'installed.json').read_text())
  except BaseException:
   for name in saved:atomic_replace(MAIN/name,(backup/'before'/name).read_bytes())
   for name in absent:
    path=(MAIN/name).resolve();assert path.is_relative_to(MAIN.resolve())
    if path.is_file():path.unlink()
   (backup/'ROLLED_BACK.json').write_text(json.dumps(dict(restored=len(saved),new_files_removed=len(absent)),indent=2));raise
 finally:
  EXTERNAL_LOCKS=None
  for lock in locks.values():lock.close()
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args();transactional_apply() if args.apply else main(False)
