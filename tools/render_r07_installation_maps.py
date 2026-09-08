"""Annotated overhead maps from saved world blocks, read only through query_blocks."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from query_blocks import iter_selected_sections,AIR
from regional_voxels import ROOT,WORLD,DIM

OUT=ROOT/'artifacts/world_expansion_r07/maps';OUT.mkdir(exist_ok=True)
FONT=FontProperties(fname='C:/Windows/Fonts/msyh.ttc')
def colour(state):
    s=state.split('[')[0]
    for word,c in [('water','#285c72'),('grass','#53664d'),('dirt','#646153'),('sand','#b5ae8f'),('black_concrete','#252c30'),('white_concrete','#d1d1c4'),('green_terracotta','#626f4c'),('blue_terracotta','#465770'),('red_terracotta','#875b50'),('yellow','#d5b450'),('sea_lantern','#c8e2d2'),('strip_light','#c8e2d2'),('glass','#71918e'),('iron','#8e9b9c'),('hazard','#bc9f53'),('floor_panel','#929c96'),('wall_panel','#c1c5be')]:
        if word in s:return np.array([int(c[i:i+2],16) for i in (1,3,5)],float)
    return np.array([111,121,120],float)
def topmap(box):
    x0,z0,x1,z1=box;h=np.full((z1-z0+1,x1-x0+1),-999,dtype=np.int16);rgb=np.zeros((*h.shape,3),float)
    selected={(cx,cz):set(range(2,11)) for cx in range(x0//16,x1//16+1) for cz in range(z0//16,z1//16+1)}
    for cx,cz,sy,pal,idx in iter_selected_sections(WORLD,DIM,selected):
        a=idx.reshape(16,16,16);visible=np.array([s.split('[')[0] not in AIR|{'minecraft:light','minecraft:barrier'} for s in pal])[a]
        y=15-np.argmax(visible[::-1],axis=0);valid=visible.any(axis=0);height=y+sy*16
        ix0=max(x0,cx*16);ix1=min(x1+1,cx*16+16);iz0=max(z0,cz*16);iz1=min(z1+1,cz*16+16)
        sl=(slice(iz0-cz*16,iz1-cz*16),slice(ix0-cx*16,ix1-cx*16));dest=(slice(iz0-z0,iz1-z0),slice(ix0-x0,ix1-x0))
        win=valid[sl]&(height[sl]>h[dest]);states=a[y,np.arange(16)[:,None],np.arange(16)[None,:]]
        colors=np.array([colour(s) for s in pal])[states];h[dest][win]=height[sl][win];rgb[dest][win]=colors[sl][win]
    assert (h!=-999).all(),'Map contains unmeasured columns'
    dy,dx=np.gradient(h.astype(float));shade=np.clip(1-dx*.045-dy*.065,.68,1.12);rgb=np.clip(rgb*shade[:,:,None],0,255).astype(np.uint8)
    np.savez_compressed(OUT/(('base' if x0>6000 else 'harbor')+'_saved_surface.npz'),height=h,rgb=rgb,bounds=box)
    return rgb
def make(name,box,title,sub,labels):
    rgb=topmap(box);x0,z0,x1,z1=box
    fig,ax=plt.subplots(figsize=(11,12 if name=='base' else 8),facecolor='#152129');ax.set_facecolor('#152129')
    ax.imshow(rgb,extent=[x0,x1+1,z1+1,z0],interpolation='nearest')
    for label,point,position in labels:
        ax.annotate(label,xy=point,xytext=position,fontproperties=FONT,fontsize=11,color='#f0eddf',ha='center',va='center',bbox=dict(boxstyle='round,pad=.5',fc='#18262b',ec='#849895',alpha=.93),arrowprops=dict(arrowstyle='-',color='#ecce7f',lw=1.1))
    ax.set_title(title,fontproperties=FONT,fontsize=20,color='#e6ddc3',loc='left',pad=28)
    ax.text(0,1.025,sub,transform=ax.transAxes,fontproperties=FONT,fontsize=10,color='#a1bab9')
    ax.set_xlabel('X / 方块坐标',fontproperties=FONT,color='#a1bab9');ax.set_ylabel('Z / 方块坐标（上方为北）',fontproperties=FONT,color='#a1bab9')
    ax.tick_params(colors='#9eaeab');ax.spines[['top','right']].set_visible(False)
    for s in ('left','bottom'):ax.spines[s].set_color('#536660')
    fig.text(.11,.02,'R07  |  实際存档方块顶面扫描 · 非游戏截图 · 车辆位置请参照现场实拍',fontproperties=FONT,fontsize=9,color='#95aaa7')
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(OUT/(name+'_map_r07.png'),dpi=170,facecolor=fig.get_facecolor());plt.close(fig)
make('harbor',(1184,288,1655,624),'湾岸港区 · 已建成布置','主港场 Y68 ｜ 靠泊码头 Y64 ｜ 舰上主甲板 Y66',[
    ('P1 港口车站\n向西连接城市',(1192,472),(1244,607)),('物流仓库',(1272,365),(1245,304)),('集装箱作业区',(1348,382),(1351,305)),('港务与海上支援',(1352,490),(1336,582)),('岸桥与装卸码头',(1412,386),(1495,307)),('护航舰 · 110 格\n近防炮 / 直升机',(1444,403),(1568,397)),('补给舰 · 100 格\n舰内楼梯与船员舱',(1444,518),(1568,525)),('可驾驶巡逻艇',(1468,586),(1546,608))])
make('base',(6288,-6736,6911,-5921),'远郊试验基地 · 已建成布置','距第三新东京市约 9.1 千格 ｜ 基地 Y74 ｜ 地表试验机库 Y76',[
    ('基地管制与队员区',(6430,-6580),(6410,-6708)),('自动防御岗楼',(6856,-6680),(6760,-6708)),('航空器防护机库\nJ-16 / KV-16',(6640,-6569),(6640,-6665)),('车辆整备与坦克',(6634,-6380),(6490,-6436)),('608 格跑道\n平行滑行道',(6784,-6340),(6840,-6340)),('地表机密试验格纳库\n未命名 EVA / LCL 排液舱',(6442,-6205),(6420,-6358)),('试验机出舱门\n宽 33 × 高 65',(6442,-6136),(6425,-6076)),('旋翼机停机坪',(6664,-6140),(6745,-6123)),('动力与冷却设备',(6380,-6020),(6410,-5940)),('基地入口',(6560,-5964),(6560,-6008)),('航空联络站',(6652,-6010),(6810,-5980))])
print('Saved native block maps to',OUT)
