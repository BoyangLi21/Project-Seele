"""Passenger-scale terminal architecture, with continuous protected underpasses."""
import argparse,json
import regional_voxels as vox
from quality_structures import Builder,Station,OUT,OLD,CASES,load,walk
from quality_circulation import Network
from regional_architecture import *

def build(p):
    net=Network(p)
    platforms=[d for d in load(OLD/'transit_plan.json')['platforms'] if d['id'] in ('A1_airport','S1_hakone_airfield')]
    for d in platforms:Station(p,d).run()
    for key,sx,gx,rz in [('bay',740,650,1430),('hakone',-1670,-1610,-20)]:
        x0,x1,z0,z1=sx-100,sx+100,rz-380,rz-305;name='airport/'+key
        # Bury the former branch outside the station. Its new junction sits
        # north of the station, so it cannot end as an open six-metre drop.
        if gx<sx-58:p.fill(gx,71,rz-254,sx-59,76,rz-246,'minecraft:stone',name+'/retired_branch')
        if gx>sx+58:p.fill(sx+59,71,rz-254,gx,76,rz-246,'minecraft:stone',name+'/retired_branch')
        # Entry forecourt and a rhythm of low concrete canopy bays.
        p.fill(x0-4,77,z0-12,x1+4,79,z0-1,'minecraft:stone',name)
        p.fill(x0-4,80,z0-12,x1+4,80,z0+4,FLOOR,name)
        p.fill(x0-4,81,z0-12,x1+4,87,z0+4,AIR,name)
        p.fill(x0-4,89,z0-11,x1+4,89,z0+4,WHITE,name)
        p.fill(x0-4,88,z0-11,x1+4,88,z0-10,DARK,name)
        for x in range(x0+8,x1,24):
            if abs(x-sx)<12:continue
            p.fill(x,81,z0-8,x+1,88,z0-7,'minecraft:polished_basalt[axis=y]',name)
            p.fill(x+3,88,z0-5,x+14,88,z0-5,LIGHT,name)
        # Mullions, deep roof edge and continuous indoor lighting.
        for z in (z0,z1):
            for x in range(x0,x1+1,16):p.fill(x,81,z,x+1,99,z,WALL,name)
            p.fill(x0,96,z,x1,97,z,DARK,name)
            p.fill(x0,100,z-1,x1,101,z+1,WHITE,name)
        for x in range(x0+8,x1-7,16):
            p.fill(x,98,z0+3,x+1,98,z1-3,WALL,name)
            for z in (z0+20,z0+47):p.fill(x+3,98,z,x+12,98,z,LIGHT,name)
        # Keep the centre of the terminal legible and free of furniture.
        p.fill(sx-8,81,z0,sx+8,89,z1-5,AIR,name)
        p.fill(sx-8,80,z0-12,sx+8,80,z1-5,FLOOR,name)
        for z in range(z0+5,z1-8,8):p.fill(sx-1,80,z,sx+1,80,z+2,DARK,name)
        for side in (-1,1):
            for z in (z0+29,z0+43,z0+56):
                for x in (sx+side*30,sx+side*55,sx+side*80):
                    bench(p,x,z,80,name,'north');p.put(x+3,81,z,WALL,name)
                    p.put(x+3,82,z,'minecraft:flower_pot',name)
        p.fill(sx-11,91,z0-1,sx+11,94,z0-1,DARK,name)
        p.sign(sx,93,z0-2,['箱根湾空港' if key=='bay' else '新箱根飛行場','TERMINAL 01','出発 / 到着','RAIL CONNECTION'],name)
        for x,label in [(sx-40,'CHECK-IN'),(sx+40,'ARRIVALS')]:p.sign(x,86,z0+15,[label,'案内 / INFORMATION','',''],name)
        sz=1190 if key=='bay' else -265
        net.line((sx,z1+7),(sx,sz),71,name+'/rail_concourse',5,4)
        junction=sz-23
        net.line((gx,junction),(sx,junction),71,name+'/gate_concourse',5,4)
        net.line((gx,junction),(gx,rz-235),71,name+'/gate_turn',5,4)
        net.line((sx-9,sz-13),(sx-9,sz+13),71,name+'/bridge',5,4,False)
        net.line((sx-9,sz),(sx,sz),71,name+'/bridge_arm',5,4,False)
        # Passenger stair heads stand outside the measured taxiing wing space.
        p.fill(gx-6,89,rz-239,gx+6,89,rz-219,WHITE,name)
        for x in (gx-6,gx+6):
            for z in (rz-239,rz-220):p.fill(x,81,z,x,88,z,WALL,name)
        p.fill(gx-2,88,rz-229,gx+2,88,rz-225,LIGHT,name)
        p.meta['landmarks'].append(dict(id=name+'/terminal',entry=[sx,81,z0],floor=80,style='concrete_terminal_with_canopy'))
    net.finish()
    for d in platforms:
        s=Station(p,d)
        for v in (-10,10):
            s.fill(-21,s.y+1,v-2,-13,s.y+10,v+2,AIR)
            x,y,z=s.xyz(-18,s.y,v);stairs(p,x,z,y,6,'east',s.owner+'/stair',5,'owned')
    for sx,gx,rz in [(740,650,1430),(-1670,-1610,-20)]:
        name='airport/stair/'+str(sx);z1=rz-305
        stairs(p,sx,z1+6,71,9,'north',name+'/terminal',5,'owned')
        stairs(p,gx,rz-234,71,9,'south',name+'/apron',5,'owned')
        p.fill(sx-3,80,z1-5,sx+3,80,z1-3,FLOOR,name)
        p.fill(sx-3,81,z1-5,sx+3,85,z1-3,AIR,name)
        p.fill(gx-3,80,rz-225,gx+3,80,rz-192,FLOOR,name)
        p.fill(gx-3,81,rz-225,gx+3,85,rz-212,AIR,name)
        for i in range(9):
            for xx,zz in [(sx,z1+6-i),(gx,rz-234+i)]:
                for side in (-4,4):p.fill(xx+side,73+i,zz,xx+side,74+i,zz,GLASS,name)
        walk(name+'/terminal',[sx+.5,72,z1+8.5],[sx+.5,81,z1-4.5])
        walk(name+'/apron',[gx+.5,72,rz-235.5],[gx+.5,81,rz-223.5])
        walk(name+'/entry',[sx+.5,81,rz-391.5],[sx+.5,81,rz-311.5])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args()
    vox.OUT=OUT;p=Builder();build(p)
    (OUT/'walk_cases_airports.json').write_text(json.dumps(CASES,ensure_ascii=False,indent=2),encoding='utf-8')
    p.apply('airport_architecture') if args.apply else p.save_plan('airport_architecture')

if __name__=='__main__':main()
