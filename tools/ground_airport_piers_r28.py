"""Continue the authored station piers down to their measured seabed, never into routes."""
from pathlib import Path
import json
import regional_voxels as v
from query_blocks import read_box
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_FIELD_R28_REVIEW';OUT=ROOT/'artifacts/facility_r28/airport_piers'
def main():
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();rows=[]
    for x in range(494,669,22):
        for z in (104,152):
            for X in (x,x+1):
                cells=read_box(WORLD,v.DIM,(X,0,z),(X,70,z));assert cells[X,70,z]=='projectseele:nerv_structural_panel'
                top=69;bottom=top
                while bottom>=0 and cells[X,bottom,z].split('[')[0] in ('minecraft:air','minecraft:water','minecraft:seagrass','minecraft:tall_seagrass'):bottom-=1
                assert bottom>=0
                for y in range(bottom+1,top+1):p.match((X,y,z,X,y,z),cells[X,y,z],'projectseele:nerv_structural_panel','r28/authored_station_pier')
                rows.append(dict(column=[X,z],foundation_y=bottom,changed=max(0,top-bottom)))
    p.meta.update(columns=rows,top=69,reason='Native oblique view showed authored piers ending above the seabed; continue only those existing columns.')
    p.apply('continuous_airport_pier_foundations');(OUT/'contract.json').write_text(json.dumps(p.meta,indent=2))
    # All public station routes begin at Y73 or above; the new material ends at
    # Y69. No passenger or aircraft clearance volume is altered.
    checks=[]
    for row in rows:
        x,z=row['column'];a=read_box(WORLD,v.DIM,(x,row['foundation_y']+1,z),(x,70,z))
        assert all(s=='projectseele:nerv_structural_panel' for s in a.values());checks.append(row)
    (OUT/'verified.json').write_text(json.dumps(dict(passed=True,columns=checks,max_changed_y=69),indent=2))
    print('Grounded',len(rows),'pier columns;',sum(q['changed'] for q in rows),'cells',flush=True)
if __name__=='__main__':main()
