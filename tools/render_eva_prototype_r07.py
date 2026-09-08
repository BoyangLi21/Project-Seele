"""Offline studio rendering of the actual authored mesh, not its concept illustration."""
import bpy,numpy as np,math
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/eva');OUT=ROOT/'artifacts/world_expansion_r07/prototype'
d=np.load(OUT/'model.npz');v=d['vertices'][:,[0,2,1]]*[1,-1,1]/16*5
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
me=bpy.data.meshes.new('Original R07 prototype');me.from_pydata(v,[],np.arange(len(v)).reshape(-1,3));me.update()
ob=bpy.data.objects.new('Unnamed experimental EVA',me);bpy.context.collection.objects.link(ob)
for i,colour in enumerate(d['colours']):
    rgb=[int(colour[j:j+2],16)/255 for j in (1,3,5)];mat=bpy.data.materials.new('Finish '+str(i));mat.diffuse_color=(*rgb,1);mat.use_nodes=True
    mat.node_tree.nodes.clear();bsdf=mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled');output=mat.node_tree.nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(bsdf.outputs['BSDF'],output.inputs['Surface'])
    bsdf.inputs['Base Color'].default_value=(*rgb,1);bsdf.inputs['Roughness'].default_value=.42 if i==0 else .65;bsdf.inputs['Metallic'].default_value=.3 if i==2 else .03
    if i==7:bsdf.inputs['Emission Color'].default_value=(*rgb,1);bsdf.inputs['Emission Strength'].default_value=1.4
    me.materials.append(mat)
for p,c in zip(me.polygons,d['materials']):p.material_index=int(c)
bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.remove_doubles(threshold=.00005);bpy.ops.object.mode_set(mode='OBJECT');bpy.ops.object.shade_smooth()
bpy.ops.mesh.primitive_plane_add(size=360,location=(0,0,-.08));plane=bpy.context.object
mat=bpy.data.materials.new('Warm studio floor');mat.diffuse_color=(.18,.21,.22,1);plane.data.materials.append(mat)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.world.color=(.3,.32,.34);scene.render.resolution_x=1080;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
for loc,power,size in [((35,-45,85),35000,45),((-35,-10,48),17000,32),((0,35,65),40000,25)]:
    bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(Vector((0,0,28))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';camera.data.ortho_scale=68;scene.camera=camera
for name,loc in [('front',(0,110,35)),('threequarter',(77,115,49)),('rear',(0,-110,35))]:
    camera.location=loc;camera.rotation_euler=(Vector((0,0,30))-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'eva_prototype_r07.blend'))
