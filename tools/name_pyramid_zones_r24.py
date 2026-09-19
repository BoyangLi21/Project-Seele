"""Rename the 78 verified junction boards without changing their mounts or arrows."""
from pathlib import Path
import json,argparse,copy,nbtlib
import regional_voxels as v
from query_blocks import read_box,iter_block_entities
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R24_TV_REVIEW';OUT=ROOT/'artifacts/facility_r24/wayfinding_labels'
def zone(y):
    for height,name in [(-465,'总部车站层'),(-455,'交通接驳层'),(-440,'总部主环廊'),(-426,'作业联络层'),(-412,'技术联络层'),(-399,'指挥联络层'),(-384,'综合服务层')]:
        if y<=height:return name
    return '上层接待区'
def main(apply=False):
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();changes=[]
    boards=json.loads((ROOT/'artifacts/facility_r23/navigation_final/junctions.json').read_text(encoding='utf8'))['boards']
    tags=dict(iter_block_entities(WORLD,v.DIM,(-80,-475,230),(165,-350,480)))
    for board in boards:
        q=tuple(board['position']);tag=tags[q];state=read_box(WORLD,v.DIM,q,q)[q]
        assert str(tag['id'])=='projectseele:station_departure_board' and bool(tag['Wayfinding'])
        new=copy.deepcopy(tag);new['Station']=nbtlib.String('NERV 总部 · '+zone(board['site'][1]))
        if new==tag:continue
        p.update_block_entity(q,state,tag,new,'r24/human_readable_zone_names');changes.append(dict(position=q,before=str(tag['Station']),after=str(new['Station']),unchanged_rows=board['rows']))
    p.meta.update(renamed=changes,sign_mounts_preserved=True,route_arrows_preserved=True)
    p.save_plan('named_pyramid_junction_zones')
    if apply:p.apply('named_pyramid_junction_zones')
    (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Renamed verified junction boards:',len(changes))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
