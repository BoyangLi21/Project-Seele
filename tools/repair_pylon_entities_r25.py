"""Find every authored power socket and repair missing native block-entity records."""
from pathlib import Path
import json,nbtlib,numpy as np
import regional_voxels as v
from query_blocks import iter_matching_sections,read_box,iter_block_entities
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R25_REVIEW';OUT=ROOT/'artifacts/facility_r25/power_ports'
def main():
 OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();cache=OUT/'measured.json'
 if cache.exists():data=json.loads(cache.read_text());ports=data['ports'];stats=data['scan']
 else:
  ports=[];stats={}
  for cx,cz,sy,pal,a in iter_matching_sections(WORLD,v.DIM,['projectseele:umbilical_pylon'],stats):
   selected=np.array([s.startswith('projectseele:umbilical_pylon') for s in pal])[a]
   for raw in np.flatnonzero(selected):
    i=int(raw);ports.append([cx*16+(i&15),sy*16+(i>>8),cz*16+((i>>4)&15)])
  cache.write_text(json.dumps(dict(ports=ports,scan=stats),indent=2))
 repaired=[];kept=[]
 for point in ports:
  q=tuple(point);state=read_box(WORLD,v.DIM,q,q)[q];assert state.startswith('projectseele:umbilical_pylon')
  tags=list(iter_block_entities(WORLD,v.DIM,q,q))
  if tags:
   assert str(tags[0][1]['id'])=='projectseele:umbilical_pylon',('Wrong socket entity',q,tags[0][1].snbt());kept.append(q);continue
  tag=nbtlib.Compound({'id':nbtlib.String('projectseele:umbilical_pylon'),'x':nbtlib.Int(q[0]),'y':nbtlib.Int(q[1]),'z':nbtlib.Int(q[2])})
  p.update_block_entity(q,state,None,tag,'r25/register_existing_power_socket');repaired.append(q)
 p.meta.update(scan=stats,total_ports=len(ports),repaired=repaired,existing_preserved=kept);p.apply('native_power_socket_registration')
 (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Power sockets',len(ports),'missing native registrations repaired',len(repaired),flush=True)
if __name__=='__main__':main()
