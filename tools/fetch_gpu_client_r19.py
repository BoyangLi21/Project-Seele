"""Optional upstream Acedium build, pinned for isolated GPU-renderer evaluation."""
from pathlib import Path
import hashlib,urllib.request

ROOT=Path(__file__).resolve().parents[1]
URL='https://github.com/ferriarnus/acedium/releases/download/v0.2.7-1.20.1/acedium-0.2.7-beta.jar'
SHA256='03cbd3abd91e23c46303d5326613dd8d96ffeb08cc0cb4eea50e74e52b516433'

def ensure_local():
    path=ROOT/'.Codex/local-mods-optional/acedium-0.2.7-beta.jar';path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==SHA256:return path
    request=urllib.request.Request(URL,headers={'User-Agent':'Project-Seele-local-client'})
    with urllib.request.urlopen(request,timeout=60) as response:data=response.read()
    if hashlib.sha256(data).hexdigest()!=SHA256:raise RuntimeError('Unexpected Acedium release bytes')
    temp=path.with_suffix('.download');temp.write_bytes(data);temp.replace(path);return path

if __name__=='__main__':print(ensure_local())
