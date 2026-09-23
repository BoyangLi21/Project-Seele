"""Dense geometric containment against the five actual neutral meshes; no game/world mutation."""
from pathlib import Path
import json,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r31/transport';PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele/mesh'
def transform(points,pitch,yaw):
    phase=math.radians(pitch);a=-phase;h=math.radians(180-yaw);x,y,z=points.T;y=y-34;yy=y*math.cos(a)-z*math.sin(a)+34+54*math.sin(phase)-8*math.sin(2*phase);zz=y*math.sin(a)+z*math.cos(a)
    return np.c_[x*math.cos(h)+zz*math.sin(h),yy,-x*math.sin(h)+zz*math.cos(h)]
def corners(lo,hi):return np.array([[x,y,z] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])])
cases=[(0,.001,0,0),(0,1.7,0,2.5),(44.2,45.9,12,-2.5),(88.3,90,179,2.5),(90,89,-179,-2.5),(1.7,0,0,2.5),(0,0,12,2.5)]
records=[];checks=0;minimum_margin=1e9
for name in ('eva_unit00','eva_unit01','eva_unit02','eva_prototype','eva_un01'):
    pack=ROOT/'run/resourcepacks/eva_un_r31_review/assets/projectseele/mesh' if name in ('eva_prototype','eva_un01') else PACK
    path=pack/(name+'.mesh.json');mesh=json.loads(path.read_text());points=[]
    for part,q in mesh['parts'].items():
        if part in ('cannon','knife','lance','shield','n2'):continue
        a=np.asarray(q['vertices']).reshape(-1,8);points.append((a[:,:3]+q['pivot'])*[-1,1,1]*5/16)
    points=np.concatenate(points);model_checks=0
    for section in range(4):
        selected=points[(points[:,1]>=section*16)&(points[:,1]<(section+1)*16)]
        if not len(selected):continue
        lo=selected.min(0);hi=selected.max(0);vertices=corners(lo,hi)
        for pa,pb,ya,turn in cases:
            pn=max(1,math.ceil(abs(pb-pa)/.5));yn=max(1,math.ceil(abs(turn)/.5));arc=math.radians(abs(pb-pa)/pn+abs(turn)/yn);pad=.012+140*arc*arc/8
            for ip in range(pn):
                p0=pa+(pb-pa)*ip/pn;p1=pa+(pb-pa)*(ip+1)/pn
                for iy in range(yn):
                    y0=ya+turn*iy/yn;y1=ya+turn*(iy+1)/yn
                    endpoints=np.concatenate([transform(vertices,p,y) for p in (p0,p1) for y in (y0,y1)]);low=endpoints.min(0)-pad;high=endpoints.max(0)+pad
                    # Independent phase parameters deliberately test different
                    # easing rates; a single shared interpolation would miss this.
                    for p in np.linspace(p0,p1,13):
                        for y in np.linspace(y0,y1,13):
                            v=transform(vertices,p,y);margin=min(float((v-low).min()),float((high-v).min()));minimum_margin=min(minimum_margin,margin);assert margin>=-1e-8,(name,pa,pb,ya,turn,p,y,margin);checks+=len(v);model_checks+=len(v)
    records.append({'model':name,'neutralMeshVertices':len(points),'denseCornerChecks':model_checks})
def bearing(top,bottom,planes):return any(abs(top-y)<.002 and bottom<y-.001 for y in planes)
support={'fullFloor':bearing(80,79,[80]),'thinFloor':bearing(80,79.9375,[80]),'newRaisedBlock':not bearing(81,80,[80]),'sideWall':not bearing(100,79,[80]),'ceiling':not bearing(143,142,[80]),'noInitialContact':not bearing(80,79,[])}
assert all(support.values());report={'status':'offline geometry passed; native collision and networking remain separate','orientation':'prone: physical root X=-phase, face down and dorsal cradle up','models':records,'denseCornerChecks':checks,'minimumBoundMargin':minimum_margin,'supportPlaneCases':support,'phases':'First-lift near-zero pitch, fast pitch/yaw, 179-degree heading crossing, full horizontal, and descending final rotation'}
(OUT/'continuous_sweep_check.json').write_text(json.dumps(report,indent=2));print(json.dumps({'checks':checks,'minMargin':minimum_margin,'support':support}),flush=True)
