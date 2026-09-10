"""Stage targeted native paths and main-world staff/door/landscape photographs, then restore the complete catalog."""
import json,shutil,msvcrt,math,argparse,time
from regional_voxels import ROOT,WORLD
OUT=ROOT/'artifacts/staff_world_r15';CAT=OUT/'main_review';CAT.mkdir(parents=True,exist_ok=True)
def load(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['stage','restore']);args=ap.parse_args()
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  if args.mode=='restore':
   planned=load(CAT/'staged.json');fresh=load(WORLD/'quality_native_walk_results.json');assert (WORLD/'quality_native_walk_results.json').stat().st_mtime>planned['epoch'];assert {r['id'] for r in fresh}==set(planned['cases']);assert all(r['status']=='pass' for r in fresh)
   previous=load(ROOT/'artifacts/world_refinement_r14/native_world_complete.json');merged={r['id']:r for r in previous};merged.update({r['id']:r for r in fresh});save(OUT/'native_world_r15.json',fresh);save(OUT/'native_world_complete.json',list(merged.values()))
   for name in ['quality_walk_cases.json','regional_states.json','r07_photo_views.json']:shutil.copy2(CAT/name,WORLD/name)
   assert len(load(WORLD/'quality_walk_cases.json'))==8550;save(CAT/'restored.json',dict(fresh_cases=len(fresh),full_catalog=8550));print('Restored complete8550; fresh checks',len(fresh));return
  if (CAT/'staged.json').exists():raise RuntimeError('An R15 stage already exists; inspect before restaging')
  for name in ['quality_walk_cases.json','regional_states.json','r07_photo_views.json','quality_native_walk_results.json']:shutil.copy2(WORLD/name,CAT/name)
  catalog=load(CAT/'quality_walk_cases.json');assert len(catalog)==8550
  cases=[r for r in catalog if r['id'].startswith(('r04/pyramid/','r04/terminal_dogma/','r14/','hangar/','station/U2_hangar/')) or r['id']=='r03/continuous/pyramid_to_cage_wait']
  states=set(load(CAT/'regional_states.json'))
  for p in (OUT/'map').glob('*/states.json'):states.update(load(p))
  save(WORLD/'quality_walk_cases.json',cases);save(WORLD/'regional_states.json',sorted(states));views=[]
  for name,pos,target,seconds in [
   ('r15_command_staff',[27.5,-409,279.5],[29,-407.7,283],75),
   ('r15_staff_lounge',[-39,-447,307],[-59,-446,303],65),
   ('r15_roof_door',[28.5,-388,309],[28.5,-387,317.5],65),
   ('r15_hangar_staff',[54,-393,-129],[50,-393,-120],75),
   ('r15_un_personnel',[6395,78,-6658],[6400,76,-6650],100),
   ('r15_pyramid_far',[-155,-371.62,492],[28,-410,318],100),
   ('r15_lakeshore',[-240,-444,360],[-560,-468,230],100),
   ('r15_city_far',[-493,158.38,746],[0,90,325],100)]:
   dx,dy,dz=target[0]-pos[0],target[1]-pos[1]-1.62,target[2]-pos[2];views.append(dict(file=name+'.png',position=pos,yaw=math.degrees(math.atan2(-dx,dz)),pitch=math.degrees(math.atan2(-dy,math.hypot(dx,dz))),warmupTicks=seconds*20))
  save(WORLD/'r07_photo_views.json',views);save(CAT/'staged.json',dict(epoch=time.time(),cases=[r['id'] for r in cases],photos=views));print('Staged main native checks',len(cases),'photos',len(views))
if __name__=='__main__':main()
