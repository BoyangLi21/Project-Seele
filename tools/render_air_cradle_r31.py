"""Inspect the actual UN-01 runtime triangles against the articulated original transport mesh."""
import bpy,sys,runpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/facility_r31/transport';OUT.mkdir(parents=True,exist_ok=True)
sys.argv=[str(ROOT/'tools/render_un_r30.py'),'--','--unit','01','--views','']
ctx=runpy.run_path(str(ROOT/'tools/render_un_r30.py'))
body=[o for o in bpy.context.scene.objects if o.get('runtime_bone')]
for o in list(bpy.context.scene.objects):
    if o not in body:bpy.data.objects.remove(o,do_unlink=True)

def mesh_parts(path,predicate):
    objects=[]
    for name,raw in json.loads(path.read_text())['parts'].items():
        if not predicate(name):continue
        a=np.array(raw).reshape(-1,6);v=a[:,:3][:,[0,2,1]]*[1,-1,1]
        data=bpy.data.meshes.new(name);data.from_pydata(v,[],np.arange(len(v)).reshape(-1,3));data.update()
        o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o)
        col=data.color_attributes.new(name='Paint',type='FLOAT_COLOR',domain='CORNER')
        for loop in data.loops:col.data[loop.index].color=(*a[loop.vertex_index,3:]/255,1)
        material=bpy.data.materials.new(name+' paint');material.use_nodes=True
        node=material.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name='Paint'
        shader=material.node_tree.nodes.get('Principled BSDF');material.node_tree.links.new(node.outputs['Color'],shader.inputs['Base Color'])
        shader.inputs['Metallic'].default_value=.35;shader.inputs['Roughness'].default_value=.44
        data.materials.append(material);objects.append(o)
    return objects

plane=mesh_parts(ROOT/'src/main/resources/assets/projectseele/mesh/tv_facilities_r16.json',lambda n:n=='un_transport_body')
cradle=mesh_parts(OUT/'air_cradle_r31.json',lambda n:True)
for o in plane:o.matrix_world=Matrix.Translation((0,0,112))@Matrix.Rotation(math.pi,4,'Z')
for o in cradle:
    for v in o.data.vertices:v.co.x*=1.05
scene=bpy.context.scene;scene.cycles.samples=12;scene.render.resolution_x=1400;scene.render.resolution_y=1000
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.38,.43,.49,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.75
for loc,power,size in [((70,60,160),150000,85),((-70,-70,120),100000,80),((0,0,200),110000,100)]:
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,0,65))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(190,85,105));camera=bpy.context.object;camera.data.type='ORTHO';camera.data.ortho_scale=186;scene.camera=camera
target=Vector((0,0,65));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
rods=[]
def rod(a,b,radius):
    a=Vector(a);b=Vector(b);direction=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=radius,depth=direction.length,location=(a+b)/2)
    o=bpy.context.object;o.rotation_euler=direction.to_track_quat('Z','Y').to_euler();rods.append(o)
    material=bpy.data.materials.get('Hydraulic metal')
    if material is None:
        material=bpy.data.materials.new('Hydraulic metal');material.diffuse_color=(.32,.37,.40,1)
    o.data.materials.append(material)
for degrees in (0,45,90):
    angle=math.radians(degrees);lift=54*math.sin(angle)-8*math.sin(2*angle)
    frame=Matrix.Translation((0,0,34+lift))@Matrix.Rotation(-angle,4,'X')@Matrix.Translation((0,0,-34))
    for o in body+cradle:o.matrix_world=frame
    for o in rods:bpy.data.objects.remove(o,do_unlink=True)
    rods.clear()
    for side in (-1,1):
        for end in (-1,1):
            a=Vector((side*14,-end*10,101));b=frame@Vector((side*14*1.05,-8,18 if end<0 else 50));mid=a.lerp(b,.58)
            rod(a,mid,.48);rod(mid,b,.27)
    scene.render.filepath=str(OUT/f'actual_UN01_cradle_{degrees}.png');bpy.ops.render.render(write_still=True)
    if degrees==90:bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'actual_UN01_cradle.blend'))
print('Actual runtime UN-01 plus R31 cradle, three rotations rendered',flush=True)
