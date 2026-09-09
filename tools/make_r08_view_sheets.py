"""Compose annotated static multi-angle sheets from the verified 3D renders."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_refinement_r08';DIR=OUT/'facilities'
FONT='C:/Windows/Fonts/msyh.ttc';f=lambda n:ImageFont.truetype(FONT,n)
SHEETS={
 'pyramid':('NERV 金字塔 · 多角度结构图',[
  ('pyramid_exterior','A  完整外壳 · 保留外墙与顶面'),
  ('pyramid_x_section','B  东侧剖视 · 保留 X≤30'),
  ('pyramid_z_section','C  南侧剖视 · 保留 Z≤327')],
  ['塔尖：Y=-294；总部平台：约 Y=-467。','城市基准约 Y=80，金字塔全部位于地下。','人员电梯竖井继续向上，超出本图范围。','两块旧发射井残墙已从实际存档移除。','B、C 的切面仅用于绘图，不是地图破洞。']),
 'hangar':('主机库与发射区 · 多角度结构图',[
  ('hangar_exterior','A  完整机库屋面 · 井筒上段截短显示'),
  ('hangar_bay_section','B  分机位剖视 · 展示栈桥与 LCL 舱'),
  ('hangar_cross_section','C  横向剖视 · 展示三机位的高差关系')],
  ['三座机库保留完整双层顶板：Y=-355/-354。','本轮新增屋面覆板、结构肋与通风设备。','黑色发射井继续到地表，图框截至 Y=-320。','内侧通道、机位、梯道与发射净空保留。','B、C 隐去部分外墙和顶盖，仅为展示内部。']),
 'terminal_dogma':('TERMINAL DOGMA · 多角度结构图',[
  ('dogma_exterior','A  完整压力围护 · 顶部保留'),
  ('dogma_entrance_section','B  北侧剖视 · 入口、LCL 湖与莉莉丝'),
  ('dogma_longitudinal_section','C  东侧纵剖 · 电梯、围廊与观察平台')],
  ['入口观察层：Y=-566；LCL 液面：Y=-601。','标本位置、朝向和比例读取自当前存档。','建筑剖切时，莉莉丝模型完整保留。','地质围岩在图框外；围护不等同于自然洞穴。','深层距离为游戏化压缩，详见原 TV 对照记录。'])}
for name,(title,items,notes) in SHEETS.items():
    im=Image.new('RGB',(2400,1700),'#eef1ee');draw=ImageDraw.Draw(im)
    draw.text((55,28),title,font=f(43),fill='#202d31');draw.text((58,90),'R08 · 当前存档方块几何 · XYZ 等比例 · 2026-09-09',font=f(24),fill='#526467')
    spots=[(40,155),(1220,155),(40,915)]
    for (stem,label),(x,y) in zip(items,spots):
        draw.rounded_rectangle((x,y,x+1140,y+710),radius=12,fill='white')
        source=Image.open(DIR/(stem+'_view.png')).convert('RGB');thumb=ImageOps.contain(source,(1110,635),Image.Resampling.LANCZOS);im.paste(thumb,(x+(1140-thumb.width)//2,y+55+(635-thumb.height)//2))
        draw.text((x+23,y+15),label,font=f(27),fill='#263d43')
    x,y=1246,965;draw.text((x,y),'读图说明',font=f(35),fill='#263d43');y+=73
    for note in notes:
        draw.ellipse((x,y+13,x+8,y+21),fill='#bb8e40');draw.text((x+25,y),note,font=f(25),fill='#43575b');y+=66
    draw.text((1246,1490),'材质作简化显示；实际光照、标牌和活动设备请看游戏实景。',font=f(22),fill='#617377')
    draw.text((54,1650),'来源：SEELE_TV_WORLD_PREVIEW_20260906 / projectseele:geofront',font=f(21),fill='#617377')
    im.save(OUT/(name+'_multiangle.png'))
    print(OUT/(name+'_multiangle.png'))
