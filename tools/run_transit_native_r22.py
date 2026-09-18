"""Standalone commissioning uses the same finite flight-speed rule as the game."""
from pathlib import Path
import argparse,json,subprocess,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/access_r22/transit';CLASSES=ROOT/'.Codex/r22-native/classes'
def main():
 global OUT
 ap=argparse.ArgumentParser();ap.add_argument('--stage',default='rebuilt4');ap.add_argument('--out',default='built4');ap.add_argument('--cadence',action='store_true');ap.add_argument('--artifact-root',type=Path);a=ap.parse_args()
 if a.artifact_root:OUT=a.artifact_root.resolve();OUT.mkdir(parents=True,exist_ok=True)
 r=json.loads((ROOT/'artifacts/world_rebuild_r20/transit/runtime.json').read_text());java=Path(r['java']);asm=next((Path.home()/'.gradle/caches/modules-2/files-2.1/org.ow2.asm/asm/9.8').rglob('asm-9.8.jar'));CLASSES.mkdir(parents=True,exist_ok=True)
 cp=r['classpath']+';'+str(asm)+';'+str(CLASSES)+';'+str(ROOT/'.Codex/r20-java')
 sources=[ROOT/'tools/java'/name for name in ('FlightSpeedR22Agent.java','TransitRebuildR20.java','TransitCadenceR20.java','TransitSnapshotR20.java')]+[ROOT/'src/main/java/com/projectseele/world/UNFlightSpeedR22.java']
 subprocess.run([str(java/'javac.exe'),'-encoding','UTF-8','-cp',cp,'-d',str(CLASSES)]+list(map(str,sources)),check=True)
 resource='data/projectseele/transit/un_f2_fast_edges.txt';dest=CLASSES/resource;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'src/main/resources'/resource,dest)
 manifest=CLASSES/'MANIFEST.MF';manifest.write_text('Manifest-Version: 1.0\nPremain-Class: FlightSpeedR22Agent\n\n');agent=CLASSES.parent/'speed-agent.jar'
 subprocess.run([str(java/'jar.exe'),'cfm',str(agent),str(manifest),'-C',str(CLASSES),'.'],check=True)
 base=[str(java/'java.exe'),'-Xmx2G','-Dfile.encoding=UTF-8','-javaagent:'+str(agent),'-cp',cp]
 stage=ROOT/'.Codex/r22-native'/a.stage;out=OUT/a.out
 if not a.cadence:
  with (OUT/(a.out+'.log')).open('w',encoding='utf8') as log:subprocess.run(base+['TransitRebuildR20',str(OUT/'native_plan.json'),str(stage),str(out)],stdout=log,stderr=subprocess.STDOUT,check=True)
 for line,mode in [('trains','TRAIN'),('F2','AIRPLANE')]:
  with (OUT/(a.out+'_cadence_'+line+'.log')).open('w',encoding='utf8') as log:
   args=base+['TransitCadenceR20',str(stage),str(out/('cadence_'+line+'.json'))]
   if line=='F2':args+=['F2',mode]
   subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True)
   result=json.loads((out/('cadence_'+line+'.json')).read_text(encoding='utf8'));assert result['passed'] and len(result['cycles'])==(1 if line=='F2' else 4),'Empty or incomplete cadence coverage'
 # Expose evaluated curves, the new consists and native departure databases.
 with (OUT/(a.out+'_snapshot.log')).open('w',encoding='utf8') as log:subprocess.run(base+['TransitSnapshotR20',str(stage),str(out/'native_final.json')],stdout=log,stderr=subprocess.STDOUT,check=True)
 (out/'runtime.json').write_text(json.dumps(dict(stage=str(stage),java=str(java),classpath=cp,agent=str(agent)),indent=2));print('R22 native routes, minute cadence, faster F2 and snapshot finished')
if __name__=='__main__':main()
