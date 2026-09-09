"""Adapt unsupported source rigging and add fine steel members plus serviced aircraft bays."""
import json,math
import numpy as np
import regional_voxels as v
from prepare_r08_ship_import import SPECS
from scan_regional_completion import volume
OUT=v.ROOT/'artifacts/world_refinement_r08';v.OUT=OUT;p=v.Painter();members=[]
def beam(key,a,b,width,block):
    a=np.array(a,float);b=np.array(b,float);delta=b-a;length=np.linalg.norm(delta);direction=delta/length
    quat=np.array([-direction[1],direction[0],0,1+direction[2]])
    if np.linalg.norm(quat)<1e-8:quat=np.array([0,1,0,0.])
    quat/=np.linalg.norm(quat)
    from scipy.spatial.transform import Rotation
    translation=Rotation.from_quat(quat).apply([-width/2,-width/2,0])
    members.append(dict(key=key,position=a.tolist(),block=block,scale=[width,width,float(length)],rotation=quat.tolist(),translation=translation.tolist()))
def fill(box,state,owner):p.fill(*box,state,'r08/fine/'+owner,'owned')
def cable(key,a,b,sag=0):
    count=8 if sag else 1;points=[]
    for i in range(count+1):
        t=i/count;q=np.array(a)*(1-t)+np.array(b)*t;q[1]-=4*sag*t*(1-t);points.append(q)
    for i,(a,b) in enumerate(zip(points,points[1:])):beam(key+'/'+str(i),a,b,.10,'minecraft:black_concrete')

# Buttons mounted on invisible barriers were a texture-pack-dependent rigging convention.
removed=0
for spec in SPECS:
    d=np.load(OUT/'ships'/(spec['id']+'_source.npz'));a=d['blocks'];pal=d['palette'];lo=d['lo'];cx,z0=spec['destination'];source=json.loads((OUT/'ships/selected.json').read_text());bounds=next(s for s in source if s['id']==spec['id'])['actual_bounds'];xmin=bounds[0][0];cz=(bounds[0][2]+bounds[1][2])//2
    from build_r08_historic_berths import rotate
    for iy,iz,ix in np.argwhere(np.array([s.split('[')[0].endswith('_button') for s in pal])[a]):
        state=str(pal[a[iy,iz,ix]]);props=dict(t.split('=') for t in state.split('[')[1][:-1].split(','));face=props.get('face');dx=dy=dz=0
        if face=='floor':dy=-1
        elif face=='ceiling':dy=1
        else:dx,dz={'east':(-1,0),'west':(1,0),'south':(0,-1),'north':(0,1)}[props['facing']]
        yy,zz,xx=iy+dy,iz+dz,ix+dx
        if not(0<=yy<a.shape[0] and 0<=zz<a.shape[1] and 0<=xx<a.shape[2]) or not str(pal[a[yy,zz,xx]]).startswith('minecraft:barrier'):continue
        x,y,z=int(cx-(iz+lo[2]-cz)),int(iy+lo[1]-43),int(z0+ix+lo[0]-xmin)
        p.match((x,y,z,x,y,z),rotate(state),'minecraft:air','r08/fine/retire_button_rigging');removed+=1
    x=cx+.5
    cable(spec['id']+'/mast_link',(x,92.5,394.5),(x,112.5,494.5),2)
    cable(spec['id']+'/aft_stay',(x,92.5,394.5),(x,69.8,338.5))
    cable(spec['id']+'/fore_stay',(x,112.5,494.5),(x,75,558.5))
    for sign in (-1,1):
        cable(spec['id']+'/fore_shroud_'+str(sign),(x,109,494.5),(x+sign*8,76,506.5))
        cable(spec['id']+'/aft_shroud_'+str(sign),(x,91,394.5),(x+sign*8,69,401.5))

# Replace corner-touching staircase diagonals with continuous native block-display steelwork.
def retire_line(a,b,state):
    n=max(abs(b[i]-a[i]) for i in range(3))
    for k in range(n+1):
        pos=tuple(round(a[i]+(b[i]-a[i])*k/max(n,1)) for i in range(3));p.match((*pos,*pos),state,'minecraft:air','r08/fine/retire_pixel_strut')
for z in (370,510):
    key='crane/'+str(z)
    for x in (1405,1417):
        for zz in (z-7,z+7):
            a=(x,67,zz);b=(1411,85,zz);retire_line(a,b,'minecraft:yellow_terracotta');beam(key+'/leg/'+str((x,zz)),np.array(a)+.5,np.array(b)+.5,.9,'minecraft:yellow_terracotta')
    for zz in (z-7,z+7):
        for i,(a,b) in enumerate([((1405,68,zz),(1417,80,zz)),((1417,68,zz),(1405,80,zz))]):
            retire_line(a,b,'minecraft:gray_concrete')
            aa,bb=((1406,70,zz),(1413,79,zz)) if i==0 else ((1416,70,zz),(1409,79,zz))
            beam(key+'/brace/'+str((zz,i)),np.array(aa)+.5,np.array(bb)+.5,.4,'minecraft:gray_concrete')
        for x in (1405,1417):p.put(x,67,zz,'minecraft:yellow_terracotta','r08/fine/crane_foot_shoe','owned')
    for yy in (89,93):
        a=(1411,yy,z);b=(1430,yy+4,z);retire_line(a,b,'minecraft:yellow_terracotta');beam(key+'/jib/'+str(yy),np.array(a)+.5,np.array(b)+.5,.6,'minecraft:yellow_terracotta')
    for x in range(1411,1429,4):
        a=(x,89+(x-1411)//5,z);b=(x+4,93+(x-1407)//5,z);retire_line(a,b,'minecraft:gray_concrete');beam(key+'/web/'+str(x),np.array(a)+.5,np.array(b)+.5,.3,'minecraft:gray_concrete')
    cable(key+'/hoist',(1428.5,96, z+.5),(1428.5,75,z+.5))

# A 36-block clear aircraft bay with glazed maintenance annexes replaces the empty full-width hall.
for z0 in (-6600,-6512,-6248):
    o='aircraft_service/'+str(z0)
    for x in (6622,6658):
        fill((x,75,z0+4,x,82,z0+52),'minecraft:light_gray_concrete',o)
        for z in range(z0+7,z0+44,8):fill((x,78,z,x,80,z+5),'minecraft:gray_stained_glass',o)
        fill((x,75,z0+48,x,78,z0+52),'minecraft:air',o+'/entry')
        fill((x,75,z0+19,x,78,z0+22),'minecraft:air',o+'/cross_door')
    for x0,x1 in ((6609,6621),(6659,6671)):
        fill((x0,83,z0+3,x1,83,z0+52),'minecraft:gray_concrete',o+'/ceiling')
        for z in range(z0+8,z0+49,10):fill((x0+2,82,z,x1-2,82,z),'projectseele:nerv_strip_light',o+'/light')
    for x in (6625,6655):fill((x,74,z0+5,x,74,z0+54),'minecraft:yellow_terracotta',o+'/bay_line')
    for x in (6611,6668):
        for z in (z0+18,z0+31,z0+43):
            fill((x,75,z,x+1,75,z+3),'minecraft:polished_andesite',o+'/bench')
            p.put(x,76,z,'minecraft:grindstone[face=floor,facing=south]','r08/fine/'+o,'owned')
            p.put(x+1,76,z+2,'minecraft:anvil[facing=north]','r08/fine/'+o,'owned')
            p.put(x,75,z+5,'minecraft:smithing_table','r08/fine/'+o,'owned')
    for x in (6630,6650):
        for z in (z0+10,z0+46):beam(o+'/truss/'+str((x,z)),(6622.5 if x==6630 else 6658.5,83.5,z+.5),(6640.5,90.5,z+.5),.35,'minecraft:gray_concrete')
    for z in (z0+10,z0+46):
        beam(o+'/tie/'+str(z),(6622.5,83.5,z+.5),(6658.5,83.5,z+.5),.35,'minecraft:gray_concrete')
        beam(o+'/king_post/'+str(z),(6640.5,83.5,z+.5),(6640.5,90.5,z+.5),.25,'minecraft:gray_concrete')

# Replace cuboid engine placeholders in the tank shop with functional workshop fixtures.
for x in (6606,6634,6662):
    for xx in range(x-4,x+5,3):
        p.match((xx,76,-6403,xx+1,78,-6400),'minecraft:iron_block','minecraft:air','r08/fine/retire_engine_placeholder')
        p.put(xx,76,-6402,'minecraft:blast_furnace[facing=south,lit=false]','r08/fine/shop_engine','owned')
        p.put(xx+1,76,-6402,'minecraft:smithing_table','r08/fine/shop_engine','owned')
        p.put(xx,77,-6402,'minecraft:grindstone[face=floor,facing=south]','r08/fine/shop_engine','owned')
        p.put(xx+1,77,-6402,'minecraft:anvil[facing=north]','r08/fine/shop_engine','owned')
p.meta.update(removed_barrier_supported_buttons=removed,native_display_members=len(members))
p.apply('fine_native_details')
for path in (OUT/'native_details.json',v.WORLD/'r08_native_details.json'):path.write_text(json.dumps(dict(members=members),indent=2),encoding='utf8')
path=OUT/'base_detail_walk_cases.json';cases=json.loads(path.read_text(encoding='utf8'))
for case in cases:
    if '/air_shelter_' in case['id']:
        z=int(case['id'].split('/air_shelter_')[1].split('/')[0]);case['path']=[[6616.5,75,z+59.5],[6624.5,75,z+59.5],[6624.5,75,z+50.5],[6616.5,75,z+50.5],[6616.5,75,z+20.5],[6629.5,75,z+20.5]]
        if case['id'].endswith('/return'):case['path'].reverse()
path.write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8')
print('Native members',len(members),'retired rigging buttons',removed,flush=True)
