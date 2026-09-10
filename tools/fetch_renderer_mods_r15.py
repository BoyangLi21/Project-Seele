"""Download exact official render/memory mod builds with SHA-512 verification."""
from pathlib import Path
import hashlib,urllib.request
ROOT=Path(__file__).resolve().parents[1]
MODS=[
 ('DistantHorizons-3.2.0-b-1.20.1-fabric-forge.jar','uCdwusMi','FWGxbEM3','1ecd2b58f026d09154b6d678ecea9452f22c8a9704f8dfb6cc7d64cf6b6f88118ba4284c7537f50107f34ee320dd2c6fc1adbbce2ef0e6a8d2db6783a60c5b93'),
 ('embeddium-0.3.31+mc1.20.1.jar','sk9rgfiA','UTbfe5d1','ffbf2da4685260a4d5c14c621708bd20722563f084f042d3dfb0a7b87f048e39299648c854a93939129da0d23a15a91ec628560d601e76074b08e275f6e132e9'),
 ('ferritecore-6.0.1-forge.jar','uXXizFIs','DG5Fn9Sz','a1960a7c03dc32d4ccaccaf28afdd9b078758bbd62d15a91d4039a83fa9397a098e89b69591f6bd5190254d9ee97e502504154b9aec764adb8c65f000b75ba2c')]
def main():
 folder=ROOT/'.Codex/local-mods';folder.mkdir(parents=True,exist_ok=True)
 for name,project,version,expected in MODS:
  target=folder/name
  if target.exists() and hashlib.sha512(target.read_bytes()).hexdigest()==expected:print('Verified',name);continue
  request=urllib.request.Request(f'https://cdn.modrinth.com/data/{project}/versions/{version}/{name}',headers={'User-Agent':'ProjectSeele/private-test'})
  with urllib.request.urlopen(request,timeout=120) as response:data=response.read()
  if hashlib.sha512(data).hexdigest()!=expected:raise ValueError('Hash mismatch: '+name)
  temporary=target.with_suffix('.download');temporary.write_bytes(data);temporary.replace(target);print('Installed',name)
if __name__=='__main__':main()
