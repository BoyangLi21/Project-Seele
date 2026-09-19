"""Install the author's unchanged texture archive locally, never mirror it."""
from pathlib import Path
import argparse,hashlib,json,shutil,urllib.request,zipfile
ROOT=Path(__file__).resolve().parents[1]

def install(game, enable=False):
    spec=json.loads((ROOT/'tools/realistic_pack_r25.json').read_text(encoding='utf8'))
    target=game/'resourcepacks'/spec['filename'];target.parent.mkdir(parents=True,exist_ok=True)
    def valid(path):
        if not path.is_file() or path.stat().st_size!=spec['bytes']:return False
        with path.open('rb') as stream:return hashlib.file_digest(stream,'sha512').hexdigest()==spec['sha512']
    if not valid(target):
        temp=target.with_suffix('.download')
        request=urllib.request.Request(spec['download_url'],headers={'User-Agent':'Project-SEELE-private-client/25'})
        with urllib.request.urlopen(request,timeout=120) as response,temp.open('wb') as output:shutil.copyfileobj(response,output)
        assert valid(temp),'Author archive checksum mismatch'
        temp.replace(target)
    with zipfile.ZipFile(target) as z:
        meta=json.loads(z.read('pack.mcmeta'));names=z.namelist()
        assert all(not n.startswith('assets/projectseele/') for n in names)
        assert 'assets/minecraft/textures/block/stone.png' in names
    report={'path':str(target),'sha512':spec['sha512'],'metadata':meta,'entries':len(names),'project_assets_overridden':False}
    (ROOT/'artifacts/facility_r25/texture').mkdir(parents=True,exist_ok=True)
    (ROOT/'artifacts/facility_r25/texture/archive.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    if enable:
        options=game/'options.txt';lines=options.read_text(encoding='utf8').splitlines();key='file/'+spec['filename']
        backup=ROOT/'artifacts/facility_r25/texture/options_before.txt'
        if not backup.exists():shutil.copy2(options,backup)
        for i,line in enumerate(lines):
            if line.startswith('resourcePacks:'):
                packs=json.loads(line.partition(':')[2]);packs=[p for p in packs if p!=key]
                idx=packs.index('file/eva_real_model') if 'file/eva_real_model' in packs else len(packs)
                packs.insert(idx,key);lines[i]='resourcePacks:'+json.dumps(packs,separators=(',',':'));break
        else:lines.append('resourcePacks:'+json.dumps([key,'file/eva_real_model']))
        # 1.20.1 predates supported_formats and otherwise drops the author's
        # advertised multi-version archive at startup (pack_format is 16).
        for i,line in enumerate(lines):
            if line.startswith('incompatibleResourcePacks:'):
                accepted=json.loads(line.partition(':')[2])
                if key not in accepted:accepted.append(key)
                lines[i]='incompatibleResourcePacks:'+json.dumps(accepted,separators=(',',':'));break
        else:lines.append('incompatibleResourcePacks:'+json.dumps([key]))
        options.write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--game',type=Path,default=ROOT/'run');ap.add_argument('--enable',action='store_true');a=ap.parse_args();install(a.game,a.enable)
