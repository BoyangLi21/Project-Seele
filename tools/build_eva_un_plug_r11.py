"""Generate a dedicated black-accent EVA-UN plug from the original local shell and model-space lettering."""
import json,hashlib
from pathlib import Path
from PIL import Image
import make_entry_plug_identification as marks
import make_entry_plug_model as shell
ROOT=marks.REPO;PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele';OUT=ROOT/'artifacts/world_motion_r11/un';OUT.mkdir(exist_ok=True)
def main():
 protected={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [PACK/'mesh'/f'entry_plug_unit{i:02d}.mesh.json' for i in range(3)]}
 mesh=json.loads((PACK/'mesh/entry_plug.mesh.json').read_text(encoding='utf8'));logo=Image.open(ROOT/'run/projectseele-local-maps/un_emblem.png').convert('RGBA');text,emblem=marks.identification_masks('EVAGELION-UN',logo)
 marks.MARK_Z_MIN=29.2;values=mesh['parts']['entry_plug']['vertices'];before=len(values);marks.append_mask_geometry(values,text,1);marks.append_mask_geometry(values,emblem,11)
 mesh['triangle_count']=mesh.get('triangle_count',0)+(len(values)-before)//24;mesh.setdefault('audit',{})['identification']='EVAGELION-UN / United Nations; attached shell geometry';(PACK/'mesh/entry_plug_un.mesh.json').write_text(json.dumps(mesh,separators=(',',':')),encoding='utf8')
 palette=list(shell.PALETTE)
 for i in [2,6,10]:palette[i]=(19,23,29,255)
 palette[11]=(27,34,41,255);shell.write_palette(PACK/'textures/entity/entry_plug_un.png',palette)
 for p,h in protected.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
 (OUT/'plug_manifest.json').write_text(json.dumps(dict(text='EVAGELION-UN',model=str(PACK/'mesh/entry_plug_un.mesh.json'),palette=palette,canonical_plugs_unchanged=protected),indent=2),encoding='utf8');print('EVA-UN plug generated; original three plugs unchanged')
if __name__=='__main__':main()
