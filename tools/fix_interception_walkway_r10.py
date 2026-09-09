"""Move the avenue lighting to the outer kerb after actual player collision found it in the walking line."""
import json,shutil,msvcrt
import regional_voxels as vox
from scan_regional_completion import volume
from survey_world_art_r10 import OUT
if __name__=='__main__':
 lo=(315,80,-495);hi=(397,88,-295);a,pal=volume(lo,hi);p=vox.Painter()
 def old(pos):x,y,z=pos;return pal[a[y-lo[1],z-lo[2],x-lo[0]]]
 for src,dst in [(317,315),(395,397)]:
  for z in range(-495,-294,40):
   for y in range(81,89):
    here=(src,y,z);there=(dst,y,z);before=old(here)
    assert before.startswith('minecraft:iron_bars') if y<88 else before=='projectseele:nerv_strip_light'
    assert old(there) in {'minecraft:air','minecraft:cave_air'}
    p.match((*here,*here),before,'minecraft:air','r10/walkway_lighting/retire');p.match((*there,*there),old(there),before,'r10/walkway_lighting/outer_kerb')
   base=(dst,80,z);p.match((*base,*base),old(base),'minecraft:smooth_stone','r10/walkway_lighting/foundation')
 vox.OUT=OUT;p.apply('walkway_lighting_fix')
 with (vox.WORLD/'session.lock').open('r+b') as lock:
  msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  source=vox.WORLD/'quality_native_walk_results.json';shutil.copy2(source,OUT/'native_walk_first.json');results=json.loads(source.read_text(encoding='utf8'))
  bad={r['id'] for r in results if r['status']!='pass'};cases=json.loads((vox.WORLD/'quality_walk_cases.json').read_text(encoding='utf8'));chosen=[r for r in cases if r['id'] in bad];assert len(chosen)==4
  (vox.WORLD/'quality_walk_cases.json').write_text(json.dumps(chosen,indent=2),encoding='utf8')
