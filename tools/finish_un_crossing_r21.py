"""Open the measured existing UN apron crossing through new pedestrian rails."""
import regional_voxels as v
from query_blocks import read_box
def main():
 v.WORLD=v.ROOT/'run/saves/SEELE_R21_REVIEW';v.OUT=v.ROOT/'artifacts/world_repair_r21/details';p=v.Painter()
 for x in (6709,6715):
  for q,s in read_box(v.WORLD,v.DIM,(x,75,-6086),(x,75,-6074)).items():
   if s.startswith('minecraft:iron_bars['):p.match((*q,*q),s,'minecraft:air','r21/retained_UN_apron_crossing')
 p.meta.update(reason='Four complete original road routes encountered the new boarding footway fence',crossing_floor=74,continuous_road_width=13)
 p.apply('UN_apron_crossing_openings')
if __name__=='__main__':main()
