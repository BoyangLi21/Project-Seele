"""Preserve the full semantic route catalogue and explicitly replace retired works."""
import copy,json,math
from pathlib import Path
from collections import Counter
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_rebuild_r20'
MAIN=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'

def main():
    base=json.loads((MAIN/'quality_walk_cases.json').read_text(encoding='utf8'))
    new=json.loads((OUT/'civil_cases_latest.json').read_text(encoding='utf8'))
    roads=np.load(OUT/'road_actual/road_contract_final.npz');mask=roads['mask'];height=roads['height2'];ox,oz=map(int,roads['origin'])
    result=[];changes=[]
    retired={
        'station/':'r20/station/', 'r03/platform_length/':'r20/station/',
        'r06/station/':'r20/station/', 'r07/station/':'r20/station/',
        'interchange/':'r20/interchange/', 'kirisato_transfer/':'r20/interchange/hakone',
        'r19/upper_moving_walk':'r20/factory/middle_service',
        'r03/continuous/hangar_to_observation_lift':'r20/factory/high_observation',
        'r03/continuous/launch_control_':'r20/factory/high_observation',
        'r06/airport/':'r20/airport/bay/',
    }
    ground_prefix=('tokyo_','kirisato/','new_hakone/','extension_road/','final_crossing/','station_road/','r19/C1_street_approach/','r19/current_rail_crossing/','r07/connection/','r03/entry/')
    for original in base:
        row=copy.deepcopy(original);key=row['id'];reason=None;replacement=None
        for prefix,target in retired.items():
            if key.startswith(prefix):reason='Rebuilt station, interchange or explicitly retired observation facility';replacement=target;break
        if key.startswith('airport/') and '/管制塔/' not in key:
            reason='Retired Y72 underpasses; terminal, new elevated station and native gate now connected at apron Y81';replacement='r20/airport/'
        if reason:
            changes.append(dict(id=key,action='replaced',reason=reason,replacement_prefix=replacement));continue
        points=row.get('path',[row.get('start'),row.get('end')])
        if key.startswith('r03/continuous/cage_gallery_'):
            backward=key.endswith('/return') or key.endswith('/reverse')
            seq=list(reversed(points)) if backward else points
            tail=[[x,y,z-144] for x,y,z in seq[7:]]
            seq=[[93.5,-394,-46.5],[101.5,-394,-46.5],[101.5,-394,-60.5],[99.5,-394,-60.5],[99.5,-394,-264.5],[88.5,-394,-264.5],[88.5,-394,-261.5]]+tail
            row['path']=list(reversed(seq)) if backward else seq
            changes.append(dict(id=key,action='rerouted',reason='Original compact lift to relocated cage gallery and boarding dock'))
        elif key.startswith(('r03/continuous/pyramid_to_', 'hq/hangar_walkway','arrival/platform','nerv/arrival_platform_corridor','r03/portal_width/')):
            backward=key.endswith('/return') or key.endswith('/reverse');seq=list(reversed(points)) if backward else points
            if key.startswith('r03/continuous/pyramid_to_'):
                seq=seq[:13]+[[123.5,-442,247.5],[123.5,-442,241.5],[118.5,-442,241.5],[118.5,-442,-17.5],[150.5,-442,-17.5],[150.5,-442,-28.5]]
                if 'cage_wait' in key:seq += [[167.5,-442,-28.5],[175.5,-436,-28.5],[176.5,-436,-28.5],[176.5,-436,-51.5],[175.5,-436,-51.5],[167.5,-442,-51.5],[118.5,-442,-51.5],[118.5,-442,-46.5],[93.5,-442,-46.5]]
            elif key.startswith('hq/hangar_walkway'):seq=[seq[0],[123.5,-442,247.5],[123.5,-442,241.5],[118.5,-442,241.5],seq[-1]]
            elif key.startswith(('arrival/platform','nerv/arrival_platform_corridor')):seq=[seq[0],[-308.5,-466,768.5],[-330.5,-466,768.5],[-330.5,-466,777.5],[-308.5,-466,777.5]]
            else:
                z=-46.7+(.8 if '-49.5' in key else 1.6 if '-48.7' in key else 0);seq=[[114.5,-442,z],[93.5,-442,z]]
            row.pop('start',None);row.pop('end',None);row['path']=list(reversed(seq)) if backward else seq
            changes.append(dict(id=key,action='rerouted',reason='Explicit connection through the new station or service-gallery entrance'))
        elif key.startswith(ground_prefix):
            changed=0
            for p in points:
                x,z=math.floor(p[0])-ox,math.floor(p[2])-oz
                if 0<=z<mask.shape[0] and 0<=x<mask.shape[1] and mask[z,x] and p[1]>0:
                    target=float(height[z,x])/2
                    if p[1]!=target:p[1]=target;changed+=1
            if changed:changes.append(dict(id=key,action='ground_datum',points=changed,reason='Measured, continuous road contract after grade separation'))
        result.append(row)
    # Both the original retained route names and all new connections survive.
    ids={r['id'] for r in result}
    for row in new:
        assert row['id'] not in ids;result.append(row);ids.add(row['id'])
    assert len(ids)==len(result)
    (OUT/'quality_walk_cases_r20.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'walk_catalog_migration.json').write_text(json.dumps(dict(original=len(base),retained=sum(c['action']!='replaced' for c in changes)+len(base)-len(changes),added=len(new),total=len(result),changes=changes),ensure_ascii=False,indent=2),encoding='utf8')
    print('Complete catalogue',len(base),'->',len(result),Counter(c['action'] for c in changes))

if __name__=='__main__':main()
