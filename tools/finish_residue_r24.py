"""Retire detached remnants inside the two documented R23 rail rebuilding areas.

Native train envelopes, named walking routes, occupied plots and retained
entity-supported structures are checked separately from voxel connectivity.
"""
from pathlib import Path
from collections import Counter
import argparse,gzip,json
import numpy as np
from scipy.spatial import cKDTree
import regional_voxels as v
import repair_scan_residue_r20 as extract
from query_blocks import read_box,AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R24_TV_REVIEW';ART=ROOT/'artifacts/facility_r24';OUT=ART/'residue';SCAN=ART/'global/components'
ENVELOPES=[(-1450,32,636,-389,139,724),(-2360,32,610,-1535,160,782)]

def main(apply=False):
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;extract.REVIEW=WORLD;p=v.Painter()
    raw=json.loads((SCAN/'report.json').read_text())['candidates'];groups=json.loads((SCAN/'contact_classification.json').read_text())['groups']
    native=json.loads((WORLD/'native_transit_r23.json').read_text());rail=np.array([q for r in native['curves'] if r['mode']=='TRAIN' for q in r['points']]);rail_tree=cKDTree(rail)
    plots=json.loads((ROOT/'artifacts/world_quality_r02/surface_layout.json').read_text())['kept_plots']
    baseline=Path(json.loads((ART/'baseline.json').read_text())['backup'])/'world';removed={};retained=[];decisions=[];held=[];review_terrain=[]
    boards=json.loads((ROOT/'artifacts/facility_r23/navigation/junctions.json').read_text(encoding='utf8'))['boards']
    def inside(q,b):return all(b[i]<=q[i]<=b[i+3] for i in range(3))
    for group in groups:
        kind=group['kind'];lo=group['lo'];names={s.split('[')[0] for s in group['states']}
        if kind in ('edge_connected_to_world','fluid_contact'):continue
        reason=None
        if group['cells']==920 and lo==[19,-443,313]:reason='Protected original command display and lighting'
        elif group['cells'] in (782,24) and 1400<=lo[0]<=1435 and lo[2] in (362,502,370,510):reason='Port crane deck/hoist carried by the retained R08 steel-member entities'
        elif names=={'minecraft:structure_void'}:reason='Invisible, non-colliding construction receipts'
        elif names=={'projectseele:station_departure_board'}:
            assert any(b['position']==lo and b['suspension'] for b in boards)
            reason='Documented suspended model frame reaches the existing ceiling rods'
        if reason:retained.append(dict(lo=lo,hi=group['hi'],cells=group['cells'],reason=reason));continue
        cells={}
        for index in group['components']:cells.update(extract.cells(raw[index]))
        if kind=='isolated_soil':
            # These five formations are in terrain generated solely when a
            # native attack fixture loaded a remote empty review area. Do not
            # transplant those new test chunks into the user's original save.
            originals={q:read_box(baseline,v.DIM,q,q).get(q) for q in cells}
            assert all(s is None for s in originals.values()),('Unexpected original-world soil residue',group)
            review_terrain.append(dict(lo=lo,hi=group['hi'],cells=cells));continue
        if kind!='isolated_structure' or not names<={'minecraft:light_gray_concrete','minecraft:iron_bars','minecraft:polished_blackstone_slab'} or not all(any(inside(q,b) for b in ENVELOPES) for q in cells):held.append(group);continue
        for q,state in cells.items():
            assert read_box(baseline,v.DIM,q,q).get(q)==state,('Not an existing Main remnant',q)
            for plot in plots:
                x,X,z,Z=plot['bounds'];f=plot['floor'];roof=f+plot.get('storeys',1)*5+6
                assert not (x<=q[0]<=X and z<=q[2]<=Z and f<=q[1]<=roof),('Retained building overlap',q,plot['id'])
            close=rail[rail_tree.query_ball_point(np.array(q)+.5,15)]
            if len(close):
                conflict=(abs(close[:,0]-q[0]-.5)<5)&(abs(close[:,2]-q[2]-.5)<5)&(close[:,1]-4<q[1]+1)&(close[:,1]+8>q[1])
                assert not conflict.any(),('Current native train/track-bed envelope',q,close[conflict].tolist())
        removed.update(cells);decisions.append(dict(lo=lo,hi=group['hi'],cells=len(cells),reason='26-neighbour detached remnants in the documented bridge raising/bypass work; outside current railway, occupied plots and human route envelopes'))
    assert not held,held
    points=np.asarray(list(removed),float);tree=cKDTree(points);violations=[]
    routes={r['id']:r for r in json.loads((WORLD/'quality_walk_cases.json').read_text(encoding='utf8'))}
    routes.update({r['id']:r for r in json.loads((WORLD/'r24_walk_cases.json').read_text(encoding='utf8'))})
    for route in routes.values():
        path=route.get('path') or [route['start'],route['end']]
        for aa,bb in zip(path,path[1:]):
            a,b=np.array(aa),np.array(bb);delta=b-a;ids=tree.query_ball_point((a+b)*.5,np.linalg.norm(delta)*.5+4)
            if not ids:continue
            cells=points[ids];lower=cells+[-.4,-1.9,-.4];upper=cells+[1.4,2.1,1.4];enter=np.zeros(len(ids));leave=np.ones(len(ids));possible=np.ones(len(ids),bool)
            for axis in range(3):
                if abs(delta[axis])<1e-10:possible&=(lower[:,axis]<=a[axis])&(a[axis]<=upper[:,axis])
                else:
                    first=(lower[:,axis]-a[axis])/delta[axis];last=(upper[:,axis]-a[axis])/delta[axis]
                    enter=np.maximum(enter,np.minimum(first,last));leave=np.minimum(leave,np.maximum(first,last))
            if (possible&(enter<=leave)).any():violations.append(dict(route=route['id'],cells=cells[possible&(enter<=leave)].tolist()))
    assert not violations,violations
    for q,state in removed.items():p.match((*q,*q),state,'minecraft:air','r24/verified_detached_rail_remnant')
    p.meta.update(removed_cells=len(removed),removed_groups=decisions,retained_structures=retained,unclassified=held,protected_walk_routes=len(routes),rail_envelope_conflicts=0,plot_conflicts=0,
                  review_only_new_terrain_cells=sum(len(r['cells']) for r in review_terrain),full_chunks=51500,full_sections=3193000)
    p.save_plan('verified_rail_fragment_retirement')
    if apply:p.apply('verified_rail_fragment_retirement')
    (OUT/'classification.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
    # Keep review-only generated terrain cleanup out of the Main promotion mask.
    v.OUT=ART/'review_terrain_cleanup';v.OUT.mkdir(parents=True,exist_ok=True);temporary=v.Painter()
    for record in review_terrain:
        for q,state in record['cells'].items():temporary.match((*q,*q),state,'minecraft:air','r24/review_only_natural_fragment')
    temporary.meta.update(not_in_original_world=True,do_not_promote_generated_test_chunks=True)
    temporary.save_plan('isolated_review_terrain')
    if apply:temporary.apply('isolated_review_terrain')
    print('Existing-world fragments',len(removed),'retained groups',len(retained),'review-only new terrain fragments',sum(len(r['cells']) for r in review_terrain),'unknown',len(held))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
