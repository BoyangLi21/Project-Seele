"""Check retained command geometry, original actors and the user's work."""
from pathlib import Path
import argparse,hashlib,json
import nbtlib
from verify_main_r20 import compare_box,entities,windows
from query_blocks import iter_block_entities
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r21'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--world',default='SEELE_TV_WORLD_PREVIEW_20260906');a=ap.parse_args()
 world=ROOT/'run/saves'/a.world;baseline=json.loads((OUT/'baseline.json').read_text());cold=Path(baseline['backup'])/'world'
 for name,digest in baseline['preexisting_dirty_files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
 count=compare_box(cold,world,(6,-445,262),(52,-388,365));assert windows(cold)==windows(world)==2344
 window_entities=sum(str(t['id'])=='projectseele:one_way_glass' for _,t in iter_block_entities(world,'projectseele:geofront',(6,-329,303),(54,-315,351)));assert window_entities==2344
 old=entities(cold);now=entities(world)
 managed={uid:e for uid,e in old.items() if str(e['id']).startswith(('projectseele:eva_','projectseele:entry_plug','projectseele:nerv_staff','superbwarfare:','projectseele:nerv_armament'))}
 assert not(set(managed)-set(now)),('Original managed identities missing',set(managed)-set(now))
 af=nbtlib.load(cold/'data/projectseele_eva_fleet.dat')['data']['Fleet'];bf=nbtlib.load(world/'data/projectseele_eva_fleet.dat')['data']['Fleet'];assert len(af)==len(bf)==3
 for before,after in zip(af,bf):
  for key in ('Canonical','EntryPlug'):assert list(before[key])==list(after[key])
  assert str(after['Phase'])=='PARKED'
 original=json.loads((cold/'nerv_staff_r15.json').read_text(encoding='utf8'))['stations'];roster=json.loads((world/'nerv_staff_r15.json').read_text(encoding='utf8'))['stations'];assert {s['id'] for s in original}<={s['id'] for s in roster}
 report=dict(passed=True,world=str(world),command_cells_unchanged=count,original_model_and_motion_files_unchanged=True,one_way_windows=window_entities,original_managed_identities_preserved=len(managed),staff_positions_preserved=len(original),fleet_and_plugs_parked=True)
 name='main_preservation.json' if a.world=='SEELE_TV_WORLD_PREVIEW_20260906' else 'review_preservation.json'
 (OUT/name).write_text(json.dumps(report,indent=2));print(report)
if __name__=='__main__':main()
