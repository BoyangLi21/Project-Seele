"""Keep reachable compact corridor signs above the player's full height."""
from pathlib import Path
import copy,gzip,json,nbtlib
import regional_voxels as v
from query_blocks import read_box,iter_block_entities,AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R25_REVIEW';OUT=ROOT/'artifacts/facility_r25/sign_clearance'
def main():
 OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter()
 with gzip.open(WORLD/'nerv_routes_r24.json.gz','rt',encoding='utf8') as stream:nodes={tuple(q[:3]) for q in json.load(stream)['nodes']}
 moved=[];held=[]
 for q,tag in iter_block_entities(WORLD,v.DIM,(-80,-574,-300),(190,-334,545)):
  state=read_box(WORLD,v.DIM,q,q)[q]
  if not state.startswith('projectseele:nerv_direction_panel') or (q[0],q[1]-1,q[2]) not in nodes:continue
  new=(q[0],q[1]+1,q[2]);upper=read_box(WORLD,v.DIM,new,new).get(new,'UNKNOWN')
  if upper not in AIR:held.append(dict(position=q,above=upper));continue
  changed=copy.deepcopy(tag);changed['y']=nbtlib.Int(new[1]);p.match((*q,*q),state,'minecraft:air','r25/clear_two_metre_corridor_headroom');p.match((*new,*new),upper,state,'r25/high_wall_wayfinding');p.block_entities[new]=changed;moved.append(dict(before=q,after=new))
 p.meta.update(moved=moved,unchanged_no_upper_space=held,minimum_new_bottom_above_feet=2.125);p.apply('compact_signs_above_headroom')
 (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Raised compact corridor boards',len(moved),'retained',len(held))
if __name__=='__main__':main()
