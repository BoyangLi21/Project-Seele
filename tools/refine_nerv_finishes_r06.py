"""Apply restrained TV/Japanese finishes to measured, named architecture only."""
import argparse,json
from pathlib import Path
import numpy as np
import regional_voxels as vox
from scan_regional_completion import volume
from quality_structures import Station,ground_ports

ROOT=vox.ROOT;OUT=ROOT/'artifacts/world_motion_r06'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
PANEL='projectseele:nerv_wall_panel';DATUM='projectseele:nerv_wall_datum';FLOOR='projectseele:nerv_floor_panel';LAMP='projectseele:nerv_strip_light'
def replace(p,box,mapping,owner):
    for old,new in mapping.items():p.match(box,old,new,owner)
def pyramid(p):
    data=np.load(OUT/'pyramid_envelope.npz');lo=data['lo'];hi=data['hi'];spaces=data['spaces'];held=data['held']
    from scipy.ndimage import binary_dilation
    reach=binary_dilation(spaces,iterations=1)&~held
    current,palette=volume(lo,hi)
    mapping={'minecraft:light_gray_concrete':PANEL,'minecraft:red_terracotta':DATUM,
             'minecraft:smooth_stone':FLOOR,'minecraft:sea_lantern':LAMP}
    for before,after in mapping.items():
        codes=[i for i,state in enumerate(palette) if state==before]
        if not codes:continue
        mask=reach&np.isin(current,codes)
        for y,z in np.argwhere(mask.any(axis=2)):
            xs=np.flatnonzero(mask[y,z]);starts=np.r_[0,np.flatnonzero(np.diff(xs)>1)+1];ends=np.r_[starts[1:]-1,len(xs)-1]
            for a,b in zip(starts,ends):p.match((int(xs[a]+lo[0]),int(y+lo[1]),int(z+lo[2]),int(xs[b]+lo[0]),int(y+lo[1]),int(z+lo[2])),before,after,'r06/pyramid/finish')
    for room in load(ROOT/'artifacts/world_motion_r04/pyramid/places.json')['rooms']:
        x,y,z=room['entry'];x0,x1,z0,z1=room['bounds'];f=room['floor']
        if x in (x0,x1):box=(x,f,z-1,x,f,z+1)
        else:box=(x-1,f,z,x+1,f,z)
        replace(p,box,{'minecraft:smooth_stone':'projectseele:nerv_hazard_paving'},'r06/pyramid/threshold')
    p.meta['pyramid_rooms']=34
def stations(p):
    old=ROOT/'artifacts/world_expansion_20260907';r02=ROOT/'artifacts/world_quality_r02'
    platforms=[d for d in load(old/'transit_plan.json')['platforms'] if d.get('mode')!='AIRPLANE']+load(r02/'extension_plan.json')['transit']['platforms']
    for d in platforms:
        s=Station(p,d);y=s.y;h=s.half;side=10 if d.get('compact') else 15;owner='r06/'+s.owner
        a=s.xyz(-h,y,-side);b=s.xyz(h,y+13,side)
        replace(p,(*a,*b),{'minecraft:sea_lantern':LAMP,'minecraft:smooth_stone':FLOOR},owner+'/base')
        if y<0:replace(p,(*a,*b),{'minecraft:light_gray_concrete':PANEL,'minecraft:red_terracotta':DATUM},owner+'/interior')
        for v in (-3,3):
            replace(p,(*s.xyz(-h+5,y,v),*s.xyz(h-5,y,v)),{'minecraft:yellow_terracotta':'projectseele:station_tactile_warning'},owner+'/edge')
        for v in (-4,4):replace(p,(*s.xyz(-h+5,y,v),*s.xyz(h-5,y,v)),{'minecraft:yellow_terracotta':FLOOR},owner+'/edge_width')
        heading='east' if s.horizontal else 'north'
        for v in (-7,7):
            for u0,u1 in [(-h+6,-27),(11,h-6)]:
                if u1<u0:continue
                replace(p,(*s.xyz(u0,y,v),*s.xyz(u1,y,v)),{'minecraft:smooth_stone':f'projectseele:station_tactile_path[facing={heading}]'},owner+'/guide')
        cross='north' if s.horizontal else 'east'
        replace(p,(*s.xyz(-9,y+6,-13),*s.xyz(-9,y+6,13)),{'minecraft:smooth_stone':f'projectseele:station_tactile_path[facing={cross}]'},owner+'/bridge_guide')
        for sign in ground_ports(d):
            v0,v1=sorted((sign*7,sign*(side-1)))
            replace(p,(*s.xyz(0,y,v0),*s.xyz(0,y,v1)),{'minecraft:smooth_stone':f'projectseele:station_tactile_path[facing={cross}]'},owner+'/exit_guide')
    p.meta['station_platforms']=len(platforms)
def airports(p):
    for name,sx,rz in [('bay',740,1430),('hakone',-1670,-20)]:
        z0=rz-380;owner='r06/airport/'+name
        replace(p,(sx-104,77,z0-12,sx+104,102,z0+80),{'minecraft:smooth_stone':FLOOR,'minecraft:sea_lantern':LAMP},owner+'/finish')
        replace(p,(sx-1,80,z0-10,sx+1,80,z0+68),{'minecraft:polished_deepslate':FLOOR},owner+'/aisle')
        replace(p,(sx,80,z0-10,sx,80,z0+68),{'minecraft:smooth_stone':'projectseele:station_tactile_path[facing=north]',
                 'minecraft:polished_deepslate':'projectseele:station_tactile_path[facing=north]'},owner+'/guide')
        for z in (z0-1,z0+1):
            replace(p,(sx-3,80,z,sx+3,80,z),{'minecraft:smooth_stone':'projectseele:station_tactile_warning'},owner+'/entrance_warning')
    p.meta['airports']=2
def main(part,apply):
    vox.OUT=OUT;p=vox.Painter();{'pyramid':pyramid,'stations':stations,'airports':airports}[part](p)
    p.meta['style']='Measured TV corridor palette, flush tactile markings, warm recessed luminaires'
    p.apply('finishes_'+part) if apply else p.save_plan('finishes_'+part)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('part',choices=['pyramid','stations','airports']);ap.add_argument('--apply',action='store_true');a=ap.parse_args();main(a.part,a.apply)
