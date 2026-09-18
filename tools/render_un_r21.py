"""Neutral inspection of the actual runtime mesh, with authored joint skinning."""
import bpy,json,sys,argparse,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Euler,Quaternion
ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--unit',required=True);ap.add_argument('--views',default='front,threequarter,rear');ap.add_argument('--open',type=float,default=0);ap.add_argument('--asset-root',type=Path,default=ROOT/'artifacts/un_models_r21');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
OUT=a.asset_root/('un'+a.unit);ASSET=OUT/'runtime/assets/projectseele';mesh=json.loads((ASSET/'mesh/eva_prototype.mesh.json').read_text());geo=json.loads((ASSET/'geo/eva_prototype.geo.json').read_text())['minecraft:geometry'][0]['bones'];bones={b['name']:b for b in geo};matrices={}
def transform(name):
 if name not in matrices:
  b=bones[name];p=Vector(np.asarray(b['pivot'])*[-1,1,1]);angles=np.asarray(b.get('rotation',[0,0,0]))*[-1,-1,1];q=Euler(tuple(np.deg2rad(angles)),'XYZ').to_matrix().to_4x4()
  if name=='dorsal_cover' and a.open:
   profile=mesh['r13_dorsal_socket'];axis=Vector(profile['hinge_axis']);flip=Matrix.Diagonal(Vector((-1,1,1,1)));q=flip@Quaternion(axis,math.radians(profile['open_angle_degrees']*a.open)).to_matrix().to_4x4()@flip
  m=Matrix.Translation(p)@q@Matrix.Translation(-p);matrices[name]=transform(b['parent'])@m if b.get('parent') else m
 return matrices[name]
bpy.ops.wm.read_factory_settings(use_empty=True);image=bpy.data.images.load(str(ASSET/'textures/entity/eva_prototype.png'));image.pack()
material=bpy.data.materials.new('Runtime armour colours');material.use_nodes=True;shader=material.node_tree.nodes.get('Principled BSDF');tex=material.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image;material.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);shader.inputs['Metallic'].default_value=.22;shader.inputs['Roughness'].default_value=.44
for name,part in mesh['parts'].items():
 v=np.asarray(part['vertices']).reshape(-1,8);raw=(v[:,:3]+part['pivot'])*[-1,1,1];normal=v[:,5:]*[-1,1,1];m=np.array(transform(name));p=(np.c_[raw,np.ones(len(raw))]@m.T)[:,:3];n=normal@m[:3,:3].T
 spec=mesh.get('jointSkins',{}).get(name)
 if spec:
  # At the neutral inspection pose the principal body frames are identity;
  # check this rather than silently dropping a non-trivial blend.
  for other in spec.get('influences',{}):assert np.allclose(np.array(transform(other)),m,atol=1e-6),(name,other)
 coords=p[:,[0,2,1]]*[1,-1,1]*5/16;normals=n[:,[0,2,1]]*[1,-1,1]
 data=bpy.data.meshes.new(name);data.from_pydata(coords,[],np.arange(len(coords)).reshape(-1,3));data.update();obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);data.materials.append(material)
 uv=data.uv_layers.new(name='Runtime UV')
 for loop in data.loops:uv.data[loop.index].uv=(float(v[loop.vertex_index,3]),float(1-v[loop.vertex_index,4]))
 for poly in data.polygons:poly.use_smooth=True
 normals/=np.maximum(1e-9,np.linalg.norm(normals,axis=1,keepdims=True));data.normals_split_custom_set_from_vertices(normals.tolist());obj['runtime_bone']=name
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for device in prefs.devices:device.use=device.type=='OPTIX'
 if any(d.type=='OPTIX' for d in prefs.devices):scene.cycles.device='GPU'
except Exception:pass
bpy.ops.mesh.primitive_plane_add(size=500,location=(0,0,-.08));floor=bpy.context.object;mat=bpy.data.materials.new('Neutral ground');mat.diffuse_color=(.21,.24,.26,1);floor.data.materials.append(mat)
scene.world=bpy.data.worlds.new('Neutral inspection');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.27,.30,.34,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
for loc,power,size in [((-40,55,80),50000,45),((45,40,50),30000,35),((0,-40,75),43000,30)]:
 bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(Vector((0,0,30))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';camera.data.ortho_scale=67;scene.camera=camera;scene.render.resolution_x=980;scene.render.resolution_y=1400;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
views={'front':(0,110,33),'side':(110,0,33),'threequarter':(66,110,43),'rear':(0,-110,33),'dorsal':(15,-50,81)}
for index,name in enumerate(filter(None,a.views.split(','))):
 camera.location=views[name];camera.data.ortho_scale=21 if name=='dorsal' else 67;camera.rotation_euler=(Vector((0,0,49 if name=='dorsal' else 30))-camera.location).to_track_quat('-Z','Y').to_euler()
 if index==0:bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'runtime_inspection.blend'))
 scene.render.filepath=str(OUT/('runtime_'+name+('_open' if a.open else '')+'.png'));bpy.ops.render.render(write_still=True)
print('Actual runtime geometry and textures rendered',a.unit,flush=True)
