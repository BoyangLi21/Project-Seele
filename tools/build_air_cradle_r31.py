"""Original articulated aircraft cradle. Outputs only the isolated R31 staging directory."""
from pathlib import Path
import math
import json
import importlib.util
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("original_transport_geometry", ROOT / "tools/build_un_transport_r29.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.PARTS = {}
METAL=(124,141,145); DARK=(29,40,43); EDGE=(68,90,91); GOLD=(227,174,48); PAD=(37,47,50)

def box(*args): m.box(*args)

def cylinder(a, b, radius, color, sides=16):
    a=np.asarray(a,dtype=float); b=np.asarray(b,dtype=float)
    z=b-a; z/=np.linalg.norm(z)
    ref=np.array([0.,1.,0.]) if abs(z[1])<.95 else np.array([0.,0.,1.])
    x=np.cross(z,ref); x/=np.linalg.norm(x); y=np.cross(z,x)
    for i in range(sides):
        def ring(t): return radius*(x*math.cos(t)+y*math.sin(t))
        p=ring(i*2*math.pi/sides); q=ring((i+1)*2*math.pi/sides)
        m.quad([a+p,a+q,b+q,b+p],color)
        m.quad([a,a+q,a+p,a],color)
        m.quad([b,b+p,b+q,b],color)

def main():
    m.part="air_cradle_frame_r31"
    for side in (-1,1):
        x=side*14
        box(x-.7,2,7,x+.7,59,9,METAL)
        box(x-.72,3,6.9,x+.72,58,7.1,EDGE)
        cylinder((x-1.2,34,8),(x+1.2,34,8),2.2,EDGE,24)
        cylinder((x-1.25,34,8),(x+1.25,34,8),1.0,GOLD,24)
        for y in (13,31,47,56):
            # Leave the dorsal socket and UN-01 jet pair between the shoulder
            # cradles. A full crossbar here would intersect the nozzles.
            inner=side*7 if y==47 else 0
            box(min(inner,x),y-.6,7,max(inner,x),y+.6,9,METAL)
            cylinder((x,y,7),(x-side*3,y-5,8),.38,EDGE,12)
        for y in range(5,58,4):
            cylinder((x-.75,y,6.86),(x+.75,y,6.86),.11,GOLD,8)
        # Individually supported heels leave no rail platform hanging below the aircraft.
        fx=side*9
        box(fx-3,1,0,fx+3,2.3,8,DARK)
        box(fx-3,2.3,6.4,fx+3,4,8,EDGE)
        for y in (12,30,46):
            px=side*(8 if y==12 else 10 if y==46 else 6)
            box(px-3,y-1.3,5.6,px+3,y+1.3,7.8,PAD)
            for dy in (-.7,0,.7): box(px-2.8,y+dy-.08,5.55,px+2.8,y+dy+.08,5.65,EDGE)
    for side in (-1,1):
        m.part="air_cradle_jaw_r31_"+str(side)
        for y,reach in ((13,9),(31,11),(47,13)):
            x=side*14
            box(min(x,x-side*2.5),y-.9,-1,max(x,x-side*2.5),y+.9,8,EDGE)
            box(min(x-side*2.5,side*reach),y-1,-2,max(x-side*2.5,side*reach),y+1,1,PAD)
            cylinder((x,y,7),(x,y,1),.55,METAL)
            cylinder((x,y,1),(x,y,-1.2),.32,GOLD)
    path=ROOT/"artifacts/facility_r31/transport/air_cradle_r31.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    data={"source":"Project SEELE original rotating airlift cradle, authored R31; no extracted anime assets","parts":m.PARTS}
    path.write_text(json.dumps(data,separators=(",",":")),encoding="utf8")
    print(json.dumps({"artifact":str(path),"triangles":sum(len(p)//18 for p in m.PARTS.values()),"parts":list(m.PARTS)},ensure_ascii=False))

if __name__=="__main__": main()
