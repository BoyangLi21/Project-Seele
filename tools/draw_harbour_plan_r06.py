"""Annotate a port preparation scheme on actual saved coast data, never on invented terrain."""
import json,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
from regional_voxels import ROOT

OUT=ROOT/'artifacts/world_motion_r06/harbour';d=np.load(OUT/'outer/coast.npz');lo=d['lo'];top=d['top'];water=d['water'];bed=d['seabed'];depth=top-bed
FONT=lambda n:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
def measure(box):
    x0,z0,x1,z1=box;s=np.s_[z0-lo[2]:z1-lo[2]+1,x0-lo[0]:x1-lo[0]+1];w=water[s];v=depth[s]
    return dict(box=box,water_fraction=float(w.mean()),minimum_depth=int(v[w].min()),median_depth=float(np.median(v[w])),maximum_depth=int(v[w].max()))
plan=dict(status='PREPARATION_ONLY_NOT_BUILT',world='SEELE_TV_WORLD_PREVIEW_20260906',
    source='399360 individually measured saved columns; sea water top Y62',
    quay=dict(edge_x=1424,z=[344,536],deck_y=64,berths=2,length_each=96,water=measure([1424,344,1456,536])),
    cargo_yard=dict(box=[1304,344,1400,440],deck_y=68),nerv_transfer=dict(box=[1328,456,1400,528],deck_y=68),
    warehouse=dict(box=[1248,344,1296,432],deck_y=68),customs=dict(box=[1248,448,1280,496],deck_y=68),
    basin=dict(centre=[1542,440],radius=82),rail=dict(siding_y=70,maximum_reserved_grade_percent=1.4,
        corridor=[[320,80,300],[440,80,300],[560,79,420],[800,76,432],[1008,74,432],[1168,72,432],[1248,71,432],[1328,70,432]],
        status='Reserved alignment; bridges, curves, MTR trains and signalling not built'),
    links=dict(passengers='C1 Harbour station (320,80,300), connecting road/bus reservation',
               security='Separate NERV badge-controlled yard, matching current HQ access logic in later construction'),
    character='TV industrial / military logistics plus Shimizu white gantries and ordered container rows; an original extension, not a canonical TV harbor',
    next_construction=['Survey bridge abutments and exact rail curves along the reserved approach',
        'Build quay/retaining structure and protected road approach',
        'Build warehouse, cargo yard, station connection and separate NERV gate',
        'Commission rail signalling and vehicles; check vessel clearance before adding ships'])
yy,xx=np.indices(top.shape);circle=(xx+lo[0]-1542)**2+(yy+lo[2]-440)**2<=82**2
plan['basin'].update(water_fraction=float(water[circle].mean()),minimum_depth=int(depth[circle].min()),median_depth=float(np.median(depth[circle])))
(OUT/'harbour_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
rgb=np.zeros((*top.shape,3),np.uint8);shade=np.clip((top-62)/65,0,1)
for n,(a,b) in enumerate(zip((170,185,151),(99,127,100))):rgb[:,:,n]=(a*(1-shade)+b*shade).astype(np.uint8)
v=np.clip(depth/24,0,1)
for n,(a,b) in enumerate(zip((134,195,201),(36,98,130))):rgb[:,:,n][water]=(a*(1-v[water])+b*v[water]).astype(np.uint8)
im=Image.new('RGB',(1536,1080),'#f1f0e8');im.paste(Image.fromarray(rgb),(62,172));draw=ImageDraw.Draw(im)
def text(x,y,s,size=22,fill='#263e44'):draw.text((x,y),s,font=FONT(size),fill=fill)
def xy(x,z):return (62+x-lo[0],172+z-lo[2])
def polygon(box,color,label):
    x0,z0,x1,z1=box;a=xy(x0,z0);b=xy(x1,z1);draw.rectangle((*a,*b),fill=color,outline='#f4df9c',width=2)
    draw.text((a[0]+5,a[1]+5),label,font=FONT(17),fill='#fff9df')
text(62,35,'海湾港区建设准备',40);text(1177,49,'PROJECT SEELE · R06',18)
text(62,99,'底图是现存世界实测；黄色轮廓为拟建区域，本轮尚未建造港口。',23,'#645c44')
for x in range(1072,1632,128):
    u,y=xy(x,64);draw.line((u,172,u,812),fill='#94aaa7');text(u-19,145,str(x),14)
for z in range(64,704,128):
    x,y=xy(1008,z);draw.line((62,y,686,y),fill='#94aaa7');text(16,y-9,str(z),14)
polygon(plan['cargo_yard']['box'],'#727b71','货场 Y68');polygon(plan['nerv_transfer']['box'],'#744e50','NERV')
polygon(plan['warehouse']['box'],'#8d969b','仓库');polygon(plan['customs']['box'],'#8d969b','关务')
polygon([1400,344,1424,536],'#b69a60','')
for z in (375,470):
    a=xy(1412,z);draw.line((*a,*xy(1454,z)),fill='#fcf9e9',width=3);draw.rectangle((a[0]-3,a[1]-5,a[0]+4,a[1]+5),outline='#fcf9e9',width=2)
a=xy(1542-82,440-82);b=xy(1542+82,440+82);draw.ellipse((*a,*b),outline='#f5e4a4',width=3)
text(*xy(1486,413),'回旋水域',17,'#fff4c8');text(*xy(1486,438),'直径 164 格',15,'#fff4c8')
for x in (1232,1240):draw.line((*xy(x,320),*xy(x,536)),fill='#594941',width=3)
route=[xy(1008,432),xy(1180,432),xy(1180,320),xy(1232,320)];draw.line(route,fill='#594941',width=4)
road=[xy(1008,462),xy(1216,462),xy(1216,544),xy(1384,544),xy(1424,544)];draw.line(road,fill='#f5e4a4',width=5)
text(83,756,'N ↑',20);text(83,784,'100 格',15);draw.line((168,801,268,801),fill='#263e44',width=3)
text(753,180,'01  正式泊位放在外侧宽水面',27)
text(753,228,'两座 96 格泊位，码头面 Y64。',22)
text(753,266,f"泊位前实测水深 {plan['quay']['water']['minimum_depth']}–{plan['quay']['water']['maximum_depth']} 格。",22)
text(753,304,f"回旋区全部为水面，最浅 {plan['basin']['minimum_depth']} 格。",22)
text(753,369,'02  日常货运与 NERV 运输分区',27)
text(753,417,'西侧仓库、堆场、关务；南侧独立门禁区。',22)
text(753,455,'白色门式吊机、灰蓝仓库、克制的警戒标识。',22)
text(753,521,'03  连接现有城市与铁路',27)
text(753,569,'C1 港湾站位于 (320, 80, 300)。',22)
text(753,607,'预留道路接驳与货运支线，货运站场 Y70。',22)
text(753,645,'支线纵坡预留 ≤1.4%；桥位和曲线待细化。',22)
text(753,711,'设计依据',23)
text(753,751,'原 TV 的工业设施语汇 + 清水港实际布局。',21)
text(753,786,'此港是世界扩展设计，不冒充原剧完整港口。',21)
draw.line((62,866,1474,866),fill='#c8c9bb',width=2)
text(62,890,'高差分层',24)
for x,label,y in [(220,'城市  Y80',930),(610,'货运站场  Y70',956),(1000,'堆场  Y68',962),(1310,'码头  Y64',974)]:
    draw.line((x,y,x+120,y),fill='#596664',width=5);text(x,y-35,label,19)
draw.line((340,930,610,956),fill='#9b744c',width=3);draw.line((730,956,1000,962),fill='#9b744c',width=3);draw.line((1120,962,1310,974),fill='#9b744c',width=3)
text(62,1020,'图示纵断面为设计标高，非已建成线路；先验证桥梁、支撑和通行，再落地施工。',20,'#655f50')
im.save(OUT/'harbour_plan_r06.png');print('Harbor plan',plan['quay']['water'],plan['basin'],flush=True)
