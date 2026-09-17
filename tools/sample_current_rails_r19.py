"""Cold-copy current MTR data, then ask the installed MTR runtime for its curves."""
from pathlib import Path
import shutil,msvcrt,subprocess,json,hashlib
from regional_voxels import ROOT,WORLD

def hashes(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

def main():
    stage=ROOT/'.Codex/world_repair_r19/transit_survey';out=ROOT/'artifacts/world_repair_r19/rails';out.mkdir(parents=True,exist_ok=True)
    if not stage.exists():
        with (WORLD/'session.lock').open('r+b') as lock:
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);before=hashes(WORLD/'mtr');shutil.copytree(WORLD/'mtr',stage)
            assert before==hashes(stage)==hashes(WORLD/'mtr')
            (out/'native_copy.json').write_text(json.dumps({'source':str(WORLD/'mtr'),'copy':str(stage),'source_hashes':before},indent=2))
    java=Path.home()/'jdks/jdk-17.0.19+10/bin';classes=ROOT/'.Codex/world_repair_r19/java';classes.mkdir(parents=True,exist_ok=True)
    cache=Path.home()/'.gradle/caches/modules-2/files-2.1/org.apache.logging.log4j'
    cp=';'.join(map(str,[ROOT/'.Codex/local-mods/MTR-forge-4.0.5+1.20.1.jar']+sorted(cache.glob('*/2.19.0/*/*.jar'))))
    subprocess.run([str(java/'javac.exe'),'-encoding','UTF-8','-cp',cp,'-d',str(classes),str(ROOT/'tools/java/CurrentRailSurveyR19.java')],check=True)
    subprocess.run([str(java/'java.exe'),'-cp',cp+';'+str(classes),'CurrentRailSurveyR19',str(stage),str(out/'current_train_samples.json')],check=True)

if __name__=='__main__':main()
