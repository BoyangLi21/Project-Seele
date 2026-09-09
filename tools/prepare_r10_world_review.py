"""Stage native circulation and appearance checks while keeping the complete route catalog recoverable."""
import argparse,json,shutil,msvcrt,math
from pathlib import Path
from regional_voxels import ROOT,WORLD
OUT=ROOT/'artifacts/first_battle_world_r10/world_art';CAT=OUT/'audit_catalog';CAT.mkdir(exist_ok=True)
load=lambda p:json.loads(p.read_text(encoding='utf8'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
def prepare(mode):
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  if mode=='restore':
   for name in ['quality_walk_cases.json','regional_states.json']:shutil.copy2(CAT/name,WORLD/name)
   (CAT/'pending.json').unlink();return
  if mode=='photos':
   views=[]
   for name,pos,target in [
    ('briefing',[99,-431,292],[84,-432,274]),
    ('computer_room',[-14,-431,287],[-44,-432,276]),
    ('medical_room',[-9,-431,399],[-37,-432,386]),
    ('interception_avenue',[422,111,-340],[322,89,-447]),
    ('geofront_lakeshore',[-240,-444,360],[-560,-468,230]),
    ('tokyo_green_edge',[-824,128,199],[-711,91,299]),
    ('hakone_green_edge',[-985,109,635],[-1120,94,680])]:
    dx,dy,dz=target[0]-pos[0],target[1]-pos[1]-1.62,target[2]-pos[2]
    views.append(dict(file='r10_'+name+'.png',position=pos,yaw=math.degrees(math.atan2(-dx,dz)),pitch=math.degrees(math.atan2(-dy,math.hypot(dx,dz))),warmupTicks=400))
   save(WORLD/'r07_photo_views.json',views);save(OUT/'native_photo_views.json',views);return
  if (CAT/'pending.json').exists():raise RuntimeError('Restore the currently staged R10 audit first')
  for name in ['quality_walk_cases.json','regional_states.json']:
   if not (CAT/('baseline_'+name)).exists():shutil.copy2(WORLD/name,CAT/('baseline_'+name))
  catalog=load(CAT/'baseline_quality_walk_cases.json');states=set(load(CAT/'baseline_regional_states.json'))
  added=[]
  routes=[('west_pavement',[[317.5,81,-505.5],[317.5,81,-286.5]]),('east_pavement',[[395.5,81,-505.5],[395.5,81,-286.5]]),('city_join_north',[[282.5,81,-449.5],[356.5,81,-449.5]]),('city_join_south',[[282.5,81,-299.5],[356.5,81,-299.5]]),('dispatch',[[110.5,-434,285.5],[86.5,-434,285.5],[86.5,-434,275.5]])]
  for name,path in routes:
   for rev in [False,True]:added.append(dict(id='r10/'+name+('/return' if rev else ''),path=path[::-1] if rev else path))
  catalog+=added;assert len({r['id'] for r in catalog})==len(catalog)
  cases=[r for r in catalog if r['id'].startswith(('r04/pyramid/','r10/'))]
  for path in OUT.glob('*/states.json'):states.update(load(path))
  save(CAT/'quality_walk_cases.json',catalog);save(CAT/'regional_states.json',sorted(states));save(WORLD/'quality_walk_cases.json',cases);save(WORLD/'regional_states.json',sorted(states));save(CAT/'pending.json',dict(full_catalog=len(catalog),native=len(cases),added=len(added)))
  print('Staged',len(cases),'native routes;',len(catalog),'catalog entries')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['audit','restore','photos']);prepare(ap.parse_args().mode)
