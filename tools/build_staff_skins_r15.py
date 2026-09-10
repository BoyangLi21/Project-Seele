"""Original pixel uniforms extending the existing SEELE human-skin atlas."""
from pathlib import Path
from PIL import Image,ImageDraw
import json
OUT=Path(__file__).resolve().parents[1]/'src/main/resources/assets/projectseele/textures/entity'
HEAD=[(8,0,15,7),(16,0,23,7),(0,8,7,15),(8,8,15,15),(16,8,23,15),(24,8,31,15)]
BODY=[(20,16,27,19),(28,16,35,19),(16,20,19,31),(20,20,27,31),(28,20,31,31),(32,20,39,31)]
ARMS=[(44,16,47,19),(48,16,51,19),(40,20,55,31),(36,48,39,51),(40,48,43,51),(32,52,47,63)]
LEGS=[(4,16,7,19),(8,16,11,19),(0,20,15,31),(20,48,23,51),(24,48,27,51),(16,52,31,63)]
def build(name,coat,hair,skin=(220,181,153),trousers=(38,44,45),un=False,slim=False):
 im=Image.new('RGBA',(64,64));d=ImageDraw.Draw(im)
 def paint(boxes,c):
  for box in boxes:d.rectangle(box,fill=(*c,255))
 paint(HEAD,skin);paint(BODY+ARMS,coat);paint(LEGS,trousers)
 # Face, fringe, directional hair shading and a separately modelled outer fringe.
 paint([HEAD[0],HEAD[2],HEAD[4],HEAD[5]],hair);d.rectangle((8,8,15,10),fill=(*hair,255));d.rectangle((8,11,8,14),fill=(*hair,255))
 for x in (10,13):d.point((x,12),fill=(35,41,52,255));d.point((x+1,12),fill=(220,223,211,255))
 d.line((11,14,12,14),fill=(161,98,91,255));d.rectangle((40,8,47,9),fill=(*tuple(min(255,c+13) for c in hair),255));d.rectangle((40,10,40,12),fill=(*hair,255));d.rectangle((47,10,47,12),fill=(*hair,255))
 for y in range(20,32):
  d.line((23,y,24,y),fill=(25,30,34,255))
  if y%3==0:d.point((24,y),fill=(165,167,151,255))
 d.rectangle((21,20,26,21),fill=(227,220,199,255));d.rectangle((20,29,27,30),fill=(33,39,41,255));d.rectangle((22,24,22,26),fill=(149,34,38,255))
 for x,y in [(40,28),(44,28),(48,28),(52,28),(32,60),(36,60),(40,60),(44,60)]:d.rectangle((x,y,x+(2 if slim else 3),y+3),fill=(*skin,255))
 for x,y in [(0,29),(4,29),(8,29),(12,29),(16,61),(20,61),(24,61),(28,61)]:d.rectangle((x,y,x+3,y+2),fill=(23,26,28,255))
 for x,y in [(40,20),(48,20),(32,52),(40,52)]:d.line((x,y,x,y+7),fill=(*tuple(max(0,c-22) for c in coat),255))
 if name=='misato':
  d.rectangle((22,20,25,25),fill=(27,26,37,255));d.line((24,21,24,24),fill=(225,214,177,255));d.line((23,22,25,22),fill=(225,214,177,255));d.rectangle((20,28,27,31),fill=(28,25,37,255));paint([(24,8,31,15)],hair)
 if name=='ritsuko':
  d.rectangle((22,20,25,28),fill=(45,61,83,255));d.line((21,20,22,24),fill=(195,202,199,255));d.line((26,20,25,24),fill=(195,202,199,255));d.rectangle((20,26,21,28),fill=(170,191,198,255))
 if un:
  d.rectangle((8,8,15,10),fill=(61,117,160,255));d.rectangle((8,0,15,7),fill=(54,105,145,255));d.point((14,9),fill=(237,239,229,255));d.rectangle((21,23,22,24),fill=(66,119,158,255));d.point((22,23),fill=(235,237,227,255))
 OUT.mkdir(parents=True,exist_ok=True);im.save(OUT/f'staff_{name}.png')
def main():
 build('misato',(154,36,48),(57,38,82),slim=True);build('ritsuko',(215,220,208),(193,156,64),slim=True)
 build('maya',(86,112,103),(62,43,31),slim=True);build('operator',(87,112,105),(39,35,33));build('technician',(88,121,116),(52,40,33));build('medic',(216,221,204),(70,48,37));build('guard',(57,75,67),(42,33,28));build('un_guard',(88,105,88),(48,38,28),un=True);build('un_crew',(87,104,120),(57,40,27),un=True)
 print('Nine original staff skins authored')
if __name__=='__main__':main()
