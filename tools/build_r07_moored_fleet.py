"""Two original, walkable moored hulls with seats reserved for real SBW naval weapons."""
import math,json
import regional_voxels as vox
from regional_architecture import stairs
from build_r07_installations import ramp,walk,CASES,desk

OUT=vox.ROOT/'artifacts/world_expansion_r07';vox.OUT=OUT
AIR='minecraft:air';DECK='minecraft:gray_concrete';LIGHT='projectseele:nerv_strip_light';GLASS='minecraft:gray_stained_glass';BARS='minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]'
p=vox.Painter();ships=[];vehicles=[]
def cabin(cx,z0,z1,f,h,width,name):
    p.fill(cx-width,f,z0,cx+width,f,z1,DECK,name)
    p.fill(cx-width,f+1,z0,cx+width,f+h,z1,'minecraft:light_gray_concrete',name)
    p.fill(cx-width+1,f+1,z0+1,cx+width-1,f+h-1,z1-1,AIR,name)
    p.fill(cx-width,f+h,z0,cx+width,f+h,z1,DECK,name)
    for x in (cx-width,cx+width):p.fill(x,f+2,z0+2,x,f+h-2,z1-2,GLASS,name)
    p.fill(cx-width+1,f+2,z0,cx+width-1,f+h-2,z0,GLASS,name)
    p.fill(cx-1,f+1,z1,cx+1,f+3,z1,AIR,name)
    for z in range(z0+3,z1-1,6):p.put(cx,f+h,z,LIGHT,name)
def ship(cx,bow,length,label):
    o='r07/fleet/'+label;stern=bow+length-1
    for z in range(bow,stern+1):
        t=(z-bow)/(length-1);width=round(10.5*min(1,.09+2.7*t)) if t<.38 else round(10.5*(1-.18*(t-.38)/.62))
        keel=58+(2 if t<.12 else 0)
        for y in range(keel,67):
            half=max(1,round(width*(.52+.48*(y-keel)/max(1,66-keel))))
            colour='minecraft:gray_concrete' if y>=64 else 'minecraft:black_concrete' if y==63 else 'minecraft:red_terracotta'
            p.fill(cx-half,y,z,cx+half,y,z,colour,o+'/hull')
        if .20<t<.90 and width>=7:
            p.fill(cx-width+2,61,z,cx+width-2,61,z,DECK,o+'/inner_deck')
            p.fill(cx-width+2,62,z,cx+width-2,65,z,AIR,o+'/inner_clearance')
        if width>=6:
            for x in (cx-width,cx+width):p.put(x,67,z,BARS,o+'/lifeline')
    # Compartments keep a central longitudinal corridor open below deck.
    for z in range(bow+25,stern-12,14):
        p.fill(cx-6,62,z,cx+6,65,z,'projectseele:nerv_wall_panel',o+'/bulkhead')
        p.fill(cx-1,62,z,cx+1,64,z,AIR,o+'/door')
        p.put(cx,65,z+4,LIGHT,o+'/interior_light')
        bed_z=min(z+6,math.floor(bow+.9*(length-1))-1)
        for x in (cx-5,cx+4):p.bed(x,62,bed_z,o+'/crew',color='light_gray')
    walk('fleet/'+label+'/inner',[[cx+.5,62,bow+27.5],[cx+.5,62,stern-16.5]])
    # Raised working bridge and smaller upper wheelhouse.
    cabin(cx,bow+54,bow+74,68,6,6,o+'/bridge')
    cabin(cx,bow+57,bow+69,75,5,5,o+'/wheelhouse')
    desk(p,cx-2,bow+59,68,o+'/bridge');desk(p,cx+2,bow+61,68,o+'/bridge')
    for z in range(bow+77,stern-5):p.fill(cx-7,66,z,cx+7,66,z,DECK,o+'/aft_deck')
    # Add all floor planes before opening the internal stair runs.
    stairs(p,cx-4,stern-14,61,5,'north',o+'/crew_stair',3,'owned')
    stairs(p,cx,bow+77,66,2,'north',o+'/bridge_stair',3,'owned')
    p.fill(cx-2,68,bow+74,cx+2,68,bow+75,DECK,o+'/bridge_landing')
    stairs(p,cx+3,bow+70,68,7,'north',o+'/upper_bridge_stair',3,'owned')
    p.fill(cx+1,76,bow+63,cx+4,78,bow+64,AIR,o+'/wheelhouse_entry')
    walk('fleet/'+label+'/bridge',[[cx+.5,67,bow+79.5],[cx+.5,69,bow+72.5]])
    walk('fleet/'+label+'/crew_stair',[[cx-3.5,62,stern-12.5],[cx-3.5,67,stern-19.5]])
    # Radar mast, exhausts, lifeboats and sealed missile-cell covers.
    p.fill(cx,81,bow+63,cx,98,bow+63,'minecraft:iron_block',o+'/mast')
    p.fill(cx-6,92,bow+63,cx+6,92,bow+63,DECK,o+'/radar_yard')
    p.fill(cx-4,95,bow+62,cx+4,97,bow+62,DECK,o+'/radar_face')
    for x in (cx-3,cx+3):
        p.fill(x,67,bow+44,x+1,75,bow+48,DECK,o+'/exhaust');p.fill(x,76,bow+44,x+1,76,bow+48,'minecraft:black_concrete',o+'/exhaust_top')
    for x in (cx-4,cx+2):
        for z in range(bow+30,bow+43,4):
            p.fill(x,67,z,x+2,69,z+2,DECK,o+'/missile_cell')
            p.fill(x,70,z,x+2,70,z+2,'minecraft:iron_trapdoor[facing=north,half=top,open=false,powered=false,waterlogged=false]',o+'/cell_cover')
    for x in (cx-7,cx+7):p.fill(x,68,bow+75,x,68,bow+82,'minecraft:orange_terracotta',o+'/rescue_boat')
    heliz=stern-8
    p.fill(cx-5,66,heliz-4,cx+5,66,heliz+4,'minecraft:green_terracotta',o+'/helipad')
    for x in (cx-2,cx+2):p.fill(x,66,heliz-2,x,66,heliz+2,'minecraft:white_concrete',o+'/H')
    p.fill(cx-2,66,heliz,cx+2,66,heliz,'minecraft:white_concrete',o+'/H')
    vehicles.extend([dict(id='superbwarfare:mk_42',position=[cx+.5,67,bow+20.5],yaw=180,role='naval_gun'),
        dict(id='superbwarfare:hpj_11',position=[cx+6.5,67,bow+80.5],yaw=0,role='defense')])
    ships.append(dict(id=label,centre_x=cx,bow=bow,stern=stern,deck=66,interior=61,original=True,moored=True))
    p.sign(cx-6,70,bow+74,['NERV / UN',label,'艦橋・BRIDGE',''],o,'south')
    return heliz
heli1=ship(1444,338,110,'ESCORT-01');heli2=ship(1444,462,100,'SUPPORT-02')
for label,z in [('ESCORT-01',426),('SUPPORT-02',546)]:
    # These mooring points avoid the apron bollards and the crane paths.
    ramp(p,1424,1436,z,5,64,66,'fleet/'+label+'/gangway')
    p.fill(1434,67,z-2,1435,68,z+2,AIR,'r07/fleet/rail_opening','owned')
    p.fill(1434,66,z-2,1438,66,z+2,DECK,'r07/fleet/landing')
    walk('fleet/'+label+'/board',[[1421.5,65,z+.5],[1436.5,67,z+.5],[1442.5,67,z+.5]])
vehicles.extend([dict(id='superbwarfare:ah_6',position=[1444.5,67,heli1+.5],yaw=180,role='helicopter'),
                 dict(id='superbwarfare:speedboat',position=[1468.5,63,586.5],yaw=180,role='patrol_boat')])
p.meta.update(ships=ships,vehicles=vehicles,walk_cases=CASES,provenance='Original R07 hulls, compartments and deck architecture; naval weapons are installed SBW entities')
p.apply('moored_fleet');(OUT/'fleet_walk_cases.json').write_text(json.dumps(CASES,indent=2));(OUT/'fleet_vehicles.json').write_text(json.dumps(vehicles,indent=2))
