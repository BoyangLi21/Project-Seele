"""Measure real fist/kick contacts and remove run-foot ground penetration without changing joint rotations."""
import copy,json,hashlib
from pathlib import Path
import numpy as np
import build_eva_body_r05 as rig
ROOT=rig.ROOT;PACK=rig.PACK;OUT=ROOT/'artifacts/first_battle_world_r10/motion';OUT.mkdir(parents=True,exist_ok=True)
load=lambda p:json.loads(p.read_text(encoding='utf8'))
def foot_vertices(side):
    p=rig.mesh['parts']['foot_'+side];return (np.array(p['vertices']).reshape(-1,8)[:,:3]+p['pivot'])*[-1,1,1]
FEET={s:foot_vertices(s) for s in ['l','r']}
def low(p,s):return float(((np.c_[FEET[s],np.ones(len(FEET[s]))]@p.matrix('foot_'+s).T)[:,1]).min())
def main():
    source=PACK/'motion/eva_connected_locomotion_r05.json';motion=load(source);before=copy.deepcopy(motion);lift=[]
    for frame in motion['clips']['run']['frames']:
        p=rig.decode(frame,motion['bones']);amount=max(0,-min(low(p,'l'),low(p,'r')));frame['root_m'][1]+=amount/112;lift.append(amount)
    motion['provenance_r10']=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),change='Root height follows the measured lowest running sole; all source joint quaternions retained')
    (PACK/'motion/eva_connected_locomotion_r10.json').write_text(json.dumps(motion,separators=(',',':')),encoding='utf8')
    contacts={};report={}
    for name in ['walk','run','crouch_walk']:
        contacts[name]={};report[name]={}
        for s in ['l','r']:
            a=np.array([low(rig.decode(f,motion['bones']),s) for f in motion['clips'][name]['frames']]);ground=a<max(.6,a.min()+.6)
            forward=[round(i/(len(a)-1),6) for i in range(len(a)) if ground[i] and not ground[(i-1)%len(a)]]
            reverse=[round(i/(len(a)-1),6) for i in range(len(a)) if not ground[i] and ground[(i-1)%len(a)]]
            contacts[name][s]=dict(forward=forward,reverse=reverse);report[name][s]=dict(minimum_model_y=float(a.min()),maximum_model_y=float(a.max()))
    assert min(report['run'][s]['minimum_model_y'] for s in ['l','r'])>-.001
    curves={};motion_dir=ROOT/'src/main/resources/assets/projectseele/motion'
    ordinary=load(motion_dir/'eva_ordinary_attack_group_c_v1.json');kick=load(motion_dir/'eva_kick_side_left_v1.json')
    for stage in range(4):
        name='ordinary_attack_group_c_stage_1_loop' if stage==3 else 'ordinary_attack_group_c_stage_'+str(stage+1);side='l' if stage==1 else 'r';points=[]
        for f in ordinary['clips'][name]['frames']:
            p=rig.decode(f,ordinary['bones']);p.setp('root',[0,p.p['root'][1],0]);points.append((p.point('hand_'+side,rig.P['finger_middle_'+side])*[-5/16,5/16,-5/16]).tolist())
        curves['ordinary_'+str(stage)]=points
    points=[];centre=FEET['l'].mean(0)
    for f in kick['clips']['kick_side_left']['frames']:
        p=rig.decode(f,kick['bones']);p.setp('root',[0,p.p['root'][1],0]);points.append((p.point('foot_l',centre)*[-5/16,5/16,-5/16]).tolist())
    curves['kick']=points
    (motion_dir/'eva_melee_contacts_r10.json').write_text(json.dumps(dict(schema=1,coordinate_system='Entity-relative blocks at yaw zero, excludes physics-owned root XZ',curves=curves),separators=(',',':'))+'\n',encoding='utf8')
    (motion_dir/'eva_gait_contacts_r10.json').write_text(json.dumps(dict(schema=1,contacts=contacts),indent=2)+'\n',encoding='utf8')
    report.update(max_run_lift_blocks=max(lift)*5/16,source_joint_rotations_unchanged=all(a['rotation_wxyz']==b['rotation_wxyz'] for a,b in zip(before['clips']['run']['frames'],motion['clips']['run']['frames'])),curves={k:len(v) for k,v in curves.items()})
    (OUT/'contact_geometry.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
