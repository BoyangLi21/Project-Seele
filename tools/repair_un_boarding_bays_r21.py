"""Separate occupied boarding walkways from the measured capsule sweep."""
import argparse,json
from pathlib import Path
import regional_voxels as v
ROOT=v.ROOT;OUT=ROOT/'artifacts/un_models_r21/boarding'
def main(main_world=False):
 world=ROOT/'run/saves'/('SEELE_TV_WORLD_PREVIEW_20260906' if main_world else 'SEELE_R21_REVIEW');v.WORLD=world;v.OUT=OUT/('main' if main_world else 'review');p=v.Painter();cases=json.loads((world/'quality_walk_cases.json').read_text());changed=[]
 if main_world:assert json.loads((OUT/'native_acceptance.json').read_text())['passed']
 for cx in (6442,6282):
  def b(box,state):p.fill(*box,state,'r21/guarded_un_capsule_cradle','owned')
  # A U-shaped steel catwalk surrounds the suspended capsule. Its side and
  # rear guards have continuous floors, and the gap is never a public path.
  b((cx-16,126,-6226,cx+16,126,-6214),'projectseele:nerv_floor_panel')
  # Five clear blocks accommodate the rotating pressure-collar envelope,
  # including its corners during the final screw-in movement.
  b((cx-2,126,-6223,cx+2,126,-6214),'minecraft:air')
  b((cx-16,127,-6221,cx+16,128,-6221),'minecraft:air')
  for x in (cx-2,cx+2):b((x,127,-6222,x,127,-6214),'minecraft:air')
  b((cx-3,127,-6223,cx+3,127,-6223),'minecraft:air')
  for x in (cx-16,cx+16):
   for z in (-6224,-6215):b((x,77,z,x,125,z),'projectseele:nerv_machine_edge')
  rails={(x,127,-6226) for x in range(cx-16,cx+17)}|{(x,127,-6214) for x in range(cx-16,cx+17) if abs(x-cx)>=3}
  rails|={(x,127,z) for x in (cx-3,cx+3) for z in range(-6223,-6213)}|{(x,127,-6224) for x in range(cx-3,cx+4)}
  for x,y,z in sorted(rails):
   props={name:str((x+dx,y,z+dz) in rails).lower() for name,dx,dz in [('east',1,0),('north',0,-1),('south',0,1),('west',-1,0)]};props['waterlogged']='false'
   p.put(x,y,z,'minecraft:iron_bars['+','.join(k+'='+props[k] for k in sorted(props))+']','r21/cradle_safety_guard','owned')
  path=[[cx+4.5,127,-6217.5],[cx+4.5,127,-6224.5],[cx-3.5,127,-6224.5],[cx-3.5,127,-6217.5]]
  for suffix,points in [('',path),('/return',list(reversed(path)))]:
   case={'id':'r21/un_boarding/'+str(cx)+suffix,'path':points};changed.append(case)
 # The annex apron originally copied a pedestrian curb and lamp posts
 # straight across the full-size airframe exit. Keep them beside the lane.
 for z in (-6133,-6109):
  p.fill(6266,77,z,6298,83,z,'minecraft:air','r21/un01_clear_departure_lane','owned')
  p.fill(6266,76,z,6298,76,z,'minecraft:light_gray_concrete','r21/un01_flush_lane_marking','owned')
 for case in cases:
  if 'path' not in case:continue
  modified=False
  for point in case['path']:
   if point[1]==127 and abs(point[2]+6217.5)<.1 and any(abs(point[0]-(cx+.5))<.1 for cx in (6442,6282)):
    point[0]+=4;modified=True
  if modified:changed.append(case)
 old_ids={c['id'] for c in cases}
 cases.extend(c for c in changed if c['id'] not in old_ids)
 p.meta.update(reason='Native capsule insertion was blocked by centre floor and unsupported rear rails',boarding_positions=[[6446.5,127,-6217.5],[6286.5,127,-6217.5]],walk_nodes=changed)
 p.apply('guarded_capsule_cradles')
 (world/'quality_walk_cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8')
 if not main_world:
  OUT.mkdir(parents=True,exist_ok=True);prior=json.loads((OUT/'retest_cases.json').read_text()) if (OUT/'retest_cases.json').exists() else []
  affected={c['id'] for c in prior+changed}
  (OUT/'retest_cases.json').write_text(json.dumps([c for c in cases if c['id'] in affected],indent=2));(OUT/'full_catalogue.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8')
 print('Guarded UN boarding bays repaired; affected/new walk cases',len(changed))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--main',action='store_true');main(ap.parse_args().main)
