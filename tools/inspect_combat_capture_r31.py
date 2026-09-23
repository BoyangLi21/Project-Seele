"""CPU-only original-skeleton / EVA retarget contact sheet and source inventory."""
from pathlib import Path
import json
import struct
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import retarget_human_r12 as r

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/facility_r31/motion_sources'

def main():
    payload=json.loads((OUT/'eva_combat_capture_r31.json').read_text())
    selected=['grapple_start','shoulder_throw','air_downstrike','get_up']
    fig=plt.figure(figsize=(20,18),facecolor='#edf1f4')
    edges=[('leg_l','shin_l'),('shin_l','foot_l'),('leg_r','shin_r'),('shin_r','foot_r'),
           ('leg_l','leg_r'),('leg_l','torso_lower'),('leg_r','torso_lower'),('torso_lower','torso_upper'),
           ('torso_upper','head'),('torso_upper','arm_l'),('torso_upper','arm_r'),('arm_l','forearm_l'),
           ('forearm_l','hand_l'),('arm_r','forearm_r'),('forearm_r','hand_r')]
    for row,name in enumerate(selected):
        clip=payload['clips']['r31_'+name]
        for col,phase in enumerate(np.linspace(0,1,6)):
            index=round(phase*(len(clip['frames'])-1));pose=r.eva.decode(clip['frames'][index],payload['bones'])
            pts={k:pose.point(k)*5/16 for k in {n for pair in edges for n in pair}}
            for side in ('l','r'):
                pts['shin_'+side]=pose.point('leg_'+side,r.eva.K[side])*5/16
                pts['forearm_'+side]=pose.point('arm_'+side,r.eva.E[side])*5/16
            ax=fig.add_subplot(4,6,row*6+col+1,projection='3d')
            for aa,bb in edges:
                v=np.array([pts[aa],pts[bb]])
                colour='#2879ae' if aa.endswith('_l') or bb.endswith('_l') else '#c17535' if aa.endswith('_r') or bb.endswith('_r') else '#354657'
                ax.plot(v[:,0],v[:,2],v[:,1],color=colour,lw=2.6)
            ax.set_xlim(-38,38);ax.set_ylim(-38,38);ax.set_zlim(-4,70);ax.set_box_aspect((1,1,1));ax.view_init(elev=14,azim=-58)
            ax.set_title(f'{name}\n{phase*clip["duration_seconds"]:.2f}s',fontsize=11)
            ax.set_axis_off()
    fig.tight_layout();fig.savefig(OUT/'retarget_contact_sheet.png',dpi=125);plt.close(fig)
    path=OUT/'quaternius_ual2/UAL2_Standard_RM.glb';blob=path.read_bytes();size,kind=struct.unpack_from('<II',blob,12);gltf=json.loads(blob[20:20+size])
    animations=[]
    for a in gltf['animations']:
        inputs=[gltf['accessors'][sampler['input']] for sampler in a['samplers']]
        animations.append({'name':a['name'],'seconds':max(i.get('max',[0])[0] for i in inputs),
                           'channels':len(a['channels']),'keyframe_counts':sorted({i['count'] for i in inputs})})
    (OUT/'quaternius_ual2/actions.json').write_text(json.dumps({'format':'glTF2','bones':len(gltf['skins'][0]['joints']),
         'animations':animations,'source_url':'https://quaternius.com/packs/universalanimationlibrary2.html','license':'CC0 1.0',
         'motion_type':'Authored game animation; not claimed as human mocap'},indent=2))
    print('CPU skeletal inspection and verified GLB action list written')

if __name__=='__main__':main()
