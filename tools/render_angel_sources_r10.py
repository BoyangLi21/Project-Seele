"""Private source-model turntable sheet and measured extents, run with Blender."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/eva');OUT=ROOT/'artifacts/first_battle_world_r10/models';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);report=[]
names=['sachiel','shamshel','zeruel','israfel','bardiel','gaghiel','sahaquiel','leliel']
for index,name in enumerate(names):
    files=list((ROOT/'external-assets/incoming/angels_r10'/name).rglob('*.obj'))
    if name=='israfel':files=[p for p in files if 'Combined' in p.name]
    path=files[0];old=set(bpy.data.objects);bpy.ops.wm.obj_import(filepath=str(path));objects=[o for o in bpy.data.objects if o not in old and o.type=='MESH']
    points=[o.matrix_world@Vector(p) for o in objects for p in o.bound_box];lo=Vector([min(v[i] for v in points) for i in range(3)]);hi=Vector([max(v[i] for v in points) for i in range(3)])
    scale=8/max(hi.z-lo.z,1e-4);shift=Vector(((index%4)*12,(index//4)*15,0))
    for obj in objects:
        world=obj.matrix_world.copy()
        for v in obj.data.vertices:v.co=((world@v.co)-Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z)))*scale+shift
        obj.matrix_world.identity()
        for mat in obj.data.materials:
            if mat and mat.use_nodes:
                textures=[n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE']
                if textures:mat.node_tree.nodes.active=textures[0]
    report.append(dict(name=name,source=str(path),original_bounds=[list(lo),list(hi)],vertices=sum(len(o.data.vertices) for o in objects),polygons=sum(len(o.data.polygons) for o in objects)))
    curve=bpy.data.curves.new(name,'FONT');curve.body=name.upper();curve.size=.7;obj=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(obj);obj.location=shift+Vector((-3.7,-4.3,.03))
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';shade=scene.display.shading;shade.light='STUDIO';shade.color_type='TEXTURE';shade.show_shadows=True;shade.show_cavity=True;shade.show_specular_highlight=False;shade.background_type='WORLD';scene.world=bpy.data.worlds.new('Background');scene.world.color=(.8,.84,.85)
scene.view_settings.view_transform='Standard';scene.render.resolution_x=2200;scene.render.resolution_y=1350;scene.render.resolution_percentage=100
camera=bpy.data.objects.new('Source inspection',bpy.data.cameras.new('Camera'));bpy.context.collection.objects.link(camera);camera.data.type='ORTHO';camera.data.ortho_scale=57;camera.location=(38,-53,44);target=Vector((18,7,3));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.camera=camera
scene.render.filepath=str(OUT/'source_catalog.png');bpy.ops.render.render(write_still=True)
(OUT/'source_geometry.json').write_text(json.dumps(report,indent=2),encoding='utf8');bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'source_catalog.blend'))
