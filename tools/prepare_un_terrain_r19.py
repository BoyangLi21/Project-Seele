"""Clone only the disposable terrain laboratory for UN rig/collision review."""
from pathlib import Path
import shutil,msvcrt
import nbtlib

ROOT=Path(__file__).resolve().parents[1]
def main():
    source=ROOT/'run/saves/SEELE_TERRAIN_REVIEW_R11';dest=ROOT/'run/saves/SEELE_UN_TERRAIN_R19_REVIEW'
    if dest.exists():print('Existing review retained',dest);return
    with (source/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);shutil.copytree(source,dest,ignore=shutil.ignore_patterns('session.lock','DistantHorizons.sqlite*'))
    (dest/'session.lock').write_bytes(b'\0');level=nbtlib.load(dest/'level.dat');level['Data']['LevelName']=nbtlib.String('EVA-UN-00 R19 terrain and motion review');level.save(dest/'level.dat');print(dest)

if __name__=='__main__':main()
