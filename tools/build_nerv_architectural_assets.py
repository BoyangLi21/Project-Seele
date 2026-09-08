"""Original vector-based modular finishes, with matching Minecraft PNG textures."""
from pathlib import Path
import json
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'src/main/resources/assets/projectseele'
SOURCE=ROOT/'tools/art/nerv_architecture';SOURCE.mkdir(parents=True,exist_ok=True)
SIZE=128
class Tile:
    def __init__(self,colour):
        self.image=Image.new('RGB',(SIZE,SIZE),colour);self.draw=ImageDraw.Draw(self.image)
        self.elements=[f'<rect width="128" height="128" fill="{colour}"/>']
    def rect(self,box,colour):
        x0,y0,x1,y1=box;self.draw.rectangle(box,fill=colour)
        self.elements.append(f'<rect x="{x0}" y="{y0}" width="{x1-x0+1}" height="{y1-y0+1}" fill="{colour}"/>')
    def polygon(self,points,colour):
        self.draw.polygon(points,fill=colour)
        self.elements.append(f'<polygon points="'+ ' '.join(f'{x},{y}' for x,y in points)+f'" fill="{colour}"/>')
    def save(self,name):
        (SOURCE/(name+'.svg')).write_text('<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">'+''.join(self.elements)+'</svg>\n')
        self.image.save(ASSETS/f'textures/block/{name}.png')

def wall():
    t=Tile('#99a3af');t.rect((0,0,1,127),'#62717f');t.rect((2,0,3,127),'#b8c0c8')
    t.rect((126,0,127,127),'#788795');t.rect((0,126,127,127),'#7f8c98')
    return t
def floor():
    t=Tile('#bdbbb0');t.rect((0,0,127,1),'#85877f');t.rect((0,0,1,127),'#85877f')
    t.rect((2,2,127,3),'#d0cec3');t.rect((2,2,3,127),'#d0cec3');return t
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    (ASSETS/'textures/block').mkdir(parents=True,exist_ok=True)
    tiles={};tiles['nerv_wall_panel']=wall();t=wall();t.rect((0,74,127,87),'#6b2534');t.rect((0,73,127,73),'#893e49');tiles['nerv_wall_datum']=t
    tiles['nerv_floor_panel']=floor();t=floor();t.rect((3,3,124,124),'#d9b644')
    for x in range(-128,256,32):t.polygon([(x,4),(x+13,4),(x+133,123),(x+120,123)],'#3c4348')
    for box in [(0,0,127,3),(0,124,127,127),(0,0,3,127),(124,0,127,127)]:t.rect(box,'#737976')
    tiles['nerv_hazard_paving']=t
    t=Tile('#7b8793');t.rect((3,3,124,124),'#aab2b8');t.rect((9,42,118,86),'#53616e');t.rect((12,45,115,83),'#242f36')
    for y in (49,70):t.rect((16,y,111,y+8),'#eeeadd');t.rect((19,y+2,108,y+5),'#fffdf0')
    t.rect((13,46,16,82),'#909aa0');t.rect((111,46,114,82),'#909aa0');tiles['nerv_strip_light']=t
    for name,path in [('station_tactile_path',True),('station_tactile_warning',False)]:
        t=floor();left,right=(43,84) if path else (12,115);t.rect((left,0,right,127),'#d4af3e')
        if path:
            for x in range(left+6,right-3,10):t.rect((x,0,x+4,127),'#a98731');t.rect((x,0,x+1,127),'#edcd70')
        else:
            for x in range(left+8,right-4,16):
                for y in range(8,127,16):
                    t.rect((x-3,y-2,x+3,y+4),'#a98731');t.rect((x-3,y-3,x+1,y+1),'#edcd70')
        tiles[name]=t
    labels={
        'nerv_wall_panel':('NERV Painted Wall Panel','NERV 灰蓝墙板'),
        'nerv_wall_datum':('NERV Datum Wall Panel','NERV 红线墙板'),
        'nerv_floor_panel':('NERV Floor Panel','NERV 浅色地板'),
        'nerv_hazard_paving':('NERV Threshold Marking','NERV 门槛警戒铺装'),
        'nerv_strip_light':('NERV Recessed Strip Light','NERV 嵌入式灯具'),
        'station_tactile_path':('Station Tactile Guide','车站导向盲道'),
        'station_tactile_warning':('Station Tactile Warning','车站警示盲道')}
    for name,tile in tiles.items():
        tile.save(name)
        if name.startswith('nerv_wall'):model={'parent':'minecraft:block/cube_all','textures':{'all':'projectseele:block/'+name}}
        else:
            model={'parent':'minecraft:block/cube_bottom_top','textures':{'side':'projectseele:block/nerv_floor_panel','bottom':'projectseele:block/nerv_floor_panel','top':'projectseele:block/'+name}}
            if name=='nerv_strip_light':model['textures'].update(top='projectseele:block/nerv_wall_panel',bottom='projectseele:block/'+name);model['ambientocclusion']=False
        write(ASSETS/f'models/block/{name}.json',model)
        variants={f'facing={f}':{'model':'projectseele:block/'+name,'y':angle} for f,angle in [('north',0),('east',90),('south',180),('west',270)]} if name=='station_tactile_path' else {'':{'model':'projectseele:block/'+name}}
        write(ASSETS/f'blockstates/{name}.json',{'variants':variants});write(ASSETS/f'models/item/{name}.json',{'parent':'projectseele:block/'+name})
        write(ROOT/f'src/main/resources/data/projectseele/loot_tables/blocks/{name}.json',{'type':'minecraft:block','pools':[{'rolls':1,'entries':[{'type':'minecraft:item','name':'projectseele:'+name}],'conditions':[{'condition':'minecraft:survives_explosion'}]}]})
    for language,index in [('en_us',0),('zh_cn',1)]:
        path=ASSETS/f'lang/{language}.json';data=json.loads(path.read_text(encoding='utf-8'))
        data.update({'block.projectseele.'+n:value[index] for n,value in labels.items()});write(path,data)
    path=ROOT/'src/main/resources/data/minecraft/tags/blocks/mineable/pickaxe.json'
    data=json.loads(path.read_text()) if path.exists() else {'replace':False,'values':[]}
    data['values']=list(dict.fromkeys(data['values']+['projectseele:'+n for n in tiles]));write(path,data)
    print('Original architectural finishes:',len(tiles),'PNG + SVG + block models')

if __name__=='__main__':main()
