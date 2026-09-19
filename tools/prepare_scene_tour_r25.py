"""Fixed views of actual R25 structures and reader-height diagrams."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r25/validation'
def main():
 shots=[]
 def add(name,eye,target):shots.append(dict(name=name,eye=eye,target=target,renderDistance=6,warmupTicks=100))
 add('west_lower_command_connection',[-3.5,-432.38,276.5],[8,-428,267])
 add('east_service_command_door',[53.5,-417.38,264.5],[42,-417.5,264.5])
 add('east_lift_lobby',[73.5,-432.38,260.5],[73.5,-432.5,253])
 add('east_bottom_through_gallery',[76.5,-446.38,281.5],[91,-446.5,281.5])
 add('west_observation_lift',[-28.5,-365.38,-284.5],[-29,-365,-278])
 add('observation_sightline',[98,-365.38,-213],[72,-389,-240])
 add('new_carrier_dorsal_portal',[30,-365.38,-281.5],[30,-382,-242])
 add('station_lift_foyer',[99.5,-440.38,-46.5],[110,-440.5,-36])
 add('station_south_port',[115.5,-440.38,-22.5],[114,-440.5,-31])
 add('retired_lower_dead_gallery',[130,-430,-145],[108,-440,-165])
 add('annex_a_continuous_stair',[196.5,-459.38,402.5],[196.5,-464,410])
 add('annex_b_room_access',[328.5,-464.38,450.5],[339,-464.5,450.5])
 add('annex_c_garden_exit',[264,-464,286],[259,-469,278])
 add('pyramid_removed_stair_fragments',[145,-438,258],[133,-444,266])
 add('science_upper_and_lower_fork',[198.5,-459.38,402.5],[198.5,-460,409.5])
 add('texture_tokyo_street',[-133,82.62,-301],[-134.5,81.95,-305.9])
 add('texture_city_station',[-119.5,96.62,-164.5],[-127,95,-174])
 add('texture_surface_launch',[-4,88,-58],[30,81,-36])
 add('texture_geofront_landscape',[191,-446,350],[205,-461,415])
 boards=json.loads((ROOT/'artifacts/facility_r25/station_maps/contract.json').read_text(encoding='utf8'))['boards']
 chosen=[('map_u2_headquarters','NERV 总部','U2'),('map_u2_hangars','EVA 机库','U2'),('map_u1_gateway','地下都市入口','U1'),('map_r1_tokyo','第三新东京中央','R1'),('map_s1_hakone','新箱根中央','S1')]
 for name,station,line in chosen:
  b=next(q for q in boards if q['station']==station and q['line']==line);x,y,z=b['position'];nx,nz={'north':(0,-1),'south':(0,1),'east':(1,0),'west':(-1,0)}[b['facing']]
  add(name,[x+.5+nx*4,b['reader'][1]+1.62,z+.5+nz*4],[x+.5,y+.85,z+.5])
 for i,b in enumerate(json.loads((ROOT/'artifacts/facility_r25/transfer_signs/contract.json').read_text())['boards']):
  x,y,z=b['position'];nx,nz={'north':(0,-1),'south':(0,1),'east':(1,0),'west':(-1,0)}[b['facing']]
  add('interchange_'+str(i),[x+.5+nx*3,y+.35,z+.5+nz*3],[x+.5,y+.5,z+.5])
 OUT.mkdir(parents=True,exist_ok=True)
 data=json.dumps(shots,ensure_ascii=False,indent=2)
 (OUT/'r25_worldtour.json').write_text(data,encoding='utf8');(ROOT/'run/projectseele-local-maps/r25_worldtour.json').write_text(data,encoding='utf8')
 print('Native scene views',len(shots))
if __name__=='__main__':main()
