"""One low-angle impact shot; actor motion, geometry, timing and roots stay exact."""
from pathlib import Path
import copy,hashlib,json
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'run/projectseele-local-maps/first_battle_r18.json';OUT=ROOT/'artifacts/facility_r24/camera'

def signature(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
    source=json.loads(SOURCE.read_text(encoding='utf8'));data=copy.deepcopy(source);fps=data['fps'];start,end=round(12.2*fps),round(16.1*fps)
    for i in range(start,end):
        t=(i-start)/(end-start-1);u=t*t*(3-2*t)
        data['camera']['position'][i]=[35-2*u,14+u,136-3*u]
        data['camera']['target'][i]=[1,18+.5*u,93+u]
    data['camera']['cuts']=sorted(set(data['camera'].get('cuts',[]))|{start,end})
    data['r24_camera']={'source':SOURCE.name,'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'changed_frames':[start,end-1],
                        'intent':'Low camera inside the measured battle road during grounded core strikes; explicit TV-style cuts at landing and recoil. No actor or combat timing edits.'}
    for role in ('eva','angel'):assert signature(data[role])==signature(source[role])
    OUT.mkdir(parents=True,exist_ok=True);target=OUT/'first_battle_r24_candidate.json';target.write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
    (OUT/'contract.json').write_text(json.dumps(dict(candidate=str(target),actor_roles_unchanged=True,changed_frames=[start,end-1],camera_local_x_range=[33,35],camera_local_y_range=[14,15],
                                                      camera_local_z_range=[133,136],canonical_world_road_inside=True,not_installed=True,revision='front-side view; rear candidate hid the core strikes behind the torso'),indent=2),encoding='utf8');print(target)
if __name__=='__main__':main()
