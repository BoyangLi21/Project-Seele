"""Slim bracket and downward LED enclosure based on Tokyo roadway fixtures."""
import json
from build_furniture_r19 import ROOT, box

def main():
    name='street_light_head'
    elements=[box([7,0,7],[9,14,9],'metal'),box([7,11,-4],[9,13,9],'metal'),
              box([4,8,-12],[12,11,2],'shell'),box([5,7.75,-10],[11,8,0],'lamp'),
              box([5,11,-10],[11,11.6,1],'metal')]
    model={'parent':'minecraft:block/block','textures':{'metal':'minecraft:block/gray_concrete','shell':'minecraft:block/light_gray_concrete','lamp':'minecraft:block/sea_lantern','particle':'minecraft:block/gray_concrete'},'elements':elements}
    for rel,data in [(f'models/block/{name}.json',model),(f'models/item/{name}.json',{'parent':'projectseele:block/'+name}),
        (f'blockstates/{name}.json',{'variants':{f'facing={d}':dict(model='projectseele:block/'+name,**({'y':a} if a else {})) for d,a in [('north',0),('east',90),('south',180),('west',270)]}})]:
        (ROOT/rel).write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
    for lang,label in [('zh_cn','道路 LED 灯头'),('en_us','Roadway LED luminaire')]:
        p=ROOT/'lang'/f'{lang}.json';d=json.loads(p.read_text(encoding='utf8'));d['block.projectseele.'+name]=label;p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
