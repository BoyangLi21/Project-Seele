"""Reproducible local voxel sections at the user's R25 defects."""
from pathlib import Path
import json
from collections import Counter
from query_blocks import read_box, AIR, iter_block_entities
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R25_REVIEW';OUT=ROOT/'artifacts/facility_r25/survey';DIM='projectseele:geofront'
POINTS={'west_low':(-4,-434,273),'west_midlow':(-4,-421,273),'west_midhigh':(-4,-407,273),'west_high':(-4,-393,273),'east':(76,-393,281),'east_lift':(73,-430,256),'bricks':(136,-444,264),'legacy_a':(200,-459,397),'legacy_b':(328,-465,441),'legacy_c':(258,-466,273),'station_link':(103,-442,-40),'dead_corridor':(107,-442,-143),'wall_positive':(90,-365,214),'wall_negative':(90,-365,-214),'protrusion':(91,-367,-220),'new_lift':(-32,-367,-276)}
def symbol(s):
 if s in AIR:return '.'
 if 'glass' in s:return 'G'
 if 'escalator' in s:return 'e'
 if 'stairs' in s:return 's'
 if 'slab' in s:return '_'
 if 'sign' in s or 'panel' in s and ('direction' in s or 'departure' in s):return 'S'
 if 'elevator' in s:return 'E'
 if 'lcl' in s:return '~'
 if 'light' in s or 'lantern' in s:return '*'
 if 'rail' in s:return 'r'
 if 'barrier' in s:return 'B'
 return '#'
def main():
 OUT.mkdir(parents=True,exist_ok=True);reports=[]
 for name,(x,y,z) in POINTS.items():
  lo=(x-10,y-8,z-12);hi=(x+14,y+8,z+12);a=read_box(WORLD,DIM,lo,hi)
  lines=[name+' '+str((x,y,z)),'. air, # solid, G glass, e escalator, s stair, _ slab, E elevator, r rail, S sign, B barrier']
  for Y in (y-1,y,y+1):
   lines.append(f'Y={Y} x={lo[0]}..{hi[0]}')
   for Z in range(lo[2],hi[2]+1):lines.append(f'{Z:5} '+''.join(symbol(a.get((X,Y,Z),'UNKNOWN')) for X in range(lo[0],hi[0]+1)))
  lines.append(f'XZ vertical at z={z}, x={lo[0]}..{hi[0]}')
  for Y in range(hi[1],lo[1]-1,-1):lines.append(f'{Y:5} '+''.join(symbol(a.get((X,Y,z),'UNKNOWN')) for X in range(lo[0],hi[0]+1)))
  lines.append('Material counts '+str(Counter(a.values()).most_common(20)))
  (OUT/(name+'.txt')).write_text('\n'.join(lines),encoding='utf8')
  reports.append(dict(id=name,point=(x,y,z),lo=lo,hi=hi,states=Counter(a.values()),block_entities=[dict(pos=q,snbt=n.snbt()) for q,n in iter_block_entities(WORLD,DIM,lo,hi)]))
 (OUT/'survey.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf8')
 print('Measured',len(reports),'local volumes',OUT)
if __name__=='__main__':main()
