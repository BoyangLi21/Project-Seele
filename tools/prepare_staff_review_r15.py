"""Cold, isolated copy of the real staff facilities for native and dedicated review."""
import json,shutil,msvcrt,hashlib,sys
from pathlib import Path
import nbtlib
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906';DEST=ROOT/'run/saves/SEELE_STAFF_REVIEW_R15'

def main():
 global DEST
 if '--controls' in sys.argv:DEST=ROOT/'run/saves/SEELE_STAFF_CONTROL_R15'
 roster=json.loads((ROOT/'artifacts/staff_world_r15/nerv_staff_r15.json').read_text(encoding='utf8'))
 if DEST.exists():print('Existing review preserved:',DEST);return
 with (SOURCE/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);DEST.mkdir();rows=[]
  regions=set()
  for s in roster['stations']:
   x,y,z=s['feet']
   for xx in [x-128,x,x+128]:
    for zz in [z-128,z,z+128]:regions.add((xx//512,zz//512))
  for rx,rz in sorted(regions):
   for kind in ['region','entities','poi']:
    rel=Path('dimensions/projectseele/geofront')/kind/f'r.{rx}.{rz}.mca';src=SOURCE/rel
    if src.exists():
     dst=DEST/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);rows.append(dict(file=rel.as_posix(),size=src.stat().st_size))
  for rel in ['data','datapacks','serverconfig','dimensions/projectseele/geofront/data']:
   if (SOURCE/rel).exists():shutil.copytree(SOURCE/rel,DEST/rel,dirs_exist_ok=True)
  for name in ['.projectseele_tv_world_preview.json','.projectseele_spatial_preview_read_only.json','.projectseele_s20_rebuild.json','regional_plan.json','regional_commission_receipt.json','r07_installations.json','r07_commissioned.json','regional_native_platforms_ready.json']:
   if (SOURCE/name).exists():shutil.copy2(SOURCE/name,DEST/name)
  data=nbtlib.load(SOURCE/'level.dat');d=data['Data'];d['LevelName']=nbtlib.String('SEELE R15 staff native review');d.pop('Player',None)
  data.save(DEST/'level.dat');(DEST/'session.lock').write_bytes(b'\0');shutil.copy2(ROOT/'artifacts/staff_world_r15/nerv_staff_r15.json',DEST/'nerv_staff_r15.json')
  (ROOT/'artifacts/staff_world_r15'/('control_copy.json' if '--controls' in sys.argv else 'native_copy.json')).write_text(json.dumps(dict(source=str(SOURCE),destination=str(DEST),files=rows,bytes=sum(r['size'] for r in rows)),indent=2))
 print(DEST,'regions',len(regions),'copied MB',round(sum(r['size'] for r in rows)/1e6))
if __name__=='__main__':main()
