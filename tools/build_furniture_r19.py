"""Distinct passenger, apartment and UN workshop seats using native model geometry."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]/'src/main/resources/assets/projectseele'
FACES=('north','south','east','west','up','down')

def box(a,b,texture,rotation=None):
    # Model elements may extend beyond the owning 16-pixel block. Implicit UVs
    # would then sample unrelated tiles in Minecraft's texture atlas.
    e={'from':a,'to':b,'faces':{f:{'texture':'#'+texture,'uv':[0,0,16,16]} for f in FACES}}
    if rotation:e['rotation']=rotation
    return e

def seat(kind):
    e=[]
    if kind=='station_seat':
        # A moulded shell on a transverse station-bench beam. Seats remain
        # individually replaceable and their armrests do not enter the aisle.
        e += [box([0,5.5,7],[16,7,9],'metal')]
        for x in (4,11):
            e += [box([x,0,6],[x+1,6,10],'metal'),box([x-1,0,4],[x+2,.65,12],'metal')]
        e += [box([2.1,8,2],[13.9,9.1,12.8],'shell'),box([3,9.1,2.7],[13,9.7,11.9],'fabric'),
              box([2,9,12],[14,17.5,13.2],'shell',{'origin':[8,9,12],'axis':'x','angle':22.5}),
              box([3,9.6,11.85],[13,16.8,12.25],'fabric',{'origin':[8,9,12],'axis':'x','angle':22.5})]
        for x in (1.4,13.6):
            e += [box([x,8.5,3],[x+1,11.8,12.5],'shell'),box([x,11.8,4],[x+1,12.5,11.5],'metal')]
        textures={'shell':'minecraft:block/light_gray_concrete','fabric':'minecraft:block/blue_concrete','metal':'minecraft:block/gray_concrete'}
    elif kind=='residential_chair':
        for x in (3,12):
            for z in (3,12):e.append(box([x,0,z],[x+1,9,z+1],'metal'))
        e += [box([2,8.5,2],[14,10,14],'shell'),box([3,10,3],[13,10.6,12.5],'fabric'),
              box([2.5,11,12.5],[13.5,18,14],'shell',{'origin':[8,11,12.5],'axis':'x','angle':22.5})]
        for x in (3,12):e.append(box([x,9,12],[x+1,17,13],'metal'))
        textures={'shell':'minecraft:block/stripped_birch_log','fabric':'minecraft:block/light_gray_wool','metal':'minecraft:block/black_concrete'}
    else:
        for x in (2.8,12.2):
            e += [box([x,0,3],[x+1,10,4],'metal'),box([x,0,12],[x+1,17,13],'metal'),box([x,.5,3],[x+1,1.2,13],'metal')]
        e += [box([2.5,8.5,3],[13.5,10,13],'fabric'),box([3,11,12],[13,17,13.1],'fabric'),box([2.5,16.5,12],[13.5,17.3,13.5],'metal')]
        textures={'fabric':'minecraft:block/green_wool','metal':'minecraft:block/gray_concrete'}
    textures['particle']=textures['fabric']
    return {'parent':'minecraft:block/block','ambientocclusion':True,'textures':textures,'elements':e}

def main():
    names={'station_seat':('駅ホームの成形座席','站台模压座椅','Station moulded seat'),
           'residential_chair':('ダイニングチェア','住宅餐椅','Apartment dining chair'),
           'military_seat':('整備室チェア','UN 整备室座椅','UN workshop seat')}
    for name in names:
        for rel,data in [(f'models/block/{name}.json',seat(name)),(f'models/item/{name}.json',{'parent':'projectseele:block/'+name}),
                         (f'blockstates/{name}.json',{'variants':{f'facing={d}':dict(model='projectseele:block/'+name,**({'y':a} if a else {})) for d,a in [('north',0),('east',90),('south',180),('west',270)]}})]:
            (ROOT/rel).write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
    for language,index in [('zh_cn',1),('en_us',2)]:
        p=ROOT/'lang'/(language+'.json');d=json.loads(p.read_text(encoding='utf8'))
        for name,labels in names.items():d['block.projectseele.'+name]=labels[index]
        d['entity.projectseele.eva_prototype']='EVA-UN-00';d['hud.projectseele.role_experimental']='EVA-UN-00'
        p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Wrote three distinct seat models and identifiers.')

if __name__=='__main__':main()
