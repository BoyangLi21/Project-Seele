"""Stream every generated GeoFront chunk into a 3D connected-component audit.

Blocks are decoded only by query_blocks. Six-neighbour components merge across
chunk faces; an ungenerated neighbour is unknown, never assumed empty. Results
are candidates for inspection, not permission to remove authored structures.
"""
from array import array
from collections import Counter
from itertools import groupby
from pathlib import Path
import argparse,json,time
import numpy as np
from scipy.ndimage import label,find_objects,binary_dilation,generate_binary_structure
from query_blocks import iter_selected_sections,dimension_dir,AIR
from regional_voxels import WORLD,DIM,ROOT

SOIL={'minecraft:stone','minecraft:deepslate','minecraft:dirt','minecraft:grass_block','minecraft:gravel','minecraft:sand','minecraft:sandstone','minecraft:coarse_dirt','minecraft:clay','minecraft:andesite','minecraft:diorite','minecraft:granite','minecraft:tuff','minecraft:calcite','minecraft:bedrock','minecraft:podzol','minecraft:rooted_dirt','minecraft:mud'}
WATER={'minecraft:water','projectseele:lcl','minecraft:lava'}
STRUCTURE=generate_binary_structure(3,1)

def rle(a):
    a=a.ravel();ends=np.r_[np.flatnonzero(a[1:]!=a[:-1])+1,len(a)]
    return a[np.r_[0,ends[:-1]]].copy(),np.diff(np.r_[0,ends]).astype(np.uint16)
def expand(r):return np.repeat(*r)

class Components:
    def __init__(self,min_y):
        self.min_y=min_y;self.parent=array('i',[0]);self.size=array('q',[0]);self.flags=array('B',[0])
        self.bounds=[array('i',[0]) for _ in range(6)];self.seed=[array('i',[0]) for _ in range(3)]
        self.seen=set();self.faces={};self.solid_cells=0;self.water_cells=0
    def find(self,a):
        while self.parent[a]!=a:
            self.parent[a]=self.parent[self.parent[a]];a=self.parent[a]
        return a
    def flag(self,a,bit):
        if a:self.flags[self.find(int(a))]|=bit
    def union(self,a,b):
        a,b=self.find(int(a)),self.find(int(b))
        if a==b:return
        if self.size[a]<self.size[b]:a,b=b,a
        self.parent[b]=a;self.size[a]+=self.size[b]
        self.flags[a]=((self.flags[a]&self.flags[b])&1)|((self.flags[a]|self.flags[b])&14)
        for i in range(3):self.bounds[i][a]=min(self.bounds[i][a],self.bounds[i][b]);self.bounds[i+3][a]=max(self.bounds[i+3][a],self.bounds[i+3][b])
    def add_chunk(self,cx,cz,solid,natural,water,known=True):
        local,n=label(solid,STRUCTURE);counts=np.bincount(local.ravel(),minlength=n+1);soils=np.bincount(local[natural],minlength=n+1)
        wet=np.unique(local[binary_dilation(water,structure=STRUCTURE)&solid]) if water.any() else np.array([],int)
        wet=set(map(int,wet));bottom=set(map(int,np.unique(local[0])));top=set(map(int,np.unique(local[-1])))
        mapping=np.zeros(n+1,np.int32)
        for k,box in enumerate(find_objects(local),1):
            if box is None:continue
            node=len(self.parent);mapping[k]=node;self.parent.append(node);self.size.append(int(counts[k]))
            self.flags.append((1 if soils[k]==counts[k] else 0)|(2 if k in bottom else 0)|(4 if not known or k in top else 0)|(8 if k in wet else 0))
            lo=[cx*16+box[2].start,self.min_y+box[0].start,cz*16+box[1].start];hi=[cx*16+box[2].stop-1,self.min_y+box[0].stop-1,cz*16+box[1].stop-1]
            for axis,value in enumerate(lo+hi):self.bounds[axis].append(int(value))
            yy,zz,xx=np.unravel_index(int(np.argmax(local[box]==k)),local[box].shape)
            for axis,value in enumerate([lo[0]+xx,lo[1]+yy,lo[2]+zz]):self.seed[axis].append(int(value))
        glob=mapping[local];self.solid_cells+=int(solid.sum());self.water_cells+=int(water.sum())
        surfaces=[glob[:,:,0],glob[:,:,-1],glob[:,0,:],glob[:,-1,:]];waters=[water[:,:,0],water[:,:,-1],water[:,0,:],water[:,-1,:]]
        for side,(dx,dz,opposite) in enumerate([(-1,0,1),(1,0,0),(0,-1,3),(0,1,2)]):
            neighbour=(cx+dx,cz+dz);face=surfaces[side].ravel();fluid=waters[side].ravel()
            if neighbour in self.seen:
                other=self.faces.pop((*neighbour,opposite),None)
                if other is None:continue
                old,wetface=expand(other[0]),expand(other[1]);both=(face!=0)&(old!=0)
                pairs=np.unique((face[both].astype(np.uint64)<<32)|old[both].astype(np.uint64))
                for pair in pairs:self.union(int(pair)>>32,int(pair)&0xffffffff)
                for node in np.unique(face[wetface.astype(bool)]):self.flag(node,8)
                for node in np.unique(old[fluid]):self.flag(node,8)
            elif face.any() or fluid.any():self.faces[cx,cz,side]=(rle(face),rle(fluid))
        self.seen.add((cx,cz))
    def finish(self):
        # Remaining faces border data that was not present as a FULL chunk.
        for labels,_ in self.faces.values():
            for node in np.unique(labels[0]):self.flag(node,4)
        self.faces.clear();candidates=[];counts=Counter()
        for node in range(1,len(self.parent)):
            if self.find(node)!=node:continue
            flags=self.flags[node]
            kind='ground_connected' if flags&2 else 'unknown_boundary' if flags&4 else 'fluid_contact' if flags&8 else 'detached_soil' if flags&1 else 'detached_other'
            counts[kind]+=1
            if kind in ('detached_soil','detached_other'):
                candidates.append(dict(kind=kind,cells=int(self.size[node]),lo=[a[node] for a in self.bounds[:3]],hi=[a[node] for a in self.bounds[3:]],seed=[a[node] for a in self.seed]))
        return counts,sorted(candidates,key=lambda c:(c['kind'],-c['cells']))

def self_test():
    world=np.zeros((8,16,32),bool);world[0]=True;world[4,5,15:17]=True;world[4,10,15]=True;world[4,12,12]=True
    soil=world.copy();soil[4,12,12]=False;water=np.zeros_like(world);water[4,10,16]=True
    c=Components(0)
    for x in range(2):c.add_chunk(x,0,world[:,:,x*16:(x+1)*16],soil[:,:,x*16:(x+1)*16],water[:,:,x*16:(x+1)*16])
    counts,items=c.finish();assert counts['ground_connected']==1 and counts['fluid_contact']==1
    assert [(x['kind'],x['cells']) for x in items]==[('detached_other',1),('detached_soil',2)],items
    assert items[1]['lo']==[15,4,5] and items[1]['hi']==[16,4,5]
    print('Component audit: cross-chunk island, cross-face fluid support and ground connection PASS')

def main(output_dir=None):
    out=Path(output_dir) if output_dir else ROOT/'artifacts/world_repair_r19/global_components';out.mkdir(parents=True,exist_ok=True)
    start=time.monotonic();c=Components(-672);sections=0;incomplete=0
    regions=sorted((dimension_dir(WORLD,DIM)/'region').glob('r.*.*.mca'))
    for number,region in enumerate(regions,1):
        rx,rz=map(int,region.stem.split('.')[1:]);ys=set(range(-42,20));selected={(x,z):ys for x in range(rx*32,rx*32+32) for z in range(rz*32,rz*32+32)}
        stream=iter_selected_sections(WORLD,DIM,selected,skip_unfinished=True)
        for (cx,cz),rows in groupby(stream,key=lambda row:row[:2]):
            solid=np.zeros((992,16,16),bool);natural=np.zeros_like(solid);water=np.zeros_like(solid);seen=set()
            for _,_,sy,pal,idx in rows:
                names=[s.split('[')[0] for s in pal];a=idx.reshape(16,16,16);sl=slice((sy+42)*16,(sy+43)*16)
                solid[sl]=np.array([n not in AIR|WATER|{'minecraft:light'} for n in names])[a]
                natural[sl]=np.array([n in SOIL or n.endswith('_ore') for n in names])[a]
                water[sl]=np.array([n in WATER for n in names])[a];seen.add(sy);sections+=1
            known=seen==ys;incomplete+=not known;c.add_chunk(cx,cz,solid,natural,water,known)
        print('3D COMPONENT SCAN regions',number,'/',len(regions),'chunks',len(c.seen),'components',len(c.parent)-1,'elapsed',round(time.monotonic()-start,1),flush=True)
    counts,items=c.finish();report=dict(world=str(WORLD),dimension=DIM,regions=len(regions),full_chunks=len(c.seen),sections=sections,incomplete_section_chunks=incomplete,
        solid_voxels=c.solid_cells,fluid_voxels=c.water_cells,component_counts=dict(counts),candidates=items,elapsed_seconds=round(time.monotonic()-start,1),
        interpretation='Six-connected voxel components only. Fluid-supported ships and unknown map edges are distinguished. Authored detached components require semantic inspection; no automatic deletion.')
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('Component audit complete',dict(counts),flush=True)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--self-test',action='store_true');args=a.parse_args();self_test() if args.self_test else main()
