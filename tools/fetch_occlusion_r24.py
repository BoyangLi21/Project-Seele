"""Pinned optional client-only occlusion trial; no ticking or terrain replacement."""
from pathlib import Path
import json,re,shutil,datetime
import fetch_renderer_mods_r15 as fetch

ROOT=Path(__file__).resolve().parents[1]
def ensure():
    # 1.7.3 is self-contained. Newer releases embed SRG-named UI libraries
    # that ForgeGradle does not remap inside jars in this development setup.
    fetch.MODS=[('entityculling-forge-1.7.3-mc1.20.1.jar','NNAgCjsB','SdwRMvNg','2a5989064f58342b98045857113aa6e9b7889dcb92bebee2b2de3f97a29f52d26d4b29d7ce4026e6420992064e0f86397e00aeb5777a4d6a568588e42381c088')]
    fetch.main()
    path=ROOT/'run/config/entityculling.json';data=json.loads(path.read_text()) if path.exists() else {}
    backup=ROOT/'.Codex/r24-occlusion-backup'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
    if path.exists():shutil.copy2(path,backup/path.name)
    (backup/'receipt.json').write_text(json.dumps({'previously_existed':path.exists()}))
    own={'projectseele:'+s for s in re.findall(r'register\(\s*"([a-z0-9_]+)"',(ROOT/'src/main/java/com/projectseele/registry/ModEntities.java').read_text(encoding='utf8'))}
    assert len(own)==24
    data.update(tickCulling=False,skipBlockEntityCulling=True,blockEntityFrustumCulling=False,tracingDistance=256)
    data['entityWhitelist']=sorted(set(data.get('entityWhitelist',[]))|own|{'minecraft:player','minecraft:armor_stand'})
    path.write_text(json.dumps(data,indent=2)+'\n');print('Conservative occlusion trial:',len(own),'SEELE entities excluded; all tick culling disabled')
if __name__=='__main__':ensure()
