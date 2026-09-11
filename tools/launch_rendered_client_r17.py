"""Normal TV client: current build, persistent far view, no resident build JVM."""
from pathlib import Path
import argparse,json,os,subprocess,sys
from configure_rendering_r17 import ensure_local

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_WORLD='SEELE_TV_WORLD_PREVIEW_20260906'

def java_environment():
    env=dict(os.environ);env['PYTHONUTF8']='1';env['OPENBLAS_NUM_THREADS']='1'
    java=Path(env.get('JAVA_HOME',''))
    if not (java/'bin/java.exe').exists():java=Path.home()/'jdks/jdk-17.0.19+10'
    if not (java/'bin/java.exe').exists():raise FileNotFoundError('JDK 17 is required; set JAVA_HOME')
    env['JAVA_HOME']=str(java);env['PATH']=str(java/'bin')+os.pathsep+env.get('PATH','')
    return java,env

def prefer_discrete_gpu(java):
    if os.name!='nt':return
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\DirectX\UserGpuPreferences') as key:
        for exe in ('java.exe','javaw.exe'):
            winreg.SetValueEx(key,str((java/'bin'/exe).resolve()),0,winreg.REG_SZ,'GpuPreference=2;')

def run_prepared(path,env=None):
    d=json.loads(Path(path).read_text(encoding='utf8'));command=d['command']
    assert command and Path(command[0]).name.lower() in ('java','java.exe')
    def quote(arg):
        if any(c in arg for c in '\r\n\0'):raise ValueError('Unexpected line break in a JVM argument')
        return '"'+arg.replace('\\','\\\\').replace('"','\\"')+'"'
    args=Path(path).with_suffix('.args');args.write_text('\n'.join(quote(s) for s in command[1:])+'\n',encoding='utf8')
    child=dict(os.environ if env is None else env);child.update(d['environment'])
    return subprocess.call([command[0],'@'+str(args.resolve())],cwd=d['workingDirectory'],env=child)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--world',default=DEFAULT_WORLD);ap.add_argument('--heap',default='6G');ap.add_argument('--review');ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--prepared-file',type=Path);ap.add_argument('--native-capture',action='store_true');ap.add_argument('--battle-clip',type=Path);ap.add_argument('--far-view');ap.add_argument('--movie-only',action='store_true');a=ap.parse_args()
    if a.prepared_file:return run_prepared(a.prepared_file,java_environment()[1])
    if not (ROOT/'run/saves'/a.world/'level.dat').is_file():raise FileNotFoundError('The selected world is not installed')
    if not (ROOT/'run/resourcepacks/eva_real_model/pack.mcmeta').is_file():raise FileNotFoundError('The private EVA resource pack is not installed')
    java,env=java_environment();prefer_discrete_gpu(java)
    subprocess.run([sys.executable,'tools/fetch_renderer_mods_r17.py'],cwd=ROOT,env=env,check=True)
    ensure_local(ROOT/'run')
    command=[str(ROOT/'gradlew.bat'),'--no-daemon','writeClientLaunchR17','-PstrictHighDetail=true','-PoptimizedClient','-PnativeCapture' if a.native_capture else '-PdistantHorizons','-PclientHeap='+a.heap,'-PquickPlayWorld='+a.world]
    if a.review:command.append('-PregionalBuild='+a.review)
    if a.battle_clip:command.append('-PfirstBattleReviewClip='+str(a.battle_clip.resolve()))
    if a.far_view:command.append('-PfarViewOnly='+a.far_view)
    if a.movie_only:command.append('-PfirstBattleMovieOnly')
    subprocess.run(command,cwd=ROOT,env=env,check=True)
    if a.prepare_only:return 0
    return run_prepared(ROOT/'.Codex/client-launch-r17.json',env)

if __name__=='__main__':raise SystemExit(main())
