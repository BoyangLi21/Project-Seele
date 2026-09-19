"""Connect headquarters, actual hangar access, two station links and Dogma on measured floors."""
from pathlib import Path
import json,numpy as np
import plan_pyramid_navigation_r22 as nav
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R24_TV_REVIEW';OUT=ROOT/'artifacts/facility_r24/facility_navigation'
def main():
    OUT.mkdir(parents=True,exist_ok=True);nav.WORLD=WORLD;nav.LO=(-80,-574,-300);nav.HI=(190,-334,545)
    cases=json.loads((WORLD/'quality_walk_cases.json').read_text(encoding='utf8'));paths=[];used=[]
    for case in cases:
        path=case.get('path',[case.get('start'),case.get('end')])
        if not path or any(p is None for p in path):continue
        points=np.asarray(path)
        if np.all(points[:,1]<-300) and np.all(points>=np.array(nav.LO)-1) and np.all(points<=np.array(nav.HI)+1):paths.append(path);used.append(case['id'])
    nav.PUBLIC_DOMAINS=[((-76,-474,235),(157,-356,474))]
    nav.PUBLIC_PATHS=paths;nav.RAIL_CURVES=json.loads((WORLD/'native_transit_r23.json').read_text())['curves']
    nav.DEBUG_PATHS={r['id']:r['path'] for r in cases if r['id'] in ('r20/factory/high_observation','r20/factory/upper_lift_to_observation')}
    nav.LIFT_GROUPS=[dict(id='command_dogma',points=[(12,y,258) for y in (-566,-448,-423,-419,-409)]),dict(id='hangar_observation',points=[(93,-442,-47),(93,-394,-57),(93,-370,-57)])]
    nav.GOALS=[('command','指挥室入口',(28,-406,269)),('hangars','机库登机通道',(90,-394,-255)),('station','总部火车站',(30,-466,451)),
               ('pyramid_station','金字塔接驳站',(30,-466,520)),('launch_station','发射区车站',(150,-442,-28)),('observation','机库观景走廊',(90,-367,-221)),('dogma','终极教条前厅',(30,-566,280))]
    (OUT/'scope.json').write_text(json.dumps(dict(public_path_cases=used,public_domains=nav.PUBLIC_DOMAINS,goals=nav.GOALS,lift_groups=nav.LIFT_GROUPS),ensure_ascii=False,indent=2),encoding='utf8')
    nav.main(False,OUT,OUT/'nerv_routes_r24.json.gz')
if __name__=='__main__':main()
