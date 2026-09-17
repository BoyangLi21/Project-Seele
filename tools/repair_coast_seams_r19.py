"""Reconnect measured sea-level water to adjacent dry natural shore basins.

The flood is constrained to existing FULL chunks at the established Y=62 sea
plane. Engineered columns and named access shafts are excluded. Water is only
added above a measured natural floor, never inferred across missing chunks.
"""
from collections import defaultdict, deque
import argparse, json
import numpy as np
from scipy.ndimage import binary_propagation
import regional_voxels as vox
from query_blocks import AIR, iter_selected_sections, dimension_dir

OUT=vox.ROOT/'artifacts/world_repair_r19/coast'
SEA=62
GROUND={'minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:gravel','minecraft:sand','minecraft:sandstone','minecraft:clay','minecraft:coarse_dirt','minecraft:podzol','minecraft:andesite','minecraft:diorite','minecraft:granite','minecraft:deepslate','minecraft:tuff','minecraft:bedrock'}
PLANTS={'minecraft:grass','minecraft:tall_grass','minecraft:fern','minecraft:large_fern','minecraft:seagrass','minecraft:tall_seagrass'}
EXCLUDE=[(-373,-347,737,763),(119,141,261,285)]

def groups():
    remaining={tuple(map(int,p.stem.split('.')[1:])) for p in (dimension_dir(vox.WORLD,vox.DIM)/'region').glob('r.*.*.mca')}
    while remaining:
        first=remaining.pop();group={first};queue=deque([first])
        while queue:
            rx,rz=queue.popleft()
            for n in ((rx-1,rz),(rx+1,rz),(rx,rz-1),(rx,rz+1)):
                if n in remaining:remaining.remove(n);group.add(n);queue.append(n)
        yield sorted(group)

def main(apply=False):
    vox.OUT=OUT;painter=vox.Painter();stats=[];total=0;held_columns=[]
    for index,regions in enumerate(groups()):
        x0=min(r[0] for r in regions)*512;z0=min(r[1] for r in regions)*512
        width=(max(r[0] for r in regions)+1)*512-x0;depth=(max(r[1] for r in regions)+1)*512-z0
        eligible=np.zeros((depth,width),bool);water=np.zeros_like(eligible);by_chunk={}
        for rx,rz in regions:
            selected={(x,z):{SEA//16} for x in range(rx*32,rx*32+32) for z in range(rz*32,rz*32+32)}
            for cx,cz,sy,pal,idx in iter_selected_sections(vox.WORLD,vox.DIM,selected,skip_unfinished=True):
                a=idx.reshape(16,16,16)[SEA%16];names=[s.split('[')[0] for s in pal]
                wet=np.array([s=='minecraft:water' for s in names])[a]
                free=np.array([s in AIR|PLANTS for s in names])[a]
                zs=slice(cz*16-z0,cz*16-z0+16);xs=slice(cx*16-x0,cx*16-x0+16)
                eligible[zs,xs]=wet|free;water[zs,xs]=wet;by_chunk[cx,cz]=None
        for ax,bx,az,bz in EXCLUDE:
            if bx<x0 or ax>=x0+width or bz<z0 or az>=z0+depth:continue
            eligible[max(0,az-z0):min(depth,bz-z0+1),max(0,ax-x0):min(width,bx-x0+1)]=False
        reached=binary_propagation(water,mask=eligible|water)
        candidates=reached&~water;selected_chunks={}
        for cx,cz in by_chunk:
            local=candidates[cz*16-z0:cz*16-z0+16,cx*16-x0:cx*16-x0+16]
            if local.any():selected_chunks[cx,cz]=set(range(4))
        print('Coast component',index,'regions',len(regions),'candidate columns',int(candidates.sum()),flush=True)
        # Read only candidate columns' chunks below the actual sea plane.
        blocks={};palettes={}
        for cx,cz,sy,pal,idx in iter_selected_sections(vox.WORLD,vox.DIM,selected_chunks,skip_unfinished=True):
            blocks[cx,cz,sy]=idx.reshape(16,16,16);palettes[cx,cz,sy]=pal
        changed=0;held=0
        for cx,cz in selected_chunks:
            for zz,xx in np.argwhere(candidates[cz*16-z0:cz*16-z0+16,cx*16-x0:cx*16-x0+16]):
                x=cx*16+int(xx);z=cz*16+int(zz)
                col=[]
                for y in range(SEA+1):
                    key=cx,cz,y//16
                    col.append(palettes[key][int(blocks[key][y%16,zz,xx])] if key in blocks else 'UNKNOWN')
                names=[s.split('[')[0] for s in col]
                if any(s=='UNKNOWN' or s not in GROUND|AIR|PLANTS|{'minecraft:water'} for s in names):
                    held+=1;held_columns.append(dict(x=x,z=z,reason='Engineered or unmeasured column',states=sorted(set(s for s in names if s not in GROUND|AIR|PLANTS|{'minecraft:water'}))));continue
                floor=max((i for i,s in enumerate(names) if s in GROUND),default=-1)
                if floor<0 or floor>=SEA:
                    held+=1;held_columns.append(dict(x=x,z=z,reason='No natural bed below sea level',floor=floor));continue
                for old in set(col[floor+1:]):
                    if old.split('[')[0] in AIR|PLANTS:
                        painter.match((x,floor+1,z,x,SEA,z),old,'minecraft:water[level=0]','r19/connected_shore_water')
                if names[floor]=='minecraft:grass_block':
                    painter.match((x,floor,z,x,floor,z),col[floor],'minecraft:sand' if (x*7+z)%5 else 'minecraft:gravel','r19/submerged_shore_floor')
                changed+=1
        total+=changed;stats.append({'component':index,'regions':regions,'candidate_columns':int(candidates.sum()),'natural_columns_reconnected':changed,'engineered_or_unmeasured_columns_held':held})
        print('Measured natural shore columns',changed,'protected',held,flush=True)
    painter.meta.update(sea_level=SEA,components=stats,reconnected_columns=total,excluded_access_shafts=EXCLUDE,held_columns=held_columns)
    painter.apply('sea_level_connections') if apply else painter.save_plan('sea_level_connections')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
