"""Replace eight shop display boxes with supported, period enamel storefront plates."""
from pathlib import Path
import json,nbtlib
import regional_voxels as v
from query_blocks import read_box,iter_block_entities,AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R24_TV_REVIEW';OUT=ROOT/'artifacts/facility_r24/shop_signs'
def main():
    OUT.mkdir(parents=True,exist_ok=True);v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();rows=[]
    data=json.loads((ROOT/'artifacts/facility_r24/shops/contract.json').read_text(encoding='utf8'))
    for shop in data['shops']:
        lo=tuple(shop['box'][:3]);hi=tuple(shop['box'][3:]);blocks=read_box(WORLD,v.DIM,lo,hi)
        for old,tag in iter_block_entities(WORLD,v.DIM,lo,hi):
            if str(tag['id'])!='projectseele:station_departure_board':continue
            new=(old[0],old[1]+1,old[2]);assert blocks[new] in AIR
            for dx in (-1,0,1):assert blocks[(new[0]+dx,new[1],new[2]-1)]=='minecraft:green_terracotta'
            p.match((*old,*old),blocks[old],'minecraft:air','r24/storefront_enamel_sign')
            p.match((*new,*new),blocks[new],'projectseele:period_fixture[facing=south,kind=shop_sign]','r24/storefront_enamel_sign')
            p.block_entities[new]=nbtlib.Compound({'id':nbtlib.String('projectseele:period_fixture'),'x':nbtlib.Int(new[0]),'y':nbtlib.Int(new[1]),'z':nbtlib.Int(new[2]),'Title':nbtlib.String(str(tag['Station'])),'Lines':nbtlib.List[nbtlib.String]([nbtlib.String(str(tag['Row0']))])})
            rows.append(dict(old=old,new=new,title=str(tag['Station']),support='three existing solid fascia cells'))
    p.meta.update(replaced=rows);p.apply('supported_shop_enamel_plates')
    (OUT/'contract.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Enamel signs:',len(rows))
if __name__=='__main__':main()
