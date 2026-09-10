"""Locate the TV nape markings through their actual texture coordinates and mesh."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy.ndimage import label
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/dorsal_tv_r13';PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele'

def components(triangles):
    points,inverse=np.unique(triangles[:,:,:3].round(4).reshape(-1,3),axis=0,return_inverse=True);faces=inverse.reshape(-1,3);a=faces.ravel();b=faces[:,[1,2,0]].ravel();graph=coo_matrix((np.ones(len(a)),(a,b)),shape=(len(points),len(points)));count,groups=connected_components(graph,directed=False)
    return [np.where(groups[faces[:,0]]==i)[0] for i in range(count)]

def main():
    texture=np.asarray(Image.open(PACK/'textures/entity/eva_unit01.png').convert('RGB'));region=texture[70:96,49:79];groups,n=label(region.max(2)<115);index=max(range(1,n+1),key=lambda i:(groups==i).sum());y,x=np.where(groups==index);uv=np.array([(x.mean()+49+.5)/texture.shape[1],(y.mean()+70+.5)/texture.shape[0]])
    records={}
    for model in ['eva_unit00','eva_unit01','eva_unit02']:
        source=ROOT/'artifacts/world_motion_r11/dorsal'/(model+'_uncut.mesh.json');data=json.loads(source.read_text());part=data['parts']['head'];triangles=np.array(part['vertices']).reshape(-1,3,8);triangles[:,:,:3]+=part['pivot'];dots=[];normals=[];dot_faces=[]
        for i,triangle in enumerate(triangles):
            matrix=(triangle[1:,3:5]-triangle[0,3:5]).T
            if abs(np.linalg.det(matrix))<1e-9:continue
            weights=np.linalg.solve(matrix,uv-triangle[0,3:5]);weights=np.r_[1-weights.sum(),weights]
            if weights.min()<0:continue
            p=weights@triangle[:,:3]
            if not (p[1]>160 and p[2]>8 and abs(p[0])<8):continue
            normal=np.cross(triangle[1,:3]-triangle[0,:3],triangle[2,:3]-triangle[0,:3]);normal/=np.linalg.norm(normal)
            if normal@[0,1,1]<0:normal=-normal
            dots.append(p);normals.append(normal);dot_faces.append(i)
        assert len(dots)==2,(model,dots)
        marked=np.mean(dots,0);axis=np.mean(normals,0);axis[0]=0;axis/=np.linalg.norm(axis);centre=marked-axis*.9
        body_components=[];nape=None
        for faces in components(triangles):
            points=triangles[faces,:,:3];lo=points.min((0,1));hi=points.max((0,1));mean=points.mean((0,1))
            if hi[1]<178 and lo[1]<160 and mean[2]>0:
                body_components.extend(faces.tolist())
                if any(i in faces for i in dot_faces):nape=faces
        assert nape is not None
        points=triangles[nape,:,:3].reshape(-1,3);tip=points[points[:,2].argmax()]
        records[model]=dict(mark_uv=uv.tolist(),mark_centres=np.round(dots,6).tolist(),marked_surface_centre=marked.round(6).tolist(),mouth_centre_model=centre.round(6).tolist(),outward_model=axis.round(8).tolist(),mouth_blocks=(centre*5/16).round(7).tolist(),head_triangles_reparent_to_torso=body_components,nape_component_faces=nape.tolist(),cover_min_y=float(tip[1]-.15),cover_half_width=4.35,source=str(source))
        print(model,'mark centre',marked.round(4),'mouth blocks',np.round(centre*5/16,5),'axis',axis.round(5),'cover minY',tip[1]-.15,'reparent',len(body_components))
    # The original UN body has its own paired dorsal service sockets. Its
    # insertion axis must remain steep enough to stay inside the narrow torso.
    axis=np.array([0,np.cos(np.deg2rad(20)),np.sin(np.deg2rad(20))]);marked=np.array([0,143.,9.]);centre=marked-axis*.9
    records['eva_prototype']=dict(mark_centres=[[-7.5,143,9],[7.5,143,9]],marked_surface_centre=marked.tolist(),mouth_centre_model=centre.round(6).tolist(),outward_model=axis.round(8).tolist(),mouth_blocks=(centre*5/16).round(7).tolist(),cover_min_y=134.,cover_half_width=10.7,source='original UN scapular service sockets from build_original_eva_prototype_r08.py')
    (OUT/'measured_socket_frames.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
if __name__=='__main__':main()
