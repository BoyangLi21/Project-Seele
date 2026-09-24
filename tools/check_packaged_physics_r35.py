"""Exercise the actual reobfuscated JAR with exactly its nested physics libraries."""
from pathlib import Path
import json,subprocess,zipfile,hashlib,os
from build_server_ready_pack import newest_project_jar
from launch_rendered_client_r17 import java_environment
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/combat_rebuild_r35/packaged_physics'

def main():
    OUT.mkdir(parents=True,exist_ok=True);jar=newest_project_jar();libraries=[]
    with zipfile.ZipFile(jar) as z:
        metadata=json.loads(z.read('META-INF/jarjar/metadata.json'))
        if len(metadata['jars'])!=3:raise ValueError('Unexpected physical runtime')
        for dependency in metadata['jars']:
            path=OUT/Path(dependency['path']).name;path.write_bytes(z.read(dependency['path']));libraries.append(path)
    cache=Path.home()/'.gradle/caches/modules-2/files-2.1'
    for module in ['com.google.code.gson/gson/2.10.1','org.joml/joml/1.10.5']:
        candidates=[p for p in (cache/module).rglob('*.jar') if not p.name.endswith('-sources.jar')]
        if len(candidates)!=1:raise ValueError('Ambiguous Minecraft library: '+module)
        libraries+=candidates
    java,env=java_environment();classpath=os.pathsep.join(map(str,[jar,*libraries]))
    subprocess.run([str(java/'bin/javac.exe'),'-cp',classpath,'-d',str(OUT),str(ROOT/'tools/java/PackagedPhysicsR35Smoke.java')],check=True,env=env)
    result=OUT/'result.json'
    subprocess.run([str(java/'bin/java.exe'),'-Xmx128m','-cp',str(OUT)+os.pathsep+classpath,'PackagedPhysicsR35Smoke',str(ROOT/'artifacts/combat_rebuild_r35/jbullet/articulated_bodies_r35.json'),str(result)],check=True,env=env)
    proof=json.loads(result.read_text());proof['mod_sha256']=hashlib.sha256(jar.read_bytes()).hexdigest();proof['scope']='Actual reobfuscated classes and their exact nested physics libraries, independent of development classes; not a remote multiplayer login test.'
    result.write_text(json.dumps(proof,indent=2));print(result)
if __name__=='__main__':main()
