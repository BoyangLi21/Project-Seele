"""Read the reported locations and preserve their current block/fixture evidence."""
from pathlib import Path
from collections import Counter
import json
from query_blocks import read_box,iter_block_entities,AIR
from regional_voxels import WORLD,ROOT,DIM

OUT=ROOT/'artifacts/world_rebuild_r20'
SITES={
 'road_collapse':[-676,96,676], 'dogma_lift_rider_loss':[14,-566,256],
 'pyramid_floating_gallery':[94,-441,252], 'old_central_gallery':[31,-418,250],
 'east_lower_gallery':[85,-448,287], 'arrival_lift':[127,-443,270],
 'retire_observation_lift':[87,-412,-15], 'restore_upper_observation':[91,-369,-61],
 'remove_wrong_transfer_detail':[48,-378,-49], 'hakone_airport_access':[-1671,72,-264],
 'out_of_service_R1':[-1320,104,669], 'out_of_service_S2':[-2867,70,-960]}

def main():
    out=OUT/'reported_sites';out.mkdir(parents=True,exist_ok=True);summary=[]
    for name,point in SITES.items():
        radius=(18,8,18) if 'road' in name or 'service' in name else (10,8,12)
        lo=tuple(a-b for a,b in zip(point,radius));hi=tuple(a+b for a,b in zip(point,radius));b=read_box(WORLD,DIM,lo,hi)
        record={'anchor':point,'bounds':[lo,hi],'states':dict(Counter(b.values())),'block_entities':[{'pos':p,'snbt':tag.snbt()} for p,tag in iter_block_entities(WORLD,DIM,lo,hi)],'cells':[[*p,s] for p,s in b.items() if s.split('[')[0] not in AIR]}
        (out/(name+'.json')).write_text(json.dumps(record,ensure_ascii=False),encoding='utf8')
        summary.append({'id':name,'anchor':point,'solid_cells':len(record['cells']),'fixtures':[{'pos':e['pos'],'id':e['snbt'][:100]} for e in record['block_entities']]})
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
