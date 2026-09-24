"""Blender preview of exported game meshes; this is not native gameplay evidence."""
import bpy,json,numpy as np,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/combat_direction_r34/pose_review'
if '--' in sys.argv:OUT=Path(sys.argv[sys.argv.index('--')+1]).resolve()
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=True
scene.render.resolution_x=540;scene.render.resolution_y=620;scene.render.resolution_percentage=100;scene.world.color=(.5,.5,.5)
materials={}
for name in ('eva_unit01','sachiel'):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear();shader=nodes.new('ShaderNodeBsdfPrincipled');output=nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(shader.outputs['BSDF'],output.inputs['Surface']);shader.inputs['Roughness'].default_value=.65
    tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/f'run/resourcepacks/eva_real_model/assets/projectseele/textures/entity/{name}.png'))
    mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);materials[name]=mat
bpy.ops.mesh.primitive_plane_add(size=350,location=(0,0,-.04));floor=bpy.context.object;mat=bpy.data.materials.new('floor');mat.diffuse_color=(.23,.25,.28,1);floor.data.materials.append(mat)
for loc,power,size in [((-40,75,105),60000,70),((60,-25,65),42000,60)]:
    bpy.ops.object.light_add(type='AREA',location=loc);lamp=bpy.context.object;lamp.data.energy=power;lamp.data.size=size;lamp.rotation_euler=(Vector((0,0,28))-lamp.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(-78,130,48));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=70;cam.rotation_euler=(Vector((0,3,28))-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam
for spec in json.loads((OUT/'manifest.json').read_text()):
    if 'camera_target' in spec:
        target=Vector(spec['camera_target']);cam.location=target+Vector((-78,130,25));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    data=np.load(OUT/(spec['file']+'.npz'));v=data['vertices'][:,[0,2,1]]*[1,-1,1];me=bpy.data.meshes.new('body');me.from_pydata(v,[],np.arange(len(v)).reshape(-1,3));me.update()
    uv=me.uv_layers.new();values=data['uv'].copy();values[:,1]=1-values[:,1];uv.data.foreach_set('uv',values.ravel());me.materials.append(materials[spec['model']]);obj=bpy.data.objects.new('body',me);bpy.context.collection.objects.link(obj)
    scene.render.filepath=str(OUT/(spec['file']+'.png'));bpy.ops.render.render(write_still=True);bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(me)
