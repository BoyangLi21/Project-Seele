"""Freeze this explicitly requested intermediate checkpoint for human inspection."""
from pathlib import Path
import datetime,hashlib,json,msvcrt,shutil
import nbtlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/access_r22';WORLD=ROOT/'run/saves/SEELE_R22_REVIEW'
def main():
 stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=OUT/('manual_handoff_'+stamp);backup.mkdir()
 baseline=json.loads((OUT/'baseline.json').read_text());unchanged={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in baseline['preexisting_dirty_files'].items()};assert all(unchanged.values()),unchanged
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  targets=[WORLD/'level.dat']+list((WORLD/'playerdata').glob('*.dat'))
  for path in targets:
   target=backup/path.relative_to(WORLD);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
   data=nbtlib.load(path);player=data['Data'].get('Player') if path.name=='level.dat' else data
   if player is not None:
    player['Pos']=nbtlib.List[nbtlib.Double]([nbtlib.Double(-335.5),nbtlib.Double(-466),nbtlib.Double(739.5)])
    player['Motion']=nbtlib.List[nbtlib.Double]([nbtlib.Double(0)]*3);player['Rotation']=nbtlib.List[nbtlib.Float]([nbtlib.Float(0),nbtlib.Float(0)])
    player['Dimension']=nbtlib.String('projectseele:geofront');player['Health']=nbtlib.Float(20);player['FallDistance']=nbtlib.Float(0);player['playerGameType']=nbtlib.Int(1)
    abilities=player.get('abilities',nbtlib.Compound());abilities['flying']=nbtlib.Byte(0);abilities['mayfly']=nbtlib.Byte(1);abilities['instabuild']=nbtlib.Byte(1);abilities['invulnerable']=nbtlib.Byte(1);player['abilities']=abilities
   if path.name=='level.dat':data['Data']['LevelName']=nbtlib.String('SEELE R22 阶段人工验收');data['Data']['GameType']=nbtlib.Int(1)
   data.save(path)
  receipt={'timestamp':stamp,'world':str(WORLD),'status':'USER_REQUESTED_INTERMEDIATE_CHECKPOINT','spawn':[-335.5,-466,739.5],'main_world_map_not_overwritten':True,'auto_review_disabled':True,'preexisting_user_files_preserved':unchanged,'known_open_issue':'Elevator frame motion is stable in the latest sampled ascent, but corner-walking on arrival still triggers one inWall contact; not complete.','next_round':'docs/NEXT_ROUND_R22.md'}
  (WORLD/'r22_manual_handoff.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8');(OUT/'manual_handoff.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
 print('R22 manual checkpoint ready; original world map untouched; spawn at direct station corridor')
if __name__=='__main__':main()
