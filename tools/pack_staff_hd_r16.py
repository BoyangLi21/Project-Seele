"""Pack the generated painted surfaces into exact Minecraft UV rectangles.

Image generation supplies the new illustration detail. This tool only performs
the technical face/island registration required by the game's fixed UV layout.
Derived Misato/Ritsuko artwork remains in the private local resource pack.
"""
from pathlib import Path
import json,shutil,hashlib
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/tv_facilities_r16';REF=OUT/'references';PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele/textures/entity';SCALE=4
FILES={'misato':'exec-c062e050-6468-4fff-b3f1-a86a7bb30b7b.png','ritsuko':'exec-da5eec3a-815a-45d0-9e3f-cb7b17d03dfa.png'}

def build(name):
 source=Path('C:/Users/liboy/.codex/generated_images/01a06f62-c70f-7b41-904c-d33fc1e86924')/FILES[name];shutil.copy2(source,REF/(name+'_generated_hd.png'));image=Image.open(source).convert('RGBA');assert image.size==(1254,1254)
 out=Image.new('RGBA',(256,256));records=[]
 def crop(box):return image.crop(box)
 def put(tile,dst,description):
  x,y,w,h=dst;tile=tile.convert('RGBA');tile.putalpha(255);out.paste(tile.resize((w*SCALE,h*SCALE),Image.Resampling.LANCZOS),(x*SCALE,y*SCALE));records.append(dict(uv=dst,source=description))
 def cube(u,v,w,h,d,faces,label):
  layout=[(u+d,v,w,d),(u+d+w,v,w,d),(u,v+d,d,h),(u+d,v+d,w,h),(u+d+w,v+d,d,h),(u+d+w+d,v+d,w,h)]
  for destination,face,surface in zip(layout,faces,['top','bottom','right','front','left','back']):
   tile=face if isinstance(face,Image.Image) else crop(face);put(tile,destination,dict(part=label,surface=surface,box=None if isinstance(face,Image.Image) else face))
 if name=='misato':
  cube(0,0,8,8,8,[(248,12,468,102),(454,428,541,478),(29,199,152,406),(156,198,414,406),(419,199,553,406),(558,199,712,406)],'head')
  cube(16,16,8,12,4,[(448,428,542,480),(392,744,597,786),(319,514,375,690),(389,503,598,780),(609,514,660,690),(810,506,1058,724)],'torso')
  for u,v in [(40,16),(32,48)]:
   cube(u,v,4,12,4,[(696,513,791,576),(707,691,787,720),(691,512,732,721),(1068,507,1126,721),(747,513,794,721),(691,512,798,721)],'sleeve')
  # The generated sheet paints skirt, bare leg and footwear as separate
  # surfaces; register them to both complete leg strips without resizing a face.
  leg=Image.new('RGBA',(80,240));leg.paste(crop((402,786,487,869)).resize((80,60)),(0,0));leg.paste(crop((401,881,489,941)).resize((80,100)),(0,60));leg.paste(crop((398,950,487,1011)).resize((80,80)),(0,160))
  for u,v in [(0,16),(16,48)]:cube(u,v,4,12,4,[(400,788,487,865),(393,965,487,1012),leg,leg,leg,leg],'leg')
 else:
  cube(0,0,8,8,8,[(165,5,305,145),(97,327,145,383),(7,161,150,311),(160,159,334,342),(338,160,468,312),(477,161,622,311)],'head')
  cube(16,16,8,12,4,[(409,325,532,383),(412,646,533,699),(319,397,386,622),(395,397,548,624),(553,397,624,623),(634,399,780,623)],'coat')
  for u,v in [(40,16),(32,48)]:cube(u,v,3,12,4,[(905,322,941,389),(801,610,879,624),(899,402,938,623),(799,400,887,624),(1027,401,1088,624),(803,709,936,853)],'slim_sleeve')
  for u,v in [(0,16),(16,48)]:cube(u,v,4,12,4,[(399,963,547,1010),(83,590,154,622),(8,401,75,622),(83,401,153,622),(163,401,231,622),(241,401,309,622)],'stockings')
 # Every base island is fully opaque. No generated checkerboard is permitted
 # in unused regions: only the exact registered rectangles enter the atlas.
 target=PACK/('staff_online_'+name+'.png');shutil.copy2(target,OUT/'skin_backup'/(name+'_network_before_hd.png'));out.save(target)
 preview=REF/(name+'_hd_packed.png');out.save(preview)
 return dict(name=name,source=str(source),target=str(target),resolution=[256,256],sha256=hashlib.sha256(target.read_bytes()).hexdigest(),original_downloaded_skin=64,enhancement='Built-in imagegen using the downloaded skin as reference; painted surfaces registered to the exact classic/slim UV islands',islands=records)

def main():
 rows=[build(name) for name in FILES];(OUT/'hd_skin_packing.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8');print([(r['name'],r['resolution'],r['sha256']) for r in rows])
if __name__=='__main__':main()
