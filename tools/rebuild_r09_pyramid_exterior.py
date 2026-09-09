"""Retire the nominated east decks, preserve working interfaces, repair and paint the same pyramid."""
import argparse,json,math
from collections import Counter
import numpy as np
import nbtlib
from PIL import Image
from scipy.ndimage import label,find_objects
import regional_voxels as v
from query_blocks import AIR
from scan_regional_completion import volume
OUT=v.ROOT/'artifacts/world_refinement_r09';v.OUT=OUT
PANEL='projectseele:nerv_pyramid_panel';MARK='projectseele:nerv_pyramid_marking'
KEEP=[(111,-470,190,125,-430,267),(125,-450,265,137,90,281),(114,-446,267,137,-437,279),
      (136,-467,395,201,-454,404),(173,-478,190,230,-430,281)]
def protected(x,y,z):return any(a<=x<=d and b<=y<=e and c<=z<=f for a,b,c,d,e,f in KEEP)
def radius(y):return math.floor(120*(1-(y+466)/172)+.5)
def inside(x,y,z):return -466<=y<=-294 and max(abs(x-30),abs(z-327))<=radius(y)
def main(apply=False):
    p=v.Painter();counts=Counter()
    # Measured active interfaces: long hangar corridor, existing lift, and research bridge.
    d=np.load(OUT/'platform_before.npz');a=d['blocks'];pal=d['palette'];lo=d['lo'];columns=set()
    for iy,iz,ix in np.argwhere(np.array([s not in AIR for s in pal])[a]):
        x,y,z=int(ix+lo[0]),int(iy+lo[1]),int(iz+lo[2]);state=str(pal[a[iy,iz,ix]])
        upper=136<=x<=159 and -453<=y<=-437 and 263<=z<=403
        lower=151<=x<=159 and -466<=y<=-450 and 207<=z<=403
        if not(upper or lower) or inside(x,y,z) or protected(x,y,z):continue
        if state.startswith(('movingelevators:','mtr:')):raise RuntimeError(('Unexpected transport in retirement',x,y,z,state))
        p.match((x,y,z,x,y,z),state,'minecraft:air','r09/retire_old_east_platform');counts['platform_cells']+=1
        if y==-466:columns.add((x,z))
    # The former lower apron is lowered to the existing adjacent ground datum, not left as a void.
    for x,z in sorted(columns):
        old=str(pal[a[-467-lo[1],z-lo[2],x-lo[0]]])
        if old.split('[')[0] in ('minecraft:stone','minecraft:dirt','minecraft:reinforced_deepslate','minecraft:polished_deepslate'):
            p.match((x,-467,z,x,-467,z),old,'minecraft:grass_block[snowy=false]','r09/restore_ground_surface');counts['ground_columns']+=1
    d=np.load(OUT/'pyramid_before.npz');a=d['blocks'];pal=d['palette'];lo=d['lo'];hi=d['hi'];y,z,x=np.ogrid[lo[1]:hi[1]+1,lo[2]:hi[2]+1,lo[0]:hi[0]+1]
    r=np.floor(120*(1-(y+466)/172)+.5);ring=(y>=-466)&(y<=-294)&(abs(x-30)<=r)&(abs(z-327)<=r)&((abs(x-30)==r)|(abs(z-327)==r))
    for iy,iz,ix in np.argwhere(ring):
        xx,yy,zz=int(ix+lo[0]),int(iy+lo[1]),int(iz+lo[2]);old=str(pal[a[iy,iz,ix]])
        # Active lower entrance, north route, lift and research passage remain open.
        if protected(xx,yy,zz) or (25<=xx<=35 and -466<=yy<=-457 and zz>=439):continue
        if old.startswith('projectseele:one_way_glass'):
            facing=old.split('facing=')[1].split(',')[0].split(']')[0];new=f'projectseele:one_way_glass[facing={facing},pyramid=true]'
            p.match((xx,yy,zz,xx,yy,zz),old,new,'r09/view_glass')
            p.block_entities[xx,yy,zz]=nbtlib.Compound({'id':nbtlib.String('projectseele:one_way_glass'),'x':nbtlib.Int(xx),'y':nbtlib.Int(yy),'z':nbtlib.Int(zz)})
            counts['directional_panes']+=1
        elif old in AIR:
            # The only unprogrammed opening is the old raised south entrance.
            if 26<=xx<=34 and -442<=yy<=-436 and 426<=zz<=431:
                p.match((xx,yy,zz,xx,yy,zz),old,PANEL,'r09/retire_upper_south_opening');counts['old_opening_closed']+=1
            else:raise RuntimeError(('Unclassified shell opening',xx,yy,zz))
        else:
            if old.startswith(('mtr:','movingelevators:')):raise RuntimeError(('Active hardware in shell paint',xx,yy,zz,old))
            p.match((xx,yy,zz,xx,yy,zz),old,PANEL,'r09/uniform_pyramid_coat');counts['coated_skin']+=1
    # Keep the existing tip geometry; change only its nonfunctional finish.
    for yy in range(-293,-285):
        old=str(pal[a[yy-lo[1],327-lo[2],30-lo[0]]])
        if old not in AIR and old.split('[')[0] in ('minecraft:chiseled_deepslate','minecraft:polished_blackstone','minecraft:reinforced_deepslate','minecraft:crying_obsidian','minecraft:red_concrete'):
            p.match((30,yy,327,30,yy,327),old,PANEL,'r09/tip_finish')
    # Use the already-installed classic TV logo as local input; the motto is omitted at voxel scale.
    source=v.ROOT/'run/projectseele-local-maps/nerv_logo.png';image=np.asarray(Image.open(source).convert('RGB'))
    red=(image[:,:,0]>140)&(image[:,:,1]<90)&(image[:,:,2]<90);components,n=label(red);keep=np.zeros(red.shape,bool)
    for i,b in enumerate(find_objects(components),1):
        if b[0].stop-b[0].start>red.shape[0]*.1:keep|=components==i
    pts=np.argwhere(keep);mn=pts.min(0);mx=pts.max(0)+1;mask=Image.fromarray(keep[mn[0]:mx[0],mn[1]:mx[1]].astype('uint8')*255)
    target_h=72;target_w=round(target_h*mask.width/mask.height);mask=np.asarray(mask.resize((target_w,target_h),Image.Resampling.LANCZOS))>112
    for row,col in np.argwhere(mask):
        yy=-335-int(row);xx=30+int(col)-target_w//2;zz=327+radius(yy)
        if abs(xx-30)>radius(yy):raise RuntimeError('Logo exceeds unchanged pyramid silhouette')
        p.put(xx,yy,zz,MARK,'r09/classic_nerv_facade_mark','owned');counts['logo_pixels']+=1
    p.meta.update(counts=dict(counts),preserved_interfaces=KEEP,shape=dict(centre=[30,327],base=-466,apex=-294,half_width=120),logo=dict(local_source=str(source),face='south',height=target_h,width=target_w,classic_tv_emblem=True,motto_omitted_at_voxel_scale=True),shape_unchanged=True)
    p.apply('pyramid_exterior') if apply else p.save_plan('pyramid_exterior')
    (OUT/'pyramid_plan.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print(dict(counts),flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
