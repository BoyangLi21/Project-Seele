"""Offline paired-surface inspection; production playback is verified separately."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/first_battle_refinement_r12/paired_preview'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
materials={}
for role,name in [('hero','eva_unit01'),('angel','sachiel')]:
 mat=bpy.data.materials.new(name);mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear();tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/'run/resourcepacks/eva_real_model/assets/projectseele/textures/entity'/(name+'.png')));shader=nodes.new('ShaderNodeBsdfPrincipled');output=nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);mat.node_tree.links.new(shader.outputs['BSDF'],output.inputs['Surface']);shader.inputs['Roughness'].default_value=.85;materials[role]=mat
bpy.ops.mesh.primitive_plane_add(size=360,location=(0,-40,-.05));floor=bpy.context.object;mat=bpy.data.materials.new('Neutral floor');mat.diffuse_color=(.2,.23,.27,1);floor.data.materials.append(mat)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True;scene.render.resolution_x=1100;scene.render.resolution_y=850;scene.render.resolution_percentage=100;scene.world.color=(.4,.4,.4)
for loc,power,size in [((-50,-60,110),75000,70),((80,-25,75),58000,65)]:
 bpy.ops.object.light_add(type='AREA',location=loc);lamp=bpy.context.object;lamp.data.energy=power;lamp.data.size=size;lamp.rotation_euler=(Vector((0,-40,25))-lamp.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';scene.camera=camera
for spec in json.loads((OUT/'manifest.json').read_text()):
 name=spec['name'];data=np.load(OUT/(name+'.npz'));objects=[]
 for role in ['hero','angel']:
  vertices=data[role][:,[0,2,1]]*[1,-1,1];me=bpy.data.meshes.new(role);me.from_pydata(vertices,[],np.arange(len(vertices)).reshape(-1,3));me.update();uv=me.uv_layers.new();coords=data[role+'_uv'].copy();coords[:,1]=1-coords[:,1];uv.data.foreach_set('uv',coords.ravel());me.materials.append(materials[role]);obj=bpy.data.objects.new(role,me);bpy.context.collection.objects.link(obj);objects.append(obj)
 target=Vector((0,-25,30)) if spec['time']<10 else Vector((0,-60,27));camera.location=(-90,-95,58) if spec['time']<10 else (-80,-115,63);camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=95 if spec['time']<10 else 92
 scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
 for obj in objects:me=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(me)
