"""Map-only Xaero markers for measured entrances; retain all personal markers."""
from pathlib import Path
import argparse,json,shutil,datetime
from query_blocks import read_box,AIR
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r21/navigation';REVIEW=ROOT/'run/saves/SEELE_R21_REVIEW'
MARKERS=[
 ('金字塔北联络厅','金',112,-442,245,6),('发射区车站入口','站',150,-442,-28,11),
 ('机库登机层','登',104,-394,-65,3),('三机观察廊','观',104,-367,-221,6),
 ('总部站 U2 入口','站',30,-466,514,11),('地面公共梯前厅','梯',122,75,273,3),
 ('NERV 地面门禁入口','门',-360,81,728,6),('NERV 航空基地','航',441,73,42,11),
 ('NERV 航班登机梯','机',669,73,-1,11),('UN 航班登机梯','机',6712,75,-6108,11),
 ('EVA-UN-00 控制室','0',6402,77,-6136,6),('EVA-UN-01 控制室','1',6242,77,-6136,2),
 ('Terminal Dogma 入口','门',12,-566,278,12)]
def main(apply=False):
 OUT.mkdir(parents=True,exist_ok=True);rows=[]
 for name,initial,x,y,z,colour in MARKERS:
  block=read_box(REVIEW,'projectseele:geofront',(x,y-1,z),(x,y+1,z))
  assert block[x,y-1,z].split('[')[0] not in AIR,('No measured landing',name,block)
  assert all(block[x,yy,z].split('[')[0] in AIR for yy in (y,y+1)),('Occupied marker landing',name,block)
  rows.append(f'waypoint:SEELE {name}:{initial}:{x}:{y}:{z}:{colour}:false:0:gui.xaero_default:false:0:2:false')
 target=ROOT/'run/xaero/minimap/SEELE%us%TV%us%WORLD%us%PREVIEW%us%20260906/dim%projectseele$geofront/waypoints.txt'
 old=target.read_text(encoding='utf8') if target.exists() else '#waypoint:name:initials:x:y:z:color:disabled:type:set:rotate_on_tp:tp_yaw:visibility_type:destination\n'
 owned={'SEELE '+row[0] for row in MARKERS}
 previous=[line for line in old.splitlines() if not(line.startswith('waypoint:') and line.split(':')[1] in owned)]
 result='\n'.join(previous+rows)+'\n';(OUT/'waypoints.txt').write_text(result,encoding='utf8')
 if apply:
  assert (ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906/world_revision_r21.json').exists(),'Install and validate the final main world before publishing its map markers'
  if target.exists():shutil.copy2(target,OUT/('before_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.txt'))
  target.parent.mkdir(parents=True,exist_ok=True);target.write_text(result,encoding='utf8')
 (OUT/'receipt.json').write_text(json.dumps(dict(applied=apply,markers=len(rows),target=str(target),visibility='WORLD_MAP_LOCAL (native ordinal 2): full map only, no floating world labels',personal_markers_retained=True),indent=2))
 print('Prepared map-only navigation markers',len(rows),'applied',apply)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
