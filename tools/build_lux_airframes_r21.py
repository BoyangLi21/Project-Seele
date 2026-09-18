"""Fit actual generated armour to the live rig; keep curved surfaces and welded joints.

Rigid armour remains GPU resident. Only narrow authored seam strips deform.
The former flat procedural body and Pro's simplified body are not substituted.
"""
import argparse,copy,json,math,hashlib,shutil
from pathlib import Path
from collections import defaultdict
import numpy as np
from scipy import sparse
from PIL import Image,ImageDraw,ImageFont
import build_original_eva_prototype_r07 as m
import build_original_eva_prototype_r08 as plates
import fit_un_dorsal_r21 as dorsal
ROOT=m.ROOT;ROOT_OUT=ROOT/'artifacts/un_models_r21';INSTALLED=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele'

def main(unit):
 out=ROOT_OUT/('un'+unit);a=out/'body/assets/projectseele';a.mkdir(parents=True,exist_ok=True)
 for category in ('mesh','geo','animations','textures/entity'):(a/category).mkdir(parents=True,exist_ok=True)
 palette=['#222a32','#10161c','#69757b','#35414a','#b4924d','#070c11','#e0bc67','#9ed67b','#c9323e','#edf0e4','#324d42','#808b8d'] if unit=='00' else ['#68785d','#18202b','#65719c','#455640','#90a081','#0b1219','#b59d70','#ff993b','#c8323c','#edf0e2','#404d73','#9ca5a7']
 source=ROOT_OUT/'lux3d'/('un'+unit)/'geometry.npz'
 with np.load(source) as data:raw=data['vertices'];faces=data['triangles'];colours=data['colors'].mean(1)
 # Use the actual installed hands and their accepted finger frames. These
 # are independent articulated digits, rather than fused generated fingers.
 geo=json.loads((INSTALLED/'geo/eva_prototype.geo.json').read_text());bones=geo['minecraft:geometry'][0]['bones'];bones=[copy.deepcopy(b) for b in bones if not b['name'].startswith('dorsal_')]
 m.B={b['name']:{**b,'parent':b.get('parent'),'bindRotationDegrees':b.get('rotation',[0,0,0])} for b in bones};m.RIG=list(m.B.values());m.P={n:np.array(b['pivot'])*[-1,1,1] for n,b in m.B.items()};m.BIND.clear();m.PARTS.clear();m.PREVIEW.clear();m.COLOURS=palette
 # Annotated source-joint landmarks are measured in the normalized source,
 # never inferred from a render's perspective or a Minecraft bounding box.
 elbow=129.0;wrist=96.0;knee=64.0;hip=112.0;ankle=18.0
 arm_x=30 if unit=='00' else 40;shoulder_x=26.5 if unit=='00' else 33.5;wrist_x=33.3 if unit=='00' else 44.0;knee_x=19.5 if unit=='00' else 25.5;foot_x=25.0 if unit=='00' else 31.0
 frames={}
 for side,s in [('l',-1),('r',1)]:
  for bone,start,end,target,target_end in [
   ('arm',(s*shoulder_x,149,0),(s*arm_x,elbow,0),'arm','forearm'),
   ('forearm',(s*arm_x,elbow,0),(s*wrist_x,wrist,-2),'forearm','hand'),
   ('leg',(s*13 if unit=='00' else s*16,hip,0),(s*knee_x,knee,0),'leg','shin'),
   ('shin',(s*knee_x,knee,0),(s*foot_x,ankle,0),'shin','foot'),
   ('foot',(s*foot_x,ankle,0),(s*foot_x,0,0),'foot',None)]:
   start,end=np.asarray(start,float),np.asarray(end,float);target=m.P[target+'_'+side];finish=m.P[target_end+'_'+side] if target_end else target*[1,0,1]
   frames[bone+'_'+side]=(start,target,m.frame(end-start),m.frame(finish-target),np.linalg.norm(finish-target)/np.linalg.norm(end-start))
 def classify(q):
  x,y,z=q;ax=abs(x);side='l' if x<0 else 'r';arm_edge=23 if unit=='00' else 30
  if y>159 and ax<17:return 'head'
  if y>143 and ax>(21 if unit=='00' else 23):return 'pylon_'+side
  if ax>arm_edge and y>65:return ('arm_' if y>elbow else 'forearm_')+side
  if y<23:return 'foot_'+side
  if y<knee:return 'shin_'+side
  if y<hip and ax>7:return 'leg_'+side
  return 'torso_lower' if y<126 else 'torso_upper'
 def deform(v,bone):
  if bone in frames:
   start,target,src,dst,long=frames[bone];q=(v-start)@src;q*=np.array([.95,long,.95]);return q@dst.T+target
  q=v.copy()
  if bone.startswith('pylon_'):
   s=-1 if bone.endswith('_l') else 1;q[:,0]=m.P[bone][0]+(q[:,0]-s*shoulder_x)*.93
  else:q[:,0]*=.84 if unit=='00' else .75
  return q
 unique,first,inverse=np.unique(np.round(raw,5),axis=0,return_index=True,return_inverse=True);raw=raw[first];faces=inverse[faces]
 labels=np.array([classify(q) for q in raw]);names=sorted(set(labels));indices={n:i for i,n in enumerate(names)}
 edges=np.vstack([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]);edges=np.vstack([edges,edges[:,::-1]]);adj=sparse.coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(raw),len(raw))).tocsr();adj.data[:]=1;degree=np.maximum(1,np.asarray(adj.sum(1)).ravel())
 boundary=np.zeros(len(raw),bool);cross=edges[labels[edges[:,0]]!=labels[edges[:,1]]];boundary[cross.ravel()]=True
 near=boundary.copy()
 for _ in range(9):near|=adj@near>0
 posed=raw.copy()
 for bone in names:
  mask=labels==bone;posed[mask]=deform(raw[mask],bone)
 displacement=posed-raw
 for _ in range(20):displacement[near]=displacement[near]*.28+((adj@displacement)/degree[:,None])[near]*.72
 posed=raw+displacement
 # Remove the finest generative corrugation without changing the silhouette.
 for coefficient in (.25,-.26,.25,-.26):posed+=coefficient*((adj@posed)/degree[:,None]-posed)
 weights=np.zeros((len(raw),len(names)),np.float32);weights[np.arange(len(raw)),[indices[n] for n in labels]]=1
 for _ in range(9):weights[near]=.35*weights[near]+.65*((adj@weights)/degree[:,None])[near]
 # The rigid side of a seam must agree exactly with its deforming copy.
 # Keeping a 0.0005 tail on only the latter opens a visible knee gap under
 # large prone rotations, despite an identical neutral mesh.
 dominant=weights.argmax(1);rigid=weights[np.arange(len(weights)),dominant]>.9995
 weights[rigid]=0;weights[np.flatnonzero(rigid),dominant[rigid]]=1
 centre=raw[faces].mean(1);kept=~((np.abs(centre[:,0])>(25 if unit=='00' else 30))&(centre[:,1]>65)&(centre[:,1]<wrist))
 triangles=posed[faces];face_normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);valid=np.linalg.norm(face_normals,axis=1)>1e-8;kept&=valid
 normals=np.zeros_like(posed)
 for c in range(3):np.add.at(normals,faces[:,c],face_normals)
 normals/=np.maximum(1e-10,np.linalg.norm(normals,axis=1,keepdims=True))
 mat=np.zeros(len(faces),int);x,y,z=centre.T
 if unit=='01':
  c=colours;blue=(c[:,2]>c[:,0]*1.04)&(c[:,2]>c[:,1]*1.02);tan=(c[:,0]>c[:,1]*.96)&(c[:,1]>c[:,2]*1.2)&(c[:,0]>.1);dark=np.max(c,axis=1)<.08
  mat[blue]=2;mat[tan]=6;mat[dark]=1
  mat[(c[:,0]>c[:,1]*1.14)&(y>138)]=0
 else:
  flex=((abs(y-elbow)<3)&(abs(x)>25))|((abs(y-knee)<3)&(abs(x)>10))|((abs(y-ankle)<2)&(abs(x)>10))|((y>112)&(y<134)&(abs(x)<11))|((y>155)&(y<164)&(abs(x)<7))
  mat[flex]=1
 groups=defaultdict(list);seam_specs={};third_weight=0
 for i in np.flatnonzero(kept):
  w=weights[faces[i]];order=np.argsort(w.sum(0))[::-1];first_bone,second_bone=names[order[0]],names[order[1]]
  if np.min(w[:,order[0]])>.9995:part=first_bone
  else:
   part='r21_join_'+first_bone
   if part not in m.B:
    b=dict(name=part,parent=first_bone,pivot=m.B[first_bone]['pivot'][:],bindRotationDegrees=[0,0,0]);m.B[part]=b;m.P[part]=m.P[first_bone].copy();bones.append(dict(name=part,parent=first_bone,pivot=b['pivot']));seam_specs[part]={'influences':{n:[] for n in names}}
   w=w/np.maximum(1e-12,w.sum(1,keepdims=True))
   for j,n in enumerate(names):seam_specs[part]['influences'][n].extend(np.round(w[:,j],8).tolist())
  groups[part].append(i)
 for bone,selected in groups.items():
  ids=np.asarray(selected);v=triangles[ids];inv=np.linalg.inv(m.bind(bone));local=(np.concatenate([v,np.ones((*v.shape[:2],1))],axis=2)@inv.T)[:,:,:3]*[-1,1,1]-m.B[bone]['pivot'];n=(normals[faces[ids]]@inv[:3,:3].T)*[-1,1,1]
  d=np.empty((len(ids),3,8));d[:,:,:3]=local;d[:,:,3]=((mat[ids]%4+.5)/4)[:,None];d[:,:,4]=((mat[ids]//4+.5)/2)[:,None];d[:,:,5:]=n
  m.PARTS[bone].extend(d.ravel().tolist())
 handmesh=json.loads((INSTALLED/'mesh/eva_prototype.mesh.json').read_text())
 for bone,part in handmesh['parts'].items():
  if bone.startswith(('hand_','finger_')):
   d=np.array(part['vertices']).reshape(-1,8);old_col=np.minimum(7,np.floor(d[:,3]*4).astype(int)+4*np.floor(d[:,4]*2).astype(int))
   new_col=np.array([0,1,2,3,4,5,6,7])[old_col] if unit=='00' else np.array([0,2,2,3,3,5,6,7])[old_col]
   d[:,3]=(new_col%4+.5)/4;d[:,4]=(new_col//4+.5)/2;m.PARTS[bone].extend(d.ravel().tolist())
 for side in ('l','r'):m.ellipsoid('hand_'+side,m.P['hand_'+side],(2.7,2.1,2.3),1 if unit=='00' else 2,24,12)
 # Cache real front intersections for shallow conforming markings and bolts.
 cache={};grid=defaultdict(list);surface_faces=triangles[kept];surface_weights=weights[faces[kept]].mean(1)
 for i,q in enumerate(surface_faces):
  low=np.floor(q[:,:2].min(0)/2).astype(int);high=np.floor(q[:,:2].max(0)/2).astype(int)
  for xx in range(low[0],high[0]+1):
   for yy in range(low[1],high[1]+1):grid[xx,yy].append(i)
 def surface(bone,x,y):
  ids=np.array(grid.get((math.floor(x/2),math.floor(y/2)),[]),int)
  if not len(ids):return None
  q=surface_faces[ids];a=q[:,0,:2];b=q[:,1,:2]-a;c=q[:,2,:2]-a;den=b[:,0]*c[:,1]-b[:,1]*c[:,0]
  d=np.array([x,y])-a;safe=abs(den)>1e-9;u=np.divide(d[:,0]*c[:,1]-d[:,1]*c[:,0],den,out=np.zeros(len(den)),where=safe);v=np.divide(b[:,0]*d[:,1]-b[:,1]*d[:,0],den,out=np.zeros(len(den)),where=safe);valid=safe&(u>=0)&(v>=0)&(u+v<=1)
  if bone in indices:valid&=surface_weights[ids,indices[bone]]>.15
  ids=np.flatnonzero(valid)
  if not len(ids):return None
  zz=q[:,0,2]+u*(q[:,1,2]-q[:,0,2])+v*(q[:,2,2]-q[:,0,2]);i=ids[np.argmin(zz[ids])];n=np.cross(q[i,1]-q[i,0],q[i,2]-q[i,0]);n/=np.linalg.norm(n)
  if n[2]>0:n=-n
  return np.array([x,y,zz[i]])+n*.06,n
 def decal(bone,poly,colour,offset=.04,depth=2):
  def emit(a,b,c,level):
   if level:
    ab=(a+b)/2;bc=(b+c)/2;ca=(c+a)/2
    for t in [(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)]:emit(*t,level-1)
   else:
    points=[surface(bone,*p) for p in (a,b,c)]
    if all(p is not None for p in points):m.triangle(bone,*[p+n*offset for p,n in points][::-1],colour)
  poly=np.array(poly)
  for i,j,k in plates.ears(poly):emit(poly[i],poly[j],poly[k],depth)
 if unit=='01':
  for radius,colour,off in [(5.25,9,.12),(4.8,8,.20)]:decal('torso_upper',[(math.sin(i*math.pi/5)*radius*(1 if i%2==0 else .4),155.8+math.cos(i*math.pi/5)*radius*(1 if i%2==0 else .4)) for i in range(10)],colour,off,3)
 # Original typeface strokes are projected onto the actual curved chest.
 font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',36);im=Image.new('L',(60,42));ImageDraw.Draw(im).text((0,-5),'UN',font=font,fill=255)
 for row,col in np.argwhere(np.array(im)>160):
  x=13.3-col*.092;y=160-row*.10;decal('torso_upper',[(x,y),(x-.092,y),(x-.092,y-.10),(x,y-.10)],4 if unit=='00' else 9,.15,0)
 def trim(bone,points,width=.085):
  placed=[]
  for x,y in points:
   hit=surface(bone,x,y)
   if hit is not None:placed.append(hit[0]+hit[1]*.12)
  if len(placed)>1:m.loft(bone,placed,[width]*len(placed),[width]*len(placed),4,10)
 if unit=='00':
  trim('torso_upper',[(0,y) for y in np.linspace(155,134,35)],.10)
  for side,s in [('l',-1),('r',1)]:
   for path in [[(2,154),(7,156),(14,157),(17,153),(14,148),(9,146),(3,148)],[(3,142),(7,144),(12,143),(14,137),(7,134),(3,135)]]:
    dense=[]
    for p,q in zip(path,path[1:]):dense.extend([(s*(p[0]*(1-t)+q[0]*t),p[1]*(1-t)+q[1]*t) for t in np.linspace(0,1,9)])
    trim('torso_upper',dense)
   trim('pylon_'+side,[(m.P['pylon_'+side][0],y) for y in np.linspace(163,188,45)],.12)
   for bone,ys in [('forearm',(101,119)),('leg',(74,105)),('shin',(28,53))]:
    for dx in (-3,3):trim(bone+'_'+side,[(m.P[bone+'_'+side][0]+dx,y) for y in np.linspace(*ys,35)],.075)
 # A real metallic optical ring, with the final surface point reported for
 # the authoritative laser and first-person eye location.
 hit=surface('head',0,173 if unit=='00' else 177.8);assert hit is not None
 optic,n=hit;optic=optic+n*.35;lens=optic+n*.45
 if unit=='00':
  m.ring('head',optic,n,1.72,.28,4,48);m.ellipsoid('head',optic+n*.10,(1.30,.30,1.30),7,48,20,n)
 else:
  visor=[surface('head',x,177.8-.028*x*x) for x in np.linspace(-4.2,4.2,39)];visor=[v for v in visor if v is not None];assert len(visor)>30
  m.loft('head',[p+n*.35 for p,n in visor],[.45]*len(visor),[.90]*len(visor),5,20)
  m.loft('head',[p+n*.64 for p,n in visor],[.28]*len(visor),[.55]*len(visor),7,20);lens=hit[0]+hit[1]*.95
 for bone in ('torso_upper','torso_lower','forearm_l','forearm_r','leg_l','leg_r','shin_l','shin_r'):
  ys={'torso_upper':[142,155],'torso_lower':[106,121],'forearm_l':[103,115],'forearm_r':[103,115],'leg_l':[82,101],'leg_r':[82,101],'shin_l':[31,48],'shin_r':[31,48]}[bone]
  xs=[-12,12] if bone=='torso_upper' else [-7,7] if bone=='torso_lower' else [m.P[bone][0]-3,m.P[bone][0]+3]
  for yy in ys:
   for xx in xs:
    h=surface(bone,xx,yy)
    if h is not None:
     p,n=h;m.ring(bone,p+n*.08,n,.27,.055,4 if unit=='00' else 3,16);m.ellipsoid(bone,p+n*.07,(.19,.06,.19),5,12,6,n)
 image=Image.new('RGB',(1024,768));draw=ImageDraw.Draw(image)
 for i,c in enumerate(palette):draw.rectangle((i%4*256,i//4*256,i%4*256+255,i//4*256+255),fill=c)
 image.save(a/'textures/entity/eva_prototype.png');eyes=Image.new('RGBA',image.size,(0,0,0,0));eyes.paste(image.crop((768,256,1024,512)).convert('RGBA'),(768,256));eyes.save(a/'textures/entity/eva_prototype_eyes.png')
 parts={}
 for name,values in m.PARTS.items():
  d=np.asarray(values).reshape(-1,8);d[:,4]*=2/3;length=np.linalg.norm(d[:,5:],axis=1);zero=length<1e-8
  if zero.any():
   tris=d[:,:3].reshape(-1,3,3);normal=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]);normal/=np.maximum(1e-12,np.linalg.norm(normal,axis=1,keepdims=True));d[zero,5:]=-np.repeat(normal,3,axis=0)[zero]
  d[:,5:]/=np.maximum(1e-9,np.linalg.norm(d[:,5:],axis=1,keepdims=True));assert np.isfinite(d).all()
  parts[name]={'pivot':m.B[name]['pivot'],'vertices':np.round(d,6).ravel().tolist()}
 for spec in seam_specs.values():spec['influences']={k:v for k,v in spec['influences'].items() if max(v)>0}
 mesh=dict(format_version=1,model_height=193.1,stride=8,atlas_rows=3,triangleCount=sum(len(x['vertices'])//24 for x in parts.values()),parts=parts,jointSkins=seam_specs,eye_socket_model=lens.tolist(),source='Lux3D generated curved armour, locally articulated hands, original surface-projected marks',lux3d_task='3569385' if unit=='00' else '3569389')
 (a/'mesh/eva_prototype.mesh.json').write_text(json.dumps(mesh,separators=(',',':')))
 geo['minecraft:geometry'][0]['bones']=bones;geo['minecraft:geometry'][0]['description'].update(texture_width=1024,texture_height=768)
 (a/'geo/eva_prototype.geo.json').write_text(json.dumps(geo,indent=2));shutil.copy2(INSTALLED/'animations/eva_prototype.animation.json',a/'animations/eva_prototype.animation.json')
 final=out/'runtime/assets/projectseele'
 frame=json.loads((INSTALLED/'mesh/eva_prototype.mesh.json').read_text())['r13_dorsal_socket']
 dorsal.fit(a,final,frame,out/'dorsal.json',unit)
 for directory in ('animations','textures/entity'):
  (final/directory).mkdir(parents=True,exist_ok=True)
  for p in (a/directory).iterdir():shutil.copy2(p,final/directory/p.name)
 mesh=json.loads((final/'mesh/eva_prototype.mesh.json').read_text());report=dict(unit=unit,triangles=mesh['triangleCount'],parts=len(mesh['parts']),source_triangles=len(faces),retained_source_triangles=int(kept.sum()),seam_parts=len(seam_specs),maximum_third_weight=third_weight,optical_centre=optic.tolist(),optical_origin=lens.tolist(),canonical_body_pivots_retained=True)
 (out/'build_report.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--unit',choices=['00','01'],required=True);main(ap.parse_args().unit)
