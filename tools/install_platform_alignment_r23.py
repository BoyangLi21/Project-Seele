"""Measured platform-gate alignment and the corresponding native rail graph."""
from pathlib import Path
from collections import defaultdict,Counter
import argparse,datetime,json,math,msvcrt,shutil,nbtlib,numpy as np
import regional_voxels as v
from query_blocks import read_box,iter_selected_sections,AIR
from stage_native_transit_repair import hashes
from apply_s20_approved_semantic_repairs import atomic_replace
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23/transit/gates'
def main(apply=False):
 native=json.loads((OUT/'built2/native_final.json').read_text(encoding='utf8'));assert json.loads((OUT.parent/'road_clearance_audit.json').read_text())['passed']
 for kind,count in [('trains',4),('F2',1)]:
  proof=json.loads((OUT/f'built2/cadence_{kind}.json').read_text());assert proof['passed'] and len(proof['cycles'])==count
 v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();stations=json.loads((ROOT/'artifacts/access_r22/transit/civil/station_contract.json').read_text(encoding='utf8'))['stations'];records=[]
 for r in stations:
  x,y,z=r['center'];h=r['half'];hor=r['horizontal'];dx,dz=(h+2,20) if hor else (20,h+2);b=read_box(WORLD,v.DIM,(x-dx,y,z-dz),(x+dx,y+2,z+dz));plats=[q for q in native['platforms'] if q['id'] in r['platform_ids']]
  def at(u,Y,w):return (x+u,Y,z+w) if hor else (x+w,Y,z+u)
  edge=int(round(max(abs(((q['position1']['z']+q['position2']['z'])/2-z) if hor else ((q['position1']['x']+q['position2']['x'])/2-x)) for q in plats)))+2
  for side in (-1,1):
   plat=min(plats,key=lambda q:abs(((q['position1']['z']+q['position2']['z'])/2-z if hor else (q['position1']['x']+q['position2']['x'])/2-x)-side*4));axis='x' if hor else 'z';centre=x if hor else z;lo=min(plat['position1'][axis],plat['position2'][axis])-centre;hi=max(plat['position1'][axis],plat['position2'][axis])-centre;assert (hi-lo)%5==0
   door={};centres=list(range(lo+3,hi-1,5))
   for c in centres:door[c-1]=0;door[c]=1
   face=('south' if side<0 else 'north') if hor else ('east' if side<0 else 'west');increasing_right=face in ('north','east');cw=1 if increasing_right else -1
   for u in range(-h+1,h):
    if r['station']=='NERV 港口' and side==-1 and u<lo:
     for Y in (y+1,y+2):
      q=at(u,Y,side*edge);p.match((*q,*q),b[q],'minecraft:air','r23/curved_port_platform_mouth')
      q=at(u,Y,side*(edge+2));p.match((*q,*q),b[q],'projectseele:clear_glass','r23/curved_port_platform_guard')
     continue
    isdoor=u in door;part=door.get(u,(u-lo)%2);part=part if increasing_right else 1-part
    for half,Y in [('lower',y+1),('upper',y+2)]:
     q=at(u,Y,side*edge);props=f'facing={face},half={half},side={"left" if part==0 else "right"}';new=f'mtr:apg_door[end=false,{props},unlocked=true]' if isdoor else f'mtr:apg_glass[{props}]'
     p.match((*q,*q),b[q],new,'r23/native_doorway_alignment')
     if isdoor:p.block_entities[q]=nbtlib.Compound({'id':nbtlib.String('mtr:apg_door'),'x':nbtlib.Int(q[0]),'y':nbtlib.Int(q[1]),'z':nbtlib.Int(q[2])})
    q=at(u,y,side*edge)
    if b[q].startswith('mtr:platform['):
     right=(u+cw) in door;left=(u-cw) in door;value=2 if isdoor and right else 3 if isdoor and left else 1 if right else 4 if left else 0
     p.match((*q,*q),b[q],f'mtr:platform[door_type=apg,facing={face},side={value}]','r23/native_platform_gate_links')
   records.append(dict(station=r['station'],line=r['line'],platform=plat['id'],side=side,centres=[at(n,y+1,side*edge) for n in centres],native_rail_length=hi-lo))
 # Node extensions remain within the existing deck. Check the new engine-
 # evaluated core and remove only known formation material, never buildings.
 cells=defaultdict(set);selected=defaultdict(set)
 for rail in native['curves']:
  if rail['mode']!='TRAIN' or rail['points'][0][1]<0:continue
  for xx,yy,zz in rail['points']:
   x,y,z=math.floor(xx+1e-6),math.floor(yy+1e-6),math.floor(zz+1e-6)
   for dx in (-1,0,1):
    for dz in (-1,0,1):
     for dy in range(6):
      q=(x+dx,y+dy,z+dz);key=(q[0]//16,q[2]//16,q[1]//16);cells[key].add(q);selected[key[:2]].add(key[2])
 bad=[];cleared=Counter();allowed={'minecraft:gravel','minecraft:light_gray_concrete','projectseele:nerv_machine_edge','minecraft:stone'}
 for cx,cz,sy,pal,a in iter_selected_sections(WORLD,v.DIM,selected):
  for q in cells[cx,cz,sy]:
   old=pal[a[((q[1]&15)*16+(q[2]&15))*16+(q[0]&15)]];name=old.split('[')[0]
   if name in AIR|{'minecraft:light','minecraft:structure_void'}:continue
   port_mouth=1125<=q[0]<=1133 and 93<=q[1]<=100 and 469<=q[2]<=471
   if name not in allowed and not(port_mouth and name in {'minecraft:smooth_stone','projectseele:clear_glass','mtr:apg_glass','mtr:apg_door'}):bad.append(dict(pos=q,state=old));continue
   p.match((*q,*q),old,'minecraft:air','r23/extended_rail_core');cleared[name]+=1
 p.meta.update(stations=records,door_pitch=5,centres_and_heights_preserved=True,known_formation_removed=dict(cleared),unexpected_core_blocks=bad)
 p.save_plan('aligned_native_platform_doors');(OUT/'alignment_report.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Aligned gate faces',len(records),'core formation fixes',dict(cleared),'unexpected core cells',len(bad))
 if bad:print('Core examples',bad[:16])
 if not apply:return
 if bad:raise RuntimeError('Inspect unexpected train body obstructions before installation')
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);p.apply('aligned_native_platform_doors',session_lock=lock);stage=ROOT/'.Codex/r22-native/r23-platform-alignment2/projectseele/geofront';target=WORLD/'mtr/projectseele/geofront';backup=OUT/('native_before_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));shutil.copytree(target,backup)
  old,new=hashes(target),hashes(stage)
  for name in sorted(set(old)|set(new)):
   dst=(target/name).resolve();assert dst.is_relative_to(target.resolve())
   if name in new:dst.parent.mkdir(parents=True,exist_ok=True);atomic_replace(dst,(stage/name).read_bytes())
   elif dst.is_file():dst.unlink()
  assert hashes(target)==new
  for name in ('native_transit_r20.json','native_transit_r22.json','native_transit_r23.json'):shutil.copy2(OUT/'built2/native_final.json',WORLD/name)
  source=WORLD/'regional_plan.json';meta=json.loads(source.read_text(encoding='utf8'));meta['transit_r23']['platform_door_pitch']=5;meta['transit_r23']['rail_lengths']={'R1':130,'S1':100};meta['transit_r23']['native_source']='r23-platform-alignment2';source.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
 print('Native station stop/gate alignment installed',flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
