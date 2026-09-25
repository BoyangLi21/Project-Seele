"""Promote the tested shader selection; preserve the owner's current save."""
from pathlib import Path
import datetime,hashlib,json,shutil
from release_combat_r36 import guard
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/transport_return_r39'
def main():
    guard()
    report=json.loads((OUT/'native.json').read_text());assert report['passed']
    light=json.loads((OUT/'lighting_review.json').read_text());assert light['passed']
    source=OUT/'shaders/ComplementaryUnbound_r5.3_SEELE_R39.zip'
    digest=hashlib.sha256(source.read_bytes()).hexdigest();assert digest==light['shader_sha256']
    baseline=json.loads((OUT/'baseline.json').read_text(encoding='utf8'));world=ROOT/'run/saves/SEELE_R31_WORLD'
    for name,row in baseline['files'].items():
        p=world/name;assert p.stat().st_size==row['size'] and p.stat().st_mtime_ns==row['mtime'],name
    backup=OUT/('runtime_backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
    config=ROOT/'run/config/oculus.properties';shutil.copy2(config,backup/config.name)
    marker=ROOT/'run/projectseele-local-maps/revision_r39.json'
    if marker.exists():shutil.copy2(marker,backup/marker.name)
    for p in (source,source.with_name(source.name+'.txt')):shutil.copy2(p,ROOT/'run/shaderpacks'/p.name)
    lines=[s for s in config.read_text(encoding='utf8').splitlines() if s.partition('=')[0] not in ('enableShaders','shaderPack')]
    config.write_text('\n'.join(lines+['enableShaders=true','shaderPack='+source.name])+'\n',encoding='utf8')
    data=dict(revision=39,protocol=44,shader=dict(filename=source.name,sha256=digest),world_modified=False,world='SEELE_R31_WORLD',backup=str(backup))
    marker.write_text(json.dumps(data,indent=2),encoding='utf8');(OUT/'installed.json').write_text(json.dumps(data,indent=2),encoding='utf8')
    print('R39 selected; original progress preserved')
if __name__=='__main__':main()
