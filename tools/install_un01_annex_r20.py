"""Activate the completed empty bay and add its independent staff stations."""
from pathlib import Path
import argparse,json,copy,shutil,msvcrt
import regional_voxels as v
from query_blocks import read_box
OUT=v.ROOT/'artifacts/world_rebuild_r20/un01_hangar'
def main(world):
    world=Path(world);marker=world/'un01_annex_r20.json'
    if marker.exists():print('UN-01 annex already activated',world.name);return
    with (world/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        for pos in [(6282,76,-6205),(6270,76,-6120)]:assert read_box(world,v.DIM,pos,pos)[pos]=='projectseele:nerv_floor_panel'
        config=json.loads((OUT/'facility.json').read_text());config['installed']=True;config['spawn_airframe']=False
        path=world/'nerv_staff_r15.json';data=json.loads(path.read_text(encoding='utf8'));backup=OUT/('staff_before_'+world.name+'.json');assert not backup.exists();shutil.copy2(path,backup)
        oldids={q['id'] for q in data['stations']};staff=[]
        for row in data['stations']:
            x,y,z=row['feet']
            if 6384<=x<=6500 and -6288<=z<=-6136:
                q=copy.deepcopy(row);q['id']='r20/un01/'+str(len(staff));q['feet'][0]-=160;q['name']='UN-01 · '+q['name'];staff.append(q)
        assert len(staff)==7 and not oldids&{q['id'] for q in staff};data['stations'].extend(staff);path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');marker.write_text(json.dumps(config,indent=2));(OUT/('activated_'+world.name+'.json')).write_text(json.dumps(dict(world=str(world),airframe_spawned=False,new_staff=staff,old_staff_ids_preserved=True),ensure_ascii=False,indent=2),encoding='utf8')
    print('Independent empty UN-01 bay activated',world.name)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--world',default=str(v.WORLD));main(a.parse_args().world)
