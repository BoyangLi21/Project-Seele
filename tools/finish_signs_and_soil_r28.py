"""Named public floor labels, native airport route diagrams and verified isolated soil."""
from pathlib import Path
import copy,gzip,json,nbtlib
import regional_voxels as v
from query_blocks import read_box,iter_block_entities,AIR
from signage_r28 import FLOORS
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_FIELD_R28_REVIEW';OUT=ROOT/'artifacts/facility_r28/finish'

def main():
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();walks=[]
    points=json.loads(gzip.decompress((OUT.parent/'global/components/isolated_soil_points.json.gz').read_bytes()));removed=0
    for row in points:
        q=tuple(row['pos']);old=read_box(WORLD,v.DIM,q,q).get(q)
        if old in AIR:continue
        assert old==row['state'];p.match((*q,*q),old,'minecraft:air','r28/verified_detached_natural_fragment');removed+=1
    native=json.loads((WORLD/'native_transit_r28.json').read_text());route=next(r for r in native['routes'] if r['routeNumber']=='S1');plats={q['id']:q for q in native['platforms']}
    def station(pid):
        q=plats[pid];c=[(q['position1'][k]+q['position2'][k])/2 for k in ('x','y','z')]
        return next(s['name'] for s in native['stations'] if all(min(s['position1'][k],s['position2'][k])<=value<=max(s['position1'][k],s['position2'][k]) for k,value in zip(('x','y','z'),c)))
    seq=[q['platformId'] for q in route['routePlatformData']];new=json.loads((OUT.parent/'airport/airport_native_receipt.json').read_text())['new_platforms']
    boards=[]
    for number,pid in enumerate(new):
        next_stop=station(seq[seq.index(pid)+1]);ordered=list(dict.fromkeys(station(k) for k in seq))
        if next_stop=='湾岸防卫区':ordered.reverse()
        track=plats[pid]['position1']['z'];heading='2 站台 · 往新箱根机场' if track==124 else '1 站台 · 往 NERV 港口'
        rows=['S1 '+heading,'下一站 '+next_stop]+[('● '+name+'  本站') if name=='NERV 航空基地' else '│ '+name for name in ordered]+['每分钟一班 · 中国时间','F2 航班：下至 1F 航站楼']
        # Ground maps are visible before taking the separate platform stairs.
        for q,reader in [((490,76,98+number*30),(493.5,73,98.5+number*30)),((542,107,105 if track==124 else 151),(542.5,105,108.5 if track==124 else 148.5))]:
            face='east' if q[0]==490 else 'south' if track==124 else 'north';state=f'projectseele:station_departure_board[facing={face},wayfinding=true]'
            old=read_box(WORLD,v.DIM,q,q)[q];assert old in AIR or old in ('projectseele:clear_glass','projectseele:nerv_structural_panel')
            backing=(q[0]-1,q[1],q[2]) if face=='east' else(q[0],q[1],q[2]-1 if face=='south' else q[2]+1)
            back=read_box(WORLD,v.DIM,backing,backing)[backing]
            if back in AIR:p.match((*backing,*backing),back,'projectseele:nerv_structural_panel','r28/route_map_fixed_support')
            p.match((*q,*q),old,state,'r28/airport_preboarding_route_map')
            p.block_entities[q]=nbtlib.Compound({'id':nbtlib.String('projectseele:station_departure_board'),'x':nbtlib.Int(q[0]),'y':nbtlib.Int(q[1]),'z':nbtlib.Int(q[2]),'Wayfinding':nbtlib.Byte(1),'NativePlatformId':nbtlib.Long(pid),'Route':nbtlib.String('S1 全线站序 / 乘车方向'),'Station':nbtlib.String('NERV 航空基地'),'PlatformCentre':nbtlib.Long(0),'MapRows':nbtlib.List[nbtlib.String]([nbtlib.String(s) for s in rows])})
            boards.append(dict(position=q,reader=reader,platform=pid));walks.append(dict(id='r28/airport/map/'+str(len(boards)),path=[list(reader),list(reader)],readingBoard=q,readingWayfinding=False))
    updated=0
    for q,old in iter_block_entities(WORLD,v.DIM,(-80,-474,230),(158,-355,475)):
        if str(old.get('id',''))!='projectseele:station_departure_board':continue
        tag=copy.deepcopy(old)
        for key in ('Station','Route','Row0','Row1','Row2'):
            text=str(tag.get(key,''))
            for y,name in FLOORS.items():
                text=text.replace('直梯 '+str(y)+' →','直梯 '+name+' →').replace(str(y)+' 层',name)
            if key in tag:tag[key]=nbtlib.String(text)
        if tag!=old:
            state=read_box(WORLD,v.DIM,q,q)[q];p.update_block_entity(q,state,old,tag,'r28/human_readable_floor_labels');updated+=1
    p.meta.update(soil_cells_removed=removed,named_floor_boards=updated,airport_maps=boards,walk_nodes=walks)
    p.apply('named_floor_diagrams_and_detached_soil')
    (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Finished soil',removed,'floor labels',updated,'airport maps',len(boards),flush=True)

if __name__=='__main__':main()
