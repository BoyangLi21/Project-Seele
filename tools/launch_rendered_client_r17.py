"""Normal TV client: exact terrain by default, no resident build JVM."""
from pathlib import Path
import argparse,json,os,subprocess,sys
from configure_exact_rendering_r19 import ensure_local

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


def ensure_private_pack(game,review=False):
    """A recovery launch can clear selected packs while leaving files installed."""
    options=Path(game)/'options.txt'
    lines=options.read_text(encoding='utf8').splitlines()
    required='file/eva_real_model'
    for index,line in enumerate(lines):
        if line.startswith('resourcePacks:'):
            selected=json.loads(line.partition(':')[2])
            original=list(selected)
            if required not in selected:selected.append(required)
            extra='file/'+(review if isinstance(review,str) else 'eva_un_r21_review')
            selected=[p for p in selected if p not in ('file/eva_un_r21_review','file/eva_access_r22_review','file/eva_tv_r24_review')]
            if review:selected.append(extra)
            if original==selected:return
            lines[index]='resourcePacks:'+json.dumps(selected,ensure_ascii=False,separators=(',',':'))
            break
    else:lines.append('resourcePacks:'+json.dumps([required]+(['file/'+(review if isinstance(review,str) else 'eva_un_r21_review')] if review else [])))
    import datetime,shutil
    backup=ROOT/'.Codex/client-options-backup'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True,exist_ok=True);shutil.copy2(options,backup/options.name)
    options.write_text('\n'.join(lines)+'\n',encoding='utf8')

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
    ap=argparse.ArgumentParser();ap.add_argument('--world',default=DEFAULT_WORLD);ap.add_argument('--heap',default='6G');ap.add_argument('--review');ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--prepared-file',type=Path);ap.add_argument('--native-capture',action='store_true');ap.add_argument('--battle-clip',type=Path);ap.add_argument('--far-view');ap.add_argument('--movie-only',action='store_true');ap.add_argument('--gpu-terrain',action='store_true');ap.add_argument('--city-shaders',action='store_true');a=ap.parse_args()
    if a.prepared_file:return run_prepared(a.prepared_file,java_environment()[1])
    if not (ROOT/'run/saves'/a.world/'level.dat').is_file():raise FileNotFoundError('The selected world is not installed')
    if not (ROOT/'run/resourcepacks/eva_real_model/pack.mcmeta').is_file():raise FileNotFoundError('The private EVA resource pack is not installed')
    java,env=java_environment();prefer_discrete_gpu(java)
    subprocess.run([sys.executable,'tools/fetch_client_mods_r19.py'],cwd=ROOT,env=env,check=True)
    subprocess.run([sys.executable,'tools/fetch_piano_r22.py'],cwd=ROOT,env=env,check=True)
    ensure_local(ROOT/'run')
    if (ROOT/'run/resourcepacks/rotrblocks-v87-128x-2d.zip').is_file():
        from fetch_realistic_pack_r25 import install as ensure_realistic_pack
        ensure_realistic_pack(ROOT/'run',True)
    review_pack='eva_tv_r24_review' if a.review and a.review.startswith('r24-') else 'eva_access_r22_review' if a.review and a.review.startswith('r22-') else 'eva_un_r21_review'
    ensure_private_pack(ROOT/'run',review_pack if a.review and a.review.startswith(('r21-','r22-','r24-')) and (ROOT/'run/resourcepacks'/review_pack/'pack.mcmeta').exists() else False)
    command=[str(ROOT/'gradlew.bat'),'--no-daemon','writeClientLaunchR17','-PstrictHighDetail=true','-PoptimizedClient','-PexactTerrain','-PclientNavigation','-PclientHeap='+a.heap,'-PquickPlayWorld='+a.world]
    if a.gpu_terrain:
        from fetch_gpu_client_r19 import ensure_local as ensure_gpu
        ensure_gpu();command.append('-PgpuTerrain')
    if a.city_shaders:
        from fetch_city_shaders_r29 import install as install_city_shaders
        install_city_shaders(True);command.append('-PcityShaders')
    if a.native_capture:command.append('-PnativeCapture')
    if a.review:command.append('-PregionalBuild='+a.review)
    if a.review in ('r21-flight-riding','r22-flight-riding'):command.append('-PtvTransitCapture')
    if a.battle_clip:command.append('-PfirstBattleReviewClip='+str(a.battle_clip.resolve()))
    if a.far_view:command.append('-PfarViewOnly='+a.far_view)
    if a.movie_only:command.append('-PfirstBattleMovieOnly')
    subprocess.run(command,cwd=ROOT,env=env,check=True)
    if a.prepare_only:return 0
    # Automated reviews choose their own view distances after entry. Avoid
    # first loading the full 24-chunk play profile just to discard it then.
    # Restore only this option after the client exits; normal play keeps 24.
    option=ROOT/'run/options.txt';original_distance=None
    if a.review and not a.review.endswith('manual'):
        lines=option.read_text(encoding='utf8').splitlines()
        for i,line in enumerate(lines):
            if line.startswith('renderDistance:'):original_distance=line;lines[i]='renderDistance:8';break
        option.write_text('\n'.join(lines)+'\n',encoding='utf8')
    try:return run_prepared(ROOT/'.Codex/client-launch-r17.json',env)
    finally:
        if original_distance is not None:
            lines=option.read_text(encoding='utf8').splitlines();lines=[original_distance if s.startswith('renderDistance:') else s for s in lines];option.write_text('\n'.join(lines)+'\n',encoding='utf8')

if __name__=='__main__':raise SystemExit(main())
