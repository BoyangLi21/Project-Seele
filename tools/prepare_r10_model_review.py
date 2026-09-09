"""Create a fresh disposable flat lab and exact native model camera itinerary."""
import json,shutil,msvcrt,math
import nbtlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_ANGEL_MODEL_REVIEW_R10';OUT=ROOT/'artifacts/first_battle_world_r10/models'
def main():
    if not WORLD.exists():
        source=ROOT/'run/saves/SEELE_EVA_MOBILITY_REVIEW_R08';WORLD.mkdir()
        data=nbtlib.load(source/'level.dat');d=data['Data'];d['LevelName']=nbtlib.String('SEELE R10 Angel model review');d.pop('Player',None)
        for key,value in [('SpawnX',0),('SpawnY',-59),('SpawnZ',90)]:d[key]=nbtlib.Int(value)
        data.save(WORLD/'level.dat')
        if (source/'datapacks').exists():shutil.copytree(source/'datapacks',WORLD/'datapacks')
        (WORLD/'session.lock').write_bytes(b'\x00')
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);shots=[]
        for i,name in enumerate(['sachiel','shamshel','zeruel','israfel']):
            x=-90+i*60;position=[x+19.5,-25,88.5];target=[x,-29,0];dx,dy,dz=target[0]-position[0],target[1]-position[1]-1.62,target[2]-position[2]
            shots.append(dict(file='r10_model_'+name+'.png',position=position,yaw=math.degrees(math.atan2(-dx,dz)),pitch=math.degrees(math.atan2(-dy,math.hypot(dx,dz))),warmupTicks=360))
        for p in (WORLD/'r07_photo_views.json',OUT/'native_model_views.json'):p.write_text(json.dumps(shots,indent=2),encoding='utf8')
    print(WORLD)
if __name__=='__main__':main()
