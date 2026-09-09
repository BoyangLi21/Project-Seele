"""Retake the changed sites, close vehicle details, and the floodlit prototype."""
import json,msvcrt
import prepare_r08_photos as m
m.photos=[]
m.shot('harbor_overview',[1558.5,123,498.5],[1408,74,442],480)
m.shot('historic_destroyer',[1410.5,78,440.5],[1450,77,479],340)
m.shot('quay_cranes',[1381.5,76,450.5],[1418,85,375],340)
m.shot('tank_workshop',[6643.5,78,-6348.5],[6634,77,-6361],340)
m.shot('fighter_shelter',[6650.5,79,-6532.5],[6640,79,-6570],340)
m.shot('fighter_close',[6649.5,77,-6552.5],[6640,77,-6570],320)
m.shot('kv16_close',[6650.5,77,-6200.5],[6640,77,-6220],320)
m.shot('operations',[6448.5,75.5,-6590.5],[6432,77,-6612],320)
m.shot('prototype_full',[6442.5,108,-6112.5],[6442.5,106,-6205.5],360,'open')
m.shot('prototype_cull_check',[6453.5,124,-6172.5],[6442.5,127,-6205.5],280)
m.shot('prototype_armor',[6452.5,115,-6162.5],[6442.5,116,-6205.5],320)
m.shot('prototype_threequarter',[6455.5,105,-6146.5],[6442.5,106,-6205.5],320)
m.shot('pyramid_exterior',[211.5,-317,510.5],[30,-380,327],380)
m.shot('prototype_wet_restored',[6442.5,108,-6112.5],[6442.5,106,-6205.5],320,'wet')
if __name__=='__main__':
    lock=(m.WORLD/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    for path in (m.WORLD/'r07_photo_views.json',m.OUT/'photo_views_final.json'):path.write_text(json.dumps(m.photos,indent=2),encoding='utf8')
    print('Final native views',len(m.photos))
