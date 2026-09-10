"""Keep the entire route catalog and add native roof/lift threshold cases and photographs."""
import json,math,shutil,msvcrt
from regional_voxels import ROOT,WORLD
OUT=ROOT/'artifacts/world_refinement_r14';CAT=OUT/'audit_catalog';CAT.mkdir(exist_ok=True)
def main():
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  for name in ['quality_walk_cases.json','regional_states.json','r07_photo_views.json']:
   if (WORLD/name).exists() and not(CAT/('before_'+name)).exists():shutil.copy2(WORLD/name,CAT/('before_'+name))
  catalog=json.loads((CAT/'before_quality_walk_cases.json').read_text(encoding='utf8'));assert len(catalog)==8538
  roof=json.loads((OUT/'roof/places.json').read_text(encoding='utf8'))
  for node in roof['walk_nodes']:
   for reverse in [False,True]:
    catalog.append(dict(id=node['id']+('/return' if reverse else ''),start=node['end'] if reverse else node['start'],end=node['start'] if reverse else node['end']))
  assert len({r['id'] for r in catalog})==len(catalog)
  states=set(json.loads((CAT/'before_regional_states.json').read_text(encoding='utf8')))
  for p in OUT.glob('*/states.json'):states.update(json.loads(p.read_text(encoding='utf8')))
  for name,data in [('quality_walk_cases.json',catalog),('regional_states.json',sorted(states))]:
   (CAT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');shutil.copy2(CAT/name,WORLD/name)
  views=[]
  for name,pos,target in [('roof_reception',[28,-387,348],[28,-386,315]),('roof_piano',[18,-388,349],[11,-387,355]),('roof_gallery',[55,-387,340],[76,-391,340]),('staff_lounge',[-39,-447,307],[-59,-446,303]),('hangar_finish',[99,-399,-79],[68,-403,-120]),('lakeshore',[-240,-444,360],[-560,-468,230]),('urban_edge',[-824,128,199],[-711,91,299])]:
   dx,dy,dz=target[0]-pos[0],target[1]-pos[1]-1.62,target[2]-pos[2]
   views.append(dict(file='r14_'+name+'.png',position=pos,yaw=math.degrees(math.atan2(-dx,dz)),pitch=math.degrees(math.atan2(-dy,math.hypot(dx,dz))),warmupTicks=240))
  (WORLD/'r07_photo_views.json').write_text(json.dumps(views,indent=2));(OUT/'photo_views.json').write_text(json.dumps(views,indent=2));print('Full native route catalog',len(catalog),'photos',len(views))
if __name__=='__main__':main()
