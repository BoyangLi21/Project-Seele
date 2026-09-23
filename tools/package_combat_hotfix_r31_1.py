"""Owner-local R31.1 mod-only patch; never opens or writes a world."""
from pathlib import Path
import json,hashlib,zipfile,subprocess,datetime
import build_server_ready_pack as base

ROOT=base.ROOT
OUT=ROOT/'artifacts/r31_1_combat_hotfix'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    target=OUT/'Project_SEELE_R31_1_Combat_Fix.zip'
    if target.exists():raise FileExistsError('Keep the earlier patch intact')
    proof_root=ROOT/'artifacts/combat_repair_r32'
    cases=('normal_after_01.json','normal_after_un01.json','normal_after_variant_0.json','normal_after_variant_2.json','normal_after_variant_3.json','air_regression.json')
    reports={name:json.loads((proof_root/name).read_text(encoding='utf8')) for name in cases}
    if not all(r.get('passed') and all(c['passed'] for c in r['cases']) for r in reports.values()):raise ValueError('Repair checks have not completed')
    if len({r['media'] for r in reports.values()})!=len(cases):raise ValueError('Stale repeated review report')
    baseline=json.loads((ROOT/'artifacts/facility_r31/baseline.json').read_text(encoding='utf-8-sig'))
    for name,digest in baseline['original_user_files'].items():assert sha(ROOT/name)==digest,name
    base.validate_private_eva_mesh_contracts()
    runtime=OUT/'runtime_mods';base.copy_runtime_mods(runtime)
    jar=runtime/base.newest_project_jar().name
    guide=(ROOT/'docs/COMBAT_HOTFIX_R31_1.md').read_text(encoding='utf8')
    readme='R31.1 普通攻击修复\n\n关闭 Minecraft，把本压缩包解压至对应客户端或服务器的游戏目录，覆盖 mods/projectseele-0.1.0.jar。\n客户端和服务器均更新该同名文件，网络协议仍为35。\n存档和R31资源包继续沿用；本补丁没有存档文件。\n本机开发入口继续使用 D:/eva/start_eva_test_r31.bat。\n\n'+guide
    receipt={'revision':'R31.1','protocol':35,'created':datetime.datetime.now().astimezone().isoformat(),'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'mod_filename':jar.name,'mod_sha256':sha(jar),'world_files_included':False,'resources_compatible_with':'R31','checks':{name:{'sha256':sha(proof_root/name),'media':r['media']} for name,r in reports.items()},'acceptance':'Specific regression repaired; overall combat quality rejected by user and not claimed complete.'}
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        archive.write(jar,'mods/'+jar.name)
        archive.writestr('安装与修复说明.txt',readme)
        archive.writestr('R31_1_PATCH.json',json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    receipt['zip_sha256']=sha(target);receipt['zip_bytes']=target.stat().st_size
    (OUT/'RELEASE.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(target)
    print('Mod SHA256 '+receipt['mod_sha256'])

if __name__=='__main__':main()
