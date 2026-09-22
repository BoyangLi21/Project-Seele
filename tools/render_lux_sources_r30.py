"""Measured studio views of the unmodified Lux3D sources before retargeting."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector,Matrix

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r30/model_inspection';OUT.mkdir(parents=True,exist_ok=True)
def look(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
for serial in ('00','01'):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(ROOT/'artifacts/facility_r30/lux3d'/('un'+serial)/'source.glb'))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(meshes)==1
    body=meshes[0];corners=[body.matrix_world@Vector(p) for p in body.bound_box]
    lo=Vector(tuple(min(v[i] for v in corners) for i in range(3)));hi=Vector(tuple(max(v[i] for v in corners) for i in range(3)))
    s=2/(hi.z-lo.z);m=Matrix.Scale(s,4)@Matrix.Translation(Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z)));body.matrix_world=m@body.matrix_world
    mat=body.data.materials[0];nodes=mat.node_tree.nodes;principled=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    report={'source':str(ROOT/'artifacts/facility_r30/lux3d'/('un'+serial)/'source.glb'),'original_bounds':[list(lo),list(hi)],'material':{'metallic':principled.inputs['Metallic'].default_value,'roughness':principled.inputs['Roughness'].default_value},'images':[{'name':n.image.name,'size':list(n.image.size)} for n in nodes if n.type=='TEX_IMAGE']}
    (OUT/('source_un'+serial+'.json')).write_text(json.dumps(report,indent=2))
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.resolution_x=800;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.4,.45,.5,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
    bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object;floor.name='Preview floor';fmat=bpy.data.materials.new('neutral gray');fmat.diffuse_color=(.22,.24,.27,1);floor.data.materials.append(fmat)
    for name,pos,power,size in [('key',(-3,-4,4),550,4),('fill',(3,-2,3),300,3),('rim',(1,3,4),800,3)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size;o=bpy.data.objects.new(name,light);bpy.context.collection.objects.link(o);o.location=pos;look(o,(0,0,1))
    camera=bpy.data.objects.new('Orthographic source inspection',bpy.data.cameras.new('camera'));bpy.context.collection.objects.link(camera);camera.data.type='ORTHO';camera.data.ortho_scale=2.2;scene.camera=camera
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('source_un'+serial+'.blend')))
    for name,pos in [('front',(0,-6,1.03)),('threequarter',(3,-6,2.3)),('rear',(0,6,1.03))]:
        camera.location=pos;look(camera,(0,0,1));scene.render.filepath=str(OUT/('source_un'+serial+'_'+name+'.png'));bpy.ops.render.render(write_still=True)
