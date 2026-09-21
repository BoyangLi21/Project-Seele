"""Install verified R29 voxel/NBT deltas without transplanting the test world.

Only named R29 edit receipts contribute coordinates. Player, entity, transport,
elevator and campaign state are not copied from automated reviews.
"""
from pathlib import Path
from collections import defaultdict
import argparse,copy,datetime,hashlib,json,msvcrt,shutil
import numpy as np
import regional_voxels as v
from query_blocks import iter_selected_sections,iter_block_entities
from apply_s20_approved_semantic_repairs import atomic_replace

ROOT=v.ROOT;ART=ROOT/'artifacts/facility_r29';OUT=ART/'promotion'
MAIN=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906';REVIEW=ROOT/'run/saves/SEELE_FIELD_R29_REVIEW'
EDIT_ROOTS=('upper_gallery','surface_cut','un_berths','signage')

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def masks():
    raw=defaultdict(list);receipts=[]
    for name in EDIT_ROOTS:
        for folder in sorted((ART/name).glob('*/applied_*')):
            if (folder/'ROLLED_BACK.json').exists():continue
            receipt=json.loads((folder/'receipt.json').read_text(encoding='utf8'))
            assert receipt.get('verified',False),('Unverified edit receipt',folder,receipt)
            assert Path(receipt['world']).resolve()==REVIEW.resolve(),('Receipt belongs to another world',folder)
            receipts.append(str(folder.relative_to(ROOT)))
            for path in (folder/'delta').glob('c.*.npz'):
                cx,cz=map(int,path.stem.split('.')[1:])
                with np.load(path) as a:raw[cx,cz].append(a['offsets'].astype(np.int32)+int(a['minimum'])*256)
            tags=folder/'block_entity_deltas.json'
            for row in json.loads(tags.read_text(encoding='utf8')) if tags.exists() else []:
                x,y,z=row['position'];raw[x//16,z//16].append(np.array([y*256+(z&15)*16+(x&15)],dtype=np.int32))
    return {q:np.unique(np.concatenate(parts)) for q,parts in raw.items()},receipts

def tagged(world,mask):
    result={}
    for (cx,cz),ids in mask.items():
        lo=(cx*16,int(ids.min()//4096)*16,cz*16);hi=(cx*16+15,int(ids.max()//4096)*16+15,cz*16+15)
        for q,tag in iter_block_entities(world,v.DIM,lo,hi):
            code=q[1]*256+(q[2]&15)*16+(q[0]&15);i=np.searchsorted(ids,code)
            if i<len(ids) and ids[i]==code:result[q]=copy.deepcopy(tag)
    return result

def same(a,b):return a is None and b is None or a is not None and b is not None and a==b
def protected_hashes():
    paths=[MAIN/'level.dat']
    for root in ('playerdata','data','dimensions/projectseele/geofront/entities','dimensions/projectseele/geofront/data','mtr'):
        paths.extend(p for p in (MAIN/root).rglob('*') if p.is_file())
    return {p.relative_to(MAIN).as_posix():digest(p) for p in paths if p.exists()}


def main(apply=False):
    OUT.mkdir(parents=True,exist_ok=True)
    if apply:
        assert not (OUT/'installed.json').exists(),'R29 already installed; write a follow-up patch'
        assert json.loads((ART/'final_acceptance.json').read_text(encoding='utf8'))['passed']
    baseline=json.loads((ART/'baseline.json').read_text(encoding='utf8'));cold=Path(baseline['backup'])/'world'
    for name,sha in baseline['original_user_files'].items():assert digest(ROOT/name)==sha,('Protected user file changed',name)
    mask,receipts=masks();selected={q:set(map(int,ids//4096)) for q,ids in mask.items()}
    locks=[]
    try:
        for world in (MAIN,REVIEW):
            lock=(world/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);locks.append(lock)
        def measure(w):return {(x,z,y):(p,a) for x,z,y,p,a in iter_selected_sections(w,v.DIM,selected,skip_unfinished=True)}
        before,current,after=measure(cold),measure(MAIN),measure(REVIEW)
        base_tags,main_tags,new_tags=tagged(cold,mask),tagged(MAIN,mask),tagged(REVIEW,mask)
        v.WORLD=MAIN;v.OUT=OUT;p=v.Painter();conflicts=[];cells=0;nbt_only=0
        for (cx,cz),ids in sorted(mask.items()):
            for sy in sorted(selected[cx,cz]):
                key=cx,cz,sy
                assert all(key in m for m in (before,current,after)),('Expected existing full section',key)
                bp,ba=before[key];mp,ma=current[key];ap,aa=after[key]
                for n in ids[ids//4096==sy]%4096:
                    n=int(n);q=(cx*16+(n&15),sy*16+(n>>8),cz*16+((n>>4)&15));old,new,base=mp[ma[n]],ap[aa[n]],bp[ba[n]]
                    bt,mt,nt=base_tags.get(q),main_tags.get(q),new_tags.get(q)
                    if old==new and same(mt,nt):continue
                    if old!=base or not same(bt,mt):
                        conflicts.append(dict(pos=q,baseline=base,current=old,proposed=new,nbt_changed=not same(bt,mt)));continue
                    if old!=new:
                        p.match((*q,*q),old,new,'r29/verified_geometry');cells+=1
                        if nt is not None:p.block_entities[q]=copy.deepcopy(nt)
                    elif not same(mt,nt):
                        assert mt is not None and nt is not None,('Unexpected NBT insertion/deletion with identical block',q)
                        p.update_block_entity(q,old,mt,nt,'r29/verified_wayfinding_text');nbt_only+=1
        (OUT/'conflicts.json').write_text(json.dumps(conflicts,ensure_ascii=False,indent=2),encoding='utf8')
        assert not conflicts,conflicts[:12]
        p.meta.update(expected_cells=cells,expected_nbt_only=nbt_only,source_receipts=receipts,main_player_entity_unrelated_transport_state_preserved=True)
        p.save_plan('verified_r29_cells_and_signs')
        print('R29 preflight',cells,'voxel cells',nbt_only,'NBT-only cells',len(mask),'chunks',flush=True)
        if not apply:return
        protected=protected_hashes();stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=OUT/('main_before_'+stamp);saved={};absent=[]
        metadata={name:REVIEW/name for name in ('nerv_routes_r24.json.gz','eva_facility_r29.json','first_battle_site_r10.json')}
        # The main route catalogue keeps all existing routes and adds the
        # actually verified R29 approach paths, deduplicated by stable ID.
        routes=json.loads((MAIN/'quality_walk_cases.json').read_text(encoding='utf8'))
        union={r['id']:r for r in routes}
        union.update({r['id']:r for r in json.loads((ART/'navigation/full_walk_cases.json').read_text(encoding='utf8'))})
        payloads={'quality_walk_cases.json':json.dumps(list(union.values()),ensure_ascii=False,indent=2).encode('utf8'),
                  'regional_states.json':(REVIEW/'regional_states.json').read_bytes()}
        for name,source in metadata.items():assert source.is_file(),source;payloads[name]=source.read_bytes()
        targets={MAIN/'dimensions/projectseele/geofront/region'/f'r.{cx//32}.{cz//32}.mca' for cx,cz in mask}
        targets.update(MAIN/name for name in payloads);targets.add(MAIN/'r29_ready.json')
        for target in sorted(targets):
            rel=target.relative_to(MAIN)
            if target.exists():
                destination=backup/'before'/rel;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,destination);saved[str(rel)]=str(destination)
            else:absent.append(str(rel))
        backup.mkdir(parents=True,exist_ok=True)
        journal=dict(saved=saved,previously_absent=absent,protected=protected)
        (backup/'journal.json').write_text(json.dumps(journal,indent=2),encoding='utf8')
        try:
            result=p.apply('verified_r29_cells_and_signs',session_lock=locks[0]);assert result['counts']['cells']==cells
            for name,data in payloads.items():atomic_replace(MAIN/name,data)
            assert protected_hashes()==protected,'Player, entity, transport or mechanical state changed'
            receipt=dict(installed=True,world=str(MAIN),source=str(REVIEW),changed_cells=cells,nbt_only_cells=nbt_only,chunks=len(mask),route_catalog=len(union),backup=str(backup),protected_hashes_unchanged=True,private_pack_unchanged=True,all_mtr_files_unchanged=True)
            atomic_replace(MAIN/'r29_ready.json',json.dumps(dict(ready=True,**receipt),indent=2).encode('utf8'))
            (OUT/'installed.json').write_text(json.dumps(receipt,indent=2),encoding='utf8');print('R29 installed',receipt,flush=True)
        except BaseException:
            for rel,source in saved.items():atomic_replace(MAIN/rel,Path(source).read_bytes())
            for rel in absent:
                target=(MAIN/rel).resolve();assert target.is_relative_to(MAIN.resolve())
                if target.is_file():target.unlink()
            (backup/'ROLLED_BACK.json').write_text(json.dumps(journal,indent=2),encoding='utf8');raise
    finally:
        for lock in locks:lock.close()

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
