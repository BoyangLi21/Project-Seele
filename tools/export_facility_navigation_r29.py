"""Eight-floor routing and an explicit same-floor room-to-lift audit."""
from pathlib import Path
import json,shutil
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components,dijkstra
from scipy.spatial import cKDTree
import plan_pyramid_navigation_r22 as nav
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r29';WORLD=ROOT/'run/saves/SEELE_FIELD_R29_REVIEW';OUT=ART/'navigation'

def main():
    OUT.mkdir(parents=True,exist_ok=True);nav.WORLD=WORLD;nav.LO=(-80,-574,-300);nav.HI=(330,-334,625)
    old=json.loads((WORLD/'quality_walk_cases.json').read_text());retired=[];cases=[]
    for q in old:
        if q['id'].startswith(('r25/lift/east/','r25/east_lift_lower','r25/east_lower_through')):
            retired.append(q);continue
        if q.get('commandButton')==[27,-405,270]:q['commandButton']=[27,-405,271]
        cases.append(q)
    extra=[]
    for name in ('upper_gallery','un_berths'):
        extra+=json.loads((ART/name/'contract.json').read_text())['walk_nodes']
    overrides=ART/'navigation/route_overrides.json'
    if overrides.exists():extra+=json.loads(overrides.read_text())
    cases=list({q['id']:q for q in cases+extra}.values());paths=[]
    for q in cases:
        path=q.get('path',[q.get('start'),q.get('end')]);pts=np.asarray(path)
        if np.all(pts[:,1]<-300) and np.all(pts>=np.array(nav.LO)-1) and np.all(pts<=np.array(nav.HI)+1):paths.append(path)
    nav.PUBLIC_DOMAINS=[((-76,-474,235),(157,-356,474)),((-34,-369,-288),(115,-360,-198)),((188,-469,392),(212,-453,545))];nav.PUBLIC_PATHS=paths
    native=WORLD/'native_transit_r26.json';nav.RAIL_CURVES=json.loads(native.read_text())['curves']
    nav.LIFT_GROUPS=[dict(id='command_dogma',points=[(12,y,258) for y in (-566,-448,-423,-419,-409)]),dict(id='hangar_observation',points=[(93,-442,-47),(93,-394,-57),(93,-370,-57)]),dict(id='east_command',points=[(66,y,309) for y in (-461,-448,-434,-420,-406,-392,-378,-364)]),dict(id='west_observation',points=[(-29,y,-284) for y in (-394,-367)])]
    nav.GOALS=[('command','指挥室入口',(28,-406,269)),('hangars','机库登机通道',(90,-394,-255)),('station','总部火车站',(30,-466,451)),('pyramid_station','金字塔接驳站',(30,-466,520)),('launch_station','发射区车站',(150,-442,-28)),('observation','机库观景走廊',(90,-367,-221)),('dogma','终极教条前厅',(30,-566,280))]
    nav.LIFT_BOARD_COST=4.;nav.LIFT_VERTICAL_COST=.12;nav.LIFT_DIRECT=True;nav.STAIR_COST=4.
    nav.main(False,OUT,OUT/'nerv_routes_r24.json.gz');shutil.copy2(OUT/'nerv_routes_r24.json.gz',WORLD/'nerv_routes_r24.json.gz')
    (OUT/'full_walk_cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8');(OUT/'retired_routes.json').write_text(json.dumps(retired,indent=2))
    with np.load(OUT/'walkable_graph.npz') as d:
        coords=d['coords'];graph=csr_matrix((d['weights'],d['indices'],d['indptr']),shape=(len(coords),len(coords)))
    rooms=json.loads((WORLD/'spatial_contract_r23.json').read_text())['room_entries'];report=[];routes=[]
    for y in (-461,-448,-434,-420,-406,-392,-378,-364):
        ids=np.flatnonzero(coords[:,1]==y);tree=cKDTree(coords[ids]);sub=graph[ids][:,ids];_,labels=connected_components(sub,directed=False)
        distance,i=tree.query((66,y,309));assert distance<2,(y,distance);root=labels[i];dist,pred=dijkstra(sub,directed=False,indices=i,return_predecessors=True)
        for room in [q for q in rooms if q['floor']+1==y]:
            entry=np.asarray(room['entry']);de,j=tree.query(entry);connected=de<=3 and labels[j]==root
            x,X,z,Z=room['bounds'];inside=(coords[ids,0]>=x)&(coords[ids,0]<=X)&(coords[ids,2]>=z)&(coords[ids,2]<=Z)
            room_nodes=int(inside.sum());unreachable=coords[ids[inside & (labels!=root)]].tolist()
            row=dict(id=room['id'],floor=y,entry=room['entry'],entry_connected=bool(connected),walkable_cells=room_nodes,unreachable=unreachable);report.append(row)
            if connected:
                chain=[int(j)]
                while chain[-1]!=i:
                    nxt=int(pred[chain[-1]]);assert nxt>=0;chain.append(nxt)
                points=(coords[ids[chain]]+np.array([.5,0,.5])).tolist();compact=[points[0]]
                for k in range(1,len(points)-1):
                    if not np.array_equal(np.asarray(points[k])-points[k-1],np.asarray(points[k+1])-points[k]):compact.append(points[k])
                compact.append(points[-1]);routes.append(dict(id='r28/room_to_floor_lift/'+room['id'],path=compact))
    (OUT/'same_floor_rooms.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');(OUT/'room_lift_walk_cases.json').write_text(json.dumps(routes,ensure_ascii=False,indent=2),encoding='utf8')
    signs=ART/'signage/contract.json'
    all_cases=cases+routes+(json.loads(signs.read_text())['walk_nodes'] if signs.exists() else [])
    (OUT/'full_walk_cases.json').write_text(json.dumps(list({q['id']:q for q in all_cases}.values()),ensure_ascii=False,indent=2),encoding='utf8')
    print('Room entries to same-floor lift',sum(q['entry_connected'] for q in report),'/',len(report),'disconnected floor cells',sum(len(q['unreachable']) for q in report),flush=True)
    print('Disconnected rooms',[(q['id'],q['entry']) for q in report if not q['entry_connected']],flush=True)
if __name__=='__main__':main()
