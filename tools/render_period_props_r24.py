"""Editable offline inspection of the exact original fixture meshes."""
from pathlib import Path
import bpy,json,math
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r24/props';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
source=json.loads((ROOT/'src/main/resources/assets/projectseele/mesh/period_details_r24.json').read_text())
names=['public_phone','notice_board','utility_box','pipe_run','bollard','hydrant','wall_clock','drinking_fountain','cafe_counter','cafe_table','cafe_stool','newspaper_rack','coffee_machine']
material=bpy.data.materials.new('Original painted metal');material.use_nodes=True
nodes=material.node_tree.nodes;nodes.clear();shader=nodes.new('ShaderNodeBsdfPrincipled');output=nodes.new('ShaderNodeOutputMaterial');material.node_tree.links.new(shader.outputs[0],output.inputs['Surface']);colour=nodes.new('ShaderNodeVertexColor');colour.layer_name='Col';material.node_tree.links.new(colour.outputs['Color'],shader.inputs['Base Color']);shader.inputs['Roughness'].default_value=.52
def add(name,offset):
    data=source['parts'][name];points=[];colors=[]
    for i in range(0,len(data),6):
        x,y,z,r,g,b=data[i:i+6];points.append((x+offset[0],-z+offset[1],y));colors.append((r/255,g/255,b/255,1))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(points,[],[tuple(range(i,i+3)) for i in range(0,len(points),3)]);mesh.update();obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    attr=mesh.color_attributes.new(name='Col',type='FLOAT_COLOR',domain='CORNER')
    for loop in mesh.loops:attr.data[loop.index].color=colors[loop.vertex_index]
    if name=='phone_glass':
        glass=bpy.data.materials.new('Booth glazing');glass.diffuse_color=(.67,.8,.77,.2);glass.use_nodes=True;glass.node_tree.nodes.clear();s=glass.node_tree.nodes.new('ShaderNodeBsdfPrincipled');out=glass.node_tree.nodes.new('ShaderNodeOutputMaterial');glass.node_tree.links.new(s.outputs[0],out.inputs['Surface']);s.inputs['Base Color'].default_value=(.67,.8,.77,1);s.inputs['Roughness'].default_value=.12;s.inputs['Transmission Weight'].default_value=.92;s.inputs['IOR'].default_value=1.45;obj.data.materials.append(glass)
    else:obj.data.materials.append(material)
    return obj
for i,name in enumerate(names):
    offset=((i%4)*1.7,(i//4)*-2.15);add(name,offset)
    if name=='public_phone':add('phone_glass',offset)
bpy.ops.mesh.primitive_plane_add(size=200,location=(3,-1,-.012));floor=bpy.context.object;mat=bpy.data.materials.new('Inspection floor');mat.diffuse_color=(.72,.75,.7,1);floor.data.materials.append(mat)
bpy.ops.object.camera_add(location=(9,-15,12));camera=bpy.context.object;target=Vector((2.8,-3.4,.95));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=12
scene=bpy.context.scene;scene.camera=camera;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1440;scene.render.resolution_y=960;scene.render.resolution_percentage=100;scene.world.color=(.2,.2,.2)
for location,power,size in [((0,-4,8),1200,6),((7,1,5),800,5)]:
    bpy.ops.object.light_add(type='AREA',location=location);lamp=bpy.context.object;lamp.data.energy=power;lamp.data.shape='DISK';lamp.data.size=size;lamp.rotation_euler=(target-lamp.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'original_period_fixtures.blend'));scene.render.filepath=str(OUT/'fixture_sheet.png');bpy.ops.render.render(write_still=True)
print('Period fixture editable source and inspection rendered')
