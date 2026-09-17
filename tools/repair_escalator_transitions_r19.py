"""Restore native bottom transitions by providing their missing same-height landing."""
import argparse,json,re
import regional_voxels as vox
from query_blocks import read_box,AIR

OUT=vox.ROOT/'artifacts/world_repair_r19/escalators'
DIR={'north':(0,-1),'south':(0,1),'east':(1,0),'west':(-1,0)}

def main(apply=False):
    vox.OUT=OUT;p=vox.Painter();inv=json.loads((OUT.parent/'inventory/world_objects.json').read_text())['objects']['escalators'];existing={tuple(r['pos']):r['state'] for r in inv};repaired=[];held=[]
    for row in inv:
        s=row['state']
        if not s.startswith('mtr:escalator_step[') or 'orientation=landing_bottom' not in s:continue
        x,y,z=row['pos'];facing=re.search(r'facing=([a-z]+)',s).group(1);dx,dz=DIR[facing];side=re.search(r'side=([a-z]+)',s).group(1)
        slope=existing.get((x+dx,y+1,z+dz),'')
        if not slope.startswith('mtr:escalator_step') or 'orientation=slope' not in slope or f'facing={facing}' not in slope or f'side={side}' not in slope:continue
        behind=(x-dx,y,z-dz);handrail=(x-dx,y+1,z-dz)
        cells=read_box(vox.WORLD,vox.DIM,(min(x,x-dx),y,min(z,z-dz)),(max(x,x-dx),y+3,max(z,z-dz)))
        old=cells[behind];above=cells[handrail]
        allowed=old.split('[')[0] in AIR or any(k in old for k in ('concrete','stone','nerv_floor_panel','nerv_machine_panel','nerv_structural_panel'))
        if not allowed or above.split('[')[0] not in AIR|{'minecraft:light'}:
            held.append({'pos':[x,y,z],'landing':old,'handrail':above});continue
        p.match((*behind,*behind),old,s,'r19/native_escalator_landing')
        rail=f'mtr:escalator_side[facing={facing},orientation=landing_bottom,side={side}]'
        p.match((*handrail,*handrail),above,rail,'r19/native_escalator_landing_rail')
        p.match((x,y,z,x,y,z),cells[x,y,z],s.replace('orientation=landing_bottom','orientation=transition_bottom'),'r19/native_escalator_bottom_blend')
        current=(x,y+1,z);oldrail=cells[current]
        if not oldrail.startswith('mtr:escalator_side'):raise RuntimeError(('Missing existing handrail',current,oldrail))
        p.match((*current,*current),oldrail,oldrail.replace('orientation=landing_bottom','orientation=transition_bottom'),'r19/native_escalator_bottom_rail_blend')
        repaired.append({'step':[x,y,z],'landing':behind,'direction':facing,'side':side})
    # The uphill entrance at the specifically reported command escalator was
    # fenced across both tread lanes. Open only those two entry cells.
    for x in (29,30):
        pos=(x,-403,256);old=read_box(vox.WORLD,vox.DIM,pos,pos)[pos]
        if old.startswith('minecraft:dark_oak_fence'):
            p.match((*pos,*pos),old,'minecraft:air','r19/command_escalator_boarding_clearance')
    p.meta.update(repaired=repaired,held=held,native_contract='BlockEscalatorBase.getOrientation: same-height back + uphill front = TRANSITION_BOTTOM')
    p.apply('bottom_transitions') if apply else p.save_plan('bottom_transitions')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
