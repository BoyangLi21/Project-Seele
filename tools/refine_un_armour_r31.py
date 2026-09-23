"""Preserve the delivered rigs and add fitted, closed hard-surface armour as an isolated candidate."""
from pathlib import Path
from collections import defaultdict
import argparse,copy,hashlib,json,math,shutil
import numpy as np
from fontTools.ttLib import TTFont
import build_original_eva_prototype_r07 as m
import build_original_eva_prototype_r08 as plates
from finish_un_details_r30 import Outlines

ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele';OUT=ROOT/'artifacts/facility_r31/models'

def main(unit):
    name='eva_prototype' if unit=='00' else 'eva_un01';folder=OUT/('un'+unit);dest=folder/'runtime/assets/projectseele';baseline=folder/'baseline/assets/projectseele'
    for category,extension in [('mesh','.mesh.json'),('geo','.geo.json'),('animations','.animation.json')]:
        for target in (dest,baseline):
            (target/category).mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE/category/(name+extension),target/category/('eva_prototype'+extension))
    for target in (dest,baseline):
        (target/'textures/entity').mkdir(parents=True,exist_ok=True)
        for suffix in ('','_mr','_s','_n','_eyes'):shutil.copy2(SOURCE/'textures/entity'/(name+suffix+'.png'),target/'textures/entity'/('eva_prototype'+suffix+'.png'))
    # Ownership must be fixed before any new armour is attached. Otherwise
    # the visible thigh front is still in the pelvis's source surface pool.
    from repair_un_ownership_r31 import main as repair_ownership
    repair_ownership(unit)
    mesh_path=dest/'mesh/eva_prototype.mesh.json';mesh=json.loads(mesh_path.read_text());geo=json.loads((dest/'geo/eva_prototype.geo.json').read_text());bones=geo['minecraft:geometry'][0]['bones'];before=copy.deepcopy({key:value for key,value in mesh.items() if key!='parts' and key!='jointSkins'})
    m.B={b['name']:{**b,'parent':b.get('parent'),'bindRotationDegrees':b.get('rotation',[0,0,0])} for b in bones};m.P={n:np.array(b['pivot'])*[-1,1,1] for n,b in m.B.items()};m.BIND.clear();m.PARTS.clear();m.PREVIEW.clear()
    palette=json.loads((ROOT/'artifacts/facility_r30/models'/('un'+unit)/'palette.json').read_text());(folder/'palette.json').write_text(json.dumps(palette));m.COLOURS=palette
    # Re-author one clean UN stencil; leaving the larger R30 letters underneath
    # a smaller replacement makes their exposed fragments look like z-fighting.
    part=mesh['parts']['torso_upper'];rows=np.asarray(part['vertices']).reshape(-1,3,8);centres=((rows[:,:,:3]+part['pivot'])*[-1,1,1]).mean(1)
    u=rows[:,:,3].mean(1);v=rows[:,:,4].mean(1);cell=np.floor((u-.9375)/.0625*4)+4*np.floor(v*3)
    logo=(rows[:,:,3].min(1)>=.93749)&(cell==9)&(abs(centres[:,0])>6.5)&(centres[:,1]>152)&(centres[:,1]<162.5)&(centres[:,2]<0)
    keep=~logo;part['vertices']=rows[keep].ravel().tolist()
    if 'torso_upper' in mesh.get('jointSkins',{}):
        skin=mesh['jointSkins']['torso_upper'];skin['influences']={n:np.asarray(w)[np.repeat(keep,3)].tolist() for n,w in skin['influences'].items()}
    original={};grids={};surface_pools={};cache={};patches=[];hardware=[]
    for bone,part in mesh['parts'].items():
        a=np.asarray(part['vertices']).reshape(-1,8);v=(a[:,:3]+part['pivot'])*[-1,1,1];v=(np.c_[v,np.ones(len(v))]@m.bind(bone).T)[:,:3];original[bone]=v.reshape(-1,3,3)
    def indexed(bone):
        if bone not in grids:
            pool=[original[bone]]
            for part,skin in mesh.get('jointSkins',{}).items():
                if part==bone or bone not in skin['influences']:continue
                mask=np.asarray(skin['influences'][bone]).reshape(-1,3).mean(1)>.15
                if mask.any():pool.append(original[part][mask])
            surface_pools[bone]=np.concatenate(pool)
            grid=defaultdict(list)
            for i,q in enumerate(surface_pools[bone]):
                lo=np.floor(q[:,:2].min(0)/2).astype(int);hi=np.floor(q[:,:2].max(0)/2).astype(int)
                for x in range(lo[0],hi[0]+1):
                    for y in range(lo[1],hi[1]+1):grid[x,y].append(i)
            grids[bone]=grid
        return grids[bone]
    def surface(x,y,bone,rear=False):
        key=(round(float(x),4),round(float(y),4),bone,rear)
        if key in cache:return cache[key]
        ids=indexed(bone).get((math.floor(x/2),math.floor(y/2)),[])
        if not ids:return None
        q=surface_pools[bone][ids];a=q[:,0,:2];b=q[:,1,:2]-a;c=q[:,2,:2]-a;d=[x,y]-a;den=b[:,0]*c[:,1]-b[:,1]*c[:,0];safe=abs(den)>1e-9
        u=np.divide(d[:,0]*c[:,1]-d[:,1]*c[:,0],den,out=np.zeros(len(q)),where=safe);v=np.divide(b[:,0]*d[:,1]-b[:,1]*d[:,0],den,out=np.zeros(len(q)),where=safe)
        valid=safe&(u>=-1e-7)&(v>=-1e-7)&(u+v<=1+1e-7);keep=np.flatnonzero(valid)
        if not len(keep):return None
        z=q[:,0,2]+u*(q[:,1,2]-q[:,0,2])+v*(q[:,2,2]-q[:,0,2]);i=keep[np.argmax(z[keep]) if rear else np.argmin(z[keep])]
        normal=np.cross(q[i,1]-q[i,0],q[i,2]-q[i,0]);normal/=np.linalg.norm(normal)
        if normal[2]*(1 if rear else -1)<0:normal=-normal
        result=(np.array([x,y,z[i]]),normal);cache[key]=result;return result
    def inside(xy,poly):
        xy=np.asarray(xy);answer=np.zeros(xy.shape[:-1],bool)
        for a,b in zip(poly,np.roll(poly,-1,axis=0)):
            cross=((a[1]>xy[...,1])!=(b[1]>xy[...,1]))&(xy[...,0]<(b[0]-a[0])*(xy[...,1]-a[1])/(b[1]-a[1]+1e-30)+a[0]);answer^=cross
        return answer
    def face(bone,a,b,c,colour,rear=False):
        if np.cross(b-a,c-a)[2]*(1 if rear else -1)<0:b,c=c,b
        m.triangle(bone,a,b,c,colour)
    def panel(bone,outline,colour=0,rear=False,bevel=.045,offset=.45,fasteners=True):
        poly=np.asarray(outline,float);centre=poly.mean(0);sign=1 if rear else -1
        # Every perimeter sample must sit on the original shell. A fit based
        # only on interior rays can extrapolate into a large floating spike.
        for attempt in range(12):
            perimeter=[a*(1-t)+b*t for a,b in zip(poly,np.roll(poly,-1,axis=0)) for t in np.linspace(0,1,9)]
            if all(surface(*q,bone,rear) is not None for q in perimeter):break
            poly=centre+(poly-centre)*.91
        else:return None
        if np.prod(np.ptp(poly,axis=0))<2:return None
        samples=[]
        def evaluate(xy,push=0):
            hit=surface(*xy,bone,rear)
            if hit is None:
                for fraction in (.98,.94,.86,.70):
                    hit=surface(*(centre+(np.asarray(xy)-centre)*fraction),bone,rear)
                    if hit is not None:break
            if hit is None:raise ValueError(('Panel has no supporting shell',bone,xy))
            return np.r_[xy,hit[0][2]+sign*(offset+push)]
        # Deliberate sheet thickness and a separate bevel close the panel's
        # edges. A panel never straddles an articulated skeleton joint.
        rim=np.array([evaluate(p) for p in poly]);inner=np.array([evaluate(centre+(p-centre)*(1-bevel),.28) for p in poly]);back=rim.copy();back[:,2]-=sign*.9
        rimcolour=4 if unit=='00' else 3
        for i in range(len(poly)):
            j=(i+1)%len(poly)
            face(bone,rim[i],rim[j],inner[j],rimcolour,rear);face(bone,rim[i],inner[j],inner[i],rimcolour,rear)
            face(bone,back[i],back[j],rim[j],colour,rear);face(bone,back[i],rim[j],rim[i],colour,rear)
        inner_poly=np.array([p[:2] for p in inner]);front_faces=[]
        for i,j,k in plates.ears(inner_poly):
            # Four subdivisions retain fitted curvature while normals remain
            # clean within the ceramic face; they do not copy source ripples.
            def emit(a,b,c,left):
                if left:
                    ab=(a+b)/2;bc=(b+c)/2;ca=(c+a)/2
                    for tri in ((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)):emit(*tri,left-1)
                else:
                    tri=[evaluate(a,.28),evaluate(b,.28),evaluate(c,.28)];front_faces.append(tri);face(bone,*tri,colour,rear)
            emit(inner_poly[i],inner_poly[j],inner_poly[k],2)
        for i,j,k in plates.ears(poly):face(bone,back[k],back[j],back[i],3,rear)
        if fasteners:
            for i in range(0,len(poly),max(1,len(poly)//4)):
                xy=centre+(poly[i]-centre)*.77;point=evaluate(xy,.38);normal=np.array([0.,0.,sign])
                m.ring(bone,point,normal,.28,.075,rimcolour,20);m.ellipsoid(bone,point+normal*.03,(.16,.065,.16),5,12,6,normal)
        patches.append(dict(bone=bone,outline=poly.tolist(),rear=rear,thickness=.9,bevel=bevel,perimeterChecked=True,maxLift=offset+.28))
        evaluate.outline=poly
        evaluate.front_faces=np.asarray(front_faces)
        return evaluate
    def louver(bone,x,y,width,height,rear=False):
        poly=np.array([[x-width/2,y-height/2],[x+width/2,y-height/2],[x+width/2,y+height/2],[x-width/2,y+height/2]])
        evaluate=panel(bone,poly,5,rear,.10,.50,False)
        if evaluate is None:return
        outline=evaluate.outline;x,y=outline.mean(0);width,height=np.ptp(outline,axis=0)
        sign=1 if rear else -1
        for yy in np.linspace(y-height*.37,y+height*.37,6):
            a=evaluate([x-width*.38,yy],.38);b=evaluate([x+width*.38,yy],.38);shift=np.array([0,.34,sign*.28])
            face(bone,a,b,b+shift,3 if unit=='01' else 2,rear);face(bone,a,b+shift,a+shift,3 if unit=='01' else 2,rear)
        hardware.append(dict(kind='louver',bone=bone,centre=[x,y],rear=rear))
    def seam(bone,path,colour=None,rear=False):
        points=[]
        for a,b in zip(path,path[1:]):
            for t in np.linspace(0,1,8):
                h=surface(*(np.array(a)*(1-t)+np.array(b)*t),bone,rear)
                if h is not None:
                    p=h[0]+h[1]*.18
                    if not points or np.linalg.norm(p-points[-1])>1e-5:points.append(p)
        if len(points)>1:m.loft(bone,points,[.105]*len(points),[.105]*len(points),5 if colour is None else colour,8)
    def label(bone,text,x,y,height,evaluate):
        font=TTFont('C:/Windows/Fonts/arialbd.ttf');glyphs=font.getGlyphSet();cmap=font.getBestCmap();offset=0;paths=[]
        for letter in text:
            n=cmap[ord(letter)];pen=Outlines(glyphs);glyphs[n].draw(pen);paths.extend(p+[offset,0] for p in pen.paths);offset+=font['hmtx'][n][0]+65
        allpts=np.concatenate(paths);low=allpts.min(0);scale=height/(allpts[:,1].max()-low[1])
        def point(xy):
            q=evaluate.front_faces;a=q[:,0,:2];b=q[:,1,:2]-a;c=q[:,2,:2]-a;d=xy-a;den=b[:,0]*c[:,1]-b[:,1]*c[:,0];safe=abs(den)>1e-9
            u=np.divide(d[:,0]*c[:,1]-d[:,1]*c[:,0],den,out=np.zeros(len(q)),where=safe);v=np.divide(b[:,0]*d[:,1]-b[:,1]*d[:,0],den,out=np.zeros(len(q)),where=safe);good=safe&(u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6)
            if not good.any():return evaluate(xy,.85)
            z=q[:,0,2]+u*(q[:,1,2]-q[:,0,2])+v*(q[:,2,2]-q[:,0,2]);return np.r_[xy,z[good].min()-.12]
        for poly in paths:
            p=np.c_[x-(poly[:,0]-low[0])*scale,y+(poly[:,1]-low[1])*scale]
            for i,j,k in plates.ears(p):
                def emit(a,b,c,level):
                    if level:
                        ab=(a+b)/2;bc=(b+c)/2;ca=(c+a)/2
                        for tri in ((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)):emit(*tri,level-1)
                    else:face(bone,point(a),point(b),point(c),9)
                emit(p[i],p[j],p[k],3)
    for side,sign in [('l',-1),('r',1)]:
        mirror=lambda q:np.asarray(q)*[sign,1]
        if unit=='00':
            upper=panel('torso_upper',mirror([(2.2,156),(9,160),(18,160),(22,154),(17,149),(6,149)]),0,bevel=.028)
            panel('torso_upper',mirror([(3.7,145.2),(11,149),(18,144),(13,136.5),(5.3,136)]),0,bevel=.024)
            panel('forearm_'+side,mirror([(27.0,130),(31,132),(35.4,124),(34.8,112),(31.8,109),(29,120)]),0,bevel=.035)
            panel('leg_'+side,mirror([(11.5,112),(17.5,114),(22,106),(22,87),(17,79),(13,90)]),0,bevel=.025)
            panel('shin_'+side,mirror([(18.3,60),(23.5,57),(27.4,43),(28.1,27),(24.3,24),(22.2,43)]),0,bevel=.035)
            louver('torso_upper',sign*12,144,4,7,True)
            seam('torso_lower',mirror([(3,125),(7,119),(5,109)]),4)
        else:
            upper=panel('torso_upper',mirror([(7.3,159),(11,162.5),(19,162),(22.5,157.5),(20.5,152),(11,150.5),(7.5,152)]),0,bevel=.035)
            panel('torso_upper',mirror([(4,145.5),(12,148),(18,144),(15,139.5),(6,139)]),0,bevel=.035)
            panel('forearm_'+side,mirror([(34.5,124),(38.0,128),(42,121),(46,106),(42.4,104),(37,114)]),0,bevel=.045)
            panel('leg_'+side,mirror([(15.2,108),(23.5,110),(28,100),(28,86),(23,77),(18,85),(15.2,101)]),0,bevel=.03)
            panel('shin_'+side,mirror([(22.8,59),(28,56),(34,42),(37,25),(32,21),(28,39)]),0,bevel=.04)
            louver('torso_upper',sign*13,134.5,4.8,5.5,True)
            seam('torso_lower',mirror([(3,128),(10,124),(13,117)]),5)
        if side=='r' and upper is not None:label('torso_upper','UN',17 if unit=='00' else 19,154.5 if unit=='00' else 156,2.65,upper)
        for level in (166,180):
            x=abs(float(m.P['pylon_'+side][0]));x=max(18,min(25,x));panel('pylon_'+side,mirror([(x-1.9,level),(x+1.9,level+.5),(x+1.6,level+9),(x-1.5,level+9.4)]),0,bevel=.065,fasteners=False)
        forearm=original['forearm_'+side].reshape(-1,3);y=119 if unit=='00' else 114;band=forearm[(abs(forearm[:,1]-y)<2)]
        if len(band):louver('forearm_'+side,float(np.median(band[:,0])),y,3.0,5.4)
        # Measured elbow/knee protective caps stay on the existing hinge bone.
        for lower,marker,radius in [('forearm_','r30_elbow_socket_',2.4),('shin_','r30_knee_socket_',2.65)]:
            bone=lower+side;centre=m.P.get(marker+side)
            if centre is None:continue
            indexed(bone);q=surface_pools[bone];a=q[:,0,1:3];b=q[:,1,1:3]-a;c=q[:,2,1:3]-a;d=centre[1:3]-a;den=b[:,0]*c[:,1]-b[:,1]*c[:,0];valid=abs(den)>1e-9
            u=np.divide(d[:,0]*c[:,1]-d[:,1]*c[:,0],den,out=np.zeros(len(q)),where=valid);v=np.divide(b[:,0]*d[:,1]-b[:,1]*d[:,0],den,out=np.zeros(len(q)),where=valid);valid&=(u>=-1e-6)&(v>=-1e-6)&(u+v<=1.000001)
            if not valid.any():continue
            xx=q[:,0,0]+u*(q[:,1,0]-q[:,0,0])+v*(q[:,2,0]-q[:,0,0]);x=float(xx[valid].min() if sign<0 else xx[valid].max());point=np.array([x+sign*.08,centre[1],centre[2]]);axis=np.array([sign,0,0.])
            m.ellipsoid(bone,point,(radius,.18,radius),5,32,10,axis);m.ring(bone,point+axis*.10,axis,radius,.22,4 if unit=='00' else 3,32);m.ring(bone,point+axis*.22,axis,radius*.64,.12,2 if unit=='00' else 4,28)
            hardware.append(dict(kind='hinge_cap',bone=bone,centre=point.tolist(),radius=radius))
        # Dorsal knuckle plate: additions follow the existing hand, not the forearm.
        h=m.P['hand_'+side];panel('hand_'+side,[(h[0]-3.4,94.0),(h[0]+3.4,94.0),(h[0]+3.1,99.5),(h[0]-3.1,99.5)],0 if unit=='00' else 2,True,.08,.2)
        for digit in ('index','middle','ring','little'):
            for joint in ('','_tip','_distal'):
                bone='finger_'+digit+joint+'_'+side
                if bone not in m.P:continue
                point=m.P[bone];axis=m.bind(bone)[:3,:3]@np.array([0.,0.,1.]);m.ring(bone,point+axis*.80,axis,.47,.095,4 if unit=='00' else 3,16)
                hardware.append(dict(kind='finger_hinge',bone=bone))
    # The R30 helmet optic and its fitted edges stay untouched. A projected
    # extra line can bridge a front/rear ray discontinuity beside the neck.
    generated=0
    for bone,values in m.PARTS.items():
        a=np.asarray(values).reshape(-1,8);a[:,3]=.9375+a[:,3]*.0625;a[:,4]*=2/3
        # Palette interiors prevent atlas bake-margin contamination on tiny hardware.
        tri=a.reshape(-1,3,8);u=tri[:,:,3].mean(1);v=tri[:,:,4].mean(1);col=np.clip(np.floor((u-.9375)/.0625*4),0,3);row=np.clip(np.floor(v*3),0,2)
        tri[:,:,3]=(.9375+(col+.5)*.0625/4)[:,None]+np.array([-2,2,-2])[None,:]/4096;tri[:,:,4]=((row+.5)/3)[:,None]+np.array([-2,-2,2])[None,:]/4096
        # Smooth the ceramic face and round bearing surfaces consistently.
        _,inverse=np.unique(np.round(a[:,:3],5),axis=0,return_inverse=True);total=np.zeros((int(inverse.max())+1,3));np.add.at(total,inverse,a[:,5:8]);length=np.linalg.norm(total,axis=1);good=length[inverse]>1e-8;a[good,5:8]=total[inverse[good]]/length[inverse[good],None]
        a[:,5:8]/=np.linalg.norm(a[:,5:8],axis=1,keepdims=True)
        part=mesh['parts'][bone];old=len(part['vertices'])//8;part['vertices']+=np.round(a,6).ravel().tolist();generated+=len(a)//3
        if bone in mesh.get('jointSkins',{}):
            skin=mesh['jointSkins'][bone];skin['influences'].setdefault(bone,[0.]*old)
            for key,w in skin['influences'].items():w.extend([float(key==bone)]*len(a))
    mesh['triangleCount']=sum(len(p['vertices'])//24 for p in mesh['parts'].values());mesh['r31_armour_finish']={'source':'local original fitted plate authoring','addedTriangles':generated,'closedPanels':len(patches),'rigRetained':True,'sourceSha256':hashlib.sha256((SOURCE/'mesh'/(name+'.mesh.json')).read_bytes()).hexdigest()}
    mesh_path.write_text(json.dumps(mesh,separators=(',',':')))
    report={'unit':unit,'baselineTriangles':before['triangleCount'],'candidateTriangles':mesh['triangleCount'],'addedTriangles':generated,'panels':patches,'hardware':hardware,'rigSha256':hashlib.sha256((dest/'geo/eva_prototype.geo.json').read_bytes()).hexdigest(),'dorsalPreserved':mesh['r13_dorsal_socket']==before['r13_dorsal_socket'],'handsPreserved':mesh['r30_hands']==before['r30_hands'],'eyePreserved':mesh['eye_socket_model']==before['eye_socket_model'],'untouchedSource':str(SOURCE)}
    (folder/'armour_revision.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:report[k] for k in ('unit','baselineTriangles','candidateTriangles','addedTriangles','dorsalPreserved','handsPreserved','eyePreserved')}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--unit',choices=('00','01'),required=True);main(parser.parse_args().unit)
