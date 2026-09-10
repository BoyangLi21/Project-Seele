"""Cut a real pressure bore in the private airframes and add articulated cover leaves.

Canonical meshes come from the frozen R11 checkpoint, never from dirty source files.
The bore, liner and capsule use EntryPlugKinematics' measured socket frame.
"""
from pathlib import Path
import json, math, shutil
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele'
BACK=ROOT/'backups/SEELE_R11_20260909_234420/eva_real_model/assets/projectseele'
OUT=ROOT/'artifacts/world_motion_r11/dorsal';OUT.mkdir(parents=True,exist_ok=True)
C=np.array([0,169.28,13.92]);Z=np.array([0,math.sqrt(3)/2,.5]);X=np.array([1.,0,0]);Y=np.cross(Z,X)
RADIUS=5.75

def split(poly,n,d):
    inside=[];outside=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=a[:3]@n-d;db=b[:3]@n-d;ina=da<=1e-7;inb=db<=1e-7
        (inside if ina else outside).append(a)
        if ina!=inb:
            v=a+(b-a)*(da/(da-db));inside.append(v);outside.append(v)
    return inside,outside

def cut_part(part):
    vertices=np.array(part['vertices'],float).reshape(-1,3,8);pivot=np.array(part['pivot']);vertices[:,:,:3]+=pivot
    result=[];removed=0
    normals=[X*math.cos(a)+Y*math.sin(a) for a in np.linspace(0,2*math.pi,32,endpoint=False)]
    planes=[(n,n@C+RADIUS) for n in normals]+[(Z,Z@C+14),(-Z,-Z@C+35)]
    for tri in vertices:
        relative=tri[:,:3]-C;rad=relative@X;ry=relative@Y;t=relative@Z
        if rad.min()>RADIUS or rad.max()<-RADIUS or ry.min()>RADIUS or ry.max()<-RADIUS or t.min()>14 or t.max()<-35:
            result.append(tri);continue
        polygon=list(tri)
        for n,d in planes:
            if len(polygon)<3:break
            polygon,outside=split(polygon,n,d)
            if len(outside)>=3:
                for i in range(1,len(outside)-1):result.append(np.array([outside[0],outside[i],outside[i+1]]))
        if len(polygon)>=3:removed+=1
    v=np.array(result).reshape(-1,8);v[:,:3]-=pivot
    part['vertices']=np.round(v,6).ravel().tolist();return removed

def main():
    report=[]
    for name in ['eva_unit00','eva_unit01','eva_unit02','eva_prototype']:
        base=OUT/(name+'_uncut.mesh.json')
        source=ROOT/'src/main/resources/assets/projectseele' if name=='eva_prototype' else BACK
        if name=='eva_prototype' and 'r11_dorsal_socket' not in json.loads((source/'mesh'/f'{name}.mesh.json').read_text(encoding='utf-8')):
            shutil.copy2(source/'mesh'/f'{name}.mesh.json',base)
        if not base.exists():shutil.copy2(source/'mesh'/f'{name}.mesh.json',base)
        mesh=json.loads(base.read_text(encoding='utf-8'));geo=json.loads((source/'geo'/f'{name}.geo.json').read_text(encoding='utf-8'))
        bones=geo['minecraft:geometry'][0]['bones'];bones[:]=[b for b in bones if not b['name'].startswith('dorsal_')]
        counts={n:cut_part(mesh['parts'][n]) for n in ['torso_upper','neck'] if n in mesh['parts']}
        texture=Image.open((source if name=='eva_prototype' else PACK)/'textures/entity'/f'{name}.png').convert('RGB');ar=np.asarray(texture)
        targets={'armour':{'eva_unit00':[209,135,30],'eva_unit01':[85,47,140],'eva_unit02':[160,29,21],'eva_prototype':[25,32,36]}[name],'steel':[112,123,132],'dark':[16,21,25],'light':[182,194,180]}
        uvs={}
        for material,rgb in targets.items():
            y,x=np.unravel_index(np.sum((ar.astype(float)-rgb)**2,axis=2).argmin(),ar.shape[:2]);uvs[material]=[(x+.5)/ar.shape[1],(y+.5)/ar.shape[0]]
        pivots={'dorsal_liner':C,'dorsal_leaf_l':C-X*7.2,'dorsal_leaf_r':C+X*7.2}
        for bone,pivot in pivots.items():
            bones.append(dict(name=bone,parent='torso_upper',pivot=pivot.tolist()));mesh['parts'][bone]=dict(pivot=pivot.tolist(),vertices=[])
        def vertex(p,uv,n,bone):return [*(p-pivots[bone]),*uv,*n]
        def tri(bone,a,b,c,mat):
            n=np.cross(b-a,c-a);size=np.linalg.norm(n)
            if size<1e-8:return
            n/=size
            for p in [a,b,c]:mesh['parts'][bone]['vertices'].extend(vertex(p,uvs[mat],n,bone))
        def quad(bone,a,b,c,d,mat):tri(bone,a,b,c,mat);tri(bone,a,c,d,mat)
        def ring(t,r0,r1,mat):
            for a,b in zip(np.linspace(0,2*math.pi,49)[:-1],np.linspace(0,2*math.pi,49)[1:]):
                va=X*math.cos(a)+Y*math.sin(a);vb=X*math.cos(b)+Y*math.sin(b)
                quad('dorsal_liner',C+Z*t+va*r0,C+Z*t+vb*r0,C+Z*t+vb*r1,C+Z*t+va*r1,mat)
        # The inside is open, with a dark pressure tube and a succession of visible spinal ribs.
        for a,b in zip(np.linspace(0,2*math.pi,49)[:-1],np.linspace(0,2*math.pi,49)[1:]):
            va=X*math.cos(a)+Y*math.sin(a);vb=X*math.cos(b)+Y*math.sin(b)
            quad('dorsal_liner',C+Z*2+va*5.70,C+Z*(-35)+va*5.70,C+Z*(-35)+vb*5.70,C+Z*2+vb*5.70,'dark')
            quad('dorsal_liner',C+Z*1.3+va*7.2,C+Z*1.3+vb*7.2,C+Z*2.2+vb*7.2,C+Z*2.2+va*7.2,'armour')
        for t in [2,0,-3,-6,-10,-15,-21,-28,-34]:ring(t,5.20,7.2 if t>=0 else 5.72,'steel')
        for sign,bone in [(-1,'dorsal_leaf_l'),(1,'dorsal_leaf_r')]:
            # Two beveled pressure leaves, no window or decal pretending to be an opening.
            corners=[C+X*x+Y*y+Z*2.35 for x,y in [(sign*.02,-7.05),(sign*7.15,-7.05),(sign*7.15,7.05),(sign*.02,7.05)]]
            if sign<0:corners=corners[::-1]
            front=[p+Z*.55 for p in corners];quad(bone,*front,'armour');quad(bone,*corners[::-1],'dark')
            for i in range(4):j=(i+1)%4;quad(bone,corners[i],corners[j],front[j],front[i],'steel')
        mesh['r11_dorsal_socket']=dict(centre=C.tolist(),axis=Z.tolist(),radius=RADIUS,cut_source=str(base),original_triangles_cut=counts)
        mesh['triangleCount']=sum(len(p['vertices'])//24 for p in mesh['parts'].values())
        (PACK/'mesh'/f'{name}.mesh.json').write_text(json.dumps(mesh,separators=(',',':')),encoding='utf-8')
        (PACK/'geo'/f'{name}.geo.json').write_text(json.dumps(geo,indent=2),encoding='utf-8')
        if name=='eva_prototype':
            for category in ['mesh','geo']:
                suffix='mesh.json' if category=='mesh' else 'geo.json'
                shutil.copy2(PACK/category/f'{name}.{suffix}',source/category/f'{name}.{suffix}')
            for relative in [f'animations/{name}.animation.json',f'textures/entity/{name}.png',f'textures/entity/{name}_eyes.png']:
                shutil.copy2(source/relative,PACK/relative)
        report.append(dict(model=name,cut=counts,triangles=mesh['triangleCount']))
    (OUT/'socket_manifest.json').write_text(json.dumps(report,indent=2));print(report)

if __name__=='__main__':main()
