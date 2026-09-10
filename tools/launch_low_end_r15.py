"""Optional current-world launcher; restores the previous user options on exit."""
from pathlib import Path
import json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];WORLD='SEELE_TV_WORLD_PREVIEW_20260906'
def main():
 if not (ROOT/'run/saves'/WORLD/'level.dat').exists():raise FileNotFoundError('The current SEELE world must be installed first')
 if not (ROOT/'run/resourcepacks/eva_real_model/pack.mcmeta').exists():raise FileNotFoundError('The private EVA model resource pack must be installed first')
 env=dict(os.environ);env['PYTHONUTF8']='1';java=Path(env.get('JAVA_HOME',''))
 if not (java/'bin/java.exe').exists():java=Path.home()/'jdks/jdk-17.0.19+10'
 if not (java/'bin/java.exe').exists():raise FileNotFoundError('JDK17 is required; set JAVA_HOME')
 env['JAVA_HOME']=str(java);env['PATH']=str(java/'bin')+os.pathsep+env.get('PATH','')
 def run(args):return subprocess.run(args,cwd=ROOT,env=env,check=True)
 run([sys.executable,'tools/fetch_renderer_mods_r15.py']);receipt=ROOT/'.Codex/low-end-r15-profile.json'
 run([sys.executable,'tools/configure_far_profile_r15.py','--profile','low-end','--apply','--receipt-file',str(receipt)])
 backup=json.loads(receipt.read_text())['backup']
 try:run([str(ROOT/'gradlew.bat'),'runClient','-PstrictHighDetail=true','-PquickPlayWorld='+WORLD,'-PdistantHorizons=true','-PlowEndClient=true'])
 finally:run([sys.executable,'tools/configure_far_profile_r15.py','--restore',backup])
if __name__=='__main__':main()
