"""Validate R36 phrase availability without touching a world."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def check(directory=None):
 directory=Path(directory) if directory else ROOT/'run/projectseele-local-maps'
 for key in [0,1,2,3,4,'sachiel']:
  path=directory/('sachiel_gameplay_r32.json' if key=='sachiel' else f'eva_gameplay_r32_{key}.json');data=json.loads(path.read_text())
  if data.get('rig_key')!=key or data.get('schema')!=2 or data.get('combat_foundation')!=36:raise ValueError('Incomplete R36 profile '+path.name)
  if data.get('choreography')!='captured_full_body_r36':raise ValueError('Rejected wrist-path candidate '+path.name)
  if key!='sachiel':
   required_hands={f'finger_thumb{s}_{side}' for s in ('','_tip') for side in ('l','r')}
   if key>=3:required_hands|={f'finger_thumb_axis_{side}' for side in ('l','r')}
   if data.get('hand_pose_revision')!=2 or not required_hands.issubset(data['bones']):raise ValueError('Incomplete hand articulation '+path.name)
  required=['guard','jab','cross','hook','heavy','advance','retreat','left','right']+([] if key=='sachiel' else ['low_jab','low_cross','low_hook','low_heavy','berserk_l','berserk_r'])
  for name in required:
   c=data['clips']['r32_'+name]
   if len(c['frames'])!=len(c['trajectory_m']) or len(c['frames'])<20:raise ValueError('Incomplete phrase '+name)
   for f in c['frames']:
    if len(f['rotation_wxyz'])!=len(data['bones']):raise ValueError('Rig mismatch '+path.name)
 body=json.loads((ROOT/'run/projectseele-local-maps/articulated_bodies_r35.json').read_text())
 if set(body['models'])!={'0','1','2','3','4','sachiel'}:raise ValueError('Physical body set missing')
 print('R36 phrase profiles ready; protocol 41. Functional validation is not aesthetic approval.')
if __name__=='__main__':check()
