"""Close the reported personnel links using their measured routes and station ports."""
import argparse,json,gzip
import numpy as np
from scipy.ndimage import binary_erosion
import regional_voxels as vox
from scan_regional_completion import volume
from query_blocks import AIR

OUT=vox.ROOT/'artifacts/world_repair_r19/connections'
LO=(84,-453,-145);HI=(155,-383,278)
FRAME='projectseele:nerv_structural_panel';WALL='projectseele:nerv_wall_panel'
FLOOR='projectseele:nerv_floor_panel';GLASS='projectseele:clear_glass';LIGHT='projectseele:nerv_strip_light'
BUILDING={'minecraft:smooth_stone','minecraft:stone','minecraft:deepslate','minecraft:deepslate_bricks','minecraft:deepslate_tiles','minecraft:polished_deepslate','minecraft:polished_blackstone','minecraft:polished_blackstone_bricks','minecraft:light_gray_concrete','minecraft:gray_concrete','minecraft:white_concrete','minecraft:iron_bars','minecraft:glass','minecraft:gray_stained_glass','minecraft:sea_lantern','minecraft:light'}

def main(apply=False):
    vox.OUT=OUT;a,pal=volume(LO,HI);changes={};held=[]
    buttons=json.loads((OUT.parent/'inventory/world_objects.json').read_text())['objects']['buttons']
    controls={tuple(p) for row in buttons for p in (row['pos'],row['backing'])}
    def old(x,y,z):return pal[int(a[y-LO[1],z-LO[2],x-LO[0]])]
    def reserved(x,y,z):
        return (x,y,z) in controls or 88<=x<=99 and -59<=z<=-46 or 89<=x<=100 and -21<=z<=-10 and y>=-424
    def put(x,y,z,new,owner,allow_mtr=False):
        if not (LO[0]<=x<=HI[0] and LO[1]<=y<=HI[1] and LO[2]<=z<=HI[2]):raise ValueError((x,y,z))
        if reserved(x,y,z):return
        s=old(x,y,z);name=s.split('[')[0]
        if s==new:
            changes.pop((x,y,z),None)
            return
        allowed=name in AIR|BUILDING or name.startswith('minecraft:') and name.endswith(('_concrete','_terracotta')) or name.startswith('projectseele:nerv_') and any(k in name for k in ('panel','datum','strip_light','machine_edge','hazard')) or name==GLASS or name.endswith('_stairs') or allow_mtr and name.startswith('mtr:escalator_')
        if not allowed:held.append({'pos':[x,y,z],'old':s,'desired':new});return
        changes[x,y,z]=(s,new,owner)
    def flat_paths(paths,floor,height,owner):
        mask=np.zeros((HI[2]-LO[2]+1,HI[0]-LO[0]+1),bool)
        for x0,x1,z0,z1 in paths:mask[z0-LO[2]:z1-LO[2]+1,x0-LO[0]:x1-LO[0]+1]=True
        interior=binary_erosion(mask);rim=mask&~interior
        for zi,xi in np.argwhere(mask):
            x,z=int(xi+LO[0]),int(zi+LO[2])
            # The live U2 station owns everything north of its south facade.
            # Only the explicit doorway planes below are changed there.
            if floor==-443 and x>=108 and z<=-25:continue
            put(x,floor,z,FLOOR,owner+'/floor')
            put(x,floor+height,z,LIGHT if interior[zi,xi] and (x+z)%13==0 else FRAME,owner+'/roof')
            for y in range(floor+1,floor+height):
                state=(GLASS if floor+2<=y<=floor+4 and (x+z)%8 not in (0,1) else WALL) if rim[zi,xi] else 'minecraft:air'
                # Preserve the operating moving-walk floor and handrails.
                if old(x,y,z).startswith('mtr:'):continue
                put(x,y,z,state,owner+('/wall' if rim[zi,xi] else '/clearance'))
        return mask
    # The first R19 lower ceiling was one block too high for the retained
    # B40 concourse above it. Retire only that recorded, self-authored layer
    # before the revised union restores the two independent walking datums.
    prior=OUT/'reported_links/ops.json.gz';original={}
    if prior.exists():
        with gzip.open(prior,'rt',encoding='utf8') as stream:
            for op in json.load(stream):
                original[tuple(op['box'][:3])]=op['extra'][0]
                if op['owner']=='r19/pyramid_lower_transfer/roof' and op['box'][1]==-442:
                    x,y,z=op['box'][:3]
                    if old(x,y,z)==op['state']:put(x,y,z,op['extra'][0],'r19/retire_high_lower_ceiling')
    # One extra outer bay is necessary: x104 is the operating southbound
    # handrail. Replacing it with a wall would narrow that travel lane.
    zs=[z for z in range(-140,14) if old(103,-395,z).startswith('mtr:escalator_step') or old(104,-395,z).startswith('mtr:escalator_step')]
    for z in zs:
        for y in range(-395,-388):
            material=FLOOR if y==-395 else FRAME if y==-389 or y==-394 or (z%6)==3 else GLASS
            put(105,y,z,material,'r19/upper_walk_east_enclosure')
    # Existing narrow lift exit now meets the north platform through its west
    # face; the main passage enters the south platform through its named port.
    flat_paths([(113,123,-24,247),(114,154,-25,-9),(146,154,-27,-21),
                (90,114,-48,-44),(108,127,243,251),(120,126,244,276),
                (84,127,270,276)],-443,7,'r19/upper_transfer_and_hangar_links')
    flat_paths([(86,115,251,261),(86,92,251,274)],-449,6,'r19/pyramid_lower_transfer')
    # Retire the obsolete belt where its final spur crosses the actual U2
    # turnback. Other machine and lift blocks are not candidates.
    for x in range(90,98):
        for z in range(-45,-7):
            for y in (-443,-442):
                if old(x,y,z).startswith('mtr:escalator_'):
                    new=FLOOR if y==-443 and z<=-44 else 'minecraft:air'
                    put(x,y,z,new,'r19/retire_crossed_legacy_belt',True)
    # Five-wide, six-rise stair between the already established -449/-443
    # datums. Its headroom overrides both intersecting flat-ceiling recipes.
    for i in range(6):
        z=254-i;y=-448+i
        for x in range(110,115):
            for yy in range(-449,y):put(x,yy,z,FRAME,'r19/transfer_stair_support')
            put(x,y,z,'minecraft:polished_deepslate_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]','r19/transfer_stair')
            for yy in range(y+1,y+5):put(x,yy,z,'minecraft:air','r19/transfer_stair_headroom')
            put(x,y+5,z,FRAME,'r19/transfer_stair_soffit')
    # Existing independent routes and station doors are explicit openings.
    openings=[(108,-442,-47,114,-439,-45),(147,-442,-25,153,-438,-24),
              (90,-442,-46,96,-438,-44),(121,-442,271,126,-439,275),
              (87,-448,270,91,-444,274),(110,-442,247,114,-438,248),
              (99,-394,-8,104,-391,-8),(84,-442,272,85,-439,275)]
    for x0,y0,z0,x1,y1,z1 in openings:
        for x in range(x0,x1+1):
            for y in range(y0,y1+1):
                for z in range(z0,z1+1):put(x,y,z,'minecraft:air','r19/retained_port')
    # Every pre-existing, named level route remains a real doorway through
    # these enclosures. Guard its full body width, including the original
    # turning hall and the lift approach, rather than checking four new routes
    # and accidentally closing a different branch. Original stairs/mechanisms
    # are never inferred as air or restored from a retired belt template.
    route_cells=set()
    for case in json.loads((vox.WORLD/'quality_walk_cases.json').read_text(encoding='utf8')):
        path=case.get('path',[case.get('start'),case.get('end')])
        if any(q is None for q in path):continue
        for aa,bb in zip(path,path[1:]):
            aa=np.asarray(aa);bb=np.asarray(bb)
            if abs(aa[1]-bb[1])>.01 or np.any(np.maximum(aa,bb)<LO) or np.any(np.minimum(aa,bb)>HI):continue
            along_x=abs(bb[0]-aa[0])>abs(bb[2]-aa[2]);rx,rz=(.30,.80) if along_x else (.80,.30)
            for q in np.linspace(aa,bb,max(2,int(np.linalg.norm(bb-aa)*4)+1)):
                for x in range(int(np.floor(q[0]-rx)),int(np.floor(q[0]+rx))+1):
                    for z in range(int(np.floor(q[2]-rz)),int(np.floor(q[2]+rz))+1):
                        for y in range(int(np.floor(q[1]+.02)),int(np.floor(q[1]+1.8))+1):
                            if LO[0]<=x<=HI[0] and LO[1]<=y<=HI[1] and LO[2]<=z<=HI[2]:route_cells.add((x,y,z))
    for pos in route_cells:
        before=original.get(pos,old(*pos))
        if before.split('[')[0] in AIR|{'minecraft:light'}:put(*pos,before,'r19/retained_named_route_clearance')
    p=vox.Painter()
    for pos,(before,after,owner) in sorted(changes.items()):p.match((*pos,*pos),before,after,owner)
    p.meta.update(reported_points=[[105,-448,252],[116,-442,-16],[93,-442,-41],[107,-395,-98]],
        upper_east_wall_x=105,upper_wall_z_range=[min(zs),max(zs)],ports=openings,
        retained_mechanisms=held,walk_nodes=[{'id':'r19/pyramid_transfer_stair','start':[105,-448,254],'end':[118,-442,247]},
        {'id':'r19/hangar_south_link','start':[118,-442,-16],'end':[150,-442,-27]},
        {'id':'r19/hangar_north_platform','start':[100,-442,-46],'end':[113,-442,-46]},
        {'id':'r19/hangar_upper_walk','start':[101,-394,-125],'end':[101,-394,-28]}])
    p.meta['preserved_named_route_body_cells']=len(route_cells)
    p.apply('reported_links_v3') if apply else p.save_plan('reported_links_v3')
    preview=a.copy();lookup={s:i for i,s in enumerate(pal)}
    for pos,(_,s,_) in changes.items():
        if s not in lookup:lookup[s]=len(pal);pal.append(s)
        x,y,z=pos;preview[y-LO[1],z-LO[2],x-LO[0]]=lookup[s]
    np.savez_compressed(OUT/'reported_links_v3/preview.npz',blocks=preview,palette=np.asarray(pal),bounds=[LO,HI])

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
