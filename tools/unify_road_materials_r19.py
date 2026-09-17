"""Make graded half-height road surfaces use the same materials as full blocks.

Only measured road-mask floor cells are retinted; all heights, supporting
terrain and overhead objects remain untouched.
"""
import argparse,json
from collections import Counter,defaultdict
import numpy as np
import regional_voxels as vox
from query_blocks import iter_selected_sections

OUT=vox.ROOT/'artifacts/world_repair_r19/road_materials'

def resources():
    root=vox.ROOT/'src/main/resources/assets/projectseele'
    for key,color in [('road_asphalt_slab','black'),('road_marking_slab','white')]:
        variants={}
        for typ,parent in [('bottom','slab'),('top','slab_top'),('double','cube_all')]:
            name=key+('_'+typ if typ!='bottom' else '')
            textures={s:'minecraft:block/'+color+'_concrete' for s in (['all'] if typ=='double' else ['bottom','top','side'])}
            (root/'models/block'/f'{name}.json').write_text(json.dumps({'parent':'minecraft:block/'+parent,'textures':textures},indent=2)+'\n')
            variants['type='+typ]={'model':'projectseele:block/'+name}
        (root/'blockstates'/f'{key}.json').write_text(json.dumps({'variants':variants},indent=2)+'\n')
        (root/'models/item'/f'{key}.json').write_text(json.dumps({'parent':'projectseele:block/'+key})+'\n')
    for lang,labels in [('zh_cn',('沥青路面半砖','道路标线半砖')),('en_us',('Asphalt road slab','Road marking slab'))]:
        p=root/'lang'/f'{lang}.json';d=json.loads(p.read_text(encoding='utf8'))
        for key,label in zip(('road_asphalt_slab','road_marking_slab'),labels):d['block.projectseele.'+key]=label
        p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def main(apply=False):
    resources();vox.OUT=OUT;p=vox.Painter();stats=Counter();points=defaultdict(set)
    base=vox.ROOT/'artifacts/world_quality_r02'
    for name in ('road_surfaces.npz','extension_road_surfaces.npz'):
        a=np.load(base/name);h=a['height2'].copy();mask=a['mask'];ox,oz=map(int,a['origin'])
        if name=='road_surfaces.npz':
            for folder in ('C1_street_grade','rail_street_crossings_v2'):
                d=np.load(OUT.parent/'roads'/folder/'surface_contract.npz');px,pz=map(int,d['origin']);hh=d['after'];mm=d['mask']
                target=h[pz-oz:pz-oz+hh.shape[0],px-ox:px-ox+hh.shape[1]];target[mm]=hh[mm]
        for iz,ix in np.argwhere(mask):
            x,z=int(ix+ox),int(iz+oz);y=(int(h[iz,ix])-1)//2;points[x//16,z//16,y//16].add((x,y,z))
    selected=defaultdict(set)
    for cx,cz,sy in points:selected[cx,cz].add(sy)
    for cx,cz,sy,pal,idx in iter_selected_sections(vox.WORLD,vox.DIM,selected):
        for x,y,z in points[cx,cz,sy]:
            s=pal[int(idx[((y&15)<<8)|((z&15)<<4)|(x&15)])];base=s.split('[')[0];after=None
            if base=='minecraft:polished_blackstone_slab':after=s.replace(base,'projectseele:road_asphalt_slab')
            elif base=='minecraft:quartz_slab':after=s.replace(base,'projectseele:road_marking_slab')
            elif base=='minecraft:polished_blackstone':after='minecraft:black_concrete'
            if after:p.match((x,y,z,x,y,z),s,after,'r19/continuous_road_surface_material');stats[base]+=1
    p.meta.update(replaced=dict(stats),floor_heights_unchanged=True,road_mask_only=True,shape_and_waterlogging_preserved=True)
    p.apply('continuous_asphalt_and_markings') if apply else p.save_plan('continuous_asphalt_and_markings')
    print(dict(stats))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--apply',action='store_true');main(a.parse_args().apply)
