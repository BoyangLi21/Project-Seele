"""Original pixel hardware faces for the existing TV-style room furniture system."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];A=ROOT/'src/main/resources/assets/projectseele'
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',7)
def save(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
for name in ['nerv_server_rack','nerv_storage_panel','nerv_medical_panel']:
 im=Image.new('RGB',(64,64),'#656b68');d=ImageDraw.Draw(im)
 d.rectangle((1,1,62,62),outline='#333b3a',width=2)
 for x in (4,59):
  for y in (4,59):d.rectangle((x-1,y-1,x,y),fill='#bac0b4')
 if name.endswith('rack'):
  d.rectangle((8,5,55,59),fill='#29312f')
  for y in (9,22,35,48):
   d.rectangle((11,y,52,y+9),fill='#4a514e');d.line((12,y+9,51,y+9),fill='#151d1b')
   for x in range(15,40,4):d.line((x,y+2,x,y+6),fill='#1a2523')
   d.rectangle((45,y+2,47,y+3),fill='#b4cb7e');d.rectangle((49,y+2,50,y+3),fill='#d09e54')
  d.text((12,1),'MAGI I/O',font=font,fill='#d9d4bb')
 elif name.endswith('panel') and 'storage' in name:
  for y in (7,23,39):
   d.rectangle((8,y,55,y+15),fill='#848d88',outline='#3a4441');d.rectangle((23,y+3,39,y+6),fill='#d0c9af');d.line((25,y+11,38,y+11),fill='#282f2e',width=2)
  d.text((18,54),'TECH 03',font=font,fill='#d8d8c7')
 else:
  d.rectangle((7,7,56,38),fill='#182f2b',outline='#a8b1a5',width=2)
  d.line([(10,24),(17,24),(20,21),(23,28),(27,14),(30,32),(34,24),(51,24)],fill='#a3c896',width=1)
  d.text((10,10),'PULSE',font=font,fill='#acccba');d.text((9,43),'LCL / O2',font=font,fill='#e3d5b5')
  for x in (12,23,34):d.ellipse((x,54,x+4,58),fill='#343f3b');d.rectangle((47,51,54,58),fill='#b67358')
 tex=A/'textures/block'/f'{name}.png';tex.parent.mkdir(parents=True,exist_ok=True);im.save(tex)
 save(A/'models/block'/f'{name}.json',dict(parent='minecraft:block/orientable',textures=dict(top='projectseele:block/nerv_wall_panel',front='projectseele:block/'+name,side='projectseele:block/nerv_wall_panel')))
 save(A/'models/item'/f'{name}.json',dict(parent='projectseele:block/'+name))
 save(A/'blockstates'/f'{name}.json',dict(variants={f'facing={f}':dict(model='projectseele:block/'+name,y=r) for f,r in [('north',0),('east',90),('south',180),('west',270)]}))
for lang,labels in [('zh_cn',['NERV 计算机机柜','NERV 技术档案柜','NERV 医疗监护面板']),('en_us',['NERV Computer Rack','NERV Technical Archive','NERV Medical Monitor'])]:
 p=A/'lang'/f'{lang}.json';data=json.loads(p.read_text(encoding='utf8'))
 for name,label in zip(['nerv_server_rack','nerv_storage_panel','nerv_medical_panel'],labels):data['block.projectseele.'+name]=label
 save(p,data)
print('Three original hardware materials authored')
