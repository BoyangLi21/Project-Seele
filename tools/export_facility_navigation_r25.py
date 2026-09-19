"""Refresh only the documented public circulation with the R25 physical links."""
from pathlib import Path
import json,numpy as np,shutil
import plan_pyramid_navigation_r22 as nav
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R25_REVIEW';OUT=ROOT/'artifacts/facility_r25/navigation'
def intersects(a,b,lo,hi):
 t0,t1=0.,1.
 for axis in range(3):
  d=b[axis]-a[axis]
  if abs(d)<1e-9:
   if a[axis]<lo[axis] or a[axis]>hi[axis]:return False
  else:
   u,v=sorted(((lo[axis]-a[axis])/d,(hi[axis]-a[axis])/d));t0=max(t0,u);t1=min(t1,v)
   if t0>t1:return False
 return True
def main():
 OUT.mkdir(parents=True,exist_ok=True);nav.WORLD=WORLD;nav.LO=(-80,-574,-300);nav.HI=(190,-334,545)
 old=json.loads((WORLD/'quality_walk_cases.json').read_text(encoding='utf8'));retired=[];cases=[]
 for case in old:
  points=case.get('path',[case.get('start'),case.get('end')])
  if any(q is None for q in points):continue
  if any(intersects(a,b,(102,-443,-290),(114,-437,-50)) for a,b in zip(points,points[1:])):retired.append(case);continue
  cases.append(case)
 new=json.loads((ROOT/'artifacts/facility_r25/validation/affected_walk_cases.json').read_text(encoding='utf8'))
 cross=ROOT/'artifacts/facility_r25/crossing_finish/contract.json'
 overrides=json.loads(cross.read_text(encoding='utf8'))['route_overrides'] if cross.exists() else []
 cases=list({q['id']:q for q in cases+new+overrides}.values())
 paths=[];used=[]
 for case in cases:
  path=case.get('path',[case.get('start'),case.get('end')]);points=np.asarray(path)
  if np.all(points[:,1]<-300) and np.all(points>=np.array(nav.LO)-1) and np.all(points<=np.array(nav.HI)+1):paths.append(path);used.append(case['id'])
 nav.PUBLIC_DOMAINS=[((-76,-474,235),(157,-356,474)),((-34,-369,-288),(115,-360,-215))]
 nav.PUBLIC_PATHS=paths;nav.RAIL_CURVES=json.loads((WORLD/'native_transit_r25.json').read_text())['curves']
 nav.LIFT_GROUPS=[dict(id='command_dogma',points=[(12,y,258) for y in (-566,-448,-423,-419,-409)]),
                  dict(id='hangar_observation',points=[(93,-442,-47),(93,-394,-57),(93,-370,-57)]),
                  dict(id='east_command',points=[(73,y,260) for y in (-448,-434,-420,-406,-392)]),
                  dict(id='west_observation',points=[(-29,y,-284) for y in (-394,-367)])]
 nav.GOALS=[('command','指挥室入口',(28,-406,269)),('hangars','机库登机通道',(90,-394,-255)),('station','总部火车站',(30,-466,451)),
            ('pyramid_station','金字塔接驳站',(30,-466,520)),('launch_station','发射区车站',(150,-442,-28)),('observation','机库观景走廊',(90,-367,-221)),('dogma','终极教条前厅',(30,-566,280))]
 nav.DEBUG_PATHS={q['id']:q['path'] for q in new if q['id'].startswith(('r25/west_command','r25/east_command','r25/lift','r25/observation','r25/station_actual','r25/station_west'))}
 (OUT/'scope.json').write_text(json.dumps(dict(public_path_cases=used,public_domains=nav.PUBLIC_DOMAINS,goals=nav.GOALS,lift_groups=nav.LIFT_GROUPS,retired_route_ids=[q['id'] for q in retired]),ensure_ascii=False,indent=2),encoding='utf8')
 (OUT/'retired_routes.json').write_text(json.dumps(retired,ensure_ascii=False,indent=2),encoding='utf8')
 (OUT/'full_walk_cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8')
 nav.main(False,OUT,OUT/'nerv_routes_r24.json.gz')
 shutil.copy2(OUT/'nerv_routes_r24.json.gz',WORLD/'nerv_routes_r24.json.gz')
 print('R25 navigation refreshed; retired obsolete cases',len(retired),'new cases',len(new),flush=True)
if __name__=='__main__':main()
