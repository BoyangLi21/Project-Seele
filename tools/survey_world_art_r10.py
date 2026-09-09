"""Measure actual grades, planting clearance and room materials before the R10 detail work."""
import json
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scan_regional_completion import volume
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/first_battle_world_r10/world_art'
BOXES={
 'intercept_edge':((250,48,-670),(470,191,-150)),
 'tokyo_west_edge':((-900,48,20),(-650,159,640)),
 'hakone_east_edge':((-1170,48,330),(-960,159,960)),
 'geofront_west':((-800,-490,-100),(-120,-410,680)),
 'geofront_south':((-220,-490,550),(450,-410,950)),
}
def main():
 OUT.mkdir(parents=True,exist_ok=True);report={}
 for name,(lo,hi) in BOXES.items():
  dest=OUT/(name+'.npz')
  if dest.exists():continue
  a,pal=volume(lo,hi,allow_unknown=True);bare=[s.split('[')[0] for s in pal]
  known=~np.isin(a,[i for i,s in enumerate(pal) if s=='UNKNOWN']).any(axis=0)
  earth=np.array([s in {'minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:gravel','minecraft:sand','minecraft:clay','minecraft:coarse_dirt','minecraft:podzol','minecraft:rooted_dirt','minecraft:deepslate'} for s in bare])
  water=np.array([s=='minecraft:water' for s in bare]);tree=np.array([s.endswith(('_log','_leaves')) for s in bare])
  natural=np.array([s in {'minecraft:air','minecraft:cave_air','minecraft:void_air','minecraft:light','minecraft:grass','minecraft:fern','minecraft:tall_grass','minecraft:large_fern','minecraft:dandelion','minecraft:poppy','minecraft:dead_bush','minecraft:snow'} for s in bare])|earth|water|tree
  y=np.arange(lo[1],hi[1]+1)[:,None,None]
  def top(mask):return np.max(np.where(mask[a],y,lo[1]-1),axis=0).astype(np.int16)
  ground=top(earth);wet=top(water);engineered=top(~natural);vegetation=top(tree)
  np.savez_compressed(dest,lo=lo,hi=hi,ground=ground,water=wet,engineered=engineered,vegetation=vegetation,known=known)
  colors=np.zeros((*ground.shape,3),dtype=np.uint8);base=np.clip(ground-np.median(ground),-30,30)
  colors[:]=np.clip(np.array([100,134,91])[None,None,:]+base[:,:,None]*1.7,0,255)
  colors[wet>=ground]=[78,133,154];colors[vegetation>ground]=[48,87,64];colors[engineered>=ground]=[125,126,122];colors[ground<lo[1]]=[35,35,40]
  colors[~known]=[30,30,37]
  image=Image.fromarray(colors).resize((colors.shape[1]*2,colors.shape[0]*2));image.save(OUT/(name+'.png'))
  report[name]={'bounds':[lo,hi],'ground_range':[int(ground.min()),int(ground.max())],'ground_median':float(np.median(ground)),'natural_columns':int((engineered<ground).sum()),'water_columns':int((wet>=ground).sum())}
  print(name,report[name],flush=True)
 (OUT/'survey.json').write_text(json.dumps(report,indent=2),encoding='utf8')
if __name__=='__main__':main()
