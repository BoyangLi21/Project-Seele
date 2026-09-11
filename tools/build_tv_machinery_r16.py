"""Original engineering geometry derived from TV cage/catapult silhouettes.

All dimensions are metres/blocks in the same frame as the actual carrier.
Parts are baked once on the GPU; moving parts retain separate rigid transforms.
No episode images or downloaded textures are incorporated into these assets.
"""
from pathlib import Path
import json,math
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'src/main/resources/assets/projectseele'
OLIVE=0x657260;EDGE=0x9fa99b;STEEL=0xb3bab4;DARK=0x242c31;BLUE=0x414e68;RED=0xa12d34;BLACK=0x151c22;IVORY=0xcbd2c0;LAMP=0xe8efd4
PARTS={};part=None
def use(name):
 global part
 part=PARTS.setdefault(name,[])
def tri(a,b,c,col):
 a,b,c=map(lambda x:np.array(x,float),(a,b,c));n=np.cross(b-a,c-a);l=np.linalg.norm(n)
 if l<1e-9:return
 n/=l;shade=.74+.26*max(0,float(n@np.array([-.35,.82,-.45])))
 color=[round(((col>>i)&255)*shade) for i in (16,8,0)]
 for p in (a,b,c):part.extend([*np.round(p,5),*color])
def quad(a,b,c,d,col):tri(a,b,c,col);tri(a,c,d,col)
def box(x,y,z,w,h,d,col):
 pts=[(x+dx*w,y+dy*h,z+dz*d) for dx,dy,dz in [(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]]
 for ids in [(0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5),(3,7,6,2),(0,1,5,4)]:quad(*[pts[i] for i in ids],col)
def housing(x,y,z,w,h,d,bevel,col):
 # A real octagonal metal housing, not a stretched Minecraft cube.
 b=min(bevel,w/3,h/3);p=[(x+b,y),(x+w-b,y),(x+w,y+b),(x+w,y+h-b),(x+w-b,y+h),(x+b,y+h),(x,y+h-b),(x,y+b)]
 for i in range(8):
  a=p[i];c=p[(i+1)%8];quad((*a,z),(*a,z+d),(*c,z+d),(*c,z),col)
  tri((x+w/2,y+h/2,z),(*c,z),(*a,z),col);tri((x+w/2,y+h/2,z+d),(*a,z+d),(*c,z+d),col)
def cylinder(a,b,r,col,segments=16,inner=0):
 a,b=np.array(a,float),np.array(b,float);axis=b-a;axis/=np.linalg.norm(axis);q=np.cross(axis,[1,0,0] if abs(axis[0])<.8 else [0,1,0]);q/=np.linalg.norm(q);s=np.cross(axis,q)
 for i in range(segments):
  u=q*math.cos(i*2*math.pi/segments)+s*math.sin(i*2*math.pi/segments);v=q*math.cos((i+1)*2*math.pi/segments)+s*math.sin((i+1)*2*math.pi/segments)
  quad(a+u*r,a+v*r,b+v*r,b+u*r,col)
  if inner:
   quad(a+v*inner,a+u*inner,b+u*inner,b+v*inner,DARK);quad(a+u*inner,a+v*inner,a+v*r,a+u*r,col);quad(b+u*r,b+v*r,b+v*inner,b+u*inner,col)
  else:tri(a,a+v*r,a+u*r,col);tri(b,b+u*r,b+v*r,col)
def bolts(x,y,z,w,h,col=STEEL):
 for xx in (x,x+w):
  for yy in (y,y+h):cylinder((xx,yy,z),(xx,yy,z-.055),.075,col,6)
def warning(x,y,z,w,h):
 box(x,y,z,w,h,.035,BLACK)
 # Stripe polygons are clipped to the plate; no protruding teeth.
 for start in np.arange(-h,w,.60):
  poly=[(start,0),(start+.26,0),(start+.26+h,h),(start+h,h)]
  for axis,limit,sign in [(0,0,1),(0,w,-1)]:
   out=[]
   for a,b in zip(poly,poly[1:]+poly[:1]):
    da=sign*(a[axis]-limit);db=sign*(b[axis]-limit)
    if da>=0:out.append(a)
    if (da>=0)!=(db>=0):t=da/(da-db);out.append(tuple(a[k]+(b[k]-a[k])*t for k in range(2)))
   poly=out
  for i in range(1,len(poly)-1):tri((x+poly[0][0],y+poly[0][1],z-.006),(x+poly[i+1][0],y+poly[i+1][1],z-.006),(x+poly[i][0],y+poly[i][1],z-.006),RED)
def hose(points,r=.06):
 for a,b in zip(points,points[1:]):cylinder(a,b,r,BLACK,8)

def cage():
 use('cage_frame')
 for side in (-1,1):
  for z in (-5.8,6.3):
   x=side*15.2
   housing(x-1.0,-.05,z-1.1,2.0,65.3,2.2,.4,OLIVE)
   box(x-.40,1,z-1.14,.80,61,.06,DARK);box(x-.09,1,z-1.21,.18,61,.08,STEEL)
   for y in range(2,65,8):
    housing(x-1.18,y,z-1.2,2.36,.64,2.4,.16,EDGE);bolts(x-.78,y+.18,z-1.22,1.56,.26)
   for y in (11,29,47,62):box(x-.20,y,z-1.24,.40,1.5,.08,LAMP)
  for y in (3,23,54,62):
   housing(side*15.2-1.05,y,-4.7,2.1,1.25,11.0,.25,OLIVE)
  # Two hydraulic accumulators with flanged caps and flexible service loops.
  for y in (21,48):
   for z in (-4.0,3.6):
    cylinder((side*14.3,y,z),(side*14.3,y+3,z),.53,EDGE,24)
    for yy in (y,y+2.9):cylinder((side*14.3,yy-.06,z),(side*14.3,yy+.08,z),.65,DARK,24)
    hose([(side*(14.3-.7*math.sin(t*math.pi)),y+3+.6*math.sin(t*math.pi),z+2*t) for t in np.linspace(0,1,18)])
  for y in (20.9,51.6):
   for z in (-2.8,2.8):cylinder((side*11.8,y,z),(side*14.6,y,z),.44,OLIVE,24)
  warning(side*15.2-1.02,55.4,-6.99,2.04,.65)
  # High-level service gantry lies outside the full exit lane.
  box(side*18.15-.75,47.95,-21,1.5,.25,44,EDGE)
  for z in range(-20,24,3):
   cylinder((side*18.8,48.2,z),(side*18.8,49.3,z),.035,EDGE,8)
  cylinder((side*18.8,49.3,-21),(side*18.8,49.3,23),.04,EDGE,10)
 for y,z in [(63,-5.8),(63,6.3)]:
  box(-14.2,y,z-.8,28.4,1.1,1.6,OLIVE)
  for x in range(-12,13,3):housing(x-.65,y-.20,z-.95,1.3,.35,.28,.10,LAMP)
 use('shoulder_jaw')
 housing(7.84,50.60,-4.1,.85,4.25,8.2,.33,EDGE)
 box(7.81,51.1,-3.5,.03,2.9,7.0,DARK)
 housing(8.69,51,-3.6,1.40,3.25,7.2,.35,OLIVE)
 warning(8.70,51.25,-3.64,1.36,.62)
 for z in (-3.1,3.1):
  cylinder((8.34,54.86,z),(8.34,55.1,z),.48,OLIVE,24)
  bolts(8.0,51.9,-4.13,.46,1.8)
 use('shoulder_rod')
 for z in (-2.8,2.8):cylinder((0,51.6,z),(1,51.6,z),.20,STEEL,24)
 use('shoulder_pin')
 for z in (-3.1,3.1):
  cylinder((7.80,53.2,z),(7.80,55.3,z),.15,STEEL,24)
  cylinder((7.80,55.15,z),(7.80,55.38,z),.30,DARK,24)
 use('arm_guard')
 housing(9.45,32.4,-3.3,1.4,15.2,6.6,.60,OLIVE)
 box(9.40,33.5,-2.5,.055,12.8,5,DARK)
 for y in (34,40,45):
  housing(10.8,y,-3.55,1.40,1.10,7.1,.25,EDGE);warning(10.95,y+.2,-3.60,1.12,.45)
 use('arm_rod')
 for y in (34,40,45):cylinder((0,y+.55,1),(1,y+.55,1),.18,STEEL,16)
 use('lower_jaw')
 housing(5.98,20.2,-2.6,.82,3.4,5.2,.35,EDGE)
 box(5.95,20.7,-2.1,.04,2.4,4.2,DARK)
 use('lower_rod')
 for z in (-1.8,1.8):cylinder((0,21.0,z),(1,21.0,z),.19,STEEL,16)
 use('cage_front')
 # Segmented front guard curtains open sideways; no geometry over personnel routes.
 housing(10.6,2.0,-13.8,6.3,42.0,.85,.45,OLIVE)
 for y in range(4,43,4):
  housing(11.0,y,-13.94,5.5,2.9,.15,.22,EDGE);bolts(11.25,y+.26,-13.97,5.0,2.35)
 warning(11.05,41.9,-14.0,5.35,.75)

def carrier():
 use('carrier_deck')
 # The outer deck exactly retains the physical 29-block carrier footprint.
 housing(-14.5,-.92,-14.5,29,.91,29,.40,BLUE)
 box(-13.9,-.06,-13.9,27.8,.10,27.8,EDGE)
 for x in np.arange(-13.5,14,1.5):box(x,-.004,-13.8,.025,.046,27.6,DARK)
 for z in np.arange(-13.5,14,1.5):box(-13.8,-.003,z,27.6,.046,.025,DARK)
 for x in (-14.1,13.45):box(x,.05,-13.9,.65,.075,27.8,DARK)
 for z in (-14.13,13.48):box(-13.45,.05,z,26.9,.075,.65,DARK)
 for side in (-1,1):
  for z in (-9,7.0):
   housing(side*6-.8,-1.5,z,1.6,.62,3.0,.2,DARK)
   for zz in (z+.65,z+2.3):cylinder((side*6-.9,-1.05,zz),(side*6+.9,-1.05,zz),.45,STEEL,24)
 for x in (-8.8,7.7):box(x,-1.2,-12,1.1,.30,24,DARK)
 warning(-12.8,-.77,-14.54,25.6,.54)
 use('carrier_spine')
 for x in (-6.85,5.25):
  housing(x,0,9.65,1.6,62.0,2.0,.40,BLUE)
  box(x+.32,1,9.59,.32,59,.08,STEEL)
  for y in range(3,62,6):housing(x-.14,y,9.44,1.88,.52,2.35,.10,EDGE)
 for y,h in [(4,9),(16,9),(28,9),(39,4),(54,6)]:
  housing(-5.25,y,10.3,10.5,h,1.25,.7,BLUE)
  housing(-2.4,y+.45,10.16,4.8,h-.90,.16,.3,EDGE);bolts(-2.12,y+.73,10.10,4.24,h-1.46)
 housing(-7.1,61.4,9.05,14.2,1.1,3.2,.32,EDGE)
 for x in (-5,-2.5,0,2.5,5):cylinder((x,61.38,9.7),(x,61.24,9.7),.40,LAMP,24)
 for side in (-1,1):
  hose([(side*5.6,45+7*t,10.0-1.25*math.sin(t*math.pi)) for t in np.linspace(0,1,24)],.12)
 use('carrier_clamp')
 # The foot frame sits outside the measured sole; moving crossbar releases upward.
 for side in (-1,1):
  for x in (side*3.25-2.8,side*3.25+2.5):
   housing(x,.13,-8.25,.30,1.35,11.0,.12,OLIVE)
   cylinder((x+.15,.6,2.3),(x+.15,1.3,2.3),.20,STEEL,16)
  housing(side*3.25-2.5,.15,-8.4,5.0,.42,.65,.16,EDGE)

def doors():
 use('pressure_leaf')
 box(0,0,.30,16.5,65,.12,DARK)
 housing(0,0,-.38,16.5,65,.76,.62,OLIVE)
 for y in range(2,64,7):
  housing(.80,y,-.52,14.7,5.9,.15,.30,EDGE);bolts(1.1,y+.32,-.59,14.1,5.25)
 box(.05,0,-.55,.24,65,.18,BLACK);warning(.60,6,-.64,15.2,1.1);warning(.6,57,-.64,15.2,1.1)
 for y in range(4,65,9):
  cylinder((15.3,y,-.61),(15.3,y,-.84),.4,DARK,24)
  cylinder((15.3,y,-.84),(15.3,y,-.90),.17,STEEL,16)
 use('hatch_panel')
 # Four rigid 4 m panels per half; each lifts to its own guide tier.
 box(0,0,-16.5,4,.79,33,BLUE)
 for z in np.arange(-15.6,15.6,4):
  box(.16,.79,z,3.68,.12,3.35,EDGE)
  for x in (.40,3.60):cylinder((x,.92,z+.36),(x,.98,z+.36),.09,DARK,6)
 for x in (.015,3.86):box(x,.80,-16.5,.125,.16,33,BLACK)
 for z in (-16.4,15.75):box(.14,.80,z,3.72,.16,.65,DARK)
 use('hatch_cassette')
 # A cantilevered metal cassette is attached to the existing shaft collar.
 # Max x=20.7 leaves 0.6 m between neighbouring 42 m-spaced cassettes.
 box(16.05,-.35,-17.3,4.65,.35,34.6,BLACK)
 housing(20.45,-.35,-17.3,.25,6.02,34.6,.10,DARK)
 box(16.05,5.48,-17.3,4.65,.19,34.6,BLACK)
 for z in (-17.3,16.6):
  housing(16.05,0,z,4.4,5.48,.7,.20,DARK)
  for tier in range(4):
   box(16.2,1.02+tier*1.10,z+.15,4.1,.08,.4,STEEL)
  for y in (1.2,3.4,4.8):bolts(16.5,y,z-.04,3.5,.3)
 for z in range(-15,16,5):box(16.65,5.67,z,3.5,.025,.08,EDGE)
 use('hatch_frame')
 for x in (-17.15,16.55):
  box(x,-1.1,-17.15,.60,2.10,34.30,OLIVE)
  for z in (-12,0,12):housing(x-.25,-1.30,z-1,.95,1.2,2,.25,EDGE)
 for z in (-17.15,16.55):box(-16.55,-1.1,z,33.10,2.1,.6,OLIVE)

def materials():
 palette={'nerv_machine_panel':(100,113,94),'nerv_shaft_panel':(59,70,91),'nerv_machine_edge':(150,159,149),'nerv_machine_hazard':(35,39,41)}
 for name,c in palette.items():
  im=Image.new('RGB',(64,64),c);d=ImageDraw.Draw(im)
  if name.endswith('hazard'):
   for x in range(-64,128,24):d.polygon([(x,0),(x+10,0),(x+74,64),(x+64,64)],fill=(161,46,53))
  else:
   # Fine uniform paint; seams, witness lines and captive screws occupy the edges.
   d.line((0,63,63,63),fill=tuple(max(0,i-19) for i in c));d.line((63,0,63,63),fill=tuple(max(0,i-19) for i in c));d.line((0,0,62,0),fill=tuple(min(255,i+6) for i in c))
   for x,y in [(4,4),(59,4),(4,59),(59,59)]:d.ellipse((x-1,y-1,x+1,y+1),fill=tuple(max(0,i-13) for i in c));d.point((x,y),fill=tuple(min(255,i+10) for i in c))
  target=ASSETS/'textures/block';target.mkdir(exist_ok=True);im.save(target/(name+'.png'))
  for rel,value in [(f'blockstates/{name}.json',{'variants':{'':{'model':'projectseele:block/'+name}}}),(f'models/block/{name}.json',{'parent':'minecraft:block/cube_all','textures':{'all':'projectseele:block/'+name}}),(f'models/item/{name}.json',{'parent':'projectseele:block/'+name})]:
   (ASSETS/rel).write_text(json.dumps(value),encoding='utf8')
 tag=ROOT/'src/main/resources/data/projectseele/tags/blocks/structural_shell.json';d=json.loads(tag.read_text());d['values']=list(dict.fromkeys(d['values']+['projectseele:'+n for n in palette]));tag.write_text(json.dumps(d,indent=2)+'\n',encoding='utf8')
 for lang,labels in [('zh_cn',['机库灰绿钢板','弹射井蓝灰钢板','机械浅灰饰板','红黑机械警戒板']),('en_us',['Cage Olive Plating','Catapult Blue Plating','Machinery Edge Plating','Red Hazard Plating'])]:
  path=ASSETS/'lang'/(lang+'.json');d=json.loads(path.read_text(encoding='utf8'))
  for n,l in zip(palette,labels):d['block.projectseele.'+n]=l
  path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def main():
 cage();carrier();doors();materials();out=ASSETS/'mesh/tv_facilities_r16.json';out.write_text(json.dumps({'stride':6,'parts':PARTS},separators=(',',':')),encoding='utf8')
 print('Original TV-inspired machinery:',{k:len(v)//18 for k,v in PARTS.items()},'bytes',out.stat().st_size)
if __name__=='__main__':main()
