"""Replace the steep C1 street trough with measured 1:10 approaches and soil banks."""
import argparse,json,math
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import distance_transform_edt
import regional_voxels as vox
from scan_regional_completion import volume
from query_blocks import AIR
from quality_roads import envelopes

OUT=vox.ROOT/'artifacts/world_repair_r19/roads'
LO=(-780,56,560);HI=(-568,116,776)
SOIL={'minecraft:grass_block','minecraft:dirt','minecraft:stone','minecraft:gravel','minecraft:coarse_dirt','minecraft:andesite','minecraft:diorite','minecraft:granite'}
PAVING={'minecraft:black_concrete','minecraft:white_concrete','minecraft:light_gray_concrete','minecraft:gray_concrete','minecraft:smooth_stone','minecraft:polished_blackstone','minecraft:polished_blackstone_slab','minecraft:smooth_stone_slab','minecraft:quartz_slab','minecraft:polished_deepslate','minecraft:polished_deepslate_stairs','projectseele:nerv_structural_panel'}

def main(apply=False):
    vox.OUT=OUT;p=vox.Painter();a,pal=volume(LO,HI);base=[s.split('[')[0] for s in pal]
    old=np.load(vox.ROOT/'artifacts/world_quality_r02/road_surfaces.npz');ox,oz=map(int,old['origin'])
    sl=np.s_[LO[2]-oz:HI[2]-oz+1,LO[0]-ox:HI[0]-ox+1];mask=old['mask'][sl].copy();height=old['height2'][sl].copy();carriage=old['carriage'][sl];stripe=old['stripe'][sl]
    rails=json.loads((OUT.parent/'rails/current_train_samples.json').read_text());points=[]
    for r in rails:
        for x,y,z in r['points']:
            if -750<=x<=-548 and 610<=z<=692 and 78<=y<=102:points.append((x,y,z))
    points=np.asarray(points);zz,xx=np.indices(mask.shape);query=np.stack((xx.ravel()+LO[0]+.5,zz.ravel()+LO[2]+.5),1)
    distance,index=cKDTree(points[:,[0,2]]).query(query);distance=distance.reshape(mask.shape);ry=points[index,1].reshape(mask.shape)
    # This named north/south street meets the retained east/west rail at Z680.
    # Keep every transverse crossing datum; extend the approaches along the
    # street instead of projecting one rail's elevation across nearby roads.
    anchor=height[680-LO[2]].astype(float)/2
    cap=np.floor((anchor[None,:]+np.maximum(0,np.abs(zz+LO[2]-680)-2)*.10)*2+1e-5)
    affected=(xx+LO[0]>=-602)&(xx+LO[0]<=-582)
    target=np.where(affected,np.minimum(height,cap),height).astype(np.int16)
    target=envelopes(mask,np.where(mask,target,30000)).astype(np.int16)
    active=mask&(target<height)
    if any(active[0]) or any(active[-1]) or any(active[:,0]) or any(active[:,-1]):raise RuntimeError('Street regrade would reach an unmeasured endpoint')
    # The 1 m voxel world quantizes a 10% grade into half slabs roughly 5 m apart.
    for dx,dz in ((1,0),(0,1),(1,1),(-1,1)):
        x0,x1=max(0,-dx),min(mask.shape[1],mask.shape[1]-dx);z0,z1=0,mask.shape[0]-dz
        m=mask[z0:z1,x0:x1]&mask[z0+dz:z1+dz,x0+dx:x1+dx]
        if np.any(m&(abs(target[z0:z1,x0:x1]-target[z0+dz:z1+dz,x0+dx:x1+dx])>1)):raise RuntimeError('New road has an unwalkable adjacent height')
    changed={};held=[]
    def put(x,y,z,new,owner):
        before=pal[int(a[y-LO[1],z-LO[2],x-LO[0]])]
        if before!=new:changed[x,y,z]=(before,new,owner)
    allow=np.array([n in SOIL|PAVING|AIR|{'minecraft:light','minecraft:grass','minecraft:fern','minecraft:tall_grass'} for n in base])
    ground=np.where(np.array([n in SOIL for n in base])[a],np.arange(LO[1],HI[1]+1)[:,None,None],LO[1]-1).max(0)
    for iz,ix in np.argwhere(active):
        x,z=int(ix+LO[0]),int(iz+LO[2]);h2=int(target[iz,ix]);by=(h2-1)//2;previous=(int(height[iz,ix])-1)//2
        # Remove only old road/soil layers, including stale decks beyond the old
        # four-block headroom cut. Never touch MTR objects or building fixtures.
        for y in range(by-3,HI[1]+1):
            if not allow[a[y-LO[1],iz,ix]]:
                if y<=previous+4:held.append([x,y,z,pal[a[y-LO[1],iz,ix]]])
                continue
            kind='line' if stripe[iz,ix] else 'road' if carriage[iz,ix] else 'walk'
            material={'line':'minecraft:white_concrete','road':'minecraft:black_concrete','walk':'minecraft:smooth_stone'}[kind]
            if h2%2:material={'line':'minecraft:quartz_slab','road':'minecraft:polished_blackstone_slab','walk':'minecraft:smooth_stone_slab'}[kind]+'[type=bottom,waterlogged=false]'
            put(x,y,z,material if y==by else 'minecraft:stone' if y<by else 'minecraft:air','r19/C1_road_grade')
    # Natural verges are graded from the new pavement edge. Existing buildings,
    # trees and water are fixed; their transition is left for explicit review.
    d,near=distance_transform_edt(~mask,return_indices=True);nh=target[near[0],near[1]]/2
    bank_target=np.minimum(ground,np.floor(nh-1+d*.5)).astype(int)
    bank=(d>0)&(d<=12)&(bank_target<ground)&(bank_target>=LO[1]+3)&active[near[0],near[1]]
    for iz,ix in np.argwhere(bank):
        x,z=int(ix+LO[0]),int(iz+LO[2]);newY=int(bank_target[iz,ix]);oldY=int(ground[iz,ix])
        if not np.all(allow[a[newY-2-LO[1]:,iz,ix]]):continue
        for y in range(newY-2,HI[1]+1):
            put(x,y,z,'minecraft:grass_block[snowy=false]' if y==newY else 'minecraft:dirt' if y<newY else 'minecraft:air','r19/C1_natural_verge')
    for pos,(before,after,owner) in sorted(changed.items()):p.match((*pos,*pos),before,after,owner)
    p.meta.update(bounds=[LO,HI],road_columns=int(active.sum()),maximum_grade_before_quantization=.10,road_datums_source='CurrentRailSurveyR19',native_rail_geometry_unchanged=True,preserved_fixtures=held,
        walk_nodes=[{'id':'r19/C1_street_approach','path':[[float(x)+.5,float(target[z-LO[2],x-LO[0]])/2,float(z)+.5] for z in range(620,741,5)]} for x in (-594,-592,-590)])
    folder=p.apply('C1_street_grade') if apply else p.save_plan('C1_street_grade')
    np.savez_compressed(OUT/'C1_street_grade/surface_contract.npz',before=height,after=np.where(mask,target,height),mask=mask,changed=active,origin=[LO[0],LO[2]],bounds=[LO,HI])
    print('Graded roads',int(active.sum()),'fixtures preserved',len(held),'voxel changes',len(changed),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
