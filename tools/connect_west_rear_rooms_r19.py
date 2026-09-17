"""Complete the missing lateral hand-off of four R04 west-rear room entries."""
import argparse,json
import regional_voxels as vox
from query_blocks import AIR,read_box

OUT=vox.ROOT/'artifacts/world_repair_r19/room_connections'
FLOOR='projectseele:nerv_floor_panel';WALL='projectseele:nerv_wall_panel';FRAME='projectseele:nerv_structural_panel';DATUM='projectseele:nerv_wall_datum';LIGHT='projectseele:nerv_strip_light'

def descend(path,f,cases):
    for lower in range(f-14,-450,-14):
        for suffix in ('b/return','mid/return','a/return'):
            c=cases[f'r04/flight/{lower}/{suffix}']
            for point in (c['start'],c['end']):
                if point!=path[-1]:path.append(point)
        # The original base vestibule narrows at Z367: its return-corridor
        # jamb is X67. The measured cross-landing is one block north, Z366.
        if lower==-449:path.append([69.5,lower+1,366.5])
        else:path.extend([[64.5,lower+1,367.5],[69.5,lower+1,367.5]])
    path.extend([[69.5,-448,375.5],[87.5,-448,375.5],[87.5,-448,373.5]])
    return path

def all_room_access(rooms,cases):
    routes=[]
    for r in rooms:
        x,y,z=r['entry'];f=r['floor'];x0,x1,z0,z1=r['bounds']
        if z==z0:path=[[x+.5,y,z+1.5],[x+.5,y,z+.5]]
        elif z==z1:path=[[x+.5,y,z-.5],[x+.5,y,z+.5]]
        elif x==x0:path=[[x+1.5,y,z+.5],[x+.5,y,z+.5]]
        elif x==x1:path=[[x-.5,y,z+.5],[x+.5,y,z+.5]]
        else:raise RuntimeError(('Unknown room portal normal',r))
        if f<=-393:
            if z==377:path.append([x+.5,y,371.5])
            else:
                gallery=-4.5 if x<0 else 76.5;path.extend([[gallery,y,z+.5],[gallery,y,371.5]])
            path.extend([[76.5,y,371.5],[76.5,y,367.5],[69.5,y,367.5]])
        elif z==z1 and z==364:path.extend([[x+.5,y,367.5],[69.5,y,367.5]])
        else:path.extend([[10.5,y,z+.5],[10.5,y,344.5],[-.5,y,344.5],[-.5,y,367.5],[69.5,y,367.5]])
        path=descend(path,f,cases);path=[p for i,p in enumerate(path) if i==0 or p!=path[i-1]]
        key='r19/room_access/'+r['id'].removeprefix('r04/pyramid/')
        routes.extend([dict(id=key,path=path),dict(id=key+'/return',path=list(reversed(path)))])
    (OUT/'all_room_access_cases.json').write_text(json.dumps(routes,ensure_ascii=False,indent=2),encoding='utf8')
    return routes

def main(apply=False):
    vox.OUT=OUT;p=vox.Painter();rooms=json.loads((vox.ROOT/'artifacts/world_motion_r04/pyramid/places.json').read_text())['rooms']
    ids={'r04/pyramid/435/06','r04/pyramid/421/13','r04/pyramid/407/20','r04/pyramid/393/25'}
    old_cases={c['id']:c for c in json.loads((vox.WORLD/'quality_walk_cases.json').read_text())};routes=[];held=[]
    allowed=AIR|{FLOOR,WALL,FRAME,DATUM,LIGHT,'projectseele:clear_glass','minecraft:smooth_stone','minecraft:light_gray_concrete','minecraft:gray_concrete','minecraft:polished_deepslate','minecraft:iron_block','minecraft:sea_lantern','minecraft:white_concrete','minecraft:smooth_quartz','minecraft:red_terracotta','minecraft:gray_stained_glass'}
    for r in rooms:
        if r['id'] not in ids:continue
        cx,fy,_=r['entry'];f=r['floor'];lo=(cx-2,f-1,369);hi=(-3,f+5,373);measured=read_box(vox.WORLD,vox.DIM,lo,hi);changes={}
        def put(x,y,z,new,owner):
            old=measured[x,y,z]
            if old==new:changes.pop((x,y,z),None);return
            if old.split('[')[0] not in allowed:held.append((x,y,z,old,new));return
            changes[x,y,z]=(old,new,owner)
        for x in range(cx-2,-2):
            for z in range(369,374):
                edge=x in (cx-2,-3) or z in (369,373)
                put(x,f-1,z,FRAME,'r19/rear_room_gallery_support')
                put(x,f,z,FLOOR,'r19/rear_room_gallery_floor')
                put(x,f+5,z,LIGHT if z==371 and (x-cx)%7==0 else FRAME,'r19/rear_room_gallery_roof')
                for y in range(f+1,f+5):
                    material=DATUM if y==f+2 else 'projectseele:clear_glass' if y==f+3 and x%7 not in (0,1) else WALL
                    put(x,y,z,material if edge else 'minecraft:air','r19/rear_room_gallery_enclosure')
        # Three existing passages meet this link: the room's north stub, the
        # west gallery running north, and the rear concourse running east.
        for y in range(f+1,f+5):
            for x in range(cx-1,cx+2):put(x,y,373,'minecraft:air','r19/rear_room_north_stub_port')
            for x in (-6,-5,-4):put(x,y,369,'minecraft:air','r19/existing_west_gallery_port')
            for z in (370,371,372):put(-3,y,z,'minecraft:air','r19/existing_rear_concourse_port')
        for pos,(before,after,owner) in sorted(changes.items()):p.match((*pos,*pos),before,after,owner)
        path=[[cx+.5,fy,378.5],[cx+.5,fy,371.5],[-4.5,fy,371.5],[76.5,fy,371.5],[76.5,fy,367.5],[69.5,fy,367.5]]
        # Stitch the already commissioned switchback flights into one route.
        # The actor is placed once, inside the room, and must walk all the way
        # back to a point on the proven main-pyramid route without teleporting.
        path=descend(path,f,old_cases)
        routes.append(dict(id='r19/rear_room_to_main/'+r['id'].rsplit('/',1)[1],path=path))
    if held:raise RuntimeError(('Gallery intersects a retained fixture',held[:12]))
    p.meta.update(rooms=sorted(ids),cause='North stubs end at X=-28/-23/-19/-14; the old rear gallery begins at X=-5',walk_nodes=routes,
        original_command_room_untouched=True,room_interiors_untouched=True)
    p.apply('west_rear_gallery_links') if apply else p.save_plan('west_rear_gallery_links')
    print('Full room-to-main access routes',len(all_room_access(rooms,old_cases)))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--apply',action='store_true');main(a.parse_args().apply)
