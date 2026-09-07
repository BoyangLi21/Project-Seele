"""Orthographic cutaways drawn from saved blocks and native collision boxes.

These are measured geometry illustrations, not Minecraft screenshots. All
Anvil reads go through query_blocks; no source images or textures are used.
"""
import json,math,argparse
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from query_blocks import iter_selected_sections,AIR
from regional_voxels import WORLD,DIM,ROOT
OUT=ROOT/'artifacts/world_quality_r02'
SCENES={
    'west-station':((-746,92,174),(-690,105,230),'WEST STATION / road, platform and footbridge'),
    'airport-section':((739,63,1118),(742,89,1210),'AIRPORT / terminal stair, underpass and rail platform'),
    'hq-stair':((-34,-463,369),(-6,-442,388),'NERV WEST WING / separate stair alcove'),
    'building-stair':((-636,92,188),(-626,109,199),'RESIDENTIAL STAIR / three floors and return landings')}

def color(s):
    n=s.split('[')[0]
    if 'sea_lantern' in n:return (202,236,220)
    if 'black' in n:return (45,48,49)
    if 'red_' in n:return (135,66,54)
    if 'yellow' in n:return (172,145,68)
    if 'glass' in n:return (119,148,148)
    if 'deepslate' in n or 'basalt' in n:return (64,68,70)
    if 'iron' in n:return (162,171,170)
    if 'white' in n or 'quartz' in n:return (203,205,196)
    if 'grass_block' in n:return (94,126,75)
    if 'dirt' in n:return (119,92,63)
    if 'leaf' in n or 'leaves' in n:return (69,103,66)
    if 'oak' in n or 'chest' in n:return (104,80,53)
    if 'light_gray' in n:return (161,165,158)
    if 'concrete' in n:return (123,126,125)
    if 'sand' in n:return (185,171,132)
    if 'water' in n:return (70,122,151)
    return (135,142,136)

def render(key):
    lo,hi,title=SCENES[key];selected={}
    for cx in range(lo[0]//16,hi[0]//16+1):
        for cz in range(lo[2]//16,hi[2]//16+1):selected[cx,cz]=set(range(lo[1]//16,hi[1]//16+1))
    shapes=json.loads((WORLD/'native_collision_shapes.json').read_text(encoding='utf-8'));cells={};full=set()
    for cx,cz,sy,pal,idx in iter_selected_sections(WORLD,DIM,selected):
        a=np.asarray(pal)[idx].reshape(16,16,16)
        for y in range(max(lo[1],sy*16),min(hi[1],sy*16+15)+1):
            for z in range(max(lo[2],cz*16),min(hi[2],cz*16+15)+1):
                for x in range(max(lo[0],cx*16),min(hi[0],cx*16+15)+1):
                    state=str(a[y-sy*16,z-cz*16,x-cx*16])
                    if state in AIR:continue
                    boxes=shapes.get(state,[[0,0,0,1,1,1]])
                    if not boxes:continue
                    cells[x,y,z]=(state,boxes)
                    if boxes==[[0,0,0,1,1,1]]:full.add((x,y,z))
    faces=[]
    for (x,y,z),(state,boxes) in cells.items():
        rgb=color(state)
        for a,b,c,d,e,f in boxes:
            vertices=[(x+a,y+b,z+c),(x+d,y+b,z+c),(x+d,y+e,z+c),(x+a,y+e,z+c),
                      (x+a,y+b,z+f),(x+d,y+b,z+f),(x+d,y+e,z+f),(x+a,y+e,z+f)]
            for inds,normal,brightness,edge in [([1,5,6,2],(1,0,0),.68,d),([3,2,6,7],(0,1,0),1.0,e),([4,7,6,5],(0,0,1),.84,f)]:
                if edge==1 and (x+normal[0],y+normal[1],z+normal[2]) in full:continue
                vs=[vertices[i] for i in inds];depth=sum(sum(v) for v in vs)/4
                points=[((xx-zz)*.8660254,(xx+zz)*.5-yy) for xx,yy,zz in vs]
                faces.append((depth,points,tuple(round(v*brightness) for v in rgb)))
    faces.sort(key=lambda a:a[0]);allpoints=[v for _,points,_ in faces for v in points]
    minx,miny=np.min(allpoints,axis=0);maxx,maxy=np.max(allpoints,axis=0);width,height=1800,1250
    scale=min((width-100)/(maxx-minx),(height-140)/(maxy-miny));padx=(width-(maxx-minx)*scale)/2;pady=95+(height-140-(maxy-miny)*scale)/2
    image=Image.new('RGB',(width,height),(232,233,225));draw=ImageDraw.Draw(image)
    for _,points,rgb in faces:draw.polygon([(padx+(x-minx)*scale,pady+(y-miny)*scale) for x,y in points],fill=rgb)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
    draw.text((38,26),title,font=font,fill=(43,53,49))
    draw.text((38,62),f'Saved block geometry | bounds {lo} to {hi} | native shapes | cutaway',font=small,fill=(73,84,75))
    folder=OUT/'sections';folder.mkdir(exist_ok=True);dest=folder/(key+'.png');image.save(dest)
    print(dest,'visible faces',len(faces),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--scene',choices=list(SCENES)+['all'],default='all');args=ap.parse_args()
    for key in SCENES if args.scene=='all' else [args.scene]:render(key)
