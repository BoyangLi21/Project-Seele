"""Retopologize and bind private Angel test meshes; no third-party outputs enter src/.

Source rest poses are measured explicitly. Weights depend only on rest position,
so duplicated UV seams receive identical deformation.
"""
from pathlib import Path
import json,math,hashlib
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'external-assets/incoming/angels_r10'
PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele';OUT=ROOT/'artifacts/first_battle_world_r10/models'

def obj(path):
    v=[];uv=[];normal=[];faces=[];materials=[];material='';textures={}
    for line in path.read_text(encoding='utf8').splitlines():
        parts=line.split()
        if not parts:continue
        if parts[0]=='v':v.append(list(map(float,parts[1:4])))
        elif parts[0]=='vt':uv.append(list(map(float,parts[1:3])))
        elif parts[0]=='vn':normal.append(list(map(float,parts[1:4])))
        elif parts[0]=='usemtl':material=line[7:].strip()
        elif parts[0]=='f':
            points=[tuple(int(k)-1 for k in q.split('/')) for q in parts[1:]]
            for i in range(1,len(points)-1):faces.append([points[0],points[i],points[i+1]]);materials.append(material)
    for mtl in path.parent.glob('*.mtl'):
        key=''
        for line in mtl.read_text(encoding='utf8').splitlines():
            if line.startswith('newmtl '):key=line[7:].strip()
            elif line.startswith('map_Kd '):textures[key]=path.parent/line[7:].strip()
    return np.array(v),np.array(uv),np.array(normal),faces,materials,textures

def humanoid(name):
    if name=='sachiel':
        joints=dict(root=[0,0,0],torso_lower=[0,7.5,0],torso_upper=[0,11.2,0],neck=[0,13.5,.45],head=[0,14.6,.8],
                    arm=[3.35,14.35,0],forearm=[3.78,10.15,.2],hand=[3.78,10.15,3.55],
                    leg=[1.3,7.3,0],shin=[1.4,3.9,-.32],foot=[1.4,.65,.2])
        tips=dict(head=[0,15.9,1.3],hand=[3.78,10.15,5.35],foot=[1.4,.1,1.4])
    else:
        joints=dict(root=[0,0,0],torso_lower=[0,7.8,0],torso_upper=[0,11.2,0],neck=[0,13.3,.4],head=[0,14.5,1],
                    arm=[3,13.5,0],forearm=[7.2,15.2,.1],hand=[11.5,17.6,.1],
                    leg=[1.5,7.5,0],shin=[2.5,3.7,-.2],foot=[3.2,.5,.6])
        tips=dict(head=[0,16,1.6],hand=[12.9,18.4,.3],foot=[3.4,.1,1.8])
    bones={};segments={}
    def add(n,parent,p,end):bones[n]=dict(parent=parent,pivot=np.array(p,float));segments[n]=(np.array(p,float),np.array(end,float))
    for n,parent,end in [('root',None,'torso_lower'),('torso_lower','root','torso_upper'),('torso_upper','torso_lower','neck'),('neck','torso_upper','head')]:add(n,parent,joints[n],joints[end])
    add('head','neck',joints['head'],tips['head'])
    for side,sign in [('l',1),('r',-1)]:
        def p(n):return np.array(joints.get(n,tips.get(n)),float)*[sign,1,1]
        for part,parent,end in [('arm','torso_upper','forearm'),('forearm','arm_'+side,'hand'),('hand','forearm_'+side,None),('leg','torso_lower','shin'),('shin','leg_'+side,'foot'),('foot','shin_'+side,None)]:
            add(part+'_'+side,parent,p(part),p(end) if end else np.array(tips[part])*[sign,1,1])
    def allowed(point):
        x,y,z=point;side='l' if x>=0 else 'r'
        if y<7.9:return ['torso_lower','leg_'+side,'shin_'+side,'foot_'+side]
        if abs(x)>2.35:return ['torso_upper','arm_'+side,'forearm_'+side,'hand_'+side]
        return ['torso_lower','torso_upper','neck','head']
    return bones,segments,allowed

def creature(name):
    bones={'root':dict(parent=None,pivot=np.zeros(3))};segments={}
    def add(n,parent,p,end):bones[n]=dict(parent=parent,pivot=np.array(p,float));segments[n]=(np.array(p,float),np.array(end,float))
    if name=='shamshel':
        add('body','root',[0,8,0],[0,13.4,0]);add('head','body',[0,13.4,0],[0,16.4,1.7])
        for i in range(4):add('tail_'+str(i),'body' if i==0 else 'tail_'+str(i-1),[0,9-i*2.3,0],[0,6.7-i*2.3,0])
        for side,sign in [('l',1),('r',-1)]:
            ps=np.array([[4.45,13.3,1],[5.15,10.4,2.5],[5.4,7.5,4.5],[5.2,4.6,5.8],[4.9,1.7,6.8]])*[sign,1,1]
            for i in range(4):add('whip_'+side+'_'+str(i),'body' if i==0 else 'whip_'+side+'_'+str(i-1),ps[i],ps[i+1])
        def allowed(p):
            if abs(p[0])>3.0:return ['body']+['whip_'+('l' if p[0]>0 else 'r')+'_'+str(i) for i in range(4)]
            return ['body','head'] if p[1]>10 else ['body']+['tail_'+str(i) for i in range(4)]
    else:
        add('body','root',[0,5.8,0],[0,13,0]);add('head','body',[0,13,0],[0,16.8,-.2])
        for side,sign in [('l',1),('r',-1)]:add('paper_'+side,'body',[3.7*sign,14,-.7],[3.7*sign,9.1,-.7])
        def allowed(p):return ['body','head']
    return bones,segments,allowed

def distance(p,a,b):
    d=b-a;t=np.clip((p-a)@d/max(d@d,1e-8),0,1);return float(np.linalg.norm(p-a-t*d))
def weights(point,bones,segments,allowed):
    candidates=allowed(point);d=np.array([distance(point,*segments[n]) for n in candidates]);w=1/np.maximum(d,.12)**4
    ids=np.argsort(w)[-4:];w=w[ids];w/=w.sum();return [list(bones).index(candidates[i]) for i in ids],w.tolist()

def build(name,path=None):
    files=list((SOURCE/name).rglob('*.obj'))
    if name=='israfel':files=[p for p in files if 'Combined' in p.name]
    path=path or files[0];v,uv,normals,faces,mats,textures=obj(path)
    bones,segments,allowed=humanoid(name) if name in ('sachiel','israfel') else creature(name)
    chosen=[];excluded=set();left_strip=set()
    if name=='zeruel':
        parent=list(range(len(v)))
        def find(i):
            while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
            return i
        for face in faces:
            for point in face[1:]:parent[find(point[0])]=find(face[0][0])
        groups={}
        for i,face in enumerate(faces):groups.setdefault(find(face[0][0]),[]).append(i)
        for group in groups.values():
            pts=v[[k[0] for i in group for k in faces[i]]]
            if pts[:,1].min()<0:excluded.update(group)
            elif len(group)==50 and pts[:,0].max()< -2.7:left_strip.update(group)
        assert len(excluded)==50 and len(left_strip)==50,'Source paper-arm topology changed'
    for face_index,(face,mat) in enumerate(zip(faces,mats)):
        if name=='sachiel' and mat.startswith('6b823'):continue
        points=v[[i[0] for i in face]].copy();ns=normals[[i[2] for i in face]].copy();tex=uv[[i[1] for i in face]].copy();rigid=None
        if face_index in excluded:
            # Replace the exported fully extended right strip with the mirrored,
            # folded left strip below. It is a pose correction, not body scaling.
            continue
        if face_index in left_strip:rigid='paper_r'
        chosen.append((points,ns,tex,mat,rigid))
    if name=='zeruel':
        strips=[r for r in chosen if r[4]=='paper_r']
        chosen=[r for r in chosen if r[4]!='paper_l']
        for points,ns,tex,mat,_ in strips:chosen.append((points[[0,2,1]]*[-1,1,1],ns[[0,2,1]]*[-1,1,1],tex[[0,2,1]],mat,'paper_l'))
    used=sorted({r[3] for r in chosen});cols=2;rows=math.ceil(len(used)/cols);tile=384;atlas=Image.new('RGBA',(cols*tile,rows*tile),(0,0,0,255))
    for i,mat in enumerate(used):
        picture=Image.open(textures[mat]).convert('RGBA').resize((128,128),Image.Resampling.LANCZOS)
        for dz in range(3):
            for dx in range(3):atlas.paste(picture,((i%cols)*tile+dx*128,(i//cols)*tile+dz*128))
    allp=np.concatenate([r[0] for r in chosen]);floor=allp[:,1].min()
    body_points=allp[abs(allp[:,0])<3.0] if name=='israfel' else allp
    height=body_points[:,1].max()-floor;scale=192/height
    vertices=[];ids=[];ws=[]
    for points,ns,tex,mat,rigid in chosen:
        # One subdivision supplies enough deformation samples for smooth joints.
        pp=list(points);nn=list(ns);tt=list(tex)
        for a,b in [(0,1),(1,2),(2,0)]:
            mid=(points[a]+points[b])/2;curved=mid-.175*(ns[a]*np.dot(mid-points[a],ns[a])+ns[b]*np.dot(mid-points[b],ns[b]));pp.append(curved)
            normal=ns[a]+ns[b];nn.append(normal/max(np.linalg.norm(normal),1e-8));tt.append((tex[a]+tex[b])/2)
        for tri in [(0,3,5),(3,1,4),(5,4,2),(3,4,5)]:
            for k in tri:
                p=np.asarray(pp[k]);n=np.asarray(nn[k]);u,t=np.asarray(tt[k]);assert -1<=u<=2 and -1<=t<=2
                mi=used.index(mat);u=(mi%cols+(u+1)/3)/cols;t=(mi//cols+(2-t)/3)/rows
                q=(p-[0,floor,0])*scale*[1,1,-1];normal=n*[1,1,-1]
                vertices.extend([*q,u,t,*normal]);bi,bw=([list(bones).index(rigid)],[1.]) if rigid else weights(p,bones,segments,allowed)
                ids.extend((bi+[0]*4)[:4]);ws.extend((bw+[0]*4)[:4])
    body_bones=[]
    for n,b in bones.items():
        q=(b['pivot']-[0,floor,0])*scale*[1,1,-1]
        body_bones.append(dict(name=n,pivot=np.round(q,6).tolist(),**({'parent':b['parent']} if b['parent'] else {})))
    mesh=dict(format='weighted_angel_r10',stride=8,parts={'root':dict(pivot=[0,0,0],vertices=np.round(vertices,7).tolist())},
              skin=dict(bones=list(bones),indices=ids,weights=np.round(ws,7).tolist()),
              provenance=dict(source=str(path),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),private_test_only=True,subdivision=1,source_height=float(height)))
    geometry={'format_version':'1.12.0','minecraft:geometry':[dict(description=dict(identifier='geometry.'+name,texture_width=atlas.width,texture_height=atlas.height,visible_bounds_width=40,visible_bounds_height=40,visible_bounds_offset=[0,12,0]),bones=body_bones)]}
    idle={};walk={}
    for b in body_bones:idle[b['name']]={'rotation':[0,0,0]};walk[b['name']]={'rotation':[0,0,0]}
    if name=='sachiel':
        for side in ('l','r'):idle['forearm_'+side]['rotation']=[90,0,0];walk['forearm_'+side]['rotation']=[65,0,0]
    if name=='israfel':
        for side,sign in [('l',1),('r',-1)]:idle['arm_'+side]['rotation']=[0,0,sign*70];walk['arm_'+side]['rotation']=[0,0,sign*63]
    if name in ('sachiel','israfel'):
        for side,sign in [('l',1),('r',-1)]:
            walk['leg_'+side]['rotation']={str(round(i*.15,2)):[round(sign*22*math.sin(i*math.pi/4),3),0,0] for i in range(9)}
            walk['shin_'+side]['rotation']={str(round(i*.15,2)):[round(-max(0,-sign*math.sin(i*math.pi/4))*28,3),0,0] for i in range(9)}
    stem={'sachiel':'Sachiel','israfel':'entity_israfel','shamshel':'Shamshel','zeruel':'Zeruel'}[name]
    animations={'format_version':'1.8.0','animations':{f'animation.{stem}.idle'+('_1' if name=='israfel' else ''):dict(loop=True,animation_length=2,bones=idle),f'animation.{stem}.move':dict(loop=True,animation_length=1.2,bones=walk)}}
    for folder,suffix,data in [('geo','.geo.json',geometry),('mesh','.mesh.json',mesh),('animations','.animation.json',animations)]:
        dest=PACK/folder/(name+suffix);dest.parent.mkdir(exist_ok=True);dest.write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
    atlas.save(PACK/'textures/entity'/(name+'.png'))
    (OUT/(name+'_rig.json')).write_text(json.dumps(dict(bones=body_bones,source_scale=scale,source_floor=float(floor),source=str(path)),indent=2),encoding='utf8')
    result=dict(name=name,triangles=len(vertices)//24,bones=len(bones),height=60,skin_weight_error=float(np.max(abs(np.array(ws).reshape(-1,4).sum(1)-1))))
    print(result,flush=True);return result
if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True);report=[build(n) for n in ('sachiel','israfel','shamshel','zeruel')]
    (OUT/'rigged_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf8')
