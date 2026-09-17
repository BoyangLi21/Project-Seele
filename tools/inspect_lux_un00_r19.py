"""Blender inspection of the actual Lux3D source, before rigging or game integration."""
from pathlib import Path
import bpy,json,math,argparse,sys
from mathutils import Vector,Matrix

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r19/lux3d'
ap=argparse.ArgumentParser();ap.add_argument('--source',default='EVA-UN-00-original.glb');ap.add_argument('--prefix',default='un00_diffuse');ap.add_argument('--task',default='3541743');ap.add_argument('--material',choices=['diffuse','albedo','clay'],default='diffuse');ap.add_argument('--views',default='threequarter');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(OUT/args.source))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
points=[o.matrix_world@Vector(c) for o in objects for c in o.bound_box]
lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)])
report={'task_id':args.task,'source':args.source,'source_bounds':[list(lo),list(hi)],'objects':[],'stage':'unrigged source inspection'}
for obj in objects:
    obj.data.calc_loop_triangles();report['objects'].append({'name':obj.name,'vertices':len(obj.data.vertices),'triangles':len(obj.data.loop_triangles),'uv_layers':len(obj.data.uv_layers),'materials':len(obj.data.materials)})
    obj['lux3d_task_id']=args.task
    for material in obj.data.materials:
        if not material.use_nodes:continue
        shader=next((n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
        if shader is not None:
            # The Minecraft entity pipeline uses albedo and scene lighting,
            # not Lux's near-100% metallic map. Preview that downstream look.
            for socket,value in [('Metallic',.08),('Roughness',.65)]:
                for link in list(shader.inputs[socket].links):material.node_tree.links.remove(link)
                shader.inputs[socket].default_value=value
            if 'Weight' in shader.inputs:shader.inputs['Weight'].default_value=1
            if args.material=='clay':
                for link in list(shader.inputs['Base Color'].links):material.node_tree.links.remove(link)
                shader.inputs['Base Color'].default_value=(.18,.18,.18,1)
            elif args.material=='albedo':
                emission=material.node_tree.nodes.new('ShaderNodeEmission');colour=shader.inputs['Base Color']
                if colour.links:material.node_tree.links.new(colour.links[0].from_socket,emission.inputs['Color'])
                else:emission.inputs['Color'].default_value=colour.default_value
                output=next(n for n in material.node_tree.nodes if n.type=='OUTPUT_MATERIAL');material.node_tree.links.new(emission.outputs[0],output.inputs['Surface'])
report['preview_material']=args.material+'; original GLB remains untouched'
centre=(lo+hi)/2;scale=2/(hi.z-lo.z)
for obj in objects:
    # Apply a common world transform, preserving the source's proportions.
    obj.matrix_world=Matrix.Scale(scale,4)@Matrix.Translation(Vector((-centre.x,-centre.y,-lo.z)))@obj.matrix_world
bpy.context.view_layer.update()
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='OPTIX'
    if any(d.type=='OPTIX' for d in prefs.devices):scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=1000;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Neutral inspection studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.25,.27,.3,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
for name,location,power,size in [('key',(-3,-4,5),850,4),('fill',(3,-2,3),600,3),('rim',(0,3,4),1100,3)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
    obj=bpy.data.objects.new(name,light);scene.collection.objects.link(obj);obj.location=location;obj.rotation_euler=(Vector((0,0,1))-obj.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.002));floor=bpy.context.object
mat=bpy.data.materials.new('Studio floor');mat.diffuse_color=(.33,.35,.38,1);floor.data.materials.append(mat)
camera=bpy.data.objects.new('Source inspection',bpy.data.cameras.new('Source inspection'));scene.collection.objects.link(camera);scene.camera=camera
camera.data.type='ORTHO';camera.data.ortho_scale=2.28
scene.view_settings.view_transform='Standard' if args.material=='albedo' else 'AgX'
(OUT/(args.prefix+'_inspection.json')).write_text(json.dumps(report,indent=2))
views={'front':(0,-1,.02),'threequarter':(1,-1.8,.14),'side':(1,0,.02),'rear':(0,1,.02)}
for index,name in enumerate(args.views.split(',')):
    direction=views[name]
    camera.location=Vector((0,0,1))+Vector(direction).normalized()*6
    camera.rotation_euler=(Vector((0,0,1))-camera.location).to_track_quat('-Z','Y').to_euler()
    if index==0:bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(args.prefix+'-review.blend')))
    scene.render.filepath=str(OUT/(args.prefix+'_'+name+'.png'));bpy.ops.render.render(write_still=True)
print(json.dumps(report),flush=True)
