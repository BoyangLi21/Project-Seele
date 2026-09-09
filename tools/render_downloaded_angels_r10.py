"""Private, separately framed previews of all nine acquired source archives; these are source poses, not gameplay footage."""
import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/eva');OUT=ROOT/'artifacts/first_battle_world_r10/models/download_previews';OUT.mkdir(exist_ok=True)
report=[]
for name in ['sachiel','shamshel','ramiel','israfel','gaghiel','sahaquiel','leliel','bardiel','zeruel']:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 files=list((ROOT/'external-assets/incoming/angels_r10'/name).rglob('*.obj'))
 if name=='israfel':files=[p for p in files if 'Combined' in p.name]
 path=files[0];bpy.ops.wm.obj_import(filepath=str(path));objects=[o for o in bpy.data.objects if o.type=='MESH']
 vertices=[o.matrix_world@v.co for o in objects for v in o.data.vertices];lo=Vector([min(v[i] for v in vertices) for i in range(3)]);hi=Vector([max(v[i] for v in vertices) for i in range(3)]);centre=(lo+hi)/2;span=max(hi-lo)
 for o in objects:
  for mat in o.data.materials:
   if mat and mat.use_nodes:
    images=[n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE']
    if images:mat.node_tree.nodes.active=images[0]
 scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';shade=scene.display.shading;shade.light='STUDIO';shade.color_type='TEXTURE';shade.show_cavity=True;shade.show_shadows=True;shade.background_type='WORLD';scene.world=bpy.data.worlds.new('Backdrop');scene.world.color=(.12,.15,.17)
 scene.view_settings.view_transform='Standard';scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100
 camera=bpy.data.objects.new('Acquisition review',bpy.data.cameras.new('Camera'));bpy.context.collection.objects.link(camera);camera.data.type='ORTHO';camera.data.ortho_scale=span*1.25;camera.location=centre+Vector((span*.28,-span*2,span*.22));camera.rotation_euler=(centre-camera.location).to_track_quat('-Z','Y').to_euler();scene.camera=camera
 scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
 report.append(dict(name=name,source=str(path),vertices=len(vertices),bounds=[list(lo),list(hi)],source_pose=True))
(OUT/'geometry.json').write_text(json.dumps(report,indent=2),encoding='utf8')
