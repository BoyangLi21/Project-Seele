"""Original port and remote military-base architecture on the surveyed R07 pads."""
from pathlib import Path
import argparse,json,math
import regional_voxels as vox
from regional_architecture import stairs

ROOT=vox.ROOT;OUT=ROOT/'artifacts/world_expansion_r07';AIR='minecraft:air';WALL='projectseele:nerv_wall_panel';FLOOR='projectseele:nerv_floor_panel';DARK='minecraft:gray_concrete';LIGHT='projectseele:nerv_strip_light';WHITE='minecraft:white_concrete';GLASS='minecraft:gray_stained_glass';BAR='minecraft:iron_bars[east=true,north=false,south=false,waterlogged=false,west=true]'
CASES=[];ROOMS=[];VEHICLES=[]
def walk(name,path):
    CASES.append(dict(id='r07/'+name,path=path));CASES.append(dict(id='r07/'+name+'/return',path=path[::-1]))
def room(p,b,f,h,name,label,front='south'):
    x0,z0,x1,z1=b;o='r07/'+name;cx=(x0+x1)//2;cz=(z0+z1)//2
    p.fill(x0,f-2,z0,x1,f,z1,DARK,o)
    p.fill(x0+1,f+1,z0+1,x1-1,f+h-1,z1-1,AIR,o)
    p.fill(x0,f,z0,x1,f,z1,FLOOR,o);p.fill(x0,f+h,z0,x1,f+h,z1,DARK,o)
    for x in (x0,x1):p.fill(x,f+1,z0,x,f+h-1,z1,WALL,o)
    for z in (z0,z1):p.fill(x0,f+1,z,x1,f+h-1,z,WALL,o)
    for z in (z0,z1):
        p.fill(x0+1,f+2,z,x1-1,f+2,z,'projectseele:nerv_wall_datum',o)
        for x in range(x0+4,x1-2,8):p.fill(x,f+3,z,min(x+3,x1-2),f+5,z,GLASS,o)
    for x in range(x0+5,x1-2,10):
        for z in range(z0+5,z1-2,10):p.fill(x,f+h,z,x+2,f+h,z,LIGHT,o)
    if front in ('south','north'):
        z=z1 if front=='south' else z0;p.fill(cx-2,f+1,z,cx+2,f+4,z,AIR,o);p.fill(cx-3,f,z-3,cx+3,f,z+3,FLOOR,o)
        p.sign(cx+4,f+3,z+(1 if front=='south' else -1),[label,'NERV / UN','R07',''],o,front)
        walk(name+'/entry',[[cx+.5,f+1,z+(3.5 if front=='south' else -2.5)],[cx+.5,f+1,z+(-3.5 if front=='south' else 3.5)]])
    ROOMS.append(dict(id=name,label=label,bounds=b,floor=f,height=h))
    return cx,cz
def desk(p,x,z,f,o):
    p.fill(x-1,f+1,z,x+1,f+1,z,WHITE,o);p.put(x,f+2,z,'projectseele:nerv_workstation[facing=south]',o)
    p.put(x,f+1,z+1,'another_furniture:dark_oak_chair[facing=north,tucked=false,variant=1,waterlogged=false]',o)
def lamp(p,x,z,f,o):
    p.fill(x,f+1,z,x,f+7,z,DARK,o);p.fill(x-1,f+8,z,x+1,f+8,z,LIGHT,o)
def street(p,x0,z0,x1,z1,f,name,width=9):
    p.fill(x0-width//2,f-2,z0-width//2,x1+width//2,f,z1+width//2,DARK,'r07/'+name)
    p.fill(x0-width//2,f,z0-width//2,x1+width//2,f,z1+width//2,'minecraft:black_concrete','r07/'+name)
    p.fill(x0-width//2,f+1,z0-width//2,x1+width//2,f+6,z1+width//2,AIR,'r07/'+name)
    if z0==z1:
        for x in range(x0,x1+1,14):p.fill(x,f,z0,min(x+5,x1),f,z0,WHITE,'r07/'+name)
    if x0==x1:
        for z in range(z0,z1+1,14):p.fill(x0,f,z,x0,f,min(z+5,z1),WHITE,'r07/'+name)
    walk(name,[[x0+.5,f+1,z0+.5],[x1+.5,f+1,z1+.5]])
def ramp(p,x0,x1,z,width,lower,upper,name,axis='x'):
    def box(a,y0,c,y1):return (a,y0,z-c,a,y1,z+c) if axis=='x' else (z-c,y0,a,z+c,y1,a)
    for x in range(x0,x1+1):
        height=round((lower+(upper-lower)*(x-x0)/(x1-x0))*2)/2;floor=math.floor(height)
        p.fill(*box(x,min(lower,upper)-3,width//2,floor),DARK,'r07/'+name)
        state='minecraft:smooth_stone_slab[type=bottom,waterlogged=false]' if height%1 else FLOOR
        y=floor+1 if height%1 else floor;p.fill(*box(x,y,width//2,y),state,'r07/'+name)
        p.fill(*box(x,y+1,width//2,max(lower,upper)+5),AIR,'r07/'+name)
    path=[[x0+.5,lower+1,z+.5],[x1+.5,upper+1,z+.5]] if axis=='x' else [[z+.5,lower+1,x0+.5],[z+.5,upper+1,x1+.5]]
    walk(name,path)
def tower_stairs(p,x0,z0,f,levels,name):
    # Two flights per 10-block floor, with every slab authored before headroom.
    room(p,(x0,z0,x0+15,z0+17),f,levels*10+7,name,'昇降階段')
    for level in range(levels+1):
        y=f+10*level;p.fill(x0+1,y,z0+1,x0+14,y,z0+4,FLOOR,name);p.fill(x0+1,y,z0+13,x0+14,y,z0+16,FLOOR,name)
        for z in (z0+5,z0+12):p.fill(x0+7,y+1,z,x0+7,y+2,z,BAR,name)
    for level in range(levels):
        y=f+level*10
        p.fill(x0+2,y+5,z0+8,x0+12,y+5,z0+10,FLOOR,name)
        stairs(p,x0+4,z0+13,y,5,'north',name,3,'owned');stairs(p,x0+10,z0+9,y+5,5,'south',name,3,'owned')
        walk(name+f'/{level}/a',[[x0+4.5,y+1,z0+15.5],[x0+4.5,y+6,z0+8.5]])
        walk(name+f'/{level}/turn',[[x0+4.5,y+6,z0+8.5],[x0+10.5,y+6,z0+8.5]])
        walk(name+f'/{level}/b',[[x0+10.5,y+6,z0+8.5],[x0+10.5,y+11,z0+15.5]])
def port(p):
    o='r07/port'
    p.fill(1224,65,320,1399,68,568,DARK,o);p.fill(1224,68,320,1399,68,568,FLOOR,o)
    p.fill(1400,61,336,1424,64,568,DARK,o);p.fill(1400,64,336,1424,64,568,FLOOR,o)
    # Seaward retaining face and a clear mooring apron.
    p.fill(1423,43,336,1424,63,568,'minecraft:polished_deepslate',o)
    for z in range(344,569,16):p.put(1423,65,z,'minecraft:polished_blackstone_wall[east=none,north=none,south=none,up=true,waterlogged=false,west=none]',o+'/bollard')
    for z in (424,544):ramp(p,1376,1400,z,11,68,64,'port/yard_quay_ramp_'+str(z))
    room(p,(1248,336,1296,392),68,12,'port/warehouse','物流倉庫')
    room(p,(1248,448,1280,488),68,8,'port/customs','港湾管理・税関')
    for x in (1256,1270):desk(p,x,456,68,o+'/customs')
    for x in range(1256,1291,12):
        for z in range(345,386,12):p.fill(x,69,z,x+6,72,z+6,'minecraft:oak_planks',o+'/cargo');p.chest(x+2,69,z+7,[('minecraft:iron_ingot',64),('minecraft:coal',64)],o)
    # Ordered container lanes with open vehicle circulation between rows.
    for row,z in enumerate(range(344,409,24)):
        for col,x in enumerate(range(1308,1381,24)):
            c=['blue','light_gray','green','red'][(row+col)%4]
            p.fill(x,69,z,x+8,73,z+16,f'minecraft:{c}_terracotta',o+'/container')
            for zz in range(z+1,z+16,3):p.fill(x,69,zz,x,73,zz,'minecraft:gray_concrete',o+'/container_ribs')
    room(p,(1328,464,1376,520),68,10,'port/naval_support','海上支援・整備')
    for x in (1338,1356):desk(p,x,476,68,o)
    for z in (386,498):
        # Two light portal cranes, with both feet anchored to the apron.
        for x in (1403,1419):
            for dz in (-9,9):p.fill(x,65,z+dz,x+1,85,z+dz+1,WHITE,o+'/crane')
        p.fill(1403,85,z-9,1420,87,z+10,WHITE,o+'/crane')
        p.fill(1400,88,z-1,1454,90,z+1,WHITE,o+'/jib')
        p.fill(1447,75,z,1447,87,z,'minecraft:chain[axis=y,waterlogged=false]',o+'/hoist')
    for x,z in [(1230,328),(1230,552),(1392,328),(1392,556)]:lamp(p,x,z,68,o)
    for x,z in [(1300,432),(1300,552),(1378,432)]:p.fill(x-3,68,z-3,x+3,68,z+3,'projectseele:nerv_hazard_paving',o)
    p.meta['port']=dict(bounds=[1224,320,1424,568],yard_floor=68,quay_floor=64,ramps=[424,544])
def base(p):
    o='r07/base';f=74
    # Clear, level operational pavement; landscaped strips remain outside it.
    p.fill(6752,f-2,-6664,6816,f,-6008,DARK,o+'/runway_base')
    p.fill(6768,f,-6640,6800,f,-6032,'minecraft:black_concrete',o+'/runway')
    for z in range(-6632,-6031,24):p.fill(6783,f,z,6785,f,z+9,WHITE,o+'/centreline')
    for x in (6768,6800):p.fill(x,f,-6640,x,f,-6032,WHITE,o+'/edge')
    for z in (-6636,-6040):
        for x in range(6772,6799,4):p.fill(x,f,z,x+1,f,z+5,WHITE,o+'/threshold')
    for z in range(-6632,-6029,24):
        for x in (6764,6804):p.put(x,f,z,'minecraft:sea_lantern',o+'/runway_light')
    street(p,6720,-6608,6720,-6064,f,'base/taxiway',15)
    for z in (-6552,-6288,-6080):street(p,6608,z,6784,z,f,'base/taxi_cross_'+str(z),13)
    street(p,6560,-6656,6560,-5968,f,'base/main_road',11)
    for z in (-6456,-6080):street(p,6344,z,6712,z,f,'base/cross_'+str(z),11)
    # Vehicle maintenance, operations, barracks and airfield support.
    room(p,(6592,-6424,6680,-6344),f,15,'base/vehicle_shop','車両整備棟','south')
    for x in (6606,6634,6662):p.fill(x-5,75,-6344,x+5,81,-6344,AIR,o+'/garage_port')
    room(p,(6384,-6624,6480,-6544),f,13,'base/operations','基地運用・管制')
    for x in (6400,6420,6440,6460):
        for z in (-6608,-6584):desk(p,x,z,f,o+'/operations')
    for x in (6352,6432):
        room(p,(x,-6504,x+55,-6464),f,8,'base/barracks_'+str(x),'隊員宿舎')
        for xx in range(x+6,x+49,8):
            for z in (-6495,-6480):p.bed(xx,75,z,o,color='light_gray')
    room(p,(6616,-6040,6688,-5984),f,9,'base/air_terminal','航空連絡・乗降棟')
    for x in (6630,6652,6674):desk(p,x,-6028,f,o+'/terminal')
    room(p,(6344,-6048,6416,-5992),f,11,'base/power','動力・冷却設備')
    for x in (6360,6384):
        p.fill(x,75,-6038,x+12,81,-6018,'minecraft:iron_block',o+'/generator')
        for z in range(-6036,-6017,4):p.fill(x+1,82,z,x+11,82,z,'minecraft:iron_trapdoor[facing=north,half=top,open=false,powered=false,waterlogged=false]',o+'/vent')
    # Aircraft shelters face the taxi apron, with full-width open doors.
    for z in (-6600,-6512,-6248):
        room(p,(6608,z,6672,z+55),f,17,'base/air_shelter_'+str(z),'航空機格納庫')
        p.fill(6620,75,z+55,6660,87,z+55,AIR,o+'/aircraft_port')
    for x,z in [(6672,-6568),(6672,-6480),(6664,-6212),(6624,-6312)]:
        p.fill(x-13,74,z-16,x+13,74,z+16,FLOOR,o+'/air_apron')
    # Perimeter wall and distinct defense positions, all physically grounded.
    for x in (6332,6868):p.fill(x,74,-6692,x+1,78,-5964,DARK,o+'/perimeter')
    for z in (-6692,-5964):p.fill(6332,74,z,6869,78,z+1,DARK,o+'/perimeter')
    p.fill(6554,75,-5964,6566,80,-5963,AIR,o+'/main_gate')
    for x,z in [(6344,-6680),(6856,-6680),(6344,-5976),(6856,-5976)]:
        room(p,(x-7,z-7,x+7,z+7),74,8,'base/defense_'+str(x)+'_'+str(z),'監視・防衛')
        p.fill(x-7,83,z-7,x+7,83,z+7,FLOOR,o+'/weapon_deck')
        VEHICLES.append(dict(id='superbwarfare:hpj_11',position=[x+.5,84,z+.5],yaw=0,role='defense'))
    p.meta['base']=dict(bounds=[6320,-6704,6879,-5952],floor=74,runway=[6784,-6640,-6032],gate=[6560,75,-5964])
def secret(p):
    o='r07/secret';f=76;room(p,(6384,-6288,6500,-6136),f,84,'secret/main_hangar','機密試験格納棟')
    # Actual front gate is animated by the runtime; its physical plane is a barrier.
    p.fill(6426,77,-6136,6458,141,-6136,'minecraft:barrier',o+'/pressure_gate')
    p.fill(6400,77,-6136,6404,80,-6136,AIR,o+'/staff_entrance')
    for x in (6425,6459):
        p.fill(x,77,-6227,x,141,-6137,DARK,o+'/tank_wall')
        p.fill(x,120,-6224,x,134,-6140,GLASS,o+'/observation')
        for z in range(-6216,-6144,18):p.fill(x,82,z,x,115,z+12,GLASS,o+'/lower_observation')
    p.fill(6426,77,-6227,6458,141,-6227,DARK,o+'/tank_rear')
    p.fill(6426,77,-6226,6458,120,-6137,'projectseele:lcl[level=0]',o+'/lcl')
    for x in (6419,6460):
        p.fill(x,126,-6252,x+5,126,-6142,FLOOR,o+'/upper_gallery')
        pole=x if x==6419 else x+5
        for z in range(-6228,-6141,16):
            p.fill(pole,77,z,pole,132,z,DARK,o+'/gallery_support')
            p.fill(min(pole,x+2),132,z,max(pole,x+2),132,z,DARK,o+'/light_arm')
            p.put(x+2,131,z,LIGHT,o+'/gallery_light')
    p.fill(6420,126,-6220,6464,126,-6215,FLOOR,o+'/pilot_gantry')
    p.fill(6426,127,-6221,6458,128,-6221,BAR,o+'/gantry_rear_guard')
    for x0,x1 in ((6426,6439),(6445,6458)):p.fill(x0,127,-6214,x1,127,-6214,BAR,o+'/gantry_front_guard')
    tower_stairs(p,6472,-6264,76,5,'secret/gantry_stairs')
    p.fill(6460,126,-6250,6486,126,-6249,FLOOR,o+'/tower_link');p.fill(6472,127,-6250,6472,130,-6249,AIR,o+'/tower_door')
    room(p,(6388,-6156,6416,-6140),76,7,'secret/control','試験制御・排液')
    for x in (6394,6406):desk(p,x,-6150,76,o+'/control')
    for x in (6394,6398,6402):p.put(x,78,-6141,'minecraft:stone_button[face=wall,facing=north,powered=false]',o+'/controls')
    p.fill(6418,74,-6135,6552,76,-6120,DARK,o+'/deployment_apron');p.fill(6418,76,-6135,6552,76,-6120,FLOOR,o+'/deployment_apron')
    ramp(p,-6120,-6080,6536,31,76,74,'secret/apron_ramp','z')
    p.meta['secret']=dict(home=[6442.5,77,-6205.5],yaw=0,wet_box=[6426,77,-6226,6458,120,-6137],door=[6442.5,77,-6135.5],controls=[[6394,78,-6141],[6398,78,-6141],[6402,78,-6141]],gantry=[6442.5,127,-6217.5])
    walk('secret/gantry',[[6480.5,127,-6249.5],[6462.5,127,-6249.5],[6462.5,127,-6217.5],[6442.5,127,-6217.5]])
def main(part,apply=False):
    vox.OUT=OUT;p=vox.Painter();{'port':port,'base':base,'secret':secret}[part](p)
    p.meta.update(rooms=ROOMS,vehicles=VEHICLES,walk_cases=CASES)
    p.apply(part+'_architecture') if apply else p.save_plan(part+'_architecture')
    (OUT/(part+'_walk_cases.json')).write_text(json.dumps(CASES,ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('part',choices=['port','base','secret']);ap.add_argument('--apply',action='store_true');a=ap.parse_args();main(a.part,a.apply)
