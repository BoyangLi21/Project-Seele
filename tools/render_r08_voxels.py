"""Render measured voxel exports in several honest exterior/cutaway views."""
import bpy,numpy as np,sys,json
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:];path=Path(args[0]).resolve();stem=args[1] if len(args)>1 else path.stem
data=np.load(path);v=data['vertices'][:,[0,2,1]].copy();v[:,1]*=-1
bpy.ops.wm.read_factory_settings(use_empty=True)
me=bpy.data.meshes.new('Measured blocks');me.from_pydata(v,[],data['faces']);me.update();obj=bpy.data.objects.new('Measured blocks',me);bpy.context.collection.objects.link(obj)
for i,c in enumerate(data['colors']):
    m=bpy.data.materials.new(str(i));m.diffuse_color=(*[float(x)/255 for x in c],1);me.materials.append(m)
me.polygons.foreach_set('material_index',data['materials'].astype(np.int32))
if path.stem.startswith('dogma_'):
    pose=json.loads((path.parent/'lilith_pose.json').read_text());assert abs(pose['yaw'])<.01
    colours={'body':(224,221,207),'face_dark':(55,51,61),'mask':(107,87,139),'nails':(63,66,69),'spear':(149,33,34),'eyes':(221,197,123)}
    for layer,c in colours.items():
        source=Path('D:/eva/run/resourcepacks/eva_real_model/assets/projectseele/mesh')/('lilith_'+layer+'.mesh.json');d=json.loads(source.read_text());vs=[];fs=[]
        for part in d['parts'].values():
            vv=np.array(part['vertices']).reshape(-1,d['stride'])[:,:3]+np.array(part['pivot']);vv*=.82*pose['containmentScale']/16;vv[:,2]*=-1;vv+=pose['position'];vv=vv[:,[0,2,1]];vv[:,1]*=-1
            offset=len(vs);vs.extend(vv.tolist());fs.extend([[offset+i,offset+i+1,offset+i+2] for i in range(0,len(vv),3)])
        lm=bpy.data.meshes.new('Lilith '+layer);lm.from_pydata(vs,[],fs);lm.update();obj=bpy.data.objects.new('Saved Lilith pose '+layer,lm);bpy.context.collection.objects.link(obj);mat=bpy.data.materials.new(layer);mat.diffuse_color=(*[x/255 for x in c],1);lm.materials.append(mat)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';sh=scene.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.show_specular_highlight=False;sh.background_type='WORLD';scene.world=bpy.data.worlds.new('Paper');scene.world.color=(.9,.92,.91)
scene.render.resolution_x=1800;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.view_settings.view_transform='Standard'
cam=bpy.data.objects.new('Equal-scale orthographic',bpy.data.cameras.new('Camera'));bpy.context.collection.objects.link(cam);cam.data.type='ORTHO';cam.data.clip_end=10000;scene.camera=cam
points=[Vector(p) for p in v[::max(1,len(v)//40000)]];center=Vector((v.min(0)+v.max(0))/2)
views=[('angle_a',(1.2,-1.6,1.0)),('angle_b',(-1.5,1.1,.9)),('side',(0,-1,.18))]
if len(args)>2 and args[2]=='one':
    direction=(1.5,1.2,.95) if 'entrance_section' in path.stem else (1.5,-1.1,.9)
    views=[('view',direction)]
for name,dr in views:
    dr=Vector(dr).normalized();cam.location=center+dr*3000;cam.rotation_euler=(-dr).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update();inv=cam.matrix_world.inverted();p=[inv@v for v in points];lo=[min(q[i] for q in p) for i in (0,1)];hi=[max(q[i] for q in p) for i in (0,1)];cam.location+=cam.rotation_euler.to_quaternion()@Vector(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,0));cam.data.ortho_scale=max(hi[0]-lo[0],(hi[1]-lo[1])*1800/1100)*1.08
    scene.render.filepath=str(path.parent/(stem+'_'+name+'.png'));bpy.ops.render.render(write_still=True)
