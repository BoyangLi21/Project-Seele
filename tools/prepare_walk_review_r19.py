"""Keep the full route catalogue and add the explicitly repaired R19 connections."""
import argparse,json,shutil
import regional_voxels as vox
from pathlib import Path

def main(quick=False,affected=False):
    dest=vox.ROOT/'run/saves/SEELE_R19_NATIVE_REVIEW';source=vox.WORLD
    cases=json.loads((source/'quality_walk_cases.json').read_text(encoding='utf8'));original_count=len(cases);added=[]
    if affected:
        def overlaps(case):
            path=case.get('path',[case.get('start'),case.get('end')]);lo=(84,-453,-145);hi=(155,-383,278)
            return any(all(max(a[i],b[i])>=lo[i] and min(a[i],b[i])<=hi[i] for i in range(3)) for a,b in zip(path,path[1:]))
        cases=[c for c in cases if overlaps(c)]
    def route(name,path):
        added.append(dict(id='r19/'+name,path=path));added.append(dict(id='r19/'+name+'/return',path=list(reversed(path))))
    for x in (110.5,112.5,113.5):route('transfer_stair/'+str(x),[[x,-448,255.5],[x,-442,248.5],[118.5,-442,248.5]])
    route('hangar_south_platform',[[118.5,-442,-16.5],[118.5,-442,-21.5],[150.5,-442,-21.5],[150.5,-442,-27.5]])
    route('hangar_north_platform',[[100.5,-442,-46.5],[113.5,-442,-46.5]])
    route('upper_moving_walk',[[101.5,-394,-112.5],[101.5,-394,-50.5]])
    for folder in ('C1_street_grade','rail_street_crossings_v2'):
        for index,r in enumerate(json.loads((vox.ROOT/'artifacts/world_repair_r19/roads'/folder/'places.json').read_text())['walk_nodes']):
            route(r['id'].removeprefix('r19/')+'/'+str(index),r['path'])
    states=set(json.loads((source/'regional_states.json').read_text()))
    for f in (vox.ROOT/'artifacts/world_repair_r19').glob('*/*/states.json'):states.update(json.loads(f.read_text()))
    all_cases=added if quick else added+cases
    assert len({c['id'] for c in all_cases})==len(all_cases)
    (dest/'quality_walk_cases.json').write_text(json.dumps(all_cases,ensure_ascii=False),encoding='utf8')
    (dest/'regional_states.json').write_text(json.dumps(sorted(states)),encoding='utf8')
    out=vox.ROOT/'artifacts/world_repair_r19';(out/'walk_catalogue.json').write_text(json.dumps({'original_routes':original_count,'new_routes':len(added),'test_routes':len(all_cases),'affected_only':affected,'world':str(dest)},indent=2))
    print('R19 native routes',len(all_cases),'new',len(added))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--quick',action='store_true');ap.add_argument('--affected',action='store_true');args=ap.parse_args();main(args.quick,args.affected)
