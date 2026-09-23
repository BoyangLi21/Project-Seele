"""Geometry-only calibration of the existing red upper-back power receptacles."""
import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];ASSET=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele';OUT=ROOT/'artifacts/facility_r31/transport/power';OUT.mkdir(exist_ok=True)
for unit in ('00','01','02'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    name='eva_unit'+unit;m=json.loads((ASSET/'mesh'/(name+'.mesh.json')).read_text())
    image=bpy.data.images.load(str(ASSET/'textures/entity'/(name+'.png')));material=bpy.data.materials.new('Actual source armour');material.use_nodes=True;shader=material.node_tree.nodes.get('Principled BSDF');tex=material.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image;material.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);shader.inputs['Roughness'].default_value=.56
    for n,p in m['parts'].items():
        if n in ('cannon','knife','lance','shield','n2'):continue
        a=np.array(p['vertices']).reshape(-1,8);v=(a[:,:3]+p['pivot'])*[-1,1,1]*5/16
        data=bpy.data.meshes.new(n);data.from_pydata(v[:,[0,2,1]]*[1,-1,1],[],np.arange(len(v)).reshape(-1,3));data.update();o=bpy.data.objects.new(n,data);bpy.context.collection.objects.link(o);data.materials.append(material);uv=data.uv_layers.new()
        for loop in data.loops:uv.data[loop.index].uv=(a[loop.vertex_index,3],1-a[loop.vertex_index,4])
        for poly in data.polygons:poly.use_smooth=True
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
        for device in prefs.devices:device.use=device.type=='OPTIX'
        scene.cycles.device='GPU'
    except Exception:pass
    scene.world=bpy.data.worlds.new('Inspection');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.22,.26,.31,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
    for loc,power,size in [((-15,-25,60),30000,25),((20,-10,44),20000,20)]:
        bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.size=size;o.rotation_euler=(Vector((0,0,46))-o.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.object.camera_add(location=(0,-70,48));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=24;cam.rotation_euler=(Vector((0,0,47))-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam;scene.render.resolution_x=1200;scene.render.resolution_y=1200;scene.view_settings.view_transform='AgX'
    scene.render.filepath=str(OUT/(name+'_actual_back.png'));bpy.ops.render.render(write_still=True)
print('All three actual back meshes rendered for power socket inspection',flush=True)
