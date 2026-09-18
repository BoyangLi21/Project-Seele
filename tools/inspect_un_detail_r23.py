"""Inspect existing runtime hands and optics before choosing any replacement geometry."""
import sys,runpy,argparse,json
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--unit',required=True);ap.add_argument('--asset-root',type=Path,default=ROOT/'artifacts/access_r22/models');ap.add_argument('--output',type=Path,default=ROOT/'artifacts/facility_r23/models/inspection_before');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);unit=args.unit;OUT=args.output;OUT.mkdir(parents=True,exist_ok=True)
sys.argv=['render_un_r21.py','--','--unit',unit,'--views','','--asset-root',str(args.asset_root)]
context=runpy.run_path(str(ROOT/'tools/render_un_r21.py'));scene=bpy.context.scene;scene.cycles.samples=12;scene.render.resolution_x=800;scene.render.resolution_y=900;camera=scene.camera
records=[]
for label,bones,offset,scale in [('left_hand_front',lambda n:n=='hand_l' or n.startswith('finger_') and n.endswith('_l'),(0,24,3),13),('left_hand_oblique',lambda n:n=='hand_l' or n.startswith('finger_') and n.endswith('_l'),(-18,18,10),13),('head_front',lambda n:n=='head',(0,24,1),13),('head_oblique',lambda n:n=='head',(18,24,4),13)]:
 objects=[o for o in scene.objects if o.type=='MESH' and bones(str(o.get('runtime_bone','')))];vertices=[o.matrix_world@Vector(c) for o in objects for c in o.bound_box]
 lo=Vector([min(p[i] for p in vertices) for i in range(3)]);hi=Vector([max(p[i] for p in vertices) for i in range(3)]);target=(lo+hi)*.5
 camera.location=target+Vector(offset);camera.data.ortho_scale=scale;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/('un'+unit+'_'+label+'.png'));bpy.ops.render.render(write_still=True)
 records.append(dict(unit=unit,view=label,bounds=[list(lo),list(hi)],file=scene.render.filepath))
(OUT/('un'+unit+'.json')).write_text(json.dumps(records,indent=2));print('Runtime detail views saved',unit,flush=True)
