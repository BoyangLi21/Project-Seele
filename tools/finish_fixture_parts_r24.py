"""Install exact upper collision/picking cells in the previously reserved model envelopes."""
from pathlib import Path
import json
import regional_voxels as v
from query_blocks import read_box,AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R24_TV_REVIEW';OUT=ROOT/'artifacts/facility_r24/fixture_parts'
def main():
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();bases=[];rows=[]
    for item in json.loads((ROOT/'artifacts/facility_r24/stations/contract.json').read_text(encoding='utf8'))['placed']:
        if item['kind'] in ('public_phone','notice_board'):bases.append((tuple(item['position']),item['kind']))
    for shop in json.loads((ROOT/'artifacts/facility_r24/shops/contract.json').read_text(encoding='utf8'))['shops']:
        lo=tuple(shop['box'][:3]);hi=tuple(shop['box'][3:]);blocks=read_box(WORLD,v.DIM,lo,hi)
        for q,state in blocks.items():
            for kind in ('newspaper_rack','coffee_machine'):
                if state.startswith('projectseele:period_fixture[') and f'kind={kind}' in state:bases.append((q,kind))
    for base,kind in bases:
        for offset in range(1,3 if kind=='public_phone' else 2):
            q=(base[0],base[1]+offset,base[2]);old=read_box(WORLD,v.DIM,q,q)[q];new=f'projectseele:period_fixture_part[offset={offset}]'
            if old==new:continue
            assert old in AIR|{'minecraft:light'},(q,old,'previously reserved fixture envelope was modified')
            p.match((*q,*q),old,new,'r24/tall_fixture_physical_upper_cells');rows.append(dict(base=base,part=q,kind=kind,offset=offset))
    p.meta.update(parts=rows,bases=len(bases));p.apply('native_fixture_upper_cells')
    (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Tall fixture native parts',len(rows),'bases',len(bases))
if __name__=='__main__':main()
