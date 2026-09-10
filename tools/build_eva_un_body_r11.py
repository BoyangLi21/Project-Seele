"""Refine the actual EVA-UN geometry toward the accepted design: layered shells, recessed optics and restrained gold."""
import math,json,hashlib
import numpy as np
from pathlib import Path
from PIL import Image
import build_original_eva_prototype_r08 as old
m=old.m;ROOT=m.ROOT;m.OUT=ROOT/'artifacts/world_motion_r11/un/body';m.OUT.mkdir(parents=True,exist_ok=True)
m.COLOURS=['#252c31','#0c1115','#707b7e','#39464b','#a7884e','#030608','#d3b06a','#ffd584']
original_plate=old.plate;original_oriented=old.oriented_plate;original_ellipsoid=m.ellipsoid
def curved_face(bone,vertices,normal,colour,depth):
 vertices=np.asarray(vertices,float);normal=np.asarray(normal,float);normal/=np.linalg.norm(normal)
 u=np.cross(normal,[0,1,0])
 if np.linalg.norm(u)<.01:u=np.cross(normal,[1,0,0])
 u/=np.linalg.norm(u);v=np.cross(normal,u);xy=np.column_stack((vertices@u,vertices@v));segments=old.ears(xy);radius=max(.2,min(np.ptp(xy,axis=0))*.5)
 def curved(p):
  q=np.array([p@u,p@v]);distances=[]
  for a,b in zip(xy,np.roll(xy,-1,axis=0)):
   ab=b-a;t=np.clip((q-a)@ab/max(1e-9,ab@ab),0,1);distances.append(np.linalg.norm(q-a-t*ab))
  if min(distances)<1e-8:return p
  rel=xy-q;r=np.linalg.norm(rel,axis=1);nextv=np.roll(rel,-1,axis=0);rn=np.roll(r,-1)
  tangent=(rel[:,0]*nextv[:,1]-rel[:,1]*nextv[:,0])/np.maximum(1e-12,r*rn+(rel*nextv).sum(1));weights=(tangent+np.roll(tangent,1))/r;weights/=weights.sum()
  base=u*q[0]+v*q[1]+normal*np.dot(weights,vertices@normal)
  bulge=float(np.prod(1-np.exp(-(np.asarray(distances)/max(.12,radius*.43))**2)))
  return base+normal*depth*bulge
 def emit(a,b,c,level):
  if level:
   ab=(a+b)/2;bc=(b+c)/2;ca=(c+a)/2
   for tri in [(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)]:emit(*tri,level-1)
  else:
   aa,bb,cc=curved(a),curved(b),curved(c)
   if np.dot(np.cross(bb-aa,cc-aa),normal)<0:bb,cc=cc,bb
   old.T(bone,aa,bb,cc,colour)
 for a,b,c in segments:emit(vertices[a],vertices[b],vertices[c],2 if radius>1.2 else 1)
def clip(poly,axis,value,greater):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ia=(a[axis]>=value) if greater else (a[axis]<=value);ib=(b[axis]>=value) if greater else (b[axis]<=value)
  if ia:out.append(a)
  if ia!=ib:
   t=(value-a[axis])/(b[axis]-a[axis]);out.append((np.array(a)+(np.array(b)-a)*t).tolist())
 return out
def plate(bone,outline,thickness=1.5,colour=0,rim=4,bevel=.035,curve=.65):
 a=np.asarray(outline,float);extent=a.max(0)-a.min(0)
 # Split the large lower breast plates into overlapping stamped sections.
 if bone=='torso_upper' and a[:,2].mean()<0 and extent[0]>6 and extent[1]>16:
  cut=float(a[:,1].min()+extent[1]*.56)
  for lo,hi,offset in [(a[:,1].min()-1,cut+.4,0),(cut+.85,a[:,1].max()+1,-.35)]:
   band=clip(clip(a.tolist(),1,lo,True),1,hi,False)
   if len(band)>=3:
    b=np.asarray(band);b[:,2]+=offset;original_plate(bone,b,thickness,colour,4,.022,1.1)
  return
 if bone.startswith('pylon_') and extent[0]>6 and extent[1]>12:curve=max(curve,2.15)
 if bone=='head':curve=max(curve,1.1)
 accent=4 if bone=='torso_upper' or bone.startswith('pylon_') and extent[0]<5 else 2
 original_plate(bone,a,thickness,colour,accent if rim==4 else rim,min(bevel,.022),curve)
def oriented(bone,a,b,profile,width,depth,front_offset=0,colour=0):
 a=np.asarray(a,float);b=np.asarray(b,float);length=np.linalg.norm(b-a)
 bands=[(-1,2)]
 for index,(lo,hi) in enumerate(bands):
  polygon=clip(clip([list(q) for q in profile],1,lo,True),1,hi,False)
  if len(polygon)<3:continue
  # A rounded inset gives the black armour a real curved highlight in game.
  axis=(b-a)/length;side=np.array([1.,0,0]);side-=axis*np.dot(side,axis);side/=np.linalg.norm(side);front=np.cross(side,axis);front*= -1 if front[2]>0 else 1
  v=np.array([a+axis*t*length+side*u*width+front*(depth+front_offset+(.22 if index==0 else 0)) for u,t in polygon]);centre=v.mean(0);inner=centre+(v-centre)*.965+front*.18;back=centre+(v-centre)*.80-front*max(1.2,depth*1.8)
  if sum(polygon[i][0]*polygon[(i+1)%len(polygon)][1]-polygon[(i+1)%len(polygon)][0]*polygon[i][1] for i in range(len(polygon)))<0:v=v[::-1];inner=inner[::-1];back=back[::-1];polygon=polygon[::-1]
  outward=np.dot(np.cross(side,axis),front)>0
  def face(x,y,z,c):old.T(bone,x,y,z,c) if outward else old.T(bone,x,z,y,c)
  old.dome_face(bone,inner,front,colour,min(2.0,width*.31))
  for i,j,k in old.ears(np.asarray(polygon)):face(back[k],back[j],back[i],3)
  for i in range(len(v)):
   j=(i+1)%len(v);face(v[i],v[j],inner[j],2);face(v[i],inner[j],inner[i],2);face(v[i],back[i],back[j],colour);face(v[i],back[j],v[j],colour)
  if length>15:
   for sign in [-1,1]:
    q=a+axis*((lo+hi)/2*length)+side*sign*width*.55+front*(depth+front_offset+.65)
    m.ellipsoid(bone,q,(.18,.1,.18),4,10,6,front)
def ellipsoid(bone,c,radii,colour,*args,**kwargs):
 c=np.asarray(c,float);r=np.asarray(radii,float)
 if bone.startswith('pylon_') and colour==5 and np.allclose(r,[1.15,3.8,.4]):
  r=[2.25,3.35,.42];c[2]-=1.45;original_ellipsoid(bone,c,r,colour,*args,**kwargs);m.ring(bone,c+[0,0,-.30],(0,0,-1),2.46,.21,4,36);m.ring(bone,c+[0,0,-.36],(0,0,-1),1.78,.17,2,32);return
 if bone.startswith('pylon_') and colour==4 and np.allclose(r,[.56,2.6,.12]):return
 if bone=='head' and colour==7:r=[1.14,1.25,.25];c[2]-=.12
 original_ellipsoid(bone,c,r,colour,*args,**kwargs)
def insignia():
 # Project the emblem onto the existing chest skin, rather than suspending a label in front of it.
 alpha=np.array(Image.open(ROOT/'run/projectseele-local-maps/un_emblem.png').convert('RGBA').resize((56,48)))[:,:,3]>140
 values=np.array(m.PARTS['torso_upper']).reshape(-1,8);tri=(values[:,:3]+m.B['torso_upper']['pivot']).reshape(-1,3,3)
 def surface(x,y):
  a=tri[:,0,:2];v=tri[:,1,:2]-a;w=tri[:,2,:2]-a;delta=np.array([x,y])-a;den=v[:,0]*w[:,1]-v[:,1]*w[:,0];safe=np.abs(den)>1e-7
  u=np.divide(delta[:,0]*w[:,1]-delta[:,1]*w[:,0],den,out=np.zeros(len(den)),where=safe);t=np.divide(v[:,0]*delta[:,1]-v[:,1]*delta[:,0],den,out=np.zeros(len(den)),where=safe);ok=safe&(u>=0)&(t>=0)&(u+t<=1)
  if not ok.any():return None
  return float((tri[:,0,2]+u*(tri[:,1,2]-tri[:,0,2])+t*(tri[:,2,2]-tri[:,0,2]))[ok].min())-.035
 count=0
 for row,col in np.argwhere(alpha):
  x=7.0+col/56*6.0;y=154.5-row/48*5.14;points=[]
  for dx,dy in [(0,0),(6/56,0),(6/56,-5.14/48),(0,-5.14/48)]:
   z=surface(x+dx,y+dy)
   if z is None:break
   points.append(np.array([x+dx,y+dy,z]))
  if len(points)==4:old.T('torso_upper',points[0],points[2],points[1],6);old.T('torso_upper',points[0],points[3],points[2],6);count+=2
 return count
def main():
 old.plate=plate;old.oriented_plate=oriented;old.dome_face=curved_face;m.ellipsoid=ellipsoid;old.body();marks=insignia();m.save()
 path=m.A/'mesh/eva_prototype.mesh.json';data=json.loads(path.read_text());data['source']='Original EVA-UN R11 layered black/gold body, concept-contour refinement and surface-projected UN insignia';data['eye_socket_model']=[0,173,-7.22];path.write_text(json.dumps(data,separators=(',',':')))
 report=json.loads((m.OUT/'model_manifest.json').read_text());report.update(name='EVA-UN',surface_projected_emblem_triangles=marks,mesh_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),eye_socket_model=[0,173,-7.22]);(m.OUT/'model_manifest.json').write_text(json.dumps(report,indent=2));print('EVA-UN geometry ready',report)
if __name__=='__main__':main()
