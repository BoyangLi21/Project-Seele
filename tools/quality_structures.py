"""Repair actual three-dimensional circulation before adding architectural detail.

Uses the shared measured writer. Stair flights and landings are separate solids;
floor planes are never extended over a flight. Native walking cases are emitted
from endpoints, while the client checks the resulting saved blocks independently.
"""
from pathlib import Path
import argparse,gzip,json
import nbtlib
import regional_voxels as vox
from regional_voxels import Painter
from regional_architecture import AIR,DARK,WALL,WHITE,GLASS,FLOOR,LIGHT,STEEL,RED,stairs

ROOT=vox.ROOT;OUT=ROOT/'artifacts/world_quality_r02';OLD=ROOT/'artifacts/world_expansion_20260907'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
CASES=[]

class Builder(Painter):
    def fill(self,*args,**kw):
        if len(args)==8 and 'mode' not in kw:kw['mode']='owned'
        super().fill(*args,**kw)
    def put(self,x,y,z,state,owner,mode='owned'):super().put(x,y,z,state,owner,mode)

def walk(name,a,b,both=True):
    if a==b:return
    CASES.append(dict(id=name,start=a,end=b))
    if both:CASES.append(dict(id=name+'/return',start=b,end=a))

def intersect(a,b):
    c=tuple(max(a[i],b[i]) for i in range(3))+tuple(min(a[i],b[i]) for i in range(3,6))
    return c if all(c[i]<=c[i+3] for i in range(3)) else None

def building_repairs(p):
    plots=[b for b in load(OUT/'surface_layout.json')['kept_plots'] if 'storeys' in b]
    strips=[(-760,32,191,-194,255,209),(-119,32,-520,-101,255,-4)]
    affected={}
    for b in plots:
        x0,x1,z0,z1=b['bounds'];f=b['floor'];box=(x0,f,z0,x1,f+b['storeys']*5+5,z1)
        cuts=[c for s in strips if (c:=intersect(box,s))]
        if cuts:affected[b['id']]=cuts
    with gzip.open(OLD/'geometry_all/ops.json.gz','rt',encoding='utf-8') as fp:old_ops=json.load(fp)
    for op in old_ops:
        if op['owner'] not in affected or op['mode']=='grade':continue
        for cut in affected[op['owner']]:
            if (box:=intersect(tuple(op['box']),cut)):p.fill(*box,op['state'],'restore/'+op['owner'])
    for be in load(OLD/'geometry_all/block_entities.json'):
        x,y,z=be['pos']
        if any(any(a<=x<=d and b<=y<=e and c<=z<=f for a,b,c,d,e,f in cuts) for cuts in affected.values()):
            p.block_entities[x,y,z]=nbtlib.parse_nbt(be['snbt'])
    for b in plots:
        x0,x1,z0,z1=b['bounds'];f=b['floor'];n=b['storeys'];roof=f+n*5;owner=b['id']+'/stair_core'
        # Seven clear stair lanes, with a separate central guard strip.
        p.fill(x0+1,f+1,z0+2,x0+9,roof-1,z0+10,AIR,owner)
        flights=[]
        for level in range(n):
            y=f+level*5
            for za,zb in ((z0+2,z0+4),(z0+8,z0+10)):
                p.fill(x0+1,y,za,x0+9,y,zb,FLOOR,owner)
            p.fill(x0+9,y,z0+2,x0+9,y,z0+10,FLOOR,owner)
            for xx in (x0+1,x0+5,x0+9):
                p.fill(xx,y+1,z0+5,xx,y+2,z0+7,'minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]',owner)
            p.put(x0+1,y+4,z0+3,LIGHT,owner)
            if level==n-1:continue
            north=level%2==0;x=x0+(3 if north else 7);z=z0+(9 if north else 3)
            flights.append((x,z,y,'north' if north else 'south'))
            start=[x+.5,y+1,z+(1.5 if north else -.5)]
            end=[x+.5,y+6,z+(-4.5 if north else 5.5)]
            walk(owner+f'/{level+1}',start,end)
            # Walk out of every upper landing into the occupied floor.
            corner=[end[0],end[1],end[2]+(-2 if north else 2)]
            walk(owner+f'/{level+1}/landing_turn',end,corner)
            walk(owner+f'/{level+1}/landing',corner,[x0+10.5,y+6,corner[2]])
        # Finish ALL floor planes first: an upper landing must never recap
        # the headroom of a lower flight authored in an earlier iteration.
        for x,z,y,heading in flights:stairs(p,x,z,y,5,heading,owner,3,'owned')
        # The ground entry and forecourt retain their original datum.
        cx=(x0+x1)//2
        p.fill(cx-2,f,z1+1,cx+2,f,z1+2,DARK,owner)
    p.meta['repaired_buildings']=sorted(affected);p.meta['stair_cores']=len(plots)

class Station:
    def __init__(self,p,data):
        self.p=p;self.data=data;self.x,self.y,self.z=data['center'];self.horizontal=data['heading'] in ('E','W');self.owner='station/'+data['id'];self.half=data['length']//2+10
    def xyz(self,u,y,v):return (self.x+u,y,self.z+v) if self.horizontal else (self.x+v,y,self.z+u)
    def pos(self,u,y,v):return [a+.5 if i!=1 else a for i,a in enumerate(self.xyz(u,y,v))]
    def fill(self,u0,y0,v0,u1,y1,v1,state):self.p.fill(*self.xyz(u0,y0,v0),*self.xyz(u1,y1,v1),state,self.owner)
    def boarding_edges(self):
        for v in (-2,2):
            facing=('south' if v<0 else 'north') if self.horizontal else ('east' if v<0 else 'west')
            self.fill(-self.half+8,self.y,v,self.half-8,self.y,v,f'mtr:platform[door_type=none,facing={facing},side=0]')
    def run(self):
        p=self.p;r=self.y;h=self.half;name=self.owner
        self.fill(-h,r+1,-15,h,r+13,15,AIR)
        self.fill(-h,r-3,-15,h,r-1,15,DARK)
        self.fill(-h,r,-15,h,r,15,FLOOR)
        # Concrete plinth, open steel bays and a shallow stepped canopy.
        for v in (-15,15):
            self.fill(-h,r+1,v,h,r+2,v,WHITE)
            self.fill(-h,r+3,v,h,r+6,v,GLASS)
            self.fill(-h,r+7,v,h,r+8,v,WALL)
            for u in range(-h,h+1,16):self.fill(u,r+1,v,u,r+11,v,'minecraft:polished_basalt[axis=y]')
            self.fill(-h,r+9,v,h,r+9,v,RED if r<0 else DARK)
        self.fill(-h,r+11,-15,h,r+11,-4,DARK)
        self.fill(-h,r+11,4,h,r+11,15,DARK)
        self.fill(-h,r+12,-4,h,r+12,4,WALL)
        for u in range(-h+6,h-5,12):
            self.fill(u,r+10,-13,u+1,r+10,13,STEEL)
            for v in (-7,7):self.fill(u,r+10,v,u+3,r+10,v,LIGHT)
        # Train envelope is continuous through both end walls.
        self.fill(-h,r,-2,h,r+5,2,AIR)
        self.fill(-h,r-1,-2,h,r-1,2,DARK)
        for v in (-3,3):self.fill(-h,r,v,h,r,v,'minecraft:yellow_terracotta')
        self.boarding_edges()
        for u in (-h,h):
            for v in (-3,3):self.fill(u,r,v,u,r,v,'minecraft:smooth_stone_slab[type=bottom,waterlogged=false]')
            for a,b in [(-15,-4),(4,15)]:self.fill(u,r+1,a,u,r+2,b,GLASS)
        ports=ground_ports(self.data)
        for v in (-15,15):
            if (1 if v>0 else -1) not in ports:continue
            self.fill(-4,r+1,v,4,r+6,v,AIR)
            self.fill(-7,r+7,v,7,r+7,v,RED)
            for u in (-6,6):self.fill(u,r+1,v,u,r+6,v,STEEL)
            sign=1 if v>0 else -1
            self.fill(-5,r-2,v,-5+10,r,v+sign,FLOOR)
            self.fill(-4,r+1,v+sign,4,r+4,v+sign,AIR)
            if r<0:
                self.fill(-5,-490,v,5,r-3,v+sign,DARK)
        # Six risers meet a landing beginning strictly AFTER the final riser.
        self.fill(-12,r+6,-13,-6,r+6,13,FLOOR)
        for v in (-10,10):
            x,_,z=self.xyz(-18,r,v)
            stairs(p,x,z,r,6,'east' if self.horizontal else 'south',name+'/stair',5,'owned')
            for lateral in (v-3,v+3):
                for i in range(6):
                    self.fill(-18+i,r+i+2,lateral,-18+i,r+i+3,lateral,GLASS)
            walk(name+f'/stair_{v}',self.pos(-19,r+1,v),self.pos(-12,r+7,v))
            walk(name+f'/side_{v}',self.pos(-19,r+1,v/2),self.pos(0,r+1,v/2))
            if (1 if v>0 else -1) in ports:walk(name+f'/entry_{v}',self.pos(0,r+1,v*1.6),self.pos(0,r+1,v))
        self.fill(-5,r+7,-13,-5,r+8,13,GLASS)
        for v0,v1 in [(-13,-13),(-7,7),(13,13)]:self.fill(-13,r+7,v0,-13,r+8,v1,GLASS)
        for v in (-13,13):self.fill(-12,r+7,v,-6,r+8,v,GLASS)
        walk(name+'/bridge',self.pos(-9,r+7,-10),self.pos(-9,r+7,10))
        for v in (-10,10):
            for u in range(-h+9,h-8,18):
                if -25<=u<=5:continue
                for d in (-1,0,1):
                    x,y,z=self.xyz(u+d,r+1,v);facing=('south' if v<0 else 'north') if self.horizontal else ('east' if v<0 else 'west')
                    p.put(x,y,z,f'minecraft:dark_oak_stairs[facing={facing},half=bottom,shape=straight,waterlogged=false]',name)
        x,y,z=self.xyz(0,r+5,-16)
        p.sign(x,y,z,[self.data['name'],self.data['line'],'のりば / PLATFORMS','出口 / EXIT'],name,'north' if self.horizontal else 'west')
        p.meta['landmarks'].append(dict(id=name,center=self.data['center'],floor=r,bridge=r+6,style='industrial_platform'))

def ground_ports(data):
    y=data['center'][1]
    if 0<=y<75 and not data.get('surface'):return []
    return {'U1_geo_arrival':[-1],'U2_hq':[-1],'U2_logistics':[-1],'U2_hangar':[1]}.get(data['id'],[-1,1])

def flat(p,a,b,f,width=7,height=4,name='concourse',walls=False):
    x,z=a;xx,zz=b;rad=width//2
    x0,x1=(x-rad,x+rad) if x==xx else (min(x,xx),max(x,xx))
    z0,z1=(z-rad,z+rad) if z==zz else (min(z,zz),max(z,zz))
    p.fill(x0,f,z0,x1,f,z1,FLOOR,name)
    p.fill(x0,f+1,z0,x1,f+height,z1,AIR,name)
    if walls:
        p.fill(x0-1,f+height+1,z0-1,x1+1,f+height+1,z1+1,DARK,name)
        if x==xx:
            for edge in (x0-1,x1+1):
                p.fill(edge,f+1,z0,edge,f+height,z1,WALL,name)
                p.fill(edge,f+2,z0,edge,f+2,z1,RED,name)
        else:
            for edge in (z0-1,z1+1):
                p.fill(x0,f+1,edge,x1,f+height,edge,WALL,name)
                p.fill(x0,f+2,edge,x1,f+2,edge,RED,name)
        n=max(abs(xx-x),abs(zz-z))
        for i in range(0,n+1,12):p.put(round(x+(xx-x)*i/max(1,n)),f+height+1,round(z+(zz-z)*i/max(1,n)),LIGHT,name)
    walk(name,[x+.5,f+1,z+.5],[xx+.5,f+1,zz+.5])

def station_repairs(p):
    platforms=[a for a in load(OLD/'transit_plan.json')['platforms'] if a.get('mode')!='AIRPLANE']
    for a in platforms:Station(p,a).run()
    for x,r,z0,z1 in [(-120,80,-200,-136),(-1480,104,640,672),(30,-467,490,522)]:
        flat(p,(x-9,z0),(x-9,z1),r+6,5,4,'interchange/'+str(x))
        for xx in (x-13,x-5):p.fill(xx,r+7,z0,xx,r+8,z1,GLASS,'interchange/guard')
    # Fixed underground entries, including the offset NERV arrival passage.
    for a,b,f,n in [((-309,768),(-309,775),-467,'arrival/platform'),((30,473),(30,480),-467,'hq/platform'),((292,565),(300,565),-467,'science/west'),((320,565),(328,565),-467,'science/east'),((282,180),(291,180),-467,'logistics/platform'),((150,-23),(150,-30),-443,'hangar/platform')]:flat(p,a,b,f,5,4,n)
    for sx,gx,rz in [(740,650,1430),(-1670,-1610,-20)]:
        sz=1190 if sx==740 else -265
        flat(p,(sx-9,sz),(sx,sz),71,5,4,'airport/bridge_transfer')
        flat(p,(sx,sz),(sx,rz-250),71,5,4,'airport/rail_transfer')
    for d in platforms:
        s=Station(p,d)
        for v in (-10,10):s.fill(-13,s.y+7,v-2,-13,s.y+10,v+2,AIR)
    p.meta['stations_rebuilt']=len(platforms)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--part',choices=['buildings','stations'],required=True);ap.add_argument('--apply',action='store_true');args=ap.parse_args()
    vox.OUT=OUT;p=Builder();(building_repairs if args.part=='buildings' else station_repairs)(p)
    (OUT/f'walk_cases_{args.part}.json').write_text(json.dumps(CASES,ensure_ascii=False,indent=2),encoding='utf-8')
    p.apply('structures_'+args.part) if args.apply else p.save_plan('structures_'+args.part)

if __name__=='__main__':main()
