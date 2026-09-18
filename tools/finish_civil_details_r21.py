"""Remove source-identified obsolete civil works and finish airport approaches."""
from pathlib import Path
import json
import numpy as np
import regional_voxels as v
from query_blocks import read_box,AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R21_REVIEW';OUT=ROOT/'artifacts/world_repair_r21/details'
def main():
 v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();o='r21/retired_legacy_transit';report=[]
 footprints=json.loads((WORLD/'r21_moving_city_footprints.json').read_text())
 # Source geometry is Tokyo3LandscapeBuilder's old expressway and vanilla
 # minecart branch. Neither belongs to the commissioned MTR route graph.
 for name,lo,hi in [('expressway',(-284,81,16),(343,110,32)),('old_minecart_rail',(218,81,-93),(235,103,533))]:
  cells=read_box(WORLD,v.DIM,lo,hi);n=0
  for q,s in cells.items():
   x,y,z=q;base=s.split('[')[0]
   if base in AIR|{'minecraft:light','minecraft:structure_void'}:continue
   if any(a<=x<=c and b<=z<=d and y<=81+h+2 for a,b,c,d,h in footprints):continue
   # Imported towers and the newly commissioned airport are outside these
   # source envelopes. Underground/ground pavement is never included.
   if name=='expressway' and y<101:
    support=any(abs(x-(30+u))<=1 for u in range(-276,277,24) if abs(u-196)>10)
    if not support or abs(z-24)>1 or base!='minecraft:iron_block':continue
   if not(base.startswith('minecraft:') or base.startswith('projectseele:nerv_')):raise RuntimeError(('Unclassified old civil cell',q,s))
   if v.natural(s):continue
   p.match((*q,*q),s,'minecraft:air',o+'/'+name);n+=1
  report.append(dict(id=name,bounds=[lo,hi],removed=n))
 # Both UN gate heads use fixed red warning panels; sliding leaves never
 # carry control buttons or duplicate NERV insignia.
 for cx in (6442,6282):
  for dx in (-19,19):
   p.put(cx+dx,143,-6136,'projectseele:nerv_structural_panel','r21/un_warning_bracket','owned')
   p.put(cx+dx,144,-6136,'projectseele:nerv_warning_beacon[lit=false]','r21/un_warning_beacon','owned')
 # Complete the newly built airport's long passenger hall with two proper
 # balustraded MTR belts. Plain landing areas remain at both room entrances.
 for start,direction in [(19,True),(25,False)]:
  for x in range(450,656):
   for dz,side in [(0,'left'),(1,'right')]:
    for y,kind in [(72,'escalator_step'),(73,'escalator_side')]:
     prop=f'facing=east,orientation=flat,side={side}'
     if kind=='escalator_step':prop=f'direction={str(direction).lower()},'+prop+',status=true'
     p.put(x,y,start+dz,f'mtr:{kind}[{prop}]','r21/airport_moving_walk','owned')
 # The terminal's west entrance is connected by a gradual, full-width access
 # stair to the existing city boulevard under its railway viaduct.
 for x in range(325,386):
  f=80 if x<=330 else max(72,80-(x-330)//3)
  for z in range(34,43):
   p.fill(x,68,z,x,f-1,z,'minecraft:stone','r21/airport_city_access','owned')
   state='minecraft:smooth_quartz_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]' if 332<=x<=354 and (x-330)%3==2 else 'projectseele:nerv_floor_panel'
   p.put(x,f,z,state,'r21/airport_city_access','owned');p.fill(x,f+1,z,x,f+4,z,'minecraft:air','r21/airport_city_access','owned')
 # Airport terminal north doorway at x385..390 meets that low landing.
 p.fill(379,72,34,390,72,40,'projectseele:nerv_floor_panel','r21/airport_city_access','owned')
 p.fill(379,73,34,390,77,40,'minecraft:air','r21/airport_city_access','owned')
 p.meta.update(retired=report,source_contract='Tokyo3LandscapeBuilder HIGHWAY_Z=-196/HIGHWAY_DECK_Y=22; RAIL_X=196/RAIL_DECK_Y=12, world origin 30/80/220',walk_nodes=[dict(id='r21/airport/city_entry',path=[[325.5,81,38.5],[385.5,73,38.5]])])
 p.apply('legacy_retirement_and_airport_finish')
 print(report)
if __name__=='__main__':main()
