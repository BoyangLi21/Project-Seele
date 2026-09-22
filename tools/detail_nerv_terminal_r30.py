"""Period terminal furnishings and real native flight displays, with public routes kept clear."""
import argparse,json,math
from pathlib import Path
import numpy as np
import nbtlib
from scipy.spatial import cKDTree
import regional_voxels as v
from query_blocks import read_box,AIR
from build_station_boards_r19 import packed

WORLD=v.ROOT/'run/saves/SEELE_FIELD_R30_REVIEW';OUT=v.ROOT/'artifacts/facility_r30/terminal_detail'
def main(apply):
    v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();before=read_box(WORLD,v.DIM,(364,72,38),(478,83,82));planned={};props=[];held=[];paths=[]
    for c in json.loads((WORLD/'quality_walk_cases.json').read_text()):
        route=c.get('path') or [c.get('start'),c.get('end')]
        if not all(q is not None for q in route):continue
        for a,b in zip(route,route[1:]):
            a,b=np.asarray(a),np.asarray(b)
            if min(a[0],b[0])>478 or max(a[0],b[0])<364 or min(a[2],b[2])>82 or max(a[2],b[2])<38:continue
            paths.extend(np.linspace(a,b,max(2,math.ceil(np.linalg.norm(a-b)/.4)+1)))
    tree=cKDTree(np.asarray(paths));fixture_tall={'public_phone':2,'newspaper_rack':1,'coffee_machine':1,'notice_board':1,'vending_machine':1}
    def put(q,s):
        old=before[q];assert old in AIR,(q,old);planned[q]=s
    def prop(x,z,kind,facing='north',title='',lines=()):
        q=(x,73,z);height=fixture_tall.get(kind,0)
        if tree.query([x+.5,73,z+.5])[0]<1.35 or any(before.get((x,y,z),'UNKNOWN') not in AIR for y in range(73,74+height)) or q in planned:
            held.append({'pos':q,'kind':kind});return
        if before[x,72,z].split('[')[0] not in ['projectseele:nerv_floor_panel','minecraft:gray_concrete']:return
        if kind=='seat':put(q,f'projectseele:station_seat[facing={facing}]')
        else:
            put(q,f'projectseele:period_fixture[facing={facing},kind={kind}]')
            for dy in range(1,height+1):put((x,73+dy,z),f'projectseele:period_fixture_part[offset={dy}]')
            p.block_entities[q]=nbtlib.Compound({'id':nbtlib.String('projectseele:period_fixture'),'x':nbtlib.Int(x),'y':nbtlib.Int(73),'z':nbtlib.Int(z),'Title':nbtlib.String(title or 'NERV 航空基地'),'Lines':nbtlib.List[nbtlib.String]([nbtlib.String(s) for s in lines])})
        props.append({'pos':q,'kind':kind,'facing':facing})
    for centre in [414,432,452]:
        for z,facing in [(55,'north'),(57,'south'),(67,'north'),(69,'south')]:
            for x in [centre-2,centre,centre+2]:prop(x,z,'seat',facing)
    for x in [452,454,456,458]:prop(x,78,'cafe_counter','north','候机区服务柜台')
    prop(460,78,'coffee_machine','north');prop(465,77,'vending_machine','west');prop(469,77,'vending_machine','west')
    prop(374,77,'public_phone','east','公用电话');prop(378,77,'newspaper_rack','east','报刊阅览')
    prop(466,44,'notice_board','south','乘机须知',['登机口位于北侧连廊','F2 前往联合国总部','请以实时航班屏为准'])
    for x,z in [(425,65),(443,65),(464,63)]:prop(x,z,'cafe_table');prop(x+1,z,'cafe_stool','west')
    for x,z,facing in [(420,77,'north'),(451,41,'south')]:
        q=(x,76,z);put(q,f'projectseele:station_departure_board[facing={facing},wayfinding=false]')
        for y in range(77,83):put((x,y,z),'minecraft:chain[axis=y,waterlogged=false]')
        p.block_entities[q]=nbtlib.Compound({'id':nbtlib.String('projectseele:station_departure_board'),'x':nbtlib.Int(x),'y':nbtlib.Int(76),'z':nbtlib.Int(z),'PlatformCentre':nbtlib.Long(packed((650,72,-10))),'NativePlatformId':nbtlib.Long(5148309000717330621),'Station':nbtlib.String('NERV 航空基地 · 北侧登机连廊'),'Route':nbtlib.String('F2 联合国总部'),'Wayfinding':nbtlib.Byte(0),'AirService':nbtlib.Byte(1),'Row0':nbtlib.String('正在读取真实航班时刻'),'Row1':nbtlib.String('请前往北侧登机连廊')})
    for q,s in planned.items():p.match((*q,*q),before[q],s,'r30/nerv_terminal_furnishings')
    p.meta.update(props=props,held=held,native_air_platform=5148309000717330621,walk_clearance=1.35,layout='Grouped steel terminal seats, a small service corner, period public phone, reading rack and real flight boards; north access and main aisles retained')
    p.save_plan('nerv_terminal_furnishings');print('Terminal furnishings',len(props),'held',len(held),flush=True)
    if apply:p.apply('nerv_terminal_furnishings')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
