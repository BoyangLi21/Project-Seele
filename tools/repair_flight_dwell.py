"""Install only the F1 siding's verified dwell policy change."""
import json,msvcrt,shutil,subprocess
from datetime import datetime
from quality_structures import ROOT,OUT,load
from regional_voxels import WORLD
from stage_native_transit_repair import hashes
from repair_airfield_profiles import java_paths
from apply_s20_approved_semantic_repairs import atomic_replace

def repair():
    label=datetime.now().strftime('%Y%m%d_%H%M%S');source=WORLD/'mtr';stage=ROOT/'.Codex/world-quality'/('mtr-flight-dwell-'+label)
    proof=OUT/'flight_dwell_receipt.json';java,classes,cp=java_paths()
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        before=hashes(source);shutil.copytree(source,stage)
        if before!=hashes(stage):raise RuntimeError('Native copy mismatch')
        subprocess.run([str(java/'javac.exe'),'-encoding','UTF-8','-cp',cp,'-d',str(classes),str(ROOT/'tools/java/RegionalFlightDwellSettings.java')],check=True)
        subprocess.run([str(java/'java.exe'),'-cp',cp+';'+str(classes),'RegionalFlightDwellSettings',str(stage),str(proof)],check=True)
        result=load(proof);ident=result['id'].upper();key=f'projectseele/geofront/sidings/{ident[-2:]}/{ident}'
        if not result['passed'] or hashes(source)!=before:raise RuntimeError('Native settings precondition failed')
        backup=OUT/('flight_dwell_install_'+label)/'before'/key;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/key,backup)
        payload=(stage/key).read_bytes();atomic_replace(source/key,payload)
        if (source/key).read_bytes()!=payload:raise RuntimeError('Native dwell readback mismatch')
        after=hashes(source)
        if any(before.get(k)!=v for k,v in after.items() if k!=key):raise RuntimeError('Unrelated native files changed')
        (OUT/'flight_dwell_install_receipt.json').write_text(json.dumps(dict(verified=True,file=key,backup=str(backup)),indent=2),encoding='utf-8')
    print('F1 retains the full authored boarding interval; one native siding file updated')

if __name__=='__main__':repair()
