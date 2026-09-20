"""Stage a native S1 airport stop without writing the authoritative railway."""
from pathlib import Path
import json,shutil,subprocess,msvcrt
from stage_native_transit_repair import hashes
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_FIELD_R28_REVIEW';OUT=ROOT/'artifacts/facility_r28/airport';STAGE=ROOT/'.Codex/r28-native-airport'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if not STAGE.exists():
        with (WORLD/'session.lock').open('r+b') as lock:
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);before=hashes(WORLD/'mtr');shutil.copytree(WORLD/'mtr',STAGE)
            (OUT/'source_hashes.json').write_text(json.dumps(before,indent=2))
    java=Path.home()/'jdks/jdk-17.0.19+10/bin';classes=ROOT/'.Codex/r28-java';classes.mkdir(exist_ok=True)
    libs=Path.home()/'.gradle/caches/modules-2/files-2.1/org.apache.logging.log4j'
    cp=';'.join(map(str,[ROOT/'.Codex/local-mods/MTR-forge-4.0.5+1.20.1.jar']+sorted(libs.glob('*/2.19.0/*/*.jar'))))
    subprocess.run([str(java/'javac.exe'),'-encoding','UTF-8','-cp',cp,'-d',str(classes),*[str(ROOT/'tools/java'/n) for n in ('AirportStopR28.java','TransitSnapshotR20.java','TransitCadenceR20.java')]],check=True)
    cmd=[str(java/'java.exe'),'-Xmx1G','-Dfile.encoding=UTF-8','-cp',cp+';'+str(classes)]
    if not (OUT/'native_before.json').exists():subprocess.run(cmd+['TransitSnapshotR20',str(STAGE),str(OUT/'native_before.json')],check=True)
    if not (OUT/'airport_native_receipt.json').exists():subprocess.run(cmd+['AirportStopR28',str(STAGE),str(OUT)],check=True)
    if not (OUT/'cadence_S1.json').exists():subprocess.run(cmd+['TransitCadenceR20',str(STAGE),str(OUT/'cadence_S1.json'),'S1'],check=True)
    subprocess.run(cmd+['TransitSnapshotR20',str(STAGE),str(OUT/'native_final.json')],check=True)
    receipt=json.loads((OUT/'airport_native_receipt.json').read_text());final=json.loads((OUT/'native_final.json').read_text())
    receipt['siding']=next(s['id'] for s in final['sidings'] if s['name']=='S1车辆段')
    receipt['cadence_platforms']=[p['platformId'] for r in final['routes'] if r['routeNumber']=='S1' for p in r['routePlatformData']]
    (OUT/'airport_native_receipt.json').write_text(json.dumps(receipt,indent=2))
    (OUT/'runtime.json').write_text(json.dumps(dict(java=str(java),classes=str(classes),classpath=cp,stage=str(STAGE))))

if __name__=='__main__':main()
