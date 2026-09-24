"""Hand poses in the actual render rig, including the non-adapter thumbs."""
import numpy as np
from scipy.spatial.transform import Rotation as R

# Same anatomical opposition solved for the native mesh by its author. These
# are runtime rotation vectors, not Euler angles or long-finger hinge axes.
THUMB = {'l': (-59.326567, -140.163194, -6.397107),
         'r': (-59.107334, 140.223847, 6.348767)}

def apply(p, rig, closure=1.0):
    closure=float(np.clip(closure,0,1))
    for n,b in rig.items():
        if not n.startswith('finger_'):continue
        p.setp(n,[0,0,0])
        if '_axis_' in n:
            angles=np.asarray(b.get('rotation',[0,0,0]),float)*[-1,-1,1]
            if n.startswith('finger_thumb_axis_'):angles[2]+=(100 if n.endswith('_r') else -100)*closure
            p.setq(n,R.from_euler('xyz',angles,degrees=True))
        elif n.startswith('finger_thumb_tip') and 'finger_thumb_axis_'+n[-1] in rig:
            p.setq(n,R.from_euler('z',60*closure,degrees=True))
        elif n.startswith('finger_thumb_tip'):
            # The native thumb is a single rigid skin segment. Its tip marker
            # has no separate surface and must not introduce a second hinge.
            p.setq(n,R.identity())
        elif n.startswith('finger_thumb_') and '_axis_' in b.get('parent',''):
            p.setq(n,R.from_euler('z',45*closure,degrees=True))
        elif n.startswith('finger_thumb_'):
            p.setq(n,R.from_rotvec(np.radians(THUMB[n[-1]])*closure))
        else:
            angle=95 if '_tip_' in n else 65 if '_distal_' in n else 85
            p.setq(n,R.from_euler('z',angle*closure,degrees=True))

def names(rig):
    # Do not inherit the old 52-channel locomotion list: it predates the
    # thumb/adapter rig and silently omitted visible parts of each hand.
    return list(rig)

def refresh(directory):
    import json
    from pathlib import Path
    import author_gameplay_motion_r32 as common
    for key in range(5):
        common.configure(key);path=Path(directory)/f'eva_gameplay_r32_{key}.json';data=json.loads(path.read_text());rig=common.rt.eva.rig
        for label,c in data['clips'].items():
            closure=.5 if label=='r32_berserk_roar' else .72 if label.startswith(('r32_berserk_','r32_low_')) else 1
            p=common.rt.eva.Pose();apply(p,rig,closure)
            channels={data['bones'].index(n):[q.as_quat()[3],-q.as_quat()[0],-q.as_quat()[1],q.as_quat()[2]] for n,q in p.q.items() if n.startswith('finger_')}
            for f in c['frames']:
                for i,q in channels.items():f['rotation_wxyz'][i]=q
        data['hand_pose_revision']=2;path.write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
    print('Updated all five complete hand rigs')

if __name__=='__main__':
    import sys
    refresh(sys.argv[1])
