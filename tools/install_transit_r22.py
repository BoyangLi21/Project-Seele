"""Install the verified through network with reversible file-level retirement."""
from pathlib import Path
import argparse,datetime,json,msvcrt,shutil
from stage_native_transit_repair import hashes
from apply_s20_approved_semantic_repairs import atomic_replace
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/access_r22/transit'
def main(world):
 world=Path(world).resolve();stage=ROOT/'.Codex/r22-native/rebuilt4/projectseele/geofront';target=world/'mtr/projectseele/geofront'
 if (world/'native_transit_r23.json').exists():raise RuntimeError('This world has the newer R23 bridge profile; the old R22 graph must not overwrite it')
 final=json.loads((OUT/'built4/native_final.json').read_text(encoding='utf8'));before_native=json.loads((OUT.parent/'native_before.json').read_text(encoding='utf8'));plan=json.loads((OUT/'native_plan.json').read_text(encoding='utf8'))
 assert {r['id'] for r in before_native['routes']}-{r['id'] for r in final['routes']}==set(plan['retired_routes'])
 for kind in ('trains','F2'):
  proof=json.loads((OUT/f'built4/cadence_{kind}.json').read_text(encoding='utf8'));assert proof['passed'] and len(proof['cycles'])==(4 if kind=='trains' else 1)
 assert json.loads((OUT/'geometry_audit.json').read_text())['passed']
 if world.name!='SEELE_R22_REVIEW':assert json.loads((OUT.parent/'final_acceptance.json').read_text())['passed']
 backup=OUT/('install_'+world.name+'_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
 with (world/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);before=hashes(target);after=hashes(stage);shutil.copytree(target,backup/'before')
  for relative in sorted(set(before)|set(after)):
   dest=(target/relative).resolve();assert dest.is_relative_to(target.resolve())
   if relative in after:
    if before.get(relative)!=after[relative]:dest.parent.mkdir(parents=True,exist_ok=True);atomic_replace(dest,(stage/relative).read_bytes())
   elif dest.is_file():
    retired=(backup/'retired'/relative).resolve();assert retired.is_relative_to(backup.resolve());retired.parent.mkdir(parents=True,exist_ok=True);dest.rename(retired)
  assert hashes(target)==after
  (world/'native_transit_r22.json').write_text(json.dumps(final,ensure_ascii=False,separators=(',',':')),encoding='utf8')
  # Consumers of the older snapshot name must not keep advertising retired lines.
  shutil.copy2(world/'native_transit_r20.json',backup/'native_transit_r20.json');shutil.copy2(world/'native_transit_r22.json',world/'native_transit_r20.json')
  planfile=world/'regional_plan.json';shutil.copy2(planfile,backup/'regional_plan.json');meta=json.loads(planfile.read_text(encoding='utf8'));meta['transit_r22']={'surface_routes':['R1','S1'],'headway_ms':60000,'timezone':'Asia/Shanghai','cruise_F2_kmh':540,'consists':{'R1':6,'S1':4,'U1':4,'U2':4},'snapshot':'native_transit_r22.json'};planfile.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
 (backup/'receipt.json').write_text(json.dumps(dict(world=str(world),source=str(stage),before=before,after=after,retired_route_ids=plan['retired_routes'],preserved_other_route_ids=[r['id'] for r in final['routes']],minute_headway_verified=True),indent=2));print('R22 native network installed',world.name)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--world',default=str(ROOT/'run/saves/SEELE_R22_REVIEW'));main(ap.parse_args().world)
