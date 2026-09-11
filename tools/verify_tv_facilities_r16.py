"""Cold-save invariants for R16, using the shared block reader exclusively."""
from pathlib import Path
import json,hashlib,uuid,msvcrt
import nbtlib,numpy as np
from query_blocks import iter_block_entities
from regional_voxels import ROOT,WORLD,DIM
from scan_regional_completion import volume
OUT=ROOT/'artifacts/tv_facilities_r16'
def uid(a):return str(uuid.UUID(bytes=np.asarray(a,dtype='>i4').tobytes()))
def main():
 checks={};detail={};base=json.loads((OUT/'baseline.json').read_text())
 checks['protected_user_files_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in base['protected'].items())
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  a,p=volume((6,-329,303),(54,-315,351));panes=sum(int((a==i).sum()) for i,s in enumerate(p) if s.startswith('projectseele:one_way_glass['));entities=sum(1 for _,t in iter_block_entities(WORLD,DIM,(6,-329,303),(54,-315,351)) if str(t.get('id',''))=='projectseele:one_way_glass');checks['one_way_windows_2344_preserved']=panes==entities==2344
  checks['piano_book_preserved']=any('Book' in t for _,t in iter_block_entities(WORLD,DIM,(12,-388,356),(12,-388,356)))
  fleet=nbtlib.load(WORLD/'data/projectseele_eva_fleet.dat')['data']['Fleet'];detail['fleet']=[dict(uuid=uid(t['Canonical']),phase=str(t['Phase'])) for t in fleet]
  checks['canonical_evas_preserved']=sorted(t['uuid'] for t in detail['fleet'])==sorted(['4e449cf5-9726-4810-b07b-81aca77d0868','972271c6-dd86-472d-938e-4dc3a363f343','d0694537-3e22-4a39-a92a-cb14330ad150'])
  checks['main_fleet_parked']=all(t['phase']=='PARKED' for t in detail['fleet'])
  roster=json.loads((WORLD/'nerv_staff_r15.json').read_text(encoding='utf8'))['stations'];checks['staff_229_posts']=len(roster)==229;checks['military_68_posts']=sum(s['role'].startswith('un_') for s in roster)==68;checks['no_city_surface_npcs']=not any(s['feet'][1]>=0 and s['feet'][0]<6000 for s in roster)
  checks['full_circulation_catalog_8550']=len(json.loads((WORLD/'quality_walk_cases.json').read_text()))==8550
  for v,cx in enumerate([-12,30,72]):
   for z in [-96,-36]:a,p=volume((cx,-443,z),(cx,-443,z));checks[f'carrier_marker_{v}_{z}']=p[int(a[0,0,0])]=='minecraft:lodestone'
   for x,z in [(cx-7,-110),(cx+7,-110),(cx,-105),(cx,-120)]:
    a,p=volume((x,-395,z),(x,-392,z));states=[p[int(i)] for i in a[:,0,0]];checks[f'ring_support_{x}_{z}']=states[0] not in ('minecraft:air','minecraft:void_air') and states[1] in ('minecraft:air','minecraft:void_air') and states[2] in ('minecraft:air','minecraft:void_air')
  checks['tv_world_commission_marker']=(WORLD/'tv_facilities_r16.json').is_file()
 (OUT/'main_world_verification.json').write_text(json.dumps(dict(checks=checks,detail=detail),ensure_ascii=False,indent=2),encoding='utf8');failed=[k for k,v in checks.items() if not v];print('R16 cold main checks',len(checks),'failed',failed);assert not failed
if __name__=='__main__':main()
