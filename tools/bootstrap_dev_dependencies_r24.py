"""Fetch pinned public compile/runtime dependencies; no private models/worlds.

Uses Python's standard library. Existing mismatched files are never overwritten.
"""
from pathlib import Path
import argparse,hashlib,os,tempfile,urllib.request
ROOT=Path(__file__).resolve().parents[1]
MODRINTH=[
    ('movingelevators-1.4.12-forge-mc1.20.1.jar','9KZOe6HD','noPT9kd8','1f61ea052a37e6fe1e927f84c017523155ebd69c'),
    ('supermartijn642configlib-1.1.8-forge-mc1.20.jar','LN9BxssP','ZKor79dR','f80f9eed728966adcfbcc848633e789645057281'),
    ('supermartijn642corelib-1.1.24-forge-mc1.20.1.jar','rOUBggPv','1qHDxHxo','866b07e2eb5addbc4a191b7b5ea6aae492ca9905')]
FILES=[(name,f'https://cdn.modrinth.com/data/{project}/versions/{version}/{name}','sha1',expected) for name,project,version,expected in MODRINTH]
FILES.append(('MTR-forge-4.0.5+1.20.1.jar','https://mediafilez.forgecdn.net/files/8244/920/MTR-forge-4.0.5%2B1.20.1.jar','sha256','97466eb715ab02f50a7f7e23f920bf9fdd9d5e4bbb12620c06c6751324c66e9a'))
def sha(path,algorithm):
    with path.open('rb') as stream:return hashlib.file_digest(stream,algorithm).hexdigest()
def main(check=False):
    folder=ROOT/'.Codex/local-mods';missing=[]
    for name,url,algorithm,expected in FILES:
        target=folder/name
        if target.exists():
            if sha(target,algorithm)!=expected:raise RuntimeError(f'Existing dependency hash differs; inspect it before replacing: {target}')
            print('Verified',name);continue
        if check:missing.append(name);continue
        folder.mkdir(parents=True,exist_ok=True)
        request=urllib.request.Request(url,headers={'User-Agent':'Project-SEELE-dev-bootstrap/1.0 (github.com/BoyangLi21/Project-Seele)'})
        with tempfile.NamedTemporaryFile(prefix=name+'.',suffix='.download',dir=folder,delete=False) as stream:
            temporary=Path(stream.name)
            try:
                with urllib.request.urlopen(request,timeout=60) as response:
                    while block:=response.read(1024*1024):stream.write(block)
            except Exception:
                stream.close();temporary.unlink(missing_ok=True);raise
        if sha(temporary,algorithm)!=expected:
            temporary.unlink();raise RuntimeError('Downloaded dependency failed its pinned checksum: '+name)
        os.replace(temporary,target);print('Fetched and verified',name)
    if missing:print('Missing:',', '.join(missing));return 1
    return 0
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');raise SystemExit(main(parser.parse_args().check))
