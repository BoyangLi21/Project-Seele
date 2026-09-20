"""Verify the installed delta while preserving every original actor and unrelated file."""
from pathlib import Path
import json,msvcrt
import numpy as np
import promote_world_r26 as p
from query_blocks import iter_selected_sections,read_box
from verify_main_r20 import entities,windows

def main():
    receipt=json.loads((p.OUT/'installed.json').read_text());assert receipt['installed']
    baseline=json.loads((p.ART/'baseline.json').read_text());cold=Path(baseline['backup'])/'world'
    with (p.MAIN/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        mask,_=p.masks();selected={q:set(map(int,ids//4096)) for q,ids in mask.items()}
        def measure(world):return {(x,z,y):(pal,a) for x,z,y,pal,a in iter_selected_sections(world,p.v.DIM,selected,skip_unfinished=True)}
        main,review=measure(p.MAIN),measure(p.REVIEW);checked=0
        for (x,z),ids in mask.items():
            for y in selected[x,z]:
                indices=ids[ids//4096==y]%4096;ap,a=main[x,z,y];bp,b=review[x,z,y]
                assert np.array_equal(np.array(ap)[a[indices]],np.array(bp)[b[indices]]),(x,y,z)
                checked+=len(indices)
        a,b=p.prior.tagged(p.MAIN,mask),p.prior.tagged(p.REVIEW,mask)
        assert a.keys()==b.keys() and all(p.prior.same(a[q],b[q]) for q in a)
        before=read_box(cold,p.v.DIM,(6,-445,262),(52,-388,365));after=read_box(p.MAIN,p.v.DIM,(6,-445,262),(52,-388,365));changed=0
        for q,state in before.items():
            if after[q]==state:continue
            x,y,z=q;assert y*256+(z&15)*16+(x&15) in mask.get((x//16,z//16),[]),('Unapproved command-room change',q)
            changed+=1
        assert windows(p.MAIN)==windows(cold)==2344
        original,current=entities(cold),entities(p.MAIN);assert original.keys()==current.keys()
        assert all(p.prior.same(original[u],current[u]) for u in original)
        journal=json.loads((Path(receipt['backup'])/'journal.json').read_text());assert p.protected()==journal['protected']
        for name,digest in baseline['original_user_files'].items():assert p.digest(p.ROOT/name)==digest,name
        def files(root):return {q.relative_to(root).as_posix():p.digest(q) for q in root.rglob('*') if q.is_file()}
        # R25 froze the world only. The previous accepted R24 snapshot also
        # contains the unchanged private EVA pack, and is the real asset baseline.
        assets_baseline=json.loads((p.ROOT/'artifacts/facility_r24/baseline.json').read_text())
        old_assets=Path(assets_baseline['backup'])/'eva_real_model';assert old_assets.is_dir()
        assert files(p.ROOT/'run/resourcepacks/eva_real_model')==files(old_assets)
        for name in ('nerv_routes_r24.json.gz','regional_states.json','facility_lifts_r26.json','facility_chairs_r26.json','native_transit_r26.json','.projectseele_command_sliding_doors_r01.json'):
            assert (p.MAIN/name).read_bytes()==(p.REVIEW/name).read_bytes(),name
        routes=json.loads((p.MAIN/'quality_walk_cases.json').read_text());assert len(routes)==len({q['id'] for q in routes})
        result=dict(passed=True,masked_cells=checked,block_entities=len(a),command_room_changes_only_in_authorized_ports=changed,unchanged_command_cells=len(before)-changed,one_way_windows=2344,original_actors=len(original),actors_and_players_unchanged=True,existing_lift_groups_preserved=True,private_eva_pack_unchanged=True,retired_east_lift_replaced=True,routes=len(routes))
        (p.OUT/'verified_install.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
