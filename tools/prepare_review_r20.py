"""One current-world copy for R20; never reset or reuse an older review world."""
from pathlib import Path
import json,msvcrt,shutil,nbtlib
from regional_voxels import ROOT,WORLD

def main():
    dest=ROOT/'run/saves/SEELE_R20_REVIEW'
    if dest.exists():print('R20 review already exists');return
    with (WORLD/'session.lock').open('r+b') as f:
        msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1);shutil.copytree(WORLD,dest,ignore=shutil.ignore_patterns('session.lock','DistantHorizons.sqlite*'))
    level=nbtlib.load(dest/'level.dat');level['Data'].pop('Player',None);level['Data']['LevelName']=nbtlib.String('SEELE R20 reconstruction review');level.save(dest/'level.dat')
    for p in (dest/'playerdata').glob('*.dat'):
        d=nbtlib.load(p);d.pop('RootVehicle',None);d['Pos']=nbtlib.List[nbtlib.Double]([12.5,-566,260.5]);d['Motion']=nbtlib.List[nbtlib.Double]([0,0,0]);d['Dimension']=nbtlib.String('projectseele:geofront');d.save(p)
    (dest/'session.lock').write_bytes(b'\0');print(dest)

if __name__=='__main__':main()
