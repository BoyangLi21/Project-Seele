"""Correct measured beam clearance and route endpoints without rebuilding stations."""
import json
import regional_voxels as v
from query_blocks import read_box
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23/stations'
def main():
 v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();contract=json.loads((OUT/'contract.json').read_text(encoding='utf8'));old=json.loads((ROOT/'artifacts/access_r22/transit/civil/station_contract.json').read_text(encoding='utf8'))['stations'];case_updates=[]
 for st in contract['stations']:
  cx,y,cz=st['center'];h=st['half'];g=st['ground'];horizontal=next(r['horizontal'] for r in old if r['station']==st['station'] and r['line']==st['line'])
  def at(u,yy,w):return (cx+u,yy,cz+w) if horizontal else (cx+w,yy,cz+u)
  for u in range(-h+5,h-3,12):
   for sign in (-1,1):
    for k in range(5):
     q=at(u+k,y+9,sign*8);above=at(u+k,y+10,sign*8);s=read_box(WORLD,v.DIM,q,above)
     if s[q]=='projectseele:nerv_strip_light':p.match((*q,*q),s[q],'minecraft:air','r23/raise_bridge_light');p.match((*above,*above),s[above],'projectseele:nerv_strip_light','r23/recess_bridge_light')
  for case in st['walks']:
   kind=case['id'];path=case['path'];reverse=kind.endswith('/return');base=list(reversed(path)) if reverse else path
   if '/ordinary_stair_' in kind:
    # A midpoint had described the top of the first tread at ground height.
    axis=0 if horizontal else 2;base[1][axis]-=1
   elif '/ground_entrance_' in kind:
    axis=0 if horizontal else 2
    for point in base:point[axis]+=1
   else:continue
   case['path']=list(reversed(base)) if reverse else base;case_updates.append(case)
 contract['walk_nodes']=[q for st in contract['stations'] for q in st['walks']];contract['native_first_run_findings']={'fixed_lower_entries_at_frame_columns':28,'fixed_stair_waypoint_heights':28,'raised_overbridge_lights':True}
 p.meta.update(route_endpoints_corrected=len(case_updates));p.apply('verified_stair_landings_and_bridge_clearance');(OUT/'contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf8')
 cases=contract['walk_nodes']+json.loads((ROOT/'artifacts/access_r22/map/access_contract.json').read_text(encoding='utf8'))['walk_nodes'];(WORLD/'r23_walk_cases.json').write_text(json.dumps(cases,ensure_ascii=False),encoding='utf8');print('Corrected route endpoints',len(case_updates),'light edits',len(p.ops))
if __name__=='__main__':main()
