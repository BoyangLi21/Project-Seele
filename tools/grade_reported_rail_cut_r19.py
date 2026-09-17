"""Blend the measured C1 cutting into its hillside, retaining the native rail grade."""
import argparse,json,math
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import distance_transform_edt
import regional_voxels as vox
from scan_regional_completion import volume
from query_blocks import AIR

OUT=vox.ROOT/'artifacts/world_repair_r19/rail_cut'
LO=(-748,48,616);HI=(-400,116,712)
GROUND={'minecraft:grass_block','minecraft:dirt','minecraft:coarse_dirt','minecraft:podzol','minecraft:stone','minecraft:gravel','minecraft:sand','minecraft:clay','minecraft:andesite','minecraft:diorite','minecraft:granite'}

def smooth(v):v=np.clip(v,0,1);return v*v*(3-2*v)

def main(apply=False):
    vox.OUT=OUT;p=vox.Painter();a,pal=volume(LO,HI);names=[s.split('[')[0] for s in pal];ys=np.arange(LO[1],HI[1]+1)[:,None,None]
    soil=np.array([s in GROUND for s in names]);tree=np.array([s.endswith(('_leaves','_log')) for s in names]);water=np.array([s=='minecraft:water' for s in names]);empty=np.array([s in AIR|{'minecraft:light','minecraft:grass','minecraft:fern','minecraft:tall_grass'} for s in names])
    ground=np.where(soil[a],ys,LO[1]-1).max(0);built=np.where((~(soil|tree|water|empty))[a],ys,LO[1]-1).max(0)
    trees=np.where(tree[a],ys,LO[1]-1).max(0);wet=np.where(water[a],ys,LO[1]-1).max(0)
    fixed=(built>=ground)|(trees>ground)|(wet>=ground)|(ground<=LO[1])
    data=json.loads((OUT.parent/'rails/current_train_samples.json').read_text());points=[]
    for rail in data:
        for x,y,z in rail['points']:
            if LO[0]-20<=x<=HI[0]+20 and LO[2]-20<=z<=HI[2]+20 and 75<=y<=105:points.append((x,y,z))
    points=np.asarray(points);zz,xx=np.indices(ground.shape);world=np.stack((xx.ravel()+LO[0]+.5,zz.ravel()+LO[2]+.5),axis=1)
    distance,index=cKDTree(points[:,[0,2]]).query(world);distance=distance.reshape(ground.shape);railY=points[index,1].reshape(ground.shape)
    weight=(1-smooth((distance-3)/13))*smooth(distance_transform_edt(~fixed)/6)
    edge=np.minimum.reduce([xx,zz,ground.shape[1]-1-xx,ground.shape[0]-1-zz]);weight*=smooth(edge/8)
    cut=np.minimum(ground,railY-1+np.maximum(0,distance-3)*.75)
    fill=np.maximum(ground,railY-1-np.maximum(0,distance-3)*.75)
    desired=np.where(ground>=railY,cut,fill)
    target=np.rint(ground*(1-weight)+desired*weight).astype(int)
    active=(distance>3)&(distance<16)&~fixed&(target!=ground)
    count=0
    for iz,ix in np.argwhere(active):
        x,z=int(ix+LO[0]),int(iz+LO[2]);oldY,newY=int(ground[iz,ix]),int(target[iz,ix]);count+=1
        for y in range(min(oldY,newY)-2,max(oldY,newY)+1):
            before=pal[int(a[y-LO[1],iz,ix])];base=before.split('[')[0]
            if base not in GROUND|AIR|{'minecraft:grass','minecraft:fern','minecraft:tall_grass'}:continue
            after='minecraft:air' if y>newY else 'minecraft:gravel' if y==newY and distance[iz,ix]<5 else 'minecraft:grass_block[snowy=false]' if y==newY else 'minecraft:dirt' if y>=newY-2 else 'minecraft:stone'
            if before!=after:p.match((x,y,z,x,y,z),before,after,'r19/C1_continuous_cutting_slope')
    p.meta.update(reported_observation=[-602,103,682],native_rail_grade_unchanged=True,natural_columns=count,
        preserved='paved roads, structures, trees, water and their six-metre transition margins',bounds=[LO,HI])
    p.apply('C1_cutting') if apply else p.save_plan('C1_cutting')
    np.savez_compressed(OUT/'C1_cutting/height_comparison.npz',before=ground,after=np.where(active,target,ground),changed=active,bounds=[LO,HI])

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
