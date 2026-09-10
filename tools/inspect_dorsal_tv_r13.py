"""Blender views of the exact private back armour, current and before the R11 bore."""
from pathlib import Path
import json,math
import bpy,numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/dorsal_tv_r13';PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=True;scene.render.resolution_x=950;scene.render.resolution_y=950;scene.render.resolution_percentage=100;scene.world.color=(.35,.35,.35)
for loc,power,size in [((-70,-100,240),140000,130),((100,-50,175),90000,100)]:
 bpy.ops.object.light_add(type='AREA',location=loc);lamp=bpy.context.object;lamp.data.energy=power;lamp.data.size=size;lamp.rotation_euler=(Vector((0,-15,150))-lamp.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();camera=bpy.context.object;scene.camera=camera;camera.data.type='ORTHO';camera.data.ortho_scale=105
for model in ['eva_unit00','eva_unit01','eva_unit02','eva_prototype']:
 material=bpy.data.materials.new(model);material.use_nodes=True;nodes=material.node_tree.nodes;nodes.clear();tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(PACK/'textures/entity'/(model+'.png')));shader=nodes.new('ShaderNodeBsdfPrincipled');output=nodes.new('ShaderNodeOutputMaterial');material.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);material.node_tree.links.new(shader.outputs['BSDF'],output.inputs['Surface']);shader.inputs['Roughness'].default_value=.74
 for state in ['current','uncut']:
  path=PACK/'mesh'/(model+'.mesh.json') if state=='current' else ROOT/'artifacts/world_motion_r11/dorsal'/(model+'_uncut.mesh.json');data=json.loads(path.read_text());arrays=[]
  for name,part in data['parts'].items():
   if name in ['cannon','knife','lance','n2','entry_plug'] or name.startswith('finger'):continue
   array=np.array(part['vertices']).reshape(-1,8);array[:,:3]+=part['pivot'];arrays.append(array)
  v=np.vstack(arrays);positions=v[:,[0,2,1]]*[1,-1,1];mesh=bpy.data.meshes.new(model);mesh.from_pydata(positions,[],np.arange(len(v)).reshape(-1,3));mesh.update();uv=mesh.uv_layers.new();coords=v[:,3:5].copy();coords[:,1]=1-coords[:,1];uv.data.foreach_set('uv',coords.ravel());mesh.materials.append(material);obj=bpy.data.objects.new(model,mesh);bpy.context.collection.objects.link(obj)
  for angle in ['rear','oblique']:
   camera.location=(0,-160,167) if angle=='rear' else (-86,-138,210);target=Vector((0,-9,155));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(model+'_'+state+'_'+angle+'.png'));bpy.ops.render.render(write_still=True)
  bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
