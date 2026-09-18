"""Tenfold UN readiness: separate motor pool, sheltered flight line and service lanes."""
from pathlib import Path
import argparse,json,math
import regional_voxels as v
from query_blocks import chunk_statuses
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23/readiness'
def main(apply=False):
 OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();o='r23/un_readiness';vehicles=[];paths=[];shelters=[]
 floor='projectseele:nerv_floor_panel';wall='projectseele:nerv_wall_panel';edge='projectseele:nerv_machine_edge';light='projectseele:nerv_strip_light';dark='minecraft:gray_concrete';air='minecraft:air'
 def fill(b,s):p.fill(*b,s,o,'owned')
 def walk(name,points):
  for suffix,path in [('',points),('/return',points[::-1])]:paths.append(dict(id=o+'/'+name+suffix,path=path))
 def road(x,z,X,Z,width=13):
  fill((min(x,X)-width//2,72,min(z,Z)-width//2,max(x,X)+width//2,74,max(z,Z)+width//2),'minecraft:black_concrete')
  fill((min(x,X)-width//2,75,min(z,Z)-width//2,max(x,X)+width//2,85,max(z,Z)+width//2),air)
  if x==X:
   for q in range(min(z,Z),max(z,Z),16):fill((x,74,q,x,74,min(q+6,max(z,Z))),'minecraft:yellow_concrete')
  else:
   for q in range(min(x,X),max(x,X),16):fill((q,74,z,min(q+6,max(x,X)),74,z),'minecraft:yellow_concrete')
  walk('service/'+str((x,z,X,Z)),[[x+.5,75,z+.5],[X+.5,75,Z+.5]])
 def vehicle(kind,x,z,yaw=0,role='vehicle',y=75):
  key='vehicle/r23/'+role+'/'+str(len(vehicles));vehicles.append(dict(key=key,id='superbwarfare:'+kind,position=[x+.5,y,z+.5],yaw=yaw,role=role))
 def plate(x,y,z,title,face='north'):
  p.sign(x,y,z,[title,'联合国防卫部','UN · 战备设施',''],o,face)
 # The new flight line lies north of the occupied base. Only terrain is
 # graded; the live runway, UN wet cells and original identities are retained.
 p.grade(6320,-7060,6879,-6705,74,o+'/north_airfield',24)
 fill((6332,72,-7048,6868,74,-6712),dark);fill((6334,74,-7046,6866,74,-6714),floor)
 for x in (6490,6560,6672,6784,6854):road(x,-7036,x,-6704,15)
 road(6490,-7040,6854,-7040,15);road(6490,-6704,6854,-6704,15)
 road(6720,-6704,6720,-6608,15);road(6560,-6704,6560,-6656,11)
 # Four independent flight lines with 28 m clear mouths. Aircraft can turn
 # into a 15 m taxi lane and reach the existing runway through the north link.
 serial=0
 for col,x in enumerate((6528,6640,6752,6822)):
  for row,z in enumerate(range(-7016,-6727,36)):
   serial+=1;kind=('j_16' if serial%2 else 'kv_16') if col<3 else 'a_10a'
   # Last line has an east exit to the perimeter taxi lane; all pads are apart.
   b=(x-17,75,z-15,x+17,89,z+15)
   fill((x-18,73,z-16,x+18,74,z+16),floor);fill(b,air)
   fill((x-18,75,z-16,x-18,88,z+16),wall)
   for zz in (z-16,z+16):fill((x-18,75,zz,x+17,86,zz),wall)
   # Stepped low-pitch metal roofs, structural ribs and end fascia.
   for dz in range(-16,17):
    roof=90-abs(dz)//6;fill((x-18,roof,z+dz,x+18,roof,z+dz),dark)
   for xx in (x-17,x-7,x+3,x+16):
    for zz in (z-16,z+16):fill((xx,75,zz,xx,88,zz),edge)
   fill((x+17,88,z-16,x+18,90,z+16),edge)
   for xx in (x-10,x+6):
    fill((xx,87,z-8,xx,87,z+8),light)
    for zz in (z-6,z+6):fill((xx,88,zz,xx,88,zz),'minecraft:chain[axis=y,waterlogged=false]')
   # A supply alcove stands outside the wing and nose envelopes.
   fill((x-16,75,z+10,x-12,76,z+14),'projectseele:nerv_storage_panel');plate(x+18,85,z+16,f'UN 航空库 {serial:02}','east')
   fill((x+18,74,z-13,x+31,74,z+13),floor)
   vehicle(kind,x,z,-90,'fighter' if col<3 else 'attack_aircraft')
   shelters.append(dict(name=f'航空库 {serial:02}',bounds=b,exit=[x+19,75,z],taxi=[x+32,75,z]))
   walk('hangar/'+str(serial),[[x-3.5,75,z-12.5],[x+30.5,75,z-12.5]])
 # Nine distinct helicopter pads, with a perimeter footpath and clear rotors.
 for i,(x,z) in enumerate((x,z) for z in (-6996,-6900,-6804) for x in (6364,6412,6460)):
  fill((x-19,74,z-19,x+19,74,z+19),dark);fill((x-18,75,z-18,x+18,95,z+18),air)
  for dx,dz in [(a,b) for a in range(-16,17) for b in range(-16,17) if 14.5<math.hypot(a,b)<16]:p.put(x+dx,74,z+dz,'minecraft:yellow_concrete',o,'owned')
  for xx in (x-4,x+4):fill((xx,74,z-6,xx,74,z+6),'minecraft:white_concrete')
  fill((x-4,74,z,x+4,74,z),'minecraft:white_concrete');vehicle('ah_6',x,z,0,'helicopter')
  walk('helipad/'+str(i),[[x-19.5,75,z-19.5],[x+20.5,75,z-19.5]])
 # A 36-slot motor pool uses an existing empty paved block west of the main
 # road; it does not cover the prototype bay or its deployment route.
 fill((6340,72,-6448,6542,74,-6298),dark);fill((6340,75,-6448,6542,85,-6298),air)
 road(6344,-6456,6540,-6456,11);road(6540,-6456,6540,-6296,13);road(6344,-6296,6560,-6296,13)
 for row,z in enumerate((-6436,-6412,-6388,-6364,-6340,-6316)):
  for col,x in enumerate((6360,6388,6416,6458,6486,6514)):
   i=row*6+col;vehicle(('m_1a_2','t_90a','ztz_99a')[i%3],x,z,-90,'tank')
   fill((x-8,74,z-7,x+10,74,z+7),floor)
   for dz in (-8,8):fill((x-9,74,z+dz,x+10,74,z+dz),'minecraft:white_concrete')
 # Nine support trucks beside a continuous service road, off all jet lanes.
 for i,z in enumerate(range(-7024,-6727,36)):
  vehicle('truck',6338,z,-90,'support_truck');fill((6332,74,z-6,6351,74,z+6),floor)
 # 54 additional defensive stations, distributed around the enlarged base.
 defense=[]
 for z in range(-7040,-5959,72):defense.extend([(6324,z),(6878,z)])
 defense.extend((x,-7052) for x in range(6360,6865,72));defense.extend((x,-5956) for x in range(6360,6865,72))
 defense.extend([(6480,-6684),(6520,-6684),(6600,-6684),(6640,-6684),(6700,-6684),(6740,-6684)])
 assert len(defense)==54,len(defense)
 for i,(x,z) in enumerate(defense):
  fill((x-4,72,z-4,x+4,74,z+4),dark);fill((x-4,75,z-4,x+4,80,z+4),air)
  for xx in (x-4,x+4):fill((xx,75,z-4,xx,76,z+4),dark)
  fill((x-4,75,z-4,x+4,76,z-4),dark)
  # Low fighting positions retain a genuine walk-in rear opening.
  for xx in (x-4,x+4):fill((xx,75,z+4,xx,76,z+4),dark)
  fill((x-2,72,z+4,x+2,74,z+8),floor);fill((x-2,75,z+4,x+2,78,z+8),air)
  vehicle('laser_tower' if i%3==0 else 'hpj_11',x,z,0,'defense')
  walk('defense/'+str(i),[[x+.5,75,z+5.5],[x+.5,75,z+3.5]])
 # UN perimeter, floodlighting and accessible maintenance walkways.
 for x in (6320,6884):fill((x,74,-7064,x,78,-6704),dark)
 fill((6320,74,-7064,6884,78,-7064),dark)
 for x in (6350,6478,6610,6740,6860):
  for z in (-7056,-6720):
   fill((x,75,z,x,89,z),edge);fill((x-2,90,z,x+2,90,z),light)
 # No new rail service is introduced. Passenger access remains through the
 # original base terminal and its connected internal road network.
 totals={role:sum(q['role']==role for q in vehicles) for role in sorted({q['role'] for q in vehicles})}
 assert len(vehicles)==144,(len(vehicles),totals)
 p.meta.update(vehicles=vehicles,walk_nodes=paths,shelters=shelters,additional_counts=totals,previous_base_equipment=16,total_base_equipment=160,reference='JASDF Hamamatsu apron/hangar photographs: separate taxi lanes, shelters and support bays')
 p.save_plan('un_readiness_extension')
 status=chunk_statuses(WORLD,v.DIM,p.by_chunk);missing=[list(k) for k,s in status.items() if s!='full']
 (OUT/'generation_needed.json').write_text(json.dumps(missing));(OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Vehicles',len(vehicles),totals,'chunks requiring native generation',len(missing),flush=True)
 if apply:
  if missing:raise RuntimeError('Generate measured chunks before installation')
  p.apply('un_readiness_extension');(WORLD/'military_readiness_r23.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
