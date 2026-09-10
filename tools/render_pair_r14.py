"""Render actual posed triangles, not concept art; run in Blender."""
import bpy,json,sys,numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_refinement_r14'/('pair_'+sys.argv[sys.argv.index('--')+1])
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
materials={}
for role,name in [('hero','eva_unit01'),('angel','sachiel')]:
 mat=bpy.data.materials.new(name);mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear();shader=nodes.new('ShaderNodeBsdfPrincipled');output=nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(shader.outputs['BSDF'],output.inputs['Surface']);tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/'run/resourcepacks/eva_real_model/assets/projectseele/textures/entity'/(name+'.png')));mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);shader.inputs['Roughness'].default_value=.8;materials[role]=mat
bpy.ops.mesh.primitive_plane_add(size=320);bpy.context.object.location=(0,-40,-.1);floor=bpy.context.object;mat=bpy.data.materials.new('Ground');mat.diffuse_color=(.25,.28,.3,1);floor.data.materials.append(mat)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=True;scene.render.resolution_x=800;scene.render.resolution_y=800;scene.world.color=(.4,.4,.4)
for loc,power in [((-50,-70,120),90000),((70,-30,80),65000)]:
 bpy.ops.object.light_add(type='AREA',location=loc);lamp=bpy.context.object;lamp.data.energy=power;lamp.data.size=70;lamp.rotation_euler=(Vector((0,-50,30))-lamp.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=87;scene.camera=cam
for record in json.loads((OUT/'manifest.json').read_text()):
 data=np.load(OUT/(record['name']+'.npz'));objs=[]
 for role in ['hero','angel']:
  verts=data[role][:,[0,2,1]]*[1,-1,1];me=bpy.data.meshes.new(role);me.from_pydata(verts,[],np.arange(len(verts)).reshape(-1,3));me.update();uv=me.uv_layers.new();coords=data[role+'_uv'].copy();coords[:,1]=1-coords[:,1];uv.data.foreach_set('uv',coords.ravel());me.materials.append(materials[role]);obj=bpy.data.objects.new(role,me);bpy.context.collection.objects.link(obj);objs.append(obj)
  if role+'_normals' in data:
   for polygon in me.polygons:polygon.use_smooth=True
   me.normals_split_custom_set_from_vertices(data[role+'_normals'][:,[0,2,1]]*[1,-1,1])
 for view,loc in [('side',(-105,-62,37)),('front',(0,-155,42))]:
  cam.location=loc;cam.rotation_euler=(Vector((3,-57,31))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(record['name']+'_'+view+'.png'));bpy.ops.render.render(write_still=True)
 for obj in objs:me=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(me)
