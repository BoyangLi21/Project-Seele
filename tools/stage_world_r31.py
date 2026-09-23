"""Create R31 from the frozen user baseline, applying only the approved UN receipt."""
from pathlib import Path
from collections import defaultdict
import argparse
import copy
import datetime
import hashlib
import io
import json
import shutil
import nbtlib
import numpy as np
import regional_voxels as vox
from query_blocks import iter_selected_sections, dimension_dir

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/facility_r31'
OUT=ART/'world_stage'
WORLD=ROOT/'run/saves/SEELE_R31_WORLD'
RECEIPT=ART/'un_hangars/widening/applied_20260923_094331_755698'
DIM='projectseele:geofront'

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()
def files(world):
    return {p.relative_to(world).as_posix():sha(p) for p in world.rglob('*')
            if p.is_file() and not p.name.endswith('.lock')}
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def level_payload_without_name(level):
    """Typed, recursive NBT serialization excluding precisely Data.LevelName."""
    stripped=copy.deepcopy(level)
    stripped['Data'].pop('LevelName',None)
    buffer=io.BytesIO();stripped.write(buffer)
    return buffer.getvalue()

def rename_new_world():
    path=WORLD/'level.dat'
    original=path.read_bytes();before=nbtlib.load(path)
    unchanged=level_payload_without_name(before)
    old_name=before['Data'].get('LevelName')
    after=copy.deepcopy(before);after['Data']['LevelName']=nbtlib.String('Project SEELE R31')
    temporary=path.with_name('level.dat.r31-name.tmp')
    assert not temporary.exists(),'Unexpected leftover level.dat rename candidate'
    after.save(temporary)
    readback=nbtlib.load(temporary)
    assert str(readback['Data']['LevelName'])=='Project SEELE R31'
    assert level_payload_without_name(readback)==unchanged,'Another level.dat tag changed during rename'
    inverse=OUT/'level_name.before.dat';inverse.write_bytes(original)
    temporary.replace(path)
    receipt={'file':'level.dat','allowed_property':'Data.LevelName',
             'before':None if old_name is None else str(old_name),'after':'Project SEELE R31',
             'before_sha256':hashlib.sha256(original).hexdigest(),'after_sha256':sha(path),
             'all_other_typed_nbt_equal':True,'unchanged_typed_nbt_sha256':hashlib.sha256(unchanged).hexdigest(),
             'comparison':'Exact recursive typed NBT serialization after removing only Data.LevelName',
             'inverse_file':str(inverse.relative_to(ROOT))}
    write(OUT/'level_name_change.json',receipt)
    return receipt

def delta():
    receipt=read(RECEIPT/'receipt.json')
    baseline=read(ART/'baseline.json')
    assert receipt['verified'] and Path(receipt['world']).resolve()==Path(baseline['review_world']).resolve()
    assert receipt['dimension']==DIM and receipt['counts']['block_entities']==0
    assert not read(RECEIPT/'block_entity_deltas.json')
    changes={};regions=set()
    for path in sorted((RECEIPT/'delta').glob('c.*.npz')):
        cx,cz=map(int,path.stem.split('.')[1:]);regions.add(f'dimensions/projectseele/geofront/region/r.{cx//32}.{cz//32}.mca')
        with np.load(path) as a:
            palette=a['palette'].tolist();minimum=int(a['minimum'])
            for n,before,after in zip(a['offsets'],a['before'],a['after']):
                n=int(n);pos=(cx*16+(n&15),minimum+n//256,cz*16+((n>>4)&15))
                assert pos not in changes
                changes[pos]=(palette[int(before)],palette[int(after)])
    assert len(changes)==receipt['counts']['cells']==259026
    return changes,regions

def preconditions(world,changes):
    selected=defaultdict(set);wanted=defaultdict(list);seen=set();errors=[]
    for pos in changes:
        x,y,z=pos;selected[x//16,z//16].add(y//16);wanted[x//16,z//16,y//16].append(pos)
    for cx,cz,sy,palette,indices in iter_selected_sections(world,DIM,selected):
        for pos in wanted[cx,cz,sy]:
            x,y,z=pos;actual=palette[indices[(y-sy*16)*256+(z&15)*16+(x&15)]];seen.add(pos)
            if actual!=changes[pos][0]:errors.append({'position':pos,'expected':changes[pos][0],'actual':actual})
    assert len(seen)==len(changes),'Unmeasured receipt coordinates'
    if errors:raise RuntimeError('Baseline receipt conflict: '+json.dumps(errors[:8]))

def painter(changes):
    p=vox.Painter();rows=sorted(changes.items(),key=lambda row:(row[0][1],row[0][2],row[0][0]));i=0
    while i<len(rows):
        (x,y,z),(before,after)=rows[i];j=i+1
        while j<len(rows) and rows[j][0]==(x+j-i,y,z) and rows[j][1]==(before,after):j+=1
        p.match((x,y,z,x+j-i-1,y,z),before,after,'r31/formal_un_hangar_receipt');i=j
    p.meta.update(source_receipt=str(RECEIPT.relative_to(ROOT)),approved_scope='Two UN hangars only',
                  source_of_runtime='Frozen R30 user baseline; never the review world')
    return p

def main(apply=False,manual=False,verification_report=None):
    baseline=read(ART/'baseline.json');backup=Path(baseline['backup']).resolve()
    assert backup.is_dir() and (backup/'level.dat').is_file()
    assert backup!=WORLD.resolve() and WORLD.resolve().parent==(ROOT/'run/saves').resolve()
    assert not WORLD.exists(),'R31 destination exists; do not overwrite a world with possible user progress.'
    for name,digest in baseline['original_user_files'].items():assert sha(ROOT/name)==digest,('Protected user file changed',name)
    verification=read(Path(verification_report)) if verification_report else {'passed':None,'status':'not_run','scope':'No consolidated R31 functional report supplied'}
    if not manual:assert verification.get('revision')=='R31' and verification.get('passed') is True,'Use a real consolidated R31 verification report, or explicit --manual-acceptance.'
    changes,regions=delta();preconditions(backup,changes)
    install=read(ART/'un_hangars/installed.json');catalog=ART/'un_hangars/quality_walk_cases.after.json'
    assert sha(backup/'quality_walk_cases.json')==install['catalog_before_sha256']
    assert sha(catalog)==install['catalog_after_sha256']
    marker={'schema':'projectseele.un-hangars-r31.v1','revision':31,'hangars':read(ART/'un_hangars/geometry.json')}
    plan={'revision':'R31','source_backup':str(backup),'destination':str(WORLD),'receipt':str(RECEIPT),
          'cells':len(changes),'changed_region_files':sorted(regions),'metadata':['un_hangars_r31.json','quality_walk_cases.json','level.dat'],
          'level_name_property':{'file':'level.dat','nbt_path':'Data.LevelName','value':'Project SEELE R31'},
          'acceptance_mode':'manual_by_user' if manual else 'native_verified','verification':verification,
          'review_runtime_copied':False,'review_overworld_copied':False,'apply_requested':apply}
    write(OUT/'plan.json',plan)
    if not apply:
        print('R31 read-only preflight ready; no world created');return
    before=files(backup);write(OUT/'baseline_file_hashes.json',before)
    shutil.copytree(backup,WORLD,ignore=shutil.ignore_patterns('session.lock','*.lock'))
    assert files(WORLD)==before,'Cold copy differs from user baseline'
    (WORLD/'session.lock').write_bytes(bytes((0xe2,0x98,0x83)))
    vox.WORLD=WORLD;vox.OUT=OUT;vox.DIM=DIM
    p=painter(changes);receipt=p.apply('formal_un_hangars')
    assert receipt['counts']['cells']==len(changes)
    write(WORLD/'un_hangars_r31.json',marker)
    shutil.copy2(catalog,WORLD/'quality_walk_cases.json')
    level_name=rename_new_world()
    assert level_name['before_sha256']==before['level.dat'],'Destination level.dat no longer matches cold user baseline'
    after=files(WORLD);allowed=regions|{'un_hangars_r31.json','quality_walk_cases.json','level.dat'}
    unexpected=[name for name in set(before)|set(after) if before.get(name)!=after.get(name) and name not in allowed]
    assert not unexpected,('Unexpected non-geometry world change',unexpected[:10])
    result={**plan,'created':datetime.datetime.now().astimezone().isoformat(),'geometry_staged':True,
            'source_level_sha256':before['level.dat'],'destination_level_sha256':after['level.dat'],
            'level_name_change':level_name,'preserved_original_files':len(before)-len(regions)-2,
            'all_original_progress_files_preserved':True,'changed_files':sorted(name for name in after if before.get(name)!=after[name]),
            'catalog_rows':len(read(catalog)),'world_not_yet_finalized':True,
            'next_step':'Install R31 models and motion files, then package_release_r31.py stage creates r31_ready.json.'}
    write(WORLD/'r31_world_stage.json',result);write(OUT/'installed.json',result)
    print('R31 world geometry staged from frozen user progress; models/packaging remain separate')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');ap.add_argument('--manual-acceptance',action='store_true');ap.add_argument('--verification-report',type=Path);args=ap.parse_args()
    main(args.apply,args.manual_acceptance,args.verification_report)
