"""Recessed floor lighting for known tall-roof airport rooms."""
import json,argparse
import regional_voxels as v
from query_blocks import read_box,AIR

WORLD=v.ROOT/'run/saves/SEELE_FIELD_R30_REVIEW';OUT=v.ROOT/'artifacts/facility_r30/airport_lights'
def main(apply):
    v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();sites=[]
    rooms=[('terminal',[(x,z) for x in range(374,472,8) for z in [48,60,72]],83)]
    for cx in [545,645]:rooms.append((f'maintenance_{cx}',[(x,z) for x in [cx-30,cx-15,cx,cx+15,cx+30] for z in [34,48,64,78]],95))
    rooms.append(('control_tower',[(x,z) for x in [494,501] for z in [47,54]],106))
    for name,points,roof in rooms:
        b=read_box(WORLD,v.DIM,(min(x for x,z in points),72,min(z for x,z in points)),(max(x for x,z in points),roof,max(z for x,z in points)))
        for x,z in points:
            q=(x,73,z);old=b[q]
            if old not in AIR or b[x,74,z] not in AIR:continue
            if b[x,72,z] not in ['projectseele:nerv_floor_panel','minecraft:gray_concrete']:continue
            if b[x,roof,z] in AIR:continue
            state='projectseele:nerv_ceiling_light[hanging=false,lit=true]';p.match((*q,*q),old,state,'r30/airport_room_floor_luminaire');sites.append(q)
        p.meta['rooms'].append({'id':name,'floor':73,'roof':roof})
    p.save_plan('airport_tall_room_lighting')
    if apply:
        p.apply('airport_tall_room_lighting');f=WORLD/'facility_lighting_r30.json';data=json.loads(f.read_text());data['constant_lamps']+=sites;f.write_text(json.dumps(data,indent=2));(OUT/'sites.json').write_text(json.dumps(sites,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
