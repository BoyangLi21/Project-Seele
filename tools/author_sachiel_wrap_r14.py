"""TV episode 02 cuts 301–305: reach, wind, pull, then soft-body enclosure.

The private creature's existing UV topology morphs; it is never teleported through
the EVA. Evaluated EVA armour hulls constrain the authored surface at every frame.
Public code contains no third-party geometry or captured motion data.
"""
import json,struct,hashlib,argparse,shutil
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R
from scipy.interpolate import CubicSpline
from scipy.sparse import csr_matrix
from scipy.ndimage import gaussian_filter1d
from refine_wrap_topology_r14 import curved_subdivide
import author_first_battle_r12 as a
import finalize_first_battle_r12 as final
from preview_first_battle_r12 import angel_pose
b=a.b;eva=a.eva;UNIT=a.UNIT;OUT=b.ROOT/'artifacts/world_refinement_r14'
START=489;END=558
PARTS=[n for n in a.surface.MESH if n not in ['cannon','knife','lance','n2','entry_plug']]


def planted_knee(p,side,goal,root,sign):
 hip=p.point('leg_'+side);d=goal-hip;distance=np.linalg.norm(d);d/=distance
 la=np.linalg.norm(eva.K[side]-eva.P['leg_'+side]);lb=np.linalg.norm(eva.P['foot_'+side]-eva.K[side]);distance=np.clip(distance,abs(la-lb)+.01,la+lb-.01);along=(la*la-lb*lb+distance*distance)/(2*distance);height=np.sqrt(max(.001,la*la-along*along));centre=hip+d*along
 up=np.array([0.,1,0])-d*d[1];up/=max(1e-6,np.linalg.norm(up));horizontal=np.cross(d,up)
 if horizontal@np.array([-sign,0.,0])<0:horizontal=-horizontal
 beta=np.clip(((4.5-root[1])/UNIT-centre[1])/height/max(1e-5,up[1]),-.98,.98)
 return up*beta+horizontal*np.sqrt(1-beta*beta)

def armour(p,hr):
 return {n:a.surface.vertices(p,n)*a.MIRROR*UNIT+hr for n in PARTS}


def envelope(points,equations,axis,gap=.3,soft=False):
 """Continuous radial support of the complete measured performance envelope.

 This prevents an inside-body closest-point projection from switching sides of
 a moving arm. Every authored path stays on the same exterior winding route.
 """
 result=points.copy();direction=result-np.asarray(axis);direction[:,1]=0;length=np.linalg.norm(direction,axis=1);direction/=np.maximum(length,1e-7)[:,None]
 origins=np.tile(axis,(len(points),1)).astype(float);origins[:,1]=points[:,1]
 denominator=direction@equations[:,:3].T;offset=origins@equations[:,:3].T+equations[:,3]
 upper=np.divide(-offset,denominator,out=np.full_like(denominator,np.inf),where=denominator>1e-7).min(1)
 lower=np.divide(-offset,denominator,out=np.full_like(denominator,-np.inf),where=denominator<-1e-7).max(1)
 intersects=(lower<=upper)&(upper>=0)&np.isfinite(upper)&(length>1e-7)
 required=upper+gap
 # A hard clamp collapses the inner and outer skin layers onto the same radius,
 # causing zero-thickness folds and native depth flicker. This strictly monotone
 # barrier retains radial thickness while remaining outside the armour envelope.
 difference=np.where(intersects,length-required,0);rounded=required+3*np.logaddexp(0,difference/3) if soft else np.maximum(length,required)
 desired=np.where(intersects,rounded,length);result+=direction*(desired-length)[:,None]
 inside=np.max(result@equations[:,:3].T+equations[:,3],axis=1)
 return result,dict(corrected=int((desired>length+.001).sum()),remaining_in_hulls=int((inside<-.015).sum()),worst_depth=float(inside.min()),max_correction=float(np.max(desired-length)))

def curve_surface(rest,side,limb,centre):
 """Carry the original limb cross-section along a continuous wrapping centreline."""
 P=b.ANGEL.P;names=([f'arm_{side}',f'forearm_{side}',f'hand_{side}'] if limb=='arm' else [f'leg_{side}',f'shin_{side}',f'foot_{side}'])
 joints=np.array([P[n] for n in names]);segments=joints[1:]-joints[:-1];length=np.linalg.norm(segments,axis=1);cum=np.r_[0,np.cumsum(length)]
 ts=[];offsets=[];dist=[]
 for k in range(2):
  raw=((rest-joints[k])@segments[k])/(length[k]**2);u=np.clip(raw,0,1);anchor=joints[k]+u[:,None]*segments[k];dist.append(np.sum((rest-anchor)**2,1));ts.append((cum[k]+u*length[k])/cum[-1]);offsets.append(rest-anchor)
 choose=np.argmin(dist,axis=0);t=np.choose(choose,ts);off=np.where(choose[:,None]==0,offsets[0],offsets[1]);sign=-1 if side=='l' else 1
 if limb=='arm':
  keys=np.array([[sign*14,12,7],[sign*20,7,0],[sign*15,3,-13],[sign*7,2,-17]],float)
 else:keys=np.array([[sign*9,-9,8],[sign*16,-14,1],[sign*13,-17,-9],[sign*5,-18,-13]],float)
 spline=CubicSpline([0,.32,.7,1],keys,axis=0);anchor=spline(t);tangent=spline(t,1);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
 radial=np.c_[anchor[:,0],np.zeros(len(anchor)),anchor[:,2]];radial-=tangent*np.sum(radial*tangent,axis=1)[:,None];radial/=np.maximum(1e-5,np.linalg.norm(radial,axis=1))[:,None];binormal=np.cross(tangent,radial)
 # Rest X is lateral thickness. The other cross-axis is perpendicular to its chain.
 rest_tangent=segments[choose]/length[choose,None];rest_radial=np.tile([sign,0.,0.],(len(rest),1));rest_radial-=rest_tangent*np.sum(rest_radial*rest_tangent,axis=1)[:,None];rest_radial/=np.linalg.norm(rest_radial,axis=1)[:,None];other=np.cross(rest_tangent,rest_radial)
 x=np.sum(off*rest_radial,axis=1)*UNIT*.72;y=np.sum(off*other,axis=1)*UNIT*.72
 return centre+anchor+radial*x[:,None]+binormal*y[:,None]

def target_surface(p,hr):
 rest=b.ANGEL.vertices;centre=b.hero_world(p,hr,'torso_upper')+[0,-2,1]
 # Torso becomes the broad front mantle. No vertex is mapped to the EVA centre.
 theta=np.arctan2(rest[:,0],-rest[:,2]);v=np.clip((rest[:,1]-116)/65,-.94,.94);rad=np.sqrt(1-v*v)
 torso=centre+np.c_[17*rad*np.sin(theta),15*v,14*rad*np.cos(theta)]
 core_distance=np.linalg.norm((rest-b.ANGEL.core)*[1,1,.7],axis=1)
 core_weight=np.clip((23-core_distance)/9,0,1);core_weight=core_weight*core_weight*(3-2*core_weight)
 rigid_core=centre+[-7,13,14]+(rest-b.ANGEL.core)*UNIT*[-1,1,-1]
 torso=torso*(1-core_weight[:,None])+rigid_core*core_weight[:,None]
 head_origin=b.ANGEL.P['head'];head=centre+[-11,17,10]+(rest-head_origin)*UNIT*.85
 targets={'root':torso,'torso_lower':torso,'torso_upper':torso,'neck':head,'head':head}
 for side in ['l','r']:
  ar=curve_surface(rest,side,'arm',centre);leg=curve_surface(rest,side,'leg',centre)
  for n in ['arm','forearm','hand']:targets[n+'_'+side]=ar
  for n in ['leg','shin','foot']:targets[n+'_'+side]=leg
 result=np.zeros_like(rest)
 for j,n in enumerate(b.ANGEL.names):
  weight=np.sum(np.where(b.ANGEL.ids==j,b.ANGEL.weights,0),1);result+=targets[n]*weight[:,None]
 return result,centre

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--install',action='store_true');args=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
 if args.install:
  report=json.loads((OUT/'wrap_audit.json').read_text());assert report['passed']
  contact_source=json.loads((OUT/'triangle_contacts_source.json').read_text());contacts=json.loads((OUT/'triangle_contacts.json').read_text())
  assert contact_source['clip']==report['hashes']['first_battle_r14.json'] and contact_source['surface']==report['hashes']['sachiel_wrap_r14.bin']
  assert len(contacts)==70 and all(row['pairs']==0 for row in contacts),'Actual cross-actor triangles must clear before installation'
  dest=b.ROOT/'run/projectseele-local-maps'
  for name in ['sachiel_wrap_r14.bin','first_battle_r14.json']:
   source=OUT/name;assert hashlib.sha256(source.read_bytes()).hexdigest()==report['hashes'][name];temporary=dest/(name+'.tmp');shutil.copy2(source,temporary);temporary.replace(dest/name)
  print('Private R14 motion and surface cache installed');return
 data=json.loads((b.ROOT/'run/projectseele-local-maps/first_battle_r12.json').read_text());heroes=[eva.decode(f,data['eva']['bones']) for f in data['eva']['frames']];angels=[angel_pose(f,data['angel']['bones']) for f in data['angel']['frames']]
 # The captured kneeling support had both feet on the same side of the hips.
 # Widen the planted base during the mount, keeping the recorded torso and strikes.
 for i in range(351,START+1):
  t=i/30;original=heroes[i];p=a.clone(original);root=np.array(data['eva']['root_blocks'][i]);weight=b.smooth((t-11.7)/.7)
  hips=(b.hero_world(p,root,'leg_l')+b.hero_world(p,root,'leg_r'))/2
  for side,sign in [('l',1),('r',-1)]:
   current=b.hero_world(p,root,'foot_'+side);goal=current.copy();goal[0]=hips[0]+sign*11.2
   q=R.from_matrix(p.matrix('foot_'+side)[:3,:3]);goal[1]=-np.min(q.apply(eva.feet[side])[:,1])*UNIT
   goal=(goal-root)*a.MIRROR/UNIT;a.retarget.solve_ik(p,'leg_'+side,'shin_'+side,'foot_'+side,eva.K[side],goal,planted_knee(p,side,goal,root,sign),q)
  heroes[i]=a.mix_pose(original,p,weight)
  minimum=a.surface.floor(heroes[i],['leg_l','leg_r','shin_l','shin_r','foot_l','foot_r'])*UNIT+root[1]
  if minimum<.02:heroes[i].setp('root',heroes[i].p['root']+[0,(.02-minimum)/UNIT,0])
  if t>16.05:
   p=heroes[i];q=R.from_matrix(p.matrix('hand_l')[:3,:3]);shoulder=b.hero_world(p,root,'arm_l');current=b.hero_world(p,root,'hand_l');goal=b.mix(current,shoulder+[5,-7,5],b.smooth((t-16.05)/.25));a.retarget.solve_ik(p,'arm_l','forearm_l','hand_l',eva.E['l'],(goal-root)*a.MIRROR/UNIT,np.array([-1,0,-1]),q)
 h0=a.clone(heroes[START]);hstand=a.clone(heroes[558]);hr=np.array(data['eva']['root_blocks'][START]);ar=np.array(data['angel']['root_blocks'][START]);a0=a.clone(angels[START],True)
 feet={s:b.hero_world(h0,hr,'foot_'+s) for s in ['l','r']};hand0={s:b.hero_world(h0,hr,'hand_'+s) for s in ['l','r']}
 raw=json.loads((eva.PACK/'mesh/sachiel.mesh.json').read_text());av=np.array(raw['parts']['root']['vertices']).reshape(-1,8);_,inverse=np.unique(np.round(av[:,:3]*[-1,1,1],6),axis=0,return_inverse=True)
 faces=inverse.reshape(-1,3);edges=np.vstack([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]);edges=np.vstack([edges,edges[:,::-1]]);edges=np.unique(edges,axis=0)
 adjacency=csr_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(b.ANGEL.vertices),len(b.ANGEL.vertices)));adjacency=adjacency.multiply(1/np.maximum(1,np.asarray(adjacency.sum(1)).ravel())[:,None]).tocsr()
 preserve=np.clip((np.linalg.norm(b.ANGEL.vertices-b.ANGEL.core,axis=1)-17)/12,0,1)*np.clip((171-b.ANGEL.vertices[:,1])/12,0,1)
 source=a0.skin()*UNIT+ar;cache=[];reports=[];centres=[];groups_all=[];centre0=np.array([hr[0],0,hr[2]]);previous_delta=None
 fixed_target,_=target_surface(a.mix_pose(h0,hstand,.78),hr)
 for iteration in range(9):
  fixed_target+=.42*preserve[:,None]*(adjacency@fixed_target-fixed_target)
  fixed_target-=.43*preserve[:,None]*(adjacency@fixed_target-fixed_target)
 for i in range(START,END+1):
  t=i/30;reach=b.smooth((t-16.3)/.72);wind=b.smooth((t-16.85)/1.25);pull=b.smooth((t-17.08)/1.25)
  h=a.mix_pose(h0,hstand,.78*pull)
  # Broad braced feet stay planted while the hips rise; strain begins after first contact.
  for s in ['l','r']:
   q0=R.from_matrix(h0.matrix('foot_'+s)[:3,:3]);q1=R.from_matrix(hstand.matrix('foot_'+s)[:3,:3]);q=b.qmix(q0,q1,pull)
   planted=feet[s].copy();wide=hr+([9,0,4] if s=='l' else [-9,0,-1]);step=b.smooth((t-16.65)/1.05)
   goal=b.mix(planted,wide,step);goal[1]=-np.min(q.apply(eva.feet[s])[:,1])*UNIT+1.8*np.sin(np.pi*step)
   goal=(goal-hr)*a.MIRROR/UNIT;pole=h.point('leg_'+s,eva.K[s])-h.point('leg_'+s);a.retarget.solve_ik(h,'leg_'+s,'shin_'+s,'foot_'+s,eva.K[s],goal,pole,q)
  strain=np.sin((t-17.1)*7)*.045*wind;h.setq('torso_upper',h.q['torso_upper']*R.from_euler('xyz',[-.09*pull,0,strain]));h.setq('head',h.q['head']*R.from_euler('x',-.10*wind))
  for s,sgn in [('l',1),('r',-1)]:
   shoulder=b.hero_world(h,hr,'arm_'+s);goal=b.mix(hand0[s],shoulder+[-sgn*4,-13,6],pull);local=(goal-hr)*a.MIRROR/UNIT;q=R.from_matrix(h.matrix('hand_'+s)[:3,:3]);a.retarget.solve_ik(h,'arm_'+s,'forearm_'+s,'hand_'+s,eva.E[s],local,np.array([-sgn,0,-1]),q)
  heroes[i]=h;target=fixed_target;centre=b.hero_world(h,hr,'torso_upper')+[0,-2,1];centres.append(centre)
  weights=np.zeros(len(source))
  for j,n in enumerate(b.ANGEL.names):
   # Distal limbs establish the embrace before the torso lifts into it.
   distal=n.startswith(('forearm_','hand_'));limb=n.startswith(('arm_','leg_','shin_','foot_'))
   w=.42*reach+.58*wind if distal else .22*reach+.78*wind if limb else pull
   influence=np.sum(np.where(b.ANGEL.ids==j,b.ANGEL.weights,0),1);weights+=influence*w
  # Tissue winds along an exterior arc. A Cartesian blend to the far side would
  # pass through the EVA's chest even with perfectly smooth skeletal quaternions.
  v0=source-centre0;v1=target-centre0;angle0=np.arctan2(v0[:,0],v0[:,2]);angle1=np.arctan2(v1[:,0],v1[:,2]);delta=(angle1-angle0+np.pi)%(2*np.pi)-np.pi
  if previous_delta is not None:delta=previous_delta+(delta-previous_delta+np.pi)%(2*np.pi)-np.pi
  previous_delta=delta.copy()
  angle=angle0+delta*weights;radius=np.linalg.norm(v0[:,[0,2]],axis=1)*(1-weights)+np.linalg.norm(v1[:,[0,2]],axis=1)*weights+5*np.sin(np.pi*weights)
  result=centre0+np.c_[radius*np.sin(angle),v0[:,1]*(1-weights)+v1[:,1]*weights+3*np.sin(np.pi*weights),radius*np.cos(angle)]
  groups=armour(h,hr);groups_all.append(groups)
  result[:,1]=np.maximum(result[:,1],.02)
  cache.append(result);angels[i]=a.clone(a0,True);data['angel']['root_blocks'][i]=ar.tolist()
 for i in range(END+1,583):
  heroes[i]=a.mix_pose(heroes[END],heroes[583],b.smooth((i-END)/(583-END)));angels[i]=a.clone(a0,True);data['angel']['root_blocks'][i]=ar.tolist()
  minimum=a.surface.floor(heroes[i],['leg_l','leg_r','shin_l','shin_r','foot_l','foot_r'])*UNIT+hr[1]
  if minimum<.02:heroes[i].setp('root',heroes[i].p['root']+[0,(.02-minimum)/UNIT,0])
 # Update every shared socket, optical, core and camera curve after the paired edit.
 final.recompute(data,heroes,angels)
 cache=np.array(cache,dtype=np.float64)
 # Use the union of the actual armour over the whole short performance, so the
 # constraint itself cannot pop between moving body-part surfaces.
 envelope_vertices=np.vstack([np.vstack(list(groups.values())) for groups in groups_all]);equations=ConvexHull(envelope_vertices).equations
 for k in range(len(cache)):
  corrected,_=envelope(cache[k],equations,centre0,soft=True);cache[k]=b.mix(cache[k],corrected,b.smooth(k/9))
 filtered=gaussian_filter1d(cache,1.05,axis=0,mode='nearest');fade=np.minimum(np.arange(len(cache))/4,(len(cache)-1-np.arange(len(cache)))/4).clip(0,1)
 cache=cache*(1-fade[:,None,None])+filtered*fade[:,None,None]
 reports=[]
 for k in range(len(cache)):
  corrected,report=envelope(cache[k],equations,centre0);weight=b.smooth(k/9);cache[k]=b.mix(cache[k],corrected,weight);cache[k,:,1]=np.maximum(cache[k,:,1],.02);reports.append(dict(frame=k+START,**report))
 for k,i in enumerate(range(START,END+1)):
  # The core marker follows the actual skinned red core during metamorphosis.
  coreid=np.argmin(np.sum((b.ANGEL.vertices-b.ANGEL.core)**2,1));eyeid=np.argmin(np.sum((b.ANGEL.vertices-b.ANGEL.eye)**2,1));data['angel']['core_blocks'][i]=cache[k,coreid].round(6).tolist();data['angel']['eye_blocks'][i]=cache[k,eyeid].round(6).tolist()
  for side in ['l','r']:
   ident=np.argmin(np.sum((b.ANGEL.vertices-b.ANGEL.P['hand_'+side])**2,1));data['angel']['hand_'+side+'_blocks'][i]=cache[k,ident].round(6).tolist()
  camera_weight=b.smooth(k/13.5)
  data['camera']['position'][i]=b.mix(data['camera']['position'][i],b.curve([(16.3,[67,51,44]),(17.35,[71,45,77]),(18.6,[67,45,89])],i/30),camera_weight).tolist();data['camera']['target'][i]=b.mix(data['camera']['target'][i],centres[k]+[0,3,0],camera_weight).tolist()
 for i in range(END+1,583):
  w=b.smooth((i-END)/(583-END));data['camera']['position'][i]=b.mix(data['camera']['position'][END],data['camera']['position'][i],w).tolist();data['camera']['target'][i]=b.mix(data['camera']['target'][END],data['camera']['target'][i],w).tolist()
 cache,faces,uv,subdivision=curved_subdivide(cache,inverse.reshape(-1,3),av[:,3:5].reshape(-1,3,2),centre0,envelope,equations)
 # Binary stores unique vertices; a topology hash guards UV/mesh-order mismatches.
 binary=OUT/'sachiel_wrap_r14.bin';mesh_hash=hashlib.sha256((eva.PACK/'mesh/sachiel.mesh.json').read_bytes()).digest()
 with binary.open('wb') as f:
  f.write(b'SW14');f.write(struct.pack('>6i',START,len(cache),30,cache.shape[1],faces.size,len(inverse)));f.write(mesh_hash);f.write(np.asarray(faces.ravel(),dtype='>i4').tobytes());f.write(np.asarray(uv.reshape(-1,2),dtype='>f4').tobytes());f.write(np.asarray(cache,dtype='>f4').tobytes())
 data['surface_deformation_r14']=hashlib.sha256(binary.read_bytes()).hexdigest();data['reference']='R14 TV-inspired nonhuman reach / winding / mantle enclosure, conservative actual-armour clearance; R12 human performance preserved before 16.3 s. Private capture and geometry sources.'
 movie=OUT/'first_battle_r14.json';movie.write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
 speeds=np.linalg.norm(np.diff(cache,axis=0),axis=2);report=dict(passed=bool(all(r['remaining_in_hulls']==0 for r in reports[10:]) and speeds.max()<8),start=START,end=END,frames=len(cache),unique_vertices=cache.shape[1],subdivision=subdivision,max_step_blocks=float(speeds.max()),max_acceleration_blocks=float(np.linalg.norm(np.diff(cache,n=2,axis=0),axis=2).max()),p99_step_blocks=float(np.quantile(speeds,.99)),conservative_armour_clearance=reports,hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [binary,movie]})
 (OUT/'wrap_audit.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k!='conservative_armour_clearance'},flush=True)
if __name__=='__main__':main()
