"""Whole-width portals join existing destinations; no new mouth ends over air."""
from pathlib import Path
import json,numpy as np
import regional_voxels as v,scan_regional_completion as scan,plan_factory_r20 as f,repair_facility_r21 as h
from query_blocks import iter_block_entities
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R25_REVIEW';OUT=ROOT/'artifacts/facility_r25/port_finish'
def main():
 OUT.mkdir(parents=True,exist_ok=True);v.WORLD=scan.WORLD=WORLD;v.OUT=OUT;p=v.Painter();walks=[];records=[]
 def scene(lo,hi):f.LO=h.LO=lo;f.HI=h.HI=hi;return h.Facility()
 def finish(s,name):
  change=s.before!=s.after
  for q,t in iter_block_entities(WORLD,v.DIM,f.LO,f.HI):
   if change[q[1]-f.LO[1],q[2]-f.LO[2],q[0]-f.LO[0]]:raise RuntimeError(('Existing fixture at corrected portal',q,t.snbt()))
  records.append(dict(id=name,cells=s.delta(p,'r25/'+name)));walks.extend(s.walks)
 s=scene((45,-421,262),(49,-415,266))
 s.fill((47,-419,263,47,-417,265),'minecraft:air')
 s.path('east_service_actual_room',[[49.5,-419,264.5],[43.5,-419,264.5]])
 finish(s,'east_service_glazed_threshold')
 s=scene((73,-451,275),(92,-442,285))
 # Join the bottom lift lobby to the retained east gallery at Z=281.
 # Its former south mouth at Z=282 stopped one cell before an empty drop.
 s.hall('east_lower_existing_gallery',[(74,89,279,283)],-449,5,
        [(75,-448,279,77,-445,279),(89,-448,280,89,-445,282)])
 s.fill((74,-448,282,77,-445,282),'minecraft:air')
 s.path('east_lower_through',[[76.5,-448,277.5],[76.5,-448,281.5],[90.5,-448,281.5],[90.5,-448,286.5],[89.5,-448,286.5]])
 finish(s,'bottom_lift_to_retained_east_gallery')
 s=scene((97,-444,-50),(117,-436,-23))
 s.fill((98,-442,-49,100,-438,-49),f.WALL)
 s.fill((98,-441,-49,100,-439,-49),'projectseele:clear_glass')
 s.fill((109,-442,-25,113,-438,-25),f.WALL)
 s.fill((109,-441,-25,113,-439,-25),'projectseele:clear_glass')
 s.fill((114,-442,-25,116,-439,-25),'minecraft:air')
 s.path('station_direct_pyramid_exit',[[112.5,-442,-30.5],[115.5,-442,-26.5],[115.5,-442,-22.5],[118.5,-442,-18.5]])
 finish(s,'safe_station_south_port_and_closed_blind_north_port')
 s=scene((255,-467,261),(262,-460,263))
 s.fill((256,-466,262,256,-463,262),f.WALL);s.fill((257,-466,262,261,-463,262),'minecraft:air')
 for x in (257.5,258.5,259.5,260.5,261.5):s.path('garden_entrance_width_'+str(x),[[x,-466,260.5],[x,-466,265.5]])
 finish(s,'whole_two_lane_garden_threshold')
 for row in walks:row['id']=row['id'].replace('r21/','r25/',1)
 p.meta.update(repairs=records,walk_nodes=walks);p.apply('whole_width_connected_ports')
 (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
 # The retired north alcove is no longer a destination in the test route.
 path=ROOT/'artifacts/facility_r25/route_repairs/contract.json';data=json.loads(path.read_text(encoding='utf8'))
 for row in data['walk_nodes']:
  if row['id'] in ('r25/station_west_link','r25/station_west_link/return'):
   nodes=row['path'];nodes=[([99.5,-442,-46.5] if q==[99.5,-442,-48.5] else q) for q in nodes];row.update(path=nodes,start=nodes[0],end=nodes[-1])
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
 print('Full-width public port corrections',records)
if __name__=='__main__':main()
