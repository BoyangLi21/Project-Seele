"""Bake new 4K coatings and standard PBR maps from authored Blender materials.

Original UV detail guides material regions; generated gray streaks do not replace
the requested charcoal/gold or green/blue finish. Palette tiles are baked meshes.
"""
import bpy,sys,json,argparse,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--unit',choices=('00','01'),required=True);a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);unit=a.unit
OUT=ROOT/'artifacts/facility_r30/models'/('un'+unit);DEST=OUT/'runtime/assets/projectseele/textures/entity';DEST.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(ROOT/'artifacts/facility_r30/lux3d'/('un'+unit)/'source.glb'))
body=next(o for o in bpy.context.scene.objects if o.type=='MESH');original=body.data.materials[0];bsdf=next(n for n in original.node_tree.nodes if n.type=='BSDF_PRINCIPLED');source=bsdf.inputs['Base Color'].links[0].from_node.image
uv=body.data.uv_layers.active;uv.name='UV_Source_R30';target_uv=body.data.uv_layers.new(name='UV_Game_R30')
for before,after in zip(uv.data,target_uv.data):after.uv=(before.uv.x*.9375,before.uv.y)
body.data.uv_layers.active=target_uv
def linear(hex):
    c=[int(hex[i:i+2],16)/255 for i in (1,3,5)];return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c)+(1,)
palette=json.loads((OUT/'palette.json').read_text());colours=[linear(c) for c in palette]
def setup(name):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;n=mat.node_tree.nodes;n.clear();out=n.new('ShaderNodeOutputMaterial');emit=n.new('ShaderNodeEmission');mat.node_tree.links.new(emit.outputs[0],out.inputs['Surface']);return mat,emit
def mathnode(mat,op,*values):
    n=mat.node_tree.nodes.new('ShaderNodeMath');n.operation=op
    for i,v in enumerate(values):
        if isinstance(v,(float,int)):n.inputs[i].default_value=v
        else:mat.node_tree.links.new(v,n.inputs[i])
    return n.outputs[0]
def combine(mat,values):
    n=mat.node_tree.nodes.new('ShaderNodeCombineColor');n.mode='RGB'
    for i,v in enumerate(values):
        if isinstance(v,(float,int)):n.inputs[i].default_value=v
        else:mat.node_tree.links.new(v,n.inputs[i])
    return n.outputs[0]
def mix(mat,factor,left,right):
    n=mat.node_tree.nodes.new('ShaderNodeMixRGB');mat.node_tree.links.new(factor,n.inputs[0])
    for i,v in [(1,left),(2,right)]:
        if isinstance(v,tuple):n.inputs[i].default_value=v
        else:mat.node_tree.links.new(v,n.inputs[i])
    return n.outputs[0]
mat,emission=setup('R30 source-region coating');n=mat.node_tree.nodes;links=mat.node_tree.links
tex=n.new('ShaderNodeTexImage');tex.image=source;uvnode=n.new('ShaderNodeUVMap');uvnode.uv_map='UV_Source_R30';links.new(uvnode.outputs['UV'],tex.inputs['Vector'])
sep=n.new('ShaderNodeSeparateColor');sep.mode='RGB';links.new(tex.outputs['Color'],sep.inputs[0]);r,g,b=sep.outputs[:3]
bw=n.new('ShaderNodeRGBToBW');links.new(tex.outputs['Color'],bw.inputs[0]);luma=bw.outputs[0]
warm=mathnode(mat,'MULTIPLY',mathnode(mat,'GREATER_THAN',mathnode(mat,'DIVIDE',r,mathnode(mat,'MAXIMUM',b,.001)),1.27),mathnode(mat,'GREATER_THAN',r,mathnode(mat,'MULTIPLY',g,1.02)))
dark=mathnode(mat,'LESS_THAN',luma,.018)
blue=mathnode(mat,'MULTIPLY',mathnode(mat,'GREATER_THAN',b,mathnode(mat,'MULTIPLY',r,1.10)),mathnode(mat,'GREATER_THAN',b,mathnode(mat,'MULTIPLY',g,1.025)))
if unit=='00':
    # Gold is authored as clean machined rims and inlays. The generated hue
    # mask had ragged patches that read as peeling paint at close range.
    base=combine(mat,colours[0][:3]);rough=.34;metal=0.;f0=.06
else:
    # Anatomical paint regions are defined in measured model space. Hard
    # thresholding a generated photograph had produced chipped blue/tan noise.
    from mathutils import Vector
    corners=[body.matrix_world@Vector(p) for p in body.bound_box];lo=[min(p[i] for p in corners) for i in range(3)];hi=[max(p[i] for p in corners) for i in range(3)];scale=193.1/(hi[2]-lo[2])
    geometry=n.new('ShaderNodeNewGeometry');coordinates=n.new('ShaderNodeSeparateXYZ');links.new(geometry.outputs['Position'],coordinates.inputs[0]);wx,wy,wz=coordinates.outputs
    x=mathnode(mat,'MULTIPLY',mathnode(mat,'SUBTRACT',(lo[0]+hi[0])*.5,wx),scale);y=mathnode(mat,'MULTIPLY',mathnode(mat,'SUBTRACT',wz,lo[2]),scale);z=mathnode(mat,'MULTIPLY',wy,scale);ax=mathnode(mat,'ABSOLUTE',x)
    def both(*values):
        result=values[0]
        for value in values[1:]:result=mathnode(mat,'MULTIPLY',result,value)
        return result
    def band(value,low,high):return both(mathnode(mat,'GREATER_THAN',value,low),mathnode(mat,'LESS_THAN',value,high))
    def ellipse(a,b,ar,br):return mathnode(mat,'LESS_THAN',mathnode(mat,'ADD',mathnode(mat,'POWER',mathnode(mat,'DIVIDE',a,ar),2),mathnode(mat,'POWER',mathnode(mat,'DIVIDE',b,br),2)),1)
    upper=mathnode(mat,'ADD',136,mathnode(mat,'MULTIPLY',ax,.35))
    abdomen=both(mathnode(mat,'LESS_THAN',ax,19),mathnode(mat,'GREATER_THAN',y,132.5),mathnode(mat,'LESS_THAN',y,upper),mathnode(mat,'LESS_THAN',z,3))
    upper_arm=both(mathnode(mat,'GREATER_THAN',ax,27),band(y,136,142))
    blue=mathnode(mat,'MAXIMUM',abdomen,upper_arm)
    elbow=both(mathnode(mat,'GREATER_THAN',ax,28),band(y,130.5,136))
    knee=both(ellipse(mathnode(mat,'SUBTRACT',ax,25.5),mathnode(mat,'SUBTRACT',y,65),5.5,7),mathnode(mat,'GREATER_THAN',z,-6))
    neck=both(mathnode(mat,'LESS_THAN',ax,5),band(y,161,169),mathnode(mat,'GREATER_THAN',z,2))
    spine=both(mathnode(mat,'LESS_THAN',ax,4),band(y,123,150),mathnode(mat,'GREATER_THAN',z,2))
    hip=both(band(ax,8,21),band(y,104,116),mathnode(mat,'GREATER_THAN',z,2))
    rear_shin=both(band(y,28,52),mathnode(mat,'GREATER_THAN',z,3),mathnode(mat,'LESS_THAN',mathnode(mat,'ABSOLUTE',mathnode(mat,'SUBTRACT',ax,mathnode(mat,'SUBTRACT',38.7,mathnode(mat,'MULTIPLY',y,.15)))),3.6))
    forearm_x=mathnode(mat,'SUBTRACT',72.2,mathnode(mat,'MULTIPLY',y,.269));vent=both(ellipse(mathnode(mat,'SUBTRACT',ax,forearm_x),mathnode(mat,'SUBTRACT',y,119.5),2.1,6.7),mathnode(mat,'LESS_THAN',z,-3))
    sole=mathnode(mat,'LESS_THAN',y,3.2)
    dark=elbow
    for region in (knee,neck,spine,hip,rear_shin,vent,sole):dark=mathnode(mat,'MAXIMUM',dark,region)
    tan=mathnode(mat,'MAXIMUM',both(band(ax,18.5,33.5),band(y,61.5,84.5),mathnode(mat,'LESS_THAN',z,-7)),both(band(ax,29,42),band(y,14,25),mathnode(mat,'GREATER_THAN',z,2.5)))
    face=both(band(y,164,179),mathnode(mat,'LESS_THAN',ax,mathnode(mat,'MINIMUM',7,mathnode(mat,'MULTIPLY',mathnode(mat,'SUBTRACT',y,163),.65))),mathnode(mat,'LESS_THAN',z,1))
    base=mix(mat,blue,colours[0],colours[2]);base=mix(mat,tan,base,colours[6]);rough=mathnode(mat,'ADD',.42,mathnode(mat,'MULTIPLY',blue,.17));metal=0.;f0=.045
base=mix(mat,dark,base,colours[1]);rough=mathnode(mat,'ADD',rough,mathnode(mat,'MULTIPLY',dark,.18))
outputs={'base':base,'mr':combine(mat,[1.,rough,metal]),'s':combine(mat,[mathnode(mat,'SUBTRACT',1.,rough),f0,0.]),'n':combine(mat,[.5,.5,1.])}
body.data.materials.clear();body.data.materials.append(mat);materials=[(mat,emission,outputs)]
vertices=[];faces=[]
for i in range(12):
    x=5+i*2;vertices.extend([(x,0,0),(x+1,0,0),(x+1,0,1),(x,0,1)]);faces.append(tuple(range(i*4,i*4+4)))
mesh=bpy.data.meshes.new('UV palette tiles');mesh.from_pydata(vertices,[],faces);mesh.update();tiles=bpy.data.objects.new('Bake-only material tiles',mesh);bpy.context.collection.objects.link(tiles);mesh.uv_layers.new(name='UV_Source_R30');tiles_uv=mesh.uv_layers.new(name='UV_Game_R30');mesh.uv_layers.active=tiles_uv
for i,p in enumerate(mesh.polygons):
    col,row=i%4,i//4;u0=.9375+col*.0625/4;u1=.9375+(col+1)*.0625/4;v0=1-(row+1)/3;v1=1-row/3
    for li,coord in zip(p.loop_indices,[(u0,v0),(u1,v0),(u1,v1),(u0,v1)]):tiles_uv.data[li].uv=coord
    material,emit=setup('R30 material '+str(i));mesh.materials.append(material);p.material_index=i
    is_gold=unit=='00' and i in (4,6);is_metal=is_gold or i in (2,3) and unit=='00';roughness=.23 if is_gold else .32 if is_metal else .6 if i in (1,5) else .42
    f0_value=231/255 if is_gold else 230/255 if is_metal else .045
    base_colour=colours[i]
    if i in (7,11):base_colour=tuple(c*.18 for c in base_colour[:3])+(1,)
    material_outputs={'base':base_colour,'mr':(1.,roughness,float(is_metal),1.),'s':(1-roughness,f0_value,0.,1.),'n':(.5,.5,1.,1.),'eyes':colours[i]}
    materials.append((material,emit,material_outputs))
# Keep a separate pair of emissive tiles so unused UV space remains transparent.
eyes_mesh=mesh.copy();eyes=bpy.data.objects.new('Bake-only powered optical and nozzle cells',eyes_mesh);bpy.context.collection.objects.link(eyes)
import bmesh
bm=bmesh.new();bm.from_mesh(eyes_mesh);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index not in (7,11)],context='FACES');bm.to_mesh(eyes_mesh);bm.free()
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);tiles.select_set(True);bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.render.bake.margin=16;scene.render.bake.use_clear=True
gpu=[]
try:
    settings=bpy.context.preferences.addons['cycles'].preferences;settings.compute_device_type='OPTIX';settings.get_devices()
    for device in settings.devices:device.use=device.type=='OPTIX';gpu.extend([device.name] if device.use else [])
    if gpu:scene.cycles.device='GPU'
except Exception as error:print('GPU bake unavailable; CPU fallback:',str(error),flush=True)
print('Baking device',gpu or ['CPU'],flush=True)
records=[]
for key,suffix in [('base',''),('mr','_mr'),('s','_s'),('n','_n'),('eyes','_eyes')]:
    image=bpy.data.images.new('UN-'+unit+suffix+' 4K',4096,4096,alpha=True);image.generated_color=(0,0,0,0);image.colorspace_settings.name='sRGB' if key in ('base','eyes') else 'Non-Color'
    for material,emit,values in materials:
        tree=material.node_tree
        for link in list(emit.inputs['Color'].links):tree.links.remove(link)
        value=values.get(key,(0,0,0,1))
        if isinstance(value,tuple):emit.inputs['Color'].default_value=value
        else:tree.links.new(value,emit.inputs['Color'])
        target=tree.nodes.new('ShaderNodeTexImage');target.image=image;tree.nodes.active=target
    bpy.ops.object.select_all(action='DESELECT');active=eyes if key=='eyes' else body;active.select_set(True);bpy.context.view_layer.objects.active=active
    bpy.ops.object.bake(type='EMIT')
    if key=='eyes':
        import numpy as np
        pixels=np.empty(len(image.pixels),np.float32);image.pixels.foreach_get(pixels);pixels=pixels.reshape(-1,4);pixels[:,3]=(np.max(pixels[:,:3],axis=1)>.00001).astype(np.float32);image.pixels.foreach_set(pixels.ravel());image.update()
    path=DEST/('eva_prototype'+suffix+'.png');image.filepath_raw=str(path);image.file_format='PNG';image.save();records.append({'kind':key,'path':str(path),'width':4096,'height':4096});print('Baked',path.name,flush=True)
    for material,_,_ in materials:
        for node in list(material.node_tree.nodes):
            if node.type=='TEX_IMAGE' and node.image==image:material.node_tree.nodes.remove(node)
    bpy.data.images.remove(image)
(OUT/'material_bake.json').write_text(json.dumps({'device':gpu or ['CPU'],'maps':records,'palette':palette,'labpbr':'shaderLABS 1.3; smoothness R, F0/metal G, gold231; normals XY/AO/height. Emissive layer is switched by runtime power state.','source_uv_retained':True,'coatings':'Authored charcoal/gold or green/blue materials, not an upscaled source picture'},indent=2))
