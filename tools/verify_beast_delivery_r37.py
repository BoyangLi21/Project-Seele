"""Bind the final payload to scoped native captures and preserved user files."""
from pathlib import Path
import hashlib,json
from release_beast_r37 import ART,ROOT,payload,sha
from run_combat_review_r31 import compiled_hash

def main():
    names={'awakening':'native_combat_1790307938976','normal_unit01':'native_combat_1790308556465',
           'normal_un01':'native_combat_1790308378384','mouth_final':'native_combat_1790309101462'}
    proofs={};motions={p.name:sha(p) for p in (ART/'profiles').glob('*.json')}
    implementation=compiled_hash()
    for scope,name in names.items():
        media=ROOT/'artifacts/facility_r31'/name;proof=json.loads((media/'server_evidence.json').read_text())
        if not proof['passed'] or not proof['fleet_ids_unchanged']:raise ValueError('Failed native scope '+scope)
        if any(proof['inputs_sha256'][n]!=h for n,h in motions.items()):raise ValueError('Changed motion input '+scope)
        if scope!='awakening' and proof['implementation_sha256']!=implementation:raise ValueError('Changed implementation '+scope)
        if scope.startswith('normal'):
            client=json.loads((media/'client_evidence.json').read_text());stages={r['ordinary'] for r in client['normal_bones'] if r['stage']=='normal_empty' and r['ordinary']>=0}
            if stages!={0,1}:raise ValueError('Two distinct normal stages were not drawn')
        if scope=='mouth_final':
            for n,p in payload().items():
                if n.parts[0]!='resourcepacks':continue
                relative=p.parts[p.parts.index('assets'):];key='/'.join(relative)
                if proof['render_inputs_sha256'].get(key)!=sha(p):raise ValueError('Unreviewed final render input '+key)
            audit=json.loads((media/'material_samplers_r37.json').read_text())['projectseele:textures/entity/eva_unit01.png']
            if any(audit[n]['width']!=1024 or audit[n]['height']!=512 for n in ['normals','specular']):raise ValueError('Material samplers did not bind')
        proofs[scope]=dict(media=str(media),server_evidence_sha256=sha(media/'server_evidence.json'),implementation_sha256=proof['implementation_sha256'],cases=proof['cases'])
    baseline=json.loads((ROOT/'artifacts/facility_r31/baseline.json').read_text(encoding='utf-8-sig'))
    for n,h in baseline['original_user_files'].items():
        if sha(ROOT/n)!=h:raise ValueError('Owner file changed '+n)
    expected={'level.dat':'c59f342746f198c980002d1a3085039e478b0d997a81e5a783b0bdad2056a1d3',
              'data/projectseele_eva_fleet.dat':'e760a8b89b44743ee9554b670c9ccd0ddaadfc14422f2eac5d7e224a3c2447fc'}
    for n,h in expected.items():
        if sha(ROOT/'run/saves/SEELE_R31_WORLD'/n)!=h:raise ValueError('Formal world changed '+n)
    report=dict(native_passed=True,implementation_sha256=implementation,payload_sha256={n.as_posix():sha(p) for n,p in payload().items()},
                native=proofs,formal_world_sha256=expected,owner_files_preserved=15,visual_acceptance='Human review pending',
                scope_note='The complete awakening capture predates the closeup-only fixture/camera addition and refined seam geometry. Gameplay implementation and motions were unchanged; the final mesh and materials have their own exact-input native closeup.')
    (ART/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('R37 reviewed payload matched; protected files unchanged')
if __name__=='__main__':main()
