"""Launch the bounded original-fleet review, never the user's formal save."""
from pathlib import Path
import json
import subprocess
import time
from launch_rendered_client_r17 import run_prepared, java_environment
from run_combat_review_r31 import temporary_options

ROOT = Path(__file__).resolve().parents[1]

def main():
    guard = subprocess.run(['powershell', '-NoProfile', '-Command', "@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'java.exe' -or $_.Name -eq 'javaw.exe') -and $_.CommandLine -match 'BootstrapLauncher|cpw.mods.modlauncher|net.minecraft.client.main.Main' }).Count"], capture_output=True, text=True, check=True)
    if int(guard.stdout.strip() or '0'):
        raise RuntimeError('Finish the current Minecraft JVM before reviewing.')
    source = json.loads((ROOT / '.Codex/client-launch-r17.json').read_text(encoding='utf8'))
    command = [a for a in source['command'] if not a.startswith('-Dprojectseele.regionalBuild=')]
    command.insert(1, '-Dprojectseele.regionalBuild=r32-sortie')
    if '--quickPlaySingleplayer' in command:
        command[command.index('--quickPlaySingleplayer') + 1] = 'SEELE_R32_SORTIE_REVIEW'
    else:
        command.extend(['--quickPlaySingleplayer', 'SEELE_R32_SORTIE_REVIEW'])
    source['command'] = command
    launch = ROOT / '.Codex/client-r32-sortie.json'
    launch.write_text(json.dumps(source), encoding='utf8')
    started=time.time()
    with temporary_options(ROOT / 'run/options.txt', ':', {'renderDistance': '6'}):
        with temporary_options(ROOT / 'run/config/oculus.properties', '=', {'enableShaders': 'false'}):
            code=run_prepared(launch, java_environment()[1])
    reports=ROOT/'run/saves/SEELE_R32_SORTIE_REVIEW/Review'
    evidence=reports/'r32_sortie_pass.json'
    if not evidence.exists() or evidence.stat().st_mtime<started:
        failure=reports/'r32_sortie_failure.json'
        raise RuntimeError(failure.read_text(encoding='utf8')[-600:] if failure.exists() else 'No current completion report')
    assert json.loads(evidence.read_text(encoding='utf8'))['pass']
    return code

if __name__ == '__main__':
    raise SystemExit(main())
