"""Boot the actual reobfuscated distribution on Forge, using a disposable copy."""
from pathlib import Path
import argparse,hashlib,json,os,queue,shutil,subprocess,threading,time
import build_server_ready_pack as base
ROOT=base.ROOT;OUT=ROOT/'artifacts/server-ready-r28';STAGE=OUT/'stage';TEST=OUT/'production-run'

def main(resume=False):
    if resume:
        assert base.sha256(next((TEST/'mods').glob('projectseele-*.jar')))==base.sha256(next((STAGE/'server/mods').glob('projectseele-*.jar')))
        assert (TEST/base.WORLD_NAME/'R28_BATCH.json').read_bytes()==(STAGE/'world/R28_BATCH.json').read_bytes()
    else:
        assert not TEST.exists(),'Do not overwrite an earlier production witness'
        shutil.copytree(STAGE/'server',TEST)
        shutil.copytree(STAGE/'world',TEST/base.WORLD_NAME)
    cached=ROOT/'.Codex/server-pack-cache/runtime-r25/libraries'
    if cached.exists() and not (TEST/'libraries').exists():shutil.copytree(cached,TEST/'libraries')
    spec=json.loads((ROOT/'tools/forge_runtime_r25.json').read_text());installer=TEST/spec['filename']
    shutil.copy2(ROOT/'.Codex/server-pack-cache'/spec['filename'],installer)
    assert hashlib.sha1(installer.read_bytes()).hexdigest()==spec['sha1']
    java=Path.home()/'jdks/jdk-17.0.19+10/bin/java.exe'
    with (OUT/'forge_install.log').open('w',encoding='utf8') as log:
        subprocess.run([str(java),'-jar',str(installer),'--installServer'],cwd=TEST,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1800)
    # Reuse this machine's existing development-server acceptance only in
    # the disposable test. The files distributed to the user retain false.
    assert 'eula=true' in (ROOT/'run/eula.txt').read_text(encoding='utf8')
    shutil.copy2(ROOT/'run/eula.txt',TEST/'eula.txt')
    properties=(TEST/'server.properties').read_text(encoding='utf-8-sig').replace('server-port=25565','server-port=25569').replace('view-distance=24','view-distance=8')+'\nserver-ip=127.0.0.1\n'
    (TEST/'server.properties').write_text(properties,encoding='utf8')
    args=TEST/'smoke_jvm_args.txt';args.write_text('-Xms1G\n-Xmx5G\n-XX:+UseG1GC\n-Dfile.encoding=UTF-8\n',encoding='utf8')
    command=[str(java),'@smoke_jvm_args.txt','@libraries/net/minecraftforge/forge/1.20.1-47.4.10/win_args.txt','nogui']
    proc=subprocess.Popen(command,cwd=TEST,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace',bufsize=1)
    events=queue.Queue()
    def consume():
        for line in proc.stdout:events.put(line)
        events.put(None)
    threading.Thread(target=consume,daemon=True).start()
    start=time.monotonic();ready_at=None;stopping=False;lines=[];witness=False
    with (OUT/'production_server.log').open('w',encoding='utf8') as log:
        while True:
            try:line=events.get(timeout=1)
            except queue.Empty:line=''
            if line is None:break
            if line:
                log.write(line);log.flush();lines.append(line)
                if 'Done (' in line and ready_at is None:
                    ready_at=time.monotonic();print('Production Forge server ready',flush=True)
                    proc.stdin.write('execute in projectseele:geofront run forceload add -12 3\nexecute in projectseele:geofront run forceload add 27 277\n');proc.stdin.flush()
            if ready_at and not witness and time.monotonic()-ready_at>12:
                proc.stdin.write('execute in projectseele:geofront run data get block -12 81 3\nexecute in projectseele:geofront as @e[type=projectseele:nerv_staff,nbt={StaffId:"fuyutsuki"},x=27,y=-406,z=277,distance=..2] run say R28_FUYUTSUKI_POST_LOADED\nexecute in projectseele:geofront run time query daytime\n');proc.stdin.flush();witness=True
            if ready_at and not stopping and time.monotonic()-ready_at>25:
                proc.stdin.write('stop\n');proc.stdin.flush();stopping=True
            if time.monotonic()-start>600:
                if proc.poll() is None:proc.stdin.write('stop\n');proc.stdin.flush()
                try:proc.wait(timeout=45)
                except subprocess.TimeoutExpired:proc.terminate()
                raise TimeoutError('Production server did not complete within 600 seconds')
    code=proc.wait(timeout=60);text=''.join(lines)
    checks={'exit_zero':code==0,'forge_ready':ready_at is not None,'seele_initialized':'Project SEELE initialized' in text,'surface_pylon_loaded':'projectseele:umbilical_pylon' in text,'clean_save':'Saving chunks' in text,'no_fatal':not any(s in text for s in ('Failed to start the minecraft server','Missing mandatory dependencies','Mixin apply failed','Exception in server tick loop','Encountered an unexpected exception'))}
    checks['commander_post_loaded']='R28_FUYUTSUKI_POST_LOADED' in text
    proof={'passed':all(checks.values()),'checks':checks,'mod_sha256':base.sha256(next((TEST/'mods').glob('projectseele-*.jar'))),'scope':'Reobfuscated private R28 JAR, production Forge 47.4.10, imported complete world, loaded GeoFront pylon and existing Fuyutsuki at new commander post, clean shutdown; loopback-only, 5 GiB test heap. No remote client login asserted.'}
    (OUT/'production_check.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(proof,indent=2),flush=True)
    assert proof['passed']

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--resume',action='store_true');main(parser.parse_args().resume)
