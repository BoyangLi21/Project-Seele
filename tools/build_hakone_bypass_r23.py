"""Move the R1 approach into the vacant transport reserve, preserving occupied buildings."""
from pathlib import Path
import argparse,json,math,numpy as np
from scipy.spatial import cKDTree
import regional_voxels as v,scan_regional_completion as scan,plan_factory_r20 as f
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23/transit/gates'
def main(apply=False):
 native=json.loads((OUT/'built2/native_final.json').read_text(encoding='utf8'));old=json.loads((WORLD/'native_transit_r23.json').read_text(encoding='utf8'));newrails=[q for q in native['curves'] if q['mode']=='TRAIN' and any(abs(p[0]+1727.5)<1.1 and 711<p[2]<722 for p in (q['points'][0],q['points'][-1]))];oldrails=[q for q in old['curves'] if q['mode']=='TRAIN' and np.linalg.norm(np.asarray(q['points'][0])-q['points'][-1])>600 and any(abs(p[0]+2351.5)<1.1 and 743<p[2]<754 for p in (q['points'][0],q['points'][-1]))];assert len(newrails)==4 and len(oldrails)==2
 v.WORLD=scan.WORLD=WORLD;v.OUT=OUT;f.LO=(-2360,32,610);f.HI=(-1535,160,782);s=f.Scene();p=v.Painter();plots=json.loads((ROOT/'artifacts/world_quality_r02/surface_layout.json').read_text())['kept_plots'];protected=[]
 for b in plots:
  x,X,z,Z=b['bounds'];lo=np.maximum(f.LO,(x,b['floor'],z));hi=np.minimum(f.HI,(X,b['floor']+b.get('storeys',1)*5+6,Z))
  if np.all(lo<=hi):s.protect((*lo,*hi));protected.append(b['id'])
 def at(q):return s.palette[s.after[q[1]-f.LO[1],q[2]-f.LO[2],q[0]-f.LO[0]]]
 oldpoints=np.concatenate([q['points'] for q in oldrails]);tree=cKDTree(oldpoints[:,[0,2]]);materials={'minecraft:light_gray_concrete','minecraft:gravel','projectseele:nerv_machine_edge'}
 for xx,yy,zz in oldpoints:
  x,y,z=map(math.floor,(xx,yy,zz))
  for X in range(x-3,x+4):
   for Z in range(z-3,z+4):
    for Y in range(y-3,y):
     if at((X,Y,Z)) in materials:s.fill((X,Y,Z,X,Y,Z),'minecraft:air')
 terrain=np.load(ROOT/'artifacts/world_quality_r02/terrain_target.npz');th=terrain['height'];ox,oz=map(int,terrain['origin']);contract=json.loads((ROOT/'artifacts/access_r22/transit/civil/station_contract.json').read_text(encoding='utf8'));retired=[]
 for x,y,z in contract['piers']:
  if not(f.LO[0]+2<x<f.HI[0]-2 and f.LO[2]+2<z<f.HI[2]-2) or tree.query([x,z])[0]>4:continue
  ground=int(th[z-oz,x-ox]);retired.append([x,y,z])
  for X in range(x-1,x+2):
   for Z in range(z-1,z+2):
    for Y in range(ground+1,y-3):
     if at((X,Y,Z))=='minecraft:light_gray_concrete':s.fill((X,Y,Z,X,Y,Z),'minecraft:air')
 points=np.concatenate([q['points'] for q in newrails]);cores=set()
 for xx,yy,zz in points:
  x,y,z=math.floor(xx+1e-6),math.floor(yy+1e-6),math.floor(zz+1e-6);s.fill((x-3,y-3,z-3,x+3,y-1,z+3),'minecraft:light_gray_concrete')
  for X in range(x-1,x+2):
   for Z in range(z-1,z+2):cores.add((X,y,Z))
 for x,y,z in cores:
  sl=s.index((x,y,z,x,y+6,z));assert not s.protected[sl].any(),('New alignment still crosses a retained building',x,y,z)
  s.fill((x,y,z,x,y+6,z),'minecraft:air');s.fill((x,y-1,z,x,y-1,z),'minecraft:gravel')
 road=np.load(ROOT/'artifacts/world_rebuild_r20/road_actual/road_contract_final.npz');rm=road['mask'];rx,rz=map(int,road['origin']);allrails=np.concatenate([q['points'] for q in native['curves'] if q['mode']=='TRAIN' and q['points'][0][1]>0]);rtree=cKDTree(allrails[:,[0,2]]);piers=[]
 def possible(x,z,top):
  if any(b['bounds'][0]-3<=x<=b['bounds'][1]+3 and b['bounds'][2]-3<=z<=b['bounds'][3]+3 for b in plots):return False
  if any(0<=X-rx<rm.shape[1] and 0<=Z-rz<rm.shape[0] and rm[Z-rz,X-rx] for X in range(x-2,x+3) for Z in range(z-2,z+3)):return False
  near=rtree.query_ball_point([x,z],4)
  if any(allrails[i,1]+6>=32 and allrails[i,1]<top for i in near):return False
  return True
 for x in range(-2290,-1569,64):
  near=points[abs(points[:,0]-x)<1.5];y=math.floor(float(near[:,1].min())+1e-6);z=round(float((near[:,2].min()+near[:,2].max())/2));half=next((h for h in (10,14,18,22,26) if f.LO[2]+2<=z-h and z+h<=f.HI[2]-2 and possible(x,z-h,y-3) and possible(x,z+h,y-3)),None)
  if half is None:continue
  for Z in (z-half,z+half):
   ground=max((Y for Y in range(32,y-3) if at((x,Y,Z)).split('[')[0] in {'minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:gravel','minecraft:sand','minecraft:deepslate','minecraft:andesite','minecraft:granite','minecraft:diorite'}),default=None);assert ground is not None
   s.fill((x-1,ground,Z-1,x+1,y-4,Z+1),'minecraft:light_gray_concrete');piers.append(dict(pos=[x,y,Z],ground=ground))
  s.fill((x-1,y-3,z-half-1,x+1,y-2,z+half+1),'projectseele:nerv_machine_edge')
 count=s.delta(p,'r23/r1_reserve_alignment');p.meta.update(changed_cells=count,retained_buildings=protected,retired_piers=retired,new_portal_columns=piers,old_alignment=[q['id'] for q in oldrails],new_alignment=[q['id'] for q in newrails]);p.save_plan('r1_bypass_of_occupied_apartments')
 if apply:p.apply('r1_bypass_of_occupied_apartments')
 (OUT/'bypass_contract.json').write_text(json.dumps(p.meta,indent=2));print('R1 reserve bypass',count,'changed cells; protected plots',len(protected),'portal columns',len(piers))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
