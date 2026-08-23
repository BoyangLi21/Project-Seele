from __future__ import annotations
import json, math
from pathlib import Path
from dataclasses import dataclass
from typing import Any
import numpy as np


def T(v):
    m=np.eye(4,dtype=float); m[:3,3]=np.asarray(v,float); return m

def Rx(a):
    c,s=math.cos(a),math.sin(a); return np.array([[1,0,0,0],[0,c,-s,0],[0,s,c,0],[0,0,0,1]],float)
def Ry(a):
    c,s=math.cos(a),math.sin(a); return np.array([[c,0,s,0],[0,1,0,0],[-s,0,c,0],[0,0,0,1]],float)
def Rz(a):
    c,s=math.cos(a),math.sin(a); return np.array([[c,-s,0,0],[s,c,0,0],[0,0,1,0],[0,0,0,1]],float)

def runtime_rotation(json_deg):
    rx,ry,rz=[math.radians(float(x)) for x in json_deg]
    return Rz(rz) @ Ry(-ry) @ Rx(-rx)

def runtime_vec(json_vec):
    x,y,z=map(float,json_vec); return np.array([-x,y,z],float)

def interp_value(v, which='post'):
    if isinstance(v,dict):
        if which in v: return v[which]
        if 'vector' in v: return v['vector']
        if 'post' in v: return v['post']
        if 'pre' in v: return v['pre']
    return v

def sample_channel(ch:Any,t:float,length:float=0.0,loop=False):
    if isinstance(ch,(list,tuple)):
        return np.asarray(ch,float)
    if not isinstance(ch,dict):
        return np.zeros(3)
    items=[]
    for k,v in ch.items():
        try: items.append((float(k),v))
        except Exception: pass
    if not items:
        if 'vector' in ch: return np.asarray(ch['vector'],float)
        return np.zeros(3)
    items.sort(key=lambda x:x[0])
    if loop and length>0:
        t=t%length
    if t<=items[0][0]: return np.asarray(interp_value(items[0][1],'pre'),float)
    if t>=items[-1][0]: return np.asarray(interp_value(items[-1][1],'post'),float)
    for (ta,va),(tb,vb) in zip(items,items[1:]):
        if ta<=t<=tb:
            a=np.asarray(interp_value(va,'post'),float)
            b=np.asarray(interp_value(vb,'pre'),float)
            if tb==ta: return b
            f=(t-ta)/(tb-ta)
            return a*(1-f)+b*f
    return np.asarray(interp_value(items[-1][1],'post'),float)

@dataclass
class Bone:
    name:str
    parent:str|None
    pivot_json:np.ndarray
    static_rotation_json:np.ndarray

class Rig:
    def __init__(self,geo_path,mesh_path,anim_path):
        self.geo_path=Path(geo_path); self.mesh_path=Path(mesh_path); self.anim_path=Path(anim_path)
        geo=json.load(open(geo_path,encoding='utf-8'))['minecraft:geometry'][0]
        self.bones={}
        self.order=[]
        for b in geo['bones']:
            name=b['name']; self.order.append(name)
            self.bones[name]=Bone(name,b.get('parent'),np.asarray(b.get('pivot',[0,0,0]),float),np.asarray(b.get('rotation',[0,0,0]),float))
        self.mesh=json.load(open(mesh_path,encoding='utf-8'))
        self.animations=json.load(open(anim_path,encoding='utf-8'))['animations']
        self.parts={}
        stride=self.mesh['stride']
        for name,p in self.mesh['parts'].items():
            vals=np.asarray(p['vertices'],float).reshape(-1,stride)
            pivot=np.asarray(p['pivot'],float)
            xyz=vals[:,:3]+pivot
            xyz[:,0]*=-1
            self.parts[name]={'vertices':xyz,'uv':vals[:,3:5],'normal':np.column_stack((-vals[:,5],vals[:,6],vals[:,7])),'faces':np.arange(len(xyz)).reshape(-1,3)}

    def sample_animation(self,name,t):
        a=self.animations[name]
        length=float(a.get('animation_length',0) or 0); loop=bool(a.get('loop',False))
        out={}
        for bone,channels in a.get('bones',{}).items():
            state={}
            if 'rotation' in channels: state['rotation']=sample_channel(channels['rotation'],t,length,loop)
            if 'position' in channels: state['position']=sample_channel(channels['position'],t,length,loop)
            if 'scale' in channels: state['scale']=sample_channel(channels['scale'],t,length,loop)
            out[bone]=state
        return out

    def compose(self,layers):
        # layers: [(anim_name,time), ...], later channels overwrite earlier channels
        out={}
        for name,t in layers:
            sample=self.sample_animation(name,t)
            for bone,state in sample.items():
                out.setdefault(bone,{}).update(state)
        return out

    def matrices(self,channels=None, aim_pitch_deg=0.0):
        channels=channels or {}
        mats={}
        for name in self.order:
            b=self.bones[name]
            st=channels.get(name,{})
            pos=runtime_vec(st.get('position',[0,0,0]))
            rot_json=b.static_rotation_json+np.asarray(st.get('rotation',[0,0,0]),float)
            if name=='aim_pitch':
                # renderer setRotX(-pitch radians) runtime, equivalent JSON +pitch for X because loader negates JSON X.
                # Here directly post-multiply runtime X(-pitch).
                pass
            pivot=runtime_vec(b.pivot_json)
            local=T(pos) @ T(pivot) @ runtime_rotation(rot_json)
            if name=='aim_pitch' and aim_pitch_deg:
                local = T(pos) @ T(pivot) @ Rx(math.radians(-aim_pitch_deg)) @ runtime_rotation(rot_json) @ T(-pivot)
            else:
                local = local @ T(-pivot)
            parent=np.eye(4) if b.parent is None else mats[b.parent]
            mats[name]=parent@local
        return mats

    def posed_parts(self,channels=None,include=None,extra_meshes=None,aim_pitch_deg=0.0):
        mats=self.matrices(channels,aim_pitch_deg)
        result={}
        for name,p in self.parts.items():
            if include is not None and name not in include: continue
            V=np.column_stack((p['vertices'],np.ones(len(p['vertices']))))
            result[name]=(mats[name]@V.T).T[:,:3]
        if extra_meshes:
            for label,mesh_path,bone_name in extra_meshes:
                d=json.load(open(mesh_path,encoding='utf-8')); stride=d['stride']
                for part_name,p in d['parts'].items():
                    vals=np.asarray(p['vertices'],float).reshape(-1,stride); pivot=np.asarray(p['pivot'],float)
                    xyz=vals[:,:3]+pivot; xyz[:,0]*=-1
                    V=np.column_stack((xyz,np.ones(len(xyz))))
                    result[f'{label}:{part_name}']=(mats[bone_name]@V.T).T[:,:3]
        return result,mats

    def joint_world(self,channels=None,aim_pitch_deg=0.0):
        mats=self.matrices(channels,aim_pitch_deg)
        out={}
        for name,b in self.bones.items():
            p=np.append(runtime_vec(b.pivot_json),1)
            out[name]=(mats[name]@p)[:3]
        return out
