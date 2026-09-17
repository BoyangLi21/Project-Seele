"""Final evidence cameras after the last measured map and material repairs."""
import json
from pathlib import Path
import prepare_worldtour_r19

ROOT=Path(__file__).resolve().parents[1]

def main():
    prepare_worldtour_r19.main();p=ROOT/'run/projectseele-local-maps/r19_worldtour.json';allshots=json.loads(p.read_text())
    keep={'board_C1_tokyo_central','board_U1_geo_arrival','board_U2_hangar','board_S2_kirisato','board_P1_port','C1_reported_cut','shore_reported_seam','escalator_transition','pyramid_stair_join','hangar_station_join','staff_misato','staff_ritsuko','staff_maya','staff_fuyutsuki'}
    shots=[s for s in allshots if s['name'] in keep]
    shots.extend([
        dict(name='launch_buttress_services',eye=[9.5,-400,-28],target=[9.5,-414,-53.5]),
        dict(name='cage_lcl_and_body',eye=[17.5,-402,-97.5],target=[30.5,-424,-93.5]),
        dict(name='quay_crane_and_fire_point',eye=[1381.5,76,450.5],target=[1418,85,375]),
        dict(name='quay_grounded_fire_point',eye=[1399.5,68,458.5],target=[1408.5,66.5,450.5]),
        dict(name='UN00_installed',eye=[6442.5,100,-6157.5],target=[6442.5,101,-6205.5]),
        dict(name='airport_ceiling_hangers',eye=[-1640.5,91,-369],target=[-1643,98,-386])])
    fixtures=json.loads((ROOT/'artifacts/world_repair_r19/fixture_supports/grounded_lights_and_baffles/places.json').read_text())
    lamp=fixtures['road_lamps'][0];x,y,z=lamp['base']
    shots.append(dict(name='tokyo_street_light',eye=[x+7.5,y+2.7,z+5.5],target=[x+.5,y+4,z+.5]))
    for s in shots:s['warmupTicks']=260
    p.write_text(json.dumps(shots,indent=2));(ROOT/'artifacts/world_repair_r19/final_camera_plan.json').write_text(json.dumps(shots,indent=2));print('Final cameras',len(shots))

if __name__=='__main__':main()
