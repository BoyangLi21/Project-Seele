"""Rebuild the approved test-article silhouette with beveled armor and black/gold finishes."""
import json,math,hashlib
import numpy as np
import build_original_eva_prototype_r07 as m

m.OUT=m.ROOT/'artifacts/world_refinement_r08/prototype'
m.COLOURS=['#343a40','#0e1318','#687174','#343b40','#b99450','#030507','#e1b960','#ffcc69']
T=m.triangle;P=m.P

def ears(poly):
    q=np.array(poly);remaining=list(range(len(q)));area=sum(q[i,0]*q[(i+1)%len(q),1]-q[(i+1)%len(q),0]*q[i,1] for i in remaining)
    if area<0:remaining.reverse()
    triangles=[]
    cross=lambda a,b,c:float((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
    while len(remaining)>3:
        found=False
        for i,b in enumerate(remaining):
            a=remaining[i-1];c=remaining[(i+1)%len(remaining)]
            if cross(q[a],q[b],q[c])<=1e-8:continue
            inside=False
            for v in remaining:
                if v in (a,b,c):continue
                if min(cross(q[a],q[b],q[v]),cross(q[b],q[c],q[v]),cross(q[c],q[a],q[v]))>=-1e-7:inside=True;break
            if inside:continue
            triangles.append((a,b,c));remaining.pop(i);found=True;break
        if not found:raise ValueError('Invalid armor outline')
    triangles.append(tuple(remaining));return triangles

def dome_face(bone,v,front,colour,depth):
    """Curved stamped armor: nested contour rings preserve a nonrectangular rim."""
    c=v.mean(0);previous=v
    for t in (.16,.34,.53,.71,.87):
        current=c+(v-c)*(1-t)+front*(depth*math.sin(t*math.pi/2))
        for i in range(len(v)):
            j=(i+1)%len(v)
            if front[2]<0:T(bone,previous[i],current[j],previous[j],colour);T(bone,previous[i],current[i],current[j],colour)
            else:T(bone,previous[i],previous[j],current[j],colour);T(bone,previous[i],current[j],current[i],colour)
        previous=current
    c+=front*depth
    for i in range(len(v)):
        j=(i+1)%len(v)
        if front[2]<0:T(bone,previous[i],c,previous[j],colour)
        else:T(bone,previous[i],previous[j],c,colour)

def rounded_outline(v,fraction=.13):
    v=np.array(v,float);return np.array([q for i,p in enumerate(v) for q in (p*(1-fraction)+v[i-1]*fraction,p*(1-fraction)+v[(i+1)%len(v)]*fraction)])

def plate(bone,outline,thickness=1.5,colour=0,rim=4,bevel=.035,curve=.65):
    """A closed, inset face and an actual bevel; concave silhouettes are triangulated."""
    v=np.array(outline,float)
    area=sum(v[i,0]*v[(i+1)%len(v),1]-v[(i+1)%len(v),0]*v[i,1] for i in range(len(v)))
    if area<0:v=v[::-1]
    centre=v.mean(0);front=v.copy();front[:,:2]=centre[:2]+(v[:,:2]-centre[:2])*(1-bevel);front[:,2]+= -.25 if thickness>0 else .25
    rear=v+[0,0,thickness]
    def face(a,b,c,mat):
        T(bone,a,c,b,mat) if thickness>0 else T(bone,a,b,c,mat)
    dome_face(bone,front,np.array([0.,0.,-1 if thickness>0 else 1]),colour,curve)
    for a,b,c in ears(v[:,:2]):face(rear[c],rear[b],rear[a],3)
    for i in range(len(v)):
        j=(i+1)%len(v)
        face(v[i],v[j],front[j],rim);face(v[i],front[j],front[i],rim)
        face(v[i],rear[i],rear[j],colour);face(v[i],rear[j],v[j],colour)

def mirrored_plate(bone,sign,xy,z,**kw):plate(bone,[(sign*x,y,z if np.isscalar(z) else z[i]) for i,(x,y) in enumerate(xy)],**kw)

def oriented_plate(bone,a,b,profile,width,depth,front_offset=0,colour=0):
    a=np.array(a,float);b=np.array(b,float);axis=b-a;length=np.linalg.norm(axis);axis/=length
    side=np.array([1.,0,0]);side-=axis*np.dot(side,axis);side/=np.linalg.norm(side)
    front=np.cross(side,axis);front*= -1 if front[2]>0 else 1
    vertices=[a+axis*(t*length)+side*(u*width)+front*(depth+front_offset) for u,t in profile]
    # In-plane triangulation uses local profile, so angled forearms keep their true silhouette.
    profile=np.array(profile)
    if sum(profile[i,0]*profile[(i+1)%len(profile),1]-profile[(i+1)%len(profile),0]*profile[i,1] for i in range(len(profile)))<0:
        vertices=vertices[::-1];profile=profile[::-1]
    v=np.array(vertices);centre=v.mean(0);inner=centre+(v-centre)*.94+front*.20;back=centre+(v-centre)*.79-front*max(1.2,depth*1.8)
    outward=np.dot(np.cross(side,axis),front)>0
    def face(a,b,c,mat):T(bone,a,b,c,mat) if outward else T(bone,a,c,b,mat)
    dome_face(bone,inner,front,colour,min(1.6,width*.24))
    for i,j,k in ears(profile):face(back[k],back[j],back[i],3)
    for i in range(len(v)):
        j=(i+1)%len(v);face(v[i],v[j],inner[j],4);face(v[i],inner[j],inner[i],4);face(v[i],back[i],back[j],colour);face(v[i],back[j],v[j],colour)
    for t in (.22,.74):
        for s in (-1,1):
            point=a+axis*t*length+side*s*width*.42+front*(depth+front_offset+.30)
            m.ellipsoid(bone,point,(.21,.08,.21),6,12,6,front)

def mechanical_joint(bone,c,axis,r):
    m.ellipsoid(bone,c,(r,.55,r),1,24,12,axis)
    m.ring(bone,c,axis,r*.89,.36,4,32);m.ring(bone,np.array(c)+np.array(axis)*.22,axis,r*.68,.25,2,28)

def boot(bone,x):
    # A load-bearing heel and toe share one ground plane, not two floating lofts.
    profile=np.array([(6,0),(7,2),(7,10),(3,16),(-2,16),(-6,11),(-12,7),(-21,5),(-24,2),(-23,0)],float)
    widths=np.interp(profile[:,0],[-24,-20,-10,0,7],[3.0,3.6,4.7,4.8,3.7])
    sides=[]
    for sign in (-1,1):
        verts=np.array([(x+sign*w,y,z) for (z,y),w in zip(profile,widths)]);sides.append(verts)
        for i,j,k in ears(profile):
            if sign<0:T(bone,verts[i],verts[k],verts[j],0)
            else:T(bone,verts[i],verts[j],verts[k],0)
    for i in range(len(profile)):
        j=(i+1)%len(profile);colour=5 if i in (0,8,9) else 0
        T(bone,sides[0][i],sides[1][j],sides[0][j],colour);T(bone,sides[0][i],sides[1][i],sides[1][j],colour)
    for sign in (-1,1):
        for z in (-17,-10,-3):m.capsule(bone,(x+sign*4.0,2,z),(x+sign*4.0,5,z+2),.15,4,10)

def body():
    # A narrower segmented biological core, with convergent abdominal straps.
    m.loft('torso_lower',[(0,102,0),(0,110,0),(0,118,0),(0,127,0)],[6.3,10.2,7.8,7.0],[5.2,6.5,5.1,5.8],1,32)
    m.loft('torso_upper',[(0,124,0),(0,134,0),(0,145,0),(0,154,0),(0,159,0)],[7,12,16.4,17,7.3],[5.8,7.4,8,6.4,4.3],1,32)
    for s in (-1,1):
        for i in range(6):
            y=118+i*3.1
            m.capsule('torso_lower' if y<127 else 'torso_upper',(s*(2.2+i*.48),y-4,-5.1),(s*(7.6+i*.7),y+2.2,-4.6),.77,3,16)
        mirrored_plate('torso_upper',s,[(1.7,152),(7,157),(17.5,155),(18.6,151),(13.6,145),(7.5,142),(5.3,147)],[-9,-8.2,-5,-6.8,-9.8,-11.2,-10],thickness=2.3)
        mirrored_plate('torso_upper',s,[(1.1,147),(6.4,150),(14.4,146),(13.0,140),(8.2,136),(5.0,128),(2.4,136)],-8.5,thickness=2.3)
        mirrored_plate('torso_upper',s,[(7,142),(12.9,146),(14.5,143),(12.5,135),(8,130)],-5.0,thickness=2.0,colour=3,rim=5)
        # Scapular plates and paired dorsal service sockets.
        mirrored_plate('torso_upper',s,[(1.5,155),(10,154),(15,146),(11,138),(3.2,142)],7.8,thickness=-2.1,colour=0,rim=4)
        mechanical_joint('torso_upper',(s*7.5,143,9),(0,0,1),2.4)
    plate('torso_upper',[(0,154,-8),(3.1,148,-10),(2.5,138,-10.7),(0,128,-9),(-2.5,138,-10.7),(-3.1,148,-10)],2.0,0,6)
    # Distinct pelvic shell, with a tapered central groin rather than detached capsules.
    for s in (-1,1):
        mirrored_plate('torso_lower',s,[(1.8,116),(6,121),(11.8,124),(14.8,119),(14.4,108),(10.5,104),(7.3,114),(3.2,110)],-5.2,thickness=3)
        mirrored_plate('torso_lower',s,[(12.1,121),(16.2,117),(17.0,106),(13.2,98),(11.6,107)],.5,thickness=5,colour=0,rim=4)
    plate('torso_lower',[(0,116,-7.4),(5.1,112,-7.9),(4.2,105,-7.9),(0,99,-6.6),(-4.2,105,-7.9),(-5.1,112,-7.9)],2.4,0,6)
    # Neck bellows and the split lanceolate helmet from the approved drawing.
    m.capsule('neck',(0,154,0),(0,164,0),3.4,1)
    for y in np.linspace(156,163,9):m.ring('neck',(0,y,0),(0,1,0),3.25,.21,3,24)
    m.ellipsoid('head',(0,171,.4),(4.1,9.7,5.0),1,32,18)
    for s in (-1,1):
        mirrored_plate('head',s,[(.8,180),(3.2,181.6),(6.2,176),(6.0,170),(4.4,164),(1.1,156),(.5,158),(2.3,168),(2.5,175)],[-3,-.7,-1.3,-5.0,-7.2,-8.0,-9,-8.2,-5.5],thickness=2.2,rim=4)
        mirrored_plate('head',s,[(3,170),(5.0,168),(4.3,163),(1.1,156),(1.6,163)],-8.3,thickness=1.5,colour=3,rim=4)
        mechanical_joint('head',(s*4.7,170,.4),(s,0,0),2.05)
    m.loft('head',[(0,179,.5),(0,184,1.9),(0,193.1,3.0)],[1.75,1.0,.12],[2.9,1.45,.16],0,12)
    m.loft('head',[(0,180,-2.0),(0,185,.4),(0,192.6,2.78)],[.23,.16,.05],[.25,.16,.05],6,8)
    m.ellipsoid('head',(0,172,-5.4),(1.9,4.3,1.5),5,32,18)
    m.ring('head',(0,173,-6.82),(0,0,-1),1.12,.23,4,32)
    m.ellipsoid('head',(0,173,-7.1),(.82,.95,.22),7,32,18)
    plate('head',[(0,168.8,-7.8),(1.0,166.0,-8.4),(0,158,-8.2),(-1.0,166,-8.4)],.8,0,6)
    for side,s in [('l',-1),('r',1)]:
        shoulder=P['arm_'+side];elbow=np.array([s*23.489652,123.435069,7.737214]);wrist=P['hand_'+side]
        m.capsule('arm_'+side,shoulder,elbow,3.75,1)
        m.ellipsoid('forearm_'+side,elbow,(3.5,4.2,3.5),1)
        m.capsule('forearm_'+side,elbow,wrist,3.1,1)
        oriented_plate('arm_'+side,shoulder,elbow,[(-.65,.05),(.6,.02),(.98,.28),(.52,.73),(.03,.84),(-.62,.70),(-.92,.28)],4.2,3.1)
        oriented_plate('forearm_'+side,elbow,wrist,[(-.58,.16),(-.98,.0),(-1.03,.48),(-.64,.90),(.20,.98),(.75,.76),(.92,.20),(.45,.32),(.10,.18)],4.7,2.9)
        for t in np.linspace(.08,.30,6):m.ring('forearm_'+side,elbow*(1-t)+wrist*t,wrist-elbow,3.0,.22,3,20)
        mechanical_joint('forearm_'+side,elbow+[s*3.3,0,0],(s,0,0),2.7)
        # Oval shoulder housings and slim blade pylons (flat faced, not rounded pods).
        cx=s*24.3;bone='pylon_'+side
        m.loft(bone,[(cx,144,0),(cx,148,0),(cx,153,0),(cx,158,0),(cx,163,0)],[.8,3.6,4.8,3.9,1.6],[1.1,4.2,5.0,4.7,2.1],0,24)
        outline=[(cx+s*x,y,z) for x,y,z in [(-3.7,159,-4),(-1.8,164,-3),(2.1,163,-2),(4.6,157,-3),(4.1,150,-4),(1.4,143,-5),(-1.5,146,-5),(-3.8,151,-4)]]
        plate(bone,rounded_outline(outline,.23),8.1,0,4,curve=1.1)
        m.ellipsoid(bone,(cx,154,-4.4),(1.15,3.8,.4),5,24,14)
        m.ellipsoid(bone,(cx,154,-4.9),(.56,2.6,.12),4,20,10)
        mechanical_joint(bone,(s*28.6,154,.3),(s,0,0),4.2)
        # Three-dimensional narrow spine with a gold leading edge and open rear vents.
        mirrored_plate(bone,s,[(22.4,158),(22.7,179),(23.1,185.5),(24.5,186.7),(25.1,183),(27,158)],[-1,1,2.2,2.5,2.5,-1],thickness=4.5,colour=0,rim=6,curve=.14)
        for y in range(165,183,3):m.capsule(bone,(s*24.4,y,5.0),(s*25.4,y+1,5.0),.32,5,10)
        hip=P['leg_'+side];knee=P['shin_'+side]+[0,11.4,0];ankle=P['foot_'+side]
        m.capsule('leg_'+side,hip,knee,4.9,1);m.ellipsoid('shin_'+side,knee,(4.3,4.6,4.1),1)
        m.capsule('shin_'+side,knee,ankle,3.6,1)
        oriented_plate('leg_'+side,hip,knee,[(-.63,.04),(.4,.03),(.98,.19),(.89,.55),(.34,.91),(-.21,.97),(-.74,.75),(-.91,.28)],5.6,4.5)
        # Open knee mechanism, layered upper/shin armor and an extended narrow greave.
        mechanical_joint('shin_'+side,knee+[s*3.6,0,-.1],(s,0,0),3.15)
        kx=knee[0];ky=knee[1]
        plate('shin_'+side,[(kx-3.3,ky+4,-4.5),(kx,ky+7,-4.1),(kx+3.3,ky+4,-4.5),(kx+2.8,ky-1,-5.0),(kx,ky-3,-5.2),(kx-2.8,ky-1,-5.0)],1.4,0,4)
        oriented_plate('shin_'+side,knee,ankle,[(-.73,.11),(-1.05,-.03),(-1.0,.29),(-.51,.79),(-.3,.96),(.38,.98),(.62,.72),(.92,.19),(.66,.10),(.1,.17)],4.9,3.65)
        for t in (.12,.17,.22):m.ring('shin_'+side,knee*(1-t)+ankle*t,ankle-knee,3.35,.22,3,20)
        for t in (.84,.90,.96):m.ring('shin_'+side,knee*(1-t)+ankle*t,ankle-knee,2.9,.23,3,20)
        # Secondary inset panels and service fasteners on the sculpted armor.
        for bone,a,b,width,depth in [('leg_'+side,hip,knee,5.6,4.5),('shin_'+side,knee,ankle,4.9,3.65),('forearm_'+side,elbow,wrist,4.7,2.9)]:
            aa=np.array(a);bb=np.array(b);axis=(bb-aa)/np.linalg.norm(bb-aa);sidev=np.array([1.,0,0]);sidev-=axis*np.dot(sidev,axis);sidev/=np.linalg.norm(sidev);fv=np.cross(sidev,axis);fv*= -1 if fv[2]>0 else 1
            for sign in (-1,1):
                pts=[aa+(bb-aa)*t+sidev*sign*width*w+fv*(depth+.55) for t,w in [(.30,.72),(.48,.62),(.65,.42),(.77,.24)]]
                for a1,b1 in zip(pts,pts[1:]):m.capsule(bone,a1,b1,.105,3,8)
            for t in (.30,.44,.58,.70):
                q=aa+(bb-aa)*t+sidev*width*.63+fv*(depth+.68)
                m.ellipsoid(bone,q,(.20,.09,.20),4,12,6,fv)
        # Faceted boots with a grounded sole and a hinged instep.
        foot='foot_'+side;x=ankle[0]
        boot(foot,x)
        oriented_plate(foot,(x,3.5,-22),(x,9.5,5),[(-.67,.0),(.67,.0),(.97,.20),(.83,.61),(.60,.94),(-.6,.94),(-.83,.61),(-.97,.20)],4.7,0,colour=0)
        m.ellipsoid(foot,ankle,(3.2,4.1,3.1),1)
        mechanical_joint(foot,ankle+[s*3.3,0,0],(s,0,0),2.6)
        for dx in (-2.7,0,2.7):
            plate(foot,[(x+dx-1.1,1.9,-23.7),(x+dx+1.1,1.9,-23.7),(x+dx+.85,4.6,-20.5),(x+dx-.85,4.6,-20.5)],2.2,3,4)
        hand='hand_'+side;h=P[hand]
        m.ellipsoid(hand,h+[0,-1,0],(3.4,3.6,1.7),1,24,12)
        plate(hand,[h+[-3.1,2,-2],h+[2.9,2,-2],h+[3.1,-3,-2.5],h+[1.5,-4,-2.7],h+[-2.7,-3,-2.5]],1.0,0,4)
        for finger in ('index','middle','ring','little','thumb'):
            names=[n for n in [f'finger_{finger}_{side}',f'finger_{finger}_tip_{side}',f'finger_{finger}_distal_{side}'] if n in P]
            for i,bone in enumerate(names):
                a=P[bone];b=P[names[i+1]] if i+1<len(names) else a+[0,-2.1,0]
                m.capsule(bone,a,b,.68 if finger!='thumb' else .85,1,14)
                m.ellipsoid(bone,a,(.84,.78,.78),2,16,8)
                oriented_plate(bone,a,b,[(-.7,.12),(.7,.12),(.78,.66),(.35,.94),(-.35,.94),(-.78,.66)],.74,.56,colour=0)

if __name__=='__main__':
    body();m.save()
    path=m.A/'mesh/eva_prototype.mesh.json';data=json.loads(path.read_text(encoding='utf8'));data['source']='Original R08 silhouette-profiled, beveled black/gold test article; approved concept reference, shared public animation skeleton';path.write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
    report_path=m.OUT/'model_manifest.json';report=json.loads(report_path.read_text());report['geometry_sha256']=report['sha256'];report['mesh_resource_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();report['texture_sha256']=hashlib.sha256((m.A/'textures/entity/eva_prototype.png').read_bytes()).hexdigest();report_path.write_text(json.dumps(report,indent=2),encoding='utf8')
