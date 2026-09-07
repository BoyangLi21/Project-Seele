"""One continuous terrain field replaces overlapping parcel-by-parcel grading.

Original core city, launch mechanics, elevator shafts, railway clearance and
underground airport circulation are explicit protected volumes. The current
save is measured before writing and all changes use the shared reversible writer.
"""
from pathlib import Path
import argparse,gzip,json,math
import numpy as np
import regional_voxels as vox
from regional_voxels import Painter

ROOT=vox.ROOT;OLD=ROOT/'artifacts/world_expansion_20260907';OUT=ROOT/'artifacts/world_quality_r02'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))

def smooth(x):
    t=np.clip(x,0,1);return t*t*(3-2*t)

def tokyo_height(x,z):
    west=16*np.clip((-230-x)/490,0,1)
    north=smooth((z+194)/44)
    south=1-smooth((z-502)/28)*smooth((x+603)/41)
    return 80+west*north*south

def plots():
    data=load(OLD/'geometry_all/places.json')
    allplots=[p for p in data['landmarks'] if p.get('style') in ('office','residential','park')]
    removed=[p for p in allplots if p['id'].startswith('tokyo_west/') and p['bounds'][1]>-580 and p['bounds'][2]>=520]
    removed_ids={p['id'] for p in removed};kept=[p for p in allplots if p['id'] not in removed_ids]
    for i,a in enumerate(kept):
        for b in kept[i+1:]:
            x0,x1,z0,z1=a['bounds'];u0,u1,v0,v1=b['bounds']
            if max(x0,u0)<min(x1,u1) and max(z0,v0)<min(z1,v1):raise RuntimeError('Remaining building overlap '+a['id']+' / '+b['id'])
    return kept,removed

def protections(p,kept,transit,samples):
    # Core-city motion and both surface/underground elevator shafts are never terrain.
    for name,b in [('accepted_core',(-210,32,-20,270,255,464)),('EVA_sector',(-65,32,-175,195,255,20)),
                   ('gateway_shaft',(-369,32,741,-351,100,759)),('public_lift',(123,32,265,137,100,281))]:p.protect(b,name)
    for b in kept:
        x0,x1,z0,z1=b['bounds'];floor=b['floor'];height=b.get('storeys',2)*5+6
        p.protect((x0-1,floor,z0-1,x1+1,floor+height,z1+6),b['id'],('match','retire'))
    for platform in transit['platforms']:
        if platform.get('mode')=='AIRPLANE':continue
        x,y,z=platform['center'];half=platform['length']//2+11
        if y<0:continue
        a=platform['heading'] in ('E','W')
        b=(x-half,y-4,z-16,x+half,y+13,z+16) if a else (x-16,y-4,z-half,x+16,y+13,z+half)
        p.protect(b,'station/'+platform['id'])
    for rail in samples:
        if rail['mode']!='TRAIN':continue
        for x,y,z in {tuple(map(round,v)) for v in rail['points'][::2]}:
            if y>=0:p.protect((x-4,y-2,z-4,x+4,y+8,z+4),'native_rail/'+rail['id'])
    for sx,gx,rz,sz in [(740,650,1430,1190),(-1670,-1610,-20,-265)]:
        p.protect((sx-5,70,rz-310,sx+5,91,sz+5),'airport_terminal_access')
        p.protect((min(sx,gx)-5,70,rz-255,max(sx,gx)+5,77,rz-245),'airport_gate_crossing')
        p.protect((gx-5,70,rz-250,gx+5,91,rz-220),'airport_gate_stair')
    p.protect((-420,79,695,-292,103,819),'gateway_authored_halls',('match','retire'))

def build():
    current=np.load(OUT/'surface_levels_expanded_current.npz');reference=np.load(OUT/'surface_levels_reference.npz')
    current_height=current['height'];reference_height=reference['height']
    if not np.array_equal(current['origin'],reference['origin']) or current_height.shape!=reference_height.shape:raise RuntimeError('Height field frames differ')
    origin=current['origin'];base=np.where(reference_height>-32768,reference_height,current_height).astype(float)
    known=current['known'];base=np.where(base>-32768,base,64)
    nz,nx=base.shape;x=np.arange(nx)[None,:]+origin[0];z=np.arange(nz)[:,None]+origin[1]
    plan=load(OLD/'regional_plan.json');kept,removed=plots();sums=np.zeros(base.shape,dtype=np.float32);weights=np.zeros(base.shape,dtype=np.float32)
    footprints=[]
    for zone in plan['zones']:
        if zone['kind'] not in ('district','airport','gateway'):continue
        b=zone['bounds']
        if zone['id']=='hakone_airfield':b=[-2180,-1420,-415,95]
        if zone['id']=='bay_airport':b=[460,1220,1035,1530]
        a,bb,c,d=b;dist=np.hypot(np.maximum(np.maximum(a-x,x-bb),0),np.maximum(np.maximum(c-z,z-d),0))
        weight=1-smooth(dist/72)
        target=104 if zone['id']=='new_hakone' else 80 if zone['kind']!='district' else tokyo_height(x,z)
        sums+=weight*target;weights+=weight;footprints.append(b)
    for a,bb,c,d in [(-124,-108,-528,-20),(-119,-101,-36,4),(-768,-216,168,184),(-232,-216,168,208),(-232,-186,192,208)]:
        dist=np.hypot(np.maximum(np.maximum(a-x,x-bb),0),np.maximum(np.maximum(c-z,z-d),0));weight=1-smooth(dist/32)
        sums+=weight*tokyo_height(x,z);weights+=weight
    interior=weights>=.999;blend=np.clip(weights,0,1);desired=np.divide(sums,np.maximum(weights,.000001))
    target=base*(1-blend)+desired*blend
    # Keep each retained flat building/park plinth at its existing datum.
    pads=[]
    for station in load(OLD/'transit_plan.json')['platforms']:
        xx,yy,zz=station['center']
        if yy<75 or station.get('mode')=='AIRPLANE':continue
        half=station['length']//2+16;horizontal=station['heading'] in ('E','W')
        b=[xx-half,xx+half,zz-21,zz+21] if horizontal else [xx-21,xx+21,zz-half,zz+half]
        pads.append(dict(bounds=b,floor=yy))
    for b in pads+kept:
        a,bb,c,d=b['bounds'];margin=5
        ix0=max(0,a-margin-int(origin[0]));ix1=min(nx,bb+margin-int(origin[0])+1)
        iz0=max(0,c-margin-int(origin[1]));iz1=min(nz,d+margin-int(origin[1])+1)
        xx=x[:,ix0:ix1];zz=z[iz0:iz1,:]
        dist=np.hypot(np.maximum(np.maximum(a-xx,xx-bb),0),np.maximum(np.maximum(c-zz,zz-d),0));t=1-smooth(dist/margin)
        target[iz0:iz1,ix0:ix1]=target[iz0:iz1,ix0:ix1]*(1-t)+b['floor']*t
    target=np.rint(target).astype(np.int16);active=(weights>0)&known
    np.savez_compressed(OUT/'terrain_target.npz',height=target,active=active,origin=origin,reference=base.astype(np.int16),interior=interior)
    vox.OUT=OUT;p=Painter();transit=load(OLD/'transit_plan.json');samples=load(OLD/'transit2/track_samples.json');protections(p,kept,transit,samples)
    for b in removed:
        a,bb,c,d=b['bounds'];floor=b['floor'];top=floor+b.get('storeys',2)*5+6
        p.fill(a-3,floor,c-3,bb+3,top,d+6,'minecraft:air','retire_overlapping/'+b['id'],'retire')
    # Retire only exact old road/lamp states, and only outside retained facilities.
    with gzip.open(OLD/'geometry_all/ops.json.gz','rt',encoding='utf-8') as f:oldops=json.load(f)
    for op in oldops:
        owner=op['owner'];state=op['state']
        if not ('/street' in owner or owner.startswith('regional/')) or op['mode']=='grade':continue
        if state in ('minecraft:air','minecraft:stone'):continue
        p.match(op['box'],state,'minecraft:air','retire_fragmented_street')
    for cx,cz in load(OUT/'terrain_envelope.json')['chunks']:
        ix,iz=cx*16-int(origin[0]),cz*16-int(origin[1]);mask=active[iz:iz+16,ix:ix+16]
        old=current_height[iz:iz+16,ix:ix+16];h=target[iz:iz+16,ix:ix+16]
        trees=interior[iz:iz+16,ix:ix+16]|(h<old)|(h>old+1)
        if mask.shape==(16,16) and mask.any():p.heightfield(cx,cz,h,mask,'coherent_regional_terrain',trees)
    metadata=dict(kept_plots=kept,removed_plots=removed,remaining_overlap_pairs=0,active_columns=int(active.sum()),frame=origin.tolist())
    (OUT/'surface_layout.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Terrain plan:',len(kept),'plots retained;',len(removed),'overlapping plots retired;',int(active.sum()),'columns',flush=True)
    return p

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args();p=build()
    p.apply('terrain_repair') if args.apply else p.save_plan('terrain_repair')

if __name__=='__main__':main()
