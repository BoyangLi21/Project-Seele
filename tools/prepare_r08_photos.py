"""A fixed native screenshot itinerary, including full restoration of the wet prototype bay."""
import json,math,shutil,msvcrt
from regional_voxels import ROOT,WORLD
OUT=ROOT/'artifacts/world_refinement_r08';photos=[]
def shot(name,pos,target,warmup=300,action=''):
    dx,dy,dz=target[0]-pos[0],target[1]-pos[1]-1.62,target[2]-pos[2]
    photos.append(dict(file='r08_'+name+'.png',position=pos,yaw=math.degrees(math.atan2(-dx,dz)),pitch=math.degrees(math.atan2(-dy,math.hypot(dx,dz))),warmupTicks=warmup,**({'action':action} if action else {})))
shot('harbor_overview',[1558.5,123,498.5],[1408,74,442],540)
shot('historic_destroyer',[1410.5,78,440.5],[1450,77,479],360)
shot('quay_cranes',[1381.5,76,450.5],[1418,85,375],360)
shot('port_warehouse',[1272.5,69,388.5],[1272,71,345])
shot('base_overview',[6750.5,145,-6450.5],[6480,95,-6360],540)
shot('tank_workshop',[6643.5,78,-6348.5],[6634,77,-6361],360)
shot('fighter_shelter',[6650.5,79,-6532.5],[6640,79,-6570],360)
shot('kv16_shelter',[6652.5,79,-6180.5],[6640,79,-6220],360)
shot('operations',[6432.5,75.1,-6565.5],[6432,77,-6609])
shot('briefing_room',[6422.5,75.1,-6552.5],[6405,77,-6579])
shot('prototype_full',[6442.5,108,-6112.5],[6442.5,106,-6205.5],400,'open')
shot('prototype_armor',[6453.5,124,-6172.5],[6442.5,127,-6205.5],320)
shot('prototype_threequarter',[6455.5,105,-6146.5],[6442.5,106,-6205.5],320)
shot('surface_hangar_roof',[6548.5,192,-6070.5],[6442,130,-6205],360)
shot('main_hangar_roof',[168.5,-303,-193.5],[30,-350,-100],420)
shot('black_launch_shafts',[220.5,-184,-250.5],[30,-203,-40],420)
shot('pyramid_exterior',[211.5,-317,510.5],[30,-380,327],420)
shot('terminal_dogma',[30.5,-566,295.5],[30.5,-568,355.5],360)
shot('prototype_wet_restored',[6442.5,108,-6112.5],[6442.5,106,-6205.5],320,'wet')
if __name__=='__main__':
    lock=(WORLD/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    old=OUT/'r07_photo_views_before.json'
    if not old.exists():shutil.copy2(WORLD/'r07_photo_views.json',old)
    for path in (WORLD/'r07_photo_views.json',OUT/'photo_views.json'):path.write_text(json.dumps(photos,ensure_ascii=False,indent=2),encoding='utf8')
    print('Native photos',len(photos))
