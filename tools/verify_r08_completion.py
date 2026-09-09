"""Cold final-state checks and evidence assembly for the R08 delivery boundary."""
import json,hashlib,uuid,msvcrt,shutil
from pathlib import Path
import numpy as np
import nbtlib
from regional_voxels import ROOT,WORLD
from scan_regional_completion import volume
from inspect_map_assets import region_chunks
OUT=ROOT/'artifacts/world_refinement_r08'
def load(p):return json.loads(p.read_text(encoding='utf8'))
def ident(values):return str(uuid.UUID(bytes=b''.join((int(v)&0xffffffff).to_bytes(4,'big') for v in values)))
def run():
    lock=(WORLD/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    result={'world':str(WORLD),'checks':{}}
    for path,expected in load(OUT/'user_baseline.json').items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
    result['checks']['user_resources_preserved']=True
    catalog=load(WORLD/'quality_walk_cases.json');assert len(catalog)==8528 and len({c['id'] for c in catalog})==8528
    assert not any(c['id'].startswith('r07/fleet/') for c in catalog)
    evidence={c['id']:c for c in load(OUT/'native_walk_combined.json')}
    for c in load(OUT/'native_workshop_pass.json'):evidence[c['id']]=c
    assert len(evidence)==190 and all(c['status']=='pass' for c in evidence.values())
    (OUT/'native_walk_combined.json').write_text(json.dumps(list(evidence.values()),ensure_ascii=False,indent=2),encoding='utf8')
    result['checks']['native_walks']=dict(passed=190,catalog=8528,latest_workshop_rechecks=18)
    assert load(OUT/'mobility_native_pass.json')['passed']
    result['checks']['mobility_native']=True
    military=nbtlib.load(WORLD/'dimensions/projectseele/geofront/data/projectseele_military_r07.dat')['data']
    assert str(military['Phase'])=='WET';managed={str(k):ident(v) for k,v in military['Entities'].items()};assert len(managed)==31
    fleet=nbtlib.load(WORLD/'data/projectseele_eva_fleet.dat')['data']['Fleet']
    expected={'4e449cf5-9726-4810-b07b-81aca77d0868','972271c6-dd86-472d-938e-4dc3a363f343','d0694537-3e22-4a39-a92a-cb14330ad150'}
    assert {ident(e['Canonical']) for e in fleet}==expected
    assert managed['prototype']=='aa222a1b-fb8b-4f62-8a60-0bfd20772115'
    details=nbtlib.load(WORLD/'dimensions/projectseele/geofront/data/projectseele_r08_details.dat')['data']['Members'];assert len(details)==84
    wanted=expected|set(managed.values())|{ident(v) for v in details.values()};found={}
    directory=WORLD/'dimensions/projectseele/geofront/entities'
    for region in directory.glob('r.*.*.mca'):
        _,rx,rz=region.stem.split('.');rx,rz=int(rx),int(rz)
        for _,_,chunk in region_chunks(region,(rx*32,rx*32+31,rz*32,rz*32+31)):
            for e in chunk.get('Entities',[]):
                if 'UUID' not in e:continue
                u=ident(e['UUID'])
                if u in wanted:
                    assert u not in found,('duplicate',u);found[u]=dict(type=str(e['id']),position=list(map(float,e['Pos'])))
    assert wanted<=set(found),wanted-set(found)
    proto=found[managed['prototype']];assert np.linalg.norm(np.array(proto['position'])-[6442.5,77,-6205.5])<1
    result['checks']['identities']=dict(canonical=list(sorted(expected)),managed=len(managed),native_members=len(details),prototype=proto)
    a,p=volume((6426,77,-6226),(6458,120,-6137));assert np.all(np.array([s=='projectseele:lcl[level=0]' for s in p])[a])
    a,p=volume((6426,77,-6136),(6458,141,-6136));assert np.all(np.array([s=='minecraft:barrier' for s in p])[a])
    result['checks']['secret_hangar']='WET / physical door closed'
    # Match the exact protected inner volumes against the cold R08 survey.
    protected=0
    for name,boxes in [('shafts',[((cx-17,-348,-53),(cx+17,24,-19)) for cx in (-12,30,72)]),('hangar',[((-32,-512,-137),(93,-354,-55))])]:
        d=np.load(OUT/'facilities'/(name+'_before.npz'));old=d['blocks'];pal=d['palette'];origin=d['lo']
        for lo,hi in boxes:
            before=old[lo[1]-origin[1]:hi[1]-origin[1]+1,lo[2]-origin[2]:hi[2]-origin[2]+1,lo[0]-origin[0]:hi[0]-origin[0]+1]
            a,p=volume(lo,hi);lookup={s:i for i,s in enumerate(p)};mapping=np.array([lookup.get(s,-1) for s in pal]);assert np.array_equal(mapping[before],a),('interior changed',lo,hi)
            protected+=int(a.size)
    result['checks']['interior_cells_preserved']=protected;assert protected==3033597
    for x in (7,49):
        a,p=volume((x,-349,207),(x+4,24,237));assert np.all(np.array([s in ('minecraft:air','minecraft:cave_air','minecraft:void_air') for s in p])[a])
    result['checks']['old_shaft_walls_stay_retired']=True
    photos=OUT/'photos';photos.mkdir(exist_ok=True)
    for source in (ROOT/'run/screenshots').glob('r08_*.png'):
        if source.name in ('r08_prototype_cull_check.png',):continue
        shutil.copy2(source,photos/source.name)
    for name in ('pyramid','hangar','terminal_dogma'):assert (OUT/(name+'_multiangle.png')).stat().st_size>20000
    result['checks']['artifacts']=dict(multiangle_sheets=3,native_photos=len(list(photos.glob('*.png'))))
    result['passed']=True
    (OUT/'completion.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':run()
