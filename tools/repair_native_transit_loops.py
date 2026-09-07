"""Cold-copy, native validation, and a six-file install for the C1/F1 return paths."""
import argparse,hashlib,json,msvcrt,shutil,subprocess
from datetime import datetime
from pathlib import Path
from regional_voxels import WORLD,ROOT
from quality_structures import OUT,OLD,load
from stage_native_transit_repair import hashes

MANIFEST=OUT/'native_loop_stage.json'

def stage():
    source=WORLD/'mtr';target=ROOT/'.Codex/world-quality'/('mtr-loop-repair-'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        before=hashes(source);shutil.copytree(source,target)
        if before!=hashes(source) or before!=hashes(target):raise RuntimeError('Cold transit copy changed')
    allowed=[]
    for line in load(OLD/'transit2/native_transit_receipt.json')['lines']:
        if line['line'] not in ('C1','F1'):continue
        for kind,key in [('routes','route_id'),('depots','depot_id'),('sidings','siding_id')]:
            ident=f'{line[key] & ((1<<64)-1):016X}';allowed.append(f'projectseele/geofront/{kind}/{ident[-2:]}/{ident}')
    if len(allowed)!=6 or not all(k in before for k in allowed):raise RuntimeError('Expected six retained native files')
    proof=OUT/'native_loop_receipt.json'
    manifest=dict(source=str(source),stage=str(target),source_hashes=before,allowed=allowed,proof=str(proof))
    MANIFEST.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    java=Path('C:/Users/liboy/jdks/jdk-17.0.19+10/bin')
    cache=Path('C:/Users/liboy/.gradle/caches/modules-2/files-2.1/org.apache.logging.log4j')
    cp=';'.join(map(str,[ROOT/'.Codex/local-mods/MTR-forge-4.0.5+1.20.1.jar']+sorted(cache.glob('*/2.19.0/*/*.jar'))))
    classes=ROOT/'.Codex/world-quality/java';classes.mkdir(exist_ok=True)
    subprocess.run([str(java/'javac.exe'),'-encoding','UTF-8','-cp',cp,'-d',str(classes),str(ROOT/'tools/java/RegionalTransitLoopRepair.java')],check=True)
    subprocess.run([str(java/'java.exe'),'-cp',cp+';'+str(classes),'RegionalTransitLoopRepair',str(target),str(proof)],check=True)
    if not load(proof)['passed']:raise RuntimeError('Native closed path validation failed')
    manifest['validated_hashes']={k:hashes(target)[k] for k in allowed}
    MANIFEST.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Validated current-world loop repair',target,flush=True)

def install():
    manifest=load(MANIFEST);source=Path(manifest['source']);target=Path(manifest['stage'])
    if source.resolve()!=(WORLD/'mtr').resolve() or not target.resolve().is_relative_to((ROOT/'.Codex/world-quality').resolve()):raise RuntimeError('Unexpected transit path')
    if not load(Path(manifest['proof']))['passed']:raise RuntimeError('No successful native validation')
    backup=OUT/('native_loop_install_'+datetime.now().strftime('%Y%m%d_%H%M%S'))/'before';changed=[]
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        if hashes(source)!=manifest['source_hashes']:raise RuntimeError('World changed after cold staging')
        for key in manifest['allowed']:
            if hashlib.sha256((target/key).read_bytes()).hexdigest()!=manifest['validated_hashes'][key]:raise RuntimeError('Validated staging changed')
        for key in manifest['allowed']:
            destination=source/key;data=(target/key).read_bytes()
            if data==destination.read_bytes():continue
            before=backup/key;before.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(destination,before)
            temp=destination.with_name(destination.name+'.quality-tmp');temp.write_bytes(data);temp.replace(destination)
            if destination.read_bytes()!=data:raise RuntimeError('Native file readback mismatch')
            changed.append(key)
        after=hashes(source)
        unexpected=[k for k in set(after)|set(manifest['source_hashes']) if after.get(k)!=manifest['source_hashes'].get(k) and k not in manifest['allowed']]
        if unexpected:raise RuntimeError(f'Unrelated native files changed: {unexpected}')
    receipt=dict(verified=True,changed=changed,backup=str(backup),native_rails=112,native_routes=8)
    (OUT/'native_loop_install_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('Installed native return paths; files',len(changed),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('operation',choices=['stage','install']);args=ap.parse_args()
    stage() if args.operation=='stage' else install()
