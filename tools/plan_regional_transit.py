"""Detailed rail graph consumed by the native MTR author and the block builder."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/world_expansion_20260907'
VECT={'E':(1,0),'W':(-1,0),'N':(0,-1),'S':(0,1)}
OPPOSITE={'E':'W','W':'E','N':'S','S':'N'}


def main():
    rails=[];lines=[];station_bounds={};platform_info=[]
    def add(id,a,b,ha,hb,kind='rail',mode='TRAIN',speed=80,reverse_speed=None):
        if a==b:raise ValueError(id)
        item=dict(id=id,**{'from':a,'to':b},from_angle=ha,to_angle=OPPOSITE[hb],kind=kind,mode=mode,speed=speed)
        if reverse_speed is not None:item['reverse_speed']=reverse_speed
        rails.append(item);return id
    def station(key,name,center,heading,length,line,offset=0):
        x,y,z=center;dx,dz=VECT[heading]
        a=[x-dx*length//2,y,z-dz*length//2];b=[x+dx*length//2,y,z+dz*length//2]
        id=line+'_'+key;add(id,a,b,heading,heading,'platform')
        p=dict(id=id,station=key,name=name,center=center,heading=heading,length=length,line=line)
        platform_info.append(p)
        lo=[min(a[0],b[0])-18,y-5,min(a[2],b[2])-18];hi=[max(a[0],b[0])+18,y+18,max(a[2],b[2])+18]
        if key in station_bounds:
            old=station_bounds[key];old['min']=[min(v,w) for v,w in zip(old['min'],lo)];old['max']=[max(v,w) for v,w in zip(old['max'],hi)]
        else:station_bounds[key]=dict(id=key,name=name,min=lo,max=hi)
        return dict(id=id,a=a,b=b,heading=heading)
    def car(id,length,b1,b2,p1=1,p2=1):return dict(id=id,length=length,width=2,bogie1=b1,bogie2=b2,padding1=p1,padding2=p2)
    metro=[car('eidan_9000_cab_1',20,-6,6,1,0),car('eidan_9000_cab_2',20,-6,6,0,1)]
    tram=[car('eidan_9000_mini_cab_1',10,-1,5,1,0),car('eidan_9000_mini_cab_2',10,-5,1,0,1)]
    intercity=[metro[0],car('eidan_9000_trailer',20,-6,6,0,0),car('eidan_9000_trailer',20,-6,6,0,0),metro[1]]
    def shuttle(code,name,color,stations,cars=metro,speed=100):
        ps=[station(key,n,pos,h,length,code) for key,n,pos,h,length in stations]
        first,last=ps[0],ps[-1];dx,dz=VECT[first['heading']]
        a=[first['a'][0]-dx*160,first['a'][1],first['a'][2]-dz*160]
        b=[first['a'][0]-dx*32,first['a'][1],first['a'][2]-dz*32]
        sid=add(code+'_depot',a,b,first['heading'],first['heading'],'siding')
        add(code+'_depot_link',b,first['a'],first['heading'],first['heading'],speed=40)
        for i,(s,t) in enumerate(zip(ps,ps[1:])):
            if code=='S1' and i==1:
                portal=[-1720,65,120]
                add(code+'_section_1_descent',s['b'],portal,s['heading'],'N',speed=speed)
                add(code+'_section_1_underpass',portal,t['a'],'N',t['heading'],speed=speed)
            else:add(code+'_section_'+str(i),s['b'],t['a'],s['heading'],t['heading'],speed=speed)
        distance=24 if code=='U2' else 120
        dx,dz=VECT[last['heading']];end=[last['b'][0]+dx*distance,last['b'][1],last['b'][2]+dz*distance]
        add(code+'_turnback',last['b'],end,last['heading'],last['heading'],'turnback')
        route=[p['id'] for p in ps]+[p['id'] for p in ps[-2::-1]]
        lines.append(dict(id=code,name=name,color=color,platforms=route,siding=sid,cars=cars,frequency=2,dwell=8000,repeat=False))
    # Clockwise metropolitan orbital with separate platforms at transfer stations.
    central=station('tokyo_central','第三新東京中央',[-120,80,-200],'E',96,'C1')
    harbour=station('harbour','湾岸・都市防衛区',[320,80,300],'S',96,'C1')
    gate=station('nerv_surface','NERV 表口',[-360,80,680],'W',96,'C1')
    west=station('west_ward','西部市街',[-720,96,200],'N',96,'C1')
    points=[(central['b'],'E'),([272,80,-200],'E'),([320,80,-152],'S'),(harbour['a'],'S')]
    points2=[(harbour['b'],'S'),([320,80,632],'S'),([272,80,680],'W'),(gate['a'],'W')]
    points3=[(gate['b'],'W'),([-672,88,680],'W'),([-720,96,632],'N'),(west['a'],'N')]
    points4=[(west['b'],'N'),([-720,96,80],'N'),([-720,88,-152],'N'),([-672,80,-200],'E'),(central['a'],'E')]
    for part,path in enumerate([points,points2,points3,points4]):
        for i,((a,ha),(b,hb)) in enumerate(zip(path,path[1:])):add(f'C1_{part}_{i}',a,b,ha,hb)
    sid=add('C1_depot',[-944,96,160],[-816,96,160],'E','E','siding')
    add('C1_yard_link',[-816,96,160],[-720,96,80],'E','N',speed=40)
    lines.append(dict(id='C1',name='第三新東京環状線',color=0x426B57,platforms=[p['id'] for p in [central,harbour,gate,west]],siding=sid,cars=metro,frequency=2,dwell=8000,repeat=True))
    shuttle('R1','箱根地域本線',0x476A91,[
        ('hakone_central','新箱根中央',[-1480,104,640],'E',96),
        ('innovation','地域技術センター',[-1080,104,560],'E',96),
        ('west_ward','西部市街',[-680,96,240],'N',96),
        ('tokyo_central','第三新東京中央',[-120,80,-168],'E',96)],intercity,120)
    shuttle('A1','箱根湾空港快速',0xA98647,[
        ('tokyo_central','第三新東京中央',[-120,80,-136],'E',96),
        ('harbour','湾岸・都市防衛区',[360,80,300],'S',96),
        ('south_ward','南部住宅区',[180,80,760],'S',96),
        ('airport','箱根湾空港',[740,65,1190],'E',96)],metro,110)
    shuttle('S1','新箱根空港連絡線',0x986873,[
        ('hakone_central','新箱根中央',[-1480,104,672],'W',96),
        ('hakone_civic','新箱根市民広場',[-1720,104,360],'N',96),
        ('hakone_airfield','新箱根飛行場',[-1670,65,-265],'E',96)],metro,100)
    shuttle('U1','NERV 本部連絡線',0xAE553D,[
        ('geo_arrival','GEOFRONT 入構駅',[-330,-467,785],'E',64),
        ('hq','NERV 本部',[30,-467,490],'E',64),
        ('science','研究・シミュレーション区',[310,-467,565],'S',64)],tram,60)
    shuttle('U2','NERV 整備循環線',0x718D8C,[
        ('hq','NERV 本部',[30,-467,522],'E',64),
        ('logistics','整備補給センター',[300,-467,180],'N',64),
        ('hangar','EVA ケイジ',[150,-443,-40],'W',64)],tram,60)
    # Paired one-way runways and taxi loops; MTR creates the airborne connection.
    air_platforms=[]
    for ap,ox,rz,mirror,name in [('bay',480,1430,False,'箱根湾空港'),('hakone',-2160,-20,True,'新箱根飛行場')]:
        def xyz(u,v):return [ox+(720-u if mirror else u),80,rz+v]
        def heading(h):return {'E':'W','W':'E','N':'N','S':'S'}[h] if mirror else h
        def ar(id,a,b,ha,hb,kind='rail',speed=40,reverse_speed=0):
            return add('F1_'+ap+'_'+id,xyz(*a),xyz(*b),heading(ha),heading(hb),kind,'AIRPLANE',speed,reverse_speed)
        gate_id=ar('gate',(150,-190),(190,-190),'E','E','platform')
        air_platforms.append(gate_id)
        outbound=[((190,-190),'E'),((640,-190),'E'),((680,-150),'S'),((680,-40),'S'),((640,0),'W')]
        inbound=[((640,60),'E'),((680,60),'E'),((720,20),'N'),((720,-230),'N'),((680,-270),'W'),((80,-270),'W'),((40,-230),'S'),((80,-190),'E'),((112,-190),'E'),((150,-190),'E')]
        for section,path in [('taxi_out',outbound),('taxi_in',inbound)]:
            for i,((a,ha),(b,hb)) in enumerate(zip(path,path[1:])):ar(section+str(i),a,b,ha,hb)
        ar('takeoff',(640,0),(40,0),'W','W','runway',220,0)
        ar('landing',(40,60),(640,60),'E','E','runway',180,0)
        if ap=='bay':
            air_siding=ar('depot',(32,-130),(96,-130),'E','E','siding')
            ar('yard_link',(96,-130),(112,-190),'E','E')
        key='airport' if ap=='bay' else 'hakone_airfield'
        station_bounds[key]=dict(id=key,name=name,min=[ox-10,50,rz-310],max=[ox+740,118,rz+100])
        platform_info.append(dict(id=gate_id,station=key,name=name,center=xyz(170,-190),heading=heading('E'),length=40,line='F1',mode='AIRPLANE'))
    lines.append(dict(id='F1',name='箱根湾・新箱根連絡便',color=0x7993A4,mode='AIRPLANE',platforms=air_platforms,
                      siding=air_siding,cars=[car('a320',30,-14.25,-2,0,0)],frequency=1,dwell=20000,repeat=True,cruise=240))
    plan=dict(revision=1,rails=rails,stations=list(station_bounds.values()),platforms=platform_info,lines=lines)
    (OUT/'transit_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Native transit contract:',len(rails),'rails;',len(lines),'lines;',len(platform_info),'platforms')

if __name__=='__main__':main()
