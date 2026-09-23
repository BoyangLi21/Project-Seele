"""Original opaque carrier truss and articulated service robot parts."""
from pathlib import Path
import json, math
import numpy as np
import build_tv_machinery_r16 as b

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'src/main/resources/assets/projectseele/mesh/tv_facilities_r16.json'
BLACK=0x171c23;EDGE=0x3b434d;STEEL=0x9aa6b0;COPPER=0x8f6952;LAMP=0xc8e5e4

def build():
    b.PARTS.clear();b.use('carrier_spine')
    for side in (-1,1):
        x=side*6.25
        for z in (9.7,11.2):
            b.housing(x-.36,0,z-.32,.72,62.2,.64,.12,BLACK)
        for y in range(2,60,4):
            b.housing(x-.58,y,9.3,1.16,.40,2.3,.12,EDGE)
            b.cylinder((x-.20,y+.4,9.7),(x+.20,y+4,11.2),.13,EDGE,12)
            b.bolts(x-.37,y+.10,9.24,.74,.20)
        b.cylinder((x,2,9.04),(x,59,9.04),.10,STEEL,16)
        b.hose([(x+.4*side,3+y,11.52) for y in range(55)],.075)
        for y in (7,20,33,43):
            b.housing(x-.55,y,8.90,1.1,2.4,.65,.18,BLACK)
            b.cylinder((x,y+.3,8.82),(x,y+2.1,8.82),.16,STEEL,16)
            b.box(x-.25,y+.9,8.77,.50,.18,.035,LAMP)
        for y in (3,15,27):
            b.cylinder((x,y,10.50),(-x,y+9,10.50),.16,EDGE,12)
        b.housing(x-.60,0,9.15,1.20,1.45,2.9,.25,EDGE)
    for y in (3,15,27,39):
        b.housing(-6.6,y,9.7,13.2,.48,1.7,.12,BLACK)
        for x in (-4,-2,0,2,4):b.bolts(x,y+.12,9.65,.5,.22)
    # The dorsal hatch and hoist sweep retain their open inspection volume.
    b.use('repair_rail')
    b.housing(-.46,0,-.5,.92,59,1,.16,BLACK)
    for x in (-.27,.27):b.cylinder((x,0,-.59),(x,59,-.59),.085,STEEL,16)
    for y in range(1,59,3):b.bolts(-.3,y,-.64,.6,.3)
    b.use('repair_base');b.housing(-.8,-1,-.7,1.6,2,1.4,.22,EDGE)
    b.cylinder((0,0,-.85),(0,0,.85),.76,BLACK,24)
    b.cylinder((0,0,-.89),(0,0,-.86),.50,COPPER,24)
    b.bolts(-.40,-.40,-.91,.8,.8)
    b.use('repair_link')
    b.housing(-.24,0,-.26,.48,1,.52,.08,BLACK)
    for x in (-.32,.32):b.cylinder((x,.05,0),(x,.95,0),.06,STEEL,12)
    b.use('repair_joint')
    b.cylinder((0,0,-.38),(0,0,.38),.45,EDGE,24)
    b.cylinder((0,0,-.42),(0,0,-.39),.25,COPPER,24)
    b.use('repair_tool')
    b.housing(-.30,-.70,-.3,.60,.95,.6,.12,EDGE)
    b.cylinder((0,0,0),(0,.60,0),.14,STEEL,16)
    for x in (-.26,.26):b.cylinder((x,-.20,0),(x,.60,0),.06,BLACK,12)
    b.use('repair_arc')
    for angle in np.linspace(0,math.pi*2,9)[:-1]:
        b.cylinder((0,0,0),(.22*math.cos(angle),.08,.22*math.sin(angle)),.016,LAMP,6)
    data=json.loads(PATH.read_text());data['parts'].update(b.PARTS)
    # Existing contact pads/reels keep their exact measured contact geometry.
    for name in (() if data.get('machinery_revision',0)>=33 else ('carrier_deck','carrier_clamp','carrier_power_reel')):
        if name not in data['parts']:continue
        a=np.asarray(data['parts'][name]).reshape(-1,6);rgb=a[:,3:];lum=rgb.mean(1)
        preserve=(rgb[:,0]>rgb[:,1]*1.6)|(lum>210)
        rgb[~preserve]*=.34
        a[:,3:]=np.rint(rgb);data['parts'][name]=a.ravel().tolist()
    data['machinery_revision']=33
    PATH.write_text(json.dumps(data,separators=(',',':')))
    print({k:len(v)//18 for k,v in b.PARTS.items()})

if __name__=='__main__':build()
