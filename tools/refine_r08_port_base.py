"""Human-scale maintenance, operations and quay detail within the surveyed R07 facilities."""
import argparse,json,math
import regional_voxels as v
from regional_architecture import stairs
OUT=v.ROOT/'artifacts/world_refinement_r08';v.OUT=OUT
CASES=[]
F='minecraft:smooth_stone';D='minecraft:gray_concrete';W='minecraft:light_gray_concrete';B='minecraft:black_concrete';LIGHT='projectseele:nerv_strip_light';AIR='minecraft:air'
def walk(name,path):CASES.extend([dict(id='r08/detail/'+name,path=path),dict(id='r08/detail/'+name+'/return',path=path[::-1])])
def fill(p,box,state,owner):p.fill(*box,state,'r08/detail/'+owner,'owned')
def line(p,a,b,state,owner):
    n=max(abs(b[i]-a[i]) for i in range(3))
    for k in range(n+1):p.put(*(round(a[i]+(b[i]-a[i])*k/max(n,1)) for i in range(3)),state,'r08/detail/'+owner,'owned')
def sign(p,x,y,z,lines,o):
    fill(p,(x,y-1,z-1,x,y,z-1),D,o);p.sign(x,y,z,lines,'r08/detail/'+o,'south')
def bench(p,x,z,y,o):
    for xx in range(x,x+5):p.put(xx,y+1,z,'minecraft:dark_oak_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]','r08/detail/'+o,'owned')
def workstation(p,x,z,f,o):
    fill(p,(x-1,f+1,z,x+1,f+1,z),'minecraft:smooth_quartz',o)
    p.put(x,f+2,z,'projectseele:nerv_workstation[facing=south]','r08/detail/'+o,'owned');p.put(x,f+1,z+2,'another_furniture:dark_oak_chair[facing=north,tucked=false,variant=1,waterlogged=false]','r08/detail/'+o,'owned')
def cabinet(p,x,z,f,o):
    fill(p,(x,f+1,z,x+3,f+3,z),'minecraft:iron_block',o)
    for xx in (x,x+2):p.put(xx,f+2,z+1,'minecraft:iron_trapdoor[facing=south,half=bottom,open=true,powered=false,waterlogged=false]','r08/detail/'+o,'owned')
def roofplant(p,x,z,y,o):
    fill(p,(x,y,z,x+5,y+2,z+4),D,o)
    fill(p,(x+1,y+3,z+1,x+4,y+3,z+3),'minecraft:iron_trapdoor[facing=north,half=top,open=false,powered=false,waterlogged=false]',o)
    for xx in (x+1,x+4):fill(p,(xx,y+1,z-2,xx,y+1,z-1),'minecraft:polished_andesite',o)

def port(p):
    o='port';p.protect((1238,65,494,1295,76,556),'existing P1 station')
    # Continuous planar concrete panels, drain strips and traffic markings.
    for x in range(1300,1393,18):
        p.match((x,68,336,x,68,558),'projectseele:nerv_floor_panel',D,'r08/detail/port/expansion_joint')
    for z in range(336,565,18):p.match((1298,68,z,1392,68,z),'projectseele:nerv_floor_panel',D,'r08/detail/port/expansion_joint')
    for z in range(338,566,6):fill(p,(1401,64,z,1401,64,z+3),'minecraft:polished_blackstone',o+'/quay_drain')
    # Cargo containers gain end doors, frames and a few accessible interiors.
    colours=['blue','light_gray','green','red']
    for row,z in enumerate(range(344,409,24)):
        for col,x in enumerate(range(1308,1381,24)):
            own=o+'/container';colour=colours[(row+col)%4]
            fill(p,(x,73,z,x+8,73,z+16),f'minecraft:{colour}_terracotta',own)
            for xx in (x,x+8):fill(p,(xx,69,z+16,xx,73,z+16),D,own)
            fill(p,(x+1,69,z+16,x+7,72,z+16),'minecraft:light_gray_terracotta',own)
            for xx in (x+2,x+6):fill(p,(xx,69,z+17,xx,72,z+17),'minecraft:chain[axis=y,waterlogged=false]',own)
            if row==2 and col in (0,2):
                fill(p,(x+1,69,z+1,x+7,72,z+15),AIR,own+'/inside');fill(p,(x+2,69,z+16,x+6,71,z+17),AIR,own+'/open')
                p.chest(x+2,69,z+4,[('minecraft:iron_ingot',64),('minecraft:leather',32)],'r08/detail/'+own)
                fill(p,(x+4,69,z+2,x+6,70,z+4),'minecraft:oak_planks',own+'/pallet')
                walk(own+'/'+str(col),[[x+4.5,69,z+19.5],[x+4.5,69,z+8.5]])
    # Two dock cranes: open trusses, wheel bogies, counterweight, cab and suspended hook.
    for z in (370,510):
        own=o+'/crane_'+str(z)
        for x in (1405,1417):
            for zz in (z-7,z+7):
                fill(p,(x-1,65,zz-1,x+1,67,zz+1),B,own+'/bogie');line(p,(x,67,zz),(1411,85,zz),'minecraft:yellow_terracotta',own+'/leg')
            fill(p,(x,64,z-16,x,64,z+16),'minecraft:iron_block',own+'/rail')
        for zz in (z-7,z+7):
            line(p,(1405,68,zz),(1417,80,zz),D,own+'/brace');line(p,(1417,68,zz),(1405,80,zz),D,own+'/brace')
        fill(p,(1408,84,z-8,1414,87,z+8),D,own+'/machine_deck')
        fill(p,(1407,88,z-3,1412,92,z+3),'minecraft:yellow_terracotta',own+'/counterweight')
        fill(p,(1414,88,z-4,1418,91,z),W,own+'/cab');fill(p,(1415,89,z-5,1417,90,z-5),'minecraft:gray_stained_glass',own+'/cab_glass')
        for yy in (89,93):line(p,(1411,yy,z),(1430,yy+4,z),'minecraft:yellow_terracotta',own+'/jib')
        for x in range(1411,1429,4):line(p,(x,89+(x-1411)//5,z),(x+4,93+(x-1407)//5,z),D,own+'/web')
        fill(p,(1428,75,z,1428,95,z),'minecraft:chain[axis=y,waterlogged=false]',own+'/cable')
        fill(p,(1427,74,z,1429,74,z),B,own+'/hook')
    # Working waterfront support and a shore helipad for the real AH-6.
    fill(p,(1293,68,533,1319,68,559),D,o+'/helipad')
    for x in (1302,1310):fill(p,(x,68,542,x,68,550),'minecraft:white_concrete',o+'/helipad_H')
    fill(p,(1302,68,546,1310,68,546),'minecraft:white_concrete',o+'/helipad_H')
    for x in (1294,1318):
        for z in (534,558):p.put(x,68,z,'minecraft:sea_lantern','r08/detail/'+o,'owned')
    for x in (1332,1350,1368):roofplant(p,x,470,79,o+'/naval_support_roof')
    for x in (1252,1276):roofplant(p,x,343,81,o+'/warehouse_roof')
    fill(p,(1268,69,339,1276,73,391),AIR,o+'/warehouse_central_aisle')
    for x,z in ((1386,470),(1386,500),(1407,448)):
        fill(p,(x,69,z,x+3,71,z+3),'minecraft:red_terracotta',o+'/fire_locker');sign(p,x+1,72,z+4,['消防設備','FIRE POINT','',''],o)
    for x,z in ((1340,495),(1362,495)):
        cabinet(p,x,z,68,o+'/stores');workstation(p,x+1,z-10,68,o+'/maintenance')
    sign(p,1408,68,571,['横須賀式 港湾区','DD6 HISTORIC BERTH','桟橋 → / NERV','艦体制作 NEKOSEAL'],o)
    walk('port/warehouse',[[1272.5,69,396.5],[1272.5,69,342.5],[1288.5,69,342.5]])

def base(p):
    p.protect((6398,75,-6547,6406,80,-6543),'existing defense and power controls')
    # Operations: a real command room, briefing room and analysis room around a clear hall.
    for x in (6400,6420,6440,6460):
        for z in (-6608,-6584):fill(p,(x-1,75,z,x+1,77,z+2),AIR,'base/retire_sparse_desks')
    for x in (6426,6438):fill(p,(x,75,-6584,x,81,-6548),W,'base/partitions')
    fill(p,(6385,75,-6586,6479,81,-6586),W,'base/partitions');fill(p,(6428,75,-6586,6436,78,-6586),AIR,'base/command_entry')
    for x in (6426,6438):fill(p,(x,75,-6568,x,77,-6564),AIR,'base/room_door')
    for x0,x1 in ((6386,6426),(6438,6478)):
        fill(p,(x0,82,-6585,x1,82,-6548),'minecraft:white_concrete','base/acoustic_ceiling')
        for z in (-6580,-6566,-6552):fill(p,(x0+4,81,z,x1-4,81,z),LIGHT,'base/room_light')
    fill(p,(6393,77,-6623,6471,81,-6623),B,'base/command_display')
    for x in range(6396,6470,8):
        fill(p,(x,78,-6622,x+4,79,-6622),'minecraft:cyan_stained_glass','base/command_display')
        fill(p,(x,77,-6622,x+4,77,-6622),'minecraft:gray_concrete','base/display_console')
    for x in range(6398,6471,12):
        for z in (-6611,-6598):workstation(p,x,z,74,'base/command_consoles')
    for z in (-6578,-6571,-6564,-6557):
        for x in (6393,6403,6413):bench(p,x,z,74,'base/briefing_seats')
    fill(p,(6390,77,-6585,6421,80,-6585),B,'base/briefing_screen')
    for x in (6445,6457,6469):workstation(p,x,-6577,74,'base/analysis')
    fill(p,(6446,75,-6565,6470,75,-6557),'minecraft:smooth_quartz','base/map_table')
    fill(p,(6448,76,-6563,6468,76,-6559),'minecraft:green_terracotta','base/map_table')
    for x in (6441,6473):cabinet(p,x,-6550,74,'base/archive')
    sign(p,6429,78,-6543,['作戦運用棟','OPERATIONS','← BRIEFING','ANALYSIS →'],'base')
    walk('base/operations_rooms',[[6432.5,75,-6540.5],[6432.5,75,-6565.5],[6420.5,75,-6565.5]])
    walk('base/command_room',[[6432.5,75,-6565.5],[6432.5,75,-6590.5],[6457.5,75,-6590.5]])
    walk('base/analysis_room',[[6432.5,75,-6565.5],[6439.5,75,-6565.5],[6439.5,75,-6553.5]])
    # Vehicle shop: clear bay envelopes, gantry beams and actual tool stores.
    for x in (6606,6634,6662):
        for xx in (x-11,x+11):fill(p,(xx,74,-6414,xx,74,-6345),'minecraft:yellow_terracotta','base/tank_bay_line')
        workstation(p,x,-6417,74,'base/shop_bench');cabinet(p,x-9,-6419,74,'base/shop_cabinet')
        p.chest(x+7,75,-6417,[('minecraft:iron_ingot',64),('minecraft:iron_pickaxe',2),('minecraft:redstone',32)],'r08/detail/base/tools')
        fill(p,(x-5,75,-6404,x+5,75,-6399),'minecraft:polished_deepslate','base/engine_stand')
        for xx in range(x-4,x+5,3):fill(p,(xx,76,-6403,xx+1,78,-6400),'minecraft:iron_block','base/engine_fixture')
    for x in (6594,6678):fill(p,(x,85,-6422,x,87,-6346),D,'base/crane_runway')
    for z in (-6386,-6410):
        fill(p,(6595,87,z,6677,88,z+1),'minecraft:yellow_terracotta','base/bridge_crane')
        fill(p,(6629,85,z-1,6638,86,z+2),D,'base/trolley');fill(p,(6634,82,z,6634,84,z),'minecraft:chain[axis=y,waterlogged=false]','base/hook')
    walk('base/vehicle_shop_service',[[6634.5,75,-6339.5],[6634.5,75,-6348.5],[6620.5,75,-6348.5],[6620.5,75,-6410.5]])
    # The three hangars get a shaped exterior crown and a human maintenance strip.
    for z0 in (-6600,-6512,-6248):
        own='base/air_shelter_'+str(z0)
        for x in range(6608,6673):
            h=91+round(7*(1-(abs(x-6640)/32)**1.5));fill(p,(x,92,z0,x,h,z0+55),W,own+'/roof_crown') if h>=92 else None
            for zz in range(z0,z0+56,9):fill(p,(x,max(92,h),zz,x,max(92,h),zz),D,own+'/roof_ribs')
        for x in (6614,6666):fill(p,(x,74,z0+4,x,74,z0+52),'minecraft:yellow_terracotta',own+'/clearance')
        for x in (6613,6623,6654,6663):cabinet(p,x,z0+3,74,own+'/tool_storage')
        for x in (6618,6658):workstation(p,x,z0+10,74,own+'/maintenance')
        for z in (z0+19,z0+35):
            fill(p,(6610,75,z,6612,77,z+3),'minecraft:red_terracotta',own+'/fire_equipment')
            fill(p,(6668,75,z,6670,77,z+3),'minecraft:iron_block',own+'/power_cart')
        sign(p,6615,79,z0+56,['航空機整備','AIRCRAFT SERVICE','牽引経路を確保','KEEP TAXIWAY CLEAR'],own)
        walk(own+'/service_aisle',[[6616.5,75,z0+59.5],[6624.5,75,z0+59.5],[6624.5,75,z0+50.5],[6616.5,75,z0+50.5],[6616.5,75,z0+16.5],[6629.5,75,z0+16.5]])
    # Living quarters and forecourts: lockers, seating and washrooms.
    for x0 in (6352,6432):
        for x in range(x0+4,x0+50,10):cabinet(p,x,-6502,74,'base/barracks_lockers')
        for x in (x0+3,x0+45):
            fill(p,(x,75,-6470,x+4,75,-6467),'minecraft:smooth_quartz','base/wash_counter');p.put(x+2,76,-6468,'minecraft:water_cauldron[level=3]','r08/detail/base/wash','owned')
        bench(p,x0+12,-6461,74,'base/forecourt');bench(p,x0+37,-6461,74,'base/forecourt')
        for x in (x0+5,x0+49):roofplant(p,x,-6496,83,'base/barracks_roof')
    # Exterior building rhythm, grounded perimeter buttresses and visible service equipment.
    for x0,z0,x1,z1,roof in [(6384,-6624,6480,-6544,87),(6592,-6424,6680,-6344,89),(6616,-6040,6688,-5984,83)]:
        for x in range(x0+1,x1,12):
            for z in (z0-1,z1+1):fill(p,(x,75,z,x,roof,z),D,'base/facade_pier')
        for x in range(x0+8,x1-8,23):roofplant(p,x,z0+8,roof+1,'base/rooftop_services')
    for x in (6331,6870):
        for z in range(-6686,-5970,24):fill(p,(x,74,z,x,80,z+2),'minecraft:polished_deepslate','base/perimeter_buttress')
    for x in range(6348,6855,24):
        for z in (-6693,-5962):fill(p,(x,74,z,x+2,80,z),'minecraft:polished_deepslate','base/perimeter_buttress')
    # Fill a service yard with disciplined equipment groups, leaving cross roads open.
    for x in (6494,6510):
        for z in (-6595,-6579):
            fill(p,(x,74,z,x+7,74,z+9),D,'base/service_pad');fill(p,(x+1,75,z+1,x+6,78,z+8),'minecraft:green_terracotta','base/supply_container')
    for x,z in ((6370,-6530),(6490,-6460),(6508,-6000)):
        fill(p,(x-4,74,z-3,x+4,74,z+3),'minecraft:coarse_dirt','base/landscape_bed')
        fill(p,(x,75,z,x,80,z),'minecraft:spruce_log[axis=y]','base/pine')
        for y,r in ((78,3),(80,2),(82,1)):fill(p,(x-r,y,z-r,x+r,y,z+r),'minecraft:spruce_leaves[distance=1,persistent=true,waterlogged=false]','base/pine')

def main(part,apply=False):
    p=v.Painter();{'port':port,'base':base}[part](p);p.meta.update(walk_cases=CASES,reference='JMSDF waterfront support / JASDF maintenance and operations, interpreted for NERV; original authored blocks')
    p.apply(part+'_detail') if apply else p.save_plan(part+'_detail')
    (OUT/(part+'_detail_walk_cases.json')).write_text(json.dumps(CASES,ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('part',choices=['port','base']);ap.add_argument('--apply',action='store_true');args=ap.parse_args();main(args.part,args.apply)
