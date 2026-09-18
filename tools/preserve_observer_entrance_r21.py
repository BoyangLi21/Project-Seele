"""Keep the user's named X90/Z-221 landing when routing outside the hoist."""
import json,argparse
import regional_voxels as v
ROOT=v.ROOT;OUT=ROOT/'artifacts/world_repair_r21'
def main(main_world=False):
 v.WORLD=ROOT/'run/saves'/('SEELE_TV_WORLD_PREVIEW_20260906' if main_world else 'SEELE_R21_REVIEW')
 if main_world:assert (OUT/'main_install.json').exists()
 v.OUT=OUT/('main_observer_landing' if main_world else 'hoist_separation/retained_entrance');p=v.Painter()
 def b(box,state):p.fill(*box,state,'r21/preserve_named_observer_entrance','owned')
 b((85,-369,-226,94,-361,-216),'projectseele:nerv_structural_panel')
 b((86,-368,-225,94,-368,-217),'projectseele:nerv_floor_panel')
 b((86,-367,-225,94,-362,-217),'minecraft:air')
 for z in (-226,-216):b((86,-366,z,93,-363,z),'projectseele:clear_glass')
 b((87,-361,-223,90,-361,-220),'projectseele:nerv_strip_light')
 p.meta.update(entrance=[90.5,-367,-221.5],connection=[102.5,-367,-221.5],mechanical_minimum_x_clearance=6.9)
 p.apply('retained_user_observation_entrance')
 for path in [v.WORLD/'quality_walk_cases.json',OUT/'full_walk_catalogue.json']:
  cases=json.loads(path.read_text())
  for r in cases:
   if 'r21/upper_three_cages' in r['id']:
    r['path']=[[90.5,-367,-221.5],[102.5,-367,-221.5],[102.5,-367,-205.5],[-29.5,-367,-205.5]]
    if r['id'].endswith('/return'):r['path'].reverse()
  path.write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8')
 if not main_world:
  (OUT/'hoist_separation/retest_cases.json').write_text(json.dumps([r for r in cases if 'r21/upper_three_cages' in r['id']],indent=2))
 for path in [v.WORLD/'spatial_contract_r21.json']+([] if main_world else [OUT/'facility_contract.json',OUT/'spatial_contract_r21.json']):
  data=json.loads(path.read_text())
  for r in data['sections']:
   if r['id']=='commander_gallery' and [85,94,-226,-216] not in r['rects']:r['rects'].append([85,94,-226,-216])
  path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--main',action='store_true');main(ap.parse_args().main)
