"""Uniform facade materials and a retained legacy pane model; no imported texture files."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];A=ROOT/'src/main/resources/assets/projectseele'
def save(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
for name,texture in [('nerv_pyramid_panel','black_concrete'),('nerv_pyramid_marking','red_concrete')]:
    faces={d:dict(texture='#all',cullface=d) for d in ('north','south','east','west','up','down')}
    save(A/'models/block'/f'{name}.json',dict(ambientocclusion=False,textures=dict(all='minecraft:block/'+texture,particle='minecraft:block/'+texture),elements=[dict(**{'from':[0,0,0],'to':[16,16,16]},shade=False,faces=faces)]))
    save(A/'models/item'/f'{name}.json',dict(parent='projectseele:block/'+name))
    save(A/'blockstates'/f'{name}.json',dict(variants={'':dict(model='projectseele:block/'+name)}))
save(A/'models/block/one_way_glass.json',dict(ambientocclusion=False,render_type='cutout',textures=dict(outside='minecraft:block/polished_blackstone',particle='minecraft:block/polished_blackstone'),elements=[dict(**{'from':[0,0,0],'to':[16,16,16]},faces=dict(north=dict(texture='#outside',cullface='north')))]))
obsolete=A/'models/block/one_way_glass_corner.json'
if obsolete.exists():obsolete.unlink()
variants={}
for facing,rotation in [('north',0),('east',90),('south',180),('west',270)]:
    for pyramid in (False,True):variants[f'facing={facing},pyramid={str(pyramid).lower()}']=dict(model='projectseele:block/'+('nerv_pyramid_panel' if pyramid else 'one_way_glass'),**({'y':rotation} if rotation else {}))
save(A/'blockstates/one_way_glass.json',dict(variants=variants))
for language,labels in [('zh_cn',('NERV 金字塔深色饰面','NERV 金字塔标识饰面')),('en_us',('NERV Pyramid Facade','NERV Pyramid Marking'))]:
    path=A/'lang'/f'{language}.json';data=json.loads(path.read_text(encoding='utf8'))
    for key,label in zip(('nerv_pyramid_panel','nerv_pyramid_marking'),labels):data['block.projectseele.'+key]=label
    save(path,data)
