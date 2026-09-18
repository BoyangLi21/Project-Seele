"""Repair the actual runtime mesh: planar wrist cut, anatomical palm, seated optics."""
from pathlib import Path
import argparse,copy,json,math,shutil
import numpy as np
import build_original_eva_prototype_r07 as m
ROOT=m.ROOT;OUT=ROOT/'artifacts/facility_r23/models'
BASE=Path(json.loads((ROOT/'artifacts/facility_r23/baseline.json').read_text())['backup'])/'review_assets/assets/projectseele'

def clip(poly,dist,inside=True):
 result=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  da,db=dist(a),dist(b);ka=da>=-1e-9 if inside else da<=1e-9;kb=db>=-1e-9 if inside else db<=1e-9
  if ka:result.append(a)
  if ka!=kb:result.append(a+(b-a)*(da/(da-db)))
 return result
def triangulate(poly):return [np.stack([poly[0],poly[i],poly[i+1]]) for i in range(1,len(poly)-1)]
def world(v,pivot,bone):
 raw=(v[:,:3]+pivot)*[-1,1,1];matrix=m.bind(bone);return (np.c_[raw,np.ones(len(raw))]@matrix.T)[:,:3]
def wrist_cut(mesh,side):
 hand=m.P['hand_'+side];elbow=m.P['forearm_'+side];axis=elbow-hand;axis/=np.linalg.norm(axis);plane=hand+axis*6.5;changed=0;boundary=[]
 for name,part in mesh['parts'].items():
  if name not in ('forearm_'+side,'r21_join_forearm_'+side):continue
  verts=np.asarray(part['vertices']).reshape(-1,8);wp=world(verts,np.array(part['pivot']),name);skin=mesh.get('jointSkins',{}).get(name);names=list(skin['influences']) if skin else [];weights=np.stack([skin['influences'][b] for b in names],axis=1) if skin else np.zeros((len(verts),0))
  # Upper forearm geometry and its hard-edge normals remain unchanged.
  records=np.c_[verts,wp,weights];out=[]
  for tri in records.reshape(-1,3,records.shape[1]):
   d=(tri[:,8:11]-plane)@axis
   if np.min(d)>=0:out.append(tri)
   elif np.max(d)>=0:out.extend(triangulate(clip(list(tri),lambda v:float((v[8:11]-plane)@axis))));changed+=1
   else:changed+=1
  result=np.concatenate(out);normal=result[:,5:8];normal/=np.maximum(1e-12,np.linalg.norm(normal,axis=1,keepdims=True));part['vertices']=np.round(result[:,:8],6).ravel().tolist()
  boundary.extend(result[np.abs((result[:,8:11]-plane)@axis)<1e-5,8:11])
  if skin:
   values=result[:,11:];values/=np.maximum(1e-12,values.sum(1,keepdims=True));skin['influences']={b:np.round(values[:,i],8).tolist() for i,b in enumerate(names)}
 if boundary:
  boundary=np.unique(np.round(boundary,5),axis=0);basis=m.frame(axis);uv=(boundary-plane)@basis[:,[0,2]];order=np.argsort(np.arctan2(uv[:,1],uv[:,0]));ring=boundary[order];centre=ring.mean(0)
  for i in range(len(ring)):m.triangle('forearm_'+side,centre,ring[i],ring[(i+1)%len(ring)],0)
  radius=np.max(np.abs((boundary-centre)@basis[:,[0,2]]),axis=0)+.12
  m.loft('forearm_'+side,[centre+axis*.7,centre,hand+axis*3.1],[radius[0],radius[0],3.0],[radius[1],radius[1],2.8],0,40)
 return hand,axis,plane,changed
def pivot(name):return (m.bind(name)@np.r_[m.P[name],1])[:3]
def tube(bone,centres,width,depth,colour,basis,sides=24):
 rings=[]
 for p,w,d in zip(centres,width,depth):rings.append([p+basis[:,0]*w*math.cos(t)+basis[:,2]*d*math.sin(t) for t in np.linspace(0,2*math.pi,sides,endpoint=False)])
 for a,b in zip(rings,rings[1:]):
  for i in range(sides):j=(i+1)%sides;m.triangle(bone,a[i],b[i],b[j],colour);m.triangle(bone,a[i],b[j],a[j],colour)
 for ring,centre,reverse in [(rings[0],centres[0],True),(rings[-1],centres[-1],False)]:
  for i in range(sides):j=(i+1)%sides;m.triangle(bone,centre,ring[j] if reverse else ring[i],ring[i] if reverse else ring[j],colour)
def hand_mesh(side,hand,axis,plane,unit):
 colour=0 if unit=='00' else 0;flex=1 if unit=='00' else 2;trim=4 if unit=='00' else 3
 # Complete sleeves hide the old saw-tooth boundary; a smaller compliant wrist
 # bridges to the moving palm without a large sheet passing through the thumb.
 m.loft('wrist_'+side,[hand+axis*3.0,hand+axis*.7,hand-axis*1.0],[2.65,2.9,2.75],[2.5,2.7,2.5],flex,32)
 knuckles=np.array([pivot('finger_'+n+'_'+side) for n in ('index','middle','ring','little')]);tip=knuckles.mean(0);long=tip-hand;long/=np.linalg.norm(long);width=knuckles[0]-knuckles[-1];width-=long*np.dot(width,long);width/=np.linalg.norm(width);normal=np.cross(width,long);normal/=np.linalg.norm(normal);basis=np.column_stack([width,long,normal]);length=np.linalg.norm(tip-hand)
 centres=[hand+long*d for d in (-.5,.5,length*.40,length*.75,length+.35)]
 tube('hand_'+side,centres,[2.3,2.8,4.1,5.0,5.15],[2.0,2.05,1.65,1.45,1.1],flex,basis,32)
 # Four separate dorsal metacarpal plates follow the actual knuckle fan.
 for root in knuckles:
  start=hand*.62+root*.38+normal*1.45;end=root+normal*.95
  m.loft('hand_'+side,[start,(start+end)*.5,end],[.7,1.0,.85],[.22,.35,.22],colour,16)
 for name in ('index','middle','ring','little','thumb'):
  bone='finger_'+name+'_'+side;second='finger_'+name+'_tip_'+side;third='finger_'+name+'_distal_'+side;points=[pivot(bone),pivot(second)]
  if third in m.B:points.append(pivot(third));points.append(points[-1]+(points[-1]-points[-2])*.72);parts=[bone,second,third]
  else:points.append(points[-1]+(points[-1]-points[-2])*.66);parts=[bone,second]
  radius=.93 if name=='little' else 1.15 if name=='thumb' else 1.05
  for i,(a,b,parent) in enumerate(zip(points,points[1:],parts)):
   v=b-a;length=np.linalg.norm(v);v/=length;r=radius*(1-.1*i)
   m.ellipsoid(parent,a,(r*.95,r*.88,r*.94),flex,24,12,v)
   m.loft(parent,[a+v*.2,a+v*(length*.25),b-v*.32,b+v*.16],[r*.84,r,r*.85,r*.53],[r*.77,r*.90,r*.72,r*.49],flex,24)
   # Low protective shells, not rows of oversized gold bolts.
   shell_a=a+v*.65+normal*(r*.80);shell_b=b-v*.42+normal*(r*.64)
   if np.linalg.norm(shell_b-shell_a)>.4:m.loft(parent,[shell_a,(shell_a+shell_b)*.5,shell_b],[r*.62,r*.80,r*.54],[.15,.25,.13],colour,16)
 return dict(wrist=hand.tolist(),knuckles=knuckles.tolist(),palm_normal=normal.tolist(),fingers=5)
def face_depth(triangles,x,y):
 a=triangles[:,0,:2];b=triangles[:,1,:2]-a;c=triangles[:,2,:2]-a;den=b[:,0]*c[:,1]-b[:,1]*c[:,0];d=np.array([x,y])-a;safe=abs(den)>1e-10;u=np.divide(d[:,0]*c[:,1]-d[:,1]*c[:,0],den,out=np.zeros(len(den)),where=safe);v=np.divide(b[:,0]*d[:,1]-b[:,1]*d[:,0],den,out=np.zeros(len(den)),where=safe);mask=safe&(u>=0)&(v>=0)&(u+v<=1);z=triangles[:,0,2]+u*(triangles[:,1,2]-triangles[:,0,2])+v*(triangles[:,2,2]-triangles[:,0,2]);return float(z[mask].min())
def optics(mesh,unit):
 part=mesh['parts']['head'];v=np.asarray(part['vertices']).reshape(-1,3,8);mat=(np.floor(v[:,:,3].mean(1)*4).astype(int)+4*np.floor(v[:,:,4].mean(1)*3).astype(int));old_lens=np.isin(mat,[4,7] if unit=='00' else [5,7]);v=v[~old_lens]
 wp=world(v.reshape(-1,8),np.array(part['pivot']),'head').reshape(-1,3,3);cy=173.0 if unit=='00' else 177.8;rx,ry=(1.80,1.80) if unit=='00' else (1.38,2.0)
  # The housing follows the original face at its perimeter, and becomes
  # planar inside. The head itself is never flattened or cut through.
 samples=[face_depth(wp,rx*r*math.cos(t),cy+ry*r*math.sin(t)) for r in (0,.5,1.12) for t in np.linspace(0,2*math.pi,32,endpoint=False)]
 z=min(samples)-.10;centre=np.array([0.,cy,z]);part['vertices']=v.ravel().tolist()
 rings=[]
 for r,mix in ((1.85,0),(1.55,.22),(1.25,.75),(1.08,1.0)):
  ring=[]
  for t in np.linspace(0,2*math.pi,96,endpoint=False):
   x,y=rx*r*math.cos(t),cy+ry*r*math.sin(t);depth=face_depth(wp,x,y)-.06;ring.append(np.array([x,y,depth*(1-mix)+z*mix]))
  rings.append(ring)
 for outer,inner in zip(rings,rings[1:]):
  for i in range(96):j=(i+1)%96;m.triangle('head',outer[i],outer[j],inner[j],5);m.triangle('head',outer[i],inner[j],inner[i],5)
 normal=np.array([0.,0.,-1.]);basis=np.column_stack([np.array([1.,0,0]),normal,np.array([0.,1.,0])])
 tube('head',[centre-normal*.10,centre,centre+normal*.10],[rx*1.03,rx*1.12,rx*1.06],[ry*1.03,ry*1.12,ry*1.06],5,basis,48)
 # Elliptical machined bezel, centred on the head symmetry plane.
 for inner,colour in [(1.0,4 if unit=='00' else 6),(.80,1)]:
  rings=[]
  for t in np.linspace(0,2*math.pi,64,endpoint=False):
   radial=np.array([rx*inner*math.cos(t),ry*inner*math.sin(t),0]);out=np.array([math.cos(t),math.sin(t),0]);rings.append([centre+normal*.15+radial+out*.11*math.cos(a)+normal*.08*math.sin(a) for a in np.linspace(0,2*math.pi,8,endpoint=False)])
  for i in range(64):
   for j in range(8):ii=(i+1)%64;jj=(j+1)%8;m.triangle('head',rings[i][j],rings[ii][j],rings[ii][jj],colour);m.triangle('head',rings[i][j],rings[ii][jj],rings[i][jj],colour)
 m.ellipsoid('head',centre+normal*.11,(rx*.74,.12,ry*.74),7,48,20,normal)
 # Narrow mechanical iris, without a pupil/glint that reads as a cartoon eye.
 m.ellipsoid('head',centre+normal*.245,(rx*.12,.055,ry*.52),5,32,14,normal)
 lens=centre+normal*.33;mesh['eye_socket_model']=lens.tolist();mesh['r23_optical_frame']={'centre':centre.tolist(),'axis':normal.tolist(),'lens':lens.tolist(),'profile':'central circular optic' if unit=='00' else 'central vertical optic','old_optic_triangles_removed':int(old_lens.sum())};return mesh['r23_optical_frame']
def main(unit):
 name='eva_prototype' if unit=='00' else 'eva_un01';mesh=json.loads((BASE/'mesh'/(name+'.mesh.json')).read_text());geo=json.loads((BASE/'geo'/(name+'.geo.json')).read_text());bones=geo['minecraft:geometry'][0]['bones']
 m.B={b['name']:{**b,'parent':b.get('parent'),'bindRotationDegrees':b.get('rotation',[0,0,0])} for b in bones};m.P={n:np.array(b['pivot'])*[-1,1,1] for n,b in m.B.items()};m.BIND.clear();m.PARTS.clear();m.PREVIEW.clear()
 old_count=mesh['triangleCount'];hands={};cuts={}
 for side in ('l','r'):
  hand,axis,plane,changed=wrist_cut(mesh,side);cuts[side]=changed;hands[side]=hand_mesh(side,hand,axis,plane,unit)
 for key in list(mesh['parts']):
  if key.startswith(('hand_','finger_','wrist_')):del mesh['parts'][key]
 eye=optics(mesh,unit)
 for bone,values in m.PARTS.items():
  new=np.array(values).reshape(-1,8);new[:,4]*=2/3
  mesh['parts'].setdefault(bone,{'pivot':m.B[bone]['pivot'],'vertices':[]})['vertices']+=np.round(new,6).ravel().tolist()
  skin=mesh.get('jointSkins',{}).get(bone)
  if skin:
   # The newly closed wrist rim is rigid to its forearm. Preserve exact
   # influence/vertex cardinality; otherwise the live renderer rejects it.
   if bone not in skin['influences']:skin['influences'][bone]=[0.]*(len(mesh['parts'][bone]['vertices'])//8-len(new))
   for influence,weights in skin['influences'].items():weights.extend([1. if influence==bone else 0.]*len(new))
 removed_degenerate=0
 for bone,part in mesh['parts'].items():
  data=np.asarray(part['vertices']).reshape(-1,3,8);normal=np.cross(data[:,1,:3]-data[:,0,:3],data[:,2,:3]-data[:,0,:3]);keep=np.linalg.norm(normal,axis=1)>1e-10;removed_degenerate+=int((~keep).sum());data=data[keep];normal=normal[keep];flat=data.reshape(-1,8)
  lengths=np.linalg.norm(flat[:,5:8],axis=1);zero=lengths<1e-8
  if zero.any():
   normal/=np.maximum(1e-12,np.linalg.norm(normal,axis=1,keepdims=True));flat[zero,5:8]=-np.repeat(normal,3,axis=0)[zero]
  flat[:,5:8]/=np.maximum(1e-12,np.linalg.norm(flat[:,5:8],axis=1,keepdims=True));part['vertices']=np.round(flat,6).ravel().tolist()
  if bone in mesh.get('jointSkins',{}):
   skin=mesh['jointSkins'][bone];skin['influences']={k:np.asarray(w)[np.repeat(keep,3)].tolist() for k,w in skin['influences'].items()}
 mesh['triangleCount']=sum(len(p['vertices'])//24 for p in mesh['parts'].values());mesh['r23_hands']=hands;mesh['source']+='; R23 rebuilt anatomical palms, exact wrist cuts, symmetric recessed optics'
 dest=OUT/('un'+unit)/'runtime/assets/projectseele'
 for folder in ('mesh','geo','textures/entity','animations'):(dest/folder).mkdir(parents=True,exist_ok=True)
 (dest/'mesh/eva_prototype.mesh.json').write_text(json.dumps(mesh,separators=(',',':')));geo['minecraft:geometry'][0]['description']['identifier']='geometry.eva_prototype';(dest/'geo/eva_prototype.geo.json').write_text(json.dumps(geo,indent=2))
 for suffix in ('.png','_eyes.png'):shutil.copy2(BASE/'textures/entity'/(name+suffix),dest/'textures/entity'/('eva_prototype'+suffix))
 shutil.copy2(BASE/'animations'/(name+'.animation.json'),dest/'animations/eva_prototype.animation.json')
 report=dict(unit=unit,old_triangles=old_count,triangles=mesh['triangleCount'],parts=len(mesh['parts']),removed_degenerate_triangles=removed_degenerate,wrist_cut_faces=cuts,hands=hands,optics=eye,original_body_and_joint_rig_retained=True)
 (OUT/('un'+unit)/'repair.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--unit',choices=['00','01'],required=True);main(ap.parse_args().unit)
