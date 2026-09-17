"""Blender review of the private R19 mesh with its actual skeleton and UV atlas."""
import bpy,json,math,sys,argparse
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Euler

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r19/un00_local';A=OUT/'assets/projectseele'
args=argparse.ArgumentParser();args.add_argument('--views',default='threequarter');args.add_argument('--installed',action='store_true');a=args.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
if a.installed:A=OUT/'runtime_candidate/assets/projectseele'
prefix='installed_model' if a.installed else 'body_candidate'
mesh=json.loads((A/'mesh/eva_prototype.mesh.json').read_text());geo=json.loads((A/'geo/eva_prototype.geo.json').read_text())['minecraft:geometry'][0]['bones'];bones={b['name']:b for b in geo};matrices={}
def transform(name):
    if name in matrices:return matrices[name]
    b=bones[name];p=Vector(np.asarray(b['pivot'])*[-1,1,1]);degrees=np.asarray(b.get('rotation',[0,0,0]),float)*[-1,-1,1]
    if name=='arm_l':degrees[2]-=8
    if name=='arm_r':degrees[2]+=8
    rotation=Euler(tuple(np.deg2rad(degrees)),'XYZ').to_matrix().to_4x4();m=Matrix.Translation(p)@rotation@Matrix.Translation(-p)
    matrices[name]=transform(b['parent'])@m if b.get('parent') else m;return matrices[name]
bpy.ops.wm.read_factory_settings(use_empty=True)
image=bpy.data.images.load(str(A/'textures/entity/eva_prototype.png'));materials=[]
for i in range(8):
    material=bpy.data.materials.new('R19 finish '+str(i));material.use_nodes=True;shader=material.node_tree.nodes.get('Principled BSDF');texture=material.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image
    material.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color']);shader.inputs['Roughness'].default_value=.55;shader.inputs['Metallic'].default_value=.38 if i in (4,6) else .08
    if 'Weight' in shader.inputs:shader.inputs['Weight'].default_value=1
    if i==7:material.node_tree.links.new(texture.outputs['Color'],shader.inputs['Emission Color']);shader.inputs['Emission Strength'].default_value=.8
    materials.append(material)
for name,part in mesh['parts'].items():
    v=np.asarray(part['vertices'],float).reshape(-1,8);raw=(v[:,:3]+part['pivot'])*[-1,1,1];m=np.asarray(transform(name));posed=(np.c_[raw,np.ones(len(raw))]@m.T)[:,:3]
    coords=posed[:,[0,2,1]]*[1,-1,1]/16*5;data=bpy.data.meshes.new(name);data.from_pydata(coords,[],np.arange(len(coords)).reshape(-1,3));data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    for material in materials:data.materials.append(material)
    uv=data.uv_layers.new(name='Source UV')
    for loop in data.loops:uv.data[loop.index].uv=(float(v[loop.vertex_index,3]),float(1-v[loop.vertex_index,4]))
    for polygon in data.polygons:
        index=polygon.vertices[0];polygon.material_index=min(7,int(v[index,3]*4)+4*int(v[index,4]*2));polygon.use_smooth=True
    normal=(v[:,5:]*[-1,1,1])@m[:3,:3].T;normal=normal[:,[0,2,1]]*[1,-1,1]
    normal/=np.maximum(1e-9,np.linalg.norm(normal,axis=1,keepdims=True));data.normals_split_custom_set_from_vertices(normal.tolist())
bpy.ops.mesh.primitive_plane_add(size=360,location=(0,0,-.08));floor=bpy.context.object;mat=bpy.data.materials.new('Neutral floor');mat.diffuse_color=(.18,.2,.21,1);floor.data.materials.append(mat)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='OPTIX'
    if any(d.type=='OPTIX' for d in prefs.devices):scene.cycles.device='GPU'
except Exception:pass
scene.world=bpy.data.worlds.new('Inspection');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.25,.27,.3,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.4
scene.render.resolution_x=832;scene.render.resolution_y=1280;scene.render.resolution_percentage=100
for location,power,size in [((35,55,85),40000,45),((-40,20,45),18000,40),((0,-35,75),33000,28)]:
    bpy.ops.object.light_add(type='AREA',location=location);light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(Vector((0,0,30))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';camera.data.ortho_scale=66;scene.camera=camera;scene.view_settings.view_transform='AgX'
views={'front':(0,110,34),'threequarter':(70,110,44),'rear':(0,-110,34)}
for index,name in enumerate(a.views.split(',')):
    camera.location=views[name];camera.rotation_euler=(Vector((0,0,30))-camera.location).to_track_quat('-Z','Y').to_euler()
    if index==0:bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(prefix+'_review.blend')))
    scene.render.filepath=str(OUT/(prefix+'_'+name+'.png'));bpy.ops.render.render(write_still=True)
print('Private body candidate rendered from actual mesh, geo and texture resources')
