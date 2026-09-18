"""Classify the complete scan; remove detached residue, attach useful fixtures."""
from pathlib import Path
from collections import defaultdict,Counter
import argparse,gzip,json,math
import numpy as np
from scipy.spatial import cKDTree
import regional_voxels as v
import repair_scan_residue_r20 as extract
from query_blocks import read_box,AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23/global/cleanup';SCAN=OUT.parent/'components'
def main(apply=False):
 OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;extract.REVIEW=WORLD;p=v.Painter();raw=json.loads((SCAN/'report.json').read_text())['candidates'];groups=json.loads((SCAN/'contact_classification.json').read_text())['groups'];removed={};decisions=[];held=[];struts=[]
 before=json.loads((ROOT/'artifacts/access_r22/native_before.json').read_text());oldpoints=np.asarray([q for r in before['curves'] if r['mode']=='TRAIN' for q in r['points']]);oldtree=cKDTree(oldpoints[:,[0,2]])
 whitelist={'minecraft:gray_concrete','minecraft:light_gray_concrete','minecraft:iron_block','minecraft:iron_bars','minecraft:polished_basalt','minecraft:polished_deepslate','minecraft:gray_stained_glass','minecraft:light_gray_stained_glass','minecraft:smooth_stone','minecraft:polished_blackstone_slab','minecraft:chain','minecraft:black_concrete','projectseele:nerv_machine_edge'}
 with gzip.open(SCAN/'isolated_soil_points.json.gz','rt') as stream:
  for row in json.load(stream):removed[tuple(row['pos'])]=row['state']
 for group in groups:
  kind=group['kind'];lo,hi=group['lo'],group['hi'];names={s.split('[')[0] for s in group['states']};reason=None;retire=False
  if kind in ('edge_connected_to_world','fluid_contact','isolated_soil'):continue
  if kind=='isolated_vegetation':reason='Detached vegetation has no trunk, terrain or fluid support in 26 neighbouring cells';retire=True
  elif group['cells']==920 and lo==[19,-443,313]:reason='Retain original protected command display and lighting'
  elif group['cells'] in (782,24) and 1400<=lo[0]<=1435 and lo[2] in (362,502,370,510):reason='Retain crane decks and hoists carried by the actual R08 steel-member entities'
  elif names=={'minecraft:structure_void'}:reason='Retain non-rendered, non-colliding construction receipts'
  elif names=={'projectseele:station_departure_board'}:
   reason='Retain model-sized suspended board; its documented outer frame meets real ceiling rods'
   boards=json.loads((ROOT/'artifacts/facility_r23/navigation/junctions.json').read_text(encoding='utf8'))['boards'];assert any(q['position']==lo and q['suspension'] for q in boards)
  elif any(n.endswith('_wall_sign') for n in names) and group['cells']==1:
   reason='Remounted on the measured hangar frame, or original watchpost backing restored by finish patch'
  elif names=={'projectseele:nerv_strip_light'} and lo[0]>6000:
   reason='Suspend useful flight-line luminaires from the real roof'
   x,y,z=lo;Z=hi[2]
   for zz in (z+2,Z-2):
    b=read_box(WORLD,v.DIM,(x,y+1,zz),(x,y+8,zz));top=next((yy for yy in range(y+1,y+9) if b[x,yy,zz].split('[')[0] not in AIR|{'minecraft:light'}),None);assert top is not None
    for yy in range(y+1,top):p.match((x,yy,zz,x,yy,zz),b[x,yy,zz],'minecraft:chain[axis=y,waterlogged=false]','r23/flight_line_light_hangers');struts.append([x,yy,zz])
  elif names<=whitelist and lo[1]>=32:
   points=np.asarray([raw[i]['seed'] for i in group['components']]);distance,_=oldtree.query(points[:,[0,2]]+.5)
   if distance.max()<32:
    reason='Disconnected formation, pier, railing or station trim from the superseded rail alignments';retire=True
  if reason is None:held.append(group);continue
  if retire:
   for i in group['components']:removed.update(extract.cells(raw[i]))
  decisions.append(dict(kind=kind,cells=group['cells'],lo=lo,hi=hi,action='retire' if retire else 'retain_or_support',reason=reason))
 # A route can never lose its supporting floor as a side effect of cleanup.
 points=np.asarray(list(removed),float);tree=cKDTree(points);cases=json.loads((ROOT/'artifacts/facility_r23/validation/full_walk_cases.json').read_text(encoding='utf8'));violations=[]
 for case in cases:
  route=case.get('path',[case.get('start'),case.get('end')])
  for aa,bb in zip(route,route[1:]):
   a,b=np.asarray(aa,float),np.asarray(bb,float);d=b-a;ids=tree.query_ball_point((a+b)*.5,np.linalg.norm(d)*.5+3)
   if not ids:continue
   cells=points[ids];lower=cells+[-.3,.8,-.3];upper=cells+[1.3,1.1,1.3];enter=np.zeros(len(ids));leave=np.ones(len(ids));possible=np.ones(len(ids),bool)
   for axis in range(3):
    if abs(d[axis])<1e-10:possible&=(lower[:,axis]<=a[axis])&(a[axis]<=upper[:,axis])
    else:
     first=(lower[:,axis]-a[axis])/d[axis];last=(upper[:,axis]-a[axis])/d[axis];enter=np.maximum(enter,np.minimum(first,last));leave=np.minimum(leave,np.maximum(first,last))
   if (possible&(enter<=leave)).any():violations.append(dict(id=case['id'],cells=cells[possible&(enter<=leave)].tolist()))
 assert not violations,violations[:5]
 for q,s in removed.items():p.match((*q,*q),s,'minecraft:air','r23/whole_save_verified_residue')
 p.meta.update(removed_cells=len(removed),classifications=decisions,unclassified=held,light_hanger_cells=len(struts),named_route_support_intersections=0,full_scan_chunks=53188,full_scan_sections=3297656)
 p.save_plan('classified_residue_and_supported_lights');(OUT/'classification.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Remove cells',len(removed),'light hangers',len(struts),'unclassified',len(held),Counter(q['kind'] for q in decisions))
 if held:print('Unclassified',held[:8])
 if apply:
  if held:raise RuntimeError('Classify every remaining structural group before final cleanup')
  p.apply('classified_residue_and_supported_lights')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
