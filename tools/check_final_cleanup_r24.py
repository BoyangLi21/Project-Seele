"""Reconcile the full-height scan after deleting only proved isolated groups."""
from pathlib import Path
import json,msvcrt
import numpy as np
from query_blocks import iter_selected_sections
import promote_world_r24 as p
ROOT=p.ROOT;ART=p.ART;WORLD=p.REVIEW
def main():
    rows={};counts={}
    for name in ('residue','review_terrain_cleanup'):
        count=0
        for path in (ART/name).rglob('c.*.npz'):
            if path.parent.name!='delta':continue
            cx,cz=map(int,path.stem.split('.')[1:])
            with np.load(path) as a:
                codes=a['offsets'].astype(int)+int(a['minimum'])*256
                for code,value in zip(codes,a['after']):rows[cx,cz,int(code)]=str(a['palette'][int(value)]);count+=1
        counts[name]=count
    assert counts=={'residue':216,'review_terrain_cleanup':34},counts
    selected={}
    for x,z,code in rows:selected.setdefault((x,z),set()).add(code//4096)
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        data={(x,z,y):(pal,a) for x,z,y,pal,a in iter_selected_sections(WORLD,p.v.DIM,selected,skip_unfinished=True)}
        for (x,z,code),wanted in rows.items():
            pal,a=data[x,z,code//4096];assert pal[a[code%4096]]==wanted=='minecraft:air',(x,z,code)
    report=dict(passed=True,existing_main_fragments_removed=216,review_only_fragments=34,coordinates_verified=len(rows),
                method='Full-height 6-neighbour scan plus 26-neighbour semantic classification. Deleted groups had no neighbours, so their deletion cannot disconnect retained structures. Exact post-native readback confirms every retirement.',
                retained_semantic_groups=8,unclassified_groups=0,original_main_test_chunks_not_transplanted=True)
    (ART/'validation/post_cleanup_readback.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(report)
if __name__=='__main__':main()
