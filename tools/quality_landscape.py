"""Restore planted parks and restrained street lighting after terrain repair."""
import argparse,json,math,random
import numpy as np
import regional_voxels as vox
from quality_structures import Builder,OUT,OLD,load
from regional_architecture import FLOOR,DARK,AIR,bench

def tree(p,x,z,f,owner,seed):
    rng=random.Random(seed);height=6+seed%3;name='birch' if seed%4==0 else 'oak'
    p.fill(x,f+1,z,x,f+height,z,f'minecraft:{name}_log[axis=y]',owner)
    for side in (-1,1):p.fill(x+min(0,side*2),f+height-1,z,x+max(0,side*2),f+height-1,z,f'minecraft:{name}_log[axis=x]',owner)
    leaf=f'minecraft:{name}_leaves[distance=1,persistent=true,waterlogged=false]'
    for yy in range(-3,5):
        for zz in range(-4,5):
            for xx in range(-4,5):
                if (xx/4.2)**2+(zz/3.9)**2+(yy/3.7)**2>1+rng.uniform(-.12,.12):continue
                if xx==zz==0 and yy<=0:continue
                if yy==-1 and zz==0 and abs(xx)<=2:continue
                p.put(x+xx,f+height+yy,z+zz,leaf,owner)

def build():
    p=Builder();layout=load(OUT/'surface_layout.json');a=np.load(OUT/'road_surfaces.npz');mask=a['mask'];values=a['height2'];ox,oz=map(int,a['origin'])
    buildings=layout['kept_plots'];parks=[b for b in buildings if b.get('style')=='park']
    for b in parks:
        x0,x1,z0,z1=b['bounds'];f=b['floor'];cx=(x0+x1)//2;cz=(z0+z1)//2;name=b['id']+'/landscape'
        p.fill(cx-1,f,z0,cx+1,f,z1,'minecraft:gravel',name)
        p.fill(x0,f,cz-1,x1,f,cz+1,'minecraft:gravel',name)
        for dx in (-1,1):
            for dz in (-1,1):tree(p,cx+dx*9,cz+dz*9,f,name,sum(map(ord,b['id']))+dx*13+dz*29)
        for x in (cx-6,cx+6):bench(p,x,cz+6,f,name,'north')
        # Keep any already verified approach that touches a park completely clear.
        for z in range(z0,z1+1):
            for x in range(x0,x1+1):
                if mask[z-oz,x-ox]:p.protect((x,f,z,x,f+12,z),'verified_road')
    occupied=set()
    for rail in load(OLD/'transit2/track_samples.json'):
        if rail['mode']!='TRAIN':continue
        for x,y,z in rail['points'][::6]:
            if y>=65:
                cx,cz=round(x)//8,round(z)//8;occupied.update((cx+i,cz+j) for i in (-1,0,1) for j in (-1,0,1))
    placed=set()
    for x,z,xx,zz,width in load(OUT/'road_plan.json')['segments']:
        distance=max(abs(xx-x),abs(zz-z));vx,vz=xx-x,zz-z
        for i in range(20,distance,48):
            px=round(x+vx*i/max(1,distance));pz=round(z+vz*i/max(1,distance));offset=width//2+4
            lx,lz=(px+offset,pz) if vx==0 else (px,pz+offset)
            if (lx,lz) in placed or (lx//8,lz//8) in occupied:continue
            ix,iz=px-ox,pz-oz;ax,az=lx-ox,lz-oz
            if not 0<=ax<mask.shape[1] or not 0<=az<mask.shape[0] or not mask[iz,ix] or mask[az,ax]:continue
            if any(a-2<=lx<=b+2 and c-2<=lz<=d+2 for a,b,c,d in [v['bounds'] for v in buildings]):continue
            if -432<=lx<=-280 and 690<=lz<=833:continue
            floor=(int(values[iz,ix])-1)//2;owner='city/street_light';placed.add((lx,lz))
            p.fill(lx,floor-3,lz,lx,floor,lz,DARK,owner)
            p.fill(lx,floor+1,lz,lx,floor+6,lz,'minecraft:iron_bars[east=false,north=false,south=false,waterlogged=false,west=false]',owner)
            dx,dz=(-1,0) if vx==0 else (0,-1)
            p.fill(lx,floor+6,lz,lx+dx,floor+6,lz+dz,'minecraft:polished_blackstone_slab[type=bottom,waterlogged=false]',owner)
            p.put(lx+dx,floor+5,lz+dz,'minecraft:lantern[hanging=true,waterlogged=false]',owner)
    p.meta['restored_parks']=len(parks);p.meta['street_lights']=len(placed);vox.OUT=OUT
    return p

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args();p=build()
    p.apply('city_landscape') if args.apply else p.save_plan('city_landscape')
