"""Stage original single-cover spinal hardware at the measured rear markings.

Third-party airframe surfaces stay in the private candidate resource pack.
The current game pack is only replaced by a separate reviewed installation.
"""
from pathlib import Path
import json,math
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/dorsal_tv_r13';CHECK=json.loads((OUT/'checkpoint.json').read_text(encoding='utf-8'));BACK=Path(CHECK['backup'])/'run/resourcepacks/eva_real_model/assets/projectseele';TARGET=OUT/'candidate/assets/projectseele';SPECS=json.loads((OUT/'measured_socket_frames.json').read_text());RADIUS=3.65

def split(poly,n,d):
    inner=[];outer=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=a[:3]@n-d;db=b[:3]@n-d;ina=da<=1e-7;inb=db<=1e-7
        (inner if ina else outer).append(a)
        if ina!=inb:
            v=a+(b-a)*(da/(da-db));inner.append(v);outer.append(v)
    return inner,outer

def fan(poly):
    return [np.array([poly[0],poly[i],poly[i+1]]) for i in range(1,len(poly)-1) if np.linalg.norm(np.cross(poly[i][:3]-poly[0][:3],poly[i+1][:3]-poly[0][:3]))>1e-7]

def partition(triangles,planes):
    inside=[];outside=[]
    for tri in triangles:
        distances=np.array([tri[:,:3]@n-d for n,d in planes])
        if (distances.min(1)>1e-7).any():outside.append(tri);continue
        if distances.max()<=1e-7:inside.append(tri);continue
        remaining=list(tri)
        for n,d in planes:
            if len(remaining)<3:break
            remaining,discarded=split(remaining,n,d);outside.extend(fan(discarded))
        if len(remaining)>=3:inside.extend(fan(remaining))
    return np.array(inside).reshape(-1,3,8),np.array(outside).reshape(-1,3,8)

def world(part):
    v=np.array(part['vertices']).reshape(-1,3,8);v[:,:,:3]+=part['pivot'];return v

def packed(v,pivot):
    values=np.array(v).reshape(-1,8).copy();values[:,:3]-=pivot;return dict(pivot=np.asarray(pivot).tolist(),vertices=np.round(values,6).ravel().tolist())

def main():
    manifest=[]
    for model,spec in SPECS.items():
        original=json.loads((ROOT/'artifacts/world_motion_r11/dorsal'/(model+'_uncut.mesh.json')).read_text());mesh=json.loads((BACK/'mesh'/(model+'.mesh.json')).read_text());geo=json.loads((BACK/'geo'/(model+'.geo.json')).read_text());parts=mesh['parts'];bones=geo['minecraft:geometry'][0]['bones'];bones[:]=[b for b in bones if not b['name'].startswith('dorsal_')]
        for name in list(parts):
            if name.startswith('dorsal_'):del parts[name]
        for name in ['torso_upper','neck']:
            if name in original['parts']:parts[name]=original['parts'][name]
        C=np.array(spec['mouth_centre_model']);C[0]=0;N=np.array(spec['outward_model']);N/=np.linalg.norm(N);X=np.array([1.,0,0]);Y=np.cross(N,X);half=spec['cover_half_width']
        if model!='eva_prototype':
            head=world(original['parts']['head']);body_ids=np.array(spec['head_triangles_reparent_to_torso']);nape_ids=np.array(spec['nape_component_faces']);nape=head[nape_ids]
            planes=[(X,half),(-X,half),(-np.array([0,1.,0]),-spec['cover_min_y']),(-np.array([0,0,1.]),-7.8),(-N,-N@C+3.4)]
            cover,remainder=partition(nape,planes);rest=head[np.setdiff1d(body_ids,nape_ids)];torso=np.concatenate([world(parts['torso_upper']),rest,remainder]);keep=np.ones(len(head),bool);keep[body_ids]=False;parts['head']=packed(head[keep],parts['head']['pivot'])
            # Keep the supplied silhouette and UVs; a modest width adjustment
            # leaves clearance for the existing pressure shell and metal lip.
            cover[:,:,0]*=1.50;cover[:,:,:3]+=N*1.3
            cover[:,:,5]/=1.50;cover[:,:,5:8]/=np.maximum(1e-8,np.linalg.norm(cover[:,:,5:8],axis=2,keepdims=True))
        else:
            torso=world(parts['torso_upper']);planes=[(X,half),(-X,half),(-np.array([0,1.,0]),-134.),(np.array([0,1.,0]),156.),(-np.array([0,0,1.]),-6.7)]
            cover,torso=partition(torso,planes)
            # Form a continuous pressure fairing between the UN service discs.
            # It conceals the oblique collar while preserving the existing
            # black/gold surface and fading back into the outer scapular edges.
            x=cover[:,:,0];y=cover[:,:,1]-143;bulge=6*np.exp(-(x/6.8)**4-(y/10.5)**4);dx=bulge*(-4*x**3/6.8**4);dy=bulge*(-4*y**3/10.5**4);cover[:,:,2]+=bulge;cover[:,:,5]-=dx*cover[:,:,7];cover[:,:,6]-=dy*cover[:,:,7];cover[:,:,5:8]/=np.maximum(1e-8,np.linalg.norm(cover[:,:,5:8],axis=2,keepdims=True))
        assert len(cover)>15,(model,len(cover))
        bore=[(X*math.cos(a)+Y*math.sin(a),(X*math.cos(a)+Y*math.sin(a))@C+RADIUS) for a in np.linspace(0,2*math.pi,48,endpoint=False)]+[(N,N@C+5),(-N,-N@C+36)]
        cut,torso=partition(torso,bore);parts['torso_upper']=packed(torso,parts['torso_upper']['pivot'])
        if 'torso_lower' in parts:
            _,lower=partition(world(parts['torso_lower']),bore);parts['torso_lower']=packed(lower,parts['torso_lower']['pivot'])
        depth=float(((cover[:,:,:3]-C)@N).min());hinge=C-X*(half*(1.50 if model!='eva_prototype' else 1)+.08)+Y*2+N*min(-4.,depth-.6)
        bones.extend([dict(name='dorsal_cover',parent='torso_upper',pivot=hinge.round(6).tolist()),dict(name='dorsal_liner',parent='torso_upper',pivot=C.round(6).tolist())])
        parts['dorsal_cover']=packed(cover,hinge);parts['dorsal_liner']=packed([],C)
        image=np.asarray(Image.open(BACK/'textures/entity'/(model+'.png')).convert('RGB'));targets={'steel':[135,143,148],'ivory':[190,190,165],'dark':[20,23,26],'red':[116,25,28],'gold':[164,134,58]};uv={}
        for name,colour in targets.items():
            y,x=np.unravel_index(np.sum((image.astype(float)-colour)**2,2).argmin(),image.shape[:2]);uv[name]=np.array([(x+.5)/image.shape[1],(y+.5)/image.shape[0]])
        def tri(a,b,c,material,bone='dorsal_liner'):
            normal=np.cross(b-a,c-a);length=np.linalg.norm(normal)
            if length<1e-8:return
            normal/=length;pivot=hinge if bone=='dorsal_cover' else C
            for p in [a,b,c]:parts[bone]['vertices'].extend([*(p-pivot),*uv[material],*normal])
        def quad(a,b,c,d,material,bone='dorsal_liner'):tri(a,b,c,material,bone);tri(a,c,d,material,bone)
        def tube(a,b,outer,inner,material,segments=48,bone='dorsal_liner'):
            direction=b-a;direction/=np.linalg.norm(direction);x=np.cross(direction,[1.,0,0] if abs(direction[0])<.9 else [0,1.,0]);x/=np.linalg.norm(x);y=np.cross(direction,x)
            for s,t in zip(np.linspace(0,2*math.pi,segments+1)[:-1],np.linspace(0,2*math.pi,segments+1)[1:]):
                r=x*math.cos(s)+y*math.sin(s);q=x*math.cos(t)+y*math.sin(t)
                quad(a+r*outer,a+q*outer,b+q*outer,b+r*outer,material,bone);quad(a+r*inner,a+q*inner,a+q*outer,a+r*outer,material,bone);quad(b+r*outer,b+q*outer,b+q*inner,b+r*inner,material,bone)
                if inner>0:quad(a+r*inner,b+r*inner,b+q*inner,a+q*inner,'dark',bone)
        # Dark open pressure tube, ivory spinal face, gasket and successive ribs.
        tube(C-N*35.5,C+N*.12,3.72,3.56,'dark',64)
        tube(C-N*.22,C+N*.32,4.35,3.57,'ivory',64)
        tube(C+N*.33,C+N*.43,3.85,3.57,'red',64)
        for depth in [2,5,9,14,20,27,34]:tube(C-N*(depth+.18),C-N*depth,3.64,3.49,'steel',48)
        # The plate and actuator share an actual hinge axis along the edge.
        for along in [-3.8,1.2,5.3]:
            p=hinge+Y*along;tube(p-Y*.65,p+Y*.65,.44,.16,'steel',24)
        # The cover's cut boundary receives thickness rather than an open paper edge.
        verts,inv=np.unique(np.round(cover[:,:,:3],5).reshape(-1,3),axis=0,return_inverse=True);faces=inv.reshape(-1,3);edge_counts={}
        for face in faces:
            for u,v in zip(face,np.roll(face,-1)):
                key=tuple(sorted((int(u),int(v))));edge_counts[key]=edge_counts.get(key,0)+1
        for (u,v),count in edge_counts.items():
            if count==1:
                p,q=verts[u],verts[v];quad(p,q,q-N*.55,p-N*.55,'dark','dorsal_cover')
        # A dark backing seals the moving cover while preserving its outside UVs.
        for triangle in cover:
            a,b,c=triangle[:,:3]-N*.55;tri(c,b,a,'dark','dorsal_cover')
        # A continuous pressure seal on the underside covers small gaps in
        # the source panel's low-resolution outline. It moves with the lid.
        centre=C-N*.24
        for angle,next_angle in zip(np.linspace(0,2*math.pi,65)[:-1],np.linspace(0,2*math.pi,65)[1:]):
            p=centre+(X*math.cos(angle)+Y*math.sin(angle))*3.74;q=centre+(X*math.cos(next_angle)+Y*math.sin(next_angle))*3.74
            tri(centre,p,q,'dark','dorsal_cover');tri(centre-N*.24,q-N*.24,p-N*.24,'dark','dorsal_cover');quad(p,p-N*.24,q-N*.24,q,'steel','dorsal_cover')
        mesh.pop('r11_dorsal_socket',None);mesh['r13_dorsal_socket']=dict(centre=C.round(6).tolist(),outward=N.round(8).tolist(),hinge=hinge.round(6).tolist(),hinge_axis=Y.round(8).tolist(),open_angle_degrees=-105,radius_model=RADIUS,source_markers=spec['mark_centres'],reparented_head_triangles=len(spec.get('head_triangles_reparent_to_torso',[])),bore_triangles_removed=len(cut))
        mesh['triangleCount']=sum(len(p['vertices'])//24 for p in parts.values())
        for category,data in [('mesh',mesh),('geo',geo)]:
            folder=TARGET/category;folder.mkdir(parents=True,exist_ok=True);(folder/(model+'.'+category+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
        record=dict(model=model,triangles=mesh['triangleCount'],cover_triangles=len(parts['dorsal_cover']['vertices'])//24,**mesh['r13_dorsal_socket']);manifest.append(record);print(model,'cover',record['cover_triangles'],'total',record['triangles'],'staged only')
    (OUT/'candidate_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
if __name__=='__main__':main()
