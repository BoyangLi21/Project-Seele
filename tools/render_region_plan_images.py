"""Two annotated planning images, using scanned ground and authored facility bounds."""
from pathlib import Path
import json,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from quality_structures import ROOT,OUT,OLD,load

DEST=OUT/'maps';DEST.mkdir(exist_ok=True)
W,H=1800,1380;BG=(241,240,230);INK=(37,55,51);MUTED=(89,108,99)
FONT='C:/Windows/Fonts/msyh.ttc';BOLD='C:/Windows/Fonts/msyhbd.ttc'
def font(n,bold=False):return ImageFont.truetype(BOLD if bold else FONT,n)
COLORS={'C1':(58,109,86),'R1':(60,104,150),'A1':(157,121,49),'S1':(128,94,148),'S2':(205,131,49),'U1':(171,75,60),'U2':(66,129,134)}

class Map:
    def __init__(self,bounds,title,subtitle):
        self.bounds=bounds;x0,x1,z0,z1=bounds;self.scale=min(1210/(x1-x0),1050/(z1-z0));self.left=70+(1210-(x1-x0)*self.scale)/2;self.top=185+(1050-(z1-z0)*self.scale)/2
        self.im=Image.new('RGB',(W,H),BG);self.d=ImageDraw.Draw(self.im)
        self.d.text((64,40),title,font=font(49,True),fill=INK);self.d.text((66,108),subtitle,font=font(25),fill=MUTED)
        self.d.line((65,153,1730,153),fill=(188,195,181),width=2)
    def pos(self,x,z):return self.left+(x-self.bounds[0])*self.scale,self.top+(z-self.bounds[2])*self.scale
    def box(self,b,fill,outline=None,width=1):
        x0,x1,z0,z1=b;self.d.rectangle((*self.pos(x0,z0),*self.pos(x1,z1)),fill=fill,outline=outline,width=width)
    def line(self,points,color,width=3,dash=False):
        p=[self.pos(x,z) for x,z in points]
        if not dash:self.d.line(p,fill=color,width=width,joint='curve');return
        progress=0
        for a,b in zip(p,p[1:]):
            length=math.dist(a,b);steps=max(1,math.ceil(length/3))
            for i in range(steps):
                if int(progress/8)%2==0:
                    t=i/steps;u=(i+1)/steps;self.d.line((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[0]+(b[0]-a[0])*u,a[1]+(b[1]-a[1])*u),fill=color,width=width)
                progress+=length/steps
    def point(self,number,x,z,label,detail,y,offset=(0,0)):
        px,pz=self.pos(x,z);cx,cz=px+offset[0],pz+offset[1]
        if offset!=(0,0):self.d.line((px,pz,cx,cz),fill=INK,width=2)
        self.d.ellipse((cx-20,cz-20,cx+20,cz+20),fill=BG,outline=INK,width=3)
        t=str(number);bb=self.d.textbbox((0,0),t,font=font(24,True));self.d.text((cx-(bb[2]-bb[0])/2,cz-17),t,font=font(24,True),fill=INK)
        self.d.text((1330,y),f'{number:02d}  {label}',font=font(29,True),fill=INK);self.d.text((1380,y+40),detail.replace('↔','往返'),font=font(23),fill=MUTED)
    def finish(self,name,notes):
        self.d.text((72,1257),'N',font=font(26,True),fill=INK);self.d.line((87,1244,87,1203),fill=INK,width=3);self.d.polygon([(87,1193),(81,1207),(93,1207)],fill=INK)
        length=500 if self.bounds[1]-self.bounds[0]>2000 else 100;px=150;py=1232
        self.d.line((px,py,px+length*self.scale,py),fill=INK,width=4)
        for xx in (px,px+length*self.scale):self.d.line((xx,py-6,xx,py+6),fill=INK,width=3)
        self.d.text((px,py+13),f'{length} 格',font=font(23),fill=MUTED)
        self.d.text((65,1310),notes,font=font(23),fill=MUTED)
        self.im.save(DEST/name);print(DEST/name,flush=True)

def surface():
    m=Map((-3070,1370,-1300,1650),'地上区域规划','R02 修复版 · 两座城市 / 双机场 / 霧里住宅区 / NERV 地表入口')
    step=4;xg=np.arange(m.bounds[0],m.bounds[1]+1,step);zg=np.arange(m.bounds[2],m.bounds[3]+1,step);height=np.full((len(zg),len(xg)),np.nan)
    for target,source in [('terrain_target.npz','surface_levels_expanded_current.npz'),('extension_terrain_target.npz','surface_levels_extension_before.npz')]:
        a=np.load(OUT/target);s=np.load(OUT/source);h=a['height'];known=s['known'];ox,oz=map(int,a['origin']);ix=xg-ox;iz=zg-oz;xx=np.flatnonzero((ix>=0)&(ix<h.shape[1]));zz=np.flatnonzero((iz>=0)&(iz<h.shape[0]))
        values=h[np.ix_(iz[zz],ix[xx])];ok=known[np.ix_(iz[zz],ix[xx])]&(values>-1000);dest=height[np.ix_(zz,xx)];dest[ok]=values[ok];height[np.ix_(zz,xx)]=dest
    rgb=np.zeros((*height.shape,3),np.uint8);rgb[:]=(223,226,216);ok=np.isfinite(height);t=np.clip((np.nan_to_num(height,nan=64)-64)/95,0,1)
    for k,(lo,hi) in enumerate(zip((209,216,186),(127,153,121))):rgb[:,:,k][ok]=(lo+(hi-lo)*t[ok]).astype(np.uint8)
    rgb[ok&(height<63)]=(132,177,188)
    a=m.pos(m.bounds[0],m.bounds[2]);b=m.pos(m.bounds[1],m.bounds[3]);base=Image.fromarray(rgb).resize((round(b[0]-a[0]),round(b[1]-a[1])),Image.Resampling.BILINEAR);m.im.paste(base,(round(a[0]),round(a[1])));m.d=ImageDraw.Draw(m.im)
    for zone in load(OLD/'regional_plan.json')['zones']:
        if zone['kind']=='district':m.box(zone['bounds'],None,(152,166,149),2)
    old=load(OLD/'map/surface.json');codes=np.frombuffer(old['codes'].encode(),dtype=np.uint8).reshape(old['nz'],old['nx'])-48
    for iz,ix in zip(*np.nonzero(codes==5)):
        x,z=old['x']+int(ix)*old['step'],old['z']+int(iz)*old['step']
        if -210<=x<=270 and -20<=z<=464:m.box((x,x+16,z,z+16),(112,126,120))
    for b in load(OUT/'surface_layout.json')['kept_plots']:
        m.box(b['bounds'],(119,150,112) if b['style']=='park' else (119,131,132),(84,102,101))
    e=load(OUT/'extension_plan.json')
    for b in e['estate']['blocks']:m.box(b['bounds'],(171,160,135),(99,96,85),2)
    for sx,ox,rz in [(740,480,1430),(-1670,-2160,-20)]:
        m.box((ox-10,ox+730,rz-300,rz+95),(179,186,180),(119,135,131),2)
        m.box((sx-100,sx+100,rz-380,rz-305),(228,226,203),(98,120,117),2)
        for z in (rz,rz+60):m.box((ox+25,ox+655,z-18,z+18),(61,73,74));m.line([(ox+35,z),(ox+645,z)],(238,236,213),2,True)
    for x,z,xx,zz,width in load(OUT/'road_plan.json')['segments']:m.line([(x,z),(xx,zz)],(116,123,116),2)
    for r in e['roads']:m.line([(p[0],p[2]) for p in r['points']],(113,116,106),2)
    rails=[r for r in load(OLD/'transit2/track_samples.json') if r['id']!='S1_section_1_underpass']
    rails += [r for r in load(OUT/'airport_rail_splice_prototype/track_samples.json') if r['id'].startswith('S1_tunnel_')]
    for rail in rails:
        if rail['mode']!='TRAIN' or max(v[1] for v in rail['points'])<0:continue
        m.line([(p[0],p[2]) for p in rail['points'][::3]+[rail['points'][-1]]],COLORS[rail['id'].split('_')[0]],4,min(v[1] for v in rail['points'])<75)
    for rail in load(OUT/'estate_transit_draft/track_samples.json'):m.line([(p[0],p[2]) for p in rail['points'][::3]+[rail['points'][-1]]],COLORS['S2'],4)
    items=[(1,-2752,-1040,'霧里独立住宅区','6 栋旧公寓 · A 栋 402 室'),(2,-1610,925,'新箱根 · 第二城市','城区 Y=105 · R1 / S1'),(3,-1670,-360,'新箱根飞行场','地面 Y=81 · 地下站 Y=66'),(4,30,220,'第三新东京市','保留升降核心 / 周边扩建街区'),(5,740,1090,'箱根湾机场','地面 Y=81 · A1 / F1'),(6,-360,750,'NERV 正式入口','刷卡 → 大电梯 → 地下'),(7,-700,220,'西部市街换乘站','C1 / R1 · 本次截图位置'),(8,30,-35,'EVA 地表发射区','三处发射井 · Y=81'),(9,-1496,748,'S2 新箱根换乘站','接既有车站 · 已通过载人测试'),(10,-120,-168,'第三新东京中央站','C1 / R1 / A1'),(11,340,300,'湾岸换乘区','C1 / A1 · 临海街区')]
    for i,x,z,label,detail in items:m.point(i,x,z,label,detail,200+(i-1)*91)
    m.d.text((140,190),'橙色 S2：霧里住宅区通勤线已接入',font=font(25,True),fill=COLORS['S2'])
    m.finish('surface-plan.png','X / Z 为游戏坐标；Y 为行走高度。底图来自存档地形扫描；浅灰区未纳入本次测绘。虚线表示部分地下轨道。')

def underground():
    m=Map((-700,450,-200,930),'地下核心设施规划','不同高程叠绘 · 轨道、步行通道、直梯与房间之间的连接')
    a=load(OLD/'map/underground.json');codes=np.frombuffer(a['codes'].encode(),dtype=np.uint8).reshape(a['nz'],a['nx'])-48
    palette=np.asarray([(226,230,219),(190,202,187),(127,173,184),(150,177,140),(203,194,164),(154,166,156)],np.uint8)
    image=Image.fromarray(palette[codes]);lo=m.pos(a['x'],a['z']);hi=m.pos(a['x']+a['nx']*a['step'],a['z']+a['nz']*a['step']);m.im.paste(image.resize((round(hi[0]-lo[0]),round(hi[1]-lo[1])),Image.Resampling.NEAREST),(round(lo[0]),round(lo[1])));m.d=ImageDraw.Draw(m.im)
    old=load(OLD/'geometry_all/places.json');rooms=[r for r in old['rooms'] if not r['id'].startswith('hq/')]+load(OUT/'circulation_repair/places.json')['rooms']
    for box in {tuple(r['bounds']) for r in rooms}:m.box(box,(225,221,201),(121,127,107),2)
    for box in [(-34,94,393,430),(-403,-315,710,741),(213,288,590,684),(-62,110,-166,12)]:m.box(box,(201,205,187),(103,130,119),2)
    seen=set()
    for r in load(OUT/'walk_cases_circulation.json'):
        a,b=r['start'],r['end'];key=tuple(sorted((tuple(a),tuple(b))))
        if key in seen:continue
        seen.add(key);m.line([(a[0],a[2]),(b[0],b[2])],(185,142,55) if a[1]!=b[1] else (231,210,145),5)
    for rail in load(OLD/'transit2/track_samples.json'):
        if rail['id'].startswith(('U1_','U2_')):m.line([(p[0],p[2]) for p in rail['points'][::2]+[rail['points'][-1]]],COLORS[rail['id'].split('_')[0]],5)
    for p in load(OLD/'transit_plan.json')['platforms']:
        if p['center'][1]>=0:continue
        x,y,z=p['center'];m.d.ellipse((*m.pos(x-4,z-4),*m.pos(x+4,z+4)),fill=BG,outline=INK,width=2)
    items=[(1,30,325,'金字塔 / 指挥中枢','总部大厅行走层 Y=-461'),(2,-49,333,'两翼 16 间功能房','B2：-461 / B1：-448'),(3,30,506,'总部换乘站','U1 / U2 · Y=-466'),(4,30,-95,'EVA 机库 / 发射设施','主平台 Y=-442'),(5,150,-40,'EVA 机库站','U2 · Y=-442'),(6,220,180,'整备 / LCL / 动力区','服务走廊 Y=-466'),(7,350,500,'研究与分析区','分析 / 医疗 / 档案 · -466'),(8,250,641,'Sigma 试验厅','Pribnow 试验单元 · -466'),(9,-360,750,'地下到达厅 / 大电梯','Y=-466 ↔ 地面 81'),(10,130,273,'保留的地表直梯','Y=-442 ↔ 地面 81'),(11,72,273,'深层教义区入口','直梯下行至 Y=-566')]
    for i,x,z,label,detail in items:m.point(i,x,z,label,detail,200+(i-1)*91,(-62,0) if i==2 else (0,0))
    m.d.text((135,190),'红：U1 本部线   青：U2 整备线   金：步行 / 楼梯',font=font(25,True),fill=INK)
    m.finish('underground-plan.png','本图聚焦地下核心设施；交叉线不代表同层平交。主要高差：到达层 -466 → 总部 -461 → 两翼 -448 → 机库通道 -442。')

if __name__=='__main__':surface();underground()
