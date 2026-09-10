"""Conforming curved subdivision of the private, UV-preserving wrap performance."""
import numpy as np

def curved_subdivide(cache,faces,uv,axis,enclose,equations):
 records=[]
 for iteration in range(7):
  edges=np.vstack([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]);edges=np.unique(np.sort(edges,axis=1),axis=0)
  pa=cache[:,edges[:,0]];pb=cache[:,edges[:,1]]
  ta=np.unwrap(np.arctan2(pa[:,:,0]-axis[0],pa[:,:,2]-axis[2]),axis=0);tb=np.unwrap(np.arctan2(pb[:,:,0]-axis[0],pb[:,:,2]-axis[2]),axis=0);tb-=np.round((tb[0]-ta[0])/(2*np.pi))[None,:]*2*np.pi
  angular=np.max(np.abs(tb[8:]-ta[8:]),axis=0);length=np.max(np.linalg.norm(pb[8:]-pa[8:],axis=2),axis=0)
  selected=(angular>np.radians(17))|(length>4)
  if iteration>=5:
   bad=np.zeros(len(faces),bool)
   for k in range(10,len(cache)):
    triangle=cache[k,faces];samples=np.concatenate([triangle.mean(1),(triangle[:,0]+triangle[:,1])/2,(triangle[:,1]+triangle[:,2])/2,(triangle[:,2]+triangle[:,0])/2])
    inside=np.max(samples@equations[:,:3].T+equations[:,3],axis=1)<-.01;bad|=inside.reshape(4,-1).any(0)
   wanted=np.unique(np.sort(np.concatenate([faces[bad][:,[0,1]],faces[bad][:,[1,2]],faces[bad][:,[2,0]]]),axis=1),axis=0)
   selected=np.isin(edges[:,0]*cache.shape[1]+edges[:,1],wanted[:,0]*cache.shape[1]+wanted[:,1])
   print('Curved triangle clearance',iteration,'faces',int(bad.sum()),flush=True)
  if not selected.any():break
  edge_ids=np.where(selected)[0];new_edges=edges[selected]
  ra=np.linalg.norm((pa[:,selected]-axis)[...,[0,2]],axis=2);rb=np.linalg.norm((pb[:,selected]-axis)[...,[0,2]],axis=2);theta=(ta[:,selected]+tb[:,selected])/2;radius=(ra+rb)/2
  midpoint=(pa[:,selected]+pb[:,selected])/2;curved=np.stack([axis[0]+radius*np.sin(theta),midpoint[:,:,1],axis[2]+radius*np.cos(theta)],axis=2)
  for k in range(len(cache)):
   w=min(1,k/9);w=w*w*w*(10+w*(-15+6*w));curved[k]=midpoint[k]*(1-w)+curved[k]*w;projected,_=enclose(curved[k],equations,axis,gap=.7);curved[k]=curved[k]*(1-w)+projected*w
  first=cache.shape[1];lookup={tuple(edge):first+i for i,edge in enumerate(new_edges)};cache=np.concatenate([cache,curved],axis=1)
  new_faces=[];new_uv=[]
  for tri,coords in zip(faces,uv):
   a,b,c=map(int,tri);m=[lookup.get(tuple(sorted(edge))) for edge in [(a,b),(b,c),(c,a)]];count=sum(x is not None for x in m)
   if count==0:new_faces.append(tri);new_uv.append(coords);continue
   for _ in range(3):
    if count==3 or count==1 and m[0] is not None or count==2 and m[0] is not None and m[1] is not None:break
    a,b,c=b,c,a;m=m[1:]+m[:1];coords=np.roll(coords,-1,axis=0)
   u,v,w=coords;uvab=(u+v)/2;uvbc=(v+w)/2;uvca=(w+u)/2
   if count==1:parts=[((a,m[0],c),(u,uvab,w)),((m[0],b,c),(uvab,v,w))]
   elif count==2:parts=[((b,m[1],m[0]),(v,uvbc,uvab)),((a,m[0],c),(u,uvab,w)),((m[0],m[1],c),(uvab,uvbc,w))]
   else:parts=[((a,m[0],m[2]),(u,uvab,uvca)),((m[0],b,m[1]),(uvab,v,uvbc)),((m[2],m[1],c),(uvca,uvbc,w)),((m[0],m[1],m[2]),(uvab,uvbc,uvca))]
   for face,tex in parts:new_faces.append(face);new_uv.append(tex)
  faces=np.asarray(new_faces,dtype=np.int32);uv=np.asarray(new_uv)
  records.append(dict(round=iteration,split_edges=len(new_edges),vertices=cache.shape[1],triangles=len(faces)))
  print('Curved topology',records[-1],flush=True)
  if cache.shape[1]>95000:raise RuntimeError('Surface topology budget exceeded')
 return cache,faces,uv,records
