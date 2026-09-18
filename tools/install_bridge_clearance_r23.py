"""Install the native, clearance-checked S1 bridge profile and its measured civil works."""
from pathlib import Path
import argparse,datetime,json,math,msvcrt,shutil,numpy as np
import regional_voxels as v,scan_regional_completion as scan,plan_factory_r20 as f
from stage_native_transit_repair import hashes
from apply_s20_approved_semantic_repairs import atomic_replace
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23/transit'
def main(apply=False):
 proof=json.loads((OUT/'road_clearance_audit.json').read_text());assert proof['passed'] and proof['minimum_bridge_clearance']>=6
 source=OUT/'built2/native_final.json';native=json.loads(source.read_text(encoding='utf8'));old=json.loads((ROOT/'artifacts/facility_r23/validation/low_rail_curves.json').read_text());rails=[r for r in native['curves'] if r['mode']=='TRAIN' and any(abs(q[0]+895.5)<1.1 and abs(q[1]-118)<.01 and 675<q[2]<686 for q in (r['points'][0],r['points'][-1]))];assert len(rails)==4
 v.WORLD=scan.WORLD=WORLD;v.OUT=OUT;f.LO=(-1450,32,636);f.HI=(-389,139,724);s=f.Scene();p=v.Painter();road=np.load(ROOT/'artifacts/world_rebuild_r20/road_actual/road_contract_final.npz');mask=road['mask'];height=road['height2'];carriage=road['carriage'];stripe=road['stripe'];ox,oz=map(int,road['origin']);stations=json.loads((ROOT/'artifacts/access_r22/transit/civil/station_contract.json').read_text(encoding='utf8'))
 for station in stations['stations']:
  x,y,z=station['center'];h=station['half'];dx,dz=(h+1,19) if station['horizontal'] else (19,h+1);a=tuple(np.maximum(f.LO,(x-dx,station['ground']-3,z-dz)));b=tuple(np.minimum(f.HI,(x+dx,y+14,z+dz)))
  if all(a[i]<=b[i] for i in range(3)):s.protect((*a,*b))
 def at(q):return s.palette[s.after[q[1]-f.LO[1],q[2]-f.LO[2],q[0]-f.LO[0]]]
 def road_at(x,z):return 0<=x-ox<mask.shape[1] and 0<=z-oz<mask.shape[0] and bool(mask[z-oz,x-ox])
 oldcols=set();oldstates={'minecraft:light_gray_concrete','minecraft:gravel','projectseele:nerv_machine_edge'}
 for rail in old:
  for xx,yy,zz in rail['points']:
   x,y,z=map(math.floor,(xx,yy,zz))
   for dx in range(-3,4):
    for dz in range(-3,4):
     for Y in range(y-3,y):oldcols.add((x+dx,Y,z+dz))
 for q in oldcols:
  if at(q) in oldstates:s.fill((*q,*q),'minecraft:air')
 terrain=np.load(ROOT/'artifacts/world_quality_r02/terrain_target.npz');terrain_height=terrain['height'];tx,tz=map(int,terrain['origin'])
 oldpiers=[]
 for x,y,z in stations['piers']:
  if not(-1450<x<-389 and 662<z<704):continue
  ground=int(terrain_height[z-tz,x-tx]);oldpiers.append([x,y,z])
  for X in range(x-1,x+2):
   for Z in range(z-1,z+2):
    for Y in range(ground+1,y-3):
     q=(X,Y,Z)
     if at(q)=='minecraft:light_gray_concrete':s.fill((*q,*q),'minecraft:air')
 # Restore the retained road profile and six metres of air, including places
 # where the earlier bridge overwrote the asphalt itself.
 paving=set((x,z) for x,_,z in oldcols if road_at(x,z))
 for x,z in paving:
  h=int(height[z-oz,x-ox]);y=(h-1)//2;kind=2 if stripe[z-oz,x-ox] else 1 if carriage[z-oz,x-ox] else 0
  material=['minecraft:smooth_stone','minecraft:black_concrete','minecraft:white_concrete'][kind]
  if h%2:material=['minecraft:smooth_stone_slab','projectseele:road_asphalt_slab','projectseele:road_marking_slab'][kind]+'[type=bottom,waterlogged=false]'
  s.fill((x,y-2,z,x,y-1,z),'minecraft:stone');s.fill((x,y,z,x,y,z),material)
  for Y in range(y+1,y+7):
   q=(x,Y,z)
   if at(q) in oldstates:s.fill((*q,*q),'minecraft:air')
 # Union both track formations before clearing the exact rail cores.
 cores=set();allpoints=[]
 for rail in rails:
  points=np.asarray(rail['points']);allpoints.extend(points)
  for xx,yy,zz in points:
   x,y,z=map(math.floor,(xx,yy,zz));s.fill((x-3,y-3,z-3,x+3,y-1,z+3),'minecraft:light_gray_concrete')
   for dx in (-1,0,1):
    for dz in (-1,0,1):cores.add((x+dx,y,z+dz))
 for x,y,z in cores:s.fill((x,y,z,x,y+6,z),'minecraft:air');s.fill((x,y-1,z,x,y-1,z),'minecraft:gravel')
 # Twin supports straddle streets. The crossbeam remains within the deck
 # depth used by the clearance audit; it never hangs below the 6 m envelope.
 points=np.asarray(allpoints);piers=[];plots=json.loads((ROOT/'artifacts/world_quality_r02/surface_layout.json').read_text())['kept_plots']
 def free_site(x,z,top):
  if any(road_at(x+dx,z+dz) for dx in range(-2,3) for dz in range(-2,3)):return False
  if any(b['bounds'][0]-3<=x<=b['bounds'][1]+3 and b['bounds'][2]-3<=z<=b['bounds'][3]+3 for b in plots):return False
  return True
 for x in range(-1380,-439,64):
  near=points[abs(points[:,0]-x)<1.5];assert len(near)>0;y=math.floor(float(near[:,1].min()));z=round(float((near[:,2].min()+near[:,2].max())/2));chosen=None
  for half in (10,14,18,22,26,30):
   if z-half<f.LO[2]+1 or z+half>f.HI[2]-1:continue
   if free_site(x,z-half,y) and free_site(x,z+half,y):chosen=half;break
  if chosen is None:continue
  for Z in (z-chosen,z+chosen):
   ground=max((Y for Y in range(32,y-3) if at((x,Y,Z)).split('[')[0] in {'minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:gravel','minecraft:sand','minecraft:deepslate','minecraft:andesite','minecraft:granite','minecraft:diorite'}),default=None)
   if ground is None:raise RuntimeError(('Missing measured portal foundation',x,Z))
   s.fill((x-1,ground,Z-1,x+1,y-4,Z+1),'minecraft:light_gray_concrete');piers.append(dict(position=[x,y,Z],ground=ground))
  s.fill((x-1,y-3,z-chosen-1,x+1,y-2,z+chosen+1),'projectseele:nerv_machine_edge')
 count=s.delta(p,'r23/raised_s1_bridge_over_retained_roads');p.meta.update(rail_arcs=4,old_arcs=2,old_piers_removed=oldpiers,new_portal_columns=piers,restored_road_columns=len(paving),changed_cells=count,minimum_road_clearance=6,station_positions_retained=True)
 p.save_plan('raised_s1_bridge_and_road_restoration')
 if apply:
  p.apply('raised_s1_bridge_and_road_restoration');stage=ROOT/'.Codex/r22-native/r23-road-clearance2/projectseele/geofront';target=WORLD/'mtr/projectseele/geofront';backup=OUT/('native_before_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
  with (WORLD/'session.lock').open('r+b') as lock:
   msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);oldhash,newhash=hashes(target),hashes(stage);shutil.copytree(target,backup)
   for name in sorted(set(oldhash)|set(newhash)):
    dst=(target/name).resolve();assert dst.is_relative_to(target.resolve())
    if name in newhash:dst.parent.mkdir(parents=True,exist_ok=True);atomic_replace(dst,(stage/name).read_bytes())
    elif dst.is_file():dst.unlink()
   assert hashes(target)==newhash
   for name in ('native_transit_r22.json','native_transit_r20.json'):shutil.copy2(source,WORLD/name)
   (WORLD/'native_transit_r23.json').write_text(source.read_text(encoding='utf8'),encoding='utf8')
 (OUT/'civil_contract.json').write_text(json.dumps(p.meta,indent=2));print('S1 bridge cells',count,'portal columns',len(piers),'road columns restored',len(paving))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
