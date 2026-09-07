"""Physical envelopes for the already validated native commuter rail geometry."""
import argparse,json,math
from collections import Counter
import numpy as np
import regional_voxels as vox
from quality_structures import Builder,OUT,load
from regional_architecture import AIR,DARK,WALL,LIGHT,STEEL

def build():
    a=np.load(OUT/'surface_levels_extension_before.npz');base=a['height'];known=a['known'];ox,oz=map(int,a['origin']);p=Builder();counts=Counter();clear=[];lights=[]
    plots=load(OUT/'surface_layout.json')['kept_plots']
    for rail in load(OUT/'estate_transit_draft/track_samples.json'):
        owner='rail/'+rail['id'];seen=set()
        for i,point in enumerate(rail['points']):
            x,y,z=map(round,point)
            if (x,y,z) in seen:continue
            seen.add((x,y,z));ix,iz=x-ox,z-oz
            if not 0<=iz<base.shape[0] or not 0<=ix<base.shape[1] or not known[iz,ix] or base[iz,ix]<32:raise RuntimeError('Unknown rail ground '+str((x,y,z)))
            for b in plots:
                x0,x1,z0,z1=b['bounds']
                if x0-2<=x<=x1+2 and z0-2<=z<=z1+2 and b['floor']-2<=y+5 and b['floor']+b.get('storeys',1)*5>=y:raise RuntimeError('Rail intersects retained building '+b['id'])
            ground=int(base[iz,ix]);city=rail['id'] in ('S2_city_street','S2_hakone','S2_terminal_buffer') and x>=-1880
            material='minecraft:black_concrete' if city else DARK
            p.fill(x-3,y-3,z-3,x+3,y-1,z+3,material,owner)
            if ground>y+6 and not city:
                p.fill(x-4,y-3,z-4,x+4,y+7,z+4,WALL,owner+'/tunnel');counts['tunnel_samples']+=1
                if i%16==0:lights.append((x,y+6,z))
            elif ground<y-4:
                counts['bridge_samples']+=1
                if i%24==0:
                    p.fill(x,ground+1,z,x,y-4,z,'minecraft:polished_basalt[axis=y]',owner+'/pier')
                    p.fill(x-3,y-3,z-3,x+3,y-3,z+3,STEEL,owner+'/beam')
                previous=rail['points'][max(0,i-1)];following=rail['points'][min(len(rail['points'])-1,i+1)]
                dx,dz=following[0]-previous[0],following[2]-previous[2];length=max(.001,math.hypot(dx,dz))
                for side in (-4,4):
                    xx,zz=round(x-dz/length*side),round(z+dx/length*side)
                    p.fill(xx,y,zz,xx,y+1,zz,'minecraft:iron_bars[east=true,north=true,south=true,waterlogged=false,west=true]',owner+'/bridge_guard')
            clear.append((x-2,y,z-2,x+2,y+5,z+2))
        counts['native_rails']+=1
    # Car bodies, including bends, are a union cut after every lining and pier.
    for box in clear:p.fill(*box,AIR,'S2/continuous_vehicle_space')
    for x,y,z in lights:p.put(x,y,z,LIGHT,'S2/tunnel_lighting')
    p.meta['physical_rail_envelope']=dict(counts);vox.OUT=OUT
    return p

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args();p=build()
    p.apply('estate_track_envelopes') if args.apply else p.save_plan('estate_track_envelopes')
