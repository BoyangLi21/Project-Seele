"""Transparent, load-bearing viewing bays remove the measured downward occlusion."""
import json
import numpy as np
import regional_voxels as v
import scan_regional_completion as scan
import plan_factory_r20 as factory
from repair_containment_r23 import LO,HI,sightlines
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23/observation'
def main():
 OUT.mkdir(parents=True,exist_ok=True);v.WORLD=scan.WORLD=WORLD;v.OUT=OUT;factory.LO=LO;factory.HI=HI;s=factory.Scene();p=v.Painter();before=sightlines(s.before,s.palette);bays=[]
 allowed={'projectseele:nerv_floor_panel','projectseele:nerv_structural_panel','projectseele:clear_glass','minecraft:glass','minecraft:light_gray_stained_glass'}
 for c in (-12,30,72):
  # The front shell has a three-block-thick opaque sill below its old pane.
  # Replace that bounded viewing strip with pressure glass, retaining the
  # complete side piers and the wet-cell boundary far below it.
  box=(c-6,-380,-269,c+6,-375,-267);sl=s.index(box);a=s.after[sl];opaque=np.array([q in {'projectseele:nerv_machine_panel','projectseele:nerv_shaft_panel','projectseele:nerv_structural_panel'} for q in s.palette])[a];a[opaque]=s.state('projectseele:clear_glass')
  for side,z0,z1 in [('front',-281,-275),('rear',-210,-204)]:
   box=(c-6,-370,z0,c+6,-368,z1);sl=s.index(box);a=s.after[sl];mask=np.array([q.split('[')[0] in allowed or q.startswith('mtr:escalator_step') for q in s.palette])[a];a[mask]=s.state('projectseele:clear_glass')
   # These are stationary viewing bays; the flat travel lanes resume beyond
   # each bay. Whole two-block lanes are retired together.
   for x in range(c-6,c+7):
    for z in range(z0,z1+1):
     q=(x,-367,z);state=s.palette[s.after[-367-LO[1],z-LO[2],x-LO[0]]]
     if state.startswith('mtr:escalator_side'):s.fill((*q,*q),'minecraft:air')
   bays.append(dict(cage=c,side=side,glazed_floor=box))
 after=sightlines(s.after,s.palette);remaining=[r for r in after if r['first_obstruction']]
 count=s.delta(p,'r23/clear_glazed_observation_bays');p.meta.update(bays=bays,sightlines_before=before,sightlines_after=after,remaining_obstructions=remaining,changes=count,glass_retains_full_collision=True)
 p.apply('glazed_viewing_bays');(OUT/'report.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Viewing bays',len(bays),'clear rays',len(after)-len(remaining),'of',len(after),'remaining',remaining)
if __name__=='__main__':main()
