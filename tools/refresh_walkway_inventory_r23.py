"""Refresh every edited section in the previous complete escalator census."""
from pathlib import Path
import json,shutil
import numpy as np
from query_blocks import iter_selected_sections
from promote_world_r23 import masks,REVIEW
import audit_moving_walks_r23 as audit

ROOT=Path(__file__).resolve().parents[1]
def main():
    snapshot=audit.OUT/'native_cells.json';base=audit.OUT/'native_cells_before_final.json'
    if not base.exists():shutil.copy2(snapshot,base)
    data=json.loads(base.read_text());assert data['scan']['complete']
    selected={q:set(map(int,ids//4096)) for q,ids in masks().items()}
    def unedited(row):return row[1]//16 not in selected.get((row[0]//16,row[2]//16),set())
    steps=[r for r in data['steps'] if unedited(r)];sides=[r for r in data['sides'] if unedited(r)]
    sections=0
    for cx,cz,sy,pal,indices in iter_selected_sections(REVIEW,'projectseele:geofront',selected,skip_unfinished=True):
        sections+=1
        match=np.array([s.startswith(('mtr:escalator_step','mtr:escalator_side')) for s in pal])[indices]
        for i in np.flatnonzero(match):
            state=pal[indices[i]];q=[cx*16+(int(i)&15),sy*16+(int(i)>>8),cz*16+((int(i)>>4)&15),state]
            (steps if state.startswith('mtr:escalator_step') else sides).append(q)
    data.update(steps=steps,sides=sides);data['scan']['changed_sections_refreshed']=sections
    snapshot.write_text(json.dumps(data,separators=(',',':')))
    audit.main(False)
    report=json.loads((audit.OUT/'audit.json').read_text(encoding='utf8'))
    assert not report['orphan_halves'] and report['flat_handrails_removed']==0
    shutil.copy2(audit.OUT/'audit.json',ROOT/'artifacts/facility_r23/validation/final_walkway_audit.json')
if __name__=='__main__':main()
