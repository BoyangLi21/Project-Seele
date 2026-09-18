"""Resolve measured sign, transfer-envelope and retained defense-post conflicts."""
from pathlib import Path
import argparse,copy,datetime,json,msvcrt,os,shutil
import nbtlib
import regional_voxels as v
from query_blocks import read_box,iter_block_entities,AIR
from apply_s20_approved_semantic_repairs import atomic_replace
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23/finish'
def main(apply=False):
 OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();counts={};cold=Path(json.loads((ROOT/'artifacts/facility_r23/baseline.json').read_text())['backup'])/'world'
 receipt=ROOT/'artifacts/facility_r23/station_details/waiting_rooms_native_gates_and_guidance/applied_20260918_194537_548389';prior=OUT/'station_before';regions=prior/'dimensions/projectseele/geofront/region';regions.mkdir(parents=True,exist_ok=True)
 for src in (receipt/'before').glob('r.*.mca'):
  dst=regions/src.name
  if not dst.exists():os.link(src,dst)
 seen=set()
 def restore(source,lo,hi,owner,only=None):
  a=read_box(source,v.DIM,lo,hi);b=read_box(WORLD,v.DIM,lo,hi);n=0
  for q,old in b.items():
   if only is not None and q not in only or q in seen or old==a[q]:continue
   p.match((*q,*q),old,a[q],owner);seen.add(q);n+=1
  for q,tag in iter_block_entities(source,v.DIM,lo,hi):
   if q in seen:p.block_entities[q]=copy.deepcopy(tag)
  counts[owner]=counts.get(owner,0)+n
 # Later architectural dressing must retain the complete live transfer tube,
 # including its walls, paired moving stairs and crossing landings.
 contracts=json.loads((ROOT/'artifacts/access_r22/transit/civil/station_contract.json').read_text(encoding='utf8'))
 for link in contracts['transfer_links']:
  if link['id'].endswith('/return'):continue
  cells=set();horizontal=abs(link['path'][0][0]-link['path'][-1][0])>abs(link['path'][0][2]-link['path'][-1][2])
  for point in link['path']:
   x,y,z=map(int,point) if all(t>=0 for t in point) else (int(__import__('math').floor(q)) for q in point)
   cells.update((x+dx,Y,z+dz) for Y in range(y-3,y+5) for dx in ([0] if horizontal else range(-4,5)) for dz in (range(-4,5) if horizontal else [0]))
  lo=tuple(min(q[i] for q in cells) for i in range(3));hi=tuple(max(q[i] for q in cells) for i in range(3));restore(prior,lo,hi,'r23/retained_full_transfer_envelope',cells)
 # Stop secondary north taxi lanes at their cross-taxiway. Restore the
 # original perimeter/watchpost that one extended lane accidentally entered.
 for x in (6490,6672,6784,6854):restore(cold,(x-7,72,-6696),(x+7,90,-6673),'r23/retained_original_defense_and_perimeter')
 inventory=json.loads((ROOT/'artifacts/facility_r23/global/inventory/world_objects.json').read_text(encoding='utf8'));moved=[]
 for row in inventory['objects']['signs']:
  q=tuple(row['pos'])
  if not row['unsupported'] or q[1]!=85 or q[2]>-6715:continue
  destination=(q[0],q[1],q[2]+3);lo=(q[0]-1,q[1],q[2]);hi=destination;b=read_box(WORLD,v.DIM,lo,hi);tags=dict(iter_block_entities(WORLD,v.DIM,q,q));tag=copy.deepcopy(tags[q])
  assert b[destination].split('[')[0] in AIR and b[(destination[0]-1,destination[1],destination[2])].split('[')[0] not in AIR
  p.match((*q,*q),b[q],'minecraft:air','r23/hangar_sign_relocation');p.match((*destination,*destination),b[destination],b[q],'r23/hangar_sign_relocation')
  tag['z']=nbtlib.Int(destination[2]);p.block_entities[destination]=tag;moved.append(dict(before=q,after=destination))
 # Door 18's inherited controls were on its inner side. Provide a reachable
 # control on the corridor side, attached to the existing left jamb.
 button=(27,-405,270);back=(26,-405,270);b=read_box(WORLD,v.DIM,back,button)
 assert b[button].split('[')[0] in AIR and b[back]=='minecraft:black_concrete'
 p.match((*button,*button),b[button],'minecraft:stone_button[face=wall,facing=east,powered=false]','r23/public_command_door_control')
 p.meta.update(restored_cells=counts,relocated_hangar_signs=moved,public_command_button=button,command_layout_unchanged=True)
 p.save_plan('verified_conflict_finish')
 if apply:
  p.apply('verified_conflict_finish');marker=WORLD/'.projectseele_command_sliding_doors_r01.json';data=json.loads(marker.read_text());shutil.copy2(marker,OUT/'command_doors_before.json')
  for door in data['doors']:
   if door['id']==18 and list(button) not in door['buttons']:door['buttons'].append(list(button))
  marker.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
  # Restore this same retained defense entity to its restored original deck.
  from transplant_s22_authority import read_region,parse_chunk,build_region,chunk_blob
  fixes=json.loads((ROOT/'artifacts/facility_r23/readiness/original_vehicle_positions.json').read_text());fixes={tuple(q['uuid']):q for q in fixes};changed=[]
  with (WORLD/'session.lock').open('r+b') as lock:
   msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
   for path in (WORLD/'dimensions/projectseele/geofront/entities').glob('r.*.mca'):
    if path.stat().st_size<8192:continue
    stamps,blobs=read_region(path);dirty=False
    for slot,blob in enumerate(blobs):
     if not blob:continue
     root=parse_chunk(blob);altered=False
     for entity in root.get('Entities',[]):
      uid=tuple(map(int,entity.get('UUID',[])))
      if uid not in fixes:continue
      row=fixes[uid];assert str(entity['id'])==row['id'];assert [float(q) for q in entity['Pos']]==row['after']
      entity['Pos']=nbtlib.List[nbtlib.Double](row['before']);entity['Motion']=nbtlib.List[nbtlib.Double]([0.,0.,0.]);entity['FallDistance']=nbtlib.Float(0);changed.append(row);altered=dirty=True
     if altered:blobs[slot]=chunk_blob(root)
    if dirty:
     dest=OUT/'entity_before'/path.name;dest.parent.mkdir(exist_ok=True);shutil.copy2(path,dest);atomic_replace(path,build_region(stamps,blobs))
   assert len(changed)==len(fixes);(OUT/'retained_entity_restore.json').write_text(json.dumps(changed,indent=2))
 (OUT/'report.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Exact conflict fixes',counts,'signs moved',len(moved))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
