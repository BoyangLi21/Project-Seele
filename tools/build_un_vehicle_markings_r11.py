"""Model-space UN stencils on the installed local vehicle models.

The original texture and animation are retained. Tiny ink polygons inherit their
actual armour/wing bone, so markings follow pitch, roll and turret articulation.
The third-party geometry remains in the private resource pack.
"""
import copy,json,zipfile,io,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import minimum_filter
ROOT=Path(__file__).resolve().parents[1];PACK=ROOT/'run/resourcepacks/eva_real_model';OUT=ROOT/'artifacts/world_motion_r11/un'
JAR=ROOT/'.Codex/local-mods/superbwarfare-0.8.9.1-hotfix-mc1.20.1-993063bed-all.jar'
def masks():
 a=Image.new('L',(64,40),0);d=ImageDraw.Draw(a);f=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',37);d.text((3,-3),'UN',font=f,fill=255)
 return np.array(a)>140
def colour_pixel(image,bright=True,emissive=None):
 a=np.array(image.convert('RGBA'));solid=minimum_filter(a[:,:,3],size=3)>250;mean=a[:,:,:3].astype(float).mean(-1)
 if emissive is not None:
  e=np.array(emissive.convert('RGBA'));solid &= e[:,:,:3].max(-1)<25
 score=minimum_filter(mean,size=3) if bright else -minimum_filter(-mean,size=3);score=np.where(solid,score if bright else -score,-1e9);y,x=np.unravel_index(score.argmax(),score.shape)
 return [float(x)+.25,float(y)+.25]
def top_mark(bone,cube,width,depth,u=.5):
 x,y,z=cube['origin'];sx,sy,sz=cube['size'];cx=x+sx*u;cz=z+sz*.5;mask=masks();items=[];rows,cols=mask.shape
 for row in range(rows):
  col=0
  while col<cols:
   if not mask[row,col]:col+=1;continue
   start=col
   while col<cols and mask[row,col]:col+=1
   q={'origin':[cx-width/2+start/cols*width,y+sy+cube.get('inflate',0)+.025,cz-depth/2+row/rows*depth],'size':[(col-start)/cols*width,.025,depth/rows]}
   for key in ['rotation','pivot']:
    if key in cube:q[key]=cube[key]
   items.append(q)
 return items

def side_mark(cube,width,height,side,u=.42):
 x,y,z=cube['origin'];sx,sy,sz=cube['size'];cy=y+sy*.5;cz=z+sz*u;mask=masks();items=[];rows,cols=mask.shape
 for row in range(rows):
  col=0
  while col<cols:
   if not mask[row,col]:col+=1;continue
   start=col
   while col<cols and mask[row,col]:col+=1
   zz=cz-width/2+start/cols*width if side>0 else cz+width/2-col/cols*width
   inflate=cube.get('inflate',0)
   q={'origin':[x+sx+inflate+.035 if side>0 else x-inflate-.06,cy+height/2-(row+1)/rows*height,zz], 'size':[.025,height/rows,(col-start)/cols*width]}
   for key in ['rotation','pivot']:
    if key in cube:q[key]=cube[key]
   items.append(q)
 return items

def palette_patch(geo,image):
 # Reserve only pixels outside every original UV rectangle, including a guard
 # for filtering. The atlas dimensions and all used pixels stay unchanged.
 width,height=image.size;sx=width/geo['description']['texture_width'];sy=height/geo['description']['texture_height'];used=np.zeros((height,width),bool)
 def mark(u,v,w,h):
  a,b=sorted((u,u+w));c,d=sorted((v,v+h));x0=max(0,int(np.floor(a*sx))-4);x1=min(width,int(np.ceil(b*sx))+5);y0=max(0,int(np.floor(c*sy))-4);y1=min(height,int(np.ceil(d*sy))+5);used[y0:y1,x0:x1]=True
 for bone in geo['bones']:
  if 'poly_mesh' in bone:
   poly=bone['poly_mesh'];uvs=np.array(poly['uvs'],float)
   if poly.get('normalized_uvs',False):uvs*=np.array([geo['description']['texture_width'],geo['description']['texture_height']])
   for face in poly['polys']:
    points=uvs[[int(corner[2]) for corner in face]];lo=points.min(0);hi=points.max(0);mark(*lo,*(hi-lo))
    # Normalized polygon exporters use both V conventions; reserving both is conservative.
    mark(lo[0],geo['description']['texture_height']-hi[1],hi[0]-lo[0],hi[1]-lo[1])
  for cube in bone.get('cubes',[]):
   uv=cube.get('uv',{})
   if isinstance(uv,list):
    x,y,z=cube['size'];mark(*uv,2*(x+z),y+z)
   else:
    for face in uv.values():mark(*face['uv'],*face.get('uv_size',[0,0]))
 for hh,ww in [(10,20),(8,16),(6,12)]:
  free=minimum_filter((~used).astype('uint8'),size=(hh,ww),mode='constant',cval=0);points=np.argwhere(free)
  if len(points):break
 else:raise RuntimeError('No unreferenced palette space')
 cy,cx=map(int,points[-1]);x0=cx-ww//2;y0=cy-hh//2;x1=x0+ww;y1=y0+hh
 if used[y0:y1,x0:x1].any():raise RuntimeError('Palette guard overlap')
 out=image.convert('RGBA');draw=ImageDraw.Draw(out);draw.rectangle((x0,y0,x0+ww//2-1,y1-1),fill=(242,244,246,255));draw.rectangle((x0+ww//2,y0,x1-1,y1-1),fill=(10,12,14,255))
 return out,[(x0+ww*.25)/sx,(y0+hh*.5)/sy],[(x0+ww*.75)/sx,(y0+hh*.5)/sy],(x0,y0,x1,y1),np.array([1/sx,1/sy])
def main():
 OUT.mkdir(exist_ok=True);manifest=[]
 with zipfile.ZipFile(JAR) as archive:
  for name in ['m_1a_2','t_90a','ztz_99a','j_16','kv_16','a_10a','ah_6']:
   path='assets/superbwarfare/models/bedrock/vehicle/'+name+'.geo.json';source=archive.read(path);data=json.loads(source);geo=data['minecraft:geometry'][0];bones={b['name']:b for b in geo['bones']};chosen=[]
   def chain(n):
    out=[]
    while n is not None:out.append(n);n=bones[n].get('parent')
    return out
   if name=='j_16':chosen=[(bones[n],bones[n]['cubes'][1],.5) for n in ['wingL','wingL2']]
   elif name=='a_10a':chosen=[(bones[n],bones[n]['cubes'][4],.5) for n in ['zuoyi','youyi']]
   elif name=='ah_6':chosen=[(bones['bone4'],bones['bone4']['cubes'][54],.5)]
   elif name=='kv_16':chosen=[(bones['chi'],bones['chi']['cubes'][1],.5)]
   else:
    candidates=[]
    for b in geo['bones']:
     parents=chain(b['name']);text='/'.join(parents).lower()
     if any(s in text for s in ['propeller','rotor','wheel','barrel','track','gun']):continue
     for cube in b.get('cubes',[]):
      sx,sy,sz=cube['size'];rotation=cube.get('rotation',[0,0,0]);score=sx*sz
      if name in ['m_1a_2','t_90a','ztz_99a'] and 'turret' not in parents:continue
      if sx<7 or sz<8 or abs(rotation[0])>35 or abs(rotation[2])>35:continue
      candidates.append((score,b,cube))
    if not candidates:raise RuntimeError('No reviewed armour surface for '+name)
    _,b,cube=max(candidates,key=lambda r:r[0]);chosen=[(b,cube,.5)]
   tex='assets/superbwarfare/textures/bedrock/vehicle/'+name+'.png';image=Image.open(io.BytesIO(archive.read(tex)));ep=tex[:-4]+'_e.png';em=Image.open(io.BytesIO(archive.read(ep))) if ep in archive.namelist() else None
   texture,white,black,reserved,scale=palette_patch(geo,image)
   texture_target=PACK/tex;texture_target.parent.mkdir(parents=True,exist_ok=True);texture.save(texture_target)
   auxiliary=[]
   prefix=tex[:-4]+'_'
   for asset in archive.namelist():
    if not asset.startswith(prefix) or not asset.endswith('.png'):continue
    original=Image.open(io.BytesIO(archive.read(asset))).convert('RGBA')
    if original.size!=image.size:continue
    aux=original.copy();x0,y0,x1,y1=reserved;ImageDraw.Draw(aux).rectangle((x0,y0,x1-1,y1-1),fill=(127,127,255,255) if asset.endswith('_n.png') else (0,0,0,0));aux.save(PACK/asset);auxiliary.append(asset)
   count=0;mounts=[]
   side_specs={'m_1a_2':[('bone22',0,-1),('bone2',0,1)],'t_90a':[('bone56',0,-1),('bone3',0,1)],'ztz_99a':[('wheel_armor_right',0,-1),('wheel_armor_left',0,1)]}
   if name=='ah_6':
    # The Loach has an open/glazed cabin and a narrow tail. Use small bolt-on
    # identification armour on the cabin frame, clear of the gun and rotor.
    side_specs[name]=[]
    for side in [-1,1]:
     plate={'origin':[11.5 if side>0 else -11.68,16.5,-7],'size':[.18,8,14],'uv':{face:{'uv':black,'uv_size':(.25*scale).tolist()} for face in ['north','south','east','west','up','down']}}
     bone=bones['bone4'];bone['cubes'].append(plate);side_specs[name].append(('bone4',len(bone['cubes'])-1,side))
   surface=[(b,c,u,0) for b,c,u in chosen]
   if name in side_specs:surface=[(bones[n],bones[n]['cubes'][i],.42,side) for n,i,side in side_specs[name]]
   for number,(bone,cube,u,side) in enumerate(surface):
    if side:
     width=min(26,cube['size'][2]*.8);depth=min(11,cube['size'][1]*.8,width*.625);ink=side_mark(cube,width,depth,side,u)
    else:
     width=min(cube['size'][0]*(.62 if name=='ah_6' else .80 if name=='a_10a' else .65),25 if name in ['j_16','a_10a'] else 19);depth=min(cube['size'][2]*.76,width*.625);ink=top_mark(bone,cube,width,depth,u)
    cubes=[]
    for black_layer in [True,False]:
     for c in ink:
      c=copy.deepcopy(c)
      if black_layer:
       if side:c['origin'][1]-=.10;c['origin'][2]-=.10;c['size'][1]+=.20;c['size'][2]+=.20;c['origin'][0]-=side*.008
       else:c['origin'][0]-=.10;c['origin'][2]-=.10;c['size'][0]+=.20;c['size'][2]+=.20;c['origin'][1]-=.008
      uv=black if black_layer else white;c['uv']={face:{'uv':uv,'uv_size':(.5*scale).tolist()} for face in ['north','south','east','west','up','down']};cubes.append(c)
    bone['cubes'].extend(cubes);count+=len(cubes);mounts.append(dict(parent=bone['name'],source_cube=cube,width=width,depth=depth,u=u,side=side))
   target=PACK/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(data,separators=(',',':')),encoding='utf8');manifest.append(dict(vehicle=name,source_sha256=hashlib.sha256(source).hexdigest(),mounts=mounts,ink_cubes=count,white_texel=white,black_texel=black,original_uv_rectangles_and_atlas_dimensions_preserved=True,unreferenced_palette_pixels=reserved,patched_auxiliary_textures=auxiliary));print(name,'mounted ink',count,'unreferenced palette',reserved,flush=True)
 (OUT/'vehicle_stencils.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
if __name__=='__main__':main()
