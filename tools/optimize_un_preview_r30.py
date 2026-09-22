"""Avoid an enormous intermediate JavaScript array when decoding HD GLBs."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];FOLDER=ROOT/'artifacts/facility_r30/models/delivery'
OLD=b'function Lf(i){let e=atob(i);return Uint8Array.from(e,t=>t.charCodeAt(0))}'
NEW=b'function Lf(i){if(typeof Uint8Array.fromBase64==="function")return Uint8Array.fromBase64(i);let e=atob(i),t=new Uint8Array(e.length);for(let n=0;n<e.length;n++)t[n]=e.charCodeAt(n);return t}'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def main():
    source=FOLDER/'preview.html';target=FOLDER/'preview.optimized.html';before=sha(source);pending=b'';count=0
    with source.open('rb') as src,target.open('wb') as dst:
        for block in iter(lambda:src.read(1024*1024),b''):
            pending+=block
            # The final bundled module is much smaller than this margin.
            if len(pending)>2*1024*1024:
                emit,pending=pending[:-1024*1024],pending[-1024*1024:];count+=emit.count(OLD);dst.write(emit.replace(OLD,NEW))
        count+=pending.count(OLD);dst.write(pending.replace(OLD,NEW))
    assert count==1,('Expected the known Lux viewer decoder exactly once',count)
    target.replace(source);(FOLDER/'preview_runtime_patch.json').write_text(json.dumps({'source_sha256':before,'result_sha256':sha(source),'replacement_count':count,'scope':'Only the known base64-to-typed-array helper; embedded models, manifest, evidence, controls and verification statuses are unchanged. Native fromBase64 with a bounded-memory fallback loop.'},indent=2))
    print('HD preview decoder optimized without modifying model or status data',flush=True)
if __name__=='__main__':main()
