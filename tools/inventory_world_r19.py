"""Read all generated GeoFront sections for the reported defect classes."""
from pathlib import Path
from collections import Counter
import json, re, time
import numpy as np
from query_blocks import iter_selected_sections, read_box, dimension_dir, AIR
from regional_voxels import WORLD, DIM, ROOT

OUT=ROOT/'artifacts/world_repair_r19/inventory'

def category(s):
    name=s.split('[')[0]
    if name.endswith(('_wall_sign','_sign','_hanging_sign')): return 'signs'
    if name.endswith('_button'): return 'buttons'
    if name.startswith('mtr:ticket_machine'): return 'ticket_machines'
    if name.startswith('another_furniture:') and ('chair' in name or 'bench' in name): return 'wooden_seats'
    if name.startswith('mtr:escalator_'): return 'escalators'
    if name in ('projectseele:station_departure_board','projectseele:nerv_direction_panel'):return 'departure_boards'
    if name.startswith('mtr:apg_'):return 'platform_gates'
    if name.startswith('projectseele:moving_walkway'):return 'legacy_walkways'
    return None

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    results={k:[] for k in ('signs','buttons','ticket_machines','wooden_seats','escalators','departure_boards','platform_gates','legacy_walkways')}
    sections=0;chunks=set();start=time.monotonic();census=Counter();states=set()
    regions=sorted((dimension_dir(WORLD,DIM)/'region').glob('r.*.*.mca'))
    for number,path in enumerate(regions):
        rx,rz=map(int,path.stem.split('.')[1:]);ys=set(range(-42,20))
        selected={(x,z):ys for x in range(rx*32,rx*32+32) for z in range(rz*32,rz*32+32)}
        for cx,cz,sy,pal,idx in iter_selected_sections(WORLD,DIM,selected,skip_unfinished=True):
            sections+=1;chunks.add((cx,cz));states.update(pal)
            for i,s in enumerate(pal):
                cat=category(s)
                if cat is None:continue
                offsets=np.flatnonzero(idx==i);census[cat]+=len(offsets)
                for n in offsets:
                    results[cat].append({'pos':[cx*16+int(n%16),sy*16+int(n//256),cz*16+int((n//16)%16)],'state':s})
        if number%5==0:print('Scanned',number+1,'/',len(regions),'regions;',len(chunks),'chunks;',round(time.monotonic()-start,1),'seconds',flush=True)
    # Support inspection is grouped by chunk so cross-boundary neighbours are
    # measured once through the same canonical reader, not guessed as air.
    supports={};faces={'north':(0,0,1),'south':(0,0,-1),'east':(-1,0,0),'west':(1,0,0)}
    for cat in ('signs','buttons'):
        for row in results[cat]:
            s=row['state'];x,y,z=row['pos']
            if '_wall_sign[' in s or cat=='buttons' and 'face=wall' in s:
                facing=re.search(r'facing=([a-z]+)',s).group(1);dx,dy,dz=faces[facing]
            elif '_hanging_sign[' in s or cat=='buttons' and 'face=ceiling' in s:dx,dy,dz=0,1,0
            else:dx,dy,dz=0,-1,0
            at=(x+dx,y+dy,z+dz);key=(at[0]//16,at[1]//16,at[2]//16)
            if key not in supports:
                cx,sy,cz=key;supports[key]=read_box(WORLD,DIM,(cx*16,sy*16,cz*16),(cx*16+15,sy*16+15,cz*16+15))
            state=supports[key].get(at,'UNKNOWN');row['backing']=list(at);row['backing_state']=state
            row['unsupported']=state.split('[')[0] in AIR|{'minecraft:light'}
    report={'world':str(WORLD),'regions':len(regions),'full_chunks':len(chunks),'sections':sections,'census':dict(census),'seconds':round(time.monotonic()-start,1),'objects':results,'block_states':sorted(states)}
    (OUT/'world_objects.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('Inventory complete:',{k:len(v) for k,v in results.items()},'unsupported signs',sum(r['unsupported'] for r in results['signs']),'unsupported buttons',sum(r['unsupported'] for r in results['buttons']),flush=True)

if __name__=='__main__':main()
