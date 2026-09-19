"""Close the measured public drop edges; retain the real ladder and retire our spare stub."""
from pathlib import Path
import json
import regional_voxels as v
from query_blocks import read_box,iter_block_entities,AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R25_REVIEW';OUT=ROOT/'artifacts/facility_r25/edge_finish'
def main():
 OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();proof=json.loads((ROOT/'artifacts/facility_r25/edge_audit/candidates.json').read_text());guards=[];kept=[]
 for i,r in enumerate(proof['risks']):
  a=r['from_pos'];q=tuple(r['open_side'])
  if a==[24,-423,254]:kept.append(dict(**r,reason='Existing south-facing ladder supplies a real vertical connection'));continue
  if a[1]==-367 and -24<=a[0]<=-22 and a[2]==-267:continue
  box=(q[0],q[1]-2,q[2]);top=(q[0],q[1]+1,q[2]);cells=read_box(WORLD,v.DIM,box,top)
  assert not list(iter_block_entities(WORLD,v.DIM,box,top)),q
  for pos,old in cells.items():
   assert old.split('[')[0] in AIR,('An edge acquired an occupied block',pos,old)
   material='projectseele:nerv_structural_panel' if pos[1]<q[1] else 'projectseele:clear_glass'
   p.match((*pos,*pos),old,material,'r25/continuous_public_edge_guard')
  guards.append(dict(id='r25/connected_public_edge/'+str(i),start=[a[0]+.5,a[1],a[2]+.5],direction=[q[0]-a[0],0,q[2]-a[2]]))
 # At the upper stop the old through gallery is north of Z=-275. The
 # lower stop needs the south arm; its copied upper-floor arm had no destination.
 cold=Path(json.loads((ROOT/'artifacts/facility_r25/baseline.json').read_text())['backup'])/'world'
 lo=(-25,-369,-275);hi=(-21,-362,-267);now=read_box(WORLD,v.DIM,lo,hi);before=read_box(cold,v.DIM,lo,hi)
 assert not list(iter_block_entities(WORLD,v.DIM,lo,hi))
 retired=0
 for q,old in now.items():
  if old!=before[q]:p.match((*q,*q),old,before[q],'r25/retire_own_upper_lift_blind_arm');retired+=1
 p.meta.update(guards=guards,preserved_vertical_ports=kept,retired_own_stub_cells=retired);p.apply('public_edges_and_upper_lift_end')
 (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8')
 old=json.loads((WORLD/'r23_guard_cases.json').read_text(encoding='utf8')) if (WORLD/'r23_guard_cases.json').exists() else []
 retained=[];retired_old=[]
 for q in old:
  x,y,z=q['start']
  if 102<=x<=115 and -443<=y<=-437 and -291<=z<=-50:retired_old.append(q);continue
  retained.append(q)
 (WORLD/'r25_guard_cases.json').write_text(json.dumps(retained+guards,ensure_ascii=False,indent=2),encoding='utf8')
 (OUT/'retired_old_guard_cases.json').write_text(json.dumps(retired_old,ensure_ascii=False,indent=2),encoding='utf8')
 print('New edge pushes',len(guards),'retained',len(retained),'retired unused upper stub cells',retired)
if __name__=='__main__':main()
