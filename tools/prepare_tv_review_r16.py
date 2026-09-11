"""Copy the current commissioned world for native testing and camera work."""
from pathlib import Path
import shutil,json,msvcrt,math
import nbtlib
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906';DEST=ROOT/'run/saves/SEELE_TV_FACILITIES_R16';OUT=ROOT/'artifacts/tv_facilities_r16'
def main():
 if DEST.exists():raise RuntimeError('Existing R16 review retained; do not overwrite its evidence')
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  shutil.copytree(WORLD,DEST,ignore=shutil.ignore_patterns('session.lock','DistantHorizons.sqlite*','*_failure*'))
  data=nbtlib.load(DEST/'level.dat');data['Data'].pop('Player',None);data['Data']['LevelName']=nbtlib.String('SEELE TV facility review R16');data.save(DEST/'level.dat');(DEST/'session.lock').write_bytes(b'\0')
  views=[]
  for name,eye,target in [('r16_cage_front',(32,-388,-121),(30,-395,-96)),('r16_cage_rear',(46,-382,-77),(30,-390,-89)),('r16_launch_lower',(39,-387,-48),(30,-412,-36)),('r16_shaft_shutter',(38,-308,-47),(30,-332,-36))]:
   dx,dy,dz=target[0]-eye[0],target[1]-eye[1],target[2]-eye[2];views.append(dict(file=name+'.png',position=[eye[0],eye[1]-1.62,eye[2]],yaw=math.degrees(math.atan2(-dx,dz)),pitch=math.degrees(math.atan2(-dy,math.hypot(dx,dz))),warmupTicks=500))
  (DEST/'r07_photo_views.json').write_text(json.dumps(views,indent=2),encoding='utf8')
 (OUT/'review_copy.json').write_text(json.dumps(dict(source=str(WORLD),destination=str(DEST),regional_metadata_copied=True),indent=2));print(DEST)
if __name__=='__main__':main()
