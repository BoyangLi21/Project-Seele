"""Check the installed cells and native S1 delta against their verified sources."""
from pathlib import Path
import json,msvcrt,zipfile,hashlib,numpy as np
import promote_world_r29 as p
from query_blocks import iter_selected_sections,read_box
from verify_main_r20 import entities,windows

def main():
    installed=json.loads((p.OUT/'installed.json').read_text());assert installed['installed']
    baseline=json.loads((p.ART/'baseline.json').read_text());cold=Path(baseline['backup'])/'world'
    with (p.MAIN/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);mask,_=p.masks();selected={q:set(map(int,ids//4096)) for q,ids in mask.items()}
        def measure(world):return {(x,z,y):(pal,a) for x,z,y,pal,a in iter_selected_sections(world,p.v.DIM,selected,skip_unfinished=True)}
        target,source=measure(p.MAIN),measure(p.REVIEW);count=0
        for (x,z),ids in mask.items():
            for y in selected[x,z]:
                offsets=ids[ids//4096==y]%4096;ap,a=target[x,z,y];bp,b=source[x,z,y]
                assert np.array_equal(np.asarray(ap)[a[offsets]],np.asarray(bp)[b[offsets]]),(x,y,z);count+=len(offsets)
        a,b=p.tagged(p.MAIN,mask),p.tagged(p.REVIEW,mask);assert a.keys()==b.keys() and all(p.same(a[q],b[q]) for q in a)
        old,current=entities(cold),entities(p.MAIN);assert old.keys()==current.keys() and all(p.same(old[k],current[k]) for k in old),'Actor state changed'
        assert windows(p.MAIN)==windows(cold)==2344
        journal=json.loads((Path(installed['backup'])/'journal.json').read_text());assert p.protected_hashes()==journal['protected']
        for name,sha in baseline['original_user_files'].items():assert p.digest(p.ROOT/name)==sha,name
        pack=p.ROOT/'run/resourcepacks/eva_real_model'
        def hashes(root):return {q.relative_to(root).as_posix():p.digest(q) for q in root.rglob('*') if q.is_file()}
        # R25's cold backup contains the world only. The sealed R27 client
        # archive is the actual preceding delivery of all private model files.
        archive=p.ROOT/'artifacts/server-ready-r28/Project_SEELE_R28_Client.zip'
        prefix='resourcepacks/eva_real_model/'
        with zipfile.ZipFile(archive) as source:
            oldpack={name[len(prefix):]:hashlib.sha256(source.read(name)).hexdigest() for name in source.namelist() if name.startswith(prefix) and not name.endswith('/')}
        assert oldpack and hashes(pack)==oldpack,'Private EVA assets changed unexpectedly'
        for x in (-12,30,72):
            assert read_box(p.MAIN,p.v.DIM,(x,81,-75),(x,81,-75))[x,81,-75]=='minecraft:air'
            assert read_box(p.MAIN,p.v.DIM,(x,81,3),(x,81,3))[x,81,3]=='projectseele:umbilical_pylon'
        routes=json.loads((p.MAIN/'quality_walk_cases.json').read_text());assert len(routes)==installed['route_catalog']
        report=dict(passed=True,masked_cells=count,block_entities=len(a),original_actor_count=len(old),all_original_actor_state_preserved=True,windows=2344,unrelated_transport_players_campaign_and_lifts_preserved=True,all_mtr_files_unchanged=True,private_model_assets_preserved=True,registered_routes=len(routes))
    (p.OUT/'verified_install.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
