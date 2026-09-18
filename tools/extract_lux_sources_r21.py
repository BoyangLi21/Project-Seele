"""Read generated meshes with Blender; retain complete positions, UVs and normals."""
import bpy,json,sys,argparse,hashlib
import numpy as np
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--unit',required=True);ap.add_argument('--source');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/un_models_r21/lux3d'/('un'+a.unit);source=Path(a.source).resolve() if a.source else OUT/'source.glb'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(objects)==1
o=objects[0];mesh=o.data;mesh.calc_loop_triangles();mat=mesh.materials[0];bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');image=bsdf.inputs['Base Color'].links[0].from_node.image
pixels=np.empty(len(image.pixels),np.float32);image.pixels.foreach_get(pixels);pixels=pixels.reshape(image.size[1],image.size[0],4)
image.filepath_raw=str(OUT/'source_basecolor.png');image.file_format='PNG';image.save()
v=np.array([o.matrix_world@q.co for q in mesh.vertices]);v=v[:,[0,2,1]]*[-1,1,1]
scale=193.1/(v[:,1].max()-v[:,1].min());v[:,0]-=(v[:,0].min()+v[:,0].max())/2;v[:,1]-=v[:,1].min();v*=scale
tri=np.array([t.vertices[:] for t in mesh.loop_triangles],np.int32)
loops=np.array([t.loops[:] for t in mesh.loop_triangles]);uvs=np.array([q.uv[:] for q in mesh.uv_layers.active.data]);uv=uvs[loops]
normal_matrix=np.asarray(o.matrix_world.to_3x3().inverted().transposed());normals=np.array([q.vector[:] for q in mesh.corner_normals])[loops]@normal_matrix.T
normals=normals[:,:,[0,2,1]]*[-1,1,1];normals/=np.maximum(1e-12,np.linalg.norm(normals,axis=2,keepdims=True))
coords=np.clip(np.rint(uv*np.array([image.size[0]-1,image.size[1]-1])),0,np.array([image.size[0]-1,image.size[1]-1])).astype(int);colors=pixels[coords[:,:,1],coords[:,:,0],:3]
np.savez_compressed(OUT/'geometry.npz',vertices=v,triangles=tri,uv=uv,colors=colors,normals=normals,pixels=pixels)
report={'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'bounds':[v.min(0).tolist(),v.max(0).tolist()],'triangles':len(tri),'vertices':len(v),'texture':list(image.size),'bands':{}}
for y in range(10,191,10):
 band=v[abs(v[:,1]-y)<1.5];report['bands'][y]=np.quantile(band[:,[0,2]],[0,.1,.25,.5,.75,.9,1],axis=0).tolist() if len(band) else []
(OUT/'geometry.json').write_text(json.dumps(report,indent=2));print(a.unit,len(v),len(tri),'complete source read, corner normals retained')
