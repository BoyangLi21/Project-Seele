"""Read back all five real wet-cell volumes after native operation cycles."""
from pathlib import Path
import json,numpy as np
from scipy.ndimage import label
import scan_regional_completion as scan
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23/validation'
def main():
 scan.WORLD=WORLD;results=[]
 for name,lo,hi,cages in [('nerv',(-60,-530,-305),(180,-330,25),[(x,-442,-266,x+38,-399,-214) for x in (-31,11,53)]),('un',(6220,65,-6300),(6504,146,-6100),[(6266,77,-6226,6298,120,-6137),(6426,77,-6226,6458,120,-6137)])]:
  a,pal=scan.volume(lo,hi);fluid=np.array([s.startswith('projectseele:lcl[') for s in pal])[a];allowed=np.zeros_like(fluid)
  for x,y,z,X,Y,Z in cages:allowed[y-lo[1]:Y-lo[1]+1,z-lo[2]:Z-lo[2]+1,x-lo[0]:X-lo[0]+1]=True
  escaped=np.argwhere(fluid&~allowed);_,components=label(fluid);rows=[]
  for box in cages:
   x,y,z,X,Y,Z=box;rows.append(dict(bounds=box,fluid_cells=int(fluid[y-lo[1]:Y-lo[1]+1,z-lo[2]:Z-lo[2]+1,x-lo[0]:X-lo[0]+1].sum())))
  result=dict(region=name,wet_cells=rows,components=int(components),outside_count=len(escaped),outside_examples=(escaped[:30, [2,0,1]]+np.array(lo)).tolist(),passed=len(escaped)==0 and all(r['fluid_cells']>10000 for r in rows));results.append(result)
 report=dict(passed=all(r['passed'] for r in results),results=results);(OUT/'final_lcl_containment.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert report['passed']
if __name__=='__main__':main()
