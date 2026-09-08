"""Survey the generated coast at one-block resolution before harbor planning."""
import json,argparse
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scan_regional_completion import volume,AIR
from regional_voxels import ROOT,WORLD

OUT=ROOT/'artifacts/world_motion_r06/harbour';OUT.mkdir(parents=True,exist_ok=True)
LO=(400,32,64);HI=(975,255,527)
def main():
    a,pal=volume(LO,HI)
    empty=np.asarray([s.split('[')[0] in AIR or s.startswith('minecraft:light[') for s in pal])[a]
    top=255-np.argmax(~empty[::-1],axis=0);zz,xx=np.indices(top.shape);top_code=a[top-32,zz,xx]
    water=np.asarray([s.startswith('minecraft:water') for s in pal])[top_code]
    bed=np.asarray([s.split('[')[0] not in AIR and not any(t in s for t in ('water','kelp','seagrass','light[')) for s in pal])[a]
    seabed=255-np.argmax(bed[::-1],axis=0)
    np.savez_compressed(OUT/'coast.npz',top=top,water=water,seabed=seabed,top_code=top_code,palette=np.array(pal),lo=LO,hi=HI)
    rgb=np.empty((*top.shape,3),dtype=np.uint8)
    shade=np.clip((top-62)/70,0,1)
    for n,(low,high) in enumerate(zip((153,172,129),(75,104,80))):rgb[:,:,n]=(low*(1-shade)+high*shade).astype(np.uint8)
    depth=top-seabed;v=np.clip(depth/16,0,1)
    for n,(low,high) in enumerate(zip((133,193,198),(38,100,136))):rgb[:,:,n][water]=(low*(1-v[water])+high*v[water]).astype(np.uint8)
    built=np.asarray([not any(t in s for t in ('stone','dirt','grass','sand','gravel','water','leaves','log','seagrass','kelp','air')) for s in pal])[top_code]
    rgb[built]=[172,173,172]
    scale=2;w=top.shape[1]*scale;h=top.shape[0]*scale
    im=Image.new('RGB',(w+200,h+200),'#f3f1e9');im.paste(Image.fromarray(rgb).resize((w,h)),(100,100));d=ImageDraw.Draw(im)
    font=lambda n:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
    d.text((100,25),'海湾港区 · 逐格实测岸线与水深',font=font(29),fill='#20383b')
    for x in range(LO[0],HI[0]+1,64):
        u=100+(x-LO[0])*scale;d.line((u,100,u,h+100),fill='#a2ada4',width=1);d.text((u-16,70),str(x),font=font(14),fill='#20383b')
    for z in range(LO[2],HI[2]+1,64):
        y=100+(z-LO[2])*scale;d.line((100,y,w+100,y),fill='#a2ada4',width=1);d.text((54,y-10),str(z),font=font(14),fill='#20383b')
    d.text((100,h+122),'蓝色：实测水面（越深颜色越深）  绿色：现有陆地  灰色：既有设施',font=font(21),fill='#20383b')
    d.text((100,h+156),'北 ↑   每格对应 1 方块；海面约 Y=63。本图尚未叠加港口方案。',font=font(20),fill='#506066')
    im.save(OUT/'coast_measured.png')
    (OUT/'survey.json').write_text(json.dumps(dict(world=str(WORLD),bounds=[LO,HI],columns=top.size,water_columns=int(water.sum()),sea_levels=np.unique(top[water]).tolist(),maximum_depth=int(depth[water].max())),indent=2))
    print('Dense coast',top.size,'columns;',int(water.sum()),'water columns',flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--outer',action='store_true');args=ap.parse_args()
    if args.outer:
        OUT=OUT/'outer';OUT.mkdir(exist_ok=True);LO=(1008,32,64);HI=(1631,255,703)
    main()
