"""Connected road surfaces with at most half a block of rise in any walking direction."""
from pathlib import Path
from collections import defaultdict
import heapq,json,math,shutil
import numpy as np
import regional_voxels as vox
from regional_voxels import Painter
from regional_architecture import street_light

ROOT=vox.ROOT;OUT=ROOT/'artifacts/world_quality_r02';OLD=ROOT/'artifacts/world_expansion_20260907'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))

def envelopes(mask,initial):
    """Exact min-plus Lipschitz envelope on eight-connected road cells."""
    h,w=mask.shape;m=mask.reshape(-1);v=np.asarray(initial,dtype=np.int32).reshape(-1).copy()
    queue=[(int(v[i]),int(i)) for i in np.flatnonzero(m & (v<20000))];heapq.heapify(queue)
    offsets=(-w-1,-w,-w+1,-1,1,w-1,w,w+1)
    while queue:
        value,i=heapq.heappop(queue)
        if value!=v[i]:continue
        x=i%w;n=value+1
        for d in offsets:
            j=i+d
            if j<0 or j>=len(m) or abs(j%w-x)>1 or not m[j] or v[j]<=n:continue
            v[j]=n;heapq.heappush(queue,(n,j))
    return v.reshape(mask.shape)

def plan_roads():
    a=np.load(OUT/'terrain_target.npz');terrain=a['height'];origin=a['origin'];nz,nx=terrain.shape
    mask=np.zeros(terrain.shape,bool);carriage=np.zeros_like(mask);stripe=np.zeros_like(mask);fixed=np.full(terrain.shape,30000,dtype=np.int32)
    layout=load(OUT/'surface_layout.json');plots=layout['kept_plots'];plan=load(OLD/'regional_plan.json');transit=load(OLD/'transit_plan.json')
    if list((OUT/'estate_stations').glob('applied_*/receipt.json')):
        transit['platforms'] += [p for p in load(OUT/'extension_plan.json')['transit']['platforms'] if p.get('compact')]
    segments=[]
    def segment(x,z,xx,zz,width=9):segments.append((x,z,xx,zz,width))
    for zone in plan['zones']:
        if zone['kind']!='district':continue
        x0,x1,z0,z1=zone['bounds'];step=zone['spacing'];west=zone['id']=='tokyo_west'
        for x in range(x0,x1+1,step):segment(x,z0,x,520 if west and x>-592 else z1)
        for z in range(z0,z1+1,step):segment(x0,z,-592 if west and z>502 else x1,z)
    segment(-116,-520,-116,-28,13);segment(-116,-28,-110,-28,13);segment(-110,-28,-110,-4,13)
    segment(-760,176,-224,176,13);segment(-224,176,-224,200,13);segment(-224,200,-194,200,13)
    segment(-360,680,-360,700,13)
    segment(-432,696,-432,832,9);segment(-432,832,-280,832,9);segment(-280,696,-280,832,9)
    for z in (512,568,624,680,736):segment(-592,z,-560,z+8,9)
    def draw_segment(s,width_override=None,mark_stripe=False):
        x,z,xx,zz,width=s;width=width_override or width;n=max(abs(xx-x),abs(zz-z));r=width//2
        for i in range(n+1):
            px=round(x+(xx-x)*i/max(1,n));pz=round(z+(zz-z)*i/max(1,n));ix,iz=px-origin[0],pz-origin[1]
            if not 0<=ix<nx or not 0<=iz<nz:continue
            mask[max(0,iz-r-2):min(nz,iz+r+3),max(0,ix-r-2):min(nx,ix+r+3)]=True
            carriage[max(0,iz-r):min(nz,iz+r+1),max(0,ix-r):min(nx,ix+r+1)]=True
            if mark_stripe and i%12<6:stripe[iz,ix]=True
    for s in segments:draw_segment(s,mark_stripe=True)
    # Door approaches use the actual nearest street and stay in each front forecourt.
    entrances=[]
    for b in plots:
        if b.get('style')=='park':continue
        x0,x1,z0,z1=b['bounds'];x=(x0+x1)//2;z=z1+1
        candidates=[]
        for sx,sz,ex,ez,width in segments:
            vx,vz=ex-sx,ez-sz;t=np.clip(((x-sx)*vx+(z-sz)*vz)/max(1,vx*vx+vz*vz),0,1)
            tx,tz=round(sx+t*vx),round(sz+t*vz)
            if tz<z1 and x0-2<=tx<=x1+2:continue
            candidates.append((abs(tx-x)+abs(tz-z),tx,tz))
        if not candidates:continue
        _,tx,tz=min(candidates)
        if abs(tx-x)+abs(tz-z)>90:continue
        # At the facade, protect the actual door and wall; the path begins outside.
        draw_segment((x,z,x,max(z,tz),3),3);draw_segment((x,max(z,tz),tx,max(z,tz),3),3)
        if tz<z:draw_segment((tx,z,tx,tz,3),3)
        ix,iz=x-origin[0],z-origin[1]
        if 2<=ix<nx-2 and 0<=iz<nz-1:
            fixed[iz:iz+2,ix-2:ix+3]=2*(b['floor']+1)
            entrances.append(dict(id=b['id'],pos=[x+.5,b['floor']+1,z+.5]))
    station_paths=[]
    for station in transit['platforms']:
        sx,y,sz=station['center']
        if y<75 or station.get('mode')=='AIRPLANE':continue
        horizontal=station['heading'] in ('E','W')
        for side in (-1,1):
            radius=station.get('half_width',15)+1
            x,z=(sx,sz+side*radius) if horizontal else (sx+side*radius,sz)
            candidates=[]
            for ax,az,bx,bz,width in segments:
                dx,dz=bx-ax,bz-az;t=np.clip(((x-ax)*dx+(z-az)*dz)/max(1,dx*dx+dz*dz),0,1)
                tx,tz=round(ax+t*dx),round(az+t*dz)
                if ((tz-z) if horizontal else (tx-x))*side<0:continue
                candidates.append((abs(tx-x)+abs(tz-z),tx,tz))
            if not candidates:continue
            length,tx,tz=min(candidates)
            if length>150:continue
            corner=(tx,z) if horizontal else (x,tz)
            draw_segment((x,z,*corner,3),3);draw_segment((*corner,tx,tz,3),3)
            station_paths.append(dict(id=station['id']+'/'+str(side),points=[[x,z],list(corner),[tx,tz]],floor=y))
            ix,iz=x-origin[0],z-origin[1];fixed[iz,ix]=2*station.get('outer_walk_height',y+1)
    building_mask=np.zeros_like(mask)
    for b in plots:
        if b.get('style')=='park':continue
        x0,x1,z0,z1=b['bounds'];building_mask[z0-origin[1]:z1-origin[1]+1,x0-origin[0]:x1-origin[0]+1]=True
    mask &= ~building_mask
    for x0,x1,z0,z1 in [(-420,-292,700,819),(-65,195,-175,20)]:
        mask[z0-origin[1]:z1-origin[1]+1,x0-origin[0]:x1-origin[0]+1]=False
    station_boxes=[]
    for p in transit['platforms']:
        x,y,z=p['center']
        if y<75 or p.get('mode')=='AIRPLANE':continue
        half=p['length']//2+10;horizontal=p['heading'] in ('E','W')
        radius=p.get('half_width',15);outer=p.get('outer_walk_height',y+1)
        x0,x1,z0,z1=(x-half,x+half,z-radius,z+radius) if horizontal else (x-radius,x+radius,z-half,z+half)
        station_boxes.append((x0,x1,z0,z1,y))
        mask[z0-origin[1]:z1-origin[1]+1,x0-origin[0]:x1-origin[0]+1]=False
        def station_datum(xx,zz):
            along=abs(xx-x) if horizontal else abs(zz-z)
            if along>half-8:return None
            lateral=abs(zz-z) if horizontal else abs(xx-x)
            # Track mouths use the ballast datum. The next two lanes are
            # transition strips, so a concourse pin cannot create a 1 m kerb.
            return y*2 if lateral<=2 else None if lateral<=4 else 2*outer
        # The surrounding concourse meets the platform at exactly its walking datum.
        for zz in range(z0-1,z1+2):
            for xx in (x0-1,x1+1):
                ix,iz=xx-origin[0],zz-origin[1]
                datum=station_datum(xx,zz)
                if datum is not None and 0<=ix<nx and 0<=iz<nz and mask[iz,ix]:fixed[iz,ix]=datum
        for xx in range(x0-1,x1+2):
            for zz in (z0-1,z1+1):
                ix,iz=xx-origin[0],zz-origin[1]
                datum=station_datum(xx,zz)
                if datum is not None and 0<=ix<nx and 0<=iz<nz and mask[iz,ix]:fixed[iz,ix]=datum
    desired=(terrain.astype(np.int32)+1)*2
    samples=load(OLD/'transit2/track_samples.json');crossings=[];rail_cap=np.full_like(fixed,30000);rail_high=np.full_like(fixed,-30000)
    for rail in samples:
        if rail['mode']!='TRAIN':continue
        for xx,yy,zz in rail['points'][::2]:
            x,y,z=round(xx),round(yy),round(zz);ix,iz=x-origin[0],z-origin[1]
            if y<75 or not(2<=ix<nx-2 and 2<=iz<nz-2):continue
            local=mask[iz-2:iz+3,ix-2:ix+3]
            if not local.any():continue
            # The complete rail body footprint constrains the road, not only
            # isolated centre samples. Half levels follow the native curve.
            view=rail_cap[iz-2:iz+3,ix-2:ix+3];view[local]=np.minimum(view[local],math.floor(yy*2+1e-6))
            high=rail_high[iz-2:iz+3,ix-2:ix+3];high[local]=np.maximum(high[local],math.ceil(yy*2-1e-6))
            crossings.append([x,yy,z])
    fixed[~mask]=30000
    ceiling=np.full_like(fixed,30000);floor=np.full_like(fixed,-30000);policies=[]
    remaining=set(map(int,np.flatnonzero(mask.reshape(-1)&(rail_cap.reshape(-1)<20000))));offsets=(-nx-1,-nx,-nx+1,-1,1,nx-1,nx,nx+1)
    while remaining:
        first=remaining.pop();group=[first];queue=[first]
        while queue:
            i=queue.pop();ix=i%nx
            for delta in offsets:
                j=i+delta
                if j in remaining and abs(j%nx-ix)<=1:remaining.remove(j);queue.append(j);group.append(j)
        ids=np.asarray(group);diff=desired.reshape(-1)[ids]/2-(rail_cap.reshape(-1)[ids]+rail_high.reshape(-1)[ids])/4
        median=float(np.median(diff));kind='bridge' if median>=6 else 'underpass' if median<=-6 else 'crossing'
        if kind=='bridge':floor.reshape(-1)[ids]=rail_high.reshape(-1)[ids]+14
        elif kind=='underpass':ceiling.reshape(-1)[ids]=rail_cap.reshape(-1)[ids]-10
        else:ceiling.reshape(-1)[ids]=rail_cap.reshape(-1)[ids];floor.reshape(-1)[ids]=rail_cap.reshape(-1)[ids]-1
        policies.append(dict(kind=kind,cells=len(ids),median_offset=median,bounds=[int((ids%nx).min()+origin[0]),int((ids//nx).min()+origin[1]),int((ids%nx).max()+origin[0]),int((ids//nx).max()+origin[1])]))
    upper=envelopes(mask,np.minimum(fixed,ceiling))
    minimum=np.maximum(np.where(fixed<20000,fixed,-30000),floor)
    negative=np.where(minimum>-20000,-minimum,30000);lower=-envelopes(mask,negative)
    contradiction=mask & (lower>upper)
    if contradiction.any():
        zz,xx=np.nonzero(contradiction);problems=[]
        for iz,ix in zip(zz,xx):
            nearby=[]
            for pz,px in zip(*np.nonzero((fixed[max(0,iz-12):iz+13,max(0,ix-12):ix+13]<20000))):
                ax=max(0,ix-12)+px;az=max(0,iz-12)+pz
                nearby.append([int(origin[0]+ax),int(origin[1]+az),int(fixed[az,ax])])
            problems.append(dict(pos=[int(origin[0]+ix),int(origin[1]+iz)],lower=int(lower[iz,ix]),upper=int(upper[iz,ix]),pins=nearby))
        (OUT/'road_conflicts.json').write_text(json.dumps(problems,indent=2),encoding='utf-8')
        raise RuntimeError(f'Incompatible road/entry datums: {int(contradiction.sum())} cells; see road_conflicts.json')
    initial=np.minimum(np.maximum(desired,lower),upper);initial[~mask]=30000
    result=envelopes(mask,initial)
    pins=mask&(fixed<20000)
    if not np.array_equal(result[pins],fixed[pins]):raise RuntimeError('Road endpoint drift')
    for dz,dx in [(0,1),(1,0),(1,1),(1,-1)]:
        zz0=max(0,-dz);zz1=min(nz,nz-dz);xx0=max(0,-dx);xx1=min(nx,nx-dx)
        m=mask[zz0:zz1,xx0:xx1]&mask[zz0+dz:zz1+dz,xx0+dx:xx1+dx]
        diff=np.abs(result[zz0:zz1,xx0:xx1]-result[zz0+dz:zz1+dz,xx0+dx:xx1+dx])
        if np.any(diff[m]>1):raise RuntimeError('Unwalkable road height step')
    np.savez_compressed(OUT/'road_surfaces.npz',height2=result.astype(np.int16),mask=mask,carriage=carriage,stripe=stripe,origin=origin)
    (OUT/'road_plan.json').write_text(json.dumps(dict(segments=segments,entrances=entrances,station_paths=station_paths,crossings=crossings,crossing_policy=policies,road_cells=int(mask.sum()),maximum_adjacent_step=.5),ensure_ascii=False,indent=2),encoding='utf-8')
    print('Road plan',int(mask.sum()),'cells;',len(entrances),'entrances;',len(crossings),'crossing samples',flush=True)
    return result,mask,carriage,stripe,origin,plots,station_boxes,samples,segments

def author(data,incremental=False):
    values,mask,carriage,stripe,origin,plots,station_boxes,samples,segments=data;vox.OUT=OUT;p=Painter()
    public_mask=mask.copy()
    for b in plots:
        if b.get('style')=='park':continue
        x0,x1,z0,z1=b['bounds'];p.protect((x0,b['floor'],z0,x1,b['floor']+b.get('storeys',1)*5+6,z1),b['id'])
    p.protect((-194,32,-4,254,255,444),'original_core')
    p.protect((-65,32,-175,195,255,20),'EVA_surface')
    p.protect((-420,79,700,-292,105,819),'NERV_entrance')
    p.protect((-367,-467,743,-353,89,757),'NERV_native_car_sweep')
    for x0,x1,z0,z1,y in station_boxes:p.protect((x0,y-4,z0,x1,y+16,z1),'station')
    # Rail geometry/IDs live in the native MTR database. The measured ballast
    # may become crossing paving; the planner keeps every solid below the rail.
    if incremental:
        prior=np.load(OUT/'road_surfaces_previous.npz')
        changed=(values!=prior['height2']) | (mask!=prior['mask'])
        for bad in load(OUT/'road_actual_audit.json')['bad']:
            x,y,z=bad['pos'];changed[z-origin[1],x-origin[0]]=True
        mask=mask&changed
    for iz in range(mask.shape[0]):
        xs=np.flatnonzero(mask[iz]);k=0
        while k<len(xs):
            ix=int(xs[k]);h2=int(values[iz,ix]);kind='line' if stripe[iz,ix] else 'road' if carriage[iz,ix] else 'walk';end=k+1
            while end<len(xs) and xs[end]==xs[end-1]+1 and int(values[iz,xs[end]])==h2 and ('line' if stripe[iz,xs[end]] else 'road' if carriage[iz,xs[end]] else 'walk')==kind:end+=1
            x0,x1=int(origin[0])+ix,int(origin[0])+int(xs[end-1]);z=int(origin[1])+iz;block_y=(h2-1)//2
            material={'line':'minecraft:white_concrete','road':'minecraft:black_concrete','walk':'minecraft:smooth_stone'}[kind]
            if h2%2:material={'line':'minecraft:quartz_slab','road':'minecraft:polished_blackstone_slab','walk':'minecraft:smooth_stone_slab'}[kind]+'[type=bottom,waterlogged=false]'
            p.fill(x0,block_y-3,z,x1,block_y-1,z,'minecraft:stone','continuous_road_foundation','owned')
            p.fill(x0,block_y,z,x1,block_y,z,material,'continuous_road_surface','owned')
            p.fill(x0,block_y+1,z,x1,block_y+4,z,'minecraft:air','continuous_road_headroom','owned')
            k=end
    # Retained trains pass beneath road bridges. Thin the road foundations
    # only inside their body corridor; every actual road floor stays above it.
    for rail in samples:
        if rail['mode']!='TRAIN':continue
        for x,y,z in {tuple(map(round,a)) for a in rail['points'][::2]}:
            ix,iz=x-int(origin[0]),z-int(origin[1])
            if y>=75 and 0<=iz<public_mask.shape[0] and 0<=ix<public_mask.shape[1] and public_mask[iz,ix] and values[iz,ix]>=2*(y+7):
                for xx in range(x-2,x+3):
                    for zz in range(z-2,z+3):
                        ax,az=xx-int(origin[0]),zz-int(origin[1]);top=y+5
                        if 0<=az<public_mask.shape[0] and 0<=ax<public_mask.shape[1] and public_mask[az,ax]:top=min(top,(int(values[az,ax])-1)//2-1)
                        if top>=y:p.fill(xx,y,zz,xx,top,zz,'minecraft:air','retained_train_under_road_bridge','owned')
    p.meta['road_surface_contract']='Every adjacent walking surface, including diagonal neighbours, differs by at most 0.5 block.'
    return p

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');parser.add_argument('--incremental',action='store_true');args=parser.parse_args()
    if args.incremental:shutil.copy2(OUT/'road_surfaces.npz',OUT/'road_surfaces_previous.npz')
    data=plan_roads();p=author(data,args.incremental)
    p.apply('roads_repair') if args.apply else p.save_plan('roads_repair')
