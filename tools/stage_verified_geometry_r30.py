"""Compose only verified voxel receipts into the offline R30 output world.

No block/actor state is read from the live test session. Each receipt contributes
its measured before/after states; player, entity and transport data are preserved.
"""
from pathlib import Path
from collections import defaultdict
import argparse,hashlib,json
import nbtlib
import numpy as np
import regional_voxels as v
from query_blocks import iter_selected_sections,iter_block_entities,AIR

ROOT=v.ROOT;ART=ROOT/'artifacts/facility_r30';WORLD=ROOT/'run/saves/SEELE_R30_WORLD';REVIEW=ROOT/'run/saves/SEELE_FIELD_R30_REVIEW';OUT=ART/'geometry_stage'
ROOTS=['lighting','un_intake','public_edges','nerv_transport','retired_cage_lip','airport_lights','un_intake_ports','mission_alert',
       'lighting_refinement','board_mounts','global_repairs','retired_pier_terrain','city_edge_grading','terminal_detail']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def protected():
    result={'level.dat':digest(WORLD/'level.dat')}
    for part in ['playerdata','data','dimensions/projectseele/geofront/entities','dimensions/projectseele/geofront/data','mtr']:
        for p in (WORLD/part).rglob('*'):
            if p.is_file():result[p.relative_to(WORLD).as_posix()]=digest(p)
    return result
def main(apply):
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT
    baseline=json.loads((ART/'baseline.json').read_text())
    for name,sha in baseline['original_user_files'].items():assert digest(ROOT/name)==sha,('Protected user file changed',name)
    staged_path=OUT/'staged.json';staged=json.loads(staged_path.read_text()) if staged_path.exists() else {}
    if staged and 'source_receipts' not in staged:
        staged['source_receipts']=json.loads((OUT/'verified_geometry_stage/places.json').read_text())['source_receipts']
        staged_path.write_text(json.dumps(staged,indent=2))
    completed=set(staged.get('source_receipts',[]))
    receipts=sorted([p for name in ROOTS for p in (ART/name).glob('*/applied_*') if not (p/'ROLLED_BACK.json').exists()
                     and str(p.relative_to(ROOT)) not in completed],key=lambda p:p.name)
    delta={};sources=[];new_entities={}
    for p in receipts:
        receipt=json.loads((p/'receipt.json').read_text());assert receipt['verified'] and Path(receipt['world']).resolve()==REVIEW.resolve(),p;sources.append(str(p.relative_to(ROOT)))
        assert not (p/'block_entity_deltas.json').exists() or not json.loads((p/'block_entity_deltas.json').read_text()),'Add explicit NBT composition before using new NBT receipts'
        local=set()
        for f in (p/'delta').glob('c.*.npz'):
            cx,cz=map(int,f.stem.split('.')[1:])
            with np.load(f) as a:
                minimum=int(a['minimum']);palette=a['palette'].tolist()
                for n,old,new in zip(a['offsets'],a['before'],a['after']):
                    y=minimum+int(n)//256;x=cx*16+(int(n)&15);z=cz*16+((int(n)>>4)&15);q=x,y,z;before=palette[old];after=palette[new]
                    local.add(q)
                    if q in delta:
                        assert delta[q][1]==before,('Noncontiguous receipt history',q,delta[q],before,p);delta[q]=(delta[q][0],after)
                    else:delta[q]=(before,after)
        entities=p.parent/'block_entities.json'
        for e in json.loads(entities.read_text()) if entities.exists() else []:
            q=tuple(e['pos'])
            if q not in local:continue
            assert delta[q][0] in AIR,('Only measured new block entities are supported here',q,delta[q])
            new_entities[q]=nbtlib.parse_nbt(e['snbt'])
    selected=defaultdict(set);lookup=defaultdict(list)
    for q in delta:
        x,y,z=q;selected[x//16,z//16].add(y//16);lookup[x//16,z//16,y//16].append(q)
    current={}
    for cx,cz,sy,pal,indices in iter_selected_sections(WORLD,v.DIM,selected,skip_unfinished=True):
        for q in lookup.get((cx,cz,sy),[]):
            x,y,z=q;current[q]=pal[indices[(y-sy*16)*256+(z&15)*16+(x&15)]]
    conflicts=[];changes=[]
    for q,(old,new) in delta.items():
        at=current.get(q,'UNKNOWN')
        if at==new:continue
        if at!=old:conflicts.append({'pos':q,'expected':old,'current':at,'proposed':new})
        else:changes.append((q,old,new))
    (OUT/'conflicts.json').write_text(json.dumps(conflicts,ensure_ascii=False,indent=2));assert not conflicts,conflicts[:10]
    entity_before={}
    if new_entities:
        lo=tuple(min(q[i] for q in new_entities) for i in range(3));hi=tuple(max(q[i] for q in new_entities) for i in range(3))
        entity_before=dict(iter_block_entities(WORLD,v.DIM,lo,hi,selected_chunks={(q[0]//16,q[2]//16) for q in new_entities}))
        for q,tag in new_entities.items():
            actual=entity_before.get(q)
            assert actual is None or actual==tag,('Unexpected existing block entity',q)
    p=v.Painter();changes.sort(key=lambda item:(item[0][1],item[0][2],item[0][0]));i=0
    while i<len(changes):
        q,old,new=changes[i];x,y,z=q;j=i+1
        while j<len(changes) and changes[j][0]==(x+j-i,y,z) and changes[j][1:]==(old,new):j+=1
        p.match((x,y,z,x+j-i-1,y,z),old,new,'r30/verified_geometry_stage');i=j
    changing={q for q,_,_ in changes}
    for q,tag in new_entities.items():
        if q in changing:p.block_entities[q]=tag
        elif entity_before.get(q)!=tag:p.update_block_entity(q,delta[q][1],entity_before.get(q),tag,'r30/verified_new_fixture_nbt')
    p.meta.update(unique_receipt_cells=len(delta),changed_cells=len(changes),source_receipts=sources,new_fixture_tags=len(new_entities),scope='Verified geometry only. No native review actors, MTR, player or campaign state. This is not final delivery.')
    p.save_plan('verified_geometry_stage');print('R30 geometry preflight',len(changes),'changed;',len(delta),'receipt cells;',len(receipts),'receipts',flush=True)
    if not apply:return
    before=protected();result=p.apply('verified_geometry_stage');assert result['counts']['cells']==len(changes)
    if new_entities:
        readback=dict(iter_block_entities(WORLD,v.DIM,lo,hi,selected_chunks={(q[0]//16,q[2]//16) for q in new_entities}))
        assert all(readback.get(q)==tag for q,tag in new_entities.items()),'New fixture NBT readback failed'
    for name in ['facility_lighting_r30.json','nerv_transport_r30.json','mission_alert_r30.json']:
        (WORLD/name).write_bytes((REVIEW/name).read_bytes())
    routes={c['id']:c for c in json.loads((WORLD/'quality_walk_cases.json').read_text())}
    for c in json.loads((ART/'full_walk_cases.json').read_text()):routes[c['id']]=c
    for c in json.loads((ART/'un_intake_ports/intake_pedestrian_ports/places.json').read_text())['walk_nodes']:routes[c['id']]=c
    (WORLD/'quality_walk_cases.json').write_text(json.dumps(list(routes.values()),ensure_ascii=False,indent=2),encoding='utf8')
    (WORLD/'regional_states.json').write_bytes((REVIEW/'regional_states.json').read_bytes())
    assert protected()==before,'Protected runtime state changed'
    staged_path.write_text(json.dumps({'geometry_staged':True,'final_delivery':False,'changed_cells':len(changes),'source_receipts':sorted(completed|set(sources)),'protected_runtime_hashes':before,'routes':len(routes)},indent=2))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
