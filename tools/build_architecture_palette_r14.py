"""Original industrial finish extending SEELE's existing block-panel system."""
from pathlib import Path
import json
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];RES=ROOT/'src/main/resources';ASSET=RES/'assets/projectseele'
def main():
 name='nerv_structural_panel'
 for face,base in [('side',(77,85,83)),('top',(88,95,91))]:
  im=Image.new('RGB',(64,64),base);d=ImageDraw.Draw(im)
  # Small edge rebates and a warm-grey painted centre, without stone mottling.
  d.rectangle((0,0,63,63),outline=(45,53,52));d.line((1,1,62,1),fill=tuple(v+12 for v in base));d.line((1,1,1,62),fill=tuple(v+7 for v in base))
  d.line((2,62,62,62),fill=tuple(v-12 for v in base));d.line((62,2,62,62),fill=tuple(v-10 for v in base))
  if face=='side':
   for x,y in [(5,5),(58,5),(5,58),(58,58)]:d.rectangle((x,y,x+1,y+1),fill=(58,65,62))
  im.save(ASSET/f'textures/block/{name}_{face}.png')
 (ASSET/f'blockstates/{name}.json').write_text(json.dumps({'variants':{'':{'model':'projectseele:block/'+name}}},indent=2)+'\n')
 (ASSET/f'models/item/{name}.json').write_text(json.dumps({'parent':'projectseele:block/'+name},indent=2)+'\n')
 (ASSET/f'models/block/{name}.json').write_text(json.dumps({'parent':'minecraft:block/cube_bottom_top','textures':{'side':'projectseele:block/'+name+'_side','top':'projectseele:block/'+name+'_top','bottom':'projectseele:block/'+name+'_top'}},indent=2)+'\n')
 for lang,label in [('en_us','NERV Structural Panel'),('zh_cn','NERV 涂装结构板')]:
  p=ASSET/f'lang/{lang}.json';data=json.loads(p.read_text(encoding='utf8'));data['block.projectseele.'+name]=label;p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 tag=RES/'data/projectseele/tags/blocks/structural_shell.json';tag.parent.mkdir(parents=True,exist_ok=True);tag.write_text(json.dumps({'replace':False,'values':['minecraft:reinforced_deepslate','projectseele:nerv_structural_panel']},indent=2)+'\n')
if __name__=='__main__':main()
