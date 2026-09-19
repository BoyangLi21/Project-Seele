"""Install the native-reviewed camera adaptation as a private runtime clip."""
from pathlib import Path
import datetime,hashlib,json,msvcrt,shutil
from apply_s20_approved_semantic_repairs import atomic_replace
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r24';MAIN=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def role(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
    assert json.loads((ART/'promotion/installed.json').read_text())['installed']
    proof=json.loads((ART/'camera/visual_acceptance.json').read_text());assert proof['passed']
    source=Path(proof['candidate']);source=source if source.is_absolute() else ROOT/source
    assert sha(source)==proof['sha256'];new=json.loads(source.read_text());base=ROOT/'run/projectseele-local-maps/first_battle_r18.json'
    assert sha(base)==new['r24_camera']['source_sha256'];old=json.loads(base.read_text())
    assert all(role(new[k])==role(old[k]) for k in ('eva','angel'))
    destinations=[ROOT/'run/projectseele-local-maps/first_battle_r24.json']
    for directory in (ROOT/'.Codex/world-expansion/server',):
        prior=directory/'projectseele-local-maps/first_battle_r18.json'
        if prior.is_file():
            assert sha(prior)==sha(base),('Server has a different private motion baseline',prior)
        if directory.is_dir():destinations.append(prior.with_name('first_battle_r24.json'))
    backup=ART/'camera/install'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True);saved={};absent=[]
    with (MAIN/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        try:
            for i,target in enumerate(destinations):
                if target.exists():shutil.copy2(target,backup/(str(i)+'.json'));saved[str(target)]=str(backup/(str(i)+'.json'))
                else:absent.append(str(target))
                target.parent.mkdir(parents=True,exist_ok=True)
                atomic_replace(target,source.read_bytes());assert sha(target)==proof['sha256']
            result=dict(installed=True,sha256=proof['sha256'],destinations=list(map(str,destinations)),original_actor_roles_unchanged=True,source_motion=sha(base),saved=saved,previously_absent=absent)
            (ART/'camera/installed.json').write_text(json.dumps(result,indent=2));(MAIN/'r24_camera.json').write_text(json.dumps(result,indent=2));print('Private R24 camera installed',len(destinations),'runtime locations')
        except BaseException:
            for name,path in saved.items():atomic_replace(Path(name),Path(path).read_bytes())
            for name in absent:
                target=Path(name).resolve();assert target.is_relative_to(ROOT.resolve())
                if target.is_file():target.unlink()
            raise
if __name__=='__main__':main()
