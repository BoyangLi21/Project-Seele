"""Reshoot obsolete camera heights and allow destination terrain to finish loading."""
from pathlib import Path
import json,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r23/validation'
p=ROOT/'run/projectseele-local-maps/r23_worldtour.json'
original=json.loads((OUT/'worldtour.json').read_text(encoding='utf8'))
changes={
    'station_tokyo_platform':([-145.5,96.62,-164.5],[-104,96,-164.5]),
    'station_tokyo_waiting_room':([-131,96.62,-157],[-114,96,-157]),
    'station_tokyo_concourse':([-190.5,82.62,-185.5],[-177.5,88,-181.5]),
    'hakone_interchange':([-1479.5,120.62,666.5],[-1479.5,131.6,650.5]),
    'pyramid_wayfinding':([-31,-446.38,308.5],[-27.5,-444.8,308.5]),
    'observation_rear':([35.5,-365.38,-205.5],[30.5,-389,-240]),
    'un_motor_pool':(None,None),
    'un_helipads':([6410,93,-6960],[6412.5,75,-6995.5]),
    'un_readiness_overview':([6490,115,-6870],[6540,83,-6907]),
}
shots=[]
for row in original:
    if row['name'] not in changes:continue
    a,b=changes[row['name']]
    if a is not None:row.update(eye=a,target=b)
    row.update(warmupTicks=700 if not shots else 420,renderDistance=8 if row['name'].startswith(('station','un_')) else 6)
    shots.append(row)
shutil.copy2(OUT/'client_tour_receipt.json',OUT/'client_tour_initial_receipt.json')
p.write_text(json.dumps(shots,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'retake_cameras.json').write_text(json.dumps(shots,ensure_ascii=False,indent=2),encoding='utf8')
print('Prepared',len(shots),'measured camera retakes')
