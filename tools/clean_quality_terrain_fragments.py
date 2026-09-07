"""Remove measured legacy soil above the target grade in old protection fringes.

The main terrain field already handled unprotected ground. This narrow pass
only visits old rail/station/airport protection masks and only removes soil
states above the intended ground, retaining all constructed blocks and parks.
"""
import json,argparse
import numpy as np
import regional_voxels as vox
from quality_structures import Builder,OUT,load

def build():
    a=np.load(OUT/'terrain_target.npz');heights=a['height'];ox,oz=map(int,a['origin']);maximum=np.zeros(heights.shape,dtype=np.int16)
    for box in load(OUT/'terrain_repair/protected.json'):
        owner=box['owner']
        if not owner.startswith(('station/','native_rail/','airport_')):continue
        x0,y0,z0,x1,y1,z1=box['box'];x0=max(0,x0-ox);x1=min(heights.shape[1]-1,x1-ox);z0=max(0,z0-oz);z1=min(heights.shape[0]-1,z1-oz)
        if x0>x1 or z0>z1:continue
        v=maximum[z0:z1+1,x0:x1+1];np.maximum(v,y1,out=v)
    active=maximum>heights
    vox.OUT=OUT;p=Builder()
    for name,box in [('core',(-210,32,-20,270,255,464)),('EVA',(-65,32,-175,195,255,20)),('gateway',(-420,32,700,-292,110,819))]:p.protect(box,name)
    for b in load(OUT/'surface_layout.json')['kept_plots']:
        x0,x1,z0,z1=b['bounds'];f=b['floor'];p.protect((x0,f,z0,x1,f+b.get('storeys',3)*5+8,z1),b['id'])
    for iz in range(heights.shape[0]):
        xs=np.flatnonzero(active[iz]);i=0
        while i<len(xs):
            ix=int(xs[i]);lo=int(heights[iz,ix])+1;hi=int(maximum[iz,ix]);j=i+1
            while j<len(xs) and xs[j]==xs[j-1]+1 and heights[iz,xs[j]]+1==lo and maximum[iz,xs[j]]==hi:j+=1
            p.fill(ox+ix,lo,oz+iz,ox+int(xs[j-1]),hi,oz+iz,'minecraft:air','legacy_soil_fringe','ground_clear');i=j
    return p

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args();p=build()
    p.apply('soil_fringe_cleanup') if args.apply else p.save_plan('soil_fringe_cleanup')
