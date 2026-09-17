"""Restore intact artist-drawn Minecraft skins and extend the native pixel-uniform source."""
from pathlib import Path
import datetime, json, shutil
import build_staff_skins_r15 as pixels

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele/textures/entity'

def main():
    backup=ROOT/'artifacts/world_repair_r19/staff_backup'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    for name in ('misato','ritsuko'):
        target=PACK/('staff_online_'+name+'.png');shutil.copy2(target,backup/target.name)
        source=ROOT/'artifacts/tv_facilities_r16/skin_backup'/(name+'_network_before_hd.png')
        shutil.copy2(source,target)
    target=ROOT/'src/main/resources/assets/projectseele/textures/entity/staff_fuyutsuki.png'
    shutil.copy2(target,backup/target.name)
    pixels.build('fuyutsuki',(90,105,83),(162,166,164),skin=(219,185,157),trousers=(39,47,40))
    (backup/'receipt.json').write_text(json.dumps({'misato_ritsuko':'Restore unchanged downloaded 64x64 Minecraft artist skins; remove the painted-photo enhancement','fuyutsuki':'Native procedural pixel-uniform source','mesh_details':'NervStaffAccessoryLayer adds animated physical hair and Misato pendant'},indent=2),encoding='utf8')
    print('Stylized skins installed. Previous atlases retained:',backup)

if __name__=='__main__':main()
