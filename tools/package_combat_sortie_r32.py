"""Local R32 runtime update. Preserves the owner's existing R31 worlds and resources."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import zipfile
import build_server_ready_pack as base

ROOT = base.ROOT
PROOF = ROOT / 'artifacts/combat_sortie_r32'
OUT = ROOT / 'artifacts/r32_runtime_update'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    expected = {
        'sortie_pass.json': 'pass',
        'duel_anatomical_pass.json': 'passed',
        'jump_final_pass.json': 'passed',
        'jump_early_pass.json': 'passed',
        'un00_motion_pass.json': 'passed',
        'un01_motion_pass.json': 'passed',
        'air_nerv_pass.json': 'passed',
        'visual_final_pass.json': 'passed',
    }
    evidence = {}
    for name, flag in expected.items():
        path = PROOF / name
        data = json.loads(path.read_text(encoding='utf8'))
        if not data.get(flag):
            raise ValueError(f'Incomplete native check: {name}')
        evidence[name] = {'sha256': sha(path), 'media': data.get('media')}
    visual = json.loads((PROOF / 'visual_final_pass.json').read_text(encoding='utf8'))
    if not visual.get('wreck_not_stood_up_in_transit') or not visual.get('wreck_delivery_keeps_damage'):
        raise ValueError('Fallen pickup and damage persistence must be checked in the rendered flight')
    baseline = json.loads((ROOT / 'artifacts/facility_r31/baseline.json').read_text(encoding='utf-8-sig'))
    for name, digest in baseline['original_user_files'].items():
        if sha(ROOT / name) != digest:
            raise ValueError(f'Original owner file changed: {name}')
    base.validate_private_eva_mesh_contracts()
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / 'Project_SEELE_R32_Runtime_Update.zip'
    if target.exists():
        raise FileExistsError(target)
    runtime = OUT / 'runtime_mods'
    base.copy_runtime_mods(runtime)
    jar = runtime / base.newest_project_jar().name
    profiles=[PROOF/'gameplay_sources'/name for name in [*(f'eva_gameplay_r32_{i}.json' for i in range(5)),'sachiel_gameplay_r32.json']]
    for profile in profiles:
        if json.loads(profile.read_text(encoding='utf8')).get('schema')!=2:raise ValueError(profile)
    motion_hashes={p.name:sha(p) for p in profiles}
    for name in ['duel_anatomical_pass.json','jump_final_pass.json','jump_early_pass.json','un00_motion_pass.json','un01_motion_pass.json']:
        if json.loads((PROOF/name).read_text(encoding='utf8')).get('motion_inputs_sha256')!=motion_hashes:raise ValueError('Motion input changed since native review: '+name)
    receipt = {
        'revision': 'R32', 'protocol': 36,
        'created': datetime.datetime.now().astimezone().isoformat(),
        'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'mod_sha256': sha(jar), 'mod_filename': jar.name,
        'world_files_included': False, 'resource_compatibility': 'Existing R31 model, texture and shader packs',
        'checks': evidence,
        'motion_profiles': motion_hashes,
        'quality_scope': 'Native workflow and regression evidence; subjective combat/artistic acceptance remains with the owner.',
    }
    guide = (ROOT / 'docs/COMBAT_SORTIE_R32.md').read_text(encoding='utf8')
    installation = ('R32 更新（客户端和服务端都要更新）\n\n'
        '先关闭 Minecraft 或服务器，再解压到对应游戏目录，覆盖 mods 和 projectseele-local-maps 两个文件夹。\n'
        '六份新动作 JSON 必须与模组一起安装，客户端和服务端都要有。\n'
        '网络协议为 36，旧协议 35 的客户端无法连接更新后的服务器。\n'
        '保留现有 R31 存档、模型包、材质和光影。本更新没有存档文件，不会覆盖玩家进度。\n'
        '本机开发入口：D:/eva/start_eva_test_r32.bat，仍使用 SEELE_R31_WORLD。\n\n' + guide)
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.write(jar, 'mods/' + jar.name)
        for profile in profiles:archive.write(profile,'projectseele-local-maps/'+profile.name)
        archive.writestr('安装与操作说明.txt', installation)
        archive.writestr('R32_UPDATE.json', json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    receipt['zip_sha256'] = sha(target)
    receipt['zip_bytes'] = target.stat().st_size
    (OUT / 'RELEASE.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(target)
    print('Mod SHA256:', receipt['mod_sha256'])

if __name__ == '__main__':
    main()
