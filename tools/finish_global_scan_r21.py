"""Classify final whole-map islands and author only evidenced repairs."""
import argparse,copy,gzip,json,math
from pathlib import Path
import numpy as np
import regional_voxels as v
from query_blocks import read_box,AIR
import repair_scan_residue_r20 as extract
ROOT=v.ROOT;OUT=ROOT/'artifacts/world_repair_r21';WORLD=ROOT/'run/saves/SEELE_R21_REVIEW';FROZEN=OUT/'global_audit/world_geometry'
def main(apply=False):
 v.WORLD=WORLD;v.OUT=OUT/'global_audit/cleanup';extract.REVIEW=FROZEN;p=v.Painter()
 raw=json.loads((OUT/'global_audit/components/report.json').read_text())['candidates']
 groups=json.loads((OUT/'global_audit/components/contact_classification.json').read_text())['groups']
 with gzip.open(OUT/'global_audit/components/isolated_soil_points.json.gz','rt') as f:soil=json.load(f)
 removed={tuple(r['pos']):r['state'] for r in soil};decisions=[]
 for group in groups:
  if group['kind']!='isolated_structure':continue
  lo,hi=group['lo'],group['hi'];n=group['cells'];names={s.split('[')[0] for s in group['states']};decision=None
  if n==920 and lo==[19,-443,313]:decision='Retain original command-room display and lighting'
  elif n==782 and lo in ([1407,84,362],[1407,84,502]):decision='Retain crane deck with four modelled steel legs; verify original quay anchors'
  elif n==24 and lo in ([1427,74,370],[1427,74,510]):decision='Retain crane hook attached to the modelled hoist'
  elif names=={'minecraft:structure_void'}:decision='Retain invisible noncolliding construction receipts'
  elif n==661 and 'projectseele:umbilical_pylon' in names:decision='Keep current power pedestal; extend its foundation to measured ground'
  elif n==2 and 'projectseele:nerv_warning_beacon' in names:decision='Keep live warning lamp; connect its bracket to the adjacent cage wall'
  elif n==1 and 'minecraft:oak_wall_sign' in names:decision='Already remounted on an existing fixed wall by the measured fixture patch'
  elif lo==[217,102,192] and hi==[217,102,248] and n==57:
   decision='Retire remaining west lintel of the explicitly retired vanilla minecart station'
   for index in group['components']:removed.update(extract.cells(raw[index]))
  elif n==1 and names=={'minecraft:sea_lantern'} and lo[0:2]==[158,-442] and lo[2] in (-135,-111,-87,-63):
   decision='Retire isolated exterior lamps of the retired east-side corridor'
   for index in group['components']:removed.update(extract.cells(raw[index]))
  assert decision,('Unclassified structure',group)
  decisions.append(dict(lo=lo,hi=hi,cells=n,decision=decision))
 # A removed voxel must not be a floor under any registered route segment.
 boxes=np.asarray(list(removed),float);floor_lo=boxes+[-.3,.8,-.3];floor_hi=boxes+[1.3,1.1,1.3]
 for case in json.loads((OUT/'full_walk_catalogue.json').read_text()):
  path=case.get('path',[case.get('start'),case.get('end')])
  for aa,bb in zip(path,path[1:]):
   a=np.asarray(aa,float);b=np.asarray(bb,float);d=b-a
   selected=((floor_hi>=np.minimum(a,b))&(floor_lo<=np.maximum(a,b))).all(1)
   if not selected.any():continue
   lower=floor_lo[selected];upper=floor_hi[selected];enter=np.zeros(len(lower));leave=np.ones(len(lower));possible=np.ones(len(lower),bool)
   for axis in range(3):
    if abs(d[axis])<1e-10:possible&=(lower[:,axis]<=a[axis])&(a[axis]<=upper[:,axis])
    else:
     first=(lower[:,axis]-a[axis])/d[axis];last=(upper[:,axis]-a[axis])/d[axis]
     enter=np.maximum(enter,np.minimum(first,last));leave=np.minimum(leave,np.maximum(first,last))
   assert not (possible&(enter<=leave)).any(),('Removal intersects route support',case['id'],boxes[selected][possible&(enter<=leave)])
 for q,s in removed.items():p.match((*q,*q),s,'minecraft:air','r21/isolated_and_explicitly_retired_residue')
 foundations=[]
 for cx in (-12,30):
  measured=read_box(FROZEN,v.DIM,(cx-5,32,-82),(cx+5,76,-68))
  for x in range(cx-5,cx+6):
   for z in range(-82,-67):
    solid=[y for y in range(32,77) if measured[x,y,z].split('[')[0] not in AIR|{'minecraft:light','minecraft:water','minecraft:grass','minecraft:fern','minecraft:tall_grass'}]
    assert solid,(x,z,'No measured foundation')
    top=max(solid);foundations.append([x,top,z])
    for y in range(top+1,77):p.match((x,y,z,x,y,z),measured[x,y,z],'projectseele:nerv_structural_panel','r21/pylon_foundation_to_measured_ground')
 for cx in (-12,30,72):
  for side in (-1,1):
   anchor=(cx+side*20,-380,-221);assert read_box(FROZEN,v.DIM,anchor,anchor)[anchor]=='projectseele:nerv_shaft_panel'
   for distance in (18,19):
    q=(cx+side*distance,-380,-221);old=read_box(FROZEN,v.DIM,q,q)[q];assert old in AIR
    p.match((*q,*q),old,'projectseele:nerv_machine_edge','r21/beacon_wall_bracket')
 # The modelled crane supports and their block foundations are independently
 # retained; their lack of voxel legs is not evidence of floating construction.
 import scipy.spatial.transform
 members=json.loads((WORLD/'r08_native_details.json').read_text())['members']
 for z in (370,510):
  legs=[m for m in members if m['key'].startswith(f'crane/{z}/leg/')];assert len(legs)==4
  for m in legs:
   a=np.asarray(m['position']);b=a+scipy.spatial.transform.Rotation.from_quat(m['rotation']).apply([0,0,m['scale'][2]])
   assert np.all(b>=np.array([1407,84,z-8])) and np.all(b<=np.array([1419,93,z+9]))
   q=tuple(map(math.floor,a));assert read_box(FROZEN,v.DIM,q,q)[q]=='minecraft:yellow_terracotta'
 p.meta.update(natural_residue_cells=len(soil),retired_structure_cells=len(removed)-len(soil),component_decisions=decisions,pylon_foundations=foundations,route_support_intersections=0,source_full_chunks=47842,complete_classification=True,incremental_proof='Only isolated components are removed; new foundation/bracket cells join existing ground-connected structures; prior sign/shaft/stair fixes have separate exact receipts')
 if apply:p.apply('classified_whole_map_repairs')
 else:p.save_plan('classified_whole_map_repairs')
 print('R21 final scan plan',len(soil),'natural cells,',len(removed)-len(soil),'retired structure cells;',len(decisions),'structure decisions',flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
