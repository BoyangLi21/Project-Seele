"""Local armour revision on the live skeleton, guided by inspected Lux3D volumes.

This writes a private candidate, never the installed model. R13 dorsal hardware
and runtime motion verification must be completed before promotion.
"""
import json,hashlib,shutil
from pathlib import Path
import numpy as np
import build_eva_un_body_r11 as previous

old=previous.old;m=previous.m
ROOT=m.ROOT;OUT=ROOT/'artifacts/world_repair_r19/un00_local';A=OUT/'assets/projectseele'
HAND_SCALE=1.55
raw_triangle=m.triangle;raw_ellipsoid=previous.original_ellipsoid;raw_capsule=m.capsule
raw_plate=previous.original_plate;raw_oriented=previous.original_oriented
original_dome=old.dome_face
skip_torso=True;transform_old=True;frames={};DETAILS=[]

def frame_map(a,b,c,d,radius):
    a,b,c,d=map(lambda v:np.asarray(v,float),(a,b,c,d));la=np.linalg.norm(b-a);lb=np.linalg.norm(d-c)
    return a,c,m.frame(b-a),m.frame(d-c),la,lb,radius

def mapped(points,bone):
    if bone not in frames:return np.asarray(points,float)
    a,c,source,target,la,lb,radius=frames[bone];local=(np.asarray(points)-a)@source
    s=local[:,1];cap=min(5,la*.18,lb*.18)
    local[:,1]=np.where(s<cap,s,np.where(s>la-cap,lb-la+s,cap+(s-cap)*(lb-2*cap)/(la-2*cap)))
    local[:,0]*=radius;local[:,2]*=radius
    return local@target.T+c

def triangle(bone,a,b,c,colour):
    if skip_torso and bone in ('torso_lower','torso_upper'):return
    points=np.asarray([a,b,c],float)
    if transform_old:
        points=mapped(points,bone)
        if bone.startswith('pylon_'):
            pivot=m.P[bone];points=pivot+(points-pivot)*[1.14,1,1.18]
        if bone.startswith('foot_'):
            pivot=m.P[bone];points[:,0]=pivot[0]+(points[:,0]-pivot[0])*1.20
    raw_triangle(bone,*points,colour)

def ellipsoid(bone,centre,radii,colour,*args,**kwargs):
    centre=np.asarray(centre,float);radii=np.asarray(radii,float)
    if transform_old and bone in frames and colour==4 and max(radii)<=.3:
        DETAILS.append(('bolt',bone,mapped([centre],bone)[0],.24));return
    if bone.startswith('hand_'):
        h=m.P[bone];centre=h+(centre-h)*HAND_SCALE;radii*=HAND_SCALE
    elif bone.startswith('finger_'):radii*=HAND_SCALE
    previous.ellipsoid(bone,centre,radii,colour,*args,**kwargs)

def finger_end(bone,a,b):
    a,b=np.asarray(a,float),np.asarray(b,float)
    if bone.startswith('finger_') and not any(row['parent']==bone for row in m.RIG):b=a+(b-a)*HAND_SCALE
    return a,b

def capsule(bone,a,b,radius,*args,**kwargs):
    if transform_old and bone in frames and radius<=.11:
        DETAILS.append(('seam',bone,*mapped([a,b],bone)));return
    if bone.startswith('finger_'):a,b=finger_end(bone,a,b);radius*=HAND_SCALE
    raw_capsule(bone,a,b,radius,*args,**kwargs)

def plate(bone,outline,thickness=1.5,colour=0,rim=4,bevel=.035,curve=.65):
    outline=np.asarray(outline,float)
    if bone.startswith('hand_'):
        h=m.P[bone];outline=h+(outline-h)*HAND_SCALE;thickness*=HAND_SCALE
    if bone.startswith('finger_'):rim=2
    raw_plate(bone,outline,thickness,colour,rim,min(.028,bevel),min(curve,.65))

def oriented(bone,a,b,profile,width,depth,front_offset=0,colour=0):
    if bone.startswith('finger_'):a,b=finger_end(bone,a,b);width*=HAND_SCALE;depth*=HAND_SCALE
    raw_oriented(bone,a,b,profile,width,depth,front_offset,colour)

def stable_armour_face(bone,vertices,normal,colour,depth):
    if not bone.startswith(('arm_','forearm_','leg_','shin_','hand_','finger_')):
        return original_dome(bone,vertices,normal,colour,depth)
    # Concave V-shaped plates cannot be filled by shrinking their outline
    # towards a centroid: that creates overlapping rings at the notch.
    # These manufactured plates use a proper planar triangulation instead.
    vertices=np.asarray(vertices);normal=np.asarray(normal);basis=m.frame(normal);uv=vertices@basis[:,[0,2]]
    for a,b,c in old.ears(uv):
        if np.cross(vertices[b]-vertices[a],vertices[c]-vertices[a])@normal<0:b,c=c,b
        old.T(bone,vertices[a],vertices[b],vertices[c],colour)

def panel(bone,points,colour=0,rim=4,depth=1.4,curve=.32):
    raw_plate(bone,np.asarray(points,float),depth,colour,rim,.022,curve)

def torso():
    # Closed, layered plates keep the central sternum continuous. The older
    # split recipe produced four broad sheets with an exposed central seam.
    m.loft('torso_upper',[(0,124,0),(0,133,0),(0,146,0),(0,155,0),(0,159,0)],
           [7,12,16.3,15.5,7.4],[5.5,7.1,7.7,6.3,4.1],1,32)
    for s in (-1,1):
        def wing(points,**kw):panel('torso_upper',[(s*x,y,z) for x,y,z in points],**kw)
        wing([(2.7,155.8,-6.9),(7.7,158,-5.8),(16.5,155,-6.4),(18,152,-6.9),(12,148.7,-9.4),(5.5,150,-9.8)],depth=1.55,curve=.3)
        wing([(1.8,148.8,-10),(11.6,151,-9.3),(15,147,-9.2),(9,140,-10.1),(2.2,134.5,-8.9)],depth=1.8,curve=.42)
        wing([(12.4,145,-7.5),(16,147,-6.2),(16.2,140.7,-5.8),(12.2,134.6,-6.5),(8.8,137,-8.1)],colour=3,depth=1.5)
        wing([(2.2,156,6.8),(11,155,7.2),(16,146,6.2),(11.5,137,7),(3,140,7.7)],depth=-1.6,curve=.22)
        for x,y,z in [(6.2,154.7,-9.0),(14.0,151.5,-8.4),(10.6,142.4,-10.35),(13.7,138.3,-8.0)]:
            DETAILS.append(('bolt','torso_upper',np.array([s*x,y,z]),.26))
            if y<140:DETAILS.append(('ring','torso_upper',np.array([s*x,y,z]),.72))
    panel('torso_upper',[(0,150.2,-10.35),(2.5,147,-10.8),(2.1,138,-10.3),(0,128.2,-8.0),(-2.1,138,-10.3),(-2.5,147,-10.8)],rim=6,depth=1.2,curve=.22)
    m.loft('torso_lower',[(0,97,0),(0,108,0),(0,117,0),(0,124.8,0)],[5.2,9.2,7.6,7.0],[4.8,6.2,5.1,5.6],1,32)
    for s in (-1,1):
        for i in range(7):
            y=107+i*2.5
            raw_capsule('torso_lower',(s*3.0,y-1.1,-5.6),(s*(7.3+.08*i),y+2.3,-4.8),.43,1,14)
        panel('torso_lower',[(s*1.2,123,-5.9),(s*5.8,125,-4.9),(s*7.2,118,-5.2),(s*4.8,109,-6.1),(s*.9,105,-6.5)],colour=3,rim=5,depth=1.1)
        # Outer hip guards follow the femur instead of sitting across a joint
        # whose leg must swing through them during a crouch.
        panel('leg_'+('r' if s>0 else 'l'),[(s*7.5,122,-5.2),(s*12,125,-3.7),(s*16.4,120,-2.7),(s*17.0,110,-3.6),(s*12.2,104,-5.4),(s*9.1,112,-6.1)],depth=1.6,curve=.4)
    panel('torso_lower',[(0,116,-7.5),(4.0,112,-7.8),(3.2,105,-7.6),(0,99,-6.5),(-3.2,105,-7.6),(-4,112,-7.8)],rim=6,depth=1.3)

def surface_details():
    # Old fasteners used a guessed constant front depth and were buried by
    # the curved armour. Project details onto the actual completed surfaces.
    cache={};placed={'bolts':0,'seams':0,'panels':0,'letters':0};missed=0
    def project(bone,u,v,axis=2):
        key=(bone,axis)
        if key not in cache:
            data=np.asarray(m.PARTS[bone]).reshape(-1,8);raw=(data[:,:3]+m.B[bone]['pivot'])*[-1,1,1]
            world=(np.c_[raw,np.ones(len(raw))]@m.bind(bone).T)[:,:3].reshape(-1,3,3);axes=(0,1) if axis==2 else (0,2)
            a=world[:,0,list(axes)];b=world[:,1,list(axes)]-a;c=world[:,2,list(axes)]-a;den=b[:,0]*c[:,1]-b[:,1]*c[:,0]
            mats=(np.floor(data[::3,3]*4)+4*np.floor(data[::3,4]*2)).astype(int);cache[key]=(world,a,b,c,den,mats)
        tri,a,b,c,den,mats=cache[key];delta=np.array([u,v])-a;valid=np.abs(den)>1e-8
        s=np.divide(delta[:,0]*c[:,1]-delta[:,1]*c[:,0],den,out=np.zeros_like(den),where=valid)
        t=np.divide(b[:,0]*delta[:,1]-b[:,1]*delta[:,0],den,out=np.zeros_like(den),where=valid)
        ok=valid&(s>=-1e-5)&(t>=-1e-5)&(s+t<=1.00001)
        ids=np.flatnonzero(ok)
        if not len(ids):return None
        depth=tri[:,0,axis]+s*(tri[:,1,axis]-tri[:,0,axis])+t*(tri[:,2,axis]-tri[:,0,axis]);i=int(ids[np.argmin(depth[ids]) if axis==2 else np.argmax(depth[ids])])
        point=tri[i,0]+s[i]*(tri[i,1]-tri[i,0])+t[i]*(tri[i,2]-tri[i,0]);normal=np.cross(tri[i,1]-tri[i,0],tri[i,2]-tri[i,0]);normal/=np.linalg.norm(normal)
        if (axis==2 and normal[axis]>0) or (axis==1 and normal[axis]<0):normal=-normal
        return point,normal,int(mats[i])
    def line(bone,points,colour=5,radius=.055,axis=2,allow_rubber=False):
        nonlocal missed
        previous_point=None
        for aa,bb in zip(points,points[1:]):
            aa,bb=np.asarray(aa),np.asarray(bb)
            for q in np.linspace(aa,bb,max(2,int(np.linalg.norm(bb-aa)/.55)+1)):
                hit=project(bone,q[0],q[1] if axis==2 else q[2],axis)
                if hit is None:previous_point=None;missed+=1;continue
                point,normal,material=hit
                if not allow_rubber and material in (1,5,7):previous_point=None;continue
                point=point+normal*.065
                if previous_point is not None and 1e-5<np.linalg.norm(point-previous_point)<1.4:m.loft(bone,[previous_point,point],[radius,radius],[radius,radius],colour,8)
                previous_point=point
    def bolt(bone,rough,radius,axis=2):
        nonlocal missed
        hit=project(bone,rough[0],rough[1] if axis==2 else rough[2],axis)
        if hit is None:missed+=1;return
        point,normal,material=hit
        if material in (1,5,7):return
        point+=normal*.07;raw_ellipsoid(bone,point,(radius,.07,radius),4,16,6,normal)
        tangent=np.cross(normal,[0,1,0] if abs(normal[1])<.8 else [1,0,0]);tangent/=np.linalg.norm(tangent)
        m.loft(bone,[point+normal*.075-tangent*.10,point+normal*.075+tangent*.10],[.023,.023],[.023,.023],5,6);placed['bolts']+=1
    for kind,bone,a,b in DETAILS:
        if kind=='seam':line(bone,[a,b]);placed['seams']+=1
        elif kind=='bolt':bolt(bone,a,b)
        else:
            hit=project(bone,a[0],a[1])
            if hit:m.ring(bone,hit[0]+hit[1]*.08,hit[1],b,.09,4,28)
    def inset(bone,polygon,axis=2):
        xy=np.array([[q[0],q[1] if axis==2 else q[2]] for q in polygon])
        boundary=[project(bone,*q,axis) for q in xy]
        if any(q is None or q[2] in (1,5,7) for q in boundary):return
        staged=[];valid=[True]
        def emit(a,b,c,depth):
            if depth:
                ab=(a+b)/2;bc=(b+c)/2;ca=(c+a)/2
                for t in [(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)]:emit(*t,depth-1)
            else:
                hits=[project(bone,*p,axis) for p in (a,b,c)]
                if any(h is None or h[2] in (1,5,7) for h in hits):valid[0]=False;return
                points=[p+n*.07 for p,n,_ in hits];normal=np.cross(points[1]-points[0],points[2]-points[0]);sign=-1 if axis==2 else 1
                if normal[axis]*sign<0:points[1],points[2]=points[2],points[1]
                staged.append(points)
        for i,j,k in old.ears(xy):emit(xy[i],xy[j],xy[k],2)
        if not valid[0]:return
        for points in staged:raw_triangle(bone,*points,3)
        line(bone,polygon+[polygon[0]],5,.05,axis)
        for q in (polygon[0],polygon[2]):bolt(bone,q,.20,axis)
        placed['panels']+=1
    for side in ('l','r'):
        for name,end,width in [('leg','shin',6.0),('shin','foot',4.5),('forearm','hand',4.2)]:
            bone=name+'_'+side;a=m.P[bone];b=m.P[end+'_'+side]
            outline=[a+(b-a)*t+np.array([u*width,0,0]) for u,t in [(-.48,.28),(.38,.24),(.58,.40),(.30,.68),(-.38,.75),(-.58,.48)]]
            inset(bone,outline)
        s=-1 if side=='l' else 1
        for i in range(3):
            line('torso_upper',[np.array([s*(3.4+i*.55),126.0+i*.6,0]),np.array([s*(8.0+i*.35),132.0+i*.6,0])],3,.14,allow_rubber=True)
        foot='foot_'+side;cx=m.P[foot][0]
        for offset in (-3.2,0,3.2):
            inset(foot,[np.array([cx+offset-1.2,0,-22]),np.array([cx+offset+1.2,0,-22]),np.array([cx+offset+.9,0,-12]),np.array([cx+offset-.9,0,-12])],1)
        bone='pylon_'+side;cx=(-1 if side=='l' else 1)*24.7
        for dx in (-2.7,2.7):
            for y in (150,157.5):bolt(bone,np.array([cx+dx,y,0]),.22)
        # Front-facing UN lettering consists of surface-fitted strokes, not a
        # floating text entity or a screenshot pasted onto the armour.
        letters=[[(-1.65,1.2),(-1.65,-.5),(-1.35,-1.1),(-.55,-1.1),(-.25,-.5),(-.25,1.2)],[(.35,-1.1),(.35,1.2),(1.7,-1.1),(1.7,1.2)]]
        for stroke in letters:line(bone,[np.array([cx-u,160+v,0]) for u,v in stroke],6,.105);placed['letters']+=1
    return dict(placed=placed,unmatched_surface_samples=missed)

def main():
    global skip_torso,transform_old
    OUT.mkdir(parents=True,exist_ok=True)
    for name in ('textures/entity','geo','mesh','animations'):(A/name).mkdir(parents=True,exist_ok=True)
    m.OUT=OUT;m.A=A;m.PARTS.clear();m.PREVIEW.clear();m.BIND.clear()
    m.COLOURS=['#24282d','#090d10','#5a646a','#343e43','#aa8242','#030506','#d4aa5e','#ffda88']
    original_pivots={b['name']:list(b['pivot']) for b in m.RIG}
    for side,s in [('l',-1),('r',1)]:
        hand=m.P['hand_'+side].copy()
        for name in list(m.B):
            if name.startswith('finger_') and name.endswith('_'+side):
                m.P[name]=hand+(m.P[name]-hand)*HAND_SCALE;m.B[name]['pivot']=(m.P[name]*[-1,1,1]).tolist()
        shoulder=m.P['arm_'+side];old_elbow=np.array([s*23.489652,123.435069,7.737214]);elbow=m.P['forearm_'+side]
        hip=m.P['leg_'+side];knee=m.P['shin_'+side];old_knee=knee+[0,11.4,0];ankle=m.P['foot_'+side]
        frames['arm_'+side]=frame_map(shoulder,old_elbow,shoulder,elbow,1.28)
        frames['forearm_'+side]=frame_map(old_elbow,hand,elbow,hand,1.40)
        frames['leg_'+side]=frame_map(hip,old_knee,hip,knee,1.38)
        frames['shin_'+side]=frame_map(old_knee,ankle,knee,ankle,1.50)
    m.triangle=old.T=triangle;m.ellipsoid=ellipsoid;m.capsule=capsule;old.plate=plate;old.oriented_plate=oriented;old.dome_face=stable_armour_face
    old.body();skip_torso=False;transform_old=False;torso();details=surface_details();marks=previous.insignia();m.save()
    installed=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele/animations/eva_prototype.animation.json'
    if not installed.exists():installed=ROOT/'src/main/resources/assets/projectseele/animations/eva_prototype.animation.json'
    shutil.copy2(installed,A/'animations/eva_prototype.animation.json')
    path=A/'mesh/eva_prototype.mesh.json';mesh=json.loads(path.read_text());mesh.update(source='Original locally authored R19 armour, proportions reviewed against Lux3D task 3541743 and the accepted black/gold concept',eye_socket_model=[0,173,-7.22]);path.write_text(json.dumps(mesh,separators=(',',':')))
    report=json.loads((OUT/'model_manifest.json').read_text());report.update(name='EVA-UN-00',stage='PRIVATE BODY CANDIDATE - dorsal hardware and live validation pending',hand_scale=HAND_SCALE,
        original_pivots=original_pivots,canonical_major_joint_centres_preserved=True,finger_pivots_scaled_about_unchanged_wrists=True,knee_visual_offset_corrected=11.4,elbow_visual_offset_corrected=[.127,-.790,-6.425],surface_projected_emblem_triangles=marks,
        lux3d_reference='artifacts/world_repair_r19/lux3d/EVA-UN-00-original.glb',surface_details=details,mesh_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (OUT/'model_manifest.json').write_text(json.dumps(report,indent=2));print('Private R19 body candidate ready',report['triangles'],'triangles',flush=True)

if __name__=='__main__':main()
