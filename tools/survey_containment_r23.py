"""Cache actual factory volumes and measure liquid escaping registered wet cells."""
from pathlib import Path
import json
import numpy as np
from scipy.ndimage import label,find_objects
import scan_regional_completion as scan
import regional_voxels as v
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23/survey'
def main():
 OUT.mkdir(parents=True,exist_ok=True);scan.WORLD=WORLD;reports=[]
 for name,lo,hi in [('factory',(-60,-530,-305),(180,-330,25)),('pyramid',(-85,-485,231),(166,-350,475))]:
  a,pal=scan.volume(lo,hi);np.savez_compressed(OUT/(name+'.npz'),blocks=a,palette=pal,lo=lo,hi=hi)
  wet=np.array([s.startswith('projectseele:lcl') for s in pal])[a];components,n=label(wet);parts=[]
  for i,sl in enumerate(find_objects(components),1):
   if sl is None:continue
   ys,zs,xs=sl;mask=components[sl]==i;coords=np.argwhere(mask)+[ys.start,zs.start,xs.start];points=coords[:,[2,0,1]]+lo
   parts.append(dict(cells=int(mask.sum()),lo=points.min(0).tolist(),hi=points.max(0).tolist(),source_cells=int(sum(int(np.count_nonzero(a[sl][mask]==p)) for p,s in enumerate(pal) if s.startswith('projectseele:lcl') and 'level=0' in s))))
  reports.append(dict(region=name,lo=lo,hi=hi,liquid_cells=int(wet.sum()),liquid_components=parts,materials=len(pal)))
 (OUT/'liquid_components.json').write_text(json.dumps(reports,indent=2));print(json.dumps(reports,indent=2),flush=True)
if __name__=='__main__':main()
