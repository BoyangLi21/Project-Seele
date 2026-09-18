"""Fetch the pinned, user-requested playable piano from its official distribution."""
from pathlib import Path
import hashlib,json,os,urllib.request
ROOT=Path(__file__).resolve().parents[1]
def main():
 record=json.loads((ROOT/'tools/piano_mod_r22.json').read_text());target=ROOT/'.Codex/local-mods'/record['filename']
 if target.exists() and hashlib.sha512(target.read_bytes()).hexdigest()==record['sha512']:return
 request=urllib.request.Request(record['url'],headers={'User-Agent':'ProjectSeele-local-validation/1.0'})
 data=urllib.request.urlopen(request,timeout=90).read();assert hashlib.sha512(data).hexdigest()==record['sha512']
 target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_suffix('.download');temporary.write_bytes(data);os.replace(temporary,target)
 print('Installed verified playable piano',record['version'],flush=True)
if __name__=='__main__':main()
