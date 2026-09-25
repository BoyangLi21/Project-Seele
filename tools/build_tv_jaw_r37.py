"""TV episode-2 jaw: split the original serrated armour seam, with inset red interlocks.

No external dental arch. The closed surface is preserved exactly, and the
dark inner membrane is skinned continuously between the head and lower jaw.
"""
from pathlib import Path
import json,hashlib,shutil,numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele';OUT=ROOT/'artifacts/combat_beast_r37/tv_jaw/assets/projectseele'
# Trace the three interlocking blue-grey cusps, not a generic sawtooth line.
# The outer points turn back up the cheek; the central fang has a short,
# flattened tip, and the two lower cusps rise beside it.
HALF_SEAM=[[0,162.24],[.20,162.27],[.36,162.39],[.46,162.72],[.62,163.24],
    [.78,163.75],[.93,164.06],[1.12,164.16],[1.40,164.30],[1.56,164.48],
    [1.68,163.86],[1.80,163.24],[1.91,163.07],[2.04,163.32],[2.25,163.66],
    [2.45,164.02],[2.57,164.40],[2.70,165.35],[2.82,166.25],[3.2,166.35],[4,166.5]]
SEAM=np.array([[-x,y] for x,y in reversed(HALF_SEAM[1:])]+HALF_SEAM)

def split(poly,n,c):
    yes=[];no=[];n=np.array(n)
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=a[:3]@n-c;db=b[:3]@n-c;(yes if da<=0 else no).append(a)
        if (da<=0)!=(db<=0):p=a+(b-a)*da/(da-db);yes.append(p);no.append(p)
    return yes,no
def fan(poly):return [np.array([poly[0],poly[i],poly[i+1]]) for i in range(1,len(poly)-1)] if len(poly)>=3 else []
def main():
    original=ROOT/'artifacts/combat_beast_r37/tv_jaw_source'
    if not (original/'mesh/eva_unit01.mesh.json').is_file():
        if 'r37_mouth' in json.loads((SRC/'mesh/eva_unit01.mesh.json').read_text()):raise ValueError('R36 source is required; refusing to split an already modified jaw')
        for kind in ['mesh','geo']:
            target=original/kind/f'eva_unit01.{kind}.json';target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SRC/kind/target.name,target)
    mesh=json.loads((original/'mesh/eva_unit01.mesh.json').read_text());geo=json.loads((original/'geo/eva_unit01.geo.json').read_text());head=mesh['parts']['head'];old=np.array(head['vertices']).reshape(-1,3,8);old[:,:,:3]+=head['pivot'];upper=[];jaw=[]
    for triangle in old:
        poly=list(triangle)
        for n,c in [([0,-1,0],-156.3),([0,1,0],167),([1,0,0],4),([-1,0,0],4),([0,0,1],-6)]:
            poly,out=split(poly,n,c);upper+=fan(out)
            if not poly:break
        if not poly:continue
        for (xa,ya),(xb,yb) in zip(SEAM,SEAM[1:]):
            slab,_=split(poly,[-1,0,0],-xa);slab,_=split(slab,[1,0,0],xb)
            if not slab:continue
            m=(yb-ya)/(xb-xa);c=ya-m*xa;lo,hi=split(slab,[-m,1,0],c);jaw+=fan(lo);upper+=fan(hi)
    # Give the cut armour its actual thickness. Both lips are made from the
    # original cut edge, so the closing silhouette remains the source head.
    def lip_thickness(triangles,lower):
        rims=[]
        for tri in triangles:
            for a,b in zip(tri,np.roll(tri,-1,axis=0)):
                if min(a[2],b[2])>=-6 or abs(a[0]-b[0])<1e-7:continue
                if any(abs(p[1]-np.interp(p[0],SEAM[:,0],SEAM[:,1]))>.00002 for p in (a,b)):continue
                inner_a=a.copy();inner_b=b.copy();inner_a[2]+=.10;inner_b[2]+=.10
                inner_a[1]+=-.045 if lower else .045;inner_b[1]+=-.045 if lower else .045
                back_a=inner_a.copy();back_b=inner_b.copy();back_a[2]+=.34;back_b[2]+=.34
                for first_a,first_b,last_a,last_b in [(a,b,inner_a,inner_b),(inner_a,inner_b,back_a,back_b)]:
                    for values in ([first_a,first_b,last_b],[first_a,last_b,last_a]):
                        row=np.array(values).copy();n=np.cross(row[1,:3]-row[0,:3],row[2,:3]-row[0,:3]);n/=max(np.linalg.norm(n),1e-9);row[:,5:8]=n;rims.append(row)
        return triangles+rims
    upper=lip_thickness(upper,False);jaw=lip_thickness(jaw,True)
    hinge=[0,165.6,-3.0]
    def part(tris,pivot,tint=None):
        a=np.array(tris).reshape(-1,8).copy();a[:,:3]-=pivot;row=dict(pivot=list(map(float,pivot)),vertices=a.round(7).ravel().tolist())
        if tint is not None:row['tint']=tint
        return row
    mesh['parts']['head']=part(upper,head['pivot']);mesh['parts']['r37_jaw']=part(jaw,hinge)
    tex=np.array(Image.open(SRC/'textures/entity/eva_unit01.png').convert('RGBA'));rgb=tex[:,:,:3].astype(float);cost=((rgb-245)**2).sum(2)+(rgb.max(2)-rgb.min(2))**2*8;cost[tex[:,:,3]<250]=1e9;y,x=np.unravel_index(cost.argmin(),cost.shape);uv=[(x+.5)/tex.shape[1],(y+.5)/tex.shape[0]]
    def face(a,b,c):
        a,b,c=map(np.array,(a,b,c));normal=np.cross(b-a,c-a);normal/=max(np.linalg.norm(normal),1e-8)
        return np.array([np.r_[p,uv,normal] for p in (a,b,c)])
    def quad(a,b,c,d):return [face(a,b,c),face(a,c,d)]
    def seam(x):return float(np.interp(x,SEAM[:,0],SEAM[:,1]))
    from functools import lru_cache
    va,vb,vc=old[:,0,:3],old[:,1,:3],old[:,2,:3]
    den=(vb[:,1]-vc[:,1])*(va[:,0]-vc[:,0])+(vc[:,0]-vb[:,0])*(va[:,1]-vc[:,1]);valid=np.abs(den)>1e-8;safe=np.where(valid,den,1)
    @lru_cache(None)
    def surface(x,y=None):
        y=seam(x) if y is None else y;u=((vb[:,1]-vc[:,1])*(x-vc[:,0])+(vc[:,0]-vb[:,0])*(y-vc[:,1]))/safe
        v=((vc[:,1]-va[:,1])*(x-vc[:,0])+(va[:,0]-vc[:,0])*(y-vc[:,1]))/safe
        inside=valid&(u>=-1e-6)&(v>=-1e-6)&(u+v<=1.000001)
        depths=u*va[:,2]+v*vb[:,2]+(1-u-v)*vc[:,2]
        return float(depths[inside].min()) if inside.any() else -12.8+.5*x*x
    def lug(x,lower):
        sy=seam(x);sign=1 if lower else -1;y=sy+(-.68 if lower else .7)
        # Red interlocking pieces sit behind the blue-grey armour and share
        # its narrow V-shaped profile; they do not form a human white denture.
        rings=[]
        for f,s in [(0,1),(.70,.9),(1,.62)]:
            ring=[]
            for dx,dz in [(-.36,-.26),(.36,-.26),(.43,-.12),(.43,.24),(.30,.38),(-.30,.38),(-.43,.24),(-.43,-.12)]:
                px=x+dx*s;py=y+sign*1.02*f
                # Follow the measured curved inner surface, rather than a
                # constant-depth tooth that pokes through the cheek armour.
                ring.append([px,py,surface(px,py)+.80+dz*s])
            rings.append(ring)
        tris=[]
        for a,b in zip(rings,rings[1:]):
            for i in range(8):tris+=quad(a[i],a[(i+1)%8],b[(i+1)%8],b[i])
        center=np.mean(rings[-1],0)
        for i in range(8):tris.append(face(rings[-1][i],rings[-1][(i+1)%8],center))
        return tris
    top=[];bottom=[]
    for x in [-2.2,-.72,.72,2.2]:top+=lug(x,False)
    for x in [-2.55,-1.15,1.15,2.55]:bottom+=lug(x,True)
    mesh['parts']['r37_red_upper']=part(top,head['pivot'],[.43,.018,.025]);mesh['parts']['r37_red_lower']=part(bottom,hinge,[.40,.015,.020])
    membrane=[];weights=[]
    xs=np.linspace(-4.1,4.1,57);ts=np.linspace(0,1,13)
    def point(x,t):return np.array([x,seam(x),surface(x)+.8+np.sin(np.pi*t)*1.4])
    for x0,x1 in zip(xs,xs[1:]):
        for t0,t1 in zip(ts,ts[1:]):
            a,b,c,d=point(x0,t0),point(x1,t0),point(x1,t1),point(x0,t1)
            membrane+=quad(a,b,c,d);weights.extend([t0,t0,t1,t0,t1,t1])
    mesh['parts']['r37_lining']=part(membrane,head['pivot'],[.022,.004,.008]);mesh.setdefault('jointSkins',{})['r37_lining']=dict(otherBone='r37_jaw',weights=weights)
    geo['minecraft:geometry'][0]['bones'].extend([dict(name='r37_jaw',parent='head',pivot=hinge),dict(name='r37_red_upper',parent='head',pivot=head['pivot']),dict(name='r37_red_lower',parent='r37_jaw',pivot=hinge),dict(name='r37_lining',parent='head',pivot=head['pivot'])])
    mesh['r37_mouth']=dict(contract='tv2-serrated-jaw',seam_revision=2,opening_degrees=31,forward_glide_pixels=.8,reference='TV episode 2 red internal interlocks and original serrated armour seam',closed_triangles_preserved=True)
    mesh['triangleCount']=sum(len(p['vertices'])//24 for p in mesh['parts'].values())
    for kind,data in [('mesh',mesh),('geo',geo)]:
        path=OUT/kind/f'eva_unit01.{kind}.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
    resources={'mesh':OUT/'mesh/eva_unit01.mesh.json','geo':OUT/'geo/eva_unit01.geo.json','animation':SRC/'animations/eva_unit01.animation.json','texture':SRC/'textures/entity/eva_unit01.png'}
    manifest=dict(schema='projectseele.tv-jaw-r37.v1',triangles=mesh['triangleCount'],parts=len(mesh['parts']),sha256={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in resources.items()})
    path=OUT/'eva/unit01_tv_jaw_r37.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(manifest,indent=2))
    print('TV jaw authored:',len(jaw),'original lower-jaw triangles, inset red parts, continuous skinned lining')
if __name__=='__main__':main()
