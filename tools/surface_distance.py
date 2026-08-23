from __future__ import annotations
import numpy as np
from scipy.spatial import cKDTree


def closest_point_triangle(p, a, b, c):
    # Christer Ericson, Real-Time Collision Detection
    ab=b-a; ac=c-a; ap=p-a
    d1=np.dot(ab,ap); d2=np.dot(ac,ap)
    if d1<=0 and d2<=0:return a
    bp=p-b; d3=np.dot(ab,bp); d4=np.dot(ac,bp)
    if d3>=0 and d4<=d3:return b
    vc=d1*d4-d3*d2
    if vc<=0 and d1>=0 and d3<=0:
        v=d1/(d1-d3);return a+v*ab
    cp=p-c; d5=np.dot(ab,cp); d6=np.dot(ac,cp)
    if d6>=0 and d5<=d6:return c
    vb=d5*d2-d1*d6
    if vb<=0 and d2>=0 and d6<=0:
        w=d2/(d2-d6);return a+w*ac
    va=d3*d6-d5*d4
    if va<=0 and (d4-d3)>=0 and (d5-d6)>=0:
        w=(d4-d3)/((d4-d3)+(d5-d6));return b+w*(c-b)
    denom=1.0/(va+vb+vc);v=vb*denom;w=vc*denom
    return a+ab*v+ac*w

class TriangleSurfaceIndex:
    def __init__(self, triangles:np.ndarray):
        self.tri=np.asarray(triangles,float).reshape(-1,3,3)
        a,b,c=self.tri[:,0],self.tri[:,1],self.tri[:,2]
        samples=np.concatenate([a,b,c,(a+b)*.5,(b+c)*.5,(c+a)*.5,(a+b+c)/3],axis=0)
        ids=np.tile(np.arange(len(self.tri)),7)
        self.tree=cKDTree(samples)
        self.sample_ids=ids
    def query_one(self,p,k=48):
        kk=min(k,len(self.sample_ids)); _,ix=self.tree.query(np.asarray(p,float),k=kk)
        ix=np.atleast_1d(ix); ids=np.unique(self.sample_ids[ix])
        bestd=1e99;best=None;besti=-1
        for i in ids:
            q=closest_point_triangle(np.asarray(p,float),*self.tri[i])
            d=float(np.linalg.norm(q-p))
            if d<bestd:bestd=d;best=q;besti=int(i)
        return bestd,best,besti
    def query(self,points,k=48):
        ds=[];qs=[];ids=[]
        for p in np.asarray(points,float):
            d,q,i=self.query_one(p,k);ds.append(d);qs.append(q);ids.append(i)
        return np.asarray(ds),np.asarray(qs),np.asarray(ids)
