"""Reversible client/server presets for the tested Minecraft/Forge versions."""
import argparse,json,shutil,tomllib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def dump_toml(data):
 lines=[]
 def emit(obj,path=''):
  if path:lines.append('['+path+']')
  for key,value in obj.items():
   if not isinstance(value,dict):lines.append(key+' = '+json.dumps(value,ensure_ascii=False))
  for key,value in obj.items():
   if isinstance(value,dict):lines.append('');emit(value,(path+'.' if path else '')+key)
 emit(data);return '\n'.join(lines)+'\n'
def put(data,path,value):
 parts=path.split('.');obj=data
 for name in parts[:-1]:obj=obj.setdefault(name,{})
 obj[parts[-1]]=value
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--game-dir',type=Path,default=ROOT/'run');ap.add_argument('--profile',choices=['low-end','server','bake-existing'],default='low-end');ap.add_argument('--apply',action='store_true');ap.add_argument('--restore',type=Path);ap.add_argument('--receipt-file',type=Path);args=ap.parse_args();game=args.game_dir.resolve()
 if args.restore:
  receipt=json.loads((args.restore/'receipt.json').read_text());assert str(game)==receipt['game_dir']
  for row in receipt['files']:
   dst=game/row['path']
   if row['existed']:shutil.copy2(args.restore/row['path'],dst)
   elif dst.exists():dst.unlink()
  print('Restored',args.restore);return
 profiles=ROOT/'artifacts/staff_world_r15/profiles'/args.profile;profiles.mkdir(parents=True,exist_ok=True)
 existing=game/'config/DistantHorizons.toml';d=tomllib.loads(existing.read_text()) if existing.exists() else {}
 common={'common.multiThreading.numberOfThreads':4 if args.profile=='bake-existing' else 2,'common.multiThreading.threadRunTimeRatio':.7 if args.profile=='bake-existing' else .2,'common.worldGenerator.enableDistantGeneration':args.profile=='bake-existing','common.worldGenerator.distantGeneratorMode':'PRE_EXISTING_ONLY','server.enableServerGeneration':args.profile!='low-end','server.maxGenerationRequestDistance':96,'server.maxSyncOnLoadRequestDistance':96,'server.enableRealTimeUpdates':True,'server.synchronizeOnLoad':True,'common.lodBuilding.worldCompression':'MERGE_SAME_BLOCKS','common.lodBuilding.disableUnchangedChunkCheck':args.profile=='bake-existing',
 'client.advanced.graphics.quality.lodChunkRenderDistanceRadius':96,'client.advanced.graphics.quality.horizontalQuality':'LOW','client.advanced.graphics.quality.verticalQuality':'HIGH','client.advanced.graphics.quality.increaseQualityWhenZoomedIn':False,'client.advanced.graphics.quality.lodBiomeBlending':0,
 'client.advanced.graphics.culling.enableCaveCulling':False,'client.advanced.graphics.culling.ignoredRenderBlockCsv':'minecraft:barrier,minecraft:structure_void,minecraft:light,minecraft:tripwire,projectseele:geofront_skyweave','client.advanced.graphics.texture.enableTexturedLods':False}
 if args.profile=='server':common['common.worldGenerator.enableDistantGeneration']=True
 # Remote requests stay enabled; singleplayer only imports pre-existing chunks
 # at a small background budget after the main cache has been prepared.
 if args.profile=='low-end':
  common.update({'common.worldGenerator.enableDistantGeneration':True,'server.enableServerGeneration':True,'common.multiThreading.numberOfThreads':1,'common.multiThreading.threadRunTimeRatio':.1})
 for k,v in common.items():put(d,k,v)
 targets={'config/DistantHorizons.toml':dump_toml(d)}
 if args.profile!='server':
  options={'renderDistance':'4','simulationDistance':'5','graphicsMode':'0','renderClouds':'"false"','particles':'1','entityDistanceScaling':'0.65','biomeBlendRadius':'0','mipmapLevels':'1','enableVsync':'false','maxFps':'60'}
  p=game/'options.txt';lines=p.read_text(encoding='utf8').splitlines() if p.exists() else [];seen=set();out=[]
  for line in lines:
   key,sep,_=line.partition(':');out.append(key+':'+options[key] if sep and key in options else line);seen.add(key)
  out.extend(k+':'+v for k,v in options.items() if k not in seen);targets['options.txt']='\n'.join(out)+'\n'
  p=game/'config/projectseele-client.toml';client=tomllib.loads(p.read_text()) if p.exists() else {}
  for k,v in {'cockpit_video.targetFps':10,'cockpit_video.captureWidth':640,'cockpit_video.quality':.72,'cockpit_video.frameBudgetKiB':128}.items():put(client,k,v)
  targets['config/projectseele-client.toml']=dump_toml(client)
 for rel,content in targets.items():p=profiles/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content,encoding='utf8')
 if args.apply:
  backup=ROOT/'artifacts/staff_world_r15/profile_backups'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True);receipt={'game_dir':str(game),'profile':args.profile,'files':[]}
  for rel,content in targets.items():
   p=game/rel;receipt['files'].append({'path':rel,'existed':p.exists()});old=backup/rel;old.parent.mkdir(parents=True,exist_ok=True)
   if p.exists():shutil.copy2(p,old)
   p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content,encoding='utf8')
  (backup/'receipt.json').write_text(json.dumps(receipt,indent=2));print('Applied profile; restore backup:',backup)
  if args.receipt_file:args.receipt_file.parent.mkdir(parents=True,exist_ok=True);args.receipt_file.write_text(json.dumps({'backup':str(backup)},indent=2))
 else:print('Reviewable profile:',profiles)
if __name__=='__main__':main()
