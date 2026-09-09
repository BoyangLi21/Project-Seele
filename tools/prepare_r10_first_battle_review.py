"""Create the isolated native driving/encounter review; never reset an existing review save."""
import shutil,sys,time
from pathlib import Path
import nbtlib
ROOT=Path(__file__).resolve().parents[1]
WORLD=ROOT/'run/saves/SEELE_FIRST_BATTLE_REVIEW_R10'
if __name__=='__main__':
    if '--new-cycle' in sys.argv and WORLD.exists():
        import msvcrt
        with (WORLD/'session.lock').open('r+b') as lock:
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
            out=ROOT/'artifacts/first_battle_world_r10/review_history'/str(int(time.time()));out.mkdir(parents=True)
            for name in ['r10_resume_expected.json','r10_first_battle_review.json']:
                p=WORLD/name
                if p.exists():shutil.move(p,out/name)
    if not WORLD.exists():
        source=ROOT/'run/saves/SEELE_EVA_MOBILITY_REVIEW_R08'
        WORLD.mkdir()
        data=nbtlib.load(source/'level.dat');d=data['Data'];d['LevelName']=nbtlib.String('SEELE R10 first battle review');d.pop('Player',None)
        for k,v in [('SpawnX',0),('SpawnY',-59),('SpawnZ',-18)]:d[k]=nbtlib.Int(v)
        data.save(WORLD/'level.dat')
        if (source/'datapacks').exists():shutil.copytree(source/'datapacks',WORLD/'datapacks')
        (WORLD/'session.lock').write_bytes(b'\x00')
    print(WORLD)
