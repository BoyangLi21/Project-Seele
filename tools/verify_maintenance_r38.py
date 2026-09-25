"""Collect scoped native evidence, including actual drawn surface seams."""
from pathlib import Path
import hashlib,json,re,shutil
from run_combat_review_r31 import compiled_hash
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/combat_facility_r38'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def native(log):
    text=(ART/log).read_text(encoding='utf8',errors='replace');matches=re.findall(r'Server evidence:\s*(.+?server_evidence[.]json)',text)
    if not matches:raise ValueError('Missing native output '+log)
    path=Path(matches[-1].strip());data=json.loads(path.read_text())
    if not data.get('passed') or not data.get('fleet_ids_unchanged'):raise ValueError('Failed native review '+log)
    return path.parent,data
def main():
    current=compiled_hash();results={}
    for key,log in [('close_contacts','close_contacts_final.log'),('prone_wreck','prone_seams_final.log'),('un_wreck','wreck_un01.log'),('close_finale','finale_seams_final.log')]:
        folder,data=native(log);row=dict(folder=str(folder),cases=data['cases'],implementation_sha256=data['implementation_sha256'])
        if key in ('prone_wreck','close_finale'):
            if data['implementation_sha256']!=current:raise ValueError('Final implementation changed '+key)
            joints=json.loads((folder/'joint_audit_r38.json').read_text());seams=json.loads((folder/'surface_seams_r38.json').read_text())
            if not joints['passed'] or not seams['passed'] or seams['compared_pairs']<100:raise ValueError('Final rendered attachments failed '+key)
            if key=='prone_wreck' and joints['physical_frames']<5:raise ValueError('No physical neck coverage')
            row.update(joints=joints,drawn_seams=seams)
        if key=='un_wreck':
            joints=json.loads((folder/'joint_audit_r38.json').read_text())
            if not joints['passed'] or joints['physical_frames']<5:raise ValueError('UN physical attachment coverage failed')
            row['joints']=joints
        results[key]=row
    for name in ['force_recovery','force_recovery_cargo']:
        d=json.loads((ART/(name+'.json')).read_text())
        if not d.get('passed'):raise ValueError('Transport maintenance failed '+name)
        results[name]=d
    log=(ART/'lighting_checked.log').read_text(encoding='utf8',errors='replace')
    if 'Using shaderpack: ComplementaryUnbound_r5.3_SEELE_R38.zip' not in log:raise ValueError('Wrong shader reviewed')
    if log.count('REGIONAL PHOTO REQUIRED SECTIONS PASS')<3:raise ValueError('Incomplete-room screenshots')
    photo_dir=ART/'lighting';photo_dir.mkdir(exist_ok=True);photos={}
    for scene in ['command','command_off','pyramid','transfer']:
        name='r38_checked_'+scene+'.png';source=ROOT/'run/screenshots'/name
        if ('REGIONAL PHOTO READY file='+name) not in log or not source.is_file():raise ValueError('Missing current scene '+scene)
        shutil.copy2(source,photo_dir/name);photos[scene]=dict(file=str(photo_dir/name),sha256=sha(source))
    baseline=json.loads((ART/'baseline.json').read_text())
    for name,h in baseline['original_user_files'].items():
        if sha(ROOT/name)!=h:raise ValueError('Owner file modified '+name)
    for name,h in baseline['world_files'].items():
        if sha(ROOT/'run/saves/SEELE_R31_WORLD'/name)!=h:raise ValueError('Formal world modified '+name)
    report=dict(passed=True,implementation_sha256=current,shader_sha256=sha(ART/'shaders/ComplementaryUnbound_r5.3_SEELE_R38.zip'),native=results,photos=photos,formal_world_preserved=True,owner_files_preserved=15,
        scope='Close-contact captures exercise the unchanged target/attack code; subsequent changes refine disabled-pose blending and add diagnostics. UN captures precede audit/test-fixture changes. Final prone and finisher captures bind the final implementation and actual emitted seams. Rendering preference remains for human review.')
    (ART/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('R38 native workflows, drawn seams, shader and saved progress verified')
if __name__=='__main__':main()
