"""Stage affected HQ/Dogma routes without discarding the full circulation catalog."""
import argparse,json,msvcrt,shutil
from regional_voxels import ROOT,WORLD
OUT=ROOT/'artifacts/world_refinement_r09';DIR=OUT/'audit_catalog'
load=lambda p:json.loads(p.read_text(encoding='utf8'))
def main(restore=False):
    DIR.mkdir(exist_ok=True);pending=DIR/'pending.json'
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        if restore:
            if not pending.exists():raise RuntimeError('No staged R09 audit')
            for name in ('quality_walk_cases.json','regional_states.json'):shutil.copy2(DIR/name,WORLD/name)
            pending.unlink();print('Restored complete R09 catalog');return
        if pending.exists():raise RuntimeError('Restore previous staged audit first')
        for name in ('quality_walk_cases.json','regional_states.json'):
            if not (DIR/('baseline_'+name)).exists():shutil.copy2(WORLD/name,DIR/('baseline_'+name))
        baseline=load(DIR/'baseline_quality_walk_cases.json')
        retired=[r for r in baseline if r['id'].startswith('r08/structure/east_platform_maintenance')]
        path=[[12.5,-566,280.5],[91.5,-566,280.5]]
        added=[dict(id='r09/dogma/restored_front_gallery',path=path),dict(id='r09/dogma/restored_front_gallery/return',path=path[::-1])]
        catalog=[r for r in baseline if r not in retired]+added
        assert len({r['id'] for r in catalog})==len(catalog)
        native=[]
        for r in catalog:
            points=r.get('path',[r.get('start'),r.get('end')]);points=[p for p in points if p]
            if (r['id'].startswith(('r04/terminal_dogma/','r09/dogma/')) or
                any(-110<=p[0]<=205 and -470<=p[1]<=-285 and 190<=p[2]<=551 for p in points)):
                native.append(r)
        states=set(load(DIR/'baseline_regional_states.json'))
        for p in OUT.glob('*/states.json'):states.update(load(p))
        for p,value in [(DIR/'quality_walk_cases.json',catalog),(DIR/'regional_states.json',sorted(states)),(WORLD/'quality_walk_cases.json',native),(OUT/'retired_platform_routes.json',retired)]:
            p.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
        shutil.copy2(DIR/'regional_states.json',WORLD/'regional_states.json')
        pending.write_text(json.dumps(dict(catalog=len(catalog),native=len(native),retired=len(retired),added=len(added)),indent=2),encoding='utf8')
        print(pending.read_text(encoding='utf8'))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--restore',action='store_true');main(ap.parse_args().restore)
