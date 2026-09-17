"""Retire superseded transport displays and update typed world metadata."""
import argparse,copy,datetime,json,msvcrt,shutil
from pathlib import Path
import nbtlib
import regional_voxels as v
from retire_floating_labels_r19 import identity,label_id
from transplant_s22_authority import read_region,parse_chunk,build_region,chunk_blob
from apply_s20_approved_semantic_repairs import atomic_replace
ROOT=v.ROOT;OUT=ROOT/'artifacts/world_rebuild_r20/metadata'

def main(world):
    world=Path(world);marker=world/'world_revision_r20.json'
    assert not marker.exists(),'Metadata already installed'
    native=json.loads((OUT.parent/'transit/built11/native_commission.json').read_text(encoding='utf8'))
    catalogue=json.loads((world/'regional_wayfinding.json').read_text(encoding='utf8'))
    retired=[];updated=[];kept=[]
    for row in catalogue:
        key=row['id']
        if key.startswith(('station/','C1_','R1_','S1_','S2_','A1_','U1_','U2_','P1_')) or key in ('bay/departures','hakone/departures'):
            retired.append(row);continue
        q=copy.deepcopy(row)
        if key in ('bay/terminal','hakone/terminal'):
            q['text']={'text':('箱根湾机场' if key.startswith('bay') else '新箱根机场')+'\n一号航站楼','color':'#e7e8dc'}
        elif key.startswith(('bay/checkin/','hakone/checkin/')):q['text']={'text':key.rsplit('/',1)[1].zfill(2)+'  值机柜台\nF1  联络航班','color':'#e7e8dc'}
        if q!=row:updated.append(q)
        kept.append(q)
    wanted={label_id(q['id']):q for q in retired};texts={label_id(q['id']):q for q in updated};found=set();pending=[]
    OUT.mkdir(parents=True,exist_ok=True);backup=OUT/(world.name+'_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
    with (world/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        for path in (world/'dimensions/projectseele/geofront/entities').glob('r.*.*.mca'):
            if path.stat().st_size<8192:continue
            stamps,blobs=read_region(path);dirty=False
            for i,blob in enumerate(blobs):
                if not blob:continue
                root=parse_chunk(blob);entities=[];changed=False
                for e in root.get('Entities',[]):
                    uid=identity(e['UUID']) if 'UUID' in e else ''
                    if uid in wanted or uid in texts:
                        assert str(e['id'])=='minecraft:text_display' and 'projectseele_r03_wayfinding' in map(str,e.get('Tags',[]));found.add(uid);changed=True
                        if uid in wanted:continue
                        e['text']=nbtlib.String(json.dumps(texts[uid]['text'],ensure_ascii=False))
                    entities.append(e)
                if changed:root['Entities']=nbtlib.List[nbtlib.Compound](entities);blobs[i]=chunk_blob(root);dirty=True
            if dirty:pending.append((path,build_region(stamps,blobs)))
        assert set(wanted)|set(texts)<=found,('Known displays not found',(set(wanted)|set(texts))-found)
        for path,data in pending:shutil.copy2(path,backup/path.name);atomic_replace(path,data)
        files={}
        files['regional_wayfinding.json']=kept
        plan=json.loads((world/'regional_plan.json').read_text(encoding='utf8'))
        old=json.loads((OUT.parent/'transit/native_snapshot.json').read_text(encoding='utf8'))
        stations=json.loads((OUT.parent/'transit/civil/continuous_platform_aisles/places.json').read_text(encoding='utf8'))['stations']
        for q in plan['stations']:
            x,_,z=q['pos'];near=min(stations,key=lambda s:(s['old_center'][0]-x)**2+(s['old_center'][2]-z)**2)
            if (near['old_center'][0]-x)**2+(near['old_center'][2]-z)**2<400:q['pos']=near['center'];q['name']=near['station']
        plan.update(revision=20,status='manual_acceptance',quality_stage='r20_native_verified',native_rail_count=len(native['curves']),native_route_count=len(native['routes']),transport_plan='native_transit_r20.json',train_headway_ms=60000,timezone='Asia/Shanghai',eva_cage_shift_r20=-144,eva_cages=[[-12,-443,-240],[30,-443,-240],[72,-443,-240]],eva_launch_beds=[[-12,-411,-36],[30,-411,-36],[72,-411,-36]],un01_model='deferred_to_ChatGPT_Pro',remaining_validation=['Human aesthetic and driving acceptance'])
        files['regional_plan.json']=plan
        files['native_transit_r20.json']={k:native[k] for k in ('stations','platforms','routes','depots','sidings','curves') if k in native}
        files['quality_walk_cases.json']=json.loads((OUT.parent/'quality_walk_cases_r20.json').read_text(encoding='utf8'))
        for name,data in files.items():
            path=world/name
            if path.exists():shutil.copy2(path,backup/name)
            atomic_replace(path,json.dumps(data,ensure_ascii=False,indent=2).encode('utf8'))
        receipt=dict(world=str(world),retired_labels=[q['id'] for q in retired],updated_labels=[q['id'] for q in updated],remaining_labels=len(kept),full_walk_catalogue=len(files['quality_walk_cases.json']),model_work_deferred=True,backup=str(backup))
        atomic_replace(marker,json.dumps(receipt,ensure_ascii=False,indent=2).encode('utf8'));(backup/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
    print('Metadata installed',world.name,'retired transport labels',len(retired),'Chinese terminal labels',len(updated))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--world',default=str(v.WORLD));main(p.parse_args().world)
