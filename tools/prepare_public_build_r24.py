"""Prepare a clean public-source build snapshot, excluding local/user work.

This does not publish, stage or commit anything. Protected user modifications
remain in the real checkout and use their existing HEAD versions in this test.
"""
from pathlib import Path
import datetime,hashlib,json,shutil,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r24/release'

def main():
    baseline=json.loads((ROOT/'artifacts/facility_r24/baseline.json').read_text(encoding='utf8'));protected=baseline['original_user_files']
    for name,sha in protected.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');folder=ROOT/'.Codex'/('r24-public-build-'+stamp);folder.mkdir();archive=folder/'head.zip';source=folder/'source';source.mkdir()
    subprocess.run(['git','archive','--format=zip','--output='+str(archive),'HEAD'],cwd=ROOT,check=True)
    with zipfile.ZipFile(archive) as stream:
        for info in stream.infolist():assert (source/info.filename).resolve().is_relative_to(source.resolve()),info.filename
        stream.extractall(source)
    def names(args):return subprocess.check_output(['git',*args],cwd=ROOT).decode('utf8').split('\0')
    changed=set(names(['-c','core.autocrlf=false','diff','--name-only','-z','HEAD']))|set(names(['ls-files','--others','--exclude-standard','-z']))
    copied=[]
    for name in sorted(changed):
        if not name or name in protected or name.endswith('.class'):continue
        path=(ROOT/name).resolve();assert path.is_relative_to(ROOT.resolve())
        if not path.is_file():continue
        dest=(source/name).resolve();assert dest.is_relative_to(source.resolve());dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
        copied.append(dict(path=name,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    assert not (source/'run').exists() and not (source/'external-assets').exists()
    report=dict(source=str(source),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),overlaid=copied,protected_user_files_not_overlaid=list(protected),private_worlds_or_packs_copied=False)
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'clean_build_snapshot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(source,flush=True)
if __name__=='__main__':main()
