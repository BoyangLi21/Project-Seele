"""Two-bone IK with an explicit anatomical hinge, rather than a free ball knee.

The visible bind pose may bow sideways. Its two segment vectors therefore do
not define the anatomical flexion axis. The axis is an explicit rig property.
"""
import numpy as np
from scipy.spatial.transform import Rotation as R

def unit(v,fallback=(1,0,0)):
    v=np.asarray(v,float);length=np.linalg.norm(v)
    return v/length if length>1e-9 else np.asarray(fallback,float)

def limits(u,v,axis,maximum_flex=2.60):
    axis=unit(axis);parallel=axis*(axis@v);perpendicular=v-parallel
    a=u@perpendicular;b=u@np.cross(axis,v)
    neutral=np.arctan2(b,a)
    return float(neutral),float(neutral+maximum_flex)

def solve(p,P,upper,lower,end,joint,target,pole,axis,orientation=None):
    origin=p.point(upper);u=joint-P[upper];v=P[end]-joint
    axis=unit(axis);parallel=axis*(axis@v);perpendicular=v-parallel
    a=u@perpendicular;b=u@np.cross(axis,v);c=u@parallel;amp=np.hypot(a,b)
    low,high=limits(u,v,axis);la=np.linalg.norm(u);lb=np.linalg.norm(v)
    maximum=np.sqrt(la*la+lb*lb+2*(amp+c))*.997
    minimum=np.sqrt(max(0,la*la+lb*lb+2*(a*np.cos(high)+b*np.sin(high)+c)))+.001
    direction=unit(np.asarray(target)-origin,(0,-1,0));length=np.clip(np.linalg.norm(np.asarray(target)-origin),minimum,maximum)
    target=origin+direction*length
    desired=(length*length-la*la-lb*lb)/2
    angle=low+np.arccos(np.clip((desired-c)/max(amp,1e-8),-1,1));rotation=R.from_rotvec(axis*angle)
    along=(la*la-lb*lb+length*length)/(2*length)
    bend=unit(np.asarray(pole)-direction*(np.asarray(pole)@direction),(0,0,-1))
    middle=origin+direction*along+bend*np.sqrt(max(0,la*la-along*along))
    wanted_upper=middle-origin;wanted_lower=target-middle;template_lower=rotation.apply(v)
    def frame(first,second):
        y=unit(first);x=unit(np.cross(first,second));return np.column_stack((x,y,np.cross(x,y)))
    world=R.from_matrix(frame(wanted_upper,wanted_lower)@frame(u,template_lower).T)
    p.setq(upper,R.from_matrix(p.parent(upper)[:3,:3]).inv()*world)
    p.setq(lower,rotation);offset=joint-P[lower];p.setp(lower,offset-rotation.apply(offset))
    if orientation is not None:p.setq(end,R.from_matrix(p.parent(end)[:3,:3]).inv()*orientation)
    return {'angle':float(angle),'minimum':low,'maximum':high,'end_error':float(np.linalg.norm(p.point(end)-target))}
