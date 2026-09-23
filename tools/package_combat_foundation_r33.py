"""Package the verified local runtime; never include or overwrite a save."""
from pathlib import Path
import json,hashlib,subprocess,zipfile,datetime
import build_server_ready_pack as base
ROOT=base.ROOT;PROOF=ROOT/'artifacts/combat_foundation_r33';OUT=ROOT/'artifacts/r33_runtime_update'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    checks={}
    names=['duel_pass','un00_motion_pass','un01_motion_pass','jump_pass','repair_nerv','repair_un0','repair_un1','carrier_clearance','repair_visual']
    hashes={p.name:sha(p) for p in (PROOF/'profiles').glob('*.json')}
    for name in names:
        p=PROOF/(name+'.json');d=json.loads(p.read_text(encoding='utf8'))
        if not d.get('passed'):raise ValueError('Native check missing or failed: '+name)
        if 'motion_inputs_sha256' in d and d['motion_inputs_sha256']!=hashes:raise ValueError('Motion inputs changed: '+name)
        checks[name]=sha(p)
    baseline=json.loads((ROOT/'artifacts/facility_r31/baseline.json').read_text(encoding='utf-8-sig'))
    for name,digest in baseline['original_user_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Owner file changed: '+name)
    OUT.mkdir(parents=True,exist_ok=True);runtime=OUT/'runtime_mods';base.copy_runtime_mods(runtime);jar=runtime/base.newest_project_jar().name
    receipt={'revision':'R33','protocol':37,'created':datetime.datetime.now().astimezone().isoformat(),
             'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
             'mod_sha256':sha(jar),'motion_profiles':hashes,'checks':checks,'world_files_included':False}
    guide='关闭游戏和服务器后，将 mods 与 projectseele-local-maps 覆盖到对应游戏目录。客户端和服务端都要更新，网络协议为 37。\n保留现有存档、模型、材质和光影。\n\n'+(ROOT/'docs/COMBAT_FOUNDATION_R33.md').read_text(encoding='utf8')
    target=OUT/'Project_SEELE_R33_Runtime_Update.zip'
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.write(jar,'mods/'+jar.name)
        for name in hashes:z.write(PROOF/'profiles'/name,'projectseele-local-maps/'+name)
        z.writestr('安装与操作说明.txt',guide);z.writestr('R33_UPDATE.json',json.dumps(receipt,ensure_ascii=False,indent=2))
        z.write(ROOT/'docs/ASSETS.md','素材来源与许可.md')
    receipt.update(zip_sha256=sha(target),zip_bytes=target.stat().st_size)
    (OUT/'RELEASE.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));print(target)
if __name__=='__main__':main()
