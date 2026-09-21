"""Original UN heavy-lift VTOL: curved hull, swept wings, ducted rotors and cargo rig."""
from pathlib import Path
import json,math,numpy as np
ROOT=Path(__file__).resolve().parents[1];PARTS={};part='un_transport_body'
PALE=(206,216,219);EDGE=(93,110,119);DARK=(25,32,38);BLUE=(48,123,172);METAL=(145,158,163);GOLD=(221,168,54)
def quad(points,color):
    a,b,c=np.asarray(points[:3],dtype=float);normal=np.cross(b-a,c-a);normal/=max(np.linalg.norm(normal),1e-9)
    light=.76+.24*max(0,float(normal@np.array([.3,.88,-.35])))
    target=PARTS.setdefault(part,[])
    for i in (0,1,2,0,2,3):target.extend([round(float(q),4) for q in points[i]]+[round(q*light) for q in color])
def box(x,y,z,X,Y,Z,color):
    v=[(x,y,z),(X,y,z),(X,Y,z),(x,Y,z),(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)]
    for face in ((0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5),(3,7,6,2),(0,1,5,4)):quad([v[i] for i in face],color)
def hull(profiles,color):
    rings=[]
    for z,rx,ry,cy in profiles:rings.append([(rx*math.cos(t),cy+ry*math.sin(t),z) for t in np.linspace(0,2*math.pi,33)[:-1]])
    for a,b in zip(rings,rings[1:]):
        for i in range(32):quad([a[i],a[(i+1)%32],b[(i+1)%32],b[i]],color)
def duct(x,y,z,radius,height,color):
    for i in range(40):
        a,b=i*math.pi/20,(i+1)*math.pi/20
        def p(angle,r,h):return(x+r*math.cos(angle),y+h,z+r*math.sin(angle))
        quad([p(a,radius,0),p(b,radius,0),p(b,radius,height),p(a,radius,height)],color)
        quad([p(a,radius,height),p(b,radius,height),p(b,radius-1,height),p(a,radius-1,height)],METAL)
        quad([p(a,radius-1,height),p(b,radius-1,height),p(b,radius-1,0),p(a,radius-1,0)],DARK)
def wing(side):
    outline=[(9,-22),(27,-26),(66,-2),(69,13),(40,17),(10,31)]
    top=[(side*x,2.5-(x-9)*.012,z) for x,z in outline];bottom=[(x,y-1.7,z) for x,y,z in top]
    centre=(side*25,2.2,0)
    for i in range(len(top)):
        j=(i+1)%len(top);quad([centre,top[i],top[j],centre],PALE)
        quad([(centre[0],centre[1]-1.7,centre[2]),bottom[j],bottom[i],(centre[0],centre[1]-1.7,centre[2])],EDGE)
        quad([top[i],bottom[i],bottom[j],top[j]],EDGE)
    # A separate swept tailplane and a canted fin.
    quad([(side*5,4,-43),(side*24,8,-51),(side*23,8,-42),(side*5,4,-32)],PALE)
    quad([(side*8,3,-47),(side*10,19,-54),(side*13,19,-47),(side*12,3,-29)],EDGE)
    box(side*11 if side>0 else -12,-1,-34,side*12 if side>0 else -11,3,31,BLUE)
def main():
    global part
    hull([(-56,.1,.1,0),(-49,4,3,0),(-38,8,5,0),(-23,12,7,0),(9,12,8,0),(30,10,7,0),(44,7,5,-.4),(55,2.5,2,-1),(58,.1,.1,-1)],PALE)
    for side in (-1,1):wing(side)
    for side in (-1,1):box(min(side*11.0,side*12.03),-3,-8,max(side*11.0,side*12.03),4,5,PALE)
    # Dark wraparound flight deck and the reinforced central cargo keel.
    quad([(-6,5,37),(6,5,37),(4,4,48),(-4,4,48)],DARK)
    for side in (-1,1):quad([(side*6,5,37),(side*8,1,35),(side*5,1,46),(side*4,4,48)],BLUE)
    box(-6,-10,-31,6,-7,27,DARK);box(-4,-10.5,-30,4,-10,26,METAL)
    for z in range(-30,31,6):box(-11,-1,z,11,-.65,z+.18,EDGE)
    for i,(x,z) in enumerate(((-29,-11),(29,-11),(-49,9),(49,9))):
        duct(x,-1,z,8,6,PALE);duct(x,5,z,8,.4,DARK);box(x-1,-2,z-1,x+1,5,z+1,METAL)
        part='un_transport_rotor_'+str(i)
        for k in range(12):
            angle=k*math.pi/6
            def p(r,a,h):return(r*math.cos(a),h,r*math.sin(a))
            quad([p(1,angle,0),p(6.9,angle+.14,.1),p(6.9,angle+.38,.1),p(1,angle+.3,0)],DARK)
        part='un_transport_body'
    # Four permanent telescopic winch housings; moving cargo-side hooks are
    # a separate rigid part so the approach/release can animate continuously.
    for x in (-14,14):
        for z in (-10,10):
            box(x-1.3,-11,z-1.3,x+1.3,-7,z+1.3,EDGE)
    part='un_transport_clamps'
    for x in (-14,14):
        for z in (-10,10):box(x-.45,-45,z-.45,x+.45,-11,z+.45,METAL)
    box(-14,-39,-12,14,-37,-10,METAL)
    for x in (-14,14):box(x-.7,-39,-11,x+.7,-37,11,METAL)
    for side in (-1,1):
        x=side*11
        box(min(x,side*14),-39,-10,max(x,side*14),-37,10,METAL)
        box(x-.8,-76,-12,x+.8,-36,-10,METAL)
        for y in (-39,-61,-76):box(x-.8,y,-11,x+.8,y+1,4,METAL)
        for y in (-39,-61,-76):box(min(x,side*17),y,-.4,max(x,side*17),y+.8,.4,METAL)
        for y in (-39,-61,-76):box(x-.81,y,-12.05,x+.81,y+.65,-12,GOLD)
        part='un_transport_jaw_'+str(side)
        box(min(x,x-side*3),-40,-4,max(x,x-side*3),-36,4,EDGE)
        box(min(x,x-side*2),-62,-4,max(x,x-side*2),-58,4,EDGE)
        box(min(x,x-side*2.8),-77,-6,max(x,x-side*2.8),-74,5,DARK)
        part='un_transport_clamps'
    part='un_ground_carrier'
    box(-12,-1.55,-14,12,-.3,14,DARK);box(-11.5,-.3,-13.5,11.5,0,13.5,METAL)
    for side in (-1,1):
        for z in np.arange(-12,13,2.8):
            x=side*11.5;box(x-.7,-1.7,z-.8,x+.7,-.4,z+.8,EDGE)
        for z in (-10,10):box(min(side*8,side*11),0,z-1,max(side*8,side*11),4,z+1,EDGE)
    for x in range(-10,11,3):box(x,-.29,-13.7,x+1.3,.02,-13.3,GOLD)
    target=ROOT/'artifacts/facility_r29/aircraft/un_transport_r29.json';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({'source':'Original Project SEELE UN heavy VTOL, R29','parts':PARTS},separators=(',',':')),encoding='utf8')
    runtime=ROOT/'src/main/resources/assets/projectseele/mesh/tv_facilities_r16.json';data=json.loads(runtime.read_text());data['parts'].update(PARTS);runtime.write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
    print('Original aircraft parts',len(PARTS),'triangles',sum(len(a)//18 for a in PARTS.values()),'span138m/length114m')
if __name__=='__main__':main()
