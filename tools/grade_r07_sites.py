"""Engineer surveyed pads while preserving water outside the reclamation boundary."""
import argparse,json
import numpy as np
from regional_voxels import ROOT
import regional_voxels as vox

OUT=ROOT/'artifacts/world_expansion_r07'
PADS={'base':[(6320,-6704,6879,-5952,74),(6344,-6336,6575,-6080,76)],
      'port':[(1224,320,1399,568,68),(1400,336,1424,568,64)]}

def main(area,apply=False):
    source=OUT/'survey'/(area+'.npz');data=np.load(source);lo=data['lo'];hi=data['hi'];top=data['top'];water=data['water'];zz,xx=np.indices(top.shape);xx+=lo[0];zz+=lo[2]
    desired=top.copy();active=np.zeros(top.shape,bool)
    for x0,z0,x1,z1,floor in PADS[area]:
        distance=np.hypot(np.maximum.reduce([x0-xx,np.zeros(xx.shape),xx-x1]),np.maximum.reduce([z0-zz,np.zeros(zz.shape),zz-z1]))
        core=distance==0;blend=(distance<24)&(~water|active)
        mask=core|blend;t=np.clip(distance/24,0,1);t=t*t*(3-2*t)
        target=np.rint(floor*(1-t)+desired*t).astype(int);desired[mask]=target[mask];active|=mask
    # Port apron and yard meet across an intentional four-block height change;
    # short full-width ramps will be authored with the circulation plan.
    vox.OUT=OUT;p=vox.Painter()
    for cz in range(int(lo[2])//16,int(hi[2])//16+1):
        for cx in range(int(lo[0])//16,int(hi[0])//16+1):
            x=cx*16-lo[0];z=cz*16-lo[2];a=active[z:z+16,x:x+16]
            if a.shape!=(16,16) or not a.any():continue
            p.heightfield(cx,cz,desired[z:z+16,x:x+16],a,'r07/'+area+'/graded_pad')
    p.meta.update(pads=PADS[area],measured_source=str(source),preserved_water_outside_core=True,
                  columns=int(active.sum()),maximum_grade_change=int(np.max(np.abs(desired[active]-top[active]))))
    p.apply(area+'_grading') if apply else p.save_plan(area+'_grading')
    np.savez_compressed(OUT/(area+'_grading.npz'),before_top=top,desired_top=desired,active=active,lo=lo,hi=hi)
    print('Engineered pad',area,int(active.sum()),flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('area',choices=PADS);ap.add_argument('--apply',action='store_true');a=ap.parse_args();main(a.area,a.apply)
