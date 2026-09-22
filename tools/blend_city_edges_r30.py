"""Broaden steep artificial grading seams without moving cities, roads or railways."""
from pathlib import Path
import argparse,json,math
import numpy as np
from scipy.ndimage import gaussian_filter,distance_transform_edt,maximum_filter,minimum_filter,binary_dilation
from scipy.spatial import cKDTree
import regional_voxels as v

ROOT=v.ROOT;BASE=ROOT/'run/saves/SEELE_R30_WORLD';WORLD=ROOT/'run/saves/SEELE_FIELD_R30_REVIEW';OUT=ROOT/'artifacts/facility_r30/city_edge_grading'
NAMES=['tokyo_west_edge','tokyo_north_edge','tokyo_south_edge','hakone_east_edge','hakone_west_edge','city_connector','nerv_airport_edge']
def main(apply):
    v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();native=json.loads((BASE/'native_transit_r26.json').read_text());rail=[];plane=[];paths=[]
    for c in native['curves']:
        (rail if c['mode']=='TRAIN' else plane).extend(c['points'])
    for c in json.loads((BASE/'quality_walk_cases.json').read_text()):
        a=c.get('path') or [c.get('start'),c.get('end')]
        if not all(q is not None for q in a):continue
        for aa,bb in zip(a,a[1:]):
            aa,bb=np.array(aa),np.array(bb)
            if min(aa[1],bb[1])<32:continue
            paths.extend(np.linspace(aa,bb,max(2,math.ceil(np.linalg.norm(bb-aa)/2)+1)))
    rail=np.asarray(rail);plane=np.asarray(plane);paths=np.asarray(paths)
    rails=cKDTree(rail[:,[0,2]]);planes=cKDTree(plane[:,[0,2]]);walk=cKDTree(paths[:,[0,2]]);done=set();plans=[]
    OUT.mkdir(parents=True,exist_ok=True)
    for name in NAMES:
        d=np.load(OUT.parent/'landscape/survey'/f'{name}.npz');lo,hi=d['lo'],d['hi'];g=d['ground'].astype(float);valid=d['known']&(g>lo[1]+3)
        _,nearest=distance_transform_edt(~valid,return_indices=True);h=np.where(valid,g,g[tuple(nearest)])
        built=d['engineered']>=g;dist=distance_transform_edt(~built);trees=binary_dilation(d['vegetation']>g,iterations=4)
        smooth=gaussian_filter(h,10);steep=(maximum_filter(h,5)-minimum_filter(h,5))>=7;zone=binary_dilation(steep,iterations=18)
        feather=np.clip((dist-6)/12,0,1)*np.clip((88-dist)/24,0,1);target=np.rint(h+np.clip(smooth-h,-18,18)*feather).astype(int)
        wet=d['water']>=g;shore,shore_index=distance_transform_edt(~wet,return_indices=True)
        if wet.any():target=np.maximum(target,np.where(shore<20,np.minimum(g,d['water'][tuple(shore_index)]+1),target)).astype(int)
        active=valid&zone&(dist>6)&(dist<88)&~trees&(shore>2)&(d['water']<g)
        active[:20]=False;active[-20:]=False;active[:,:20]=False;active[:,-20:]=False
        iz,ix=np.where(active);world=np.c_[ix+lo[0]+.5,iz+lo[2]+.5]
        rd,ri=rails.query(world);ad,ai=planes.query(world);wd,wi=walk.query(world);tops=np.maximum(g[iz,ix],target[iz,ix])
        # A high viaduct is not a 2D prohibition on landscaping the ground far
        # below it. Keep actual pier columns and a real vertical safety margin.
        safe=((rd>12)|(tops<rail[ri,1]-8))&((ad>38)|(tops<plane[ai,1]-8))&((wd>5)|(tops<paths[wi,1]-4))
        for n,(x,z) in enumerate(world):
            if -234<=x<=294 and -44<=z<=488:safe[n]=False
            q=(int(math.floor(x)),int(math.floor(z)))
            if q in done:safe[n]=False
            if safe[n]:done.add(q)
        active[iz[~safe],ix[~safe]]=False
        # Feather to unchanged natural neighbours so the patch has no new hard rim.
        distance=distance_transform_edt(active);blend=np.clip(distance/6,0,1);target=np.rint(g+(target-g)*blend).astype(int);active&=target!=g
        for cz in range(int(lo[2])//16,int(hi[2])//16+1):
            for cx in range(int(lo[0])//16,int(hi[0])//16+1):
                zz,xx=np.mgrid[cz*16:cz*16+16,cx*16:cx*16+16];rz,rx=zz-lo[2],xx-lo[0];inside=(rx>=0)&(rx<g.shape[1])&(rz>=0)&(rz<g.shape[0]);mask=np.zeros((16,16),bool);heights=np.zeros((16,16),int)
                mask[inside]=active[rz[inside],rx[inside]];heights[inside]=target[rz[inside],rx[inside]]
                if mask.any():p.heightfield(cx,cz,heights,mask,'r30/'+name+'/softened_civil_grade',clear_vegetation=mask)
        np.savez_compressed(OUT/(name+'.npz'),lo=lo,before=g,after=np.where(active,target,g),active=active)
        plans.append({'area':name,'changed_columns':int(active.sum()),'maximum_delta':int(np.max(abs(target[active]-g[active]))) if active.any() else 0,'preserved':'constructed columns+6m, trees+4m, water and first2m of banks; no lowering below adjacent waterline; rails12m/8m vertical, aircraft38m/8m vertical, public walking5m/4m vertical; accepted retractable core24m'})
        print(name,plans[-1]['changed_columns'],'columns',flush=True)
    p.meta.update(areas=plans,existing_cities_and_transit_not_moved=True);p.save_plan('soften_artificial_city_edges')
    if apply:p.apply('soften_artificial_city_edges')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
