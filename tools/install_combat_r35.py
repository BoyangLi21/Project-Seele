"""Back up and install the reviewed R35 files without changing any world."""
from pathlib import Path
import json,hashlib,subprocess,datetime,shutil
from check_runtime_r35 import check
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/combat_rebuild_r35'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def inputs():
    result={p.name:p for p in (ART/'profiles').glob('*.json')}
    result['articulated_bodies_r35.json']=ART/'jbullet/articulated_bodies_r35.json'
    return result

def main():
    guard=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'java.exe' -or $_.Name -eq 'javaw.exe') -and $_.CommandLine -match 'BootstrapLauncher|cpw.mods.modlauncher|net.minecraft.client.main.Main|client-.*[.]args' }).Count"],capture_output=True,text=True,check=True)
    if int(guard.stdout.strip() or '0'):raise RuntimeError('Close the current Minecraft session before installing')
    paths=inputs();hashes={n:sha(p) for n,p in paths.items()}
    check(ART/'profiles',paths['articulated_bodies_r35.json'])
    proof=json.loads((ART/'acceptance.json').read_text())
    if not proof.get('native_passed') or proof.get('inputs_sha256')!=hashes:raise ValueError('Native evidence does not match these files')
    baseline=json.loads((ROOT/'artifacts/facility_r31/baseline.json').read_text(encoding='utf-8-sig'))
    for n,h in baseline['original_user_files'].items():
        if sha(ROOT/n)!=h:raise ValueError('Owner file changed: '+n)
    backup=ART/('runtime_backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
    rows=[]
    for name,path in paths.items():
        target=ROOT/'run/projectseele-local-maps'/name;before=sha(target) if target.exists() else None
        if target.exists():shutil.copy2(target,backup/name)
        shutil.copy2(path,target)
        if sha(target)!=hashes[name]:raise RuntimeError('Checksum mismatch '+name)
        rows.append({'file':name,'before_sha256':before,'after_sha256':hashes[name]})
    audition=ROOT/'run/resourcepacks/eva_roar_r34/pack.mcmeta';local_roar=False
    if audition.is_file():
        options=ROOT/'run/options.txt';shutil.copy2(options,backup/'options.before.txt');lines=options.read_text(encoding='utf8').splitlines()
        for i,line in enumerate(lines):
            if line.startswith('resourcePacks:'):
                selected=json.loads(line.partition(':')[2])
                if 'file/eva_roar_r34' not in selected:selected.append('file/eva_roar_r34')
                lines[i]='resourcePacks:'+json.dumps(selected,ensure_ascii=False);local_roar=True;break
        options.write_text('\n'.join(lines)+'\n',encoding='utf8')
    (ART/'installed.json').write_text(json.dumps({'revision':35,'protocol':39,'backup':str(backup),'world_modified':False,'files':rows,'existing_local_roar_audition_selected':local_roar},indent=2))
    check();print('Installed with exact backup:',backup)
if __name__=='__main__':main()
