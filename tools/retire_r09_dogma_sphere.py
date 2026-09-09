"""Retire the old ellipsoid cap and obsolete x72 protection while retaining the real x9 lift."""
import argparse,json
from collections import Counter
import numpy as np
import regional_voxels as v
import refine_eva_world_r04 as old
from query_blocks import AIR,iter_block_entities
OUT=v.ROOT/'artifacts/world_refinement_r09';v.OUT=OUT
KEEP=[(8,-569,249,16,-400,257),(8,-569,257,16,-560,258)]
def held(x,y,z):return any(a<=x<=d and b<=y<=e and c<=z<=f for a,b,c,d,e,f in KEEP)
def main(apply=False):
    d=np.load(OUT/'dogma_before.npz');a=d['blocks'];pal=d['palette'];lo=d['lo'];hi=d['hi'];p=v.Painter();counts=Counter()
    # Reconstruct the documented R04 intention without the obsolete x72 non-elevator keep-out.
    authored=v.Painter();old.dogma(authored);old.junctions(authored)
    expected=np.full(a.shape,65535,np.uint16);names=[];codes={}
    for op in authored.ops:
        x0,y0,z0,x1,y1,z1=op.box;x0=max(x0,int(lo[0]));y0=max(y0,int(lo[1]));z0=max(z0,int(lo[2]));x1=min(x1,int(hi[0]));y1=min(y1,int(hi[1]));z1=min(z1,int(hi[2]))
        if x0>x1 or y0>y1 or z0>z1:continue
        if op.state not in codes:codes[op.state]=len(names);names.append(op.state)
        expected[y0-lo[1]:y1-lo[1]+1,z0-lo[2]:z1-lo[2]+1,x0-lo[0]:x1-lo[0]+1]=codes[op.state]
    y,z,x=np.ogrid[lo[1]:hi[1]+1,lo[2]:hi[2]+1,lo[0]:hi[0]+1]
    radius=((x-30)/40)**2+((y+574)/44)**2+((z-296)/48)**2
    north_cap=(z<265)&(radius<=1.30)
    obsolete_keep=(x>=66)&(x<=79)&(z>=266)&(z<=281)
    wall_and_entry=(z<=267)&(expected!=65535)
    for iy,iz,ix in np.argwhere(north_cap|obsolete_keep|wall_and_entry):
        xx,yy,zz=int(ix+lo[0]),int(iy+lo[1]),int(iz+lo[2]);before=str(pal[a[iy,iz,ix]])
        if held(xx,yy,zz):continue
        wanted=int(expected[iy,iz,ix]);after=names[wanted] if wanted!=65535 else ('minecraft:deepslate' if yy<=-576 else 'minecraft:stone')
        if before==after:continue
        if before.startswith('movingelevators:'):raise RuntimeError(('Active lift outside surveyed keep-out',xx,yy,zz))
        p.match((xx,yy,zz,xx,yy,zz),before,after,'r09/retire_old_dogma_sphere')
        counts['cells']+=1
        if before.split('[')[0] in ('minecraft:deepslate_bricks','minecraft:polished_basalt'):counts['old_shell_blocks']+=1
        if after in AIR:counts['open_chamber_cells']+=1
        if after=='projectseele:lcl[level=0]':counts['restored_lcl_cells']+=1
    # New block entities are used only when a recreated authored fixture owns the cell.
    for pos,tag in authored.block_entities.items():
        xx,yy,zz=pos
        if lo[0]<=xx<=hi[0] and lo[1]<=yy<=hi[1] and lo[2]<=zz<=hi[2] and not held(xx,yy,zz):
            if zz<=267 or 66<=xx<=79 and 266<=zz<=281:p.block_entities[pos]=tag
    p.meta.update(counts=dict(counts),retained_native_lift=dict(controller=[9,-566,253],boxes=KEEP),retired_sphere=dict(centre=[30,-574,296],radii=[40,44,48]),obsolete_keep_out=[66,-630,266,79,-529,281],evidence='Actual elevator groups contain 9;253 and no x72/z273 group; no block entity exists in the retired x72 box',lilith_and_current_lake_preserved=True)
    p.apply('dogma_sphere_retirement') if apply else p.save_plan('dogma_sphere_retirement')
    (OUT/'dogma_plan.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print(dict(counts),flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
