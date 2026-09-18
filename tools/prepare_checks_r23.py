"""Compose current route coverage, preserving all routes not explicitly rebuilt."""
from pathlib import Path
import argparse,json,math
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23/validation'
def main(install=False):
 OUT.mkdir(parents=True,exist_ok=True);old=json.loads((WORLD/'quality_walk_cases.json').read_text(encoding='utf8'));retired=[];cases=[]
 for c in old:
  # R22 replaced all elevated station interiors and the one named gateway
  # detour. Streets, buildings, rooms and all other destinations stay tested.
  if c['id'].startswith(('r20/station/','r20/interchange/','nerv/arrival_platform_corridor','arrival/platform','nerv/arrival_spine')):retired.append(dict(id=c['id'],reason='Superseded by the installed R23 station geometry, the R22 Hakone/Bay direct interchanges or direct gateway corridor'))
  else:cases.append(c)
 for file in ['artifacts/facility_r23/stations/contract.json','artifacts/access_r22/map/access_contract.json','artifacts/facility_r23/readiness/contract.json']:
  cases+=json.loads((ROOT/file).read_text(encoding='utf8'))['walk_nodes']
 source=json.loads((ROOT/'artifacts/access_r22/transit/civil/station_contract.json').read_text(encoding='utf8'));cases+=source['transfer_links']
 stations=json.loads((ROOT/'artifacts/facility_r23/stations/contract.json').read_text(encoding='utf8'))['stations']
 for r in stations:
  for i,b in enumerate(r['belts']):
   if not b['rise']:continue
   x,y,z=b['start'];n=b['rise'];axis=b['axis']
   for lane in (.625,1.375):
    start=[x-1.5,y+1,z+lane] if axis=='x' else [x+lane,y+1,z-1.5]
    end=[x+n+4.5,y+n+1,z+lane] if axis=='x' else [x+lane,y+n+1,z+n+4.5]
    key=f'r23/native_escalator/{r["station"]}/{r["line"]}/{i}/{lane}'
    cases.extend([dict(id=key,start=start,end=end),dict(id=key+'/return',start=end,end=start)])
  # Waiting rooms have a real entry on the boarding aisle, then a clear
  # forecourt in front of the seats. Never route through bench collisions.
  sr=next(q for q in source['stations'] if q['station']==r['station'] and q['line']==r['line']);x,y,z=r['center']
  for side in (-1,1):
   at=lambda u,w:[x+u+.5,y+1,z+w+.5] if sr['horizontal'] else [x+w+.5,y+1,z+u+.5]
   displaced={('新箱根中央','R1'):1,('新箱根中央','S1'):-1,('湾岸防卫区','R1'):-1,('湾岸防卫区','S1'):1};offset=20 if displaced.get((r['station'],r['line']))==side else 0
   pts=[at(offset,side*8),at(offset,side*14),at(offset+8,side*14)];key=f'r23/waiting_room/{r["station"]}/{r["line"]}/{side}'
   cases.extend([dict(id=key,path=pts),dict(id=key+'/return',path=pts[::-1])])
 # The public command entrance is reached from the real lift landing and
 # the three-riser stair. Operators behind the glazed island are not a goal.
 cases+= [dict(id='r23/command_public_entrance',path=[[12.5,-409,258.5],[25.5,-409,258.5],[28.5,-409,258.5],[28.5,-409,261.5],[28.5,-406,265.5],[28.5,-406,269.5]])]
 cases+= [dict(id='r23/command_real_door_roundtrip',commandButton=[27,-405,270],path=[[28.5,-406,269.5],[28.5,-406,275.5],[28.5,-406,269.5]])]
 keys=[q['id'] for q in cases];assert len(keys)==len(set(keys)),[k for k in set(keys) if keys.count(k)>1]
 (OUT/'full_walk_cases.json').write_text(json.dumps(cases,ensure_ascii=False),encoding='utf8');(OUT/'retired_routes.json').write_text(json.dumps(retired,ensure_ascii=False,indent=2),encoding='utf8')
 if install:
  (WORLD/'r23_walk_cases.json').write_text(json.dumps(cases,ensure_ascii=False),encoding='utf8')
  states=set(json.loads((WORLD/'regional_states.json').read_text()));inventory=ROOT/'artifacts/facility_r23/global/inventory/world_objects.json'
  if inventory.exists():states.update(json.loads(inventory.read_text(encoding='utf8'))['block_states'])
  (WORLD/'regional_states.json').write_text(json.dumps(sorted(states)))
 print('Current routes',len(cases),'explicitly retired',len(retired))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--install',action='store_true');main(ap.parse_args().install)
