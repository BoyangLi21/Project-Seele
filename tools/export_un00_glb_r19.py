"""Export the tested segmented game rig as a portable GLB and Blender project."""
from pathlib import Path
import bpy,json,math,hashlib,datetime
import numpy as np
from mathutils import Matrix,Vector,Euler

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r19/un00_local';A=OUT/'runtime_candidate/assets/projectseele';DELIVERY=OUT/'delivery';DELIVERY.mkdir(exist_ok=True)
mesh=json.loads((A/'mesh/eva_prototype.mesh.json').read_text());geo=json.loads((A/'geo/eva_prototype.geo.json').read_text())['minecraft:geometry'][0]['bones'];bones={b['name']:b for b in geo}
bpy.ops.wm.read_factory_settings(use_empty=True);axis=Matrix(((1,0,0),(0,0,-1),(0,1,0)));nodes={}
def point(p):return axis@Vector(np.asarray(p)*[-1,1,1])*(5/16)
for b in geo:
    obj=bpy.data.objects.new(b['name'],None);obj.empty_display_type='PLAIN_AXES';obj.empty_display_size=.25;bpy.context.collection.objects.link(obj);nodes[b['name']]=obj
for b in geo:
    obj=nodes[b['name']];parent=b.get('parent');delta=np.asarray(b['pivot'])-(np.asarray(bones[parent]['pivot']) if parent else 0)
    rot=Euler(tuple(np.deg2rad(np.asarray(b.get('rotation',[0,0,0]))*[-1,-1,1])),'XYZ').to_matrix();obj.parent=nodes[parent] if parent else None;obj.matrix_local=Matrix.Translation(point(delta))@(axis@rot@axis.inverted()).to_4x4()
image=bpy.data.images.load(str(A/'textures/entity/eva_prototype.png'));eye=bpy.data.images.load(str(A/'textures/entity/eva_prototype_eyes.png'));materials=[]
for i in range(8):
    mat=bpy.data.materials.new('UN finish '+str(i));mat.use_nodes=True;shader=mat.node_tree.nodes['Principled BSDF'];tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image;mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);shader.inputs['Metallic'].default_value=.35 if i in (4,6) else .08;shader.inputs['Roughness'].default_value=.55
    if 'Weight' in shader.inputs:shader.inputs['Weight'].default_value=1
    if i==7:glow=mat.node_tree.nodes.new('ShaderNodeTexImage');glow.image=eye;mat.node_tree.links.new(glow.outputs['Color'],shader.inputs['Emission Color']);shader.inputs['Emission Strength'].default_value=1
    materials.append(mat)
for name,part in mesh['parts'].items():
    v=np.asarray(part['vertices'],float).reshape(-1,8);positions=(v[:,:3]*[-1,1,1])[:,[0,2,1]]*[1,-1,1]*(5/16)
    data=bpy.data.meshes.new(name+' armour');data.from_pydata(positions,[],np.arange(len(v)).reshape(-1,3));data.update();obj=bpy.data.objects.new(name+' geometry',data);bpy.context.collection.objects.link(obj);obj.parent=nodes[name];obj.matrix_local=Matrix.Identity(4)
    for mat in materials:data.materials.append(mat)
    uv=data.uv_layers.new(name='Game UV')
    for loop in data.loops:uv.data[loop.index].uv=(float(v[loop.vertex_index,3]),float(1-v[loop.vertex_index,4]))
    for f in data.polygons:f.use_smooth=True;index=f.vertices[0];f.material_index=min(7,int(v[index,3]*4)+4*int(v[index,4]*2))
    normal=(v[:,5:]*[-1,1,1])[:,[0,2,1]]*[1,-1,1];normal/=np.maximum(1e-9,np.linalg.norm(normal,axis=1,keepdims=True));data.normals_split_custom_set_from_vertices(normal.tolist())
nodes['root']['rig_type']='segmented rigid bone hierarchy';nodes['root']['game_model']='EVA-UN-00';nodes['root']['animation_source']='Minecraft geo/mesh and existing game animations; this GLB contains the articulated rest rig'
bpy.context.view_layer.update();bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(DELIVERY/'EVA-UN-00-R19.blend'))
path=DELIVERY/'EVA-UN-00-R19.glb';bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',export_animations=False,export_yup=True,export_extras=True)
report={'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,'triangles':mesh['triangleCount'],'rig_nodes':len(nodes),'source_mesh':str(A/'mesh/eva_prototype.mesh.json'),'source_mesh_sha256':hashlib.sha256((A/'mesh/eva_prototype.mesh.json').read_bytes()).hexdigest(),'exported_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'animations':'Game animation files are supplied separately; GLB is the articulated rest rig'}
(DELIVERY/'export.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
