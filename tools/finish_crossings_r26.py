"""Keep the original upper stairs clear and put the U1 diagram on the reader side."""
from pathlib import Path
import copy,json
import nbtlib
import regional_voxels as v,scan_regional_completion as scan,plan_factory_r20 as f,repair_facility_r21 as h
from query_blocks import read_box,iter_block_entities,AIR
ROOT=v.ROOT;ART=ROOT/'artifacts/facility_r26';WORLD=ROOT/'run/saves/SEELE_R26_REVIEW';OUT=ART/'crossing_finish'

def main():
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=scan.WORLD=WORLD;v.OUT=OUT;p=v.Painter()
    cold=Path(json.loads((ART/'baseline.json').read_text())['backup'])/'world';paths=[]
    for y in (-378,-364):
        h.LO=f.LO=(53,y-2,303);h.HI=f.HI=(70,y+5,368);s=h.Facility()
        lo=(64,y-2,312);hi=(68,y+4,365)
        assert not list(iter_block_entities(WORLD,v.DIM,lo,hi))
        for q,state in read_box(cold,v.DIM,lo,hi).items():s.fill((*q,*q),state)
        s.hall('upper_lift_bypass_'+str(y),[(64,68,305,311),(54,68,307,311),(54,58,307,365)],y-1,5,
               [(65,y,305,67,y+2,306),(55,y,365,57,y+2,365)])
        s.delta(p,'r26/upper_lift_corridor_clear_of_original_stairs')
        path=[[66.5,y,308.5],[66.5,y,309.5],[56.5,y,309.5],[56.5,y,367.5],[66.5,y,367.5]]
        paths += [dict(id='r26/core_lift/'+str(y),path=path),dict(id='r26/core_lift/'+str(y)+'/return',path=path[::-1])]
    a=(-330,-464,779);b=(-332,-464,776);state=read_box(WORLD,v.DIM,a,a)[a];tag=copy.deepcopy(next(iter_block_entities(WORLD,v.DIM,a,a))[1]);tag['x']=nbtlib.Int(b[0]);tag['z']=nbtlib.Int(b[2])
    assert all(s.split('[')[0] in AIR for s in read_box(WORLD,v.DIM,(b[0]-1,b[1],b[2]),(b[0]+1,b[1]+1,b[2])).values())
    p.match((*a,*a),state,'minecraft:air','r26/move_u1_diagram_before_glazing');p.match((*b,*b),'minecraft:air',state,'r26/move_u1_diagram_before_glazing');p.block_entities[b]=tag
    bars='minecraft:iron_bars[east=false,north=false,south=false,waterlogged=false,west=false]'
    for x in (-331,-329):
        for y in range(-462,-452):
            q=(x,y,779);old=read_box(WORLD,v.DIM,q,q)[q]
            if old!=bars:break
            assert read_box(cold,v.DIM,q,q)[q].split('[')[0] in AIR
            p.match((*q,*q),old,'minecraft:air','r26/retire_old_diagram_support')
    for x in (b[0]-1,b[0]+1):
        for y in range(-462,-452):
            q=(x,y,b[2]);old=read_box(WORLD,v.DIM,q,q)[q]
            if old.split('[')[0] not in AIR:break
            p.match((*q,*q),old,bars,'r26/diagram_ceiling_support')
        else:raise AssertionError('No ceiling above relocated diagram')
    p.meta.update(route_overrides=paths,moved_board=dict(before=a,after=b));p.apply('upper_stair_and_station_crossings')
    data=json.loads((ART/'signage/contract.json').read_text())
    row=next(q for q in data['created'] if q['position']==list(a));row['position']=list(b);row['reader']=[b[0],-466,b[2]-2]
    for q in data['walk_nodes']:
        if q['readingBoard']==list(a):q['readingBoard']=list(b);q['path']=[[row['reader'][0]+.5,row['reader'][1],row['reader'][2]+.5]]*2
    (ART/'signage/contract.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    core=json.loads((ART/'core_lift/contract.json').read_text());mapped={q['id']:q for q in paths};core['walk_nodes']=[mapped.get(q['id'],q) for q in core['walk_nodes']];(ART/'core_lift/contract.json').write_text(json.dumps(core,ensure_ascii=False,indent=2),encoding='utf8')
    details=json.loads((ART/'details/contract.json').read_text())
    for q in details['walk_nodes']:
        if 'shaft_observer_retained' in q['id']:
            path=[[103.5,-369,-70.5],[103.5,-369,-60.5],[98.5,-369,-60.5]];q['path']=path[::-1] if q['id'].endswith('/return') else path
    (ART/'details/contract.json').write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'contract.json').write_text(json.dumps(p.meta,indent=2),encoding='utf8')
if __name__=='__main__':main()
