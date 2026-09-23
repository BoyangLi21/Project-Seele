"""Install only the reviewed profiles, with exact backups and no save edits."""
from pathlib import Path
import json,hashlib,subprocess,datetime,shutil
from check_runtime_r33 import check
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/combat_foundation_r33'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    guard=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'java.exe' -or $_.Name -eq 'javaw.exe') -and $_.CommandLine -match 'BootstrapLauncher|cpw.mods.modlauncher|net.minecraft.client.main.Main|client-.*[.]args' }).Count"],capture_output=True,text=True,check=True)
    if int(guard.stdout.strip() or '0'):raise RuntimeError('Close Minecraft before installing runtime profiles')
    source=ART/'profiles';check(source);hashes={p.name:sha(p) for p in source.glob('*.json')}
    for name in ['duel_pass','un00_motion_pass','un01_motion_pass','jump_pass']:
        d=json.loads((ART/(name+'.json')).read_text())
        if not d.get('passed') or d.get('motion_inputs_sha256')!=hashes:raise ValueError('Review does not match the candidate: '+name)
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=ART/('runtime_backup_'+stamp);backup.mkdir()
    target=ROOT/'run/projectseele-local-maps';rows=[]
    for name,digest in hashes.items():
        p=target/name;old=sha(p) if p.exists() else None
        if p.exists():shutil.copy2(p,backup/name)
        shutil.copy2(source/name,p)
        if sha(p)!=digest:raise RuntimeError('Install checksum '+name)
        rows.append({'file':name,'before_sha256':old,'after_sha256':digest})
    receipt={'revision':33,'protocol':37,'backup':str(backup),'files':rows,'world_modified':False}
    (ART/'installed_motion_profiles.json').write_text(json.dumps(receipt,indent=2));check();print('Installed with backup:',backup)
if __name__=='__main__':main()
