"""Restore the user-reported former surface railway cut, using its recorded alignment."""
from pathlib import Path
import json,math,numpy as np
from scipy.spatial import cKDTree
import regional_voxels as v
from query_blocks import read_box,iter_block_entities
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_FIELD_R29_REVIEW';OUT=ROOT/'artifacts/facility_r29/surface_cut'
def main():
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter()
    historical=ROOT/'artifacts/world_rebuild_r20/transit/native_snapshot.json'
    old=[c for c in json.loads(historical.read_text())['curves'] if c['mode']=='TRAIN' and 70<c['points'][0][1]<90]
    points=np.array([q for c in old for q in c['points']]);oldtree=cKDTree(points[:,[0,2]])
    active=[c for c in json.loads((WORLD/'native_transit_r28.json').read_text())['curves'] if c['mode']=='TRAIN' and c['points'][0][1]>30]
    nowtree=cKDTree(np.array([q for c in active for q in c['points']])[:,[0,2]])
    lo=(158,40,-112);hi=(270,90,28);cells=read_box(WORLD,v.DIM,lo,hi)
    ground=[]
    for (x,y,z),s in cells.items():
        if s.startswith('minecraft:grass_block') and oldtree.query([x+.5,z+.5])[0]>9:ground.append((x+.5,y,z+.5))
    ground=np.array(ground);tree=cKDTree(ground[:,[0,2]])
    fixtures=list(iter_block_entities(WORLD,v.DIM,lo,hi))
    formation={'minecraft:polished_deepslate','minecraft:light_gray_concrete','minecraft:polished_basalt','minecraft:iron_bars','minecraft:gravel'}
    columns=[];protected=0
    for x in range(173,256):
        for z in range(-97,14):
            if math.hypot(x-214,z+42)>49:continue
            distance,index=oldtree.query([x+.5,z+.5]);current,_=nowtree.query([x+.5,z+.5])
            if distance>8.0 or current<12:continue
            if any(abs(x-q[0])<=3 and abs(z-q[2])<=3 for q,t in fixtures):protected+=1;continue
            ds,ids=tree.query([x+.5,z+.5],k=16);near=ground[ids]
            # Fit to the surrounding uncut grass, never to the void or old rail.
            weight=1/np.maximum(ds,1);a=np.c_[near[:,0]-(x+.5),near[:,2]-(z+.5),np.ones(len(near))]
            fit=np.linalg.lstsq(a*weight[:,None],near[:,1]*weight,rcond=None)[0]
            top=int(np.clip(round(fit[2]),math.floor(near[:,1].min()),math.ceil(near[:,1].max())))
            top=max(64,min(82,top));changed=0
            for y in range(60,86):
                oldstate=cells[x,y,z];kind=oldstate.split('[')[0]
                if y<=top and (kind in formation or kind in ('minecraft:air','minecraft:grass_block','minecraft:dirt','minecraft:stone')):
                    wanted='minecraft:grass_block[snowy=false]' if y==top else 'minecraft:dirt' if y>=top-2 else 'minecraft:stone'
                elif y>top and kind in formation:wanted='minecraft:air'
                else:continue
                if oldstate!=wanted:p.match((x,y,z,x,y,z),oldstate,wanted,'r29/retired_surface_cut_backfill');changed+=1
            if changed:columns.append(dict(x=x,z=z,top=top,changed=changed,old_rail=points[index].tolist(),current_rail_distance=float(current)))
    p.meta.update(reported_xz=[214,-42],measured_excavation_floor=64,columns=columns,protected_fixtures=protected,historical_alignment=str(historical),scope='Former surface rail corridor within49m of reported point; current rails12m and all existing block-entity fixtures excluded; underground U1/U2 untouched.')
    p.apply('backfill_recorded_surface_cut');(OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
    print('Restored',len(columns),'former corridor columns',flush=True)
if __name__=='__main__':main()
