"""Audit current MTR curves and prune vegetation/repair missing track support."""
from collections import defaultdict,Counter
import argparse,json,math
import numpy as np
import regional_voxels as vox
from query_blocks import AIR,iter_selected_sections
from audit_regional_transit_clearance import mark
from scan_regional_completion import volume

OUT=vox.ROOT/'artifacts/world_repair_r19/rails'
GROUND={'minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:coarse_dirt','minecraft:podzol','minecraft:rooted_dirt','minecraft:sand','minecraft:gravel','minecraft:clay','minecraft:andesite','minecraft:diorite','minecraft:granite','minecraft:deepslate','minecraft:tuff'}

def natural(s):
    n=s.split('[')[0]
    return n in GROUND|{'minecraft:grass','minecraft:fern','minecraft:tall_grass','minecraft:large_fern','minecraft:vine','minecraft:dead_bush'} or n.endswith(('_leaves','_log','_ore'))

def main(apply=False):
    vox.OUT=OUT;painter=vox.Painter();rails=json.loads((OUT/'current_train_samples.json').read_text());clear={};beds={};selected=defaultdict(set)
    for rail in rails:
        for point in rail['points']:
            x,y,z=map(math.floor,point)
            mark(clear,x-2,y+1,z-2,x+2,y+5,z+2)
            mark(beds,x-2,y-2,z-2,x+2,y-1,z+2)
    for cx,cz,sy in clear.keys()|beds.keys():selected[cx,cz].add(sy)
    repaired=Counter();blocked=Counter();examples=[];measured_chunks=set()
    for cx,cz,sy,pal,idx in iter_selected_sections(vox.WORLD,vox.DIM,selected):
        measured_chunks.add((cx,cz));a=idx.reshape(16,16,16);key=cx,cz,sy
        if key in clear:
            mask=clear[key]
            for value in np.unique(a[mask]):
                s=pal[int(value)];base=s.split('[')[0]
                if base in AIR|{'minecraft:light'}:continue
                bad=mask&(a==value)
                if natural(s):
                    for yy,zz,xx in np.argwhere(bad):
                        pos=(cx*16+int(xx),sy*16+int(yy),cz*16+int(zz));painter.match((*pos,*pos),s,'minecraft:air','r19/native_rail_natural_clearance')
                    repaired['rail_clearance']+=int(bad.sum())
                else:
                    blocked[s]+=int(bad.sum())
                    if len(examples)<200:
                        for yy,zz,xx in np.argwhere(bad)[:5]:examples.append({'pos':[cx*16+int(xx),sy*16+int(yy),cz*16+int(zz)],'state':s})
        if key in beds:
            mask=beds[key]
            for value in np.unique(a[mask]):
                s=pal[int(value)]
                if s.split('[')[0] not in AIR:continue
                for yy,zz,xx in np.argwhere(mask&(a==value)):
                    pos=(cx*16+int(xx),sy*16+int(yy),cz*16+int(zz))
                    # Never add a support block in another line's vehicle envelope.
                    if key in clear and clear[key][yy,zz,xx]:continue
                    painter.match((*pos,*pos),s,'projectseele:nerv_structural_panel' if pos[1]<0 else 'minecraft:gray_concrete','r19/missing_rail_support');repaired['bed']+=1
    stations=json.loads((vox.ROOT/'artifacts/world_expansion_20260907/transit_plan.json').read_text(encoding='utf8'))['platforms']
    stations+=json.loads((vox.ROOT/'artifacts/world_quality_r02/extension_plan.json').read_text(encoding='utf8'))['transit']['platforms']
    stations+=json.loads((vox.ROOT/'artifacts/world_expansion_r07/port_transit_plan.json').read_text(encoding='utf8'))['platforms']
    vegetation=[]
    for st in stations:
        if st.get('mode')=='AIRPLANE':continue
        x,y,z=map(int,st['center']);h=st['length']//2+13;r=13 if st.get('compact') else 18;horizontal=st['heading'] in ('E','W')
        lo=(x-h,y+1,z-r) if horizontal else (x-r,y+1,z-h);hi=(x+h,y+18,z+r) if horizontal else (x+r,y+18,z+h)
        a,pal=volume(lo,hi);count=0
        for i,s in enumerate(pal):
            n=s.split('[')[0]
            if not n.endswith(('_leaves','_log')):continue
            for yy,zz,xx in np.argwhere(a==i):
                pos=(int(xx+lo[0]),int(yy+lo[1]),int(zz+lo[2]));painter.match((*pos,*pos),s,'minecraft:air','r19/station_vegetation_intrusion');count+=1
        vegetation.append({'station':st['id'],'removed_intruding_tree_blocks':count})
    painter.meta.update(source='CurrentRailSurveyR19 using the installed MTR evaluator on a cold copy',rails=len(rails),measured_chunks=len(measured_chunks),
        repaired=dict(repaired),station_vegetation=vegetation,authored_obstructions_requiring_review=dict(blocked),obstruction_examples=examples,
        envelope='TRAIN radius2 at y+1..5; support y-2..-1. No guessed rail paths and no change to native transit data.')
    painter.apply('rail_envelopes') if apply else painter.save_plan('rail_envelopes')
    print('Repair counts:',dict(repaired),'station vegetation',sum(s['removed_intruding_tree_blocks'] for s in vegetation),'authored obstruction cells',sum(blocked.values()),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
