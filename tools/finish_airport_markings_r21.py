"""Restore continuous runway markings after the curved taxi apron was paved."""
import regional_voxels as v
v.WORLD=v.ROOT/'run/saves/SEELE_R21_REVIEW';v.OUT=v.ROOT/'artifacts/world_repair_r21/airport/markings'
p=v.Painter()
def paint(x,z,X,Z,state):
 for old in ('minecraft:gray_concrete','minecraft:black_concrete','minecraft:white_concrete','minecraft:yellow_concrete'):
  p.match((x,72,z,X,72,Z),old,state,'r21/continuous_runway_paint')
for z in (-145,-95):
 paint(710,z-17,1350,z+17,'minecraft:black_concrete')
 for zz in (z-16,z+16):paint(710,zz,1350,zz,'minecraft:white_concrete')
 for x in range(790,1295,28):paint(x,z-1,x+11,z+1,'minecraft:white_concrete')
 for x in (723,1317):
  for zz in range(z-12,z+13,4):paint(x,zz,x+12,zz+1,'minecraft:white_concrete')
 # Clear touchdown aiming bars, placed symmetrically about each centreline.
 for x in (830,1220):
  for zz in (z-10,z+8):paint(x,zz,x+13,zz+2,'minecraft:white_concrete')
for x in (545,645,746,806):
 paint(x-13,41,x+13,41,'minecraft:yellow_concrete')
 paint(x,42,x,65,'minecraft:yellow_concrete')
 for xx in (x-23,x+23):paint(xx,39,xx,76,'minecraft:white_concrete')
p.meta.update(cosmetic_only=True,collision_unchanged='All replacements are full concrete cubes at the same Y72 datum',reason='Taxi sweeps had overwritten portions of the painted runway')
p.apply('continuous_runways_and_stand_lines')
