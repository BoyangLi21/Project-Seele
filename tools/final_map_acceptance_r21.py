"""Assemble evidence gates; never equate authored geometry with passed gameplay."""
import gzip,json,hashlib
from pathlib import Path
import numpy as np
from query_blocks import iter_selected_sections,AIR
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r21';WORLD=ROOT/'run/saves/SEELE_R21_REVIEW'
def read(name):return json.loads((OUT/name).read_text(encoding='utf8'))
def main():
 checks={}
 r=read('full_native_walk_final.json');assert r['passed'] and len(r['results'])==8865 and all(x['status']=='pass' for x in r['results']);checks['native_routes']=8865
 un=json.loads((ROOT/'artifacts/un_models_r21/boarding/native_acceptance.json').read_text());assert un['passed'];checks['un_catwalks']=un
 r=read('native_lift_pass.json');assert not r['error'] and not r['damage'] and len(r['trips'])==4;checks['native_passenger_lift_trips']=4
 r=read('edge_physics_pass.json');assert r['passed'];checks['native_edge_and_belt_cases']=len(r['checks'])
 r=read('native_factory_pass.json');phases={x['phase'] for x in r};assert {'PLUG_INSERTING','PLUG_LOCKING','TO_SILO','SILO_READY','DEPLOYED','DESCENDING','TO_HANGAR','FILLING','PARKED'}<=phases;checks['native_factory_cycle']=True
 for name in ('native_flight_pass.json','native_un_boarding_pass.json'):
  r=read(name);assert r['passed'] and r['nativePassengerRegistration'];checks[name]=r
 assert checks['native_flight_pass.json']['oppositeAirportStop']
 r=read('battlefield/native_flat_proof.json');assert r['passed'] and r['columns']==123904 and r['runtime_conflicts']==0;checks['flat_battlefield_columns']=r['columns']
 assert read('battlefield/native_restoration.json')['depth']==0
 for name in ('airport/clearance_final/transit_clearance.json','airport/airborne_final/flight_clearance.json'):
  r=read(name);assert r['rails']==r['passed'];checks[name]=r['passed']
 r=read('global_audit/spatial_footprint.json');assert not r['candidates'] and r['checked_footprint_cells']>=19000;checks['full_corridor_footprint']=r['checked_footprint_cells']
 assert read('review_preservation.json')['passed'];checks['preserved_command_cells']=read('review_preservation.json')['command_cells_unchanged']
 r=read('wayfinding/verification.json');assert r['passed'] and r['mounted_boards']==12;checks['backed_wayfinding_boards']=12
 assert read('sound_acceptance.json')['passed'];r=read('audio_v2/metrics.json');assert r['alarm_peak']<=.32 and not r['pitch_sweep'];checks['natural_pa_and_fixed_tone_alarm']=True
 for r in read('audio_v2/sources.json'):
  path=ROOT/'src/main/resources/assets/projectseele/sounds'/(r['name']+'.ogg');assert hashlib.sha256(path.read_bytes()).hexdigest()==r['sha256']
 # Re-read every final island repair. Removing an isolated component cannot
 # detach another one; additions explicitly join the original ground/walls.
 receipt=sorted((OUT/'global_audit/cleanup/classified_whole_map_repairs').glob('applied_*/receipt.json'))[-1];folder=receipt.parent
 selected={};payloads={}
 for p in (folder/'delta').glob('c.*.npz'):
  x,z=map(int,p.stem.split('.')[1:]);d=np.load(p);offset=d['offsets'].astype(np.int64);sy=(offset//256+int(d['minimum']))//16;selected[x,z]=set(map(int,sy));payloads[x,z]=(d,sy)
 checked=0
 for x,z,sy,palette,blocks in iter_selected_sections(WORLD,'projectseele:geofront',selected):
  d,ys=payloads[x,z];keep=ys==sy;idx=(d['offsets'][keep]%4096).astype(int)
  assert np.array_equal(np.asarray(palette)[blocks[idx]],d['palette'][d['after'][keep]]),(x,z,sy);checked+=len(idx)
 assert checked==1800;checks['final_component_repair_cells_readback']=checked
 with gzip.open(OUT/'global_audit/components/isolated_soil_points.json.gz','rt') as f:soil=json.load(f)
 assert not any(-144<=x['pos'][0]<=207 and 41<=x['pos'][2]<=392 and x['pos'][1]>=80 for x in soil),'A later natural removal changed the proven battlefield'
 checks['component_full_chunks']=47842;checks['natural_residue_removed']=744;checks['retired_structure_cells']=61
 visual=read('visual_acceptance.json');assert visual['passed'],'Inspect final native screenshots before installation';checks['native_visual_review']=visual
 result=dict(passed=True,world=str(WORLD),checks=checks,scope='R21 map, transport, signs and audio; model commissioning evidence is in artifacts/un_models_r21')
 (OUT/'map_acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print('R21 map acceptance complete')
if __name__=='__main__':main()
