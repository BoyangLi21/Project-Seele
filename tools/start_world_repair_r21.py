"""Freeze the current user world and inventory R21's reported spatial defects."""
from pathlib import Path
import datetime, json, msvcrt, shutil, subprocess, hashlib
import numpy as np
import nbtlib
import scan_regional_completion as scan
from query_blocks import iter_block_entities

ROOT=Path(__file__).resolve().parents[1]
WORLD=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'
REVIEW=ROOT/'run/saves/SEELE_R21_REVIEW'
OUT=ROOT/'artifacts/world_repair_r21'
SITES={'pyramid_escalator':[118,-442,240], 'surplus_platform':[155,-443,223],
 'launch_station_edge':[107,-441,-30], 'launch_junction':[90,-441,-45],
 'middle_lift_approach':[100,-394,-58], 'cage_middle_gallery':[92,-394,-266],
 'commander_observation':[90,-367,-221], 'upper_lift_edge':[97,-369,-56],
 'retired_outer_escalator':[102,-394,-255], 'floating_weapon_shaft':[26,81,-114],
 'retired_weapon_shaft':[28,81,296], 'abandoned_road':[-61,103,24],
 'retractable_battle_square':[32,80,217], 'nerv_airport':[395,65,-31]}

def sha(p):
    return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if not (OUT/'baseline.json').exists():
        rows=subprocess.check_output(['git','status','--porcelain','-uall','-z'],cwd=ROOT).decode().split('\0')
        dirty={r[3:]:sha(ROOT/r[3:]) for r in rows if r and (ROOT/r[3:]).is_file() and r[3:]!='tools/start_world_repair_r21.py'}
        backup=ROOT/'backups'/('SEELE_R21_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
        with (WORLD/'session.lock').open('r+b') as lock:
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
            shutil.copytree(WORLD,backup/'world',ignore=shutil.ignore_patterns('session.lock','DistantHorizons.sqlite*'))
            shutil.copytree(WORLD,REVIEW,ignore=shutil.ignore_patterns('session.lock','DistantHorizons.sqlite*'))
        (REVIEW/'session.lock').write_bytes(b'\0')
        level=nbtlib.load(REVIEW/'level.dat');level['Data']['LevelName']=nbtlib.String('SEELE R21 spatial repair review');level.save(REVIEW/'level.dat')
        (OUT/'baseline.json').write_text(json.dumps(dict(world=str(WORLD),review=str(REVIEW),backup=str(backup),preexisting_dirty_files=dirty,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()),indent=2),encoding='utf8')
        print('Cold baseline',backup,flush=True)
    (OUT/'reported_sites.json').write_text(json.dumps(SITES,indent=2),encoding='utf8')
    scan.WORLD=WORLD
    for name,lo,hi in [('pyramid_east',(65,-471,195),(175,-413,355)),('factory_east',(75,-450,-298),(148,-345,20)),('cages',(-38,-448,-292),(116,-343,-194)),('surface_core',(-160,60,-165),(224,125,405)),('airport_site',(290,40,-135),(650,140,105))]:
        target=OUT/'survey'/name;target.mkdir(parents=True,exist_ok=True)
        a,pal=scan.volume(lo,hi,allow_unknown=True)
        np.savez_compressed(target/'measured.npz',blocks=a,palette=np.asarray(pal),lo=lo,hi=hi)
        be=[dict(pos=p,snbt=t.snbt()) for p,t in iter_block_entities(WORLD,'projectseele:geofront',lo,hi)]
        (target/'block_entities.json').write_text(json.dumps(be,ensure_ascii=False),encoding='utf8')
        counts=np.bincount(a.flatten(),minlength=len(pal));summary={s:int(n) for s,n in zip(pal,counts) if n}
        (target/'counts.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
        print(name,a.shape,'states',len(pal),'fixtures',len(be),flush=True)

if __name__=='__main__':main()
