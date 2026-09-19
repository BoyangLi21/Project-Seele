"""Resolve whole-catalogue conflicts between new connectors and retained routes."""
from pathlib import Path
import copy,json
import regional_voxels as v
from query_blocks import read_box,iter_block_entities
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R25_REVIEW';ART=ROOT/'artifacts/facility_r25';OUT=ART/'crossing_finish'

def main():
    v.WORLD=WORLD;v.OUT=OUT;p=v.Painter()
    def put(lo,hi,state,reason):
        for q,old in read_box(WORLD,v.DIM,lo,hi).items():
            if old!=state:p.match((*q,*q),old,state,reason)
    # The east-west link must be a T junction with the existing north-south
    # circulation, not a tube whose side glazing cuts across that circulation.
    for z in (279,283):put((86,-448,z),(89,-445,z),'minecraft:air','r25/open_retained_east_spine_crossing')
    put((112,-442,-47),(112,-439,-44),'minecraft:air','r25/open_retained_station_port_under_existing_roof')
    # Keep the new descent and the old science overbridge as separate choices.
    # The existing nine-wide bridge has room for a two-wide upper bypass.
    put((198,-461,403),(199,-458,403),'minecraft:air','r25/science_upper_fork')
    for z in range(404,410):
        put((198,-461,z),(199,-461,z),'minecraft:smooth_stone' if z>404 else 'minecraft:smooth_quartz_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]','r25/science_upper_bypass_floor')
        put((198,-460,z),(199,-458,z),'minecraft:air','r25/science_upper_bypass_headroom')
        put((198,-457,z),(199,-457,z),'projectseele:nerv_structural_panel','r25/science_upper_bypass_ceiling')
    # The descent retains two clear cells, with a continuous solid side wall.
    for z in range(403,411):
        floor=-462 if z<=404 else max(-467,-462-(z-404))
        put((197,floor+1,z),(197,floor+4,z),'projectseele:nerv_wall_panel','r25/science_stair_east_guard')
    contract=json.loads((ART/'station_maps/contract.json').read_text(encoding='utf8'))
    board=next(b for b in contract['boards'] if b['position']==[677,82,1208]);oldpos=tuple(board['position']);newpos=(677,82,1210)
    oldtag=next(iter_block_entities(WORLD,v.DIM,oldpos,oldpos))[1];newtag=copy.deepcopy(oldtag);newtag['z']=type(newtag['z'])(1210)
    state=read_box(WORLD,v.DIM,oldpos,oldpos)[oldpos]
    for q in [oldpos]+[(x,y+dy,z) for x,y,z in board['supports'] for dy in (0,1)]:put(q,q,'minecraft:air','r25/move_airport_map_out_of_boarding_path')
    assert read_box(WORLD,v.DIM,newpos,newpos)[newpos]=='minecraft:air'
    p.put(*newpos,state,'r25/airport_map_curb_mount');p.block_entities[newpos]=newtag
    for x,y,z in board['supports']:
        for dy in (0,1):
            q=(x,y+dy,z+2);assert read_box(WORLD,v.DIM,q,q)[q]=='minecraft:air'
            p.put(*q,'minecraft:iron_bars[east=false,north=false,south=false,waterlogged=false,west=false]','r25/airport_map_curb_mount')
    board['position']=list(newpos);board['reader'][2]+=2;board['supports']=[[x,y,z+2] for x,y,z in board['supports']]
    for q in contract['walk_nodes']:
        if q.get('readingBoard')==list(oldpos):
            q['readingBoard']=list(newpos)
            for point in q['path']:point[2]+=2
    replacements={
      'science/bridge_riser':[[196.5,-461,403.5],[196.5,-461,402.5],[198.5,-461,402.5],[198.5,-461,403.5],[198.5,-460,408.5],[199.5,-460,410.5],[196.5,-460,410.5]],
      'science/rail_overbridge':[[199.5,-460,407.5],[199.5,-460,410.5],[196.5,-460,410.5],[196.5,-460,540.5]],
      'r21/upper_front_observers':[[102.5,-367,-281.5],[-18.5,-367,-281.5],[-18.5,-367,-283.5],[-29.5,-367,-283.5],[-29.5,-367,-284.5]],
    }
    overrides=[]
    for id,path in replacements.items():overrides.extend([dict(id=id,path=path),dict(id=id+'/return',path=path[::-1])])
    p.meta.update(route_overrides=overrides,airport_board=board);p.apply('retained_route_crossings')
    (ART/'station_maps/contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
    print('Crossing patch',len(p.ops),'explicit changed routes',len(overrides),flush=True)

if __name__=='__main__':main()
