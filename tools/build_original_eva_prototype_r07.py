"""Author an original experimental EVA mesh on the project's animation skeleton.

All surfaces are built here from lofts, armor shells and mechanical details;
no vertices, UVs or textures are copied from an existing EVA model.
"""
from pathlib import Path
from collections import defaultdict
import json,math,hashlib,subprocess
import numpy as np
from scipy.spatial.transform import Rotation
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1];A=ROOT/'src/main/resources/assets/projectseele';OUT=ROOT/'artifacts/world_expansion_r07/prototype'
RIG=json.loads((A/'eva/eva_rig_schema.json').read_text())['bones'];B={b['name']:b for b in RIG};P={n:np.array(b['pivot'])*[-1,1,1] for n,b in B.items()}
PARTS=defaultdict(list);PREVIEW=[];BIND={}
COLOURS=['#d4d1c4','#263035','#737a76','#4b5b43','#484f4f','#111a1e','#ae8c4b','#99be69']
def bind(n):
    if n not in BIND:
        b=B[n];q=Rotation.from_euler('xyz',np.array(b['bindRotationDegrees'])*[-1,-1,1],degrees=True).as_matrix()
        m=np.eye(4);m[:3,:3]=q;m[:3,3]=P[n]-q@P[n]
        BIND[n]=bind(b['parent'])@m if b['parent'] else m
    return BIND[n]
def frame(axis):
    y=np.asarray(axis,float);y/=np.linalg.norm(y);x=np.array([1.,0,0]);x-=y*x.dot(y)
    if np.linalg.norm(x)<.01:x=np.array([0.,0,1]);x-=y*x.dot(y)
    x/=np.linalg.norm(x);return np.column_stack((x,y,np.cross(x,y)))
def triangle(bone,a,b,c,colour):
    v=np.array([a,b,c],float);normal=np.cross(v[1]-v[0],v[2]-v[0]);length=np.linalg.norm(normal)
    if length<1e-7:return
    normal/=length;inverse=np.linalg.inv(bind(bone));local=(np.c_[v,np.ones(3)]@inverse.T)[:,:3];n=inverse[:3,:3]@normal
    source=local*[-1,1,1]-np.array(B[bone]['pivot']);n=n*[-1,1,1]
    # Each material gets an atlas tile; modest UV variation shows its finish.
    col=colour%4;row=colour//4
    for i in range(3):
        u=(col+.08+(i==1)*.82)/4;w=(row+.08+(i==2)*.82)/2
        PARTS[bone].extend([*np.round(source[i],5),round(u,6),round(w,6),*np.round(n,6)])
    PREVIEW.append((v,colour))
def loft(bone,points,widths,depths,colour=0,sides=24,caps=True):
    points=np.array(points,float);rings=[]
    for i,point in enumerate(points):
        direction=points[min(i+1,len(points)-1)]-points[max(0,i-1)];basis=frame(direction)
        ring=[point+basis[:,0]*widths[i]*math.cos(t)+basis[:,2]*depths[i]*math.sin(t) for t in np.linspace(0,2*math.pi,sides,endpoint=False)];rings.append(ring)
    for i in range(len(rings)-1):
        for j in range(sides):
            k=(j+1)%sides;triangle(bone,rings[i][j],rings[i+1][j],rings[i+1][k],colour);triangle(bone,rings[i][j],rings[i+1][k],rings[i][k],colour)
    if caps:
        for j in range(sides):
            k=(j+1)%sides;triangle(bone,points[0],rings[0][k],rings[0][j],colour);triangle(bone,points[-1],rings[-1][j],rings[-1][k],colour)
def ellipsoid(bone,centre,radii,colour=1,segments=24,rings=12,axis=(0,1,0)):
    centre=np.array(centre,float);basis=frame(axis);rx,ry,rz=radii;rows=[]
    for phi in np.linspace(-math.pi/2,math.pi/2,rings+1):
        rows.append([centre+basis@np.array([rx*math.cos(phi)*math.cos(t),ry*math.sin(phi),rz*math.cos(phi)*math.sin(t)]) for t in np.linspace(0,2*math.pi,segments,endpoint=False)])
    for i in range(rings):
        for j in range(segments):
            k=(j+1)%segments;triangle(bone,rows[i][j],rows[i+1][j],rows[i+1][k],colour);triangle(bone,rows[i][j],rows[i+1][k],rows[i][k],colour)
def capsule(bone,a,b,radius,colour=1,sides=24):
    a=np.array(a,float);b=np.array(b,float);t=np.linspace(0,1,9)
    loft(bone,[a*(1-x)+b*x for x in t],[radius*(.62+.38*math.sin(math.pi*x)) for x in t],[radius*(.55+.45*math.sin(math.pi*x)) for x in t],colour,sides)
def ring(bone,centre,axis,radius,tube,colour=2,segments=28):
    c=np.array(centre,float);basis=frame(axis)
    rows=[]
    for u in np.linspace(0,2*math.pi,segments,endpoint=False):
        radial=basis[:,0]*math.cos(u)+basis[:,2]*math.sin(u)
        rows.append([c+radial*(radius+tube*math.cos(v))+basis[:,1]*tube*math.sin(v) for v in np.linspace(0,2*math.pi,8,endpoint=False)])
    for i in range(segments):
        j=(i+1)%segments
        for k in range(8):
            l=(k+1)%8;triangle(bone,rows[i][k],rows[j][k],rows[j][l],colour);triangle(bone,rows[i][k],rows[j][l],rows[i][l],colour)
def armour(bone,centre,axis,length,width,depth,colour=0):
    c=np.array(centre,float);v=np.array(axis,float);v/=np.linalg.norm(v)
    t=np.array([-.5,-.46,-.32,.05,.34,.47,.5]);shape=np.array([.24,.61,.93,1,.81,.45,.12])
    if colour!=0 or length<10:
        loft(bone,[c+v*x*length for x in t],width*shape,depth*shape,colour,24);return
    # Broad planar ceramic faces, bevelled shoulders and separate machined rim.
    # The flatter cross section reads as fitted armor instead of a rubber capsule.
    basis=frame(v);rows=[]
    for value,s in zip(t,shape):
        ring=[]
        for angle in np.linspace(0,2*math.pi,16,endpoint=False):
            a,b=math.cos(angle),math.sin(angle)
            ring.append(c+v*value*length+basis[:,0]*width*s*np.sign(a)*abs(a)**.56+basis[:,2]*depth*s*np.sign(b)*abs(b)**.56)
        rows.append(ring)
    for i in range(len(rows)-1):
        for j in range(16):
            k=(j+1)%16;mat=2 if i in (0,5) else colour
            triangle(bone,rows[i][j],rows[i+1][j],rows[i+1][k],mat);triangle(bone,rows[i][j],rows[i+1][k],rows[i][k],mat)
    for j in range(16):
        k=(j+1)%16;triangle(bone,c-v*length*.5,rows[0][k],rows[0][j],2);triangle(bone,c+v*length*.5,rows[-1][j],rows[-1][k],2)
    front=basis[:,2]*(-1 if basis[2,2]>0 else 1)
    # Paired inlaid seams and countersunk fasteners remain attached to this plate's bone.
    if length>=16:
        for side in (-1,1):
            pts=[]
            for value in np.linspace(-.29,.27,9):
                s=np.interp(value,t,shape);pts.append(c+v*value*length+basis[:,0]*side*width*s*.72+front*depth*s*.91)
            loft(bone,pts,[.055]*9,[.075]*9,5,6)
            for value in (-.28,.25):
                s=np.interp(value,t,shape);point=c+v*value*length+basis[:,0]*side*width*s*.70+front*depth*s*.94
                ellipsoid(bone,point,(.19,.09,.19),4,12,6,front)
def body():
    # Biological core and separate overlapping ceramic chest/pelvis shells.
    loft('torso_lower',[[0,106,0],[0,111,0],[0,117,0],[0,123,0],[0,127,0]], [7,13,11,8,7],[6,8,7,5.8,6],1,32)
    loft('torso_upper',[[0,124,0],[0,130,0],[0,141,0],[0,150,0],[0,155,0]], [7,9,17,18,9],[6,7,9,8,5],1,32)
    for y in range(120,143,3):
        for sign in (-1,1):armour('torso_upper' if y>=126 else 'torso_lower',(sign*(8+(y-120)*.15),y,-4),(sign*.6,.25,1),10,1.2,1.4,4)
    for sign in (-1,1):
        armour('torso_upper',(sign*10,147,-6),(sign*.6,.32,.06),24,6.2,3.2)
        armour('torso_upper',(sign*6,137,-8),(sign*.6,.85,-.1),17,4.2,2)
        armour('torso_lower',(sign*9,113,-5),(sign*.5,.8,-.15),20,4.8,2.5)
        armour('torso_lower',(sign*12,111,4),(sign*.25,.9,.15),18,4.6,2.6)
        ellipsoid('torso_upper',(sign*6,145,8),(2.9,2.9,1.8),5)
        ring('torso_upper',(sign*6,145,9.4),(0,0,1),2.3,.5,2)
    armour('torso_upper',(0,143,-8.5),(0,1,0),20,2.6,1.6)
    armour('torso_upper',(0,150,7.5),(0,1,0),15,5,2.1)
    capsule('neck',(0,153,0),(0,165,0),4.0,1)
    # A split lanceolate helmet with one recessed vertical optical assembly.
    ellipsoid('head',(0,170,0),(6.0,11,7),5,32,18)
    for sign in (-1,1):
        loft('head',[[sign*2,156,-7],[sign*5,166,-6],[sign*6,176,-2],[sign*3,182,1]], [1.0,2.6,2.8,.9],[2,3.7,5,2],0,20)
        armour('head',(sign*4.5,164,-9),(sign*.3,.9,.28),14,1.8,2.1)
        ring('head',(sign*5.8,168,1),(1,0,0),2.6,.5,2)
    ellipsoid('head',(0,171,-7.2),(2.4,4.1,2.2),3,32,18)
    ellipsoid('head',(0,171,-9.1),(.84,2.9,.38),7,28,14)
    for x in (-1.2,1.2):capsule('head',(x,168,-9.25),(x,174,-9.25),.19,2,12)
    loft('head',[[0,180,2],[0,187,4],[0,193,6]],[2,1,.18],[3,1.8,.25],0,12)
    for side,sign in [('l',-1),('r',1)]:
        shoulder=P['arm_'+side];elbow=np.array([sign*23.489652,123.435069,7.737214]);wrist=P['hand_'+side]
        capsule('arm_'+side,shoulder,elbow,4.9,1)
        ellipsoid('forearm_'+side,elbow,(4.9,5,4.9),1)
        capsule('forearm_'+side,elbow,wrist,4.1,1)
        armour('arm_'+side,shoulder*.55+elbow*.45+[sign*2.4,0,-.7],elbow-shoulder,25,5.5,4.5)
        armour('forearm_'+side,elbow*.42+wrist*.58+[sign*.8,0,-1],wrist-elbow,27,5,3.8)
        ring('arm_'+side,shoulder+[sign*5.5,0,0],(1,0,0),5.1,.9,2)
        ring('forearm_'+side,elbow+[sign*3.8,0,0],(1,0,0),2.7,.55,2)
        for t in np.linspace(.2,.8,8):ring('forearm_'+side,elbow*(1-t)+wrist*t,wrist-elbow,3.9,.28,4,18)
        px=sign*24
        armour('pylon_'+side,(px,168,1),(sign*.14,1,.14),34,3.9,4.3)
        armour('pylon_'+side,(px-sign*2,168,4),(sign*.14,1,.14),29,2.4,3,4)
        ellipsoid('pylon_'+side,(sign*25,153,0),(7.4,10.3,7),0)
        ring('pylon_'+side,(sign*31,153,0),(1,0,0),4.5,.8,2)
        hip=P['leg_'+side];knee=P['shin_'+side]+[0,11.4,0];ankle=P['foot_'+side]
        capsule('leg_'+side,hip,knee,6.2,1)
        ellipsoid('shin_'+side,knee,(5.3,5.6,5.3),1)
        capsule('shin_'+side,knee,ankle,4.6,1)
        armour('leg_'+side,hip*.48+knee*.52+[sign*1.4,0,-1.8],knee-hip,37,6.3,5.2)
        armour('shin_'+side,knee*.4+ankle*.6+[sign*.5,0,-2],ankle-knee,42,5.3,4.2)
        armour('shin_'+side,knee+[0,-1,-4.6],(0,1,.2),13,4,2.7)
        ring('shin_'+side,knee+[sign*4.4,0,0],(1,0,0),3.5,.55,2)
        for y in np.linspace(76,83,5):ring('leg_'+side,(sign*15,y,.6),(0,1,0),4.4,.32,4,20)
        # Articulated boot, with a long armored instep and a broad stable sole.
        foot='foot_'+side;x=ankle[0]
        loft(foot,[[x,2,5],[x,2,-3],[x,3,-11],[x,4,-22]],[5.2,5.4,5.1,3.4],[2.0,2.0,2.3,2.5],4,24)
        armour(foot,(x,9,-5),(0,.55,1),23,5.3,4.2)
        armour(foot,(x,5,-17),(0,.2,1),16,4.8,3.1)
        ellipsoid(foot,ankle,(4.1,5.5,4),1)
        for dx in (-2.6,0,2.6):armour(foot,(x+dx,3,-22),(0,0,1),6,1.1,1.3,4)
        ring(foot,ankle+[sign*3.8,0,0],(1,0,0),2.6,.55,2)
        hand='hand_'+side;h=P[hand]
        armour(hand,h+[0,-1,0],(0,1,0),8,4.5,2.8,4)
        armour(hand,h+[0,-1,-2.2],(0,1,0),6.8,4.2,1.3,0)
        for finger in ['index','middle','ring','little','thumb']:
            names=[f'finger_{finger}_{side}',f'finger_{finger}_tip_{side}',f'finger_{finger}_distal_{side}']
            names=[n for n in names if n in P]
            for i,n in enumerate(names):
                start=P[n];end=P[names[i+1]] if i+1<len(names) else start+[0,-2.2,0]
                capsule(n,start,end,.88 if finger!='thumb' else 1.15,1,16)
                ellipsoid(n,start,(1.15,1.05,1.0),2,16,8)
                armour(n,(start+end)/2+[0,0,-.5],end-start,max(1.8,np.linalg.norm(end-start)*.8),.85,.65,0)
def save():
    OUT.mkdir(parents=True,exist_ok=True)
    image=Image.new('RGB',(1024,512));draw=ImageDraw.Draw(image)
    rng=np.random.default_rng(701)
    for i,c in enumerate(COLOURS):
        x=i%4*256;y=i//4*256;draw.rectangle((x,y,x+255,y+255),fill=c)
        rgb=np.array(Image.new('RGB',(1,1),c))[0,0]
        for _ in range(700):
            xx=int(rng.integers(x+5,x+251));yy=int(rng.integers(y+5,y+251));delta=int(rng.integers(-11,12));col=tuple(np.clip(rgb.astype(int)+delta,0,255));draw.point((xx,yy),fill=col)
    image.save(A/'textures/entity/eva_prototype.png')
    eyes=Image.new('RGBA',image.size,(0,0,0,0));eyes.paste(image.crop((768,256,1024,512)).convert('RGBA'),(768,256));eyes.save(A/'textures/entity/eva_prototype_eyes.png')
    # Smooth continuous machined/organic surfaces within each material without
    # blending an armor normal across a different plate or rubber sleeve.
    parts={}
    for name,values in PARTS.items():
        v=np.array(values).reshape(-1,8);keys=np.c_[v[:,:3],np.floor(v[:,3]*4),np.floor(v[:,4]*2)]
        unique,indices=np.unique(keys,axis=0,return_inverse=True);normals=np.zeros((len(unique),3));np.add.at(normals,indices,v[:,5:])
        normals/=np.maximum(1e-9,np.linalg.norm(normals,axis=1,keepdims=True));v[:,5:]=normals[indices]
        parts[name]=dict(pivot=B[name]['pivot'],vertices=np.round(v,6).ravel().tolist())
    count=sum(len(v)//24 for v in PARTS.values())
    digest=hashlib.sha256(json.dumps(parts,separators=(',',':')).encode()).hexdigest()
    mesh=dict(format_version=1,model_height=193.1,stride=8,triangleCount=count,source='Original R07 loft/armor construction; no imported EVA mesh',sourceSha256=digest,parts=parts)
    (A/'mesh').mkdir(exist_ok=True);(A/'mesh/eva_prototype.mesh.json').write_text(json.dumps(mesh,separators=(',',':')),encoding='utf8')
    geo={'format_version':'1.12.0','minecraft:geometry':[{'description':{'identifier':'geometry.eva_prototype','texture_width':1024,'texture_height':512,'visible_bounds_width':20,'visible_bounds_height':24,'visible_bounds_offset':[0,8,0]},'bones':[dict(name=b['name'],pivot=b['pivot'],**({'parent':b['parent']} if b['parent'] else {}),**({'rotation':b['bindRotationDegrees']} if any(b['bindRotationDegrees']) else {})) for b in RIG]}]}
    (A/'geo/eva_prototype.geo.json').write_text(json.dumps(geo,indent=2),encoding='utf8')
    animations=subprocess.check_output(['git','show','HEAD:src/main/resources/assets/projectseele/animations/eva_unit01.animation.json'],cwd=ROOT)
    (A/'animations/eva_prototype.animation.json').write_bytes(animations)
    verts=np.vstack([v for v,c in PREVIEW]);cols=np.array([c for v,c in PREVIEW]);np.savez_compressed(OUT/'model.npz',vertices=verts,materials=cols,colours=np.array(COLOURS))
    report=dict(triangles=count,parts=len(parts),bones=len(RIG),bounds=[verts.min(0).tolist(),verts.max(0).tolist()],sha256=digest,original_geometry=True,animation_contract='Existing project rig and public HEAD animation resource, original body geometry')
    (OUT/'model_manifest.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
if __name__=='__main__':body();save()
