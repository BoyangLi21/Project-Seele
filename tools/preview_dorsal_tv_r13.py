"""Render staged closed, open and partially inserted meshes for shape review."""
from pathlib import Path
import json,math
import bpy,numpy as np
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/dorsal_tv_r13';PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele';CAND=OUT/'candidate/assets/projectseele'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True;scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.world.color=(.36,.36,.36)
for location,power,size in [((-70,-100,240),140000,100),((100,-50,190),95000,80)]:
 bpy.ops.object.light_add(type='AREA',location=location);lamp=bpy.context.object;lamp.data.energy=power;lamp.data.size=size;lamp.rotation_euler=(Vector((0,-15,160))-lamp.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(-65,-135,225));camera=bpy.context.object;camera.data.type='ORTHO';camera.data.ortho_scale=82;camera.rotation_euler=(Vector((0,-13,163))-camera.location).to_track_quat('-Z','Y').to_euler();scene.camera=camera

def material(name):
 mat=bpy.data.materials.new(name);mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear();tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(PACK/'textures/entity'/(name+'.png')));shader=nodes.new('ShaderNodeBsdfPrincipled');output=nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);mat.node_tree.links.new(shader.outputs['BSDF'],output.inputs['Surface']);shader.inputs['Roughness'].default_value=.74;return mat

def create(name,v,mat):
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(v[:,[0,2,1]]*[1,-1,1],[],np.arange(len(v)).reshape(-1,3));mesh.update();uv=mesh.uv_layers.new();coords=v[:,3:5].copy();coords[:,1]=1-coords[:,1];uv.data.foreach_set('uv',coords.ravel());mesh.materials.append(mat);obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);return obj

for record in json.loads((OUT/'candidate_manifest.json').read_text()):
 model=record['model'];data=json.loads((CAND/'mesh'/(model+'.mesh.json')).read_text());geo=json.loads((CAND/'geo'/(model+'.geo.json')).read_text());head=np.array(next(b['pivot'] for b in geo['minecraft:geometry'][0]['bones'] if b['name']=='head'));C=np.array(record['centre']);N=np.array(record['outward']);Y=np.array(record['hinge_axis']);H=np.array(record['hinge']);mat=material(model);plug_name='entry_plug_un' if model=='eva_prototype' else 'entry_plug_'+model[-6:];plugmat=material(plug_name)
 for state in ['closed','open','insertion']:
  arrays=[];objects=[]
  for name,part in data['parts'].items():
   if name in ['cannon','knife','lance','n2','entry_plug'] or name.startswith('finger'):continue
   v=np.array(part['vertices']).reshape(-1,8);v[:,:3]+=part['pivot']
   if state!='closed' and name=='dorsal_cover':rotation=np.array(Matrix.Rotation(math.radians(record['open_angle_degrees']),3,Vector(Y)));v[:,:3]=(v[:,:3]-H)@rotation.T+H
   if state!='closed' and name=='head':rotation=np.array(Matrix.Rotation(-.72,3,'X'));v[:,:3]=(v[:,:3]-head)@rotation.T+head
   arrays.append(v)
  objects.append(create(model,np.vstack(arrays),mat))
  if state=='insertion':
   plug=json.loads((PACK/'mesh'/(plug_name+'.mesh.json')).read_text());arrays=[];basis=np.column_stack(([1,0,0],Y,N))
   for name,part in plug['parts'].items():
    if name=='plug_crane_collar':continue
    v=np.array(part['vertices']).reshape(-1,8);v[:,:3]=(v[:,:3]+part['pivot'])*.64@basis.T+C-N*9;arrays.append(v)
   objects.append(create('capsule',np.vstack(arrays),plugmat))
  scene.render.filepath=str(OUT/(model+'_r13_'+state+'.png'));bpy.ops.render.render(write_still=True)
  for obj in objects:mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
