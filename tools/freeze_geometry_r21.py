"""Freeze a read-only block survey dataset before passenger reviews resume."""
from pathlib import Path
import hashlib,json,msvcrt,shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/world_repair_r21';WORLD=ROOT/'run/saves/SEELE_R21_REVIEW'
def main():
 target=OUT/'global_audit/world_geometry'
 assert not target.exists(),'Do not silently reuse a stale geometry snapshot'
 with (WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  source=WORLD/'dimensions/projectseele/geofront/region'
  shutil.copytree(source,target/'dimensions/projectseele/geofront/region')
  for name in ('regional_wayfinding.json','regional_boarding_gates.json','quality_walk_cases.json'):
   shutil.copy2(WORLD/name,target/name)
  receipt={p.name:hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in source.glob('*.mca')}
 (OUT/'global_audit/frozen_geometry.json').write_text(json.dumps(dict(source=str(WORLD),snapshot=str(target),region_sha256=receipt),indent=2))
 print('Frozen',len(receipt),'regions for complete 3D scan')
if __name__=='__main__':main()
