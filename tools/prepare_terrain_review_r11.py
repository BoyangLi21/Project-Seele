"""Create a disposable terrain lab from settings only; never copy or modify the main city."""
from pathlib import Path
import shutil,nbtlib
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_TERRAIN_REVIEW_R11'
if __name__=='__main__':
 if not WORLD.exists():
  source=ROOT/'run/saves/SEELE_EVA_MOBILITY_REVIEW_R08';WORLD.mkdir();d=nbtlib.load(source/'level.dat');v=d['Data'];v['LevelName']=nbtlib.String('SEELE R11 terrain continuity lab');v.pop('Player',None)
  for k,n in [('SpawnX',0),('SpawnY',-59),('SpawnZ',-40)]:v[k]=nbtlib.Int(n)
  d.save(WORLD/'level.dat');shutil.copytree(source/'datapacks',WORLD/'datapacks');(WORLD/'session.lock').write_bytes(b'\0')
 print(WORLD)
