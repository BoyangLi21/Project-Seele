"""Use the existing asphalt slab on the actual graded R20 road surfaces."""
from collections import defaultdict,Counter
import numpy as np
import regional_voxels as v
from query_blocks import iter_selected_sections
OUT=v.ROOT/'artifacts/world_rebuild_r20/road_actual';REVIEW=v.ROOT/'run/saves/SEELE_R20_REVIEW'

def main():
    def arrays(path):
        with np.load(path) as f:return {k:f[k] for k in f.files}
    primary=arrays(OUT/'road_contract_final.npz');extension=arrays(v.ROOT/'artifacts/world_quality_r02/extension_road_surfaces.npz')
    px,pz=map(int,primary['origin']);ex,ez=map(int,extension['origin']);h=extension['height2'];mask=extension['mask']
    for z,x in np.argwhere(mask):
        xx,zz=int(x+ex-px),int(z+ez-pz)
        if 0<=zz<primary['mask'].shape[0] and 0<=xx<primary['mask'].shape[1] and primary['mask'][zz,xx]:h[z,x]=primary['height2'][zz,xx]
    np.savez_compressed(OUT/'extension_contract_final.npz',**extension)
    points=defaultdict(set);selected=defaultdict(set)
    for a in (primary,extension):
        ox,oz=map(int,a['origin'])
        for z,x in np.argwhere(a['mask']):
            X,Z=int(x+ox),int(z+oz);Y=(int(a['height2'][z,x])-1)//2;points[X//16,Z//16,Y//16].add((X,Y,Z));selected[X//16,Z//16].add(Y//16)
    v.OUT=OUT;p=v.Painter();stats=Counter()
    for cx,cz,sy,pal,idx in iter_selected_sections(REVIEW,v.DIM,selected):
        for x,y,z in points[cx,cz,sy]:
            before=pal[int(idx[((y&15)<<8)|((z&15)<<4)|(x&15)])];name=before.split('[')[0];after=None
            if name=='minecraft:polished_blackstone_slab':after=before.replace(name,'projectseele:road_asphalt_slab')
            elif name=='minecraft:quartz_slab':after=before.replace(name,'projectseele:road_marking_slab')
            if after:p.match((x,y,z,x,y,z),before,after,'r20/continuous_asphalt_finish');stats[name]+=1
    p.meta.update(replaced=dict(stats),shape_and_height_unchanged=True,primary_and_extension_roads=True);p.save_plan('continuous_asphalt_finish');print(dict(stats))

if __name__=='__main__':main()
