"""Blender inspection of the actual evaluated EVA surface. Not a game screenshot."""
import bpy,numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/first_battle_refinement_r12/retarget_preview'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
material=bpy.data.materials.new('Actual local Unit-01 texture');material.use_nodes=True;nodes=material.node_tree.nodes;nodes.clear();image=nodes.new('ShaderNodeTexImage');image.image=bpy.data.images.load(str(ROOT/'run/resourcepacks/eva_real_model/assets/projectseele/textures/entity/eva_unit01.png'));shader=nodes.new('ShaderNodeBsdfPrincipled');output=nodes.new('ShaderNodeOutputMaterial');material.node_tree.links.new(shader.outputs['BSDF'],output.inputs['Surface']);material.node_tree.links.new(image.outputs['Color'],shader.inputs['Base Color']);shader.inputs['Roughness'].default_value=.8
bpy.ops.mesh.primitive_plane_add(size=240,location=(0,0,-.05));floor=bpy.context.object;floor_material=bpy.data.materials.new('Neutral inspection floor');floor_material.diffuse_color=(.22,.24,.27,1);floor.data.materials.append(floor_material)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.render.resolution_x=720;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.world.color=(.4,.4,.4)
for loc,power,size in [((45,65,90),42000,60),((-50,10,55),28000,45)]:
 bpy.ops.object.light_add(type='AREA',location=loc);lamp=bpy.context.object;lamp.data.energy=power;lamp.data.size=size;lamp.rotation_euler=(Vector((0,0,28))-lamp.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(100,155,58));camera=bpy.context.object;camera.data.type='ORTHO';camera.data.ortho_scale=73;camera.rotation_euler=(Vector((0,0,28))-camera.location).to_track_quat('-Z','Y').to_euler();scene.camera=camera
for name in ['heavy_pull','grab_a','punch2','kick']:
 d=np.load(OUT/(name+'.npz'));v=d['vertices'][:,[0,2,1]]*[1,-1,1]*5/16;data=bpy.data.meshes.new(name);data.from_pydata(v,[],np.arange(len(v)).reshape(-1,3));data.update();uv=data.uv_layers.new(name='source_uv');values=d['uv'].copy();values[:,1]=1-values[:,1];uv.data.foreach_set('uv',values.ravel());data.materials.append(material);obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
 scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(data)
