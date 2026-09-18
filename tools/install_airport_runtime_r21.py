"""Install the separately verified F2 native graph and its bounded world manifests."""
import json,shutil,msvcrt
from pathlib import Path
from stage_native_transit_repair import hashes
from apply_s20_approved_semantic_repairs import atomic_replace
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r21/airport';WORLD=ROOT/'run/saves/SEELE_R21_REVIEW'
def main():
 proof=json.loads((OUT/'cadence_final.json').read_text());assert proof['passed'];stage=ROOT/'.Codex/r21-transit/projectseele/geofront';target=WORLD/'mtr/projectseele/geofront';backup=OUT/'native_before'
 if backup.exists():
  import datetime
  backup=OUT/('native_before_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);before=hashes(target);after=hashes(stage);shutil.copytree(target,backup)
  for path in sorted(set(before)|set(after)):
   dest=(target/path).resolve();assert dest.is_relative_to(target.resolve())
   if path in after:
    dest.parent.mkdir(parents=True,exist_ok=True)
    if before.get(path)!=after[path]:atomic_replace(dest,(stage/path).read_bytes())
   elif dest.exists():dest.unlink()
  assert hashes(target)==after
  gatefile=WORLD/'regional_boarding_gates.json';shutil.copy2(gatefile,OUT/'boarding_before.json');g=json.loads(gatefile.read_text());new=json.loads((OUT/'boarding_gates.json').read_text());g['gates']=[r for r in g['gates'] if r['id'] not in {q['id'] for q in new}]+new;gatefile.write_text(json.dumps(g,indent=2))
  (WORLD/'nerv_airport_r21.json').write_text(json.dumps(dict(version=21,vehicles=json.loads((OUT/'vehicles.json').read_text()))))
  planfile=WORLD/'regional_plan.json';plan=json.loads(planfile.read_text(encoding='utf8'));plan['armament_position']=[120.5,80,-35.5];plan['nerv_airport_r21']=dict(gate=[670.5,72,-9.5],un_gate=[6720.5,74,-6109.5],line='F2',headway_ms=60000);planfile.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
 (OUT/'native_install.json').write_text(json.dumps(dict(world=str(WORLD),before=before,after=after,source=str(stage),schedule_passed=True),indent=2))
 print('F2 native graph and boarding installed, old F1 and train identities retained')
if __name__=='__main__':main()
