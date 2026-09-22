"""Preserve generated silhouettes/UVs and assign an independent anatomical UN rig.

Surface geodesics separate hands from nearby thighs; no X/Y threshold can assign
a knee panel to an arm. Narrow seam skins remain continuous under articulation.
"""
from pathlib import Path
from collections import defaultdict
import argparse,copy,json,math,shutil
import numpy as np
from scipy import sparse
from scipy.spatial import cKDTree
from scipy.sparse.csgraph import dijkstra,connected_components
import build_original_eva_prototype_r07 as m
import refine_un_hands_optics_r23 as hands
import fit_un_dorsal_r21 as dorsal

ROOT=m.ROOT;OUT=ROOT/'artifacts/facility_r30/models';OLD=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele'
PALETTE={'00':['#171f27','#070d12','#65747c','#35424b','#bb954a','#030609','#e2bd70','#98c86c','#b82431','#e5e9e7','#405246','#66bde1'],
         '01':['#66785d','#101720','#515e89','#344a39','#8b9c7c','#03080e','#b9a16d','#ff982b','#c92332','#e5e9df','#303c65','#70cdec']}

def setup_rig(unit,raw):
    geo=json.loads((OLD/'geo/eva_prototype.geo.json').read_text());bones=[copy.deepcopy(b) for b in geo['minecraft:geometry'][0]['bones'] if not b['name'].startswith(('r21_join_','dorsal_','r30_'))]
    named={b['name']:b for b in bones};large=unit=='01'
    points={'root':(0,.18801,0),'torso_lower':(0,91.15596,0),'torso_upper':(0,125.26894,0),'head':(0,164.5,0),'neck':(0,164.5,0),'aim_pitch':(0,155,0)}
    for side,s in [('l',-1),('r',1)]:
        for n,p in {'arm':(s*(34 if large else 26.5),155,0),'forearm':(s*(36.7 if large else 29.5),132 if large else 136,0),
                    'wrist':(s*(45.3 if large else 34.2),100,0),'hand':(s*(45.3 if large else 34.2),100,0),
                    'leg':(s*(15.5 if large else 12.4),114,0),'shin':(s*(25.5 if large else 20),65,0),
                    'ankle':(s*(35 if large else 26.5),18.5,0),'foot':(s*(35 if large else 26.5),18.5,0),
                    'clavicle':(0,155,0)}.items():points[n+'_'+side]=p
        top=raw[(raw[:,1]>175)&(s*raw[:,0]>18)];points['pylon_'+side]=(float(np.median(top[:,0])),156,float(np.median(top[:,2])))
        wrist=np.array(points['hand_'+side]);inside=-s
        for digit,x,length in [('index',3.2,11.3),('middle',1.08,12.5),('ring',-1.1,11.7),('little',-3.25,9.7)]:
            base=wrist+np.array([inside*x,-7.6,-.1]);middle=base+np.array([0,-length*.44,0]);tip=middle+np.array([0,-length*.32,0])
            for name,p in [('finger_'+digit+'_axis_'+side,base),('finger_'+digit+'_'+side,base),('finger_'+digit+'_tip_'+side,middle),('finger_'+digit+'_distal_'+side,tip)]:points[name]=p
            named['finger_'+digit+'_axis_'+side]['rotation']=[0,-90,0]
            for suffix in ('','_tip','_distal'):named['finger_'+digit+suffix+'_'+side].pop('rotation',None)
        base=wrist+np.array([inside*4.8,-3.2,-.3]);direction=np.array([inside*.68,-.74,0]);direction/=np.linalg.norm(direction)
        points['finger_thumb_'+side]=base;points['finger_thumb_tip_'+side]=base+direction*3.6
        axis='finger_thumb_axis_'+side;points[axis]=base;named[axis]={'name':axis,'parent':'hand_'+side,'pivot':[0,0,0],'rotation':[0,-90,inside*43]};bones.append(named[axis]);named['finger_thumb_'+side]['parent']=axis;named['finger_thumb_'+side].pop('rotation',None);named['finger_thumb_tip_'+side].pop('rotation',None)
        for marker,parent,p in [('r30_elbow_socket_'+side,'forearm_'+side,points['forearm_'+side]),('r30_knee_socket_'+side,'shin_'+side,points['shin_'+side]),('r30_hand_frame_'+side,'hand_'+side,wrist)]:
            named[marker]={'name':marker,'parent':parent,'pivot':[0,0,0]};bones.append(named[marker]);points[marker]=p
    for name,p in points.items():named[name]['pivot']=(np.asarray(p)*[-1,1,1]).tolist()
    # Weapon geometry keeps its canonical mesh pivot. Runtime grip calibration
    # maps the new hand frame to that shared weapon, rather than shifting its mesh.
    m.B={b['name']:{**b,'parent':b.get('parent'),'bindRotationDegrees':b.get('rotation',[0,0,0])} for b in bones};m.P={n:np.asarray(b['pivot'])*[-1,1,1] for n,b in m.B.items()};m.BIND.clear();m.PARTS.clear();m.PREVIEW.clear();m.COLOURS=PALETTE[unit]
    geo['minecraft:geometry'][0]['bones']=bones
    return geo,bones

def geodesic_labels(raw,faces,unit):
    edges=np.vstack([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]);edges=np.sort(edges,axis=1);edges=np.unique(edges,axis=0)
    lengths=np.linalg.norm(raw[edges[:,0]]-raw[edges[:,1]],axis=1);pairs=np.vstack([edges,edges[:,::-1]]);cost=sparse.coo_matrix((np.r_[lengths,lengths],(pairs[:,0],pairs[:,1])),shape=(len(raw),len(raw))).tocsr()
    count,components=connected_components(cost);sizes=np.bincount(components);keep=sizes[components]>=100
    tree=cKDTree(raw);seeds={};segments={}
    def seed(name,points):
        for point in points:
            index=int(tree.query(point)[1])
            if keep[index]:seeds.setdefault(index,name)
    seed('torso_lower',[(x,y,z) for x in (-8,0,8) for y in (100,114,126) for z in (-7,7)])
    seed('torso_upper',[(x,y,z) for x in (-16,-8,0,8,16) for y in (138,149,157) for z in (-11,10)])
    seed('head',[(x,y,z) for x in (-4,0,4) for y in (170,180,188) for z in (-8,6)])
    for side in ('l','r'):
        p=m.P['pylon_'+side];seed('pylon_'+side,[(p[0],y,p[2]) for y in (154,164,177,188)])
        for bone,start,end in [('arm','arm','forearm'),('forearm','forearm','hand'),('leg','leg','shin'),('shin','shin','foot')]:
            a,b=m.P[start+'_'+side],m.P[end+'_'+side];segments[bone+'_'+side]=(a,b)
            seed(bone+'_'+side,[a*(1-t)+b*t+np.array([0,0,d]) for t in (.18,.40,.62,.82) for d in (-5,5)])
        p=m.P['hand_'+side];seed('hand_'+side,[p+np.array([x,y,z]) for x in (-2,2) for y in (-4,-11,-18) for z in (-1,3)])
        p=m.P['foot_'+side];seed('foot_'+side,[p+np.array([x,y,z]) for x in (-2,2) for y in (-8,-14) for z in (-11,-3,5)])
    distance,pred,source=dijkstra(cost,indices=np.array(list(seeds)),min_only=True,return_predecessors=True,directed=False)
    names=sorted(set(seeds.values()));index={n:i for i,n in enumerate(names)};labels=np.full(len(raw),-1,int)
    for start,name in seeds.items():labels[source==start]=index[name]
    unassigned=keep&(labels<0)
    if unassigned.any():
        valid=np.flatnonzero(labels>=0);near=cKDTree(raw[valid]).query(raw[unassigned])[1];labels[unassigned]=labels[valid[near]]
    adjacency=cost.copy();adjacency.data[:]=1;degree=np.maximum(1,np.asarray(adjacency.sum(1)).ravel())
    cross=edges[labels[edges[:,0]]!=labels[edges[:,1]]];boundary=np.zeros(len(raw),bool);boundary[cross.ravel()]=True;near=boundary.copy()
    for _ in range(5):near|=adjacency@near>0
    weights=np.zeros((len(raw),len(names)),np.float32);valid=labels>=0;weights[np.flatnonzero(valid),labels[valid]]=1
    for _ in range(8):weights[near]=weights[near]*.4+((adjacency@weights)/degree[:,None])[near]*.6
    weights/=np.maximum(1e-12,weights.sum(1,keepdims=True));dominant=weights.argmax(1);rigid=weights[np.arange(len(raw)),dominant]>.9995;weights[rigid]=0;weights[np.flatnonzero(rigid),dominant[rigid]]=1
    smooth=raw.copy()
    for coefficient in [.38,-.395]*6:smooth+=coefficient*((adjacency@smooth)/degree[:,None]-smooth)
    smooth[~keep]=raw[~keep]
    return smooth,weights,names,keep,{'connected_components':int(count),'removed_small_component_vertices':int((~keep).sum()),'max_smoothing_offset':float(np.linalg.norm(smooth-raw,axis=1).max()),'segmentation':'Multi-source surface geodesics from anatomical seeds; no whole-leg X threshold'}

def make_hand(side,unit):
    p=m.P['hand_'+side];axis=m.P['forearm_'+side]-p;axis/=np.linalg.norm(axis);flex=1 if unit=='00' else 2;trim=4 if unit=='00' else 3;back=np.array([0.,0.,1.]);basis=np.column_stack([[1.,0,0],[0,-1.,0],[0,0,-1.]])
    m.loft('wrist_'+side,[p+axis*5.8,p+axis*1.4,p-axis*.8],[2.9,3.15,2.9],[2.5,2.7,2.5],flex,48)
    centres=[p+np.array([0,-y,0]) for y in (-.5,.7,3.2,5.8,7.8)]
    hands.tube('hand_'+side,centres,[2.45,3.0,4.45,4.8,4.7],[1.9,2.,1.75,1.5,1.15],flex,basis,48)
    for digit in ('index','middle','ring','little','thumb'):
        names=['finger_'+digit+'_'+side,'finger_'+digit+'_tip_'+side]
        if digit!='thumb':names.append('finger_'+digit+'_distal_'+side)
        points=[m.P[n] for n in names];points.append(points[-1]+(points[-1]-points[-2])*(.75 if digit!='thumb' else .85))
        radius=.88 if digit=='little' else 1.12 if digit=='thumb' else 1.02
        for i,name in enumerate(names):
            a,b=points[i],points[i+1];v=b-a;length=np.linalg.norm(v);v/=length;r=radius*(1-i*.08)
            m.ellipsoid(name,a,(r,r*.88,r*.94),flex,32,16,v)
            m.loft(name,[a+v*.12,a+v*.65,b-v*.38,b+v*.14],[r*.87,r,r*.83,r*.56],[r*.80,r*.91,r*.77,r*.5],flex,32)
            m.loft(name,[a+v*.7+back*r*.8,(a+b)*.5+back*r*.96,b-v*.55+back*r*.7],[r*.6,r*.78,r*.56],[.15,.28,.14],0,24)
            m.ring(name,a+v*.25,v,r*.78,.09,trim,32)
        if digit!='thumb':
            base=points[0];a=p*.65+base*.35+back*1.6;b=base+back*1.2;m.loft('hand_'+side,[a,(a+b)*.5,b],[.72,1.03,.82],[.16,.29,.15],0,24)
    return {'wrist':p.tolist(),'fingers':5,'phalanges':{'index':3,'middle':3,'ring':3,'little':3,'thumb':2},'curl_axis':'Local Z, shared correctly oriented adapters on both hands','palm_back':[0,0,1]}

def main(unit):
    folder=OUT/('un'+unit);dest=folder/'runtime/assets/projectseele'
    for category in ('mesh','geo','textures/entity','animations'):(dest/category).mkdir(parents=True,exist_ok=True)
    with np.load(ROOT/'artifacts/facility_r30/lux3d'/('un'+unit)/'geometry.npz') as d:raw=d['vertices'];faces=d['triangles'];uv=d['uv'];colors=d['colors']
    _,first,inverse=np.unique(np.round(raw,5),axis=0,return_index=True,return_inverse=True);raw=raw[first];faces=inverse[faces]
    geo,bones=setup_rig(unit,raw);posed,weights,names,keep,report=geodesic_labels(raw,faces,unit);triangles=posed[faces]
    face_normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);valid=(np.linalg.norm(face_normals,axis=1)>1e-8)&keep[faces].all(1)
    normals=np.zeros_like(posed)
    for c in range(3):np.add.at(normals,faces[:,c],face_normals)
    normals/=np.maximum(1e-10,np.linalg.norm(normals,axis=1,keepdims=True))
    hand_indices=[i for i,n in enumerate(names) if n.startswith('hand_')];valid&=weights[faces][:,:,hand_indices].sum((1,2))<.06
    groups=defaultdict(list);skins={};parts={}
    for i in np.flatnonzero(valid):
        w=weights[faces[i]];primary=int(w.sum(0).argmax());bone=names[primary]
        if np.min(w[:,primary])<.9995:
            part='r21_join_'+bone
            if part not in m.B:
                b={'name':part,'parent':bone,'pivot':m.B[bone]['pivot'][:],'bindRotationDegrees':[0,0,0]};m.B[part]=b;m.P[part]=m.P[bone].copy();bones.append({'name':part,'parent':bone,'pivot':b['pivot']});skins[part]={'influences':{n:[] for n in names}}
            for j,n in enumerate(names):skins[part]['influences'][n].extend(w[:,j].tolist())
        else:part=bone
        groups[part].append(i)
    for bone,selected in groups.items():
        ids=np.asarray(selected);v=triangles[ids];inv=np.linalg.inv(m.bind(bone));local=(np.concatenate([v,np.ones((*v.shape[:2],1))],axis=2)@inv.T)[:,:,:3]*[-1,1,1]-m.B[bone]['pivot'];n=(normals[faces[ids]]@inv[:3,:3].T)*[-1,1,1]
        values=np.empty((len(ids),3,8));values[:,:,:3]=local;values[:,:,3]=uv[ids,:,0]*.9375;values[:,:,4]=1-uv[ids,:,1];values[:,:,5:]=n;parts[bone]={'pivot':m.B[bone]['pivot'],'vertices':np.round(values,6).ravel().tolist()}
    for spec in skins.values():spec['influences']={k:np.round(v,8).tolist() for k,v in spec['influences'].items() if max(v)>0}
    mesh={'format_version':1,'model_height':193.1,'stride':8,'parts':parts,'jointSkins':skins,'r30_palette_region':{'u0':.9375,'width':.0625,'rows':3},'source':'R30 Lux3D source, preserved proportions/UVs, own rig and local mechanical finishing','lux3d_task':'3672326' if unit=='00' else '3672329'}
    hand_report={}
    for side in ('l','r'):
        hands.wrist_cut(mesh,side);hand_report[side]=make_hand(side,unit)
    # Source triangle/projection data remains available for fitting the optics,
    # panel seams, insignia, plug mechanism and articulated jet nozzles.
    np.savez_compressed(folder/'surface.npz',vertices=posed,triangles=faces,valid=valid,weights=weights,bone_names=np.asarray(names),source_uv=uv,source_colors=colors)
    for bone,values in m.PARTS.items():
        data=np.asarray(values).reshape(-1,8);data[:,3]=.9375+data[:,3]*.0625;data[:,4]*=2/3
        old=mesh['parts'].setdefault(bone,{'pivot':m.B[bone]['pivot'],'vertices':[]});before=len(old['vertices'])//8;old['vertices']+=np.round(data,6).ravel().tolist()
        if bone in skins:
            spec=skins[bone];spec['influences'].setdefault(bone,[0.]*before)
            for name,values in spec['influences'].items():values.extend([1. if name==bone else 0.]*len(data))
    mesh['triangleCount']=sum(len(p['vertices'])//24 for p in mesh['parts'].values());mesh['r30_hands']=hand_report;geo['minecraft:geometry'][0]['description'].update(texture_width=4096,texture_height=4096)
    (dest/'mesh/eva_prototype.mesh.json').write_text(json.dumps(mesh,separators=(',',':')));(dest/'geo/eva_prototype.geo.json').write_text(json.dumps(geo,separators=(',',':')))
    for kind in ('mesh','geo'):
        base=folder/'body_base'/kind;base.mkdir(parents=True,exist_ok=True);shutil.copy2(dest/kind/('eva_prototype.'+kind+'.json'),base/('eva_prototype.'+kind+'.json'))
    shutil.copy2(OLD/'animations/eva_prototype.animation.json',dest/'animations/eva_prototype.animation.json')
    report.update(unit=unit,triangles=mesh['triangleCount'],retained_source_triangles=int(valid.sum()),body_proportions_preserved=True,independent_rig=True,source_uv_preserved=True,hands=hand_report,parts=len(parts),bones=len(bones));(folder/'body_build.json').write_text(json.dumps(report,indent=2));(folder/'palette.json').write_text(json.dumps(PALETTE[unit]));print(json.dumps({k:v for k,v in report.items() if k!='hands'}),flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',choices=('00','01'),required=True);main(ap.parse_args().unit)
