"""Persistent full-quality local/client and server LOD profiles, with receipts."""
from pathlib import Path
import argparse,datetime,json,shutil,tomllib
from configure_far_profile_r15 import dump_toml,put

ROOT=Path(__file__).resolve().parents[1]
IGNORED='minecraft:barrier,minecraft:structure_void,minecraft:light,minecraft:tripwire,projectseele:geofront_skyweave'

def targets(game,profile):
    path=game/'config/DistantHorizons.toml'
    d=tomllib.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
    server=profile in ('server','bake-existing')
    workers,ratio=(4,'0.75') if profile=='bake-existing' else (4,'0.50') if server else (1,'0.10') if profile=='local' else (2,'0.25')
    settings={
        'common.multiThreading.numberOfThreads':workers,
        'common.multiThreading.threadRunTimeRatio':ratio,
        'common.multiThreading.threadPriority':1,
        'common.worldGenerator.enableDistantGeneration':True,
        'common.worldGenerator.distantGeneratorMode':'PRE_EXISTING_ONLY',
        'common.lodBuilding.worldCompression':'MERGE_SAME_BLOCKS',
        'common.lodBuilding.disableUnchangedChunkCheck':profile=='bake-existing',
        'server.enableServerGeneration':True,
        'server.enableRealTimeUpdates':True,
        'server.synchronizeOnLoad':True,
        'server.maxGenerationRequestDistance':192,
        'server.maxSyncOnLoadRequestDistance':192,
        'client.advanced.graphics.quality.lodChunkRenderDistanceRadius':128,
        'client.advanced.graphics.quality.horizontalQuality':'EXTREME',
        'client.advanced.graphics.quality.verticalQuality':'VERY_HIGH',
        'client.advanced.graphics.quality.maxHorizontalResolution':'BLOCK',
        'client.advanced.graphics.quality.vanillaFadeMode':'NONE',
        'client.advanced.graphics.quality.ditherDhFade':False,
        'client.advanced.graphics.quality.dhFadeFarClipPlane':False,
        'client.advanced.graphics.quality.transparency':'COMPLETE',
        'client.advanced.graphics.culling.enableCaveCulling':False,
        'client.advanced.graphics.culling.ignoredRenderBlockCsv':IGNORED,
        'client.advanced.graphics.texture.enableTexturedLods':False,
        'client.advanced.graphics.fog.enableVanillaFog':False,
    }
    for key,value in settings.items():put(d,key,value)
    out={'config/DistantHorizons.toml':dump_toml(d)}
    if not server:
        p=game/'config/embeddium-options.json'
        e=json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else {}
        # Cap background mesh preparation, retaining shader/texture quality.
        e.setdefault('performance',{}).update(chunk_builder_threads=2,
            use_compact_vertex_format=True,use_translucent_face_sorting_v2=True)
        out['config/embeddium-options.json']=json.dumps(e,indent=2)+'\n'
        p=game/'options.txt';lines=p.read_text(encoding='utf8').splitlines() if p.exists() else []
        old=dict(line.split(':',1) for line in lines if ':' in line)
        options={'renderDistance':str(max(18,int(old.get('renderDistance','18')))),
            'entityDistanceScaling':str(max(1.,float(old.get('entityDistanceScaling','1')))),
            'mipmapLevels':'4','particles':'0','graphicsMode':str(max(1,int(old.get('graphicsMode','1'))))}
        seen=set();updated=[]
        for line in lines:
            key,sep,_=line.partition(':');updated.append(key+':'+options[key] if sep and key in options else line);seen.add(key)
        updated.extend(k+':'+v for k,v in options.items() if k not in seen)
        out['options.txt']='\n'.join(updated)+'\n'
    return out,settings

def apply(game,profile,receipt_root=None):
    game=Path(game).resolve();files,settings=targets(game,profile)
    changed={k:v for k,v in files.items() if not (game/k).exists() or (game/k).read_text(encoding='utf-8-sig')!=v}
    if not changed:return None
    backup=(receipt_root or ROOT/'artifacts/rendering_r17/backups')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup.mkdir(parents=True);receipt={'game_dir':str(game),'profile':profile,'files':[],'settings':settings}
    for rel,content in changed.items():
        path=game/rel;receipt['files'].append({'path':rel,'existed':path.exists()})
        old=backup/rel;old.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():shutil.copy2(path,old)
        path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.r17.tmp');temp.write_text(content,encoding='utf8');temp.replace(path)
    (backup/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    return backup

def ensure_local(game):
    game=Path(game).resolve();marker=game/'config/projectseele-rendering-r17.json'
    if marker.is_file() and (game/'config/DistantHorizons.toml').is_file() and json.loads(marker.read_text()).get('profile_revision')==2:return None
    backup=apply(game,'local');marker.parent.mkdir(parents=True,exist_ok=True)
    marker.write_text(json.dumps({'version':17,'profile_revision':2,'profile':'local','initial_backup':str(backup),
        'note':'Defaults installed once; subsequent in-game visual preferences are preserved.'},indent=2),encoding='utf8')
    return backup

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--game-dir',type=Path,default=ROOT/'run');ap.add_argument('--profile',choices=('local','client','server','bake-existing'),default='local');ap.add_argument('--apply',action='store_true');ap.add_argument('--ensure-local',action='store_true');ap.add_argument('--restore',type=Path);a=ap.parse_args()
    if a.restore:
        d=json.loads((a.restore/'receipt.json').read_text());assert Path(d['game_dir']).resolve()==a.game_dir.resolve()
        for r in d['files']:
            p=a.game_dir/r['path'];assert p.resolve().is_relative_to(a.game_dir.resolve())
            if r['existed']:shutil.copy2(a.restore/r['path'],p)
            elif p.exists():p.unlink()
        print('Restored',a.restore);return
    if a.ensure_local:print('R17 local defaults; initial backup:',ensure_local(a.game_dir))
    elif a.apply:print('R17 profile',a.profile,'backup:',apply(a.game_dir,a.profile))
    else:print(json.dumps(targets(a.game_dir,a.profile)[1],indent=2))

if __name__=='__main__':main()
