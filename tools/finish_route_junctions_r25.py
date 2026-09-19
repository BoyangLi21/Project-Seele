"""Repair full junction sections and reverse stair rises exposed by native walking."""
import json
import regional_voxels as v,scan_regional_completion as scan,plan_factory_r20 as f
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R25_REVIEW';OUT=ROOT/'artifacts/facility_r25/junction_finish'
def main():
 v.WORLD=scan.WORLD=WORLD;v.OUT=OUT;p=v.Painter();counts={}
 f.LO=(68,-437,257);f.HI=(79,-387,284);s=f.Scene()
 for y in (-434,-420,-406,-392):
  s.fill((70,y-1,258,77,y-1,281),f.FLOOR)
  s.fill((70,y,258,77,y+2,281),'minecraft:air')
 counts['east_lift_branch_union']=s.delta(p,'r25/open_actual_lift_branch_junctions')
 f.LO=(-34,-370,-227);f.HI=(94,-360,-215);s=f.Scene()
 s.fill((-33,-369,-226,93,-368,-216),f.STRUCT)
 s.fill((-32,-368,-225,93,-368,-217),f.FLOOR)
 s.fill((-33,-361,-226,93,-361,-216),f.STRUCT)
 for z in (-226,-216):
  s.fill((-33,-367,z,93,-367,z),f.WALL);s.fill((-33,-366,z,93,-362,z),'projectseele:clear_glass')
 s.fill((-33,-367,-225,-33,-362,-217),f.WALL)
 counts['observation_continuous_deck']=s.delta(p,'r25/full_observation_gallery_floor_and_enclosure')
 for name,x0,x1,z0,top,n in [('annex_a',195,197,405,-461,5),('annex_c',257,261,275,-466,6)]:
  f.LO=(x0,top-n-2,z0);f.HI=(x1,top+3,z0+n-1);s=f.Scene()
  for k in range(n):
   y=top-k-1;z=z0+k
   s.fill((x0,y,z,x1,y,z),'minecraft:smooth_quartz_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]')
   s.fill((x0,y+1,z,x1,y+3,z),'minecraft:air')
  counts[name]=s.delta(p,'r25/'+name+'_half_step_at_upper_landing')
 p.meta.update(native_failures_addressed=counts);p.apply('junctions_and_reverse_stairs')
 (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':main()
