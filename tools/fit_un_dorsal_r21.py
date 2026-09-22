"""Actual bored pressure tube and one clean hinged cover on the new armour."""
import json,math,copy
from pathlib import Path
import numpy as np

def split(poly,n,d):
 inside=[];outside=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  aa=a[:3]@n-d;bb=b[:3]@n-d;ia=aa<=1e-7;ib=bb<=1e-7;(inside if ia else outside).append(a)
  if ia!=ib:
   p=a+(b-a)*(aa/(aa-bb));inside.append(p);outside.append(p)
 return inside,outside
def fan(poly):return [np.array([poly[0],poly[i],poly[i+1]]) for i in range(1,len(poly)-1) if np.linalg.norm(np.cross(poly[i][:3]-poly[0][:3],poly[i+1][:3]-poly[0][:3]))>1e-8]
def outside(triangles,planes):
 result=[]
 for tri in triangles:
  distance=np.array([tri[:,:3]@n-d for n,d in planes])
  if (distance.min(1)>1e-7).any():result.append(tri);continue
  if distance.max()<=1e-7:continue
  poly=list(tri)
  for n,d in planes:
   if len(poly)<3:break
   poly,discard=split(poly,n,d);result.extend(fan(discard))
 return np.array(result).reshape(-1,3,triangles.shape[2])
def fit(source,target,old_frame,manifest,unit):
 source,target=Path(source),Path(target);mesh=json.loads((source/'mesh/eva_prototype.mesh.json').read_text());geo=json.loads((source/'geo/eva_prototype.geo.json').read_text());parts=mesh['parts'];bones=geo['minecraft:geometry'][0]['bones']
 C=np.array(old_frame['centre']);N=np.array(old_frame['outward']);N/=np.linalg.norm(N);X=np.array([1.,0,0]);Y=np.cross(N,X)
 # Find the actual outside surface along the original insertion axis.
 body=np.concatenate([(np.array(p['vertices']).reshape(-1,3,8)[:,:,:3]+p['pivot']) for name,p in parts.items() if name.startswith(('torso_','head','r21_join_'))])
 origin=C-N*20;edge1=body[:,1]-body[:,0];edge2=body[:,2]-body[:,0];h=np.cross(N,edge2);det=np.einsum('ij,ij->i',edge1,h);safe=abs(det)>1e-9;inverse=np.divide(1,det,out=np.zeros_like(det),where=safe);s=origin-body[:,0];u=inverse*np.einsum('ij,ij->i',s,h);q=np.cross(s,edge1);v=inverse*(q@N);distance=inverse*np.einsum('ij,ij->i',edge2,q);hits=distance[safe&(u>=0)&(v>=0)&(u+v<=1)&(distance>0)&(distance<52)]
 assert len(hits),'Insertion axis must intersect the measured torso'
 C=origin+N*(hits.max()+.65);hinge=C-X*6.6+Y*.3+N*.7
 planes=[(X*math.cos(t)+Y*math.sin(t),3.8+(X*math.cos(t)+Y*math.sin(t))@C) for t in np.linspace(0,2*math.pi,32,endpoint=False)]+[(N,N@C+.5),(-N,-N@C+36)]
 removed=0
 for name,p in list(parts.items()):
  if not name.startswith(('torso_','head','r21_join_')):continue
  data=np.array(p['vertices']).reshape(-1,3,8);data[:,:,:3]+=p['pivot'];spec=mesh.get('jointSkins',{}).get(name);keys=list(spec['influences']) if spec else []
  if keys:data=np.concatenate([data,np.stack([spec['influences'][k] for k in keys],axis=1).reshape(-1,3,len(keys))],axis=2)
  before=len(data);data=outside(data,planes);removed+=max(0,before-len(data));data[:,:,:3]-=p['pivot'];normal=data[:,:,5:8];normal/=np.maximum(1e-9,np.linalg.norm(normal,axis=2,keepdims=True));p['vertices']=np.round(data[:,:,:8],6).ravel().tolist()
  if spec:
   w=data[:,:,8:];w/=np.maximum(1e-12,w.sum(2,keepdims=True));spec['influences']={k:np.round(w[:,:,i].ravel(),8).tolist() for i,k in enumerate(keys)}
 for name,pivot in [('dorsal_cover',hinge),('dorsal_liner',C)]:
  bones.append(dict(name=name,parent='torso_upper',pivot=pivot.tolist()));parts[name]={'pivot':pivot.tolist(),'vertices':[]}
 def triangle(bone,a,b,c,colour):
  normal=np.cross(b-a,c-a);length=np.linalg.norm(normal)
  if length<1e-9:return
  normal/=length;pivot=np.asarray(parts[bone]['pivot']);uv=[(colour%4+.5)/4,(colour//4+.5)/3]
  if 'r30_palette_region' in mesh:
   palette=mesh['r30_palette_region'];uv[0]=palette['u0']+uv[0]*palette['width']
  # Runtime mesh positions reflect X on import. Its stored normals therefore
  # point opposite the raw Geo-space triangle winding.
  for p in (c,b,a):parts[bone]['vertices'].extend([*(p-pivot),*uv,*normal])
 def quad(bone,a,b,c,d,colour):triangle(bone,a,b,c,colour);triangle(bone,a,c,d,colour)
 def tube(start,end,outer,inner,colour,bone='dorsal_liner',segments=48):
  axis=end-start;axis/=np.linalg.norm(axis);xx=np.cross(axis,[1.,0,0] if abs(axis[0])<.9 else [0,1.,0]);xx/=np.linalg.norm(xx);yy=np.cross(axis,xx)
  for t,u in zip(np.linspace(0,2*math.pi,segments+1)[:-1],np.linspace(0,2*math.pi,segments+1)[1:]):
   a=xx*math.cos(t)+yy*math.sin(t);b=xx*math.cos(u)+yy*math.sin(u)
   quad(bone,start+a*outer,start+b*outer,end+b*outer,end+a*outer,colour)
   quad(bone,start+a*inner,start+b*inner,start+b*outer,start+a*outer,colour);quad(bone,end+a*outer,end+b*outer,end+b*inner,end+a*inner,colour)
   if inner:quad(bone,start+a*inner,end+a*inner,end+b*inner,start+b*inner,1)
 tube(C-N*35,C+N*.25,3.73,3.57,1)
 tube(C-N*.2,C+N*.32,5.5,3.80,3);tube(C+N*.33,C+N*.46,4.10,3.72,4 if unit=='00' else 2)
 for depth in (2,6,12,20,28,34):tube(C-N*(depth+.16),C-N*depth,3.64,3.49,2,segments=32)
 outline=np.array([[-5.5,4.9],[5.5,4.9],[6.3,1],[4.9,-4.7],[0,-7],[-4.9,-4.7],[-6.3,1]])
 border=[C+X*x+Y*y+N*.75 for x,y in outline];inner=[C+X*x*.91+Y*y*.91+N*1.08 for x,y in outline];back=[p-N*.5 for p in border];centre=C+N*1.08
 for i in range(len(border)):
  j=(i+1)%len(border);triangle('dorsal_cover',centre,inner[j],inner[i],0);quad('dorsal_cover',border[i],inner[i],inner[j],border[j],4 if unit=='00' else 3);quad('dorsal_cover',border[i],border[j],back[j],back[i],1);triangle('dorsal_cover',C+N*.25,back[i],back[j],1)
 for x in (-3.25,3.25):
  p=C+X*x+Y*2.45+N*1.08;tube(p,p+N*.12,.70,.39,2,'dorsal_cover',32);tube(p+N*.10,p+N*.14,.38,0,5,'dorsal_cover',32)
 for y in (-2.8,2.8):
  p=hinge+Y*y;tube(p-Y*.7,p+Y*.7,.42,.12,2,segments=24)
 frame=dict(centre=C.tolist(),outward=N.tolist(),hinge=hinge.tolist(),hinge_axis=Y.tolist(),open_angle_degrees=-105,radius_model=3.8)
 mesh['r13_dorsal_socket']=frame;mesh['triangleCount']=sum(len(p['vertices'])//24 for p in parts.values())
 for kind,data in [('mesh',mesh),('geo',geo)]:
  (target/kind).mkdir(parents=True,exist_ok=True);(target/kind/('eva_prototype.'+kind+'.json')).write_text(json.dumps(data,separators=(',',':')))
 Path(manifest).write_text(json.dumps(dict(frame=frame,source_axis=old_frame,actual_outer_intersections=hits.tolist(),triangles=mesh['triangleCount'],closed_cover='one machined thick plate with two circular rear markings',bore='32-sided 3.8 model-unit radius through actual body, skin weights interpolated on cut faces'),indent=2))
