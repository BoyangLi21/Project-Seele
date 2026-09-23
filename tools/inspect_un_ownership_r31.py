"""Colour the actual mesh by its owning bone; isolated diagnostic, not an authored gameplay clip."""
import bpy,sys,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Euler
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r31/models/ownership';OUT.mkdir(parents=True,exist_ok=True);SOURCE=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele'
CANDIDATE='--candidate' in sys.argv
if CANDIDATE:OUT=OUT/'candidate';OUT.mkdir(exist_ok=True)
colour={'torso_lower':(.8,.06,.055,1),'torso_upper':(.9,.41,.045,1),'arm':(.08,.7,.23,1),'forearm':(.85,.8,.06,1),'pylon':(.57,.09,.85,1),'leg':(.08,.25,.9,1),'shin':(.0,.66,.74,1),'hand':(.64,.7,.78,1),'head':(.8,.82,.83,1),'foot':(.28,.28,.3,1)}
reports=[]
for unit,name in [('00','eva_prototype'),('01','eva_un01')]:
    asset=ROOT/'artifacts/facility_r31/models'/('un'+unit)/'runtime/assets/projectseele' if CANDIDATE else SOURCE;stem='eva_prototype' if CANDIDATE else name
    mesh=json.loads((asset/'mesh'/(stem+'.mesh.json')).read_text());bones=json.loads((asset/'geo'/(stem+'.geo.json')).read_text())['minecraft:geometry'][0]['bones'];bones={b['name']:b for b in bones}
    for pose in ('rest','flex'):
        bpy.ops.wm.read_factory_settings(use_empty=True);matrices={};objects=[]
        def matrix(n):
            if n in matrices:return matrices[n]
            b=bones[n];pivot=Vector(np.array(b['pivot'])*[-1,1,1]);angles=np.array(b.get('rotation',[0,0,0]))*[-1,-1,1]
            if pose=='flex':
                if n.startswith('arm_'):angles[0]=-65
                if n.startswith('forearm_'):angles[0]=-45
                if n.startswith('leg_'):angles[0]=-40
                if n.startswith('shin_'):angles[0]=75;pivot=Vector(np.array(bones['r30_knee_socket_'+n[-1]]['pivot'])*[-1,1,1])
            q=Euler(np.deg2rad(angles),'XYZ').to_matrix().to_4x4();local=Matrix.Translation(pivot)@q@Matrix.Translation(-pivot);matrices[n]=matrix(b['parent'])@local if b.get('parent') else local;return matrices[n]
        stats=[]
        for n,part in mesh['parts'].items():
            a=np.asarray(part['vertices']).reshape(-1,8);p=(a[:,:3]+part['pivot'])*[-1,1,1];world=(np.c_[p,np.ones(len(p))]@np.array(matrix(n)).T)[:,:3]
            if n in mesh.get('jointSkins',{}):
                world=np.zeros_like(p)
                for bone,w in mesh['jointSkins'][n]['influences'].items():world+=((np.c_[p,np.ones(len(p))]@np.array(matrix(bone)).T)[:,:3])*np.asarray(w)[:,None]
            world*=5/16;v=world[:,[0,2,1]]*[1,-1,1]
            data=bpy.data.meshes.new(n);data.from_pydata(v,[],np.arange(len(v)).reshape(-1,3));data.update();o=bpy.data.objects.new(n,data);bpy.context.collection.objects.link(o);objects.append(o)
            owner=n.removeprefix('r21_join_');owner=next((k for k in colour if owner.startswith(k)),None);rgba=colour.get(owner,(.28,.28,.30,1));material=bpy.data.materials.new(n);material.diffuse_color=rgba;data.materials.append(material)
            for poly in data.polygons:poly.use_smooth=True
            if n in ('torso_lower','arm_l','arm_r'):stats.append(dict(bone=n,triangles=len(v)//3,extent_model=[p.min(0).tolist(),p.max(0).tolist()]))
        scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.studio_light='paint.sl';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('Ownership');scene.world.color=(.18,.18,.18);scene.view_settings.view_transform='Standard';scene.render.resolution_x=1000;scene.render.resolution_y=1400
        bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=70;scene.camera=cam
        for view,loc in [('front',(0,100,31)),('side',(100,4,32))]:
            cam.location=loc;cam.rotation_euler=(Vector((0,0,30))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/f'{unit}_{pose}_{view}.png');bpy.ops.render.render(write_still=True)
        reports.append(dict(unit=unit,pose=pose,parts=stats))
(OUT/'bone_colours.json').write_text(json.dumps(dict(colours=colour,models=reports,note='Flex is an isolated diagnostic: shoulders -65, elbow -45, hips -40, knees +75 degrees; linear weighted seam diagnostic, not a production gameplay recording (runtime uses preserve-volume skinning).'),indent=2))
print('Actual rigid ownership views complete',flush=True)
