"""Survey whole-route cross sections, including width/roof/edge evidence.

Reads every long, level segment in the complete human/player route catalogue.
No map mutations: candidate corridors still require a named destination.
"""
import json,math
from pathlib import Path
import numpy as np
import scan_regional_completion as scan
from query_blocks import AIR
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r21'
def main():
 baseline=json.loads((OUT/'baseline.json').read_text());scan.WORLD=Path(baseline['backup'])/'world'
 cases=json.loads((scan.WORLD/'quality_walk_cases.json').read_text(encoding='utf8'));segments={}
 for row in cases:
  pts=row.get('path',[row.get('start'),row.get('end')])
  for a,b in zip(pts,pts[1:]):
   if a is None or b is None or abs(a[1]-b[1])>.05:continue
   dx,dz=abs(a[0]-b[0]),abs(a[2]-b[2])
   if min(dx,dz)>.1 or max(dx,dz)<48:continue
   key=tuple(sorted([tuple(map(math.floor,a)),tuple(map(math.floor,b))]));segments.setdefault(key,[]).append(row['id'])
 rows=[]
 for i,((start,end),names) in enumerate(segments.items()):
  if max(start[1],end[1])>=250:continue
  axis='x' if start[0]!=end[0] else 'z';f=start[1]-1;lo=(min(start[0],end[0])-10,f-4,min(start[2],end[2])-10);hi=(max(start[0],end[0])+10,f+12,max(start[2],end[2])+10)
  a,pal=scan.volume(lo,hi,allow_unknown=True);free=np.array([s.split('[')[0] in AIR|{'minecraft:light'} or any(k in s for k in ['escalator_side','wall_sign','button']) for s in pal])[a]
  roof=np.array([s.startswith('projectseele:nerv_') or s.split('[')[0] in ['minecraft:polished_deepslate','minecraft:smooth_stone','minecraft:sea_lantern','minecraft:iron_block','projectseele:clear_glass'] or 'concrete' in s or 'stained_glass' in s for s in pal])[a]
  good=[];evidence=[]
  for n in range(3,int(max(abs(end[0]-start[0]),abs(end[2]-start[2])))-2,3):
   x=start[0]+(n if axis=='x' else 0);z=start[2]+(n if axis=='z' else 0);xx=x-lo[0];zz=z-lo[2];fy=f-lo[1]
   if not free[fy+2,zz,xx] or not free[fy+3,zz,xx]:continue
   ceiling=bool(roof[fy+4:fy+11,zz,xx].any());widths=[]
   for sign in (-1,1):
    width=0
    for offset in range(1,10):
     xxx=xx+(offset*sign if axis=='z' else 0);zzz=zz+(offset*sign if axis=='x' else 0)
     if not free[fy+2,zzz,xxx]:break
     width=offset
    widths.append(width)
   evidence.append(dict(at=[x,start[1],z],roof=ceiling,width=widths))
   if ceiling and all(1<=v<9 for v in widths):good.append(widths)
  fraction=len(good)/max(1,len(evidence));status='enclosed_corridor' if fraction>=.8 else 'mixed_or_outdoor'
  row=dict(id=names[0],aliases=names[1:],start=start,end=end,axis=axis,length=max(abs(end[0]-start[0]),abs(end[2]-start[2])),status=status,roof_and_side_fraction=fraction,minimum_half_width=np.min(good,axis=0).tolist() if good else None,samples=evidence)
  rows.append(row)
  if status=='enclosed_corridor':print(names[0],start,end,'min halves',row['minimum_half_width'],flush=True)
 (OUT/'global_corridor_sections.json').write_text(json.dumps(dict(scanned_unique_long_segments=len(rows),source='Complete pre-R21 route catalogue with actual transverse samples; outdoor and mixed segments retained as explicit classifications',segments=rows),ensure_ascii=False,indent=2),encoding='utf8')
 print('Global long sections',len(rows),flush=True)
if __name__=='__main__':main()
