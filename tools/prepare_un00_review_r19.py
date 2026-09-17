"""Install an isolated preview pack and clone the existing mechanics test lab."""
import argparse,json,shutil,msvcrt
from pathlib import Path
import nbtlib

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r19/un00_local';CAND=OUT/'runtime_candidate/assets/projectseele'
PACK=ROOT/'run/resourcepacks/eva_un00_r19_preview';NAME='file/eva_un00_r19_preview';OPTIONS=ROOT/'run/options.txt'

def main(disable=False):
    lines=OPTIONS.read_text(encoding='utf8').splitlines();result=[]
    for line in lines:
        key,sep,value=line.partition(':')
        if key=='resourcePacks':
            packs=json.loads(value);packs=[p for p in packs if p!=NAME]
            if not disable:packs.append(NAME)
            line=key+':'+json.dumps(packs,separators=(',',':'))
        result.append(line)
    if disable:OPTIONS.write_text('\n'.join(result)+'\n',encoding='utf8');print('UN candidate pack disabled');return
    if not (OUT/'options_before_preview.txt').exists():shutil.copy2(OPTIONS,OUT/'options_before_preview.txt')
    audit=json.loads((OUT/'runtime_geometry_audit.json').read_text());assert audit['passed'] and audit['triangles']==139806
    for relative in ('mesh/eva_prototype.mesh.json','geo/eva_prototype.geo.json','animations/eva_prototype.animation.json','textures/entity/eva_prototype.png','textures/entity/eva_prototype_eyes.png'):
        target=PACK/'assets/projectseele'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(CAND/relative,target)
    (PACK/'pack.mcmeta').write_text(json.dumps({'pack':{'pack_format':15,'description':'EVA-UN-00 R19 private review candidate'}},indent=2))
    source=ROOT/'run/saves/SEELE_MECHANICS_REVIEW_R11';dest=ROOT/'run/saves/SEELE_UN_R19_REVIEW'
    if not dest.exists():
        with (source/'session.lock').open('r+b') as lock:
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);shutil.copytree(source,dest,ignore=shutil.ignore_patterns('session.lock','DistantHorizons.sqlite*'))
        (dest/'session.lock').write_bytes(b'\0');level=nbtlib.load(dest/'level.dat');level['Data']['LevelName']=nbtlib.String('EVA-UN-00 R19 isolated mechanics review');level.save(dest/'level.dat')
    OPTIONS.write_text('\n'.join(result)+'\n',encoding='utf8')
    print('Private candidate pack enabled; disposable lab',dest)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--disable',action='store_true');main(a.parse_args().disable)
