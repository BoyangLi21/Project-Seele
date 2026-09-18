"""Keep the UN defenses and move native takeoff/touchdown away from their roofs."""
import copy,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r21/airport'
def main():
 source=json.loads((OUT/'native_plan.json').read_text(encoding='utf8'));ids={f'F2_un_depart{i}' for i in range(3)}|{'F2_un_roll','F2_un_takeoff','F2_un_land','F2_un_rollin'}
 old=[r for r in source['rails'] if r['id'] in ids];assert len(old)==7
 geometry=[('un_depart0',[6720,74,-6110],[6720,74,-6220],'N','S','rail',45),('un_depart1',[6720,74,-6220],[6760,74,-6260],'N','W','rail',45),('un_depart2',[6760,74,-6260],[6784,74,-6300],'E','S','rail',45),('un_roll',[6784,74,-6300],[6784,74,-6600],'N','S','rail',260),('un_takeoff',[6784,74,-6600],[6784,185,-6960],'N','S','runway',360),('un_land',[6832,185,-6960],[6832,74,-6480],'S','N','runway',260),('un_rollin',[6832,74,-6480],[6832,74,-6160],'S','N','rail',200)]
 new=[dict(id='F2_'+n,**{'from':a,'to':b},from_angle=aa,to_angle=bb,kind=k,mode='AIRPLANE',speed=s,reverse_speed=0) for n,a,b,aa,bb,k,s in geometry]
 receipt=json.loads((OUT/'native/native_transit_receipt.json').read_text());line=receipt['lines'][0]
 plan=dict(rails=new,retire_rails=old,stations=[],lines=[],regenerate_depots=[dict(line='F2',depot_id=line['depot_id'],siding_id=line['siding_id'],restart_vehicles=True,cruise=260,repeat=True)])
 dest=OUT/'revision2';dest.mkdir(exist_ok=True);(dest/'native_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
 rt=json.loads((ROOT/'artifacts/world_rebuild_r20/transit/runtime.json').read_text());java=Path(rt['java']);cp=rt['classpath']+';'+str(ROOT/'.Codex/r21-java')
 subprocess.run([str(java/'java.exe'),'-cp',cp,'RegionalTransitAuthor',str(dest/'native_plan.json'),str(ROOT/'.Codex/r21-transit'),str(dest),'--append'],check=True)
 samples=[r for r in json.loads((OUT/'native/track_samples.json').read_text()) if r['id'] not in ids]+json.loads((dest/'track_samples.json').read_text());(OUT/'track_samples_final.json').write_text(json.dumps(samples))
 subprocess.run([str(java/'java.exe'),'-cp',cp,'TransitCadenceR20',str(ROOT/'.Codex/r21-transit'),str(OUT/'cadence_final.json'),'F2','AIRPLANE'],check=True)
 subprocess.run([str(java/'java.exe'),'-cp',cp,'RegionalFlightPathSurvey',str(ROOT/'.Codex/r21-transit'),str(OUT/'native_flight_samples.json'),'F2'],check=True)
 print('UN runway revision complete; defenses untouched')
if __name__=='__main__':main()
