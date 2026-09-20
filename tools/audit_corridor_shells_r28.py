"""Inspect full registered hall sections, including roofs and open drop edges."""
from pathlib import Path
from collections import defaultdict
import json,math,numpy as np
from scipy.spatial import cKDTree
import regional_voxels as v
from query_blocks import read_box,AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_FIELD_R28_REVIEW';OUT=ROOT/'artifacts/facility_r28/enclosures'

def main():
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter()
    sections=json.loads((WORLD/'spatial_contract_r21.json').read_text())['sections']
    # The R25 retired lower blind hall must never be reconstructed.
    sections=[s for s in sections if s['id']!='factory_lower']
    routes=json.loads((WORLD/'quality_walk_cases.json').read_text());walk=[]
    for r in routes:
        pts=r.get('path') or [r.get('start'),r.get('end')]
        if any(q is None for q in pts):continue
        for aa,bb in zip(pts,pts[1:]):
            a,b=np.asarray(aa),np.asarray(bb)
            if min(a[1],b[1])>-300:continue
            walk.extend(np.linspace(a,b,max(2,math.ceil(np.linalg.norm(a-b)*2))))
    tree=cKDTree(np.asarray(walk));groups=defaultdict(list)
    for s in sections:groups[s['floor'],s['height']].append(s)
    fixes={};audits=[]
    shafts=[(9,-566,-409,253,7),(66,-461,-364,302,5),(93,-443,-367,-52,6),(-29,-395,-367,-278,5),(30,-389,-340,318,5),(130,-449,-390,269,6)]
    def mechanical(x,y,z):return any(abs(x-X)<=r and abs(z-Z)<=r and low-2<=y<=high+6 for X,low,high,Z,r in shafts)
    for (f,h),specs in groups.items():
        rects=[b for s in specs for b in s['rects']];cells={(x,z) for a,b,c,d in rects for x in range(a,b+1) for z in range(c,d+1)}
        lo=(min(x for x,z in cells)-2,f-2,min(z for x,z in cells)-2);hi=(max(x for x,z in cells)+2,f+h+1,max(z for x,z in cells)+2);a=read_box(WORLD,v.DIM,lo,hi)
        ports=[b for s in specs for b in s.get('ports',[])];roof=wall=0
        for x,z in sorted(cells):
            if mechanical(x,f+1,z) or a.get((x,f,z),'minecraft:air') in AIR:continue
            if any(b[0]-1<=x<=b[3]+1 and b[2]-1<=z<=b[5]+1 for b in ports):continue
            # Stairs/escalators deliberately penetrate upper floors.
            column=[a.get((x,y,z),'minecraft:air') for y in range(f+1,f+h)]
            if any('stairs' in s or 'escalator' in s or 'elevator' in s for s in column):continue
            edge=any((x+dx,z+dz) not in cells for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)))
            if edge:
                gaps=[(dx,dz) for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)) if (x+dx,z+dz) not in cells
                      and all(a.get((x+dx*k,f,z+dz*k),'minecraft:air') in AIR for k in (1,2))]
                if not gaps or tree.query([x+.5,f+1,z+.5])[0]<1.05:continue
                for y in range(f+1,f+h):
                    q=(x,y,z);old=a.get(q,'minecraft:air')
                    if old in AIR:fixes[q]=(old,'projectseele:nerv_wall_panel' if y==f+1 else 'projectseele:clear_glass');wall+=1
            else:
                q=(x,f+h,z)
                # Only an open ceiling above an otherwise free corridor is a
                # gap. Do not fill a stair head or a higher-level route.
                if a.get(q) in AIR and all(s in AIR or s=='minecraft:light' for s in column) and tree.query([x+.5,f+h,z+.5])[0]>2:
                    fixes[q]=(a[q],'projectseele:nerv_structural_panel');roof+=1
        audits.append(dict(sections=[s['id'] for s in specs],floor=f,full_floor_columns=len(cells),missing_roof_cells=roof,open_drop_wall_cells=wall))
    for q,(old,new) in fixes.items():p.match((*q,*q),old,new,'r28/documented_corridor_shell_repair')
    p.meta.update(audits=audits,repair_cells=len(fixes),retired_halls_excluded=['factory_lower'],scope='Complete registered personnel hall perimeter and roof columns, with current walk, stair and native lift exclusions')
    p.apply('documented_corridor_enclosures')
    (OUT/'contract.json').write_text(json.dumps(p.meta,indent=2));print('Full corridor-shell audit',audits,flush=True)

if __name__=='__main__':main()
