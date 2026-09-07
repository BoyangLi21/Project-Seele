"""Author the regional construction contract; geometry is applied in later stages."""
from pathlib import Path
import json,math

ROOT=Path(__file__).resolve().parents[1]
WORLD=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'
OUT=ROOT/'artifacts/world_expansion_20260907'

def main():
    survey=json.loads((OUT/'native_surface_survey.json').read_text())
    zones=[
        dict(id='tokyo_west',kind='district',bounds=[-760,-230,-160,760],floor=92,style='mixed_residential',spacing=56),
        dict(id='tokyo_north',kind='district',bounds=[-620,300,-520,-160],floor=80,style='civic_commercial',spacing=56),
        dict(id='tokyo_south',kind='district',bounds=[-560,250,520,960],floor=80,style='residential_school',spacing=56),
        dict(id='harbour_ward',kind='district',bounds=[280,440,80,580],floor=80,style='waterfront',spacing=56),
        dict(id='new_hakone',kind='district',bounds=[-1880,-1120,300,1020],floor=104,style='regional_city',spacing=64),
        dict(id='bay_airport',kind='airport',bounds=[500,1220,1050,1500],floor=80,runway=[540,1180,1430],terminal=[740,1160]),
        dict(id='hakone_airfield',kind='airport',bounds=[-2150,-1450,-320,80],floor=80,runway=[-2110,-1490,-260],terminal=[-1780,-60]),
        dict(id='nerv_surface_gateway',kind='gateway',bounds=[-420,-290,700,820],floor=80),
        dict(id='nerv_arrival',kind='underground_station',bounds=[-450,-250,712,820],floor=-467),
        dict(id='nerv_headquarters_station',kind='underground_station',bounds=[-65,125,460,545],floor=-467),
        dict(id='nerv_science',kind='science',bounds=[195,380,400,660],floor=-467),
        dict(id='nerv_logistics',kind='logistics',bounds=[165,355,70,250],floor=-467),
        dict(id='relocated_eva_plant',kind='eva_plant',bounds=[-62,165,-166,12],floor=-444),
    ]
    stations=[
        dict(id='tokyo_central',name='第三新東京中央',pos=[-120,80,-200],axis='x'),
        dict(id='harbour',name='湾岸・都市防衛区',pos=[320,80,300],axis='z'),
        dict(id='nerv_surface',name='NERV 表口',pos=[-360,80,680],axis='x'),
        dict(id='west_ward',name='西部市街',pos=[-720,96,200],axis='z'),
        dict(id='hakone_central',name='新箱根中央',pos=[-1480,104,640],axis='x'),
        dict(id='innovation',name='地域技術センター',pos=[-1080,104,560],axis='x'),
        dict(id='airport',name='箱根湾空港',pos=[740,80,1190],axis='x'),
        dict(id='south_ward',name='南部住宅区',pos=[180,80,760],axis='z'),
        dict(id='hakone_airfield',name='新箱根飛行場',pos=[-1780,80,-30],axis='x'),
        dict(id='hakone_civic',name='新箱根市民広場',pos=[-1720,104,360],axis='z'),
        dict(id='geo_arrival',name='GEOFRONT 入構駅',pos=[-330,-467,785],axis='x'),
        dict(id='hq',name='NERV 本部',pos=[30,-467,490],axis='x'),
        dict(id='science',name='研究・シミュレーション区',pos=[310,-467,565],axis='z'),
        dict(id='logistics',name='整備補給センター',pos=[300,-467,180],axis='z'),
        dict(id='hangar',name='EVA ケイジ',pos=[150,-443,-40],axis='x'),
    ]
    # Reserve only construction/rail-corridor chunks. Other terrain remains native exploration.
    chunks=set()
    def rect(x0,x1,z0,z1):
        chunks.update((x,z) for x in range(x0//16,x1//16+1) for z in range(z0//16,z1//16+1))
    for zone in zones:
        x0,x1,z0,z1=zone['bounds'];rect(x0-32,x1+32,z0-32,z1+32)
    corridors=[
        [(-720,-200),(320,-200),(320,680),(-720,680),(-720,-200)],
        [(-1550,640),(-1080,560),(-720,240),(-120,-168)],
        [(-120,-136),(360,300),(180,760),(740,1190)],
        [(-1480,670),(-1720,360),(-1780,-30)],
        [(-420,785),(-330,785),(30,490),(310,565)],
        [(30,522),(300,180),(150,-40)],
    ]
    for path in corridors:
        for (ax,az),(bx,bz) in zip(path,path[1:]):
            steps=max(1,math.ceil(math.hypot(bx-ax,bz-az)/16))
            for i in range(steps+1):
                x=round(ax+(bx-ax)*i/steps);z=round(az+(bz-az)*i/steps)
                rect(x-64,x+64,z-64,z+64)
    plan=dict(revision=1,seed=survey['seed'],world=WORLD.name,source_commit='5fb9b6e',
              status='construction_authorized',eva_offset=[0,0,-256],eva_migrated=False,
              main_lift=dict(axis=[-360,750],stops=[-466,81],width=15,height=9,exit='south'),
              zones=zones,stations=stations,coarse_corridors=corridors,
              chunks=[list(p) for p in sorted(chunks,key=lambda p:(p[1],p[0]))],
              interpretation='TV-inspired regional layout; second city and airports are project world-building, not claimed canonical maps')
    OUT.mkdir(exist_ok=True,parents=True)
    (OUT/'regional_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    (WORLD/'regional_plan.json').write_text(json.dumps(plan,ensure_ascii=False),encoding='utf-8')
    print('Regional contract:',len(zones),'zones;',len(stations),'stations;',len(chunks),'construction chunks')

if __name__=='__main__':main()
