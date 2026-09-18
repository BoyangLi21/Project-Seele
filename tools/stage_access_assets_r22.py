"""Private, reversible R22 assets; source skins remain byte-for-byte unchanged."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/access_r22'
PACK=ROOT/'run/resourcepacks/eva_access_r22_review'
def main():
 PACK.mkdir(parents=True,exist_ok=True)
 (PACK/'pack.mcmeta').write_text(json.dumps({'pack':{'pack_format':15,'description':'R22 private UN anatomy and pilot skins'}},ensure_ascii=False),encoding='utf8')
 report={'models':[],'skins':[]}
 for serial in (0,1):
  src=OUT/f'models/un0{serial}/runtime'
  for p in src.rglob('*'):
   if not p.is_file() or p.name=='pack.mcmeta':continue
   relative=p.relative_to(src)
   if serial:relative=Path(str(relative).replace('eva_prototype','eva_un01'))
   target=PACK/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
   if serial and target.name.endswith('.geo.json'):
    geometry=json.loads(target.read_text());geometry['minecraft:geometry'][0]['description']['identifier']='geometry.eva_un01';target.write_text(json.dumps(geometry,separators=(',',':')),encoding='utf8')
   report['models'].append({'serial':serial,'path':str(relative),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
 names={'shinji':'碇真嗣.png','rei':'Rei Ayanami.png','asuka':'Eva新世纪福音战士-惣流(式波)·明日香·兰格雷.png'}
 from PIL import Image
 for role,name in names.items():
  src=Path.home()/'Downloads'/name
  assert Image.open(src).size==(64,64)
  dst=PACK/f'assets/projectseele/textures/entity/training_pilot_{role}.png';dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
  report['skins'].append({'role':role,'source':str(src),'provenance':'existing user-local Minecraft skin, unchanged; private installation only','model':'slim','sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
 (OUT/'asset_stage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 print('R22 staged',len(report['models']),'model files and',len(report['skins']),'pilot skins')
if __name__=='__main__':main()
