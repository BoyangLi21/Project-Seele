"""Original TV-inspired old apartment bars, external galleries and room 402."""
import argparse,json,random,math
import regional_voxels as vox
from quality_structures import Builder,Station,OUT,CASES,load,walk,flat
from regional_architecture import *

def old_apartment(p,b):
    x0,x1,z0,z1=b['bounds'];f=b['floor'];n=b['storeys'];owner=b['id'];roof=f+n*5
    p.fill(x0,f-3,z0,x1,f-1,z1,'minecraft:stone',owner)
    p.fill(x0,f,z0,x1,roof,z1,AIR,owner)
    for level in range(n+1):
        y=f+level*5;p.fill(x0,y,z0,x1,y,z1,'minecraft:smooth_stone',owner)
        if level==n:continue
        p.fill(x0,y+1,z0,x0,y+4,z1,WALL,owner)
        p.fill(x1,y+1,z0,x1,y+4,z1,WALL,owner)
        # Exposed north access gallery; shuttered south verandas.
        p.fill(x0,y+1,z0,x1,y+1,z0,'minecraft:iron_bars[east=true,north=false,south=false,waterlogged=false,west=true]',owner)
        p.fill(x0+14,y+1,z0+4,x1,y+4,z0+4,WALL,owner)
        p.fill(x0+14,y+1,z1-3,x1,y+4,z1-3,WALL,owner)
        p.fill(x0+14,y+1,z1,x1,y+1,z1,WALL,owner)
        p.fill(x0+14,y+2,z1,x1,y+2,z1,'minecraft:iron_trapdoor[facing=south,half=bottom,open=false,powered=false,waterlogged=false]',owner)
        for unit in range(6):
            left=x0+14+unit*10;right=left+10;dx=left+5;number=(level+1)*100+unit+1
            p.fill(left,y+1,z0+4,left,y+4,z1-2,WALL,owner)
            p.fill(left+2,y+2,z1-3,left+8,y+3,z1-3,'minecraft:polished_andesite',owner)
            if (unit+level)%5==0:p.fill(left+3,y+2,z1-3,left+5,y+3,z1-3,GLASS,owner)
            opening(p,dx,z0+4,y,owner,'north',1,2,'owned');door(p,dx,z0+4,y,owner,'north',True,'owned')
            for zz,facing in [(z0+3,'north'),(z0+5,'south')]:
                p.put(dx+1,y+2,zz,f'minecraft:stone_button[face=wall,facing={facing},powered=false]',owner)
            p.sign(dx+2,y+3,z0+3,[owner[-1]+'-'+str(number),'','', ''],owner,'north')
            p.put(dx,y+4,z0+2,LIGHT if (unit+level)%2==0 else 'minecraft:gray_concrete',owner)
            p.put(left+5,y+3,z0+10,'minecraft:light[level=7,waterlogged=false]',owner)
            outside=[dx+.5,y+1,z0+3.5];inside=[dx+.5,y+1,z0+6.5]
            CASES.append(dict(id=owner+'/unit/'+str(number),start=outside,end=inside,button=[dx+1,y+2,z0+3],door=[dx,y+1,z0+4]))
            CASES.append(dict(id=owner+'/unit/'+str(number)+'/return',start=inside,end=outside,button=[dx+1,y+2,z0+5],door=[dx,y+1,z0+4]))
            rei=b['rei_room'] and number==402
            if rei:
                p.fill(left+1,y,z0+5,right-1,y,z1-4,'minecraft:light_gray_concrete',owner)
                p.bed(left+3,y+1,z1-7,owner,'white')
                p.fill(right-2,y+1,z0+6,right-2,y+2,z0+6,'minecraft:iron_block',owner)
                p.put(right-3,y+1,z0+6,'minecraft:water_cauldron[level=3]',owner)
                p.put(left+2,y+1,z0+7,'minecraft:oak_slab[type=bottom,waterlogged=false]',owner)
                p.put(left+2,y+1,z0+8,'minecraft:dark_oak_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]',owner)
                p.chest(right-2,y+1,z1-6,[('minecraft:book',2),('minecraft:glass_bottle',2)],owner,'west')
                p.fill(left+2,y+2,z1-4,left+5,y+4,z1-4,'minecraft:gray_wool',owner)
                p.put(left+6,y+4,z0+10,LIGHT,owner)
                p.meta['landmarks'].append(dict(id='rei_apartment_402',entry=[dx,y+1,z0+3],room=[left+5,y+1,z0+10],block=owner))
            elif (unit*3+level+ord(owner[-1]))%4==0:
                p.bed(left+3,y+1,z1-7,owner,'light_gray')
                p.fill(right-2,y+1,z0+6,right-2,y+2,z0+6,'minecraft:iron_block',owner)
            # The shuttered veranda has its own working door, not a sealed set.
            bx=left+7
            opening(p,bx,z1-3,y,owner,'south',1,2,'owned');door(p,bx,z1-3,y,owner,'south',True,'owned')
            for zz,facing in [(z1-4,'north'),(z1-2,'south')]:p.put(bx-1,y+2,zz,f'minecraft:stone_button[face=wall,facing={facing},powered=false]',owner)
            inside_balcony=[bx+.5,y+1,z1-4.5];outside_balcony=[bx+.5,y+1,z1-1.5]
            CASES.append(dict(id=owner+'/balcony/'+str(number),start=inside_balcony,end=outside_balcony,button=[bx-1,y+2,z1-4],door=[bx,y+1,z1-3]))
            CASES.append(dict(id=owner+'/balcony/'+str(number)+'/return',start=outside_balcony,end=inside_balcony,button=[bx-1,y+2,z1-2],door=[bx,y+1,z1-3]))
        # Quiet stains collect beneath joints and drain pipes, not as random noise.
        for x in range(x0+16,x1,20):
            p.put(x,y+4,z1-3,'minecraft:gray_concrete',owner)
            p.put(x,y+3,z1-3,'minecraft:gray_terracotta',owner)
    box_room(p,(x0+1,x0+13,z0+1,z0+14),roof,5,owner+'/roof_stair_head',WALL,'owned')
    opening(p,x0+13,z0+2,roof,owner+'/roof_exit','east',3,3,'owned')
    # Restore landings for all levels before authoring any flight headroom.
    p.fill(x0+2,f+1,z0+3,x0+10,roof+4,z0+13,AIR,owner+'/stairwell')
    for level in range(n+1):
        y=f+level*5
        for za,zb in ((z0+3,z0+5),(z0+9,z0+13)):p.fill(x0+2,y,za,x0+11,y,zb,FLOOR,owner)
        for xx in (x0+2,x0+6,x0+10):
            p.fill(xx,y,z0+6,xx,y,z0+8,FLOOR,owner)
            p.fill(xx,y+1,z0+6,xx,y+2,z0+8,'minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]',owner)
        p.put(x0+1,y+3,z0+7,LIGHT,owner)
    for level in range(n):
        y=f+level*5;north=level%2==0;x=x0+(4 if north else 8);z=z0+(10 if north else 4)
        stairs(p,x,z,y,5,'north' if north else 'south',owner+'/stairs',3,'owned')
        end=[x+.5,y+6,z0+(5.5 if north else 9.5)];corner=[x+.5,y+6,z0+(2.5 if north else 12.5)]
        walk(owner+f'/stair/{level+1}',[x+.5,y+1,z0+(11.5 if north else 3.5)],end)
        walk(owner+f'/landing/{level+1}',end,corner)
        walk(owner+f'/floor_exit/{level+1}',corner,[x0+12.5,y+6,corner[2]])
        walk(owner+f'/gallery_link/{level+1}',[x0+12.5,y+6,corner[2]],[x0+12.5,y+6,z0+2.5])
    for level in range(n):
        y=f+level*5
        walk(owner+f'/gallery/{level+1}',[x0+12.5,y+1,z0+2.5],[x1-2.5,y+1,z0+2.5])
    # Ground opening is in the open gallery, with no locked outer lobby.
    p.fill(x0+11,f+1,z0,x0+13,f+3,z0,AIR,owner)
    p.fill(x0+5,f+1,z0,x0+9,f+4,z0,WALL,owner)
    p.fill(x0+10,f,z0-4,x0+14,f,z0-1,FLOOR,owner)
    p.sign(x0+7,f+3,z0-1,[owner[-1]+'棟','霧里団地','KIRISATO',''],owner)
    walk(owner+'/main_entry',[x0+12.5,f+1,z0-3.5],[x0+12.5,f+1,z0+2.5])
    walk(owner+'/roof_exit',[x0+12.5,roof+1,z0+2.5],[x0+15.5,roof+1,z0+2.5])
    for x in (x0,x1):p.fill(x,roof+1,z0,x,roof+1,z1,WALL,owner)
    for z in (z0,z1):p.fill(x0,roof+1,z,x1,roof+1,z,WALL,owner)
    for x in (x0+29,x0+59):
        p.fill(x,roof+1,z0+8,x+5,roof+4,z0+13,'minecraft:gray_concrete',owner)
        p.fill(x-1,roof+5,z0+7,x+6,roof+5,z0+14,'minecraft:smooth_stone_slab[type=bottom,waterlogged=false]',owner)
    for x in (x0+14,x1-1):p.fill(x,f+1,z1-1,x,roof,z1-1,'minecraft:granite_wall[east=none,north=none,south=none,up=true,waterlogged=false,west=none]',owner)
    p.meta['landmarks'].append(dict(id=owner,bounds=b['bounds'],floor=f,storeys=n,style='old_danchi',entry=[x0+12,f+1,z0-1]))

def build():
    p=Builder();plan=load(OUT/'extension_plan.json')
    for b in plan['estate']['blocks']:old_apartment(p,b)
    # Small closed demolition lot: visibly separated from inhabited circulation.
    name='kirisato/demolition_lot';p.fill(-2882,70,-1088,-2820,70,-1068,'minecraft:gravel',name)
    for x in (-2882,-2820):p.fill(x,71,-1088,x,72,-1068,'minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]',name)
    for z in (-1088,-1068):p.fill(-2882,71,z,-2820,72,z,'minecraft:iron_bars[east=true,north=false,south=false,waterlogged=false,west=true]',name)
    for x,z,h in [(-2870,-1084,4),(-2854,-1084,2),(-2840,-1082,3),(-2872,-1076,1)]:
        p.fill(x,71,z,x+8,70+h,z+5,WALL,name)
        p.fill(x+2,71+h,z+1,x+5,71+h,z+3,'minecraft:cobblestone',name)
    p.fill(-2852,71,-1068,-2848,73,-1068,WALL,name)
    p.sign(-2850,72,-1067,['解体工事区域','立入禁止','WORKS AREA',''],name,'south')
    vox.OUT=OUT
    return p

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args();p=build()
    (OUT/'walk_cases_estate.json').write_text(json.dumps(CASES,ensure_ascii=False,indent=2),encoding='utf-8')
    p.apply('kirisato_apartments') if args.apply else p.save_plan('kirisato_apartments')
