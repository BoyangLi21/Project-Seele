"""DQS mesh surface probes, in renderer model space scaled to world blocks."""
import json,math,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parents[1]; PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele'; SCALE=5/16
def mul(a,b):
    return np.concatenate((a[...,:3]*b[...,3:]+b[...,:3]*a[...,3:]+np.cross(a[...,:3],b[...,:3]),a[...,3:]*b[...,3:]-np.sum(a[...,:3]*b[...,:3],axis=-1,keepdims=True)),axis=-1)
def vertices(name,held):
    source=PACK/'mesh'/f'{name}.mesh.json'; mesh=json.loads(source.read_text());skin=mesh['skin'];g=json.loads((PACK/'geo'/f'{name}.geo.json').read_text())['minecraft:geometry'][0]['bones'];bones={b['name']:b for b in g}
    animation=json.loads((PACK/'animations'/f'{name}.animation.json').read_text())['animations'][f'animation.{name.capitalize()}.idle']['bones']
    idle={n:tuple(np.array(b.get('rotation',[0,0,0]),float)*np.array([-1,-1,1])*math.pi/180) for n,b in animation.items()}
    rotations={}
    if held:
        rotations={'torso_upper':(-.18,0,0),'head':(-.12,0,0)}
        if name=='shamshel':
            rotations['body']=(-.18,0,0)
            for side,s in [('l',1),('r',-1)]:
                for segment in range(4):rotations[f'whip_{side}_{segment}']=(.4 if segment==0 else .12,0,s*.1)
        for side,s in [('l',1),('r',-1)]:
            rotations['arm_'+side]=(.65,0,s*.35);rotations['forearm_'+side]=(2.5,0,0);rotations['leg_'+side]=(-.18,0,0);rotations['shin_'+side]=(.33,0,0)
    matrices={}
    def matrix(n):
        if n in matrices:return matrices[n]
        b=bones[n];p=np.array(b['pivot'],float);p[0]*=-1;r=Rotation.from_euler('xyz',np.array(idle.get(n,(0,0,0)))+np.array(rotations.get(n,(0,0,0)))).as_matrix();m=np.eye(4);m[:3,:3]=r;m[:3,3]=p-r@p
        if b.get('parent'):m=matrix(b['parent'])@m
        matrices[n]=m;return m
    indices=np.array(skin['indices']).reshape(-1,4);weights=np.array(skin['weights']).reshape(-1,4)
    mats=np.array([matrix(n) for n in skin['bones']]);real=Rotation.from_matrix(mats[:,:3,:3]).as_quat();dual=mul(np.column_stack((mats[:,:3,3],np.zeros(len(mats)))),real)*.5
    qr=real[indices];qd=dual[indices];signed=weights*np.where(np.sum(qr*qr[:,:1],axis=-1)<0,-1,1)
    q=np.sum(qr*signed[...,None],axis=1);d=np.sum(qd*signed[...,None],axis=1);norm=np.linalg.norm(q,axis=-1,keepdims=True);q/=norm;d/=norm;d-=q*np.sum(q*d,axis=-1,keepdims=True)
    conj=q.copy();conj[:,:3]*=-1;translation=mul(d,conj)[:,:3]*2
    v=np.array(mesh['parts']['root']['vertices']).reshape(-1,8)[:,:3];v[:,0]*=-1;t=np.cross(q[:,:3],v)*2;result=(v+q[:,3:]*t+np.cross(q[:,:3],t)+translation)*SCALE
    body_ids=[i for i,n in enumerate(skin['bones']) if n in {'root','torso_lower','torso_upper','neck','head','body'}]
    body=np.sum(weights*np.isin(indices,body_ids),axis=1).reshape(-1,3).min(axis=1)>.8
    return result.reshape(-1,3,3),body,mesh

def ray(tri,o,d,mask=None):
    e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0];h=np.cross(np.broadcast_to(d,e2.shape),e2);a=np.einsum('ij,ij->i',e1,h)
    valid=np.abs(a)>1e-9
    if mask is not None:valid &= mask
    f=np.zeros_like(a);f[valid]=1/a[valid];s=o-tri[:,0];u=f*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1);v=f*(q@d);t=f*np.einsum('ij,ij->i',e2,q)
    valid &= (u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)&(t>=0)
    order=np.flatnonzero(valid);order=order[np.argsort(t[order])]
    hits=[]
    for i in order:
        if hits and abs(hits[-1]['distance']-t[i])<1e-5:continue
        normal=np.cross(e1[i],e2[i]);normal/=np.linalg.norm(normal)
        if normal@d>0:normal*=-1
        hits.append({'triangle':int(i),'distance':float(t[i]),'point':(o+d*t[i]).tolist(),'normal_facing_probe':normal.tolist(),'barycentric':[float(1-u[i]-v[i]),float(u[i]),float(v[i])]})
    return hits

def nearest(tri,p):
    a,b,c=tri[:,0],tri[:,1],tri[:,2];ab=b-a;ac=c-a;n=np.cross(ab,ac);n2=np.einsum('ij,ij->i',n,n)
    q=p-(np.einsum('ij,ij->i',p-a,n)/np.maximum(n2,1e-12))[:,None]*n
    v0=b-a;v1=c-a;v2=q-a;d00=np.einsum('ij,ij->i',v0,v0);d01=np.einsum('ij,ij->i',v0,v1);d11=np.einsum('ij,ij->i',v1,v1);d20=np.einsum('ij,ij->i',v2,v0);d21=np.einsum('ij,ij->i',v2,v1);den=d00*d11-d01*d01
    v=(d11*d20-d01*d21)/np.maximum(den,1e-12);w=(d00*d21-d01*d20)/np.maximum(den,1e-12);inside=(v>=0)&(w>=0)&(v+w<=1)&(n2>1e-12)
    candidates=[]
    d2=np.sum((q-p)**2,axis=1);d2[~inside]=np.inf;candidates.append((d2,q))
    for s,t in [(a,b),(b,c),(c,a)]:
        diff=t-s;f=np.clip(np.einsum('ij,ij->i',p-s,diff)/np.maximum(1e-12,np.sum(diff*diff,axis=1)),0,1);q=s+f[:,None]*diff;candidates.append((np.sum((q-p)**2,axis=1),q))
    best=min(((float(ds.min()),qs[int(ds.argmin())]) for ds,qs in candidates),key=lambda x:x[0])
    return {'distance':math.sqrt(best[0]),'nearest_point':best[1].tolist()}

report={'units':'world blocks; actor origin zero, yaw180 (faces grabber), Bedrock X reflected','assets':{}}
for name,width in [('sachiel',18),('shamshel',20)]:
    result={'sha256':hashlib.sha256((PACK/'mesh'/f'{name}.mesh.json').read_bytes()).hexdigest(),'poses':{}}
    for held in [False,True]:
        tri,body,mesh=vertices(name,held);points=[]
        for sign in [-1,1]:
            p=np.array([sign*width*.23,60*.76,-(width*.5-.75)]);front=ray(tri,np.array([p[0],p[1],-100.]),np.array([0.,0.,1.]),body)
            all_front=ray(tri,np.array([p[0],p[1],-100.]),np.array([0.,0.,1.]))
            points.append({'current':p.tolist(),'nearest_mesh':nearest(tri,p),'front_body_hit':front[0] if front else None,'front_plane_gap':front[0]['point'][2]-p[2] if front else None,'first_full_mesh_front':all_front[0] if all_front else None})
        probes=[]
        for height in [45.6,48.,50.]:
            for angle in [30,45,60]:
                theta=math.radians(angle);o=np.array([math.sin(theta)*70,height,-math.cos(theta)*70]);d=np.array([-math.sin(theta),0,math.cos(theta)])
                hit=ray(tri,o,d,body)
                if hit:probes.append({'height':height,'angle_from_front':angle,**hit[0]})
        result['poses']['held' if held else 'neutral']={'current_points':points,'side_front_candidates':probes}
    report['assets'][name]=result
out=ROOT/'artifacts/facility_r31/grip_surface_audit.json';out.write_text(json.dumps(report,indent=2))
for name,data in report['assets'].items():
    for pose,d in data['poses'].items():
        print(name,pose,'old',[(p['nearest_mesh']['distance'],p['front_plane_gap']) for p in d['current_points']]);print('candidate48',[(p['angle_from_front'],p['point'],p['normal_facing_probe']) for p in d['side_front_candidates'] if p['height']==48])

profile={'schema':'projectseele.angel_grip_surface_r31/v1','space':'GECKO_MODEL_BLOCKS','render_scale':5,'profiles':{}}
verification=[]
for name,angle in [('sachiel',30),('shamshel',45)]:
    neutral,body,mesh=vertices(name,False);held,_,_=vertices(name,True);skin=mesh['skin']
    geo=json.loads((PACK/'geo'/f'{name}.geo.json').read_text())['minecraft:geometry'][0]['bones']
    idle=json.loads((PACK/'animations'/f'{name}.animation.json').read_text())['animations'][f'animation.{name.capitalize()}.idle']['bones']
    bones=[]
    for b in geo:
        pivot=np.array(b['pivot'],float)*np.array([-1,1,1])/16;rotation=np.array(idle.get(b['name'],{}).get('rotation',[0,0,0]),float)*np.array([-1,-1,1])*math.pi/180
        bones.append({'name':b['name'],'parent':b.get('parent'),'pivot':pivot.tolist(),'idle':rotation.tolist()})
    record={'mesh_sha256':report['assets'][name]['sha256'],'bones':bones,'skin_bones':skin['bones'],'anchors':{}}
    raw=np.array(mesh['parts']['root']['vertices']).reshape(-1,8)[:,:3]*np.array([-1,1,1])/16
    for key,sign in [('left',1),('right',-1)]:
        theta=math.radians(angle);origin=np.array([sign*math.sin(theta)*70,48,-math.cos(theta)*70]);direction=np.array([-sign*math.sin(theta),0,math.cos(theta)])
        h=ray(neutral,origin,direction,body)[0];index=h['triangle'];bary=np.array(h['barycentric']);triangle=neutral[index];normal=np.cross(triangle[1]-triangle[0],triangle[2]-triangle[0]);normal/=np.linalg.norm(normal)
        normal_sign=1 if normal@np.array(h['normal_facing_probe'])>0 else -1
        nodes=[]
        for v in range(index*3,index*3+3):
            ids=skin['indices'][v*4:v*4+4];weights=skin['weights'][v*4:v*4+4]
            assert all(skin['bones'][i] in {'root','torso_lower','torso_upper','neck','head','body'} for i,w in zip(ids,weights) if w>0)
            nodes.append({'point':raw[v].tolist(),'indices':ids,'weights':weights})
        record['anchors'][key]={'triangle':index,'barycentric':bary.tolist(),'normal_sign':normal_sign,'vertices':nodes}
        for pose,tris in [('neutral',neutral),('held',held)]:
            p=bary@tris[index];n=np.cross(tris[index][1]-tris[index][0],tris[index][2]-tris[index][0]);n=n/np.linalg.norm(n)*normal_sign
            verification.append({'asset':name,'attacker_hand':key,'pose':pose,'world_blocks_at_yaw180':p.tolist(),'surface_normal_at_yaw180':n.tolist(),'distance_to_complete_mesh':nearest(tris,p)['distance'],'triangle':index})
    profile['profiles'][name]=record
output=ROOT/'run/projectseele-local-maps/angel_grip_r31.json';output.write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf8')
(ROOT/'artifacts/facility_r31/grip_surface_profile_verified.json').write_text(json.dumps({'contacts':verification,'profile_sha256':hashlib.sha256(output.read_bytes()).hexdigest()},indent=2))
print('Wrote',output,'bytes',output.stat().st_size,'max_surface_error',max(r['distance_to_complete_mesh'] for r in verification))
