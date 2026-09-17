"""Replace identified station clutter and unsupported signs using exact old states."""
import argparse, json, re
from collections import Counter
from pathlib import Path
import regional_voxels as vox
from query_blocks import read_box, AIR

OUT=vox.ROOT/'artifacts/world_repair_r19/objects'

def main(apply=False):
    vox.OUT=OUT;p=vox.Painter();inv=json.loads((OUT.parent/'inventory/world_objects.json').read_text())['objects']
    plan=json.loads((vox.ROOT/'artifacts/world_expansion_20260907/transit_plan.json').read_text(encoding='utf8'))
    platforms=[q for q in plan['platforms'] if q.get('mode')!='AIRPLANE']
    platforms.extend(json.loads((vox.ROOT/'artifacts/world_quality_r02/extension_plan.json').read_text(encoding='utf8'))['transit']['platforms'])
    for f in (vox.ROOT/'artifacts/world_expansion_r07/port_transit_plan.json',):
        if f.exists():platforms.extend(json.loads(f.read_text(encoding='utf8'))['platforms'])
    def station(pos):
        x,y,z=pos
        for q in platforms:
            a,b,c=q['center'];half=q['length']/2+20;along_x=q['heading'] in ('E','W')
            if abs(y-b)<14 and abs(x-a)<(half if along_x else 25) and abs(z-c)<(25 if along_x else half):return True
        return False
    removed=[]
    for row in inv['signs']:
        if not row['unsupported']:continue
        pos=tuple(row['pos']);p.match((*pos,*pos),row['state'],'minecraft:air','r19/remove_floating_sign');removed.append(row)
    for row in inv['ticket_machines']:
        pos=tuple(row['pos']);p.match((*pos,*pos),row['state'],'minecraft:air','r19/remove_ticket_machine')
    seats=Counter()
    for row in inv['wooden_seats']:
        x,y,z=row['pos'];facing=re.search(r'facing=([a-z]+)',row['state']).group(1)
        kind='station_seat' if station((x,y,z)) else 'military_seat' if x>6000 else 'nerv_office_chair' if y<0 or x>1200 and 350<z<800 else 'residential_chair'
        p.match((x,y,z,x,y,z),row['state'],f'projectseele:{kind}[facing={facing}]','r19/seating/'+kind);seats[kind]+=1
    # The entry lift's call button is already outside its seven-wide moving
    # aperture, but its fixed jamb was missing. Span floor to existing lintel.
    backing=read_box(vox.WORLD,vox.DIM,(-355,81,741),(-355,86,741))
    for pos,old in backing.items():
        if old.split('[')[0] in AIR:
            p.match((*pos,*pos),old,'projectseele:nerv_structural_panel','r19/gateway_fixed_call_jamb')
    # Four old chair-decoration buttons below stair-built armrests have no
    # registered door/operation binding. Retire the floating ornaments only.
    for row in inv['buttons']:
        x,y,z=row['pos']
        if row['unsupported'] and x in (19,37) and y==-430 and z in (328,332):
            p.match((x,y,z,x,y,z),row['state'],'minecraft:air','r19/retire_unsupported_chair_ornament')
    p.meta.update(unsupported_signs_removed=len(removed),removed_signs=removed,
        ticket_machine_blocks_removed=len(inv['ticket_machines']),seat_counts=dict(seats),
        original_command_layout_preserved=True)
    p.apply('station_objects_and_seats') if apply else p.save_plan('station_objects_and_seats')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
