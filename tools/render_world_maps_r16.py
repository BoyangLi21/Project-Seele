"""Two annotated maps from the current save, including the remote UN installation.

All block IO is centralized in query_blocks. Missing chunks stay visibly unknown.
Underground projections require measured open space above the surface, so natural
ceiling rock is not mistaken for the facility floor. Insets declare their cut level.
"""
from pathlib import Path
import argparse,json,time,msvcrt
from itertools import groupby
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from query_blocks import iter_selected_sections,AIR
from regional_voxels import ROOT,WORLD,DIM

OUT=ROOT/'artifacts/tv_facilities_r16/maps';OUT.mkdir(parents=True,exist_ok=True)
FONT=FontProperties(fname='C:/Windows/Fonts/msyh.ttc');BG='#131e26';INK='#e9e2cd';GOLD='#e4ba73';MUTED='#9eafb0'
EMPTY=AIR|{'minecraft:light','minecraft:barrier','projectseele:geofront_skyweave'}
def colour(state):
 s=state.split('[')[0]
 palette=[('lcl',(123,60,85)),('water',(43,83,102)),('leaves',(65,98,76)),('grass',(91,115,83)),('fern',(91,115,83)),('podzol',(92,91,67)),('dirt',(112,104,82)),('sand',(184,171,126)),('snow',(225,226,216)),('log',(90,78,64)),('planks',(142,127,99)),('machine_panel',(101,114,96)),('shaft_panel',(59,70,91)),('machine_edge',(155,163,152)),('structural_panel',(59,66,68)),('pyramid',(42,48,52)),('black_concrete',(32,38,43)),('white_concrete',(202,207,196)),('light_gray',(157,165,159)),('gray_concrete',(104,114,112)),('cyan',(83,124,125)),('blue',(54,78,105)),('green',(79,102,71)),('red',(135,69,63)),('orange',(174,111,60)),('yellow',(193,160,80)),('sea_lantern',(206,224,210)),('strip_light',(206,224,210)),('glass',(109,153,157)),('iron',(154,165,168)),('hazard',(173,127,66)),('floor_panel',(143,154,149)),('wall_panel',(187,193,184)),('deepslate',(66,75,79)),('blackstone',(55,63,66)),('stone',(108,120,119)),('bricks',(118,101,92))]
 for word,c in palette:
  if word in s:return c
 return (116,125,124)

def scan(name,box,ymin,ymax,exposed=False):
 target=OUT/(name+'_measured.npz')
 if target.exists():return np.load(target)
 x0,z0,x1,z1=box;h=np.full((z1-z0+1,x1-x0+1),-999,dtype=np.int16);rgb=np.zeros((*h.shape,3),np.uint8)
 sy0=ymin//16;sy1=(ymax+2)//16;bottom=sy0*16;top=(sy1+1)*16;selection=set(range(sy0,sy1+1))
 selected={(cx,cz):selection for cx in range(x0//16,x1//16+1) for cz in range(z0//16,z1//16+1)}
 iterator=iter_selected_sections(WORLD,DIM,selected,skip_unfinished=True);count=0;start=time.monotonic()
 for (cx,cz),sections in groupby(iterator,key=lambda r:(r[0],r[1])):
  visible=np.zeros((top-bottom,16,16),bool);empty=np.zeros_like(visible);colors=np.zeros((*visible.shape,3),np.uint8)
  for _,_,sy,pal,indices in sections:
   a=indices.reshape(16,16,16);names=[s.split('[')[0] for s in pal];mask=np.array([s not in EMPTY for s in names]);ys=slice(sy*16-bottom,sy*16-bottom+16)
   visible[ys]=mask[a];empty[ys]=~mask[a];colors[ys]=np.array([colour(s) for s in pal],np.uint8)[a]
  eligible=visible.copy()
  if exposed:eligible[:-2]&=empty[1:-1]&empty[2:];eligible[-2:]=False
  eligible[:ymin-bottom]=False;eligible[ymax-bottom+1:]=False
  iy=eligible.shape[0]-1-np.argmax(eligible[::-1],axis=0);valid=eligible.any(0);height=iy+bottom
  ix0=max(x0,cx*16);ix1=min(x1+1,cx*16+16);iz0=max(z0,cz*16);iz1=min(z1+1,cz*16+16)
  src=(slice(iz0-cz*16,iz1-cz*16),slice(ix0-cx*16,ix1-cx*16));dst=(slice(iz0-z0,iz1-z0),slice(ix0-x0,ix1-x0))
  topcolors=colors[iy,np.arange(16)[:,None],np.arange(16)[None,:]];h[dst]=np.where(valid[src],height[src],-999);rgb[dst]=np.where(valid[src][...,None],topcolors[src],0)
  count+=1
  if count%512==0:print(name,'chunks',count,'seconds',round(time.monotonic()-start,1),flush=True)
 known=h!=-999;yy,xx=np.indices(h.shape);ground=np.where(known,h,0).astype(float);dz,dx=np.gradient(ground)
 smooth=known&np.roll(known,1,0)&np.roll(known,-1,0)&np.roll(known,1,1)&np.roll(known,-1,1);shade=np.where(smooth,np.clip(1-dx*.033-dz*.05,.67,1.10),1)
 rgb=np.clip(rgb*shade[...,None],0,255).astype(np.uint8);rgb[~known]=(25,35,41);rgb[(~known)&((xx+yy)%40<2)]=(33,43,48)
 np.savez_compressed(target,rgb=rgb,height=h,known=known,bounds=box,ymin=ymin,ymax=ymax)
 (OUT/(name+'_source.json')).write_text(json.dumps(dict(world=str(WORLD),dimension=DIM,bounds=box,y_range=[ymin,ymax],exposed=exposed,measured_chunks=count,known_columns=int(known.sum()),missing_columns=int((~known).sum())),indent=2))
 print(name,'DONE',count,'chunks',round(time.monotonic()-start,1),'seconds',flush=True);return np.load(target)

def canvas(ax,data):
 x0,z0,x1,z1=data['bounds'];ax.imshow(data['rgb'],extent=[x0,x1+1,z1+1,z0],interpolation='nearest');ax.set_facecolor(BG);ax.tick_params(colors=MUTED,labelsize=8)
 for s in ax.spines.values():s.set_color('#485d63')
 ax.set_xlabel('X / 方块',fontproperties=FONT,color=MUTED,fontsize=9);ax.set_ylabel('Z / 北 ↑',fontproperties=FONT,color=MUTED,fontsize=9)
def label(ax,text,point,position,size=10):
 ax.scatter(*point,s=23,c=GOLD,edgecolors=BG,linewidths=.8,zorder=6)
 ax.annotate(text,xy=point,xytext=position,fontproperties=FONT,fontsize=size,color=INK,ha='center',va='center',bbox=dict(boxstyle='round,pad=.44',fc='#15252d',ec='#8f9d98',alpha=.97,lw=.65),arrowprops=dict(arrowstyle='-',color=GOLD,lw=1.0),zorder=7)
def scale(ax,x,z,length,text):
 ax.plot([x,x+length],[z,z],color=INK,lw=3);ax.plot([x,x],[z-12,z+12],color=INK,lw=1);ax.plot([x+length,x+length],[z-12,z+12],color=INK,lw=1);ax.text(x+length/2,z-25,text,fontproperties=FONT,fontsize=9,color=INK,ha='center')
def caption(fig,y,text):fig.text(.04,y,text,fontproperties=FONT,color=MUTED,fontsize=9)

def surface(main,base):
 fig=plt.figure(figsize=(18,12),facecolor=BG);fig.text(.04,.956,'地上区域总图',fontproperties=FONT,fontsize=28,color=INK);fig.text(.04,.921,'TOKYO-3  /  NEW HAKONE  /  KIRISATO  /  UN TEST FACILITY',fontsize=11,color=GOLD)
 ax=fig.add_axes([.045,.16,.69,.725]);canvas(ax,main)
 points=[('第三新东京市',(-120,250),(100,-700)),('新箱根市',(-1500,650),(-1510,1270)),('雾里团地\n独立住宅区',(-2750,-955),(-2620,-1270)),('新箱根飞行场',(-1710,-205),(-1930,-690)),('箱根湾空港',(770,1245),(800,1580)),('正式 NERV 入构设施\n大电梯 → 地下入构站',(-360,750),(-545,1370)),('湾岸港区\n晓级驱逐舰靠泊',(1430,420),(1510,920)),('第三新东京中央站',(-120,-200),(-680,-1000)),('EVA 地表出入口',(30,-36),(620,-190))]
 for text,p,q in points:label(ax,text,p,q)
 scale(ax,-2910,1510,500,'500 方块')
 # P1 geometry is the saved, commissioned native MTR track sample, not a
 # fabricated straight line between station labels.
 path=ROOT/'artifacts/world_expansion_r07/port_native_transit/track_samples.json'
 for rail in json.loads(path.read_text()):
  if rail['kind'] not in ('siding','depot'):
   pts=np.array(rail['points']);ax.plot(pts[:,0],pts[:,2],color='#dda965',lw=.85,alpha=.85)
 label(ax,'P1 湾岸联络线',(856,473),(920,775),9)
 bx=fig.add_axes([.78,.32,.18,.50]);canvas(bx,base);bx.set_title('UN 远郊军事基地',fontproperties=FONT,color=INK,fontsize=16,pad=14)
 markers=[(1,6430,-6580),(2,6640,-6569),(3,6634,-6380),(4,6442,-6205),(5,6784,-6340),(6,6560,-5964)]
 for i,x,z in markers:bx.text(x,z,str(i),ha='center',va='center',fontsize=10,color=INK,bbox=dict(boxstyle='circle,pad=.25',fc=BG,ec=GOLD,lw=1.2))
 fig.text(.78,.273,'1 管制与人员区     2 军机防护库\n3 装甲车辆整备     4 EVA-UN 试验机库\n5 跑道与滑行道     6 基地入口\n周界设有防御岗楼与巡逻岗位',fontproperties=FONT,fontsize=10,color=INK,linespacing=1.9)
 loc=fig.add_axes([.78,.835,.18,.072]);loc.set_facecolor('#1a2930');loc.plot([-120,6442],[220,-6320],color=GOLD,lw=.9,ls='--');loc.scatter([-120,6442],[220,-6320],c=[INK,GOLD],s=20);loc.set_xlim(-3100,7200);loc.set_ylim(1800,-7000);loc.set_xticks([]);loc.set_yticks([]);loc.text(-2700,-5800,'同一坐标系\n基地在主城东北约 9 千格',fontproperties=FONT,fontsize=8,color=INK)
 caption(fig,.084,'R16 · 当前存档方块顶面测绘。基地另附放大图；右上小图表示实际相对位置。')
 caption(fig,.055,'暗色斜纹为尚未测得完整区块的范围；活动车辆、人物与机械用位置标注表示。底图不使用远景缓存。')
 fig.savefig(OUT/'surface_map_r16.png',dpi=175,facecolor=BG);plt.close(fig)

def underground(main,cages,dogma):
 fig=plt.figure(figsize=(18,12),facecolor=BG);fig.text(.04,.956,'地下区域总图',fontproperties=FONT,fontsize=28,color=INK);fig.text(.04,.921,'GEOFRONT  /  NERV HEADQUARTERS  /  EVA CAGES  /  TERMINAL DOGMA',fontsize=11,color=GOLD)
 ax=fig.add_axes([.045,.14,.685,.745]);canvas(ax,main)
 labels=[('NERV 金字塔本部',(30,327),(-95,130)),('三机整备机库',(30,-96),(-340,-207)),('发射区 · 三条地表井道',(30,-36),(390,-180)),('本部电车站',(30,490),(-30,630)),('研究与模拟设施',(295,550),(520,738)),('整备补给区',(285,180),(540,230)),('正式入构大电梯\n地下入构站',(-360,750),(-560,942)),('地下湖与自然景观',(-540,360),(-695,170)),('深层电梯\n通往 Terminal Dogma',(12,253),(-280,385))]
 for t,p,q in labels:label(ax,t,p,q,10)
 scale(ax,-850,890,200,'200 方块')
 cx=fig.add_axes([.775,.545,.19,.28]);canvas(cx,cages);cx.set_title('机库作业层',fontproperties=FONT,fontsize=15,color=INK,pad=12);cx.set_xlabel('剖切上限 Y=-394',fontproperties=FONT,color=MUTED,fontsize=9)
 for name,x in [('00',-12),('01',30),('02',72)]:cx.text(x,-96,name,ha='center',va='center',fontsize=10,color=INK,bbox=dict(fc=BG,ec=GOLD,boxstyle='round,pad=.2'))
 cx.annotate('转运 → 弹射井',xy=(30,-36),xytext=(30,-58),fontproperties=FONT,fontsize=8,color=INK,ha='center',arrowprops=dict(arrowstyle='->',color=GOLD))
 dx=fig.add_axes([.775,.20,.19,.28]);canvas(dx,dogma);dx.set_title('Terminal Dogma',fontsize=15,color=INK,pad=12);dx.set_xlabel('剖切上限 Y=-566',fontproperties=FONT,color=MUTED,fontsize=9)
 label(dx,'莉莉丝 / 红十字架',(30.5,355.5),(65,420),8);label(dx,'封印区入口',(12,285),(-20,239),8)
 caption(fig,.082,'R16 · 主图投影地下暴露表面；右侧分层图剖开上方围护，以显示作业层和深层封印室。')
 caption(fig,.055,'大指挥室、会客厅与原有单向窗保留。金字塔、机库、发射区及深层设施均位于地下；地表出口见地上图。')
 fig.savefig(OUT/'underground_map_r16.png',dpi=175,facecolor=BG);plt.close(fig)

def main():
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  town=scan('surface',(-3072,-1360,1800,1695),0,319)
  base=scan('un_base',(6260,-6770,6960,-5870),32,255)
  geo=scan('geofront',(-950,-270,780,1040),-514,-300,True)
  cages=scan('cages',(-36,-134,96,-17),-447,-394,True)
  dogma=scan('dogma',(-60,220,130,450),-645,-566,True)
 surface(town,base);underground(geo,cages,dogma);print('TWO MAPS READY',OUT,flush=True)
if __name__=='__main__':main()
