"""Readable multi-angle sheets from measured save geometry, with drawing cuts identified."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_refinement_r09';DIR=OUT/'facilities'
FONT='C:/Windows/Fonts/msyh.ttc';font=lambda n:ImageFont.truetype(FONT,n)
SHEETS={
 'pyramid':('NERV 金字塔 · 清理与统一涂装',[
  ('pyramid_exterior','A  完整外壳 · 深色饰面与 NERV 标识'),
  ('pyramid_x_section','B  东侧剖视 · 保留 X≤30'),
  ('pyramid_z_section','C  南侧剖视 · 保留 Z≤327')],
  ['金字塔原轮廓、坡度与高度保持。','东侧长平台已退役，保留工作中的接驳口。','旧高位南门封闭；低位正门继续使用。','会议室窗在本图显示为外侧的实体墙面。','B、C 的剖切仅用于绘图，不是存档破洞。']),
 'terminal_dogma':('TERMINAL DOGMA · 旧球壳清理后',[
  ('dogma_exterior','A  完整压力围护 · 顶部保留'),
  ('dogma_entrance_section','B  北侧剖视 · 围廊、LCL 湖与莉莉丝'),
  ('dogma_longitudinal_section','C  东侧纵剖 · 电梯与观察平台')],
  ['旧球壳及已失效的电梯预留区已清理。','真实电梯仍位于 X=9、Z=253。','前廊 Y=-566；LCL 液面 Y=-601。','莉莉丝位置、比例与朝向保持。','图中省略围岩；剖视不改变实际房间。'])}
def main():
    for name,(title,items,notes) in SHEETS.items():
        im=Image.new('RGB',(2400,1700),'#eef1ee');d=ImageDraw.Draw(im)
        d.text((55,28),title,font=font(43),fill='#202d31')
        d.text((58,90),'R09 · 当前存档方块几何 · XYZ 等比例 · 2026-09-09',font=font(24),fill='#526467')
        for (stem,label),(x,y) in zip(items,[(40,155),(1220,155),(40,915)]):
            d.rounded_rectangle((x,y,x+1140,y+710),radius=12,fill='white')
            source=Image.open(DIR/(stem+'_view.png')).convert('RGB');thumb=ImageOps.contain(source,(1110,635),Image.Resampling.LANCZOS)
            im.paste(thumb,(x+(1140-thumb.width)//2,y+55+(635-thumb.height)//2))
            d.text((x+23,y+15),label,font=font(27),fill='#263d43')
        x,y=1246,965;d.text((x,y),'读图说明',font=font(35),fill='#263d43');y+=73
        for note in notes:
            d.ellipse((x,y+13,x+8,y+21),fill='#bb8e40');d.text((x+25,y),note,font=font(25),fill='#43575b');y+=66
        d.text((1246,1490),'材质作简化显示；实际光照与透明效果请看游戏实景。',font=font(22),fill='#617377')
        d.text((54,1650),'来源：SEELE_TV_WORLD_PREVIEW_20260906 / projectseele:geofront',font=font(21),fill='#617377')
        im.save(OUT/(name+'_multiangle.png'));print(OUT/(name+'_multiangle.png'))
if __name__=='__main__':main()
