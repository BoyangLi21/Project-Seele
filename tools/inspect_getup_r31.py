"""CPU-only source recovery contact/height analysis; never rewrites runtime clips."""
from pathlib import Path
import json,math
import numpy as np
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r31/recovery';OUT.mkdir(parents=True,exist_ok=True)
body=json.loads((ROOT/'run/projectseele-local-maps/eva_body_r31_review.json').read_text());all_metrics={};poses={}
def matrix_pose(rig,names,frame):
    matrices={};rot={n:np.eye(3) for n in rig};pos={n:np.zeros(3) for n in rig}
    for i,n in enumerate(names):
        q=frame['rotation_wxyz'][i];rot[n]=Rotation.from_quat([-q[1],-q[2],q[3],q[0]]).as_matrix();raw=np.asarray(frame['root_m'])*112 if n=='root' else np.asarray(frame.get('bone_position_xyz',{}).get(n,[0,0,0]));pos[n]=raw*[-1,1,1]/16
    def transform(n):
        if n not in matrices:
            b=rig[n];p=np.asarray(b['pivot'])*[-1,1,1]/16;m=np.eye(4);m[:3,:3]=rot[n];m[:3,3]=pos[n]+p-rot[n]@p;matrices[n]=transform(b['parent'])@m if b.get('parent') else m
        return matrices[n]
    for n in rig:transform(n)
    return matrices
edges=[('leg_l','shin_l'),('shin_l','foot_l'),('leg_r','shin_r'),('shin_r','foot_r'),('leg_l','leg_r'),('leg_l','torso_lower'),('leg_r','torso_lower'),('torso_lower','torso_upper'),('torso_upper','head'),('torso_upper','arm_l'),('torso_upper','arm_r'),('arm_l','forearm_l'),('forearm_l','hand_l'),('arm_r','forearm_r'),('forearm_r','hand_r')]
for key,short in [('1',''),('3','_un00'),('4','_un01')]:
    rig={b['name']:b for b in body['rigs'][key]};capture=json.loads((ROOT/'run/projectseele-local-maps'/('eva_combat_capture_r31'+short+'.json')).read_text());frames=capture['clips']['r31_get_up']['frames'];names=capture['bones'];support=body.get('rig_support',{}).get(key,body['support']);metrics=[];pose_list=[]
    for index,f in enumerate(frames):
        mats=matrix_pose(rig,names,f);points={n:(mats[n]@np.r_[np.asarray(rig[n]['pivot'])*[-1,1,1]/16,1])[:3]*5 for n in {n for edge in edges for n in edge}}
        for side in ('l','r'):
            if 'r30_knee_socket_'+side in rig:
                p=np.asarray(rig['r30_knee_socket_'+side]['pivot'])*[-1,1,1]/16;points['shin_'+side]=(mats['leg_'+side]@np.r_[p,1])[:3]*5
            else:
                p=np.asarray(rig['shin_'+side]['pivot'])*[-1,1,1]/16+[0,11.4/16,0];points['shin_'+side]=(mats['leg_'+side]@np.r_[p,1])[:3]*5
        floors={}
        for bone,vertices in support.items():
            if bone not in mats:continue
            p=np.asarray(vertices)/16;v=(np.c_[p,np.ones(len(p))]@mats[bone].T)[:,:3]*5;floors[bone]=float(v[:,1].min())
        floor=min(floors.values());adjusted={n:v+[0,-floor,0] for n,v in points.items()};pose_list.append(adjusted)
        row={'frame':index,'rawRootY':f['root_m'][1],'rawFloor':floor,'groundedHeadY':float(adjusted['head'][1]),'groundedHipY':float((adjusted['leg_l'][1]+adjusted['leg_r'][1])/2),'leftSoleY':floors.get('foot_l',floor)-floor,'rightSoleY':floors.get('foot_r',floor)-floor,'leftHandY':float(adjusted['hand_l'][1]),'rightHandY':float(adjusted['hand_r'][1]),'lowest':min(floors,key=floors.get)};metrics.append(row)
    all_metrics[key]=metrics;poses[key]=pose_list
indices=[0,60,120,180,230,250,270,290,310,330,350,370]
fig,axes=plt.subplots(3,len(indices),figsize=(25,8),facecolor='#edf1f4')
for row,key in enumerate(['1','3','4']):
    for col,index in enumerate(indices):
        ax=axes[row,col];p=poses[key][index]
        for a,b in edges:
            v=np.array([p[a],p[b]]);ax.plot(v[:,2],v[:,1],color='#1972a3' if a.endswith('_l') or b.endswith('_l') else '#bc6a31' if a.endswith('_r') or b.endswith('_r') else '#344758',lw=2)
        ax.axhline(0,color='#75847e',lw=.8);ax.set_xlim(-45,45);ax.set_ylim(-1,65);ax.set_aspect('equal');ax.set_title(f'rig {key}, f{index}',fontsize=9);ax.set_xticks([]);ax.set_yticks([])
fig.tight_layout();fig.savefig(OUT/'getup_source_side_sheet.png',dpi=130);plt.close(fig)
(OUT/'getup_source_metrics.json').write_text(json.dumps(all_metrics,indent=2));print(json.dumps({k:[v[i] for i in [230,250,270,290,310,330,350,370]] for k,v in all_metrics.items()},indent=2))
