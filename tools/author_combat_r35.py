"""Support-led strikes, anatomical joints and distinct Sachiel posture."""
from pathlib import Path
import json
import numpy as np
from scipy.spatial.transform import Rotation as R
import author_tv_combat_r34 as base
import anatomical_hinge_r35 as hinge

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/combat_rebuild_r35/profiles'

class Actor(base.Actor):
    def anatomical_ik(self,p,a,b,c,joint,target,pole):
        hinge.solve(p,self.P,a,b,c,joint,target,pole,[1,0,0])
        return p.point(c)

    def solve_feet(self,p,goals,orientations=None):
        orientations=orientations or {s:R.identity() for s in ('l','r')}
        for _ in range(8):
            for s in ('l','r'):
                hip=p.point('leg_'+s);reach=np.linalg.norm(self.knees[s]-self.P['leg_'+s])+np.linalg.norm(self.P['foot_'+s]-self.knees[s])
                delta=hip-goals[s];length=np.linalg.norm(delta)
                if length>reach*.991:p.setp('root',p.p['root']-delta*(1-reach*.991/length))
        for s in ('l','r'):
            hinge.solve(p,self.P,'leg_'+s,'shin_'+s,'foot_'+s,self.knees[s],goals[s],[0,0,-1],[-1,0,0],orientations[s])

    def guard_hands(self):
        if not self.angel:return super().guard_hands()
        h=self.height
        return {'l':np.array([-.29*h,.62*h,-.13*h]),'r':np.array([.29*h,.65*h,-.15*h])}

    def decode(self,frame):
        if not self.angel:return self.rig.decode(frame,base.common.NAMES)
        p=self.rig.pose()
        for n,(w,x,y,z) in zip(self.names,frame['rotation_wxyz']):p.setq(n,R.from_quat([-x,-y,z,w]))
        for n,v in frame.get('bone_position_xyz',{}).items():p.setp(n,np.asarray(v)*[-1,1,1])
        p.setp('root',np.asarray(frame['root_m'])*112*[-1,1,1]);return p

    def attack(self,label,feral=False):
        clip,stats=super().attack(label,feral)
        # The follow-up cross and hook transfer weight through a stable stance.
        # Re-stepping both feet on every input made the old chain look shuffled.
        if not feral and label in ('cross','hook'):
            frames=[]
            for frame in clip['frames']:
                p=self.decode(frame);self.solve_feet(p,self.foot_base)
                frames.append(self.encode(p,[True,True]))
            clip.update(frames=frames,trajectory_m=[[0,0,0]]*len(frames),step_contacts=[[True,True]]*len(frames),support='weight_transfer',stance_locked=True)
        return clip,stats

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for key in [0,1,2,3,4,'sachiel']:
        actor=Actor(key);name='sachiel_gameplay_r32.json' if actor.angel else f'eva_gameplay_r32_{key}.json'
        data=json.loads((ROOT/'artifacts/combat_foundation_r33/profiles'/name).read_text())
        for label in ('jab','cross','hook','heavy','shove','stomp'):
            data['clips']['r32_'+label]=actor.attack(label)[0]
        data['clips']['r32_guard']=actor.guard()
        for label in ('advance','retreat','left','right'):data['clips']['r32_'+label]=actor.walk(label)
        if not actor.angel:
            data['clips']['r32_berserk_roar']=actor.roar()
            for side,label in [('l','hook'),('r','cross')]:data['clips']['r32_berserk_'+side]=actor.attack(label,True)[0]
        for name2 in ('jab','cross','hook','heavy','shove','stomp','guard','advance','retreat','left','right','berserk_roar','berserk_l','berserk_r'):
            if 'r32_'+name2 in data['clips']:data['sources'][name2]={'source':'Original R35 choreography: explicit knee/elbow hinges, planted follow-up strikes, support-led root travel','license':'MIT'}
        data['combat_foundation']=35;data['choreography']='anatomical_support_r35'
        (OUT/name).write_text(json.dumps(data,separators=(',',':')));print('Authored',key,flush=True)
if __name__=='__main__':main()
