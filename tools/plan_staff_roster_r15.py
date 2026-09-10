"""Locate posts inside named, measured facilities; leave city streets unpopulated."""
import json,math,hashlib
from pathlib import Path
import numpy as np
from scan_regional_completion import volume,passable
from regional_voxels import ROOT,WORLD,DIM
OUT=ROOT/'artifacts/staff_world_r15';OUT.mkdir(parents=True,exist_ok=True)
def main():
 stations=[];held=[];used=[];surveys=[]
 def add(id,name,role,skin,pos,yaw,room):
  if any(np.linalg.norm((np.array(pos)-q)*[1,.8,1])<2.2 for q in used):return False
  a,p=volume((pos[0],pos[1]-1,pos[2]),(pos[0],pos[1]+1,pos[2]));states=[p[int(x)] for x in a[:,0,0]]
  if not(passable(states[1]) and passable(states[2]) and not passable(states[0])):held.append(dict(id=id,pos=pos,states=states));return False
  stations.append(dict(id=id,name=name,role=role,skin=skin,feet=pos,yaw=yaw,room=room));used.append(np.array(pos));return True
 for id,name,role,skin,pos in [('misato','葛城美里','commander','misato',[28,-409,283]),('ritsuko','赤木律子','scientist','ritsuko',[31,-409,280]),('maya','伊吹摩耶','operator','maya',[26,-409,288]),('hyuga','日向诚','operator','operator',[24,-409,280]),('aoba','青叶茂','operator','operator',[32,-409,287])]:add(id,name,role,skin,pos,180,'main_command')
 rooms=[]
 for path in ['artifacts/world_motion_r04/pyramid/places.json','artifacts/world_expansion_20260907/geometry_all/places.json']:
  for r in json.loads((ROOT/path).read_text(encoding='utf8'))['rooms']:
   if r['floor']<0:rooms.append(dict(r,military=False))
 for path in ['base_architecture','secret_architecture']:
  for r in json.loads((ROOT/f'artifacts/world_expansion_r07/{path}/places.json').read_text(encoding='utf8'))['rooms']:
   if 'stair' in r['id'] or 'main_hangar' in r['id']:continue
   x0,z0,x1,z1=r['bounds'];rooms.append(dict(r,bounds=[x0,x1,z0,z1],purpose='MILITARY',military=True))
 seen=set()
 for r in rooms:
  x0,x1,z0,z1=r['bounds'];f=r['floor'];key=(x0,x1,z0,z1,f)
  if key in seen:continue
  seen.add(key);lo=(x0,f,z0);hi=(x1,f+3,z1);a,p=volume(lo,hi);free=np.array([passable(s) for s in p]);solid=np.array([not passable(s) and not any(v in s for v in ['_stairs','_slab','glass_pane','_fence','_bars','door','bed[','chair','stool','sofa']) for s in p]);stand=solid[a[0]]&free[a[1]]&free[a[2]]
  candidate=[];entry=r.get('entry',[(x0+x1)//2,f+1,z1])
  for z,x in np.argwhere(stand):
   xx,zz=x+x0,z+z0;edge=min(xx-x0,x1-xx,zz-z0,z1-zz)
   if not 2<=edge<=5 or abs(xx-entry[0])<4 and abs(zz-entry[2])<5:continue
   # Keep a clear walking strip beside furniture; no posts in door/stair apertures.
   if x<1 or z<1 or x>=stand.shape[1]-1 or z>=stand.shape[0]-1:continue
   if stand[z-1:z+2,x-1:x+2].sum()<7:continue
   score=int(hashlib.sha256(f'{r["id"]}/{xx}/{zz}'.encode()).hexdigest()[:8],16);candidate.append((score,int(xx),int(zz)))
  candidate.sort();purpose=r.get('purpose','TECHNICAL');military=r['military'];target=5 if military else 3 if purpose in ('BRIEFING','ANALYSIS','MEDICAL','CAFETERIA') else 2;count=0;accepted=[]
  role='un_crew' if military else 'medic' if purpose=='MEDICAL' else 'operator' if purpose in ('ANALYSIS','BRIEFING','SEELE LINK') else 'technician'
  for _,x,z in candidate:
   if count>=target:break
   if any((x-ax)**2+(z-az)**2<7**2 for ax,az in accepted):continue
   pos=[x,f+1,z];id='staff/'+r['id'].replace(' ','_').lower()+f'/{count}';yaw=math.degrees(math.atan2(-((x0+x1)/2-x),(z0+z1)/2-z))
   if add(id,('UN 整备人员' if military else 'NERV '+{'medic':'医护人员','operator':'操作员','technician':'技术人员'}[role])+f' {count+1:02d}',role,role,pos,yaw,r['id']):count+=1;accepted.append((x,z))
  surveys.append(dict(room=r['id'],purpose=purpose,military=military,target=target,placed=count,bounds=[lo,hi]))
 # Named service platforms and guarded circulation endpoints, all previously authored.
 for v,x in enumerate([8,50,92]):
  for n,z in enumerate([-120,-106]):add(f'hangar/{v}/{n}',f'NERV 机库整备员 {v*2+n+1:02d}','technician','technician',[x,-394,z],180,f'cage_gallery_{v}')
 anchors=[('hangar_plant',[172,-442,-46]),('hangar_walkway',[114,-442,80]),('arrival',[-374,-466,728]),('dogma_checkpoint',[12,-566,285]),('sigma_checkpoint',[273,-466,633]),('hq_station',[32,-466,473])]
 for name,pos in anchors:
  add('guard/'+name,'NERV 值班警卫','guard','guard',pos,0,name)
 for n,pos in enumerate([[6390,75,-6650],[6410,75,-6650],[6520,75,-6670],[6808,75,-6020],[6390,77,-6150],[6407,77,-6150],[6430,77,-6240],[6453,77,-6240]]):add(f'un/guard/{n}','UN 警卫','un_guard','un_guard',pos,0,'un_base')
 add('legacy_ward/nurse','NERV 值班医护','medic','medic',[-49,-448,314],180,'legacy_command_ward')
 add('legacy_ward/technician','NERV 勤务人员','technician','technician',[-61,-448,307],90,'legacy_command_ward')
 data=dict(schema=1,dimension=DIM,stations=stations,city_surface_staff=0)
 (OUT/'nerv_staff_r15.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');(OUT/'staff_survey.json').write_text(json.dumps(dict(rooms=surveys,held=held,total=len(stations),military=sum(s['role'].startswith('un_') for s in stations)),ensure_ascii=False,indent=2),encoding='utf8');print('Planned staff',len(stations),'military',sum(s['role'].startswith('un_') for s in stations),'held candidates',len(held),flush=True)
if __name__=='__main__':main()
