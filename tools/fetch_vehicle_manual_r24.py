"""Restore the pinned SBW manual dependency from its official release."""
from pathlib import Path
import hashlib,urllib.request
ROOT=Path(__file__).resolve().parents[1]
NAME='Patchouli-1.20.1-85-FORGE.jar'
SHA='15aedda4efcc553d5e3c83aa867b62554bc2fab298b43f55ed324e10507a3605f0ec2c59c01476e6d80b2a49275ef080142e43a6e663f9463b62f520960fc203'
URL='https://cdn.modrinth.com/data/nU0bVIaL/versions/94dtOLgZ/'+NAME
def ensure():
    folder=ROOT/'.Codex/local-mods'
    if not (folder/'superbwarfare-0.8.9.1-hotfix-mc1.20.1-993063bed-all.jar').exists():return
    target=folder/NAME
    if target.exists():
        if hashlib.sha512(target.read_bytes()).hexdigest()!=SHA:raise RuntimeError('Inspect the changed manual dependency before replacing it')
        print('Verified',NAME);return
    with urllib.request.urlopen(urllib.request.Request(URL,headers={'User-Agent':'Project-SEELE-private-dev-bootstrap/1.0'}),timeout=60) as stream:data=stream.read()
    if hashlib.sha512(data).hexdigest()!=SHA:raise RuntimeError('Manual dependency checksum mismatch')
    temporary=target.with_suffix('.download');temporary.write_bytes(data);temporary.replace(target);print('Installed',NAME)
if __name__=='__main__':ensure()
