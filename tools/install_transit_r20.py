"""Install the verified native graph, preserving other dimensions and backups."""
from pathlib import Path
import argparse,json,shutil,msvcrt,datetime
from stage_native_transit_repair import hashes
from apply_s20_approved_semantic_repairs import atomic_replace
import regional_voxels as vox

ROOT=vox.ROOT;OUT=ROOT/'artifacts/world_rebuild_r20/transit'
def main(world,stage):
    world=Path(world).resolve();stage=Path(stage).resolve();selection=json.loads((OUT/'native_selection.json').read_text(encoding='utf8'))
    assert Path(selection['stage']).resolve()==stage,'Selected simulator stage and proof must agree'
    native=json.loads((OUT/selection['commission']).read_text(encoding='utf8'))
    assert native['passed'];assert stage.is_relative_to(ROOT/'.Codex')
    if world.name!='SEELE_R20_REVIEW':
        proof=json.loads((OUT/'physical_acceptance.json').read_text());assert proof['passed'],'Main world requires physical acceptance'
    plan=json.loads((OUT/'native_snapshot.json').read_text(encoding='utf8'))
    for k in ('stations','routes','platforms'):assert {r['id'] for r in plan[k]}<={r['id'] for r in native[k]}
    source=stage/'projectseele/geofront';target=world/'mtr/projectseele/geofront';assert source.is_dir() and target.is_dir()
    after=hashes(source);name='native_install_'+world.name+'_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=OUT/name
    with (world/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);before=hashes(target);shutil.copytree(target,backup/'before')
        try:
            for relative in sorted(set(before)|set(after)):
                destination=(target/relative).resolve();assert destination.is_relative_to(target)
                if relative in after:
                    if before.get(relative)!=after[relative]:destination.parent.mkdir(parents=True,exist_ok=True);atomic_replace(destination,(source/relative).read_bytes())
                elif destination.is_file():destination.unlink()
            assert hashes(target)==after
        except Exception:
            for relative in sorted(set(before)|set(after)):
                destination=target/relative
                if relative in before:atomic_replace(destination,(backup/'before'/relative).read_bytes())
                elif destination.exists():destination.unlink()
            raise
    (backup/'receipt.json').write_text(json.dumps(dict(world=str(world),source=str(source),native_graph_verified=True,public_ids_preserved=True,before=before,after=after),indent=2))
    print('R20 native graph installed in',world.name)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--world',default=str(vox.WORLD));a.add_argument('--stage',required=True);q=a.parse_args();main(q.world,q.stage)
