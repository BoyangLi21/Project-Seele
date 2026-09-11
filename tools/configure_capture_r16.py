"""Bound background LOD work for capture, without lowering native image settings."""
from pathlib import Path
import json,shutil,tomllib
from configure_far_profile_r15 import put,dump_toml
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/tv_facilities_r16/capture_profile'
def main():
 OUT.mkdir(parents=True,exist_ok=True);path=ROOT/'run/config/DistantHorizons.toml'
 if not (OUT/'previous.toml').exists():shutil.copy2(path,OUT/'previous.toml')
 d=tomllib.loads(path.read_text(encoding='utf8'))
 changes={'common.multiThreading.numberOfThreads':1,'common.multiThreading.threadRunTimeRatio':'0.08','common.multiThreading.threadPriority':1,'common.worldGenerator.enableDistantGeneration':True,'common.worldGenerator.distantGeneratorMode':'PRE_EXISTING_ONLY','server.enableServerGeneration':True,'server.maxGenerationRequestDistance':96,'server.maxSyncOnLoadRequestDistance':96,'common.lodBuilding.worldCompression':'MERGE_SAME_BLOCKS','client.advanced.graphics.quality.lodChunkRenderDistanceRadius':96,'client.advanced.graphics.quality.verticalQuality':'HIGH','client.advanced.graphics.culling.enableCaveCulling':False,'client.advanced.graphics.culling.ignoredRenderBlockCsv':'minecraft:barrier,minecraft:structure_void,minecraft:light,minecraft:tripwire,projectseele:geofront_skyweave','client.advanced.graphics.texture.enableTexturedLods':False}
 for key,value in changes.items():put(d,key,value)
 path.write_text(dump_toml(d),encoding='utf8');(OUT/'changes.json').write_text(json.dumps(changes,indent=2));print('Capture LOD budget:1thread x0.08;96chunks;existingterrainonly;nativegraphicsunchanged')
if __name__=='__main__':main()
