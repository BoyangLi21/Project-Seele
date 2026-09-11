"""Set only the disposable review player's starting position between native takes."""
from pathlib import Path
import argparse,datetime,json,msvcrt,shutil,uuid
import nbtlib

ROOT=Path(__file__).resolve().parents[1]
WORLD=ROOT/'run/saves/SEELE_TV_FACILITIES_R16'
POINTS={'port':(512.5,81,469.5),'flight':(650.5,81,1235.5),'facility':(35,-387,-112)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('scene',choices=POINTS);a=ap.parse_args()
    assert WORLD.resolve().parent==(ROOT/'run/saves').resolve()
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        level=nbtlib.load(WORLD/'level.dat');player=level['Data'].get('Player')
        initialized=player is None
        if initialized:
            # A newly copied review deliberately omits Player. Seed only this
            # disposable copy from the source's inventory/UUID before positioning.
            source=nbtlib.load(ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906/level.dat')
            player=source['Data']['Player'];level['Data']['Player']=player
        bits=0
        for part in player['UUID']:bits=(bits<<32)|(int(part)&0xffffffff)
        player_file=WORLD/'playerdata'/(str(uuid.UUID(int=bits))+'.dat')
        backup=ROOT/'artifacts/tv_facilities_r16/player_setup'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup.mkdir(parents=True)
        files=[(WORLD/'level.dat',level,player)]
        if player_file.exists():
            stored=nbtlib.load(player_file);files.append((player_file,stored,stored))
        for path,data,tag in files:
            shutil.copy2(path,backup/path.name)
            tag['Pos']=nbtlib.List[nbtlib.Double](POINTS[a.scene])
            tag['Motion']=nbtlib.List[nbtlib.Double]([0,0,0])
            tag['FallDistance']=nbtlib.Float(0)
            tag['Dimension']=nbtlib.String('projectseele:geofront')
            temporary=path.with_suffix('.r16.tmp');data.save(temporary);temporary.replace(path)
        (backup/'receipt.json').write_text(json.dumps({'scene':a.scene,'position':POINTS[a.scene],'world':str(WORLD),'initialized_player_from_main':initialized,'fields':['Pos','Motion','FallDistance','Dimension']},indent=2))
        print('Review-only starting position:',a.scene,'backup:',backup)

if __name__=='__main__':main()
