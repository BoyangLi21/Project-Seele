"""Measured coast and seabed samples, using the existing saved-block reader."""
from pathlib import Path
import json
import numpy as np
from query_blocks import iter_selected_sections,AIR
from regional_voxels import WORLD,DIM,ROOT

OUT=ROOT/'artifacts/world_motion_r06'
def main():
    points=[(x,z) for x in range(360,1225,32) for z in range(-160,801,32)]
    selected={(x//16,z//16):set(range(2,16)) for x,z in points};columns={p:{} for p in points}
    by_chunk={(x//16,z//16):(x,z) for x,z in points}
    for cx,cz,sy,pal,indices in iter_selected_sections(WORLD,DIM,selected,skip_unfinished=True):
        p=by_chunk[cx,cz];x,z=p
        for y in range(16):columns[p][sy*16+y]=pal[int(indices[(y<<8)|((z&15)<<4)|(x&15)])]
    rows=[]
    for (x,z),column in columns.items():
        if len(column)!=224:rows.append(dict(x=x,z=z,measured=False));continue
        surface=[y for y,s in column.items() if s.split('[')[0] not in AIR and not s.startswith('minecraft:light[')]
        top=max(surface) if surface else 31;state=column.get(top,'unknown');water=state.startswith('minecraft:water')
        bed=[y for y,s in column.items() if y<top and s.split('[')[0] not in AIR and not any(k in s for k in ('water','kelp','seagrass','light['))]
        bottom=max(bed) if bed else 31
        rows.append(dict(x=x,z=z,measured=True,top=top,state=state,open_water=water,seabed=bottom,depth=top-bottom if water else 0))
    (OUT/'harbour_coast_survey.json').write_text(json.dumps(dict(world=str(WORLD),step=32,range_y=[32,255],points=rows),indent=2))
    water=[r for r in rows if r.get('open_water')]
    print('Coast survey',len(rows),'samples',len(water),'open water; sea levels',sorted({r['top'] for r in water}),flush=True)
    print('Deep-water envelope',min((r['x'] for r in water),default=None),max((r['x'] for r in water),default=None),flush=True)

if __name__=='__main__':main()
