"""Close maintenance-only platform ends and pave their public side frontages."""
import regional_voxels as vox
from quality_structures import Builder,Station,OUT,OLD,load
from regional_architecture import FLOOR,GLASS

def build():
    vox.OUT=OUT;p=Builder()
    for d in load(OLD/'transit_plan.json')['platforms']:
        if d.get('mode')=='AIRPLANE':continue
        s=Station(p,d);r=s.y;h=s.half
        for u in (-h,h):
            for a,b in [(-15,-4),(4,15)]:s.fill(u,r+1,a,u,r+2,b,GLASS)
        if r>=75:
            for a,b in [(-17,-16),(16,17)]:s.fill(-h+8,r,a,h-8,r,b,FLOOR)
    return p

if __name__=='__main__':build().apply('station_frontages')
