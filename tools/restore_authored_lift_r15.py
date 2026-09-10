"""Restore only the unintended cage normalization from the exact cold pre-paint snapshot."""
import argparse,shutil,json
import regional_voxels as vox
from query_blocks import read_box,iter_block_entities
from refine_staff_facilities_r15 import MATERIALS
ROOT=vox.ROOT;OUT=ROOT/'artifacts/staff_world_r15';SOURCE=OUT/'lift_before_source';LO=(10,-449,251);HI=(14,-415,257)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args()
 folder=SOURCE/'dimensions/projectseele/geofront/region';folder.mkdir(parents=True,exist_ok=True)
 src=OUT/'map/interiors/applied_20260911_013913/before/r.0.0.mca';dst=folder/src.name
 if not dst.exists():shutil.copy2(src,dst)
 old=read_box(SOURCE,vox.DIM,LO,HI);now=read_box(vox.WORLD,vox.DIM,LO,HI);entities=dict(iter_block_entities(SOURCE,vox.DIM,LO,HI));p=vox.Painter();count=0
 for pos,state in old.items():
  name=state.split('[')[0];wanted=MATERIALS.get(name,state)
  if now[pos]==wanted:continue
  assert pos[1] in range(-449,-443) or pos[1] in range(-420,-414),('Unexpected non-cage difference',pos)
  p.match((*pos,*pos),now[pos],wanted,'r15/restore_authored_cage');count+=1
  if pos in entities:p.block_entities[pos]=entities[pos]
 p.meta.update(cold_source=str(src),restored_cells=count,restored_block_entities=len(p.block_entities),scope='Only the two affected command-lift stop volumes; retain the authored car and its native selector NBT')
 assert count in (0,224),count;vox.OUT=OUT/'map';p.apply('authored_lift_restore') if args.apply else p.save_plan('authored_lift_restore')
if __name__=='__main__':main()
