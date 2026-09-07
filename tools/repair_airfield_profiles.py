"""Native airborne runway profiles that clear the surveyed hills without terrain excavation."""
import argparse,copy,json,msvcrt,shutil,subprocess
from datetime import datetime
from pathlib import Path
from quality_structures import ROOT,OUT,OLD,load
from regional_voxels import WORLD
from stage_native_transit_repair import hashes
from apply_s20_approved_semantic_repairs import atomic_replace

NATIVE=OUT/'airfield_profile_native';MANIFEST=OUT/'airfield_profile_stage.json'

def definition():
    old=load(OLD/'transit_plan.json');retired=[];added=[]
    for airport,sign in [('bay',-1),('hakone',1)]:
        take=next(r for r in old['rails'] if r['id']==f'F1_{airport}_takeoff');land=next(r for r in old['rails'] if r['id']==f'F1_{airport}_landing')
        retired.extend([take,land])
        a=copy.deepcopy(take);a['id']+='_run';a['kind']='rail';a['to']=[take['from'][0]+sign*280,80,take['from'][2]]
        b=copy.deepcopy(take);b['from']=a['to'];b['to'][1]=180
        c=copy.deepcopy(land);c['from'][1]=180;c['to']=[land['from'][0]-sign*360,80,land['from'][2]]
        d=copy.deepcopy(land);d['id']+='_rollout';d['kind']='rail';d['from']=c['to']
        added.extend([a,b,c,d])
    ids=next(l for l in load(OLD/'transit2/native_transit_receipt.json')['lines'] if l['line']=='F1')
    return dict(rails=added,retire_rails=retired,stations=[],lines=[],regenerate_depots=[dict(line='F1',depot_id=ids['depot_id'],siding_id=ids['siding_id'],cruise=280,restart_vehicles=True)])

def java_paths():
    java=Path('C:/Users/liboy/jdks/jdk-17.0.19+10/bin');classes=ROOT/'.Codex/world-quality/java'
    cache=Path('C:/Users/liboy/.gradle/caches/modules-2/files-2.1/org.apache.logging.log4j')
    cp=';'.join(map(str,[ROOT/'.Codex/local-mods/MTR-forge-4.0.5+1.20.1.jar']+sorted(cache.glob('log4j-api/2.19.0/*/*.jar'))+sorted(cache.glob('log4j-core/2.19.0/*/*.jar'))))
    return java,classes,cp

def stage():
    source=WORLD/'mtr';target=ROOT/'.Codex/world-quality'/('mtr-airfield-'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        before=hashes(source);shutil.copytree(source,target)
        if before!=hashes(source) or before!=hashes(target):raise RuntimeError('Cold transit copy changed')
    plan=OUT/'airfield_profile_plan.json';plan.write_text(json.dumps(definition(),ensure_ascii=False,indent=2),encoding='utf-8')
    NATIVE.mkdir(exist_ok=True);MANIFEST.write_text(json.dumps(dict(source=str(source),stage=str(target),source_hashes=before),indent=2),encoding='utf-8')
    java,classes,cp=java_paths()
    subprocess.run([str(java/'javac.exe'),'-encoding','UTF-8','-cp',cp,'-d',str(classes),str(ROOT/'tools/java/RegionalTransitAuthor.java'),str(ROOT/'tools/java/RegionalFlightPathSurvey.java')],check=True)
    subprocess.run([str(java/'java.exe'),'-cp',cp+';'+str(classes),'RegionalTransitAuthor',str(plan),str(target),str(NATIVE),'--append'],check=True)
    subprocess.run([str(java/'java.exe'),'-cp',cp+';'+str(classes),'RegionalFlightPathSurvey',str(target),str(NATIVE/'flight_samples.json')],check=True)
    receipt=load(NATIVE/'native_transit_receipt.json')
    if not receipt['passed'] or receipt['native_rails']!=116 or receipt['retained_routes']!=8:raise RuntimeError('Unexpected native airfield result')
    print('Airfield profiles staged;116 rails,8 routes',flush=True)

def install():
    m=load(MANIFEST);native=load(NATIVE/'native_transit_receipt.json')
    air=load(OUT/'flight_clearance.json');ground=load(OUT/'transit_clearance_profile.json')
    if not native['passed'] or air['passed']!=air['rails'] or ground['passed']!=116 or ground['rails']!=116 or not ground.get('airfield_profile'):raise RuntimeError('Profile validation incomplete')
    source=Path(m['source']).resolve();target=Path(m['stage']).resolve()
    if source!=(WORLD/'mtr').resolve() or not target.is_relative_to((ROOT/'.Codex/world-quality').resolve()):raise RuntimeError('Unexpected native profile path')
    before=m['source_hashes'];after=hashes(target);changed=[k for k,v in after.items() if before.get(k)!=v];removed=set(before)-set(after);added=set(after)-set(before)
    retired={r['id'].upper() for r in native['retired_rails']}
    if len(removed)!=4 or any('/rails/' not in k or Path(k).name.upper() not in retired for k in removed):raise RuntimeError('Unexpected native rail deletion')
    folder=OUT/('airfield_profile_install_'+datetime.now().strftime('%Y%m%d_%H%M%S'));folder.mkdir()
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        if hashes(source)!=before:raise RuntimeError('Current world changed since staging')
        shutil.copytree(source,folder/'before')
        try:
            for key in changed:
                dest=source/key;dest.parent.mkdir(parents=True,exist_ok=True);atomic_replace(dest,(target/key).read_bytes())
            for key in removed:(source/key).unlink()
            if hashes(source)!=after:raise RuntimeError('Native profile readback mismatch')
        except Exception:
            for key in set(changed)|removed:
                old=folder/'before'/key;dest=source/key
                if old.exists():atomic_replace(dest,old.read_bytes())
                elif key in added and dest.exists():dest.unlink()
            raise
        p=WORLD/'regional_plan.json';master=load(p);master.update(native_rail_count=116,native_route_count=8,airfield_profile_revision=2,flight_cruise_y=280)
        p.write_text(json.dumps(master,ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.copy2(NATIVE/'flight_samples.json',OUT/'native_flight_samples.json')
    receipt=dict(verified=True,changed=changed,removed=sorted(removed),native_rails=116,cruise=280,backup=str(folder/'before'))
    (OUT/'airfield_profile_install_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('Installed native runway ascent/descent profiles; ground pavement unchanged',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('operation',choices=['stage','install']);args=ap.parse_args()
    stage() if args.operation=='stage' else install()
