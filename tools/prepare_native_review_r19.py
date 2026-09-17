"""Make one isolated current-world copy for R19 runtime validation."""
from pathlib import Path
import json,shutil,msvcrt
import nbtlib
from regional_voxels import ROOT,WORLD

DEST=ROOT/'run/saves/SEELE_R19_NATIVE_REVIEW'

def main():
    if DEST.exists():raise RuntimeError('R19 review already exists; preserve its evidence')
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        shutil.copytree(WORLD,DEST,ignore=shutil.ignore_patterns('session.lock','DistantHorizons.sqlite*'))
    level=nbtlib.load(DEST/'level.dat');data=level['Data'];data['LevelName']=nbtlib.String('SEELE R19 runtime verification');data.pop('Player',None);level.save(DEST/'level.dat')
    for file in (DEST/'playerdata').glob('*.dat'):
        tag=nbtlib.load(file);tag.pop('RootVehicle',None);tag['Pos']=nbtlib.List[nbtlib.Double]([10.5,-566,260.5]);tag['Dimension']=nbtlib.String('projectseele:geofront');tag['Motion']=nbtlib.List[nbtlib.Double]([0,0,0]);tag.save(file)
    (DEST/'session.lock').write_bytes(b'\0')
    out=ROOT/'artifacts/world_repair_r19';(out/'review_copy.json').write_text(json.dumps({'source':str(WORLD),'copy':str(DEST),'scope':'isolated gameplay verification; original world/player preserved'},indent=2))
    print(DEST)

if __name__=='__main__':main()
