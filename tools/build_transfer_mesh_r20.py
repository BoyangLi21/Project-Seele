"""Smooth inclined deck, service pipes and braces in the installed cage frame."""
import json,math
import numpy as np
import build_tv_machinery_r16 as m
from plan_factory_r20 import guide_y

def point(x,y,z):return (x-30,y+443,z+240)
def quad(a,b,c,d,col):m.quad(point(*a),point(*b),point(*c),point(*d),col)
def tube(a,b,r,col):m.cylinder(point(*a),point(*b),r,col,16)

def main():
    m.use('r20_transfer_guide')
    for cx in (-12,30,72):
        for z in range(-213,-52):
            y0=guide_y(z)-3.975;y1=guide_y(z+1)-3.975
            for x in range(cx-15,cx+15,5):
                col=0x626e66 if ((x-cx+15)//5+(z+213)//5)%2 else 0x67726a
                quad((x,y0,z),(x,y1,z+1),(x+5,y1,z+1),(x+5,y0,z),col)
            if (z+213)%5==0:
                quad((cx-15,y0+.008,z),(cx-15,guide_y(z+.05)-3.966,z+.05),(cx+15,guide_y(z+.05)-3.966,z+.05),(cx+15,y0+.008,z),m.DARK)
        for dx in (-15,15):
            for z in range(-213,-51):
                y0=guide_y(z)+1.08;y1=guide_y(z+1)+1.08
                quad((cx+dx-.14,y0,z),(cx+dx-.14,y1,z+1),(cx+dx+.14,y1,z+1),(cx+dx+.14,y0,z),m.STEEL)
        # The carrier's bogies sit at +/-6 m. Their running heads have real
        # vertical webs down to the recessed floor, separate from edge guards.
        for dx in (-6,6):
            x=cx+dx
            for z in range(-213,-51):
                a=guide_y(z);b=guide_y(z+1)
                quad((x-.6,a-.48,z),(x-.6,b-.48,z+1),(x+.6,b-.48,z+1),(x+.6,a-.48,z),m.STEEL)
                quad((x-.8,a-3.90,z),(x-.8,b-3.90,z+1),(x+.8,b-3.90,z+1),(x+.8,a-3.90,z),m.EDGE)
                for side in (-.16,.16):quad((x+side,a-3.90,z),(x+side,a-.55,z),(x+side,b-.55,z+1),(x+side,b-3.90,z+1),m.BLUE)
    for centre in (9,51):
        for offset in (-1.15,1.15):
            x=centre+offset
            for z in range(-212,-51):tube((x,guide_y(z)+4.2,z),(x,guide_y(z+1)+4.2,z+1),.30,m.RED)
            for z in range(-208,-51,8):
                y=guide_y(z)+4.2;tube((x,y,z-.22),(x,y,z+.22),.39,m.STEEL)
                a=point(x-.12,guide_y(z)+3.6,z-.2);m.box(*a,.24,.5,.4,m.DARK)
                # Recessed access panels along the side of the service spine.
                a=point(centre-1.5,guide_y(z)+1.4,z-2.8);m.housing(*a,3.,1.7,.35,.12,m.OLIVE)
    path=m.ASSETS/'mesh/tv_facilities_r16.json';d=json.loads(path.read_text());d['parts'].pop('r19_buttress_services',None);d['parts'].update(m.PARTS);path.write_text(json.dumps(d,separators=(',',':')))
    print('R20 guide mesh triangles',len(m.PARTS['r20_transfer_guide'])//18)

if __name__=='__main__':main()
