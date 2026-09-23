"""Record the normal driving camera and sample a sustained native combat interval."""
from pathlib import Path
import json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/combat_sortie_r32'

def main():
    log=OUT/'native_driver_combat.log';start=time.time();recorded=False
    with log.open('w',encoding='utf8') as output:
        process=subprocess.Popen([sys.executable,str(ROOT/'tools/run_combat_review_r31.py'),'--duel','--video','--variant','1','--gameplay-motion-directory',str(OUT/'gameplay_sources')],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
        while process.poll() is None:
            if not recorded and 'R31 COMBAT phase=NORMAL_MOVING' in log.read_text(encoding='utf8',errors='replace'):
                query="Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'java.exe' -and $_.CommandLine -match 'client-r31-combat[.]args' } | Select-Object -ExpandProperty ProcessId"
                pids=subprocess.check_output(['powershell','-NoProfile','-Command',query],text=True).split()
                if len(pids)!=1:raise RuntimeError('Expected the single guarded review JVM')
                subprocess.run([str(Path.home()/'jdks/jdk-17.0.19+10/bin/jcmd.exe'),pids[0],'JFR.start','name=seeleCombat','settings=profile','duration=20s','filename='+str(OUT/'combat_driver_profile.jfr'),'dumponexit=true'],check=True)
                recorded=True
            time.sleep(.5)
        if process.returncode:raise RuntimeError('Native driver review failed: '+str(process.returncode))
    folder=ROOT/'run/saves/SEELE_FIELD_R31_REVIEW/Review';report=max(folder.glob('r32_normal_*.json'),key=lambda p:p.stat().st_mtime)
    data=json.loads(report.read_text());assert report.stat().st_mtime>start and data.get('passed'),data.get('error',data)
    (OUT/'driver_view_pass.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    print('Driver camera PASS',data.get('media'),flush=True)

if __name__=='__main__':main()
