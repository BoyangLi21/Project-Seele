"""Inspect actual submitted bone poses, then retain the native result and inputs."""
from pathlib import Path
import json,hashlib,argparse
import numpy as np
from scipy.spatial.transform import Rotation as R
import author_combat_foundation_r33 as author
ROOT=author.ROOT;OUT=author.OUT

def collect(label,variant,jump=False):
    report=ROOT/'run/saves/SEELE_FIELD_R31_REVIEW/Review'/('r31_combat_pass.json' if jump else 'r32_normal_pass.json')
    result=json.loads(report.read_text());assert result.get('passed'),result
    media=(ROOT/'run'/result['media']).resolve();data=json.loads((media/'client_evidence.json').read_text())
    result['motion_inputs_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (OUT/'profiles').glob('*.json')}
    contacts=data.get('support_contacts_r33',[])
    if contacts:
        continuous=[r['error_blocks'] for r in contacts if r['tick']>=3]
        result['rendered_toe_support']={'samples':len(continuous),'max_error_blocks':max(continuous),
            'max_including_fixture_teleports':max(r['error_blocks'] for r in contacts),
            'excluded':'First two ticks after independent review-case teleports; original rows retained'}
        assert max(continuous)<.1,result['rendered_toe_support']
    if not jump:
        author.old.configure(variant);hulls=author.old.BODY['rig_support'].get(str(variant),author.old.BODY['support']);minimum=[]
        for row in data['normal_bones']:
            if row['point']!='after' or not row['stage'].startswith('normal_') or row['tick']<3 or row['ordinary']<0:continue
            pose=author.rt.battle.hero_copy(author.rt.eva.idle)
            for n,v in row['bones'].items():pose.setq(n,R.from_euler('xyz',v[:3]));pose.setp(n,np.array(v[3:6])*[-1,1,1])
            floor=min(float((np.c_[hulls['foot_'+s],np.ones(len(hulls['foot_'+s]))]@pose.matrix('foot_'+s).T)[:,1].min())*.3125 for s in ('l','r'))
            minimum.append(floor+row['y']-281)
        result['actual_sole_surface']={'samples':len(minimum),'minimum_clearance_blocks_before_renderer_lift':min(minimum),'median_clearance_blocks':float(np.median(minimum))}
        assert min(minimum)>-.1,result['actual_sole_surface']
    (OUT/(label+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2));print(label,result.get('rendered_toe_support'),result.get('actual_sole_surface'),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--variant',type=int,default=1);p.add_argument('--jump',action='store_true');a=p.parse_args();collect(a.label,a.variant,a.jump)
