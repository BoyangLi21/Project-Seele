"""Verify installed exact cells/tags and preserved original world state."""
from pathlib import Path
import hashlib,json,msvcrt
import numpy as np
import promote_world_r24 as promote
from query_blocks import iter_selected_sections
from verify_main_r20 import entities,windows,compare_box
ROOT=promote.ROOT;ART=promote.ART;MAIN=promote.MAIN;REVIEW=promote.REVIEW

def main():
    installed=json.loads((ART/'promotion/installed.json').read_text());assert installed['installed']
    baseline=json.loads((ART/'baseline.json').read_text(encoding='utf8'));cold=Path(baseline['backup'])/'world'
    with (MAIN/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        mask,_=promote.masks();selected={q:set(map(int,ids//4096)) for q,ids in mask.items()}
        def measure(w):return {(x,z,y):(p,a) for x,z,y,p,a in iter_selected_sections(w,promote.v.DIM,selected,skip_unfinished=True)}
        target,source=measure(MAIN),measure(REVIEW);checked=0
        for (x,z),ids in mask.items():
            for y in selected[x,z]:
                indices=ids[ids//4096==y]%4096;ap,a=target[x,z,y];bp,b=source[x,z,y]
                assert np.array_equal(np.array(ap)[a[indices]],np.array(bp)[b[indices]]),(x,y,z)
                checked+=len(indices)
        a,b=promote.tagged(MAIN,mask),promote.tagged(REVIEW,mask)
        assert a.keys()==b.keys() and all(promote.same(a[q],b[q]) for q in a),'Installed block-entity text/equipment mismatch'
        protected=compare_box(cold,MAIN,(6,-445,262),(52,-388,365))
        assert windows(MAIN)==windows(cold)==2344
        original,current=entities(cold),entities(MAIN)
        assert original.keys()==current.keys(),'Original actor identities changed'
        assert all(promote.same(original[u],current[u]) for u in original),'Actor state was transplanted from review'
        journal=json.loads((Path(installed['backup'])/'journal.json').read_text());assert promote.protected_hashes()==journal['protected']
        for name,sha in baseline['original_user_files'].items():assert promote.digest(ROOT/name)==sha,name
        pack=ROOT/'run/resourcepacks/eva_real_model';oldpack=Path(baseline['backup'])/'eva_real_model'
        def files(p):return {q.relative_to(p).as_posix():promote.digest(q) for q in p.rglob('*') if q.is_file()}
        assert files(pack)==files(oldpack),'Existing private models/skins changed during R24'
        assert (MAIN/'nerv_routes_r24.json.gz').read_bytes()==(REVIEW/'nerv_routes_r24.json.gz').read_bytes()
        camera=json.loads((ART/'camera/installed.json').read_text());assert camera['installed']
        assert all(promote.digest(Path(name))==camera['sha256'] for name in camera['destinations'])
        walks=json.loads((MAIN/'quality_walk_cases.json').read_text(encoding='utf8'));assert len(walks)==len({r['id'] for r in walks})==installed['route_catalog']
        report=dict(passed=True,main=str(MAIN),masked_coordinates_verified=checked,block_entities_verified=len(a),protected_command_cells=protected,one_way_windows=2344,
                    original_entity_count=len(original),original_entity_state_unchanged=True,player_transport_elevator_state_hashes_unchanged=True,private_resource_pack_unchanged=True,private_camera_sha256=camera['sha256'],protected_user_files=len(baseline['original_user_files']),routes=len(walks))
        (ART/'promotion/verified_install.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
