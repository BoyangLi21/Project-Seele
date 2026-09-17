"""Smooth service pipes and bolted brackets on the measured launch structural webs."""
import json,math
import numpy as np
import build_tv_machinery_r16 as m

def main():
    m.use('r19_buttress_services')
    for x in (-2.24,3.24):
        points=[(x,float(y),32*(1-y/75)+.7) for y in np.linspace(1,72,96)]
        for a,b in zip(points,points[1:]):m.cylinder(a,b,.20,m.RED,16)
        for y in range(4,73,6):
            z=32*(1-y/75)+.7
            m.cylinder((x,y-.23,z+.1),(x,y+.23,z-.1),.29,m.STEEL,20)
            inward=-1.95 if x<0 else 2.95
            m.box(min(x,inward),y-.16,z-.35,abs(x-inward)+.08,.32,.7,m.DARK)
            m.cylinder((inward,y,z-.23),(inward,y,z+.23),.075,m.STEEL,8)
        m.cylinder((x,72,32*(1-72/75)+.7),(x,74,1.7),.2,m.RED,16)
        m.cylinder((x,74,1.7),(x,74,-.02),.2,m.RED,16)
    m.housing(-.8,1.5,33.05,2.6,3.8,.42,.18,m.OLIVE)
    m.housing(-.58,1.74,33.47,2.16,3.31,.07,.1,m.EDGE)
    for x in (-.25,.5,1.25):m.cylinder((x,4.48,33.57),(x,4.48,33.65),.13,m.LAMP,16)
    m.bolts(-.45,2.03,33.57,1.9,2.72)
    for y in (2.25,2.55,2.85):m.box(-.35,y,33.55,1.7,.08,.08,m.DARK)
    m.warning(-.58,5.0,33.57,2.16,.26)
    path=m.ASSETS/'mesh/tv_facilities_r16.json';data=json.loads(path.read_text());data['parts'].update(m.PARTS)
    path.write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
    print('Launch service detail triangles',len(m.PARTS['r19_buttress_services'])//18)

if __name__=='__main__':main()
