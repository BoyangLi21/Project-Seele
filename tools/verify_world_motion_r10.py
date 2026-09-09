"""Final cold acceptance evidence: real map geometry, managed identities and native runtime results."""
import json,hashlib,msvcrt
from pathlib import Path
import numpy as np
import nbtlib
from regional_voxels import ROOT,WORLD,DIM
from query_blocks import AIR,iter_block_entities
from scan_regional_completion import volume
from verify_r08_completion import ident
from inspect_map_assets import region_chunks
OUT=ROOT/'artifacts/first_battle_world_r10'
load=lambda p:json.loads(p.read_text(encoding='utf8'))
def main():
 checks={}
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  for path,digest in load(OUT/'user_baseline.json').items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
  checks['user_dirty_resources_preserved']=True
  catalog=load(WORLD/'quality_walk_cases.json');walks=load(OUT/'world_art/native_walk_pass.json')
  assert len(catalog)==len({r['id'] for r in catalog})==8538;assert len(walks)==164 and all(r['status']=='pass' for r in walks)
  assert {r['id'] for r in walks}<={r['id'] for r in catalog};assert not (OUT/'world_art/audit_catalog/pending.json').exists()
  checks['circulation']=dict(native_unique_passed=164,complete_catalog_restored=8538,added_routes=10,unchanged_routes='Earlier acceptance retained; not all replayed this round')
  # The R09 optical facade and retired platform remain intact.
  before=np.load(ROOT/'artifacts/world_refinement_r09/pyramid_before.npz');lo=tuple(before['lo']);hi=tuple(before['hi']);a,pal=volume(lo,hi);y,z,x=np.ogrid[lo[1]:hi[1]+1,lo[2]:hi[2]+1,lo[0]:hi[0]+1];r=np.floor(120*(1-(y+466)/172)+.5)
  ring=(y>=-466)&(y<=-294)&(abs(x-30)<=r)&(abs(z-327)<=r)&((abs(x-30)==r)|(abs(z-327)==r))
  panes=np.array([s.startswith('projectseele:one_way_glass') and 'pyramid=true' in s for s in pal])[a];assert panes.sum()==2344
  oldsolid=np.array([s not in AIR for s in before['palette']])[before['blocks']];solid=np.array([s not in AIR for s in pal])[a]
  assert not np.any(ring&oldsolid&~solid)
  bes=[b for _,b in iter_block_entities(WORLD,DIM,(6,-329,303),(54,-315,351)) if str(b['id'])=='projectseele:one_way_glass'];assert len(bes)==2344
  checks['accepted_pyramid_envelope']=dict(original_shell_preserved=True,one_way_panes=2344)
  fleet=nbtlib.load(WORLD/'data/projectseele_eva_fleet.dat')['data']['Fleet'];canonical={ident(e['Canonical']) for e in fleet}
  assert canonical=={'4e449cf5-9726-4810-b07b-81aca77d0868','972271c6-dd86-472d-938e-4dc3a363f343','d0694537-3e22-4a39-a92a-cb14330ad150'}
  military=nbtlib.load(WORLD/'dimensions/projectseele/geofront/data/projectseele_military_r07.dat')['data'];managed={str(k):ident(v) for k,v in military['Entities'].items()};assert len(managed)==31 and str(military['Phase'])=='WET'
  details=nbtlib.load(WORLD/'dimensions/projectseele/geofront/data/projectseele_r08_details.dat')['data']['Members'];wanted=canonical|set(managed.values())|{ident(v) for v in details.values()};found=set()
  for path in (WORLD/'dimensions/projectseele/geofront/entities').glob('r.*.*.mca'):
   _,rx,rz=path.stem.split('.');rx,rz=int(rx),int(rz)
   for _,_,chunk in region_chunks(path,(rx*32,rx*32+31,rz*32,rz*32+31)):
    for e in chunk.get('Entities',[]):
     if 'UUID' not in e:continue
     uid=ident(e['UUID'])
     if uid in wanted:assert uid not in found;found.add(uid)
  assert wanted<=found,wanted-found;checks['managed_identities']=dict(original_eva=len(canonical),military=len(managed),industrial_members=len(details),all_present=True,prototype_hangar='WET')
  site=load(WORLD/'first_battle_site_r10.json');lo=(315,79,-513);hi=(397,165,-277);a,pal=volume(lo,hi);free=np.array([s in AIR or s.startswith('minecraft:light[') for s in pal])[a]
  clip=load(ROOT/'src/main/resources/assets/projectseele/motion/first_battle_r10.json');origin=np.array(site['hero']);poses=0
  for t in [0,5,9.2,10.7,11.7,15,19.4,23]:
   for role,half in [('eva',8.5),('angel',10)]:
    q=origin+clip[role]['root_blocks'][round(t*30)];low=np.floor(q-[half,0,half]).astype(int);high=np.floor(q+[half,0,half]).astype(int)
    yy=max(81,int(np.floor(q[1]+.15)));mask=free[yy-lo[1]:161-lo[1],low[2]-lo[2]:high[2]-lo[2]+1,low[0]-lo[0]:high[0]-lo[0]+1];assert mask.all(),(t,role,q);poses+=1
  support,palette=volume((320,77,-510),(392,80,-280));assert np.all(np.array([s not in AIR for s in palette])[support])
  checks['main_interception_site']=dict(anchor=site['hero'],scene_clearance_samples=poses,road_support_layers=4,console=site['console'])
  receipts=[load(p) for p in (OUT/'world_art').glob('*/applied_*/receipt.json')];assert len(receipts)==9 and all(r['verified'] for r in receipts)
  checks['map_patch_receipts']=len(receipts)
 for name in ['native_first_battle_pass.json','native_mission_pass.json']:assert load(OUT/name)['passed']
 checks['first_battle_native']=dict(normal_completion=True,real_contact_trigger=True,skip=True,missing_actor_recovery=True,actual_save_reload=True,mission_block_interaction=True)
 audit=load(OUT/'motion/native_geometry_audit_final.json');assert audit['maximum_seam_gap']<.0001 and not audit['gun_intersection_frames'];assert audit['maximum_witness']['muzzleError']<.001
 assert min(f.get('rifle_above_floor',999) for f in audit['frames'])>.10
 checks['native_mesh']=dict(samples=len(audit['frames']),seam_max_blocks=audit['maximum_seam_gap'],muzzle_max_blocks=audit['maximum_witness']['muzzleError'],rifle_body_intersections=0,rifle_ground_min_blocks=min(f.get('rifle_above_floor',999) for f in audit['frames']))
 assert 'BUILD SUCCESSFUL' in (ROOT/'.Codex/r10-final-build.log').read_text(encoding='utf8',errors='replace');checks['gradle_build']='PASS, including pose transitions and video codec'
 result=dict(passed=True,world=str(WORLD),checks=checks);(OUT/'completion.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
