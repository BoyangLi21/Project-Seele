import bpy,json,math
from pathlib import Path
from mathutils import Matrix
root=Path('D:/eva');src=root/'external-assets/incoming/mocap/mco-demo-v2';out=root/'run/resourcepacks/eva_real_model/assets/projectseele/motion';out.mkdir(parents=True,exist_ok=True)
C=Matrix(((-1,0,0),(0,0,1),(0,1,0)))
data={'source':'Motus Digital MoCap Online Demo Pack v2; private local game retarget only','fps':30,'clips':{}}
for name,file in [('idle','W2_Stand_Aim_Idle_v2.fbx'),('walk','W2_Walk_Aim_F_Loop_IPC.fbx'),('run','W2_Jog_Aim_F_Loop_IPC.fbx')]:
 bpy.ops.wm.read_factory_settings(use_empty=True);p=next(src.rglob(file));bpy.ops.import_scene.fbx(filepath=str(p));a=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');sc=bpy.context.scene;start,end=map(round,a.animation_data.action.frame_range);frames=[]
 for f in range(start,end+1):
  sc.frame_set(f);qs=[]
  for n in ['spine_02','spine_03']:
   pb=a.pose.bones[n];rest=a.matrix_world.to_3x3()@pb.bone.matrix_local.to_3x3();pose=a.matrix_world.to_3x3()@pb.matrix.to_3x3();qs.append((C@pose@rest.inverted()@C.inverted()).to_quaternion().normalized())
  qs[1]=qs[0].inverted()@qs[1]
  frames.append([[round(v,7) for v in q] for q in qs])
 data['clips'][name]={'duration':(end-start)/30,'frames':frames};print('RETARGET',name,len(frames),[[round(math.degrees(v),2) for v in q.to_euler('XYZ')] for q in qs])
(out/'rifle_mocap_r04.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
