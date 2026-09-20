"""Install only verified R26 cells, new lift groups and the one retired unused rail."""
from pathlib import Path
from collections import defaultdict
import argparse,copy,datetime,hashlib,json,msvcrt,shutil
import nbtlib,numpy as np
import regional_voxels as v
import promote_world_r24 as prior
from query_blocks import iter_selected_sections
from apply_s20_approved_semantic_repairs import atomic_replace

ROOT=v.ROOT;ART=ROOT/'artifacts/facility_r26';OUT=ART/'promotion'
MAIN=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906';REVIEW=ROOT/'run/saves/SEELE_R26_REVIEW'
EDIT_ROOTS=('core_lift','details','floor_ports','signage','crossing_finish','sign_sightlines','walkway_deck')
NEW_GROUPS={'63;302'}
RETIRED_GROUPS={'70;253'}
CAP=Path('dimensions/projectseele/geofront/data/capabilities.dat')
NATIVE_BOXES=[(62,-463,298,70,-358,310)]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def masks():
 prior.ART=ART;prior.REVIEW=REVIEW;prior.EDIT_ROOTS=EDIT_ROOTS
 mask,receipts=prior.masks();parts=defaultdict(list)
 for q,ids in mask.items():parts[q].append(ids)
 # These are the explicitly installed native mechanisms, including their
 # generated controllers, captured cabin, call panels and interlocked doors.
 for x,y,z,X,Y,Z in NATIVE_BOXES:
  for cx in range(x//16,X//16+1):
   for cz in range(z//16,Z//16+1):
    ids=[yy*256+(zz&15)*16+(xx&15) for yy in range(y,Y+1) for zz in range(max(z,cz*16),min(Z,cz*16+15)+1) for xx in range(max(x,cx*16),min(X,cx*16+15)+1)]
    parts[cx,cz].append(np.asarray(ids,dtype=np.int32))
 return {q:np.unique(np.concatenate(a)) for q,a in parts.items()},receipts
def protected():
 paths=[MAIN/'level.dat']
 for directory in ('playerdata','data','dimensions/projectseele/geofront/entities','dimensions/projectseele/geofront/data','mtr'):
  paths.extend(p for p in (MAIN/directory).rglob('*') if p.is_file())
 excluded={str(CAP).replace('\\','/')}
 return {p.relative_to(MAIN).as_posix():digest(p) for p in paths if p.exists() and p.relative_to(MAIN).as_posix() not in excluded}
def main(apply=False):
 OUT.mkdir(parents=True,exist_ok=True)
 if apply:
  assert not (OUT/'installed.json').exists(),'R26 already installed'
  assert json.loads((ART/'final_acceptance.json').read_text())['passed']
 baseline=json.loads((ART/'baseline.json').read_text(encoding='utf8'));cold=Path(baseline['backup'])/'world'
 for name,sha in baseline['original_user_files'].items():assert digest(ROOT/name)==sha,('Protected original file changed',name)
 mask,receipts=masks();selected={q:set(map(int,ids//4096)) for q,ids in mask.items()};locks=[]
 try:
  for world in (MAIN,REVIEW):
   lock=(world/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);locks.append(lock)
  def measure(world):return {(x,z,y):(p,a) for x,z,y,p,a in iter_selected_sections(world,v.DIM,selected,skip_unfinished=True)}
  base,current,after=measure(cold),measure(MAIN),measure(REVIEW);bt,mt,nt=prior.tagged(cold,mask),prior.tagged(MAIN,mask),prior.tagged(REVIEW,mask)
  v.WORLD=MAIN;v.OUT=OUT;p=v.Painter();conflicts=[];cells=nbt_only=0
  for (cx,cz),ids in mask.items():
   for sy in selected[cx,cz]:
    key=cx,cz,sy;assert all(key in data for data in (base,current,after)),key
    bp,ba=base[key];mp,ma=current[key];ap,aa=after[key]
    for raw in ids[ids//4096==sy]%4096:
     i=int(raw);q=(cx*16+(i&15),sy*16+(i>>8),cz*16+((i>>4)&15));old,new,original=mp[ma[i]],ap[aa[i]],bp[ba[i]]
     if old==new and prior.same(mt.get(q),nt.get(q)):continue
     if old!=original or not prior.same(mt.get(q),bt.get(q)):
      conflicts.append(dict(position=q,current=old,baseline=original,proposed=new));continue
     if old!=new:
      p.match((*q,*q),old,new,'r26/verified_map_and_native_mechanisms');cells+=1
      if nt.get(q) is not None:p.block_entities[q]=copy.deepcopy(nt[q])
     elif not prior.same(mt.get(q),nt.get(q)):
      assert nt.get(q) is not None,q
      p.update_block_entity(q,old,mt.get(q),nt[q],'r26/verified_sign_or_control');nbt_only+=1
  (OUT/'conflicts.json').write_text(json.dumps(conflicts,ensure_ascii=False,indent=2),encoding='utf8');assert not conflicts,conflicts[:10]
  maincap=nbtlib.load(MAIN/CAP);reviewcap=nbtlib.load(REVIEW/CAP);capkey='movingelevators:elevator_groups';groups=maincap['data'][capkey];newgroups=reviewcap['data'][capkey]
  assert NEW_GROUPS.isdisjoint(groups),'An existing main lift owns a requested new shaft'
  assert NEW_GROUPS<=set(newgroups),set(newgroups)
  original_groups=copy.deepcopy(groups)
  assert RETIRED_GROUPS<=set(groups) and RETIRED_GROUPS.isdisjoint(newgroups)
  for key in RETIRED_GROUPS:del groups[key]
  for key in NEW_GROUPS:
   assert not int(newgroups[key]['group']['isMoving']),('New cabin is moving',key)
   groups[key]=copy.deepcopy(newgroups[key])
  p.meta.update(cells=cells,nbt_only=nbt_only,receipts=receipts,new_lift_groups=sorted(NEW_GROUPS),retired_lift_groups=sorted(RETIRED_GROUPS))
  p.save_plan('verified_r26_delta');print('R26 preflight',cells,'cells',nbt_only,'NBT-only',len(mask),'chunks',flush=True)
  if not apply:return
  payloads={name:(REVIEW/name).read_bytes() for name in ('nerv_routes_r24.json.gz','regional_states.json','facility_lifts_r26.json','facility_chairs_r26.json','native_transit_r26.json','.projectseele_command_sliding_doors_r01.json')}
  payloads['quality_walk_cases.json']=(ART/'navigation/full_walk_cases.json').read_bytes()
  keep=protected();stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=OUT/('main_before_'+stamp)
  targets={MAIN/'dimensions/projectseele/geofront/region'/f'r.{cx//32}.{cz//32}.mca' for cx,cz in mask}
  targets.update(MAIN/name for name in payloads);targets.update({MAIN/CAP,MAIN/'r26_ready.json'});saved={};absent=[]
  for target in targets:
   rel=target.relative_to(MAIN).as_posix()
   if target.exists():
    dst=backup/'before'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,dst);saved[rel]=str(dst)
   else:absent.append(rel)
  backup.mkdir(parents=True,exist_ok=True);journal=dict(saved=saved,absent=absent,protected=keep)
  (backup/'journal.json').write_text(json.dumps(journal,indent=2),encoding='utf8')
  try:
   result=p.apply('verified_r26_delta',session_lock=locks[0]);assert result['counts']['cells']==cells
   for name,data in payloads.items():atomic_replace(MAIN/name,data)
   capfile=OUT/'new_capabilities.dat';maincap.save(capfile);atomic_replace(MAIN/CAP,capfile.read_bytes())
   check=nbtlib.load(MAIN/CAP)['data'][capkey]
   assert set(check)==(set(original_groups)-RETIRED_GROUPS)|NEW_GROUPS
   assert all(check[k]==value for k,value in original_groups.items() if k not in RETIRED_GROUPS),'Existing native lift state changed'
   assert protected()==keep,'Player, actor, campaign or unrelated transport data changed'
   receipt=dict(installed=True,world=str(MAIN),cells=cells,nbt_only=nbt_only,chunks=len(mask),new_groups=sorted(NEW_GROUPS),retired_groups=sorted(RETIRED_GROUPS),backup=str(backup),protected_data_unchanged=True)
   atomic_replace(MAIN/'r26_ready.json',json.dumps(dict(ready=True,**receipt),indent=2).encode())
   (OUT/'installed.json').write_text(json.dumps(receipt,indent=2),encoding='utf8');print('R26 installed',receipt,flush=True)
  except BaseException:
   for rel,source in saved.items():atomic_replace(MAIN/rel,Path(source).read_bytes())
   for rel in absent:
    q=(MAIN/rel).resolve();assert q.is_relative_to(MAIN.resolve())
    if q.is_file():q.unlink()
   (backup/'ROLLED_BACK.json').write_text(json.dumps(journal,indent=2));raise
 finally:
  for lock in locks:lock.close()
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
