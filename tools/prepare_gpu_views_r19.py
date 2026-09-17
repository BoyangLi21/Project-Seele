"""Identical real-world camera points for exact-renderer A/B verification."""
from pathlib import Path
import json,math

ROOT=Path(__file__).resolve().parents[1]
def main():
    shots=[dict(name='C1_rail_and_city',eye=[-615,106,660],target=[-602,87,682],warmupTicks=400)]
    source=json.loads((ROOT/'artifacts/world_refinement_r09/final_photo_views.json').read_text())
    for r in source:
        if r['file'] not in ('r09_final_pyramid_logo.png','r09_final_inside_view.png','r09_final_external_glass.png','r09_final_dogma_lilith.png'):continue
        x,y,z=r['position'];eye=[x,y+1.62,z];yaw,pitch=map(math.radians,(r['yaw'],r['pitch']));direction=[-math.sin(yaw)*math.cos(pitch),-math.sin(pitch),math.cos(yaw)*math.cos(pitch)]
        shots.append(dict(name=r['file'].removesuffix('.png').replace('r09_final_',''),eye=eye,target=[a+b*60 for a,b in zip(eye,direction)],warmupTicks=max(400,r['warmupTicks'])))
    shots.append(dict(name='UN_base_overview',eye=[6620,140,-6260],target=[6480,80,-6140],warmupTicks=400))
    (ROOT/'run/projectseele-local-maps/r19_worldtour.json').write_text(json.dumps(shots,indent=2))
    (ROOT/'artifacts/world_repair_r19/gpu_review_views.json').write_text(json.dumps(shots,indent=2));print('Exact-renderer views',len(shots))

if __name__=='__main__':main()
