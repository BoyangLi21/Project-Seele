"""Measured sections and exposed-face meshes; never inferred floor plans."""
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from export_spatial_twin import surface_meshes,Bounds

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r21'
COLORS=[(244,244,241),(93,102,110),(174,191,199),(212,123,34),(75,156,126),(42,66,98),(244,206,57),(145,53,63)]
def code(s):
 if s in ('minecraft:air','minecraft:cave_air','minecraft:void_air') or s.startswith('minecraft:light['):return 0
 if 'glass' in s:return 2
 if 'escalator' in s:return 3
 if 'stairs' in s:return 4
 if 'floor' in s or s in ('minecraft:smooth_stone','minecraft:polished_deepslate'):return 5
 if 'light' in s or 'lantern' in s:return 6
 if any(v in s for v in ('door','elevator','button','platform')):return 7
 return 1

def main():
 font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',15)
 for name,levels in [('pyramid_east',[-449,-443,-442,-438]),('factory_east',[-443,-442,-395,-394,-370,-369]),('cages',[-395,-394,-369,-367])]:
  d=np.load(OUT/'survey'/name/'measured.npz');a=d['blocks'];pal=d['palette'];lo=d['lo'];hi=d['hi'];c=np.asarray([code(s) for s in pal],np.uint8)[a]
  scale=4 if name=='factory_east' else 5
  w,h=c.shape[2]*scale+60,c.shape[1]*scale+55
  im=Image.new('RGB',(w*len(levels),h),'white');draw=ImageDraw.Draw(im)
  for k,y in enumerate(levels):
   slab=c[y-lo[1]];pic=Image.fromarray(np.array(COLORS,np.uint8)[slab]).resize((slab.shape[1]*scale,slab.shape[0]*scale),Image.Resampling.NEAREST);im.paste(pic,(k*w+45,35))
   draw.text((k*w+45,7),f'{name} Y={y}',fill='black',font=font)
   for x in range(((lo[0]+9)//10)*10,hi[0]+1,10):draw.text((k*w+45+(x-lo[0])*scale,20),str(x),fill='black',font=font)
   for z in range(((lo[2]+19)//20)*20,hi[2]+1,20):draw.text((k*w+2,35+(z-lo[2])*scale),str(z),fill='black',font=font)
  im.save(OUT/'survey'/(name+'_sections.png'))
  # Honest cut bands expose old rails, parapets and openings at every level.
  for low,high in ([(-447,-437),(-399,-390),(-373,-364)] if name=='factory_east' else [(-450,-438)] if name=='pyramid_east' else [(-371,-365)]):
   cut=c[max(low-lo[1],0):high-lo[1]+1].transpose(2,0,1)
   bounds=Bounds(int(lo[0]),int(hi[0]),max(int(lo[1]),low),high,int(lo[2]),int(hi[2]))
   pieces=surface_meshes(cut,bounds,1);vertices=[];faces=[];materials=[]
   for material,(v,f) in pieces.items():
    n=sum(len(q) for q in vertices);vertices.append(v);faces.append(f.reshape(-1,3)+n);materials.extend([material]*len(f.reshape(-1,3)))
   np.savez_compressed(OUT/'survey'/f'{name}_{low}.npz',vertices=np.concatenate(vertices),faces=np.concatenate(faces),materials=materials,colors=COLORS)
  print(name,'sections and meshes ready',flush=True)
if __name__=='__main__':main()
