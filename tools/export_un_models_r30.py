"""Export actual staged geometry as editable, skinned Blender/GLB files."""
import bpy,json,sys,runpy,datetime,hashlib,argparse
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];ap=argparse.ArgumentParser();ap.add_argument('--asset-root',type=Path,default=ROOT/'artifacts/facility_r30/models');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []);ASSET_ROOT=args.asset_root;OUT=ASSET_ROOT/'export';OUT.mkdir(exist_ok=True)
started=datetime.datetime.now(datetime.timezone.utc).isoformat();outputs=[]
for unit in ['00','01']:
 sys.argv=[str(ROOT/'tools/render_un_r30.py'),'--','--unit',unit,'--views','','--asset-root',str(ASSET_ROOT)]
 context=runpy.run_path(str(ROOT/'tools/render_un_r30.py'));mesh=context['mesh'];bones=context['bones'];transform=context['transform']
 objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('runtime_bone')]
 # The renderer's model frame maps to Blender's Z-up frame without scaling
 # a second time: the mesh is already in Minecraft block units.
 C=Matrix(((1,0,0),(0,0,-1),(0,1,0)))
 armature=bpy.data.armatures.new('EVA-UN-'+unit+' canonical rig');rig=bpy.data.objects.new('EVA-UN-'+unit,armature);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
 for name,b in bones.items():
  bone=armature.edit_bones.new(name);matrix=transform(name);pivot=Vector(np.asarray(b['pivot'])*[-1,1,1]);position=C@(matrix@pivot)*5/16;orientation=C@matrix.to_3x3();frame=orientation.to_4x4();frame.translation=position;bone.matrix=frame;bone.length=.55
 for name,b in bones.items():
  if b.get('parent'):armature.edit_bones[name].parent=armature.edit_bones[b['parent']]
 bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True
 for obj in objects:
  name=obj['runtime_bone'];skin=mesh.get('jointSkins',{}).get(name)
  if skin:
   for bone,weights in skin['influences'].items():
    group=obj.vertex_groups.new(name=bone)
    for index in np.flatnonzero(np.asarray(weights)>0):group.add([int(index)],float(weights[index]),'REPLACE')
  else:obj.vertex_groups.new(name=name).add(list(range(len(obj.data.vertices))),1.0,'REPLACE')
  modifier=obj.modifiers.new('Canonical articulated skin','ARMATURE');modifier.object=rig;modifier.use_deform_preserve_volume=True;obj.parent=rig
  obj['source_task']=mesh['lux3d_task'] if not name.startswith(('hand_','finger_','wrist_','dorsal_','r30_thruster_')) else 'local-modeling';obj['local_authoring']='build_un_airframes_r30.py + finish_un_details_r30.py';obj['game_mesh']='eva_prototype' if unit=='00' else 'eva_un01'
 # Preserve the editing scene, including its neutral inspection lighting.
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('EVA-UN-'+unit+'.blend')))
 bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
 for obj in objects:obj.select_set(True)
 path=OUT/('EVA-UN-'+unit+'.glb');properties=set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys());params=dict(filepath=str(path),export_format='GLB',use_selection=True,export_skins=True,export_animations=False,export_yup=True)
 if 'export_all_influences' in properties:params['export_all_influences']=False
 bpy.ops.export_scene.gltf(**params)
 outputs.append(dict(unit=unit,file=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,bones=len(bones),triangles=mesh['triangleCount'],source=str(context['ASSET']),animations='Gameplay animations stay in the Minecraft runtime; this GLB supplies the complete editable rest rig',skinning='Blender preserve-volume; standard glTF linear skinning on export'))
# One self-contained side-by-side inspection scene, independent of map placement.
bpy.ops.wm.read_factory_settings(use_empty=True)
for unit,offset in [('00',-18),('01',18)]:
 before=set(bpy.context.scene.objects);bpy.ops.import_scene.gltf(filepath=str(OUT/('EVA-UN-'+unit+'.glb')));added=set(bpy.context.scene.objects)-before
 for obj in added:
  if obj.parent not in added:obj.location.x+=offset
scene=OUT/'scene.glb';bpy.ops.export_scene.gltf(filepath=str(scene),export_format='GLB',export_skins=True,export_animations=False)
(OUT/'execution_local.json').write_text(json.dumps(dict(startedAt=started,completedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),blender=bpy.app.version_string,outputs=outputs,scene=str(scene),scene_sha256=hashlib.sha256(scene.read_bytes()).hexdigest(),layout='Display comparison only: centres X=-18 and +18 blocks, both grounded at Y=0; not their world-map coordinates'),indent=2))
print('UN pair exported with real editable rigs, materials and skin weights',flush=True)
