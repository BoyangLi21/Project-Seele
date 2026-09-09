"""Original office seating and one continuous tactical map assembled from the current city road plan."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];A=ROOT/'src/main/resources/assets/projectseele'
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def cube(lo,hi,tex):return {'from':lo,'to':hi,'faces':{f:{'texture':tex} for f in ['north','south','east','west','up','down']}}
elements=[cube([4,0,4],[12,2,12],'#metal'),cube([7,2,7],[9,8,9],'#metal'),cube([2,8,2],[14,11,14],'#fabric'),cube([2,10,12],[14,19,15],'#fabric'),cube([1,10,3],[3,13,13],'#metal'),cube([13,10,3],[15,13,13],'#metal')]
save(A/'models/block/nerv_office_chair.json',dict(parent='minecraft:block/block',textures=dict(particle='minecraft:block/gray_wool',fabric='minecraft:block/gray_wool',metal='minecraft:block/black_concrete'),elements=elements))
save(A/'blockstates/nerv_office_chair.json',dict(variants={f'facing={f}':dict(model='projectseele:block/nerv_office_chair',y=r) for f,r in [('north',0),('east',90),('south',180),('west',270)]}))
save(A/'models/item/nerv_office_chair.json',dict(parent='projectseele:block/nerv_office_chair'))
im=Image.new('RGB',(768,256),'#081b17');d=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',16);small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',11)
for x in range(12,570,24):d.line((x,40,x,239),fill='#17392d')
for y in range(42,240,24):d.line((12,y,567,y),fill='#17392d')
d.rectangle((4,4,763,251),outline='#67876b',width=2);d.text((15,12),'NERV / TACTICAL OPERATIONS',font=font,fill='#d8bc73');d.line((13,34,753,34),fill='#997f47')
road=json.loads((ROOT/'artifacts/world_quality_r02/road_plan.json').read_text(encoding='utf8'))['segments']
def xy(x,z):return (int(20+(x+800)/1300*535),int(49+(z+560)/1570*188))
for x,z,xx,zz,width in road:
 if max(x,xx)<-800 or min(x,xx)>500 or max(z,zz)<-560 or min(z,zz)>1010:continue
 a=xy(max(-800,min(500,x)),max(-560,min(1010,z)));b=xy(max(-800,min(500,xx)),max(-560,min(1010,zz)));d.line((*a,*b),fill='#58876b',width=2)
site=xy(356,-450);d.ellipse((site[0]-9,site[1]-9,site[0]+9,site[1]+9),outline='#e8b968',width=2);d.line((site[0]-16,site[1],site[0]+16,site[1]),fill='#cf6850');d.text((site[0]-73,site[1]+14),'INTERCEPT 06',font=small,fill='#d8b66e')
d.rectangle((578,45,753,238),outline='#638770');d.text((590,56),'EVA-01 / SORTIE',font=font,fill='#d8bc73');d.text((590,85),'TARGET: SACHIEL\nAT FIELD: ACTIVE\n\nCITY EVACUATION\nACCESS: NORTH-EAST\n\nSECTOR 06\nX 356 / Z -459',font=small,fill='#90bb94',spacing=4)
im.save(A/'textures/block/nerv_briefing_display.png')
variants={}
for row in range(4):
 for col in range(12):
  part=row*12+col;faces={f:dict(texture='#case',cullface=f) for f in ['north','south','east','west','up','down']}
  for side in ['north','south']:faces[side]=dict(texture='#display',cullface=side,uv=[col*16/12,row*4,(col+1)*16/12,(row+1)*4])
  save(A/'models/block'/f'nerv_briefing_tile_{part}.json',dict(ambientocclusion=False,textures=dict(case='minecraft:block/black_concrete',particle='minecraft:block/black_concrete',display='projectseele:block/nerv_briefing_display'),elements=[dict(**{'from':[0,0,0],'to':[16,16,16]},shade=False,faces=faces)]));variants[f'part={part}']=dict(model=f'projectseele:block/nerv_briefing_tile_{part}')
save(A/'blockstates/nerv_briefing_tile.json',dict(variants=variants));save(A/'models/item/nerv_briefing_tile.json',dict(parent='projectseele:block/nerv_briefing_tile_0'))
for lang,labels in [('zh_cn',['NERV 工作椅','NERV 作战地图屏']),('en_us',['NERV Office Chair','NERV Tactical Display'])]:
 p=A/'lang'/f'{lang}.json';data=json.loads(p.read_text(encoding='utf8'))
 for key,v in zip(['nerv_office_chair','nerv_briefing_tile'],labels):data['block.projectseele.'+key]=v
 save(p,data)
