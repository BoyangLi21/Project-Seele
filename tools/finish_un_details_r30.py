"""Mechanical optics, conforming armour details, insignia and dorsal engine nozzles."""
from pathlib import Path
from collections import defaultdict
import argparse,json,math,copy,shutil
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
import build_original_eva_prototype_r07 as m
import build_original_eva_prototype_r08 as plates
import fit_un_dorsal_r21 as dorsal

ROOT=m.ROOT;OUT=ROOT/'artifacts/facility_r30/models';OLD=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele'
class Outlines(BasePen):
    def __init__(self,glyphs):super().__init__(glyphs);self.paths=[];self.path=[]
    def _moveTo(self,p):self.path=[np.array(p,float)]
    def _lineTo(self,p):self.path.append(np.array(p,float))
    def _qCurveToOne(self,c,p):
        a=self.path[-1].copy();c=np.array(c);p=np.array(p)
        for t in np.linspace(0,1,10)[1:]:self.path.append((1-t)**2*a+2*(1-t)*t*c+t*t*p)
    def _curveToOne(self,b,c,p):
        a=self.path[-1].copy();b,c,p=map(np.array,(b,c,p))
        for t in np.linspace(0,1,12)[1:]:self.path.append((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*p)
    def _closePath(self):
        if len(self.path)>2:self.paths.append(np.array(self.path))
        self.path=[]
    def _endPath(self):self._closePath()

def main(unit):
    folder=OUT/('un'+unit);dest=folder/'runtime/assets/projectseele';base=folder/'body_base'
    if not base.exists():
        for kind in ('mesh','geo'):(base/kind).mkdir(parents=True,exist_ok=True);shutil.copy2(dest/kind/('eva_prototype.'+kind+'.json'),base/kind/('eva_prototype.'+kind+'.json'))
    mesh=json.loads((base/'mesh/eva_prototype.mesh.json').read_text());geo=json.loads((base/'geo/eva_prototype.geo.json').read_text());bones=geo['minecraft:geometry'][0]['bones']
    m.B={b['name']:{**b,'parent':b.get('parent'),'bindRotationDegrees':b.get('rotation',[0,0,0])} for b in bones};m.P={n:np.array(b['pivot'])*[-1,1,1] for n,b in m.B.items()};m.BIND.clear();m.PARTS.clear();m.PREVIEW.clear()
    with np.load(folder/'surface.npz') as d:vertices=d['vertices'];faces=d['triangles'];valid=d['valid'];weights=d['weights'];names=d['bone_names'].tolist()
    if unit=='00':
        horn=vertices[(vertices[:,1]>190)&(np.abs(vertices[:,0])<8)];zcentre=float(np.median(horn[:,2]))
        def sharpen(q):
            q=q.copy();selected=(q[:,1]>184)&(np.abs(q[:,0])<8);t=np.clip((q[selected,1]-184)/(193.1-184),0,1);t=t*t*(3-2*t);factor=1-.97*t;q[selected,0]*=factor;q[selected,2]=zcentre+(q[selected,2]-zcentre)*factor;return q
        vertices=sharpen(vertices)
        for name in ('head','r21_join_head'):
            if name not in mesh['parts']:continue
            part=mesh['parts'][name];data=np.asarray(part['vertices']).reshape(-1,8);world=(data[:,:3]+part['pivot'])*[-1,1,1];changed=(world[:,1]>184)&(np.abs(world[:,0])<8);world=sharpen(world);data[:,:3]=world*[-1,1,1]-part['pivot'];tri=data[:,:3].reshape(-1,3,3);norm=-np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);norm/=np.maximum(1e-12,np.linalg.norm(norm,axis=1,keepdims=True));selected=np.repeat(changed.reshape(-1,3).any(1),3);data[selected,5:8]=np.repeat(norm,3,axis=0)[selected];part['vertices']=data.ravel().tolist()
    triangles=vertices[faces[valid]];influence=weights[faces[valid]].mean(1);grid=defaultdict(list)
    for i,q in enumerate(triangles):
        lo=np.floor(q[:,:2].min(0)/2).astype(int);hi=np.floor(q[:,:2].max(0)/2).astype(int)
        for x in range(lo[0],hi[0]+1):
            for y in range(lo[1],hi[1]+1):grid[x,y].append(i)
    cache={};fair_panels=[]
    def inside_polygon(point,poly):
        x,y=point;inside=False
        for a,b in zip(poly,np.roll(poly,-1,axis=0)):
            if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
        return inside
    def surface(x,y,bone=None,rear=False):
        key=(round(float(x),5),round(float(y),5),bone,rear)
        if key in cache:return cache[key]
        ids=np.array(grid.get((math.floor(x/2),math.floor(y/2)),[]),int)
        if not len(ids):cache[key]=None;return None
        q=triangles[ids];a=q[:,0,:2];b=q[:,1,:2]-a;c=q[:,2,:2]-a;den=b[:,0]*c[:,1]-b[:,1]*c[:,0];d=np.array([x,y])-a;safe=abs(den)>1e-9
        u=np.divide(d[:,0]*c[:,1]-d[:,1]*c[:,0],den,out=np.zeros(len(den)),where=safe);v=np.divide(b[:,0]*d[:,1]-b[:,1]*d[:,0],den,out=np.zeros(len(den)),where=safe);mask=safe&(u>=-1e-7)&(v>=-1e-7)&(u+v<=1+1e-7)
        if bone in names:mask&=influence[ids,names.index(bone)]>.12
        keep=np.flatnonzero(mask)
        if not len(keep):cache[key]=None;return None
        z=q[:,0,2]+u*(q[:,1,2]-q[:,0,2])+v*(q[:,2,2]-q[:,0,2]);i=keep[np.argmax(z[keep]) if rear else np.argmin(z[keep])];n=np.cross(q[i,1]-q[i,0],q[i,2]-q[i,0]);n/=np.linalg.norm(n)
        if n[2]*(1 if rear else -1)<0:n=-n
        result=(np.array([x,y,z[i]]),n)
        if not rear:
            for owner,outline,evaluate in fair_panels:
                if (bone is None or bone==owner) and inside_polygon((x,y),outline):
                    p,normal=evaluate(np.array([x,y]))
                    if p[2]<result[0][2]:result=(p,normal)
        cache[key]=result;return result
    def facing_tri(bone,pts,colour,front=True):
        a,b,c=pts
        if np.cross(b-a,c-a)[2]*(1 if front else -1)>0:b,c=c,b
        m.triangle(bone,a,b,c,colour)
    def decal(bone,poly,colour,depth=.15,subdivide=1):
        poly=np.asarray(poly,float)
        def emit(a,b,c,left):
            if left:
                ab=(a+b)/2;bc=(b+c)/2;ca=(c+a)/2
                for t in ((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)):emit(*t,left-1)
            else:
                hits=[surface(*q,bone) for q in (a,b,c)]
                if all(q is not None for q in hits):facing_tri(bone,[p+n*depth for p,n in hits],colour)
        for i,j,k in plates.ears(poly):emit(poly[i],poly[j],poly[k],subdivide)
    def trim(bone,path,colour=4,width=.095,offset=.2):
        points=[]
        def flush():
            distinct=[]
            for point in points:
                if not distinct or np.linalg.norm(point-distinct[-1])>1e-5:distinct.append(point)
            if len(distinct)>1:m.loft(bone,distinct,[width]*len(distinct),[width]*len(distinct),colour,16)
            points.clear()
        for a,b in zip(path,path[1:]):
            a,b=np.array(a),np.array(b)
            for t in np.linspace(0,1,max(3,int(np.linalg.norm(b-a)*3))):
                hit=surface(*(a*(1-t)+b*t),bone)
                if hit is not None:points.append(hit[0]+hit[1]*offset)
                else:flush()
        flush()
    def armour_panel(bone,poly,colour,rim=None,offset=.26):
        """Fit a fair metal plate over the measured shell, not its scan ripples."""
        poly=np.asarray(poly,float);samples=[];patch=[]
        def split(a,b,c,left):
            if left:
                ab=(a+b)/2;bc=(b+c)/2;ca=(c+a)/2
                for q in ((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)):split(*q,left-1)
            else:
                hits=[surface(*q,bone) for q in (a,b,c)]
                if all(h is not None for h in hits):
                    patch.append((a,b,c));samples.extend(h[0] for h in hits)
        for i,j,k in plates.ears(poly):split(poly[i],poly[j],poly[k],4)
        if not samples:return
        samples=np.asarray(samples);centre=poly.mean(0);scale=np.maximum(np.ptp(poly,axis=0),1)
        def features(xy):
            xy=(np.asarray(xy)-centre)/scale;x,y=xy[...,0],xy[...,1]
            return np.stack([np.ones_like(x),x,y,x*x,x*y,y*y],axis=-1)
        fit=np.linalg.lstsq(features(samples[:,:2]),samples[:,2],rcond=None)[0]
        lift=max(0,float(np.max(features(samples[:,:2])@fit-samples[:,2])))+offset
        def point(xy):return np.r_[xy,float(features(xy)@fit-lift)]
        for q in patch:facing_tri(bone,[point(v) for v in q],colour)
        boundary={}
        for triangle in patch:
            for a,b in zip(triangle,(*triangle[1:],triangle[0])):
                key=tuple(sorted((tuple(np.round(a,7)),tuple(np.round(b,7)))))
                if key in boundary:boundary[key]=None
                else:boundary[key]=(point(a),point(b))
        # The bevel returns to the real shell, closing every raised edge.
        for edge in boundary.values():
            if edge is None:continue
            a,b=edge
            ha,hb=surface(*a[:2],bone),surface(*b[:2],bone)
            if ha is not None and hb is not None:
                facing_tri(bone,[a,b,hb[0]],colour);facing_tri(bone,[a,hb[0],ha[0]],colour)
            if rim is not None:m.loft(bone,[a,b],[.075,.075],[.075,.075],rim,16)
        def evaluate(xy):
            p=point(xy);dx=(point(xy+[.001,0])[2]-point(xy-[.001,0])[2])/.002;dy=(point(xy+[0,.001])[2]-point(xy-[0,.001])[2])/.002
            normal=np.array([dx,dy,-1]);normal/=np.linalg.norm(normal);return p,normal
        fair_panels.append((bone,poly,evaluate));cache.clear()
    def label(bone,text,x,y,height,colour):
        font=TTFont('C:/Windows/Fonts/arialbd.ttf');glyphs=font.getGlyphSet();cmap=font.getBestCmap();advance=0;contours=[]
        for letter in text:
            name=cmap[ord(letter)];pen=Outlines(glyphs);glyphs[name].draw(pen)
            contours.extend(p+np.array([advance,0]) for p in pen.paths);advance+=font['hmtx'][name][0]+65
        all_points=np.concatenate(contours);lo=all_points.min(0);h=all_points[:,1].max()-lo[1];scale=height/h
        for p in contours:decal(bone,np.c_[x-(p[:,0]-lo[0])*scale,y+(p[:,1]-lo[1])*scale],colour,.32,3)
    if unit=='00':
        for side,s in [('l',-1),('r',1)]:
            for poly in [[(1.8,155),(7,158),(17,160),(21,154),(13,150),(5,149)],[(2.5,145),(10,149),(18,146),(13,138),(4,137)]]:
                p=np.array(poly)*[s,1];armour_panel('torso_upper',p,0,4)
            px=m.P['pylon_'+side][0];trim('pylon_'+side,[(px,y) for y in (159,167,177,188)],4,.11,.18)
            for bone,levels in [('forearm',(112,126)),('leg',(83,105)),('shin',(31,51))]:
                x=m.P[bone+'_'+side][0]
                for delta in (-2.8,2.8):trim(bone+'_'+side,[(x+delta,y) for y in levels],4,.075,.16)
            for bone,path in [('forearm',[(28,133),(34,130),(37,122),(33,116),(29,124)]),('leg',[(14,113),(21,109),(25,100),(23,87),(19,79)]),('shin',[(20,66),(25,57),(29,48),(26,41),(23,52)])]:
                armour_panel(bone+'_'+side,np.array(path)*[s,1],0,4,.20)
            p=m.P['pylon_'+side];hit=surface(p[0],156)
            if hit is not None:
                c,n=hit;c=c+n*.40;m.ellipsoid('pylon_'+side,c,(2.5,.12,2.5),5,64,20,n);m.ring('pylon_'+side,c+n*.12,n,2.65,.22,4,96);m.ring('pylon_'+side,c+n*.17,n,2.10,.09,2,80)
            trim('head',np.array([(0.6,167),(2.8,163),(5.5,171.2),(3.1,178),(0,180)])*[s,1],4,.11,.20)
        trim('head',[(0,181),(0,187),(0,191)],4,.13,.16)
        label('torso_upper','UN',-9.0,155.5,3.3,9)
    else:
        for radius,colour,offset in [(6.2,9,.22),(5.72,8,.32)]:
            decal('torso_upper',[(math.sin(i*math.pi/5)*radius*(1 if i%2==0 else .40),154.4+math.cos(i*math.pi/5)*radius*(1 if i%2==0 else .40)) for i in range(10)],colour,offset,3)
        label('torso_upper','UN',19,156,4.0,9)
        for side,s in [('l',-1),('r',1)]:
            for path in [[(3,159),(11,162),(20,160),(24,155)],[(4,147),(12,145),(20,148)]]:trim('torso_upper',np.array(path)*[s,1],1,.10,.14)
    # Surface-mounted flush fasteners and inspection seams are real geometry.
    for bone,ys,xs in [('torso_upper',(141,158),(-14,14)),('torso_lower',(110,126),(-8,8))]:
        for y in ys:
            for x in xs:
                hit=surface(x,y,bone)
                if hit is not None:
                    p,n=hit;m.ring(bone,p+n*.16,n,.32,.065,4 if unit=='00' else 3,32);m.ellipsoid(bone,p+n*.16,(.23,.075,.23),5,24,12,n)
    cy=174.4 if unit=='00' else 181.0
    if unit=='00':
        outline=np.array([(2.4*math.cos(t),cy+2.4*math.sin(t)) for t in np.linspace(0,2*math.pi,96,endpoint=False)])
    else:outline=np.array([[-6.0,cy+.4],[-4.8,cy+1.6],[4.8,cy+1.6],[6.,cy+.4],[5.2,cy-1.3],[-5.2,cy-1.3]])
    perimeter=[surface(x,y,'head') for x,y in outline];perimeter=[h for h in perimeter if h is not None];assert perimeter
    depth=min(p[2] for p,n in perimeter)-.18;centre=np.array([0.,cy,depth]);normal=np.array([0.,0.,-1.])
    if unit=='00':
        for radius,tube,colour in [(2.05,.30,5),(1.82,.15,4),(1.40,.09,2),(.98,.055,4)]:m.ring('head',centre+normal*.25,normal,radius,tube,colour,96)
        m.ellipsoid('head',centre+normal*.26,(1.28,.25,1.28),10,96,32,normal);m.ellipsoid('head',centre+normal*.51,(.47,.04,.47),5,64,24,normal)
        m.ring('head',centre+normal*.47,normal,1.08,.045,7,96);m.ring('head',centre+normal*.53,normal,.57,.045,6,80);lens=centre+normal*.58
    else:
        middle=surface(0,cy,'head');assert middle is not None;centre=middle[0]+normal*.40
        inner=(outline-[0,cy])*[.85,.62]+[0,cy]
        decal('head',outline,5,.24,4);decal('head',inner,7,.36,4)
        # Dense curved patches follow the convex forehead. A flat visor plane
        # fitted only to the perimeter was buried behind its centre bulge.
        trim('head',[(-4.7,cy+1.6),(0,cy+1.75),(4.7,cy+1.6)],0,.16,.32)
        trim('head',[(0,cy-.8),(0,cy+.95)],5,.075,.46);lens=middle[0]+normal*.56
        mask=[(-3.5,178),(3.5,178),(5.0,174),(3,167),(0,165),(-3,167),(-5,174)];armour_panel('head',mask,10,1,.32)
        for sign in (-1,1):trim('head',np.array([(3.8,176),(5,171),(2.2,167)])*[sign,1],1,.18,.27)
        decal('head',[(-1.1,171),(1.1,171),(1.7,173.8),(.7,176),(-.7,176),(-1.7,173.8)],1,.32,3)
    # The skirt follows the measured helmet, then meets the optical housing.
    if unit=='00':
        rings=[]
        for radius in (3.0,2.5,2.1):
            row=[]
            for t in np.linspace(0,2*math.pi,96,endpoint=False):
                x,y=radius*math.cos(t),cy+radius*math.sin(t);h=surface(x,y,'head');z=h[0][2]-.07 if h else depth+.3;mix=max(0,min(1,(3-radius)/.9));row.append(np.array([x,y,z*(1-mix)+depth*mix]))
            rings.append(row)
        for aa,bb in zip(rings,rings[1:]):
            for i in range(96):j=(i+1)%96;facing_tri('head',[aa[i],aa[j],bb[j]],0);facing_tri('head',[aa[i],bb[j],bb[i]],0)
    mesh['eye_socket_model']=lens.tolist();mesh['r30_optical_frame']={'centre':centre.tolist(),'axis':normal.tolist(),'lens':lens.tolist(),'type':'coaxial circular optical assembly' if unit=='00' else 'horizontal amber forehead visor'}
    thrusters=[]
    if unit=='01':
        for side,s in [('l',-1),('r',1)]:
            jet_y=145.5
            rim=[surface(s*12.1+radius*math.cos(t),jet_y+radius*math.sin(t),None,True) for radius in (3.5,4.5,5.0) for t in np.linspace(0,2*math.pi,48,endpoint=False)];rim=[q for q in rim if q is not None];assert rim;centre=np.array([s*12.1,jet_y,max(p[2] for p,n in rim)+.25]);normal=np.array([0.,0.,1.]);bone='r30_thruster_'+side
            b={'name':bone,'parent':'torso_upper','pivot':(centre*[-1,1,1]).tolist()};bones.append(b);m.B[bone]={**b,'bindRotationDegrees':[0,0,0]};m.P[bone]=centre
            m.ring('torso_upper',centre,normal,5.0,.55,3,96);m.ring('torso_upper',centre+normal*.4,normal,4.25,.18,5,96)
            for length,radius,colour in [(-.5,4.0,3),(1.3,3.8,3),(3.0,3.65,2),(5.0,3.4,3),(6.0,3.25,5)]:m.ring(bone,centre+normal*length,normal,radius,.24,colour,80)
            # Individual overlapping petals leave the exhaust genuinely open.
            for angle in np.linspace(0,2*math.pi,28,endpoint=False):
                radial=np.array([math.cos(angle),math.sin(angle),0]);tangent=np.array([-math.sin(angle),math.cos(angle),0]);a=centre+radial*3.8+normal*1.2;b=centre+radial*3.25+normal*6
                m.triangle(bone,a-tangent*.39,a+tangent*.39,b+tangent*.30,3);m.triangle(bone,a-tangent*.39,b+tangent*.30,b-tangent*.30,3)
            m.ellipsoid(bone,centre+normal*3.0,(2.8,.20,2.8),5,80,20,normal);m.ring(bone,centre+normal*3.25,normal,2.1,.23,11,80);m.ellipsoid(bone,centre+normal*3.3,(1.0,.12,1.0),11,64,24,normal)
            thrusters.append({'bone':bone,'pivot_model':centre.tolist(),'nozzle_local':[0,0,6.25],'axis_model':[0,0,1],'gimbal_degrees_hover':65,'gimbal_degrees_cruise':15})
    for name,values in m.PARTS.items():
        a=np.asarray(values).reshape(-1,8);a[:,3]=.9375+a[:,3]*.0625;a[:,4]*=2/3;part=mesh['parts'].setdefault(name,{'pivot':m.B[name]['pivot'],'vertices':[]});before=len(part['vertices'])//8;part['vertices']+=np.round(a,6).ravel().tolist()
        if name in mesh['jointSkins']:
            skin=mesh['jointSkins'][name];skin['influences'].setdefault(name,[0.]*before)
            for key,values in skin['influences'].items():values.extend([float(key==name)]*len(a))
    mesh['r30_thrusters']=thrusters;mesh['triangleCount']=sum(len(p['vertices'])//24 for p in mesh['parts'].values());geo['minecraft:geometry'][0]['bones']=bones
    # Procedural rings and phalanges carry smooth surface normals rather than
    # flat normals copied separately into every triangle's three corners.
    for name,part in mesh['parts'].items():
        values=np.asarray(part['vertices']).reshape(-1,8);assert np.isfinite(values).all(),('Nonfinite generated geometry',name);_,inverse=np.unique(np.round(values[:,:3],5),axis=0,return_inverse=True);total=np.zeros((int(inverse.max())+1,3));np.add.at(total,inverse,values[:,5:8]);length=np.linalg.norm(total,axis=1);good=length[inverse]>1e-8;values[good,5:8]=total[inverse[good]]/length[inverse[good],None];part['vertices']=np.round(values,6).ravel().tolist()
    pre=folder/'finished_pre_dorsal'
    for kind,data in [('mesh',mesh),('geo',geo)]:
        (pre/kind).mkdir(parents=True,exist_ok=True);(pre/kind/('eva_prototype.'+kind+'.json')).write_text(json.dumps(data,separators=(',',':')))
    oldname='eva_prototype' if unit=='00' else 'eva_un01';frame=json.loads((OLD/'mesh'/(oldname+'.mesh.json')).read_text())['r13_dorsal_socket'];dorsal.fit(pre,dest,frame,folder/'dorsal_fit.json',unit)
    from normalize_un_mesh_r30 import normalize
    path=dest/'mesh/eva_prototype.mesh.json';final=json.loads(path.read_text());removed,repaired=normalize(final);path.write_text(json.dumps(final,separators=(',',':')))
    (folder/'mechanical_finish.json').write_text(json.dumps({'unit':unit,'triangle_count':final['triangleCount'],'degenerate_faces_removed':removed,'zero_normals_repaired':repaired,'optics':final['r30_optical_frame'],'thrusters':thrusters,'lettering':'Surface-conforming outline polygons, UN; no CCCP','mark':'Five-point star retained on UN-01','dorsal':final['r13_dorsal_socket']},indent=2));print(unit,'finished',final['triangleCount'],'triangles',flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',choices=('00','01'),required=True);main(ap.parse_args().unit)
