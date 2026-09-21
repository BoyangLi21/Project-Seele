"""Join the two user-identified observation halls; keep the lowered hoist below them."""
from pathlib import Path
import copy,json,nbtlib
import regional_voxels as v
from query_blocks import read_box,iter_block_entities
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_FIELD_R29_REVIEW';OUT=ROOT/'artifacts/facility_r29/upper_gallery'
AIR='minecraft:air';STRUCT='projectseele:nerv_structural_panel';FLOOR='projectseele:nerv_floor_panel';GLASS='projectseele:clear_glass'
def main():
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();walks=[]
    def b(box,state):p.fill(*box,state,'r29/join_named_observation_halls','owned')
    # These are the two measured halls at the same floor. The intervening
    # void is five metres wide, over the lowered crane's structural frame.
    b((-33,-369,-215,93,-369,-211),STRUCT);b((-33,-368,-215,93,-368,-211),FLOOR)
    b((-33,-361,-216,93,-361,-210),STRUCT)
    b((-32,-367,-216,93,-362,-210),AIR)
    # Seal the two ends of the newly joined volume. The existing east spine
    # and both old hall entrances stay open through their actual portals.
    b((-33,-367,-215,-33,-362,-211),GLASS)
    b((94,-369,-215,94,-369,-211),STRUCT);b((94,-368,-215,94,-368,-211),FLOOR)
    b((94,-367,-215,94,-362,-211),AIR);b((94,-361,-215,94,-361,-211),STRUCT)
    for x in range(-27,90,12):b((x,-361,-215,x+2,-361,-212),'projectseele:nerv_strip_light')
    # Each cage has a structural glass viewing bay. Two transparent floor
    # layers avoid a hidden opaque slab below the apparent viewing glass.
    for cx in (-12,30,72):
        b((cx-9,-369,-225,cx+9,-368,-217),GLASS)
        b((cx-9,-367,-226,cx+9,-362,-226),GLASS)
        for x in (cx-10,cx+10):b((x,-369,-225,x,-368,-217),STRUCT)
    # Move existing displays to the surviving outer wall, retaining content
    # and identity. Never leave a display hovering after removing its wall.
    moved=[]
    for q,tag in iter_block_entities(WORLD,v.DIM,(-33,-367,-210),(93,-362,-208)):
        assert str(tag['id'])=='projectseele:station_departure_board',q
        target=(q[0],q[1],-201);new=copy.deepcopy(tag);new['z']=nbtlib.Int(-201)
        new['Station']=nbtlib.String('三机联合观景廊');new['Row0']=nbtlib.String('上部观察层 · 三机联合观景廊')
        new['Row1']=nbtlib.String('↓ 机库观察窗');new['Row2']=nbtlib.String('→ 西观察廊电梯');new['Row3']=nbtlib.String('← 东侧电梯 / 登机通道')
        b((*q,*q),AIR);b((q[0],-369,-200,q[0],-361,-200),STRUCT)
        p.put(*target,'projectseele:station_departure_board[facing=north,wayfinding=true]','r29/retained_observation_display','owned');p.block_entities[target]=new
        moved.append(dict(before=q,after=target))
    # The two named black piers are inside the continuous enclosed transfer
    # building. Keep the overhead header, outside returns and shaft envelope.
    for x,X in ((5,13),(47,55)):
        p.match((x,-410,-55,X,-346,-55),'minecraft:black_concrete',AIR,'r29/remove_named_internal_black_walls')
    # The moving leaves start at -442. Their 72 m panels end at -370, with
    # the fixed top frame immediately below the observation-floor structure.
    for cx in (-12,30,72):
        for x in range(cx-17,cx+18):
            for y in range(-377,-369):
                state='minecraft:iron_block' if abs(x-cx)==17 or y==-370 else 'minecraft:barrier'
                b((x,y,-213,x,y,-213),state)
    for z in (-221.5,-213.5,-205.5):
        pts=[[-29.5,-367,z],[90.5,-367,z],[102.5,-367,z]]
        for suffix,points in (('',pts),('/return',pts[::-1])):walks.append(dict(id='r29/upper_gallery/'+str(z)+suffix,path=points))
    for x in (-12.5,30.5,72.5,90.5):
        pts=[[x,-367,-221.5],[x,-367,-205.5]]
        for suffix,points in (('',pts),('/return',pts[::-1])):walks.append(dict(id='r29/upper_join/'+str(x)+suffix,path=points))
    p.meta.update(walk_nodes=walks,display_moves=moved,merged_bounds=[-33,-369,-226,94,-361,-200],gate_top=-370,mechanical_rail_y=-373,scope='Two explicitly named observer halls, their shared void, and named internal piers only.')
    p.apply('unified_observation_and_hangar_gate');(OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
    (WORLD/'eva_facility_r29.json').write_text(json.dumps(dict(installed=True,hangar_gate_top=-370,observation_floor=-368)),encoding='utf8')
    site=json.loads((WORLD/'first_battle_site_r10.json').read_text());site.update(hero=[32.5,81,195.5],angel=[32.5,81,229.5],yaw=0,requires_retracted_city=True,label='第三新东京市中心迎击区',avenue=[-144,80,41,207,80,392],source='Existing registered retractable district and R21 reversible battlefield cover; no replacement terrain')
    (WORLD/'first_battle_site_r10.json').write_text(json.dumps(site,ensure_ascii=False,indent=2),encoding='utf8')
    print('Joined observation halls, three raised gate headers, two retired internal walls; central battle metadata set',flush=True)
if __name__=='__main__':main()
