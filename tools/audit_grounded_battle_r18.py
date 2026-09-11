"""Independent rendered-surface/foot-contact audit for the private R18 candidate."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from scipy.spatial.transform import Rotation as R
import author_first_battle_r12 as a
from refine_grounded_battle_r18 import kneepad_floor,world

ROOT=a.ROOT;OUT=ROOT/'artifacts/grounded_battle_r18';U=a.UNIT

def main():
    ap=argparse.ArgumentParser();ap.add_argument('candidate',type=Path);args=ap.parse_args()
    raw=args.candidate.read_bytes();data=json.loads(raw);old=json.loads((ROOT/'run/projectseele-local-maps/first_battle_r15.json').read_text())
    poses=[a.eva.decode(f,data['eva']['bones']) for f in data['eva']['frames']];roots=np.array(data['eva']['root_blocks'])
    floors=[];knees=[];feet={s:[] for s in ('l','r')};rotations={n:[] for n in ('leg_l','leg_r','shin_l','shin_r','foot_l','foot_r')}
    for i in range(344,601):
        p=poses[i];r=roots[i]
        for n in rotations:rotations[n].append(R.from_matrix(p.matrix(n)[:3,:3]).as_quat())
        for fraction in (0,.5):
            q=p if fraction==0 else a.mix_pose(p,poses[i+1],fraction)
            root=r if fraction==0 else (r+roots[i+1])/2
            floor=a.surface.floor(q,['torso_lower','torso_upper','head','arm_l','arm_r','forearm_l','forearm_r','hand_l','hand_r','leg_l','leg_r','shin_l','shin_r','foot_l','foot_r'])*U+root[1]
            floors.append({'time':(i+fraction)/30,'floor':float(floor)})
        if 367<=i<=486:
            for s in ('l','r'):
                knees.append({'frame':i,'side':s,'pad_floor':kneepad_floor(p,r,s)})
                feet[s].append(world(p,r,'foot_'+s))
        if i%60==0:print('R18 exact surface audit',i,flush=True)
    continuity={}
    for n,qs in rotations.items():
        q=np.array(qs);step=np.degrees(2*np.arccos(np.clip(abs((q[1:]*q[:-1]).sum(1)),0,1)));i=int(step.argmax())
        continuity[n]={'max_world_step_degrees':float(step[i]),'frame':345+i}
    contacts={s:float(np.linalg.norm(np.asarray(v)-v[0],axis=1).max()) for s,v in feet.items()}
    # The brace and three strikes end at 16.05 s. Subsequent hands withdraw
    # with the torso and must no longer be treated as fixed world contacts.
    scene=np.zeros((691,3));scene[:,2]=data.get('r18_scene_offsets',{}).get('eva',[0]*691)
    hands={s:float(np.linalg.norm((np.asarray(data['eva']['hand_'+s+'_blocks'])-scene)[366:482]-np.asarray(old['eva']['hand_'+s+'_blocks'])[366:482],axis=1).max()) for s in ('l','r')}
    hip=np.array([(world(p,r,'leg_l')+world(p,r,'leg_r'))/2 for p,r in zip(poses,roots)])
    gravity=np.diff(hip[305:344,1],n=2)*900
    checks={'same_23_second_clock':data['duration_ticks']==460 and all(len(data[k]['frames'])==691 for k in ('eva','angel')),
        'rigid_sachiel_no_retired_morph':not data.get('surface_deformation_r14'),
        'rendered_floor_clear':min(f['floor'] for f in floors)>=-.06,
        'kneepads_touch_floor':all(-.035<=k['pad_floor']<=.10 for k in knees),
        'planted_toes_no_slide':max(contacts.values())<.025,
        'brace_and_strike_contacts_preserved':max(hands.values())<.15,
        'world_rotation_continuity':max(v['max_world_step_degrees'] for v in continuity.values())<30,
        'ballistic_free_flight':gravity.max()-gravity.min()<.05 and gravity.mean()<-20}
    checks={k:bool(v) for k,v in checks.items()}
    out={'passed':all(checks.values()),'checks':checks,'sha256':hashlib.sha256(raw).hexdigest(),'surface_samples':floors,'kneepad_samples':knees,'foot_drift_blocks':contacts,'hand_drift_blocks':hands,'world_rotations':continuity,'ballistic_acceleration_blocks_s2':float(gravity.mean())}
    (OUT/'surface_audit.json').write_text(json.dumps(out,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in out.items() if k not in ('surface_samples','kneepad_samples')},indent=2),flush=True)
    raise SystemExit(0 if out['passed'] else 1)

if __name__=='__main__':main()
