"""A supported interception avenue at the measured northeast city edge, tied to the Y80 street grid."""
import argparse,json,math
import numpy as np
import regional_voxels as vox
from scan_regional_completion import volume
from survey_world_art_r10 import OUT
def build():
 p=vox.Painter();data=np.load(OUT/'intercept_edge.npz');lo=data['lo'];g=data['ground'];known=data['known'];eng=data['engineered'];owner='r10/intercept_avenue'
 # The existing east-west streets at Z -450 and -300 are both exactly Y80.
 for cx in range(288//16,432//16+1):
  for cz in range(-544//16,-240//16+1):
   heights=np.zeros((16,16),int);active=np.zeros((16,16),bool)
   for dz in range(16):
    for dx in range(16):
     x,z=cx*16+dx,cz*16+dz;ix,iz=x-lo[0],z-lo[2]
     if not(0<=iz<g.shape[0] and 0<=ix<g.shape[1]) or not known[iz,ix]:continue
     old=int(g[iz,ix]);distance=math.hypot(max(316-x,0,x-396),max(-512-z,0,z+278))
     if distance>=32 or eng[iz,ix]>=old:continue
     t=distance/32;t=t*t*(3-2*t);heights[dz,dx]=round(80*(1-t)+old*t);active[dz,dx]=True
   if active.any():p.heightfield(cx,cz,heights,active,owner+'/supported_slope')
 # Every occupied cell is within a measured natural strip, beside the preserved city grid.
 p.fill(316,80,-512,396,80,-278,'minecraft:smooth_stone',owner+'/pavement','new')
 p.fill(320,80,-510,392,80,-280,'minecraft:gray_concrete',owner+'/carriageway','new')
 for x in (320,392):p.fill(x,80,-508,x,80,-282,'minecraft:white_concrete',owner+'/edge_line','new')
 for z in range(-504,-286,14):
  for x in (329,383):p.fill(x,80,z,x,80,z+6,'minecraft:white_concrete',owner+'/road_marking','new')
 # Cross streets remain continuous and flush; the central strip admits the 60m airframe.
 for z in (-450,-300):
  p.fill(289,80,z-6,320,80,z+6,'minecraft:gray_concrete',owner+'/city_connection','new')
  for x in range(308,320,3):p.fill(x,80,z-4,x+1,80,z+4,'minecraft:white_concrete',owner+'/pedestrian_crossing','new')
 for x in (315,397):
  for z in range(-495,-294,40):
   p.fill(x,81,z,x,87,z,'minecraft:iron_bars[east=false,north=false,south=false,waterlogged=false,west=false]',owner+'/lighting','air')
   p.put(x,88,z,'projectseele:nerv_strip_light',owner+'/lighting','air')
 # Flush gutters and drain covers cannot become ankle-height collision obstacles.
 for x in (319,393):
  p.fill(x,80,-508,x,80,-282,'minecraft:polished_deepslate',owner+'/drain','new')
  for z in range(-500,-286,24):p.put(x,80,z,'minecraft:iron_trapdoor[facing=north,half=top,open=false,powered=false,waterlogged=false]',owner+'/drain_grille','new')
 p.meta['first_battle_site']=dict(dimension='projectseele:geofront',hero=[356.5,81,-459.5],angel=[356.5,81,-425.5],yaw=0,avenue=[316,80,-512,396,80,-278],console=[84,-433,274],label='第六防衛線 / Northeast interception avenue',source='Measured Y80 Tokyo-3 east street grid; new avenue supported by continuous natural-material embankments')
 p.meta['landmarks'].append(dict(id=owner,center=[356,81,-395],purpose='EVA interception avenue and two city street connections'))
 vox.OUT=OUT;return p
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args();p=build()
 if args.apply:
  p.apply('interception_avenue')
  # World-specific marker is read only by the matching world's mission console.
  (vox.WORLD/'first_battle_site_r10.json').write_text(json.dumps(p.meta['first_battle_site'],ensure_ascii=False,indent=2),encoding='utf8')
 else:p.save_plan('interception_avenue')
