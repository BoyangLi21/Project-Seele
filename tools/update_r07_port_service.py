"""Regenerate only P1 dispatch settings with native MTR, retaining every other object."""
from pathlib import Path
import json,shutil,msvcrt,subprocess,os
from datetime import datetime
from install_r07_port_transit import hashes
from regional_voxels import ROOT,WORLD
from apply_s20_approved_semantic_repairs import atomic_replace
OUT=ROOT/'artifacts/world_expansion_r07'
def main():
    lock=(WORLD/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    source=WORLD/'mtr';before=hashes(source);stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    stage=ROOT/'.Codex'/('r07-port-service-'+stamp);shutil.copytree(source,stage)
    receipt=json.loads((OUT/'port_transit_install_receipt.json').read_text(encoding='utf8'))
    changed=[n for n in receipt['added'] if any('/'+kind+'/' in n for kind in ['depots','sidings','platforms'])]
    assert len(changed)==4
    signed=lambda h:(int(h,16)+(1<<63))%(1<<64)-(1<<63)
    plan=dict(rails=[],stations=[],lines=[],regenerate_depots=[dict(line='P1',depot_id=signed('5EBAE3260E6B166A'),siding_id=signed('FA8B17F2E0948E4D'),repeat=True,restart_vehicles=True,dwell=12000,dwell_platform_ids=[signed('B616EA7C0666EC36'),signed('150052CAB93FCF8D')])])
    definition=OUT/'port_service_plan.json';definition.write_text(json.dumps(plan,indent=2),encoding='utf8')
    jars=[ROOT/'.Codex/local-mods/MTR-forge-4.0.5+1.20.1.jar']
    logs=Path('C:/Users/liboy/.gradle/caches/modules-2/files-2.1/org.apache.logging.log4j')
    for name in ('log4j-api','log4j-core'):jars.append(next((logs/name/'2.19.0').rglob('*.jar')))
    cp=os.pathsep.join(str(p) for p in jars);classes=ROOT/'.Codex/r07-java';classes.mkdir(exist_ok=True)
    jdk=Path('C:/Users/liboy/jdks/jdk-17.0.19+10/bin')
    subprocess.run([str(jdk/'javac.exe'),'-encoding','UTF-8','-cp',cp,'-d',str(classes),str(ROOT/'tools/java/RegionalTransitAuthor.java')],check=True)
    result=OUT/('port_service_native_'+stamp)
    subprocess.run([str(jdk/'java.exe'),'-Dfile.encoding=UTF-8','-cp',str(classes)+os.pathsep+cp,'RegionalTransitAuthor',str(definition),str(stage),str(result),'--append'],check=True)
    native=json.loads((result/'native_transit_receipt.json').read_text(encoding='utf8'));assert native['passed'] and native['existing_identities_preserved']
    backup=OUT/('port_service_install_'+stamp);backup.mkdir();shutil.copytree(source,backup/'before')
    assert hashes(source)==before,'World railway changed while staging'
    for n in changed:atomic_replace(source/n,(stage/n).read_bytes())
    after=hashes(source)
    assert set(after)==set(before) and all(after[n]==h for n,h in before.items() if n not in changed)
    assert all(after[n]==hashes(stage)[n] for n in changed)
    report=dict(passed=True,changed=changed,other_objects_unchanged=True,repeat=True,dwell_ms=12000,native_receipt=str(result/'native_transit_receipt.json'))
    (OUT/'port_service_install_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(report)
    original=OUT/'port_transit_plan.json';p=json.loads(original.read_text(encoding='utf8'));p['lines'][0].update(repeat=True,dwell=12000);original.write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':main()
